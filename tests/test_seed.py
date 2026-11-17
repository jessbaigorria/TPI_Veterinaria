"""El seed se crea a través de los servicios y deja datos en todos los estados."""
from datetime import date

import pytest
from sqlalchemy import func, select

from app import reportes
from app.domain import reloj
from app.domain.cirugia import DerivacionCirugia
from app.domain.muestra import HistorialEstadoMuestraFila, MuestraBiologica
from app.domain.transporte import RecepcionRemito, RemitoBiologico
from app.reportes import Filtro
from app.seed import sembrar


@pytest.fixture(scope="module")
def sesion_seed():
    from app import db
    reloj.liberar()
    eng = db.crear_engine("sqlite://")
    db.init_db(eng)
    s = db.crear_fabrica_sesiones(eng)()
    sembrar(s, date(2026, 6, 15))
    yield s
    s.close()


def _estados(s, modelo):
    return {e for (e,) in s.execute(select(modelo.estado_codigo).distinct())}


def test_remitos_y_muestras_en_todos_los_estados(sesion_seed):
    assert _estados(sesion_seed, RemitoBiologico) == {
        "Armado", "Despachado", "EnTransito", "Recibido", "RecibidoConObservaciones"}
    assert _estados(sesion_seed, MuestraBiologica) == {
        "Extraida", "Empaquetada", "EnTransito", "Recibida", "Analizada", "Rechazada"}


def test_rechazos_por_precinto_y_por_temperatura(sesion_seed):
    motivos = {r.motivo_principal() for r in sesion_seed.scalars(select(RecepcionRemito)) if not r.es_aceptada()}
    assert motivos == {"Precinto roto", "Temperatura fuera de rango"}


def test_cirugias_en_distintos_estados(sesion_seed):
    estados = {d.estado.value for d in sesion_seed.scalars(select(DerivacionCirugia))}
    assert {"SOLICITADA", "PROGRAMADA", "REALIZADA", "RECHAZADA"} <= estados


def test_toda_muestra_tiene_historial_consistente(sesion_seed):
    for m in sesion_seed.scalars(select(MuestraBiologica)):
        h = m.historial()
        assert h[0].estado_anterior == "—" and h[0].estado_nuevo == "Extraída"
        assert h[-1].estado_nuevo == m.estado_actual()
        assert all(a.estado_nuevo == b.estado_anterior for a, b in zip(h, h[1:]))
        assert [x.fecha_hora for x in h] == sorted(x.fecha_hora for x in h)
    assert sesion_seed.scalar(select(func.count(HistorialEstadoMuestraFila.id))) > 40


def test_los_cinco_reportes_tienen_datos(sesion_seed):
    filtro = Filtro(desde=date(2026, 4, 1), hasta=date(2026, 6, 15))
    for codigo in reportes.REPORTES:
        rep = reportes.generar(codigo, sesion_seed, filtro if codigo != "vacunas" else Filtro(hasta=date(2026, 6, 15)))
        assert not rep.vacio, codigo


def test_seed_respeta_horarios_y_duraciones(sesion_seed):
    from app.domain.atencion import AtencionClinica
    from app.domain.enums import EstadoAtencion, TipoAtencion
    for a in sesion_seed.scalars(select(AtencionClinica)):
        assert a.fecha_hora_inicio.time() >= AtencionClinica.HORA_APERTURA
        assert a.fecha_hora_fin.time() <= AtencionClinica.HORA_CIERRE
        assert a.fecha_hora_fin - a.fecha_hora_inicio <= AtencionClinica.duracion_maxima(a.tipo)
        if a.estado is EstadoAtencion.RESERVADA:
            assert a.tipo is not TipoAtencion.URGENCIA

"""Las 5 validaciones de la consigna + la de cirugía (proceso opcional)."""
from datetime import date, datetime, timedelta

import pytest

from app.domain import reloj
from app.domain.enums import EstadoAtencion, RiesgoAnestesico
from app.domain.excepciones import (
    DerivacionCirugiaError, MascotaSinTitularError, MuestraRechazadaError, TurnoSuperpuestoError,
    VacunasPendientesError, VeterinariaError,
)
from app.domain.personas import Mascota
from app.services.atenciones import AtencionesService
from app.services.cirugias import CirugiasService
from app.services.mascotas import MascotasService
from app.services.resultados import ResultadosService


# --- 1. Toda mascota debe tener un responsable ------------------------------------------
def test_mascota_sin_titular_dominio():
    with pytest.raises(MascotaSinTitularError):
        Mascota(None, "Michi", "GATO", "HEMBRA", date(2023, 1, 1))


def test_mascota_sin_titular_servicio(sesion, base):
    with pytest.raises(MascotaSinTitularError):
        MascotasService(sesion).crear_mascota(None, "Michi", "GATO", "HEMBRA", "2023-01-01")
    with pytest.raises(MascotaSinTitularError):
        MascotasService(sesion).crear_mascota("", "Michi", "GATO", "HEMBRA", "2023-01-01")


def test_cambiar_titular_exige_titular(sesion, base):
    with pytest.raises(MascotaSinTitularError):
        MascotasService(sesion).cambiar_titular(base.firulais.id, None)
    assert base.firulais.titular is base.titular


# --- 2. Precinto roto → muestras rechazadas, no se procesan -----------------------------
def test_precinto_roto_impide_cargar_resultados(sesion, base):
    m = base.muestra()
    r = base.remito_en_transito([m])
    rec = base.recibir(r, integro=False)
    assert rec.resultado.value == "RECHAZADA"
    assert r.estado_actual() == "Recibido con observaciones"
    assert m.estado_actual() == "Rechazada"
    with pytest.raises(MuestraRechazadaError):
        ResultadosService(sesion).cargar_resultados(m.id, [{"tipo_analisis_id": base.hemograma.id,
                                                             "valores": "x"}], "lab")
    assert m.resultados == []


def test_codigo_de_precinto_distinto_se_trata_como_roto(sesion, base):
    from app.services.recepcion import RecepcionService
    m = base.muestra()
    r = base.remito_en_transito([m])
    rec = RecepcionService(sesion).recibir(r.id, base.lab.id, True, 5, "Lucas Gomez", codigo_precinto_leido="PRE-999999")
    assert rec.motivo_rechazo == "Precinto roto"
    assert m.estado_actual() == "Rechazada"


# --- 4. Sin superposición de turnos --------------------------------------------------------
def _turno(sesion, base, inicio, minutos=30, profesional=None, mascota=None, tipo="CONSULTA"):
    return AtencionesService(sesion).reservar_turno((mascota or base.firulais).id,
                                                    (profesional or base.perez).id, base.centro.id,
                                                    inicio, inicio + timedelta(minutes=minutos), tipo)


def test_turno_superpuesto(sesion, base):
    inicio = datetime(2026, 3, 12, 10, 0)
    _turno(sesion, base, inicio)
    with pytest.raises(TurnoSuperpuestoError):
        _turno(sesion, base, inicio + timedelta(minutes=15), mascota=base.rocco)
    # bordes contiguos no se superponen
    _turno(sesion, base, inicio + timedelta(minutes=30))
    # otro profesional, mismo horario: OK
    _turno(sesion, base, inicio, profesional=base.diaz)


def test_turno_cancelado_no_bloquea(sesion, base):
    inicio = datetime(2026, 3, 12, 11, 0)
    t = _turno(sesion, base, inicio)
    AtencionesService(sesion).cancelar(t.id, "El cliente no puede venir")
    assert t.estado is EstadoAtencion.CANCELADA
    otro = _turno(sesion, base, inicio, mascota=base.rocco)
    assert otro.id is not None


def test_turno_fin_debe_ser_posterior(sesion, base):
    with pytest.raises(VeterinariaError):
        _turno(sesion, base, datetime(2026, 3, 12, 12, 0), minutos=0)


def test_se_superpone_con(base):
    a = _turno(base.s, base, datetime(2026, 3, 13, 9, 0), 60, tipo="OTRO")
    b = _turno(base.s, base, datetime(2026, 3, 13, 9, 30), 60, profesional=base.diaz, tipo="CIRUGIA")
    c = _turno(base.s, base, datetime(2026, 3, 13, 10, 0), 30, mascota=base.rocco)
    assert a.se_superpone_con(b) and b.se_superpone_con(a)
    assert not a.se_superpone_con(c)
    assert not base.perez.esta_disponible(datetime(2026, 3, 13, 9, 45), datetime(2026, 3, 13, 10, 15))


# --- 5. Vacunas obligatorias -----------------------------------------------------------------
def test_vacunas_pendientes_detectadas(base):
    pendientes = base.rocco.historia_clinica.vacunas_pendientes()
    assert {v.nombre for v in pendientes} == {"Antirrábica", "Séxtuple"}  # vencida + nunca aplicada
    assert base.firulais.historia_clinica.vacunas_pendientes() == []
    # la no obligatoria nunca figura
    assert "Leptospirosis" not in {v.nombre for v in pendientes}


def test_cachorro_menor_a_la_edad_minima_no_tiene_pendientes(sesion, base):
    cachorro = MascotasService(sesion).crear_mascota(base.titular.id, "Toby", "PERRO", "MACHO",
                                                     reloj.hoy() - timedelta(weeks=6))
    assert cachorro.historia_clinica.vacunas_pendientes() == []


def test_control_con_vacunas_pendientes_bloquea(sesion, base):
    t = _turno(sesion, base, datetime(2026, 3, 10, 15, 0), mascota=base.rocco, tipo="CONTROL")
    with pytest.raises(VacunasPendientesError) as exc:
        AtencionesService(sesion).iniciar(t.id)
    assert {v.nombre for v in exc.value.vacunas} == {"Antirrábica", "Séxtuple"}
    assert sesion.get(type(t), t.id).estado is EstadoAtencion.RESERVADA


def test_consulta_sin_turno_con_pendientes_no_se_registra(sesion, base):
    from app.domain.atencion import AtencionClinica
    antes = sesion.query(AtencionClinica).count()
    with pytest.raises(VacunasPendientesError):
        AtencionesService(sesion).registrar_sin_turno(base.perez.id, base.centro.id, "CONSULTA",
                                                      mascota_id=base.rocco.id, inicio=datetime(2026, 3, 9, 16))
    assert sesion.query(AtencionClinica).count() == antes


def test_urgencia_con_pendientes_se_permite_con_advertencia(sesion, base):
    r = AtencionesService(sesion).registrar_sin_turno(base.perez.id, base.centro.id, "URGENCIA",
                                                      mascota_id=base.rocco.id, inicio=datetime(2026, 3, 9, 17))
    assert r.atencion.estado is EstadoAtencion.EN_PROGRESO
    assert r.advertencia and "Antirrábica" in r.advertencia
    assert "vacunas pendientes" in r.atencion.observaciones


def test_vacunacion_resuelve_las_pendientes(sesion, base):
    svc = AtencionesService(sesion)
    r = svc.registrar_sin_turno(base.perez.id, base.centro.id, "VACUNACION", mascota_id=base.rocco.id,
                                inicio=datetime(2026, 3, 10, 9, 0))
    svc.finalizar(r.atencion.id, "Se aplican vacunas", importe=5000, vacunas_aplicadas=[
        {"vacuna_id": base.antirrabica.id, "lote": "A1"}, {"vacuna_id": base.sextuple.id, "lote": "S1"}])
    assert base.rocco.historia_clinica.vacunas_pendientes() == []
    # ahora el control pasa
    t = _turno(sesion, base, datetime(2026, 3, 10, 18, 0), mascota=base.rocco, tipo="CONTROL")
    assert svc.iniciar(t.id).vacunas_pendientes == []


def test_vacuna_de_otra_especie_no_se_registra(sesion, base):
    with pytest.raises(VeterinariaError):
        MascotasService(sesion).registrar_vacuna_aplicada(base.firulais.id, base.antirrabica_gato.id)


# --- 6. Cirugía de alta complejidad -------------------------------------------------------
def _derivar(sesion, base, destino=None, riesgo=RiesgoAnestesico.ASA_II, estudios=""):
    a = base.atencion()
    return CirugiasService(sesion).derivar(a.id, (destino or base.sur).id, "Osteosíntesis de fémur",
                                           riesgo_anestesico=riesgo, estudios_prequirurgicos=estudios)


def test_derivar_a_clinica_sin_alta_complejidad(sesion, base):
    with pytest.raises(DerivacionCirugiaError):
        _derivar(sesion, base, destino=base.norte)


def test_programar_sin_consentimiento(sesion, base):
    svc = CirugiasService(sesion)
    d = _derivar(sesion, base)
    svc.aceptar(d.id, base.cirujano.id)
    with pytest.raises(DerivacionCirugiaError, match="consentimiento"):
        svc.programar(d.id, reloj.ahora() + timedelta(days=2))
    svc.registrar_consentimiento(d.id, "recepcion")
    svc.programar(d.id, reloj.ahora() + timedelta(days=2))
    assert d.estado.value == "PROGRAMADA"


def test_asa_iii_sin_estudios_no_se_programa(sesion, base):
    svc = CirugiasService(sesion)
    d = _derivar(sesion, base, riesgo=RiesgoAnestesico.ASA_III)
    svc.aceptar(d.id, base.cirujano.id)
    svc.registrar_consentimiento(d.id, "recepcion")
    with pytest.raises(DerivacionCirugiaError, match="estudios"):
        svc.programar(d.id, reloj.ahora() + timedelta(days=1))
    svc.registrar_estudios(d.id, "Hemograma y ECG normales")
    svc.programar(d.id, reloj.ahora() + timedelta(days=1))


def test_flujo_completo_cirugia_y_transiciones_invalidas(sesion, base):
    svc = CirugiasService(sesion)
    d = _derivar(sesion, base)
    with pytest.raises(DerivacionCirugiaError):
        svc.registrar_cirugia(d.id, "informe")  # todavía SOLICITADA
    with pytest.raises(DerivacionCirugiaError):
        svc.aceptar(d.id, base.perez.id)  # cirujano de otra clínica
    svc.aceptar(d.id, base.cirujano.id)
    svc.registrar_consentimiento(d.id, "recepcion")
    svc.programar(d.id, reloj.ahora() + timedelta(days=3))
    svc.registrar_cirugia(d.id, "Cirugía sin complicaciones")
    assert d.estado.value == "REALIZADA"
    with pytest.raises(DerivacionCirugiaError):
        svc.cancelar(d.id, "x")


def test_rechazo_requiere_motivo(sesion, base):
    svc = CirugiasService(sesion)
    d = _derivar(sesion, base)
    with pytest.raises(DerivacionCirugiaError):
        svc.rechazar(d.id, "")
    svc.rechazar(d.id, "Sin quirófano disponible")
    assert d.estado.value == "RECHAZADA"

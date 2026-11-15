"""Bloque C: horario 08:00–19:00, duración máxima por tipo, turnos solo a futuro, atención sin turno solo
presente o pasada, tipos CIRUGIA/OTRO y rango de fechas en filtros."""
from datetime import date, datetime, timedelta

import pytest

from app.domain import reloj
from app.domain.atencion import AtencionClinica
from app.domain.enums import EstadoAtencion, TipoAtencion
from app.domain.excepciones import DatosInvalidosError, TurnoSuperpuestoError
from app.services.atenciones import AtencionesService
from app.services.base import validar_rango_fechas
from tests.fabricas import AHORA  # reloj fijo: 10/03/2026 09:00

MANANA = AHORA.date() + timedelta(days=1)


def _en(dia: date, hora: int, minuto: int = 0) -> datetime:
    return datetime.combine(dia, datetime.min.time()).replace(hour=hora, minute=minuto)


def _reservar(mundo, inicio, fin=None, tipo=TipoAtencion.CONSULTA, profesional=None):
    return AtencionClinica.reservar(mundo.mascota, mundo.clinica, profesional or mundo.vet, inicio, fin, tipo)


# --- C3: tipos de atención ------------------------------------------------------------
def test_c3_enum_tiene_cirugia_y_otro():
    assert {"CIRUGIA", "OTRO"} <= {t.value for t in TipoAtencion}


def test_c3_reservar_no_admite_urgencia(mundo):
    with pytest.raises(DatosInvalidosError, match="urgencias no se reservan"):
        _reservar(mundo, _en(MANANA, 10), tipo=TipoAtencion.URGENCIA)
    for tipo in (TipoAtencion.CONSULTA, TipoAtencion.CONTROL, TipoAtencion.VACUNACION, TipoAtencion.CIRUGIA,
                 TipoAtencion.OTRO):
        assert tipo in AtencionClinica.TIPOS_RESERVABLES


def test_c3_sin_turno_admite_urgencia_cirugia_y_otro(mundo):
    for i, tipo in enumerate((TipoAtencion.URGENCIA, TipoAtencion.CIRUGIA, TipoAtencion.OTRO)):
        a = AtencionClinica.registrar_sin_turno(mundo.mascota, mundo.clinica, mundo.vet,
                                                _en(AHORA.date() - timedelta(days=1), 9 + i), tipo=tipo)
        assert a.tipo is tipo


# --- C4 / C5: duración por tipo y fin sugerido -------------------------------------------
@pytest.mark.parametrize("tipo,maximo", [(TipoAtencion.CONSULTA, 30), (TipoAtencion.CONTROL, 30),
                                         (TipoAtencion.VACUNACION, 30), (TipoAtencion.CIRUGIA, 60),
                                         (TipoAtencion.OTRO, 60)])
def test_c4_duracion_maxima_por_tipo(mundo, tipo, maximo):
    inicio = _en(MANANA, 10)
    a = _reservar(mundo, inicio, inicio + timedelta(minutes=maximo), tipo)
    assert a.fecha_hora_fin - a.fecha_hora_inicio == timedelta(minutes=maximo)
    with pytest.raises(DatosInvalidosError, match=f"como máximo {maximo} minutos"):
        _reservar(mundo, inicio + timedelta(hours=2), inicio + timedelta(hours=2, minutes=maximo + 5), tipo)


def test_c4_urgencia_maximo_60(mundo):
    inicio = _en(AHORA.date() - timedelta(days=1), 10)
    with pytest.raises(DatosInvalidosError, match="como máximo 60 minutos"):
        AtencionClinica.registrar_sin_turno(mundo.mascota, mundo.clinica, mundo.vet, inicio,
                                            inicio + timedelta(minutes=75), TipoAtencion.URGENCIA)


def test_c4_fin_debe_ser_mayor_que_inicio(mundo):
    inicio = _en(MANANA, 10)
    with pytest.raises(DatosInvalidosError, match="posterior a la de inicio"):
        _reservar(mundo, inicio, inicio)


@pytest.mark.parametrize("tipo,minutos", [(TipoAtencion.CONSULTA, 30), (TipoAtencion.VACUNACION, 30),
                                          (TipoAtencion.CIRUGIA, 60), (TipoAtencion.OTRO, 60)])
def test_c5_fin_sugerido_segun_tipo(mundo, tipo, minutos):
    a = _reservar(mundo, _en(MANANA, 11), tipo=tipo)
    assert a.fecha_hora_fin == _en(MANANA, 11) + timedelta(minutes=minutos)


def test_c5_fin_sugerido_no_pasa_del_cierre():
    assert AtencionClinica.fin_sugerido(_en(MANANA, 18, 30), TipoAtencion.CIRUGIA) == _en(MANANA, 19)


# --- C6: horario 08:00 a 19:00 -------------------------------------------------------------
@pytest.mark.parametrize("inicio,fin", [((7, 45), (8, 15)), ((18, 45), (19, 15)), ((19, 0), (19, 30)), ((6, 0), (6, 30))])
def test_c6_fuera_de_horario(mundo, inicio, fin):
    with pytest.raises(DatosInvalidosError, match="08:00 a 19:00"):
        _reservar(mundo, _en(MANANA, *inicio), _en(MANANA, *fin))


def test_c6_bordes_del_horario_permitidos(mundo):
    _reservar(mundo, _en(MANANA, 8), _en(MANANA, 8, 30))
    _reservar(mundo, _en(MANANA, 18, 30), _en(MANANA, 19))


def test_c6_sin_turno_fuera_de_horario(mundo):
    with pytest.raises(DatosInvalidosError, match="08:00 a 19:00"):
        AtencionClinica.registrar_sin_turno(mundo.mascota, mundo.clinica, mundo.vet,
                                            _en(AHORA.date() - timedelta(days=1), 21), tipo=TipoAtencion.URGENCIA)


# --- C7: turnos solo a futuro ------------------------------------------------------------------
def test_c7_no_se_reservan_turnos_en_el_pasado(mundo):
    with pytest.raises(DatosInvalidosError, match="posterior al actual"):
        _reservar(mundo, _en(AHORA.date() - timedelta(days=1), 10))
    with pytest.raises(DatosInvalidosError, match="posterior al actual"):
        _reservar(mundo, _en(AHORA.date(), 8, 30))          # hoy, antes de la hora actual (09:00)
    with pytest.raises(DatosInvalidosError, match="posterior al actual"):
        _reservar(mundo, AHORA)                              # exactamente ahora tampoco


def test_c7_hoy_mas_tarde_y_fechas_futuras_permitidas(mundo):
    assert _reservar(mundo, _en(AHORA.date(), 9, 30)).estado is EstadoAtencion.RESERVADA
    assert _reservar(mundo, _en(MANANA, 9)).estado is EstadoAtencion.RESERVADA


# --- C8: atención sin turno solo presente o pasada ---------------------------------------------
def test_c8_sin_turno_no_puede_ser_futura(mundo):
    with pytest.raises(DatosInvalidosError, match="no puede tener fecha y hora de inicio futura"):
        AtencionClinica.registrar_sin_turno(mundo.mascota, mundo.clinica, mundo.vet, AHORA + timedelta(minutes=10),
                                            tipo=TipoAtencion.URGENCIA)


def test_c8_sin_turno_por_defecto_ahora_y_pasado_permitido(mundo):
    a = AtencionClinica.registrar_sin_turno(mundo.mascota, mundo.clinica, mundo.vet, tipo=TipoAtencion.URGENCIA)
    assert a.fecha_hora_inicio == AHORA
    b = AtencionClinica.registrar_sin_turno(mundo.mascota, mundo.clinica, mundo.vet2,
                                            _en(AHORA.date() - timedelta(days=3), 15), tipo=TipoAtencion.CONSULTA)
    assert b.fecha_hora_inicio.date() < AHORA.date()


# --- C9: la superposición sigue funcionando junto con las reglas nuevas ----------------------------
def test_c9_superposicion_sigue_vigente(mundo):
    _reservar(mundo, _en(MANANA, 10), tipo=TipoAtencion.CIRUGIA)            # 10:00–11:00
    with pytest.raises(TurnoSuperpuestoError):
        _reservar(mundo, _en(MANANA, 10, 30))
    _reservar(mundo, _en(MANANA, 11))                                        # contiguo: OK


# --- servicio: duración inválida y rango de fechas ----------------------------------------------
def test_servicio_sin_turno_duracion_invalida(sesion, base):
    with pytest.raises(DatosInvalidosError):
        AtencionesService(sesion).registrar_sin_turno(base.perez.id, base.centro.id, "URGENCIA",
                                                      mascota_id=base.firulais.id, inicio="2026-03-09T10:00",
                                                      duracion_minutos="0")


def test_c1_rango_de_fechas():
    validar_rango_fechas(date(2026, 1, 1), date(2026, 1, 1))
    with pytest.raises(DatosInvalidosError, match="no puede ser anterior"):
        validar_rango_fechas(date(2026, 2, 1), date(2026, 1, 1))
    with pytest.raises(DatosInvalidosError, match="obligatorias"):
        validar_rango_fechas(None, date(2026, 1, 1), obligatorias=True)


def test_c1_listado_de_atenciones_rechaza_rango_invertido(sesion, base):
    with pytest.raises(DatosInvalidosError):
        AtencionesService(sesion).listar(base.centro.id, desde=date(2026, 3, 10), hasta=date(2026, 3, 1))

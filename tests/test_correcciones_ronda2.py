"""Segunda ronda de correcciones del grupo ("Errores y cosas a mejorar"): reglas de dominio y servicios."""
from datetime import datetime, timedelta

import pytest

from app.domain.enums import EstadoAtencion
from app.domain.excepciones import DatosInvalidosError, VeterinariaError
from app.domain.personas import Mascota
from app.services.atenciones import AtencionesService
from app.services.mascotas import MascotasService

NUEVA = {"nombre": "Pelusa", "especie": "GATO", "sexo": "HEMBRA", "fecha_nacimiento": "2025-01-10", "raza": "Siamés"}


def _nueva(base, **extra):
    return {"titular_id": base.titular.id, **NUEVA, **extra}


# --- Nueva mascota: solo letras en nombre y raza ------------------------------------------------
@pytest.mark.parametrize("campo,valor,mensaje", [("nombre", "Pelusa2", "solo admite letras"),
                                                 ("nombre", "", "obligatorio"),
                                                 ("raza", "Siamés 3", "solo admite letras")])
def test_nombre_y_raza_de_la_mascota_solo_letras(sesion, base, campo, valor, mensaje):
    with pytest.raises(DatosInvalidosError, match=mensaje):
        MascotasService(sesion).crear_mascota(**_nueva(base, **{campo: valor}))


def test_raza_es_opcional_y_la_edicion_valida_igual(sesion, base):
    m = MascotasService(sesion).crear_mascota(**_nueva(base, raza=""))
    assert m.raza == ""
    with pytest.raises(DatosInvalidosError, match="solo admite letras"):
        MascotasService(sesion).actualizar_mascota(m.id, nombre="R2D2")
    with pytest.raises(DatosInvalidosError, match="solo admite letras"):
        MascotasService(sesion).actualizar_mascota(m.id, raza="123")


# --- Nueva mascota: excluyente con la mascota elegida ---------------------------------------------
def test_sin_turno_no_acepta_mascota_elegida_y_nueva_a_la_vez(sesion, base):
    antes = sesion.query(Mascota).count()
    with pytest.raises(DatosInvalidosError, match="Ya elegiste una mascota"):
        AtencionesService(sesion).registrar_sin_turno(base.perez.id, base.centro.id, "URGENCIA",
                                                      mascota_id=base.firulais.id, nueva_mascota=_nueva(base),
                                                      inicio=datetime(2026, 3, 9, 16))
    assert sesion.query(Mascota).count() == antes


def test_reservar_turno_con_mascota_nueva(sesion, base):
    inicio = datetime(2026, 3, 11, 10, 0)
    a = AtencionesService(sesion).reservar_turno(None, base.perez.id, base.centro.id, inicio,
                                                 inicio + timedelta(minutes=30), "CONSULTA",
                                                 nueva_mascota=_nueva(base))
    assert a.estado is EstadoAtencion.RESERVADA
    assert a.mascota.nombre == "Pelusa" and a.mascota.titular is base.titular


def test_reservar_turno_exige_una_mascota(sesion, base):
    inicio = datetime(2026, 3, 11, 10, 0)
    svc = AtencionesService(sesion)
    with pytest.raises(DatosInvalidosError, match="Elegí una mascota"):
        svc.reservar_turno("", base.perez.id, base.centro.id, inicio, inicio + timedelta(minutes=30), "CONSULTA")
    with pytest.raises(DatosInvalidosError, match="Ya elegiste una mascota"):
        svc.reservar_turno(base.firulais.id, base.perez.id, base.centro.id, inicio,
                           inicio + timedelta(minutes=30), "CONSULTA", nueva_mascota=_nueva(base))


# --- Baja de mascota: cancela turnos reservados y la atención en curso ------------------------------
def test_baja_de_mascota_cancela_turno_reservado_y_atencion_en_curso(sesion, base):
    from app.services.cirugias import CirugiasService
    from app.services.derivaciones import DerivacionesService
    svc = AtencionesService(sesion)
    en_curso = base.atencion(mascota=base.firulais)
    turno = svc.reservar_turno(base.firulais.id, base.perez.id, base.centro.id, datetime(2026, 3, 12, 10, 0),
                               datetime(2026, 3, 12, 10, 30), "CONTROL")
    finalizada = base.atencion(mascota=base.firulais)
    svc.finalizar(finalizada.id, "Sano", importe=1000)

    MascotasService(sesion).dar_de_baja(base.firulais.id)

    assert en_curso.estado is EstadoAtencion.CANCELADA and turno.estado is EstadoAtencion.CANCELADA
    assert "fue dada de baja" in turno.observaciones
    assert finalizada.estado is EstadoAtencion.FINALIZADA          # lo ya atendido no se toca
    with pytest.raises(VeterinariaError, match="en curso"):
        DerivacionesService(sesion).emitir_orden(en_curso.id, base.lab.id, [base.hemograma.id])
    with pytest.raises(VeterinariaError, match="en curso"):
        CirugiasService(sesion).derivar(en_curso.id, base.sur.id, "Biopsia")


def test_no_se_reservan_turnos_para_una_mascota_dada_de_baja(sesion, base):
    MascotasService(sesion).dar_de_baja(base.rocco.id)
    with pytest.raises(VeterinariaError, match="dada de baja"):
        AtencionesService(sesion).reservar_turno(base.rocco.id, base.perez.id, base.centro.id,
                                                 datetime(2026, 3, 12, 11, 0), datetime(2026, 3, 12, 11, 30))


def test_baja_del_titular_cancela_los_turnos_de_sus_mascotas(sesion, base):
    from app.services.clientes import ClientesService
    turno = AtencionesService(sesion).reservar_turno(base.rocco.id, base.perez.id, base.centro.id,
                                                     datetime(2026, 3, 12, 12, 0), datetime(2026, 3, 12, 12, 30))
    ClientesService(sesion).dar_de_baja(base.titular.id)
    assert turno.estado is EstadoAtencion.CANCELADA
    assert not base.rocco.activa and not base.firulais.activa

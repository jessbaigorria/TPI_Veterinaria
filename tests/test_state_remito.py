"""Patrón State – RemitoBiologico y coordinación remito ↔ muestras ↔ precinto (tabla 5.3)."""
import pytest

from app.domain.enums import EstadoContenedor, EstadoPrecinto, ResultadoRecepcion
from app.domain.estados.estado_remito import (
    EstadoRemito, RemitoArmado, RemitoDespachado, RemitoEnTransito, RemitoRecibido,
    RemitoRecibidoConObservaciones,
)
from app.domain.excepciones import (
    MuestraRechazadaError, TransicionInvalidaError, VeterinariaError,
)
from app.domain.laboratorio import ResultadoAnalisis
from app.domain.transporte import Precinto


def test_flujo_completo(mundo):
    m = mundo.muestra()
    r = mundo.remito()
    assert isinstance(r.estado, RemitoArmado) and r.estado_actual() == "Armado"
    r.agregar_muestra(m)
    assert m.estado_codigo == "Empaquetada"
    r.cerrar(Precinto("PRE-1", "recepcion"), 4.0)
    assert r.precinto.estado is EstadoPrecinto.INTEGRO
    assert r.contenedor.estado is EstadoContenedor.EN_USO
    r.despachar(mundo.envio())
    assert isinstance(r.estado, RemitoDespachado)
    assert m.estado_codigo == "EnTransito"
    r.iniciar_transito()
    assert isinstance(r.estado, RemitoEnTransito)
    rec = mundo.lab.recibir_remito(r, True, 5.0, "lab.gomez")
    assert rec.resultado is ResultadoRecepcion.ACEPTADA
    assert isinstance(r.estado, RemitoRecibido) and r.estado.es_final()
    assert m.estado_codigo == "Recibida"
    assert r.envio.fecha_hora_llegada_real is not None
    assert r.contenedor.estado is EstadoContenedor.DISPONIBLE


def test_despachar_sin_muestras_falla(mundo):
    r = mundo.remito()
    with pytest.raises(TransicionInvalidaError):
        r.despachar(mundo.envio())


def test_cerrar_sin_muestras_falla(mundo):
    r = mundo.remito()
    with pytest.raises(TransicionInvalidaError):
        r.cerrar(Precinto("PRE-1", "u"), 4.0)


def test_despachar_sin_precinto_falla(mundo):
    r = mundo.remito()
    r.agregar_muestra(mundo.muestra())
    with pytest.raises(TransicionInvalidaError):
        r.despachar(mundo.envio())
    assert isinstance(r.estado, RemitoArmado)


def test_despachar_con_temperatura_fuera_de_rango_falla(mundo):
    r = mundo.remito_cerrado([mundo.muestra()], temperatura=12.0)
    with pytest.raises(TransicionInvalidaError, match="fuera del rango"):
        r.despachar(mundo.envio())


def test_agregar_muestra_fuera_de_armado_falla(mundo):
    r = mundo.remito_en_transito([mundo.muestra()])
    with pytest.raises(TransicionInvalidaError):
        r.agregar_muestra(mundo.muestra())


def test_agregar_muestra_despues_de_cerrar_falla(mundo):
    r = mundo.remito_cerrado([mundo.muestra()])
    with pytest.raises(TransicionInvalidaError):
        r.agregar_muestra(mundo.muestra())


def test_capacidad_del_contenedor(mundo):
    mundo.contenedor.capacidad = 1
    r = mundo.remito()
    r.agregar_muestra(mundo.muestra())
    with pytest.raises(VeterinariaError, match="capacidad"):
        r.agregar_muestra(mundo.muestra())


def test_contenedor_en_mantenimiento_no_se_usa(mundo):
    mundo.contenedor.enviar_a_mantenimiento()
    with pytest.raises(VeterinariaError):
        mundo.remito()


@pytest.mark.parametrize("accion", ["despachar", "iniciar_transito", "recibir", "cerrar"])
def test_transiciones_invalidas_en_estados_finales(mundo, accion):
    r = mundo.remito_en_transito([mundo.muestra()])
    mundo.lab.recibir_remito(r, True, 5.0, "lab")
    with pytest.raises((TransicionInvalidaError, VeterinariaError)):
        {"despachar": lambda: r.despachar(mundo.envio()),
         "iniciar_transito": r.iniciar_transito,
         "recibir": lambda: mundo.lab.recibir_remito(r, True, 5.0, "lab"),
         "cerrar": lambda: r.cerrar(Precinto("X", "u"))}[accion]()


def test_iniciar_transito_desde_armado_falla(mundo):
    with pytest.raises(TransicionInvalidaError):
        mundo.remito().iniciar_transito()


def test_recibir_despachado_sin_confirmar_retiro_falla(mundo):
    r = mundo.remito_cerrado([mundo.muestra()])
    r.despachar(mundo.envio())
    with pytest.raises(TransicionInvalidaError):
        r.recibir(object())


# --- coordinación --------------------------------------------------------------------
def test_despachar_pone_todas_las_muestras_en_transito(mundo):
    orden = mundo.orden([mundo.hemograma, mundo.orina])
    ms = [mundo.muestra(orden), mundo.muestra(orden, tipo="ORINA")]
    r = mundo.remito_cerrado(ms)
    r.despachar(mundo.envio())
    assert {m.estado_codigo for m in ms} == {"EnTransito"}


def test_precinto_roto_rechaza_todas_las_muestras(mundo):
    orden = mundo.orden([mundo.hemograma, mundo.orina])
    ms = [mundo.muestra(orden), mundo.muestra(orden, tipo="ORINA")]
    r = mundo.remito_en_transito(ms)
    rec = mundo.lab.recibir_remito(r, False, 5.0, "lab.gomez")
    assert rec.resultado is ResultadoRecepcion.RECHAZADA
    assert rec.motivo_rechazo == "Precinto roto"
    assert isinstance(r.estado, RemitoRecibidoConObservaciones)
    assert r.precinto.estado is EstadoPrecinto.ROTO
    assert {m.estado_codigo for m in ms} == {"Rechazada"}
    assert all(m.motivo_rechazo() == "Precinto roto" for m in ms)
    with pytest.raises(MuestraRechazadaError):
        ms[0].registrar_resultado(ResultadoAnalisis(mundo.hemograma, "x"), "lab")


def test_temperatura_fuera_de_rango_rechaza(mundo):
    m = mundo.muestra()
    r = mundo.remito_en_transito([m])
    rec = mundo.lab.recibir_remito(r, True, 15.0, "lab")
    assert rec.resultado is ResultadoRecepcion.RECHAZADA
    assert rec.motivo_rechazo.startswith("Temperatura fuera de rango")
    assert r.precinto.estado is EstadoPrecinto.INTEGRO
    assert isinstance(r.estado, RemitoRecibidoConObservaciones)
    assert m.estado_codigo == "Rechazada"
    assert r.contenedor.estado is EstadoContenedor.DISPONIBLE


def test_precinto_se_verifica_una_sola_vez(mundo):
    p = Precinto("PRE-9", "u")
    p.verificar(True, "lab")
    with pytest.raises(VeterinariaError):
        p.verificar(False, "lab")


def test_remito_a_otro_laboratorio_no_se_recibe(mundo):
    from app.domain.laboratorio import Laboratorio
    otro = Laboratorio(nombre="Otro", activo=True)
    r = mundo.remito_en_transito([mundo.muestra()])
    with pytest.raises(VeterinariaError):
        otro.recibir_remito(r, True, 4.0, "x")


def test_estados_finales_y_rehidratacion():
    assert {e.codigo for e in EstadoRemito.todos() if e.es_final()} == {
        "RemitoRecibido", "RemitoRecibidoConObservaciones"}
    assert isinstance(EstadoRemito.desde_nombre("RemitoEnTransito"), RemitoEnTransito)


def test_temperatura_fuera_de_rango_se_puede_volver_a_medir(mundo):
    m = mundo.muestra()
    r = mundo.remito_cerrado([m], temperatura=0.0)
    with pytest.raises(TransicionInvalidaError, match="fuera del rango"):
        r.despachar(mundo.envio())
    assert m.estado_codigo == "Empaquetada"          # la muestra no se pierde
    assert "registrar_temperatura" in r.acciones()
    r.registrar_temperatura_despacho(4.0)
    r.despachar(mundo.envio())
    assert isinstance(r.estado, RemitoDespachado) and m.estado_codigo == "EnTransito"


def test_volver_a_medir_solo_en_armado_y_precintado(mundo):
    r = mundo.remito()
    r.agregar_muestra(mundo.muestra())
    with pytest.raises(TransicionInvalidaError):
        r.registrar_temperatura_despacho(4.0)        # todavía sin precinto
    r2 = mundo.remito_en_transito([mundo.muestra()])
    with pytest.raises(TransicionInvalidaError):
        r2.registrar_temperatura_despacho(4.0)       # ya salió

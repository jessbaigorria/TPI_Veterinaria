"""Patrón State – MuestraBiologica: transiciones válidas, inválidas y estados finales."""
import pytest

from app.domain.estados.estado_muestra import (
    Analizada, Empaquetada, EnTransito, EstadoMuestra, Extraida, Recibida, Rechazada,
)
from app.domain.excepciones import MuestraRechazadaError, TransicionInvalidaError
from app.domain.muestra import ResultadoAnalisis


def _resultados(m, mundo):
    for t in m.analisis_pendientes():
        m.registrar_resultado(ResultadoAnalisis(t, "OK"), "Lucas Gomez")


def test_muestra_nace_extraida(mundo):
    m = mundo.muestra()
    assert isinstance(m.estado, Extraida)
    assert m.estado_actual() == "Extraída"
    assert m.estado_codigo == "Extraida"


def test_flujo_completo_valido(mundo):
    m = mundo.muestra()
    r = mundo.remito()
    m.empaquetar(r, "u")
    assert isinstance(m.estado, Empaquetada) and m.remito is r
    m.despachar("u")
    assert isinstance(m.estado, EnTransito)
    m.recibir("u")
    assert isinstance(m.estado, Recibida)
    _resultados(m, mundo)
    assert isinstance(m.estado, Analizada)
    assert m.estado.es_final()


def test_en_transito_a_rechazada(mundo):
    m = mundo.muestra()
    m.empaquetar(mundo.remito(), "u")
    m.despachar("u")
    m.rechazar("Precinto roto", "u")
    assert isinstance(m.estado, Rechazada)
    assert m.estado.es_final()
    assert m.motivo_rechazo() == "Precinto roto"


def test_recibida_queda_recibida_hasta_tener_todos_los_resultados(mundo):
    m = mundo.muestra()  # orden con hemograma + perfil renal (ambos SANGRE)
    m.empaquetar(mundo.remito(), "u"); m.despachar("u"); m.recibir("u")
    m.registrar_resultado(ResultadoAnalisis(mundo.hemograma, "Normal"), "lab")
    assert isinstance(m.estado, Recibida)
    m.registrar_resultado(ResultadoAnalisis(mundo.renal, "Urea 40"), "lab")
    assert isinstance(m.estado, Analizada)
    assert {r.analista for r in m.resultados} == {"lab"}


# --- cada transición inválida lanza TransicionInvalidaError -------------------------------
INVALIDAS = {
    "Extraida": ["despachar", "recibir", "rechazar", "analizar"],
    "Empaquetada": ["empaquetar", "recibir", "rechazar", "analizar"],
    "EnTransito": ["empaquetar", "despachar", "analizar"],
    "Recibida": ["empaquetar", "despachar", "recibir", "rechazar"],
    "Analizada": ["empaquetar", "despachar", "recibir", "rechazar", "analizar"],
    "Rechazada": ["empaquetar", "despachar", "recibir", "rechazar"],
}


def _llevar_a(mundo, codigo):
    m = mundo.muestra()
    pasos = ["Extraida", "Empaquetada", "EnTransito", "Recibida", "Analizada"]
    if codigo == "Rechazada":
        m.empaquetar(mundo.remito(), "u"); m.despachar("u"); m.rechazar("Temperatura", "u")
        return m
    for paso in pasos[1:pasos.index(codigo) + 1]:
        {"Empaquetada": lambda: m.empaquetar(mundo.remito(), "u"),
         "EnTransito": lambda: m.despachar("u"),
         "Recibida": lambda: m.recibir("u"),
         "Analizada": lambda: _resultados(m, mundo)}[paso]()
    return m


def _ejecutar(m, accion, mundo):
    {"empaquetar": lambda: m.empaquetar(mundo.remito(), "u"),
     "despachar": lambda: m.despachar("u"),
     "recibir": lambda: m.recibir("u"),
     "rechazar": lambda: m.rechazar("x", "u"),
     "analizar": lambda: m.registrar_resultado(ResultadoAnalisis(mundo.hemograma, "x"), "u")}[accion]()


@pytest.mark.parametrize("codigo,accion", [(c, a) for c, acciones in INVALIDAS.items() for a in acciones])
def test_transiciones_invalidas(mundo, codigo, accion):
    m = _llevar_a(mundo, codigo)
    assert m.estado_codigo == codigo
    historial_antes = len(m.historial())
    with pytest.raises(TransicionInvalidaError):
        _ejecutar(m, accion, mundo)
    assert m.estado_codigo == codigo  # no cambió
    assert len(m.historial()) == historial_antes


def test_rechazada_analizar_lanza_muestra_rechazada(mundo):
    m = _llevar_a(mundo, "Rechazada")
    with pytest.raises(MuestraRechazadaError):
        m.registrar_resultado(ResultadoAnalisis(mundo.hemograma, "x"), "lab")
    # MuestraRechazadaError no es una TransicionInvalidaError genérica
    assert not issubclass(MuestraRechazadaError, TransicionInvalidaError)


def test_estados_finales():
    finales = {e.codigo for e in EstadoMuestra.todos() if e.es_final()}
    assert finales == {"Analizada", "Rechazada"}


def test_rehidratacion_desde_nombre():
    for clase in (Extraida, Empaquetada, EnTransito, Recibida, Analizada, Rechazada):
        assert isinstance(EstadoMuestra.desde_nombre(clase.__name__), clase)


def test_nombres_para_mostrar():
    assert [e.nombre for e in (Extraida(), Empaquetada(), EnTransito(), Recibida(), Analizada(), Rechazada())] == [
        "Extraída", "Empaquetada", "En tránsito", "Recibida", "Analizada", "Rechazada"]


def test_acciones_disponibles(mundo):
    assert Extraida().acciones_disponibles() == ["empaquetar"]
    assert Rechazada().acciones_disponibles() == []
    assert "cargar_resultado" in Recibida().acciones_disponibles()

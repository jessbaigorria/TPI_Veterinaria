"""Patrón Observer: historial + actualización automática de la orden."""
from app.domain.enums import EstadoOrden
from app.domain.muestra import ResultadoAnalisis
from app.domain.observadores.observadores_muestra import (
    ActualizadorEstadoOrden, ObservadorMuestra, RegistroHistorial,
)


def test_muestra_recien_creada_tiene_un_registro(mundo):
    m = mundo.muestra(usuario="dra.perez")
    h = m.historial()
    assert len(h) == 1
    assert (h[0].estado_anterior, h[0].estado_nuevo, h[0].usuario, h[0].motivo) == (
        "—", "Extraída", "dra.perez", "Extracción en consulta")


def test_cada_cambio_crea_exactamente_un_registro(mundo):
    m = mundo.muestra()
    r = mundo.remito()
    m.empaquetar(r, "ana")
    assert len(m.historial()) == 2
    m.despachar("beto")
    m.recibir("carla")
    h = m.historial()
    assert len(h) == 4
    assert [(x.estado_anterior, x.estado_nuevo, x.usuario) for x in h[1:]] == [
        ("Extraída", "Empaquetada", "ana"), ("Empaquetada", "En tránsito", "beto"),
        ("En tránsito", "Recibida", "carla")]
    assert "REM" in h[1].motivo


def test_observadores_adjuntados_automaticamente(mundo):
    m = mundo.muestra()
    tipos = {type(o) for o in m._observadores()}
    assert tipos == {RegistroHistorial, ActualizadorEstadoOrden}
    assert all(isinstance(o, ObservadorMuestra) for o in m._observadores())


def test_observador_personalizado_recibe_notificaciones(mundo):
    eventos = []

    class Espia(ObservadorMuestra):
        def actualizar(self, muestra, anterior, nuevo, motivo, usuario):
            eventos.append((anterior.nombre, nuevo.nombre, motivo, usuario))

    m = mundo.muestra()
    m.agregar_observador(Espia())
    m.empaquetar(mundo.remito(), "u")
    assert eventos == [("Extraída", "Empaquetada", m.historial()[-1].motivo, "u")]


def test_orden_pasa_a_en_proceso_y_completada_sola(mundo):
    orden = mundo.orden([mundo.hemograma])
    m = mundo.muestra(orden)
    assert orden.estado is EstadoOrden.EMITIDA
    r = mundo.remito_cerrado([m])
    assert orden.estado is EstadoOrden.EMITIDA
    r.despachar(mundo.envio())
    assert orden.estado is EstadoOrden.EN_PROCESO
    r.iniciar_transito()
    mundo.lab.recibir_remito(r, True, 4.0, "lab")
    assert orden.estado is EstadoOrden.EN_PROCESO
    m.registrar_resultado(ResultadoAnalisis(mundo.hemograma, "OK"), "lab")
    assert orden.estado is EstadoOrden.COMPLETADA


def test_orden_completada_con_muestras_rechazadas(mundo):
    orden = mundo.orden([mundo.hemograma])
    r = mundo.remito_en_transito([mundo.muestra(orden)])
    mundo.lab.recibir_remito(r, False, 4.0, "lab")
    assert orden.estado is EstadoOrden.COMPLETADA


def test_orden_no_se_completa_si_falta_un_tipo_de_muestra(mundo):
    orden = mundo.orden([mundo.hemograma, mundo.orina])
    m = mundo.muestra(orden)  # solo sangre
    r = mundo.remito_en_transito([m])
    mundo.lab.recibir_remito(r, True, 4.0, "lab")
    m.registrar_resultado(ResultadoAnalisis(mundo.hemograma, "OK"), "lab")
    assert orden.estado is EstadoOrden.EN_PROCESO

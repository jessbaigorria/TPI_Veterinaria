"""Patrón Observer: historial + actualización automática de la orden."""
import pytest

from app.domain.enums import EstadoOrden, TipoMuestra
from app.domain.estados.estado_muestra import Extraida
from app.domain.excepciones import TransicionInvalidaError, VeterinariaError
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


# --- Comportamiento del Observer (O1–O10) -----------------------------------------------------------
class Espia(ObservadorMuestra):
    """Observador de prueba: guarda cada llamada que recibe y el estado que ve la muestra en ese momento."""

    def __init__(self):
        self.eventos = []

    def actualizar(self, muestra, anterior, nuevo, motivo, usuario):
        self.eventos.append({"muestra": muestra, "anterior": anterior, "nuevo": nuevo, "motivo": motivo,
                             "usuario": usuario, "estado_visto": muestra.estado,
                             "codigo_visto": muestra.estado_codigo})


def _con_espia(m):
    espia = Espia()
    m.agregar_observador(espia)
    return espia


def _registro(m):
    return next(o for o in m._observadores() if isinstance(o, RegistroHistorial))


def test_o1_el_observador_ve_el_estado_ya_cambiado(mundo):
    m = mundo.muestra()
    espia = _con_espia(m)
    m.empaquetar(mundo.remito(), "u")
    (e,) = espia.eventos
    assert e["codigo_visto"] == "Empaquetada" and e["estado_visto"].nombre == "Empaquetada"
    assert e["estado_visto"] == e["nuevo"] and e["estado_visto"] != e["anterior"]


def test_o2_una_transicion_fallida_no_notifica(mundo):
    m = mundo.muestra()
    espia = _con_espia(m)
    antes = len(m.historial())
    with pytest.raises(TransicionInvalidaError):
        m.despachar("u")                              # una muestra Extraída no se despacha
    assert espia.eventos == [] and len(m.historial()) == antes

    otra = mundo.muestra()
    otra.empaquetar(mundo.remito(), "u")
    otra.despachar("u")
    espia = _con_espia(otra)
    antes = len(otra.historial())
    with pytest.raises(VeterinariaError):
        otra.rechazar("", "u")                        # sin motivo
    assert espia.eventos == [] and len(otra.historial()) == antes


def test_o3_un_resultado_parcial_no_notifica(mundo):
    orden = mundo.orden([mundo.hemograma, mundo.renal])
    m = mundo.muestra(orden)
    r = mundo.remito_en_transito([m])
    mundo.lab.recibir_remito(r, True, 4.0, "lab")
    espia = _con_espia(m)
    antes = len(m.historial())
    m.registrar_resultado(ResultadoAnalisis(mundo.hemograma, "Hto 42 %"), "lab")
    assert espia.eventos == [] and len(m.historial()) == antes
    assert orden.estado is EstadoOrden.EN_PROCESO
    m.registrar_resultado(ResultadoAnalisis(mundo.renal, "Urea 38 mg/dL"), "lab")
    assert [(e["anterior"].nombre, e["nuevo"].nombre) for e in espia.eventos] == [("Recibida", "Analizada")]


def test_o4_una_notificacion_por_transicion_con_los_argumentos_exactos(mundo):
    m = mundo.muestra()
    espia = _con_espia(m)
    r = mundo.remito()
    m.empaquetar(r, "beto")
    m.despachar("carla")
    m.rechazar("Precinto roto", "ana")
    assert [(e["anterior"].nombre, e["nuevo"].nombre, e["motivo"], e["usuario"]) for e in espia.eventos] == [
        ("Extraída", "Empaquetada", f"Empaquetada en el remito {r.numero}", "beto"),
        ("Empaquetada", "En tránsito", "Despachada al laboratorio", "carla"),
        ("En tránsito", "Rechazada", "Precinto roto", "ana")]
    assert all(e["muestra"] is m for e in espia.eventos)


def test_o5_adjuntar_dos_veces_no_duplica(mundo):
    m = mundo.muestra()
    espia = Espia()
    m.agregar_observador(espia)
    m.agregar_observador(espia)
    cantidad = len(m._observadores())
    m.agregar_observador(_registro(m))                # volver a agregar el que ya tiene
    assert len(m._observadores()) == cantidad
    antes = len(m.historial())
    m.empaquetar(mundo.remito(), "u")
    assert len(espia.eventos) == 1 and len(m.historial()) == antes + 1


def test_o6_la_muestra_no_depende_de_sus_observadores(mundo):
    m = mundo.muestra()
    uno, dos = _con_espia(m), _con_espia(m)
    m.empaquetar(mundo.remito(), "u")
    assert len(uno.eventos) == len(dos.eventos) == 1
    assert (uno.eventos[0]["anterior"], uno.eventos[0]["nuevo"]) == (dos.eventos[0]["anterior"],
                                                                      dos.eventos[0]["nuevo"])

    sola = mundo.muestra()
    sola._observadores().clear()
    sola.empaquetar(mundo.remito(), "u")              # sin error
    assert sola.estado_codigo == "Empaquetada"
    # Quien escribe el historial es el observador: sin él solo queda la fila de nacimiento.
    assert [h.estado_nuevo for h in sola.historial()] == ["Extraída"]


def test_o7_registro_historial_con_valores_por_defecto(mundo):
    class RepoFalso(list):
        def agregar(self, fila):
            self.append(fila)

    repo = RepoFalso()
    m = mundo.muestra()
    RegistroHistorial(repo).actualizar(m, None, Extraida(), "", "")
    (fila,) = repo
    assert fila.estado_anterior == RegistroHistorial.SIN_ESTADO == "—"
    assert (fila.estado_nuevo, fila.motivo, fila.usuario) == ("Extraída", "", "sistema")


def test_o8_actualizador_de_orden_lee_la_muestra_no_lo_empujado(mundo):
    orden = mundo.orden([mundo.hemograma])
    m = mundo.muestra(orden)
    r = mundo.remito_cerrado([m])
    m._observadores().clear()
    r.despachar(mundo.envio())
    assert m.estado_codigo == "EnTransito" and orden.estado is EstadoOrden.EMITIDA
    ActualizadorEstadoOrden().actualizar(m, None, None, None, None)     # datos empujados sin sentido
    assert orden.estado is EstadoOrden.EN_PROCESO


def _orden_sangre_y_orina(mundo):
    orden = mundo.orden([mundo.hemograma, mundo.orina])
    sangre = mundo.muestra(orden, TipoMuestra.SANGRE)
    orina = mundo.muestra(orden, TipoMuestra.ORINA)
    return orden, sangre, orina, mundo.remito_cerrado([sangre, orina])


def _llevar(m, destino):
    """Desde En tránsito: Recibida, Analizada o Rechazada (rechazo individual con m.rechazar)."""
    if destino == "Rechazada":
        m.rechazar("Muestra hemolizada", "lab")
        return
    m.recibir("lab")
    if destino == "Analizada":
        for t in m.analisis_pendientes():
            m.registrar_resultado(ResultadoAnalisis(t, "OK"), "lab")


@pytest.mark.parametrize("sangre_a,orina_a,esperada", [
    ("Analizada", "Analizada", EstadoOrden.COMPLETADA),
    ("Analizada", "Rechazada", EstadoOrden.COMPLETADA),
    ("Analizada", "Recibida", EstadoOrden.EN_PROCESO),
    (None, None, EstadoOrden.EMITIDA),                # las dos Empaquetadas
])
def test_o9_matriz_de_actualizar_estado_de_la_orden(mundo, sangre_a, orina_a, esperada):
    orden, sangre, orina, r = _orden_sangre_y_orina(mundo)
    if sangre_a:
        r.despachar(mundo.envio())
        _llevar(sangre, sangre_a)
        _llevar(orina, orina_a)
    orden.actualizar_estado()
    assert orden.estado is esperada


def test_o9_orden_completada_no_cambia_al_recalcular(mundo):
    orden, sangre, orina, r = _orden_sangre_y_orina(mundo)
    r.despachar(mundo.envio())
    _llevar(sangre, "Analizada")
    _llevar(orina, "Analizada")
    assert orden.estado is EstadoOrden.COMPLETADA
    orden.actualizar_estado()
    assert orden.estado is EstadoOrden.COMPLETADA


def test_o9_todo_rechazado_completa_la_orden_pero_no_se_factura(mundo):
    orden, sangre, orina, r = _orden_sangre_y_orina(mundo)
    r.despachar(mundo.envio())
    _llevar(sangre, "Rechazada")
    _llevar(orina, "Rechazada")
    assert orden.estado is EstadoOrden.COMPLETADA and not orden.facturable()


def test_o10_trazabilidad_indirecta_del_remito(mundo):
    muestras = [mundo.muestra(), mundo.muestra()]
    r = mundo.remito_en_transito(muestras)
    mundo.lab.recibir_remito(r, False, 5.0, "Lucas Gomez")
    for m in muestras:
        ultimo = m.historial()[-1]
        assert (ultimo.estado_anterior, ultimo.estado_nuevo) == ("En tránsito", "Rechazada")
        assert (ultimo.usuario, ultimo.motivo) == ("Lucas Gomez", "Precinto roto")

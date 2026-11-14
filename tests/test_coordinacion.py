"""Coordinación remito ↔ muestras ↔ precinto ↔ contenedor ↔ orden, a través de los servicios."""
import pytest

from app.domain.enums import EstadoContenedor, EstadoOrden, EstadoPrecinto
from app.domain.excepciones import TransicionInvalidaError, VeterinariaError
from app.services.derivaciones import DerivacionesService
from app.services.empaquetado import EmpaquetadoService


def test_flujo_feliz_completo(sesion, base):
    orden = base.orden([base.hemograma, base.renal, base.orina])
    sangre = base.muestra(orden, "SANGRE")
    orina = base.muestra(orden, "ORINA")
    assert {sangre.estado_actual(), orina.estado_actual()} == {"Extraída"}
    r = base.remito_en_transito([sangre, orina])
    assert base.contenedor.estado is EstadoContenedor.EN_USO
    assert r.precinto.estado is EstadoPrecinto.INTEGRO and r.precinto.codigo.startswith("PRE-")
    assert {sangre.estado_actual(), orina.estado_actual()} == {"En tránsito"}
    assert orden.estado is EstadoOrden.EN_PROCESO
    rec = base.recibir(r)
    assert rec.es_aceptada() and r.estado_actual() == "Recibido"
    assert base.contenedor.estado is EstadoContenedor.DISPONIBLE
    assert {sangre.estado_actual(), orina.estado_actual()} == {"Recibida"}
    base.analizar(sangre)
    assert orden.estado is EstadoOrden.EN_PROCESO
    base.analizar(orina)
    assert orden.estado is EstadoOrden.COMPLETADA
    assert len(orden.resultados()) == 3
    assert [h.estado_nuevo for h in sangre.historial()] == [
        "Extraída", "Empaquetada", "En tránsito", "Recibida", "Analizada"]


def test_temperatura_en_recepcion_rechaza_todas(sesion, base):
    orden = base.orden([base.hemograma, base.orina])
    ms = [base.muestra(orden, "SANGRE"), base.muestra(orden, "ORINA")]
    r = base.remito_en_transito(ms)
    rec = base.recibir(r, integro=True, temp=11.5)
    assert not rec.es_aceptada()
    assert r.estado_actual() == "Recibido con observaciones"
    assert {m.estado_actual() for m in ms} == {"Rechazada"}
    assert all("Temperatura" in m.motivo_rechazo() for m in ms)
    assert orden.estado is EstadoOrden.COMPLETADA


def test_muestra_debe_coincidir_con_algun_analisis(sesion, base):
    orden = base.orden([base.hemograma])
    with pytest.raises(VeterinariaError, match="orina"):
        base.muestra(orden, "ORINA")


def test_una_muestra_por_tipo(sesion, base):
    orden = base.orden([base.hemograma])
    base.muestra(orden)
    with pytest.raises(VeterinariaError):
        base.muestra(orden)


def test_muestra_de_otro_laboratorio_o_clinica_no_se_empaqueta(sesion, base):
    from app.services.catalogos import CatalogosService
    otro_lab = CatalogosService(sesion).guardar("laboratorios", {"nombre": "Otro lab", "activo": "1"})
    emp = EmpaquetadoService(sesion)
    r = emp.crear_remito(base.centro.id, otro_lab.id, base.contenedor.id, "u")
    with pytest.raises(VeterinariaError, match="destinada"):
        emp.agregar_muestras(r.id, [base.muestra().id], "u")


def test_contenedor_reservado_por_remito_en_armado(sesion, base):
    emp = EmpaquetadoService(sesion)
    emp.crear_remito(base.centro.id, base.lab.id, base.contenedor.id, "u")
    assert base.contenedor not in emp.contenedores_disponibles(base.centro.id)
    with pytest.raises(VeterinariaError):
        emp.crear_remito(base.centro.id, base.lab.id, base.contenedor.id, "u")


def test_cerrar_con_temperatura_fuera_de_rango_impide_despachar(sesion, base):
    from datetime import timedelta
    from app.domain import reloj
    from app.services.envios import EnviosService
    emp = EmpaquetadoService(sesion)
    r = emp.crear_remito(base.centro.id, base.lab.id, base.contenedor.id, "u")
    emp.agregar_muestras(r.id, [base.muestra().id], "u")
    emp.cerrar_remito(r.id, "", 15, "u")
    with pytest.raises(TransicionInvalidaError, match="temperatura"):
        EnviosService(sesion).despachar(r.id, "Transp", reloj.ahora() + timedelta(hours=2), "u")
    assert r.estado_actual() == "Armado"


def test_anular_orden(sesion, base):
    orden = base.orden()
    base.muestra(orden)
    DerivacionesService(sesion).anular_orden(orden.id, "Error de carga")
    assert orden.estado is EstadoOrden.ANULADA
    with pytest.raises(VeterinariaError):
        base.muestra(orden, "SANGRE")


def test_no_se_anula_orden_despachada(sesion, base):
    orden = base.orden()
    base.remito_en_transito([base.muestra(orden)])
    with pytest.raises(VeterinariaError):
        DerivacionesService(sesion).anular_orden(orden.id, "x")

"""Facturación: comprobantes de atención, laboratorio y cirugía."""
from datetime import timedelta
from decimal import Decimal

import pytest

from app.domain import reloj
from app.domain.enums import EstadoFactura, FormaPago, TipoComprobante
from app.domain.excepciones import VeterinariaError
from app.services.atenciones import AtencionesService
from app.services.cirugias import CirugiasService
from app.services.facturacion import FacturacionService


def test_factura_atencion_total_igual_suma_items(sesion, base):
    a = base.atencion()
    AtencionesService(sesion).finalizar(a.id, "Gastroenteritis", importe="12500.50")
    f = FacturacionService(sesion).facturar_atencion(a.id)
    assert f.tipo is TipoComprobante.ATENCION_CLINICA
    assert f.numero.startswith("FAC-")
    assert f.total == Decimal("12500.50") == sum(i.subtotal() for i in f.items)
    assert f.titular is base.titular and f.clinica is base.centro


def test_no_se_factura_dos_veces(sesion, base):
    a = base.atencion()
    AtencionesService(sesion).finalizar(a.id, "Otitis", importe=8000)
    svc = FacturacionService(sesion)
    f = svc.facturar_atencion(a.id)
    with pytest.raises(VeterinariaError, match="Ya se facturó"):
        svc.facturar_atencion(a.id)
    svc.anular(f.id)
    f2 = svc.facturar_atencion(a.id)  # con la anterior ANULADA sí se puede
    assert f2.estado is EstadoFactura.EMITIDA


def test_atencion_no_finalizada_no_se_factura(sesion, base):
    a = base.atencion()
    with pytest.raises(VeterinariaError):
        FacturacionService(sesion).facturar_atencion(a.id)


def test_laboratorio_no_cobra_muestras_rechazadas(sesion, base):
    orden = base.orden([base.hemograma, base.renal, base.orina])
    sangre = base.muestra(orden, "SANGRE")
    orina = base.muestra(orden, "ORINA")
    r1 = base.remito_en_transito([sangre])
    base.recibir(r1)
    base.analizar(sangre)
    r2 = base.remito_en_transito([orina], contenedor=base.contenedor2)
    base.recibir(r2, integro=False)
    f = FacturacionService(sesion).facturar_orden(orden.id)
    assert f.tipo is TipoComprobante.SERVICIO_LABORATORIO
    assert {i.tipo_analisis.codigo for i in f.items} == {"HEM", "REN"}  # sin Urianálisis
    assert f.total == Decimal("17500.00")


def test_orden_toda_rechazada_no_tiene_nada_para_facturar(sesion, base):
    orden = base.orden([base.hemograma])
    r = base.remito_en_transito([base.muestra(orden)])
    base.recibir(r, integro=False)
    with pytest.raises(VeterinariaError, match="nada para facturar"):
        FacturacionService(sesion).facturar_orden(orden.id)
    assert orden not in FacturacionService(sesion).pendientes(base.centro.id).ordenes


def test_factura_cirugia_y_pago(sesion, base):
    cir = CirugiasService(sesion)
    d = cir.derivar(base.atencion().id, base.sur.id, "Cesárea")
    cir.aceptar(d.id, base.cirujano.id)
    cir.registrar_consentimiento(d.id, "u")
    cir.programar(d.id, reloj.ahora() + timedelta(days=1))
    with pytest.raises(VeterinariaError):
        FacturacionService(sesion).facturar_cirugia(d.id, 90000)
    cir.registrar_cirugia(d.id, "OK")
    svc = FacturacionService(sesion)
    with pytest.raises(VeterinariaError):
        svc.facturar_cirugia(d.id, 0)
    f = svc.facturar_cirugia(d.id, "90000")
    assert f.clinica is base.sur and f.total == Decimal("90000.00")
    svc.registrar_pago(f.id, FormaPago.TARJETA)
    assert f.estado is EstadoFactura.PAGADA
    with pytest.raises(VeterinariaError):
        svc.anular(f.id)


def test_pendientes_de_facturar(sesion, base):
    a = base.atencion()
    AtencionesService(sesion).finalizar(a.id, "Control", importe=5000)
    p = FacturacionService(sesion).pendientes(base.centro.id)
    assert a in p.atenciones
    FacturacionService(sesion).facturar_atencion(a.id)
    assert a not in FacturacionService(sesion).pendientes(base.centro.id).atenciones

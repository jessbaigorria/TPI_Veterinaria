"""Portal Clínica › Facturación: pendiente de facturar, comprobantes, pago y anulación."""
from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy.orm import Session

from app.domain.excepciones import VeterinariaError
from app.services.facturacion import FacturacionService
from app.web.formato import moneda
from app.web.plantillas import render
from app.web.routers._comun import Db, UsrClinica, destino_interno, formulario, ir
from app.web.sesion import UsuarioSesion, avisar

router = APIRouter(prefix="/clinica")


@router.get("/facturacion")
def facturacion(request: Request, estado: str = "", tipo: str = "", u: UsuarioSesion = UsrClinica,
                s: Session = Db):
    svc = FacturacionService(s)
    return render(request, "clinica/facturacion.html", seccion="facturacion", pendientes=svc.pendientes(u.clinica_id),
                  facturas=svc.listar(u.clinica_id, estado, tipo))


@router.post("/facturacion/{origen}/{origen_id}")
async def facturar(request: Request, origen: str, origen_id: int, u: UsuarioSesion = UsrClinica, s: Session = Db):
    """``origen``: «atencion», «orden» o «cirugia» (la cirugía pide el importe)."""
    f = await formulario(request)
    svc = FacturacionService(s)
    if origen == "atencion":
        factura = svc.facturar_atencion(origen_id)
    elif origen == "orden":
        factura = svc.facturar_orden(origen_id)
    elif origen == "cirugia":
        factura = svc.facturar_cirugia(origen_id, f.get("importe"))
    else:
        raise VeterinariaError("Origen de factura desconocido.")
    avisar(request, f"Comprobante {factura.numero} emitido por {moneda(factura.total)}.")
    return ir(_volver(f, f"/clinica/facturacion/{factura.id}"))


@router.get("/facturacion/{factura_id}")
def factura_detalle(request: Request, factura_id: int, u: UsuarioSesion = UsrClinica, s: Session = Db):
    return render(request, "clinica/factura_detalle.html", seccion="facturacion",
                  f=FacturacionService(s).obtener_factura(factura_id))


@router.post("/facturas/{factura_id}/pagar")
async def factura_pagar(request: Request, factura_id: int, u: UsuarioSesion = UsrClinica, s: Session = Db):
    f = await formulario(request)
    fac = FacturacionService(s).registrar_pago(factura_id, f.get("forma_pago") or None)
    avisar(request, f"Pago del comprobante {fac.numero} registrado.")
    return ir(_volver(f, f"/clinica/facturacion/{factura_id}"))


@router.post("/facturas/{factura_id}/anular")
async def factura_anular(request: Request, factura_id: int, u: UsuarioSesion = UsrClinica, s: Session = Db):
    f = await formulario(request)
    fac = FacturacionService(s).anular(factura_id)
    avisar(request, f"Comprobante {fac.numero} anulado.")
    return ir(_volver(f, f"/clinica/facturacion/{factura_id}"))


def _volver(f: dict, defecto: str) -> str:
    """Después de facturar, pagar o anular se vuelve a la pantalla de origen (campo «volver»)."""
    return destino_interno(f.get("volver"), defecto, "/clinica/")

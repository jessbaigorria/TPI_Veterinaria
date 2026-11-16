"""Portal Clínica › Órdenes de laboratorio: emitir, registrar la muestra extraída y anular."""
from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy.orm import Session

from app.services.atenciones import AtencionesService
from app.services.derivaciones import DerivacionesService
from app.web.plantillas import render
from app.web.routers._comun import Db, UsrClinica, formulario, ir
from app.web.sesion import UsuarioSesion, avisar

router = APIRouter(prefix="/clinica")


@router.get("/ordenes")
def ordenes(request: Request, estado: str = "", q: str = "", u: UsuarioSesion = UsrClinica, s: Session = Db):
    return render(request, "clinica/ordenes.html", seccion="ordenes",
                  ordenes=DerivacionesService(s).listar_ordenes(u.clinica_id, estado, q))


@router.get("/ordenes/nueva")
def orden_nueva(request: Request, atencion: int, u: UsuarioSesion = UsrClinica, s: Session = Db):
    svc = DerivacionesService(s)
    a = AtencionesService(s).obtener_atencion(atencion)
    a.validar_admite_derivaciones("emitir una orden de laboratorio")
    return render(request, "clinica/orden_nueva.html", seccion="ordenes", a=a, laboratorios=svc.laboratorios(),
                  tipos=svc.tipos_analisis())


@router.post("/ordenes")
async def orden_crear(request: Request, u: UsuarioSesion = UsrClinica, s: Session = Db):
    form = await request.form()
    o = DerivacionesService(s).emitir_orden(form.get("atencion_id"), form.get("laboratorio_id"),
                                            form.getlist("analisis_id"), form.get("prioridad") or "NORMAL",
                                            form.get("observaciones", ""))
    avisar(request, f"Orden {o.numero} emitida. Registrá ahora la muestra extraída.")
    return ir(f"/clinica/ordenes/{o.id}")


@router.get("/ordenes/{orden_id}")
def orden_detalle(request: Request, orden_id: int, u: UsuarioSesion = UsrClinica, s: Session = Db):
    o = DerivacionesService(s).obtener_orden(orden_id)
    tipos_muestra = sorted({t.tipo_muestra_requerida for t in o.analisis}, key=lambda x: x.value)
    return render(request, "clinica/orden_detalle.html", seccion="ordenes", o=o, tipos_muestra=tipos_muestra)


@router.post("/ordenes/{orden_id}/muestras")
async def orden_muestra(request: Request, orden_id: int, u: UsuarioSesion = UsrClinica, s: Session = Db):
    f = await formulario(request)
    m = DerivacionesService(s).registrar_muestra(orden_id, f.get("tipo"), f.get("volumen"),
                                                 observaciones=f.get("observaciones", ""))
    avisar(request, f"Muestra {m.codigo} registrada: {m.estado_actual()}.")
    return ir(f"/clinica/ordenes/{orden_id}")


@router.post("/ordenes/{orden_id}/anular")
async def orden_anular(request: Request, orden_id: int, u: UsuarioSesion = UsrClinica, s: Session = Db):
    f = await formulario(request)
    DerivacionesService(s).anular_orden(orden_id, f.get("motivo", ""))
    avisar(request, "Orden anulada.")
    return ir(f"/clinica/ordenes/{orden_id}")


@router.get("/muestras/{muestra_id}")
def muestra_detalle(request: Request, muestra_id: int, u: UsuarioSesion = UsrClinica, s: Session = Db):
    return render(request, "componentes/muestra_detalle.html", seccion="ordenes", base="base.html",
                  m=DerivacionesService(s).obtener_muestra(muestra_id))

"""Portal Clínica › Clientes: ABM de titulares (con baja lógica)."""
from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy.orm import Session

from app.services.clientes import ClientesService
from app.web.plantillas import render
from app.web.routers._comun import Db, UsrClinica, formulario, ir
from app.web.sesion import UsuarioSesion, avisar

router = APIRouter(prefix="/clinica")

CAMPOS_TITULAR = ("dni", "nombre", "apellido", "direccion", "telefono", "email")


@router.get("/clientes")
def clientes(request: Request, q: str = "", u: UsuarioSesion = UsrClinica, s: Session = Db):
    return render(request, "clinica/clientes.html", seccion="clientes", titulares=ClientesService(s).buscar(q))


@router.get("/clientes/nuevo")
def cliente_nuevo(request: Request, u: UsuarioSesion = UsrClinica):
    return render(request, "clinica/cliente_form.html", seccion="clientes", t=None)


@router.post("/clientes")
async def cliente_crear(request: Request, u: UsuarioSesion = UsrClinica, s: Session = Db):
    f = await formulario(request)
    t = ClientesService(s).crear_titular(f.get("dni"), f.get("nombre"), f.get("apellido"), f.get("direccion", ""),
                                         f.get("telefono", ""), f.get("email", ""))
    avisar(request, f"Titular {t.nombre_completo()} creado.")
    destino = f.get("next") or ""
    if destino.startswith("/clinica/"):   # volver al formulario de origen con el titular elegido
        return ir(f"{destino}{'&' if '?' in destino else '?'}titular={t.id}")
    return ir(f"/clinica/clientes/{t.id}")


@router.get("/clientes/{titular_id}")
def cliente_detalle(request: Request, titular_id: int, u: UsuarioSesion = UsrClinica, s: Session = Db):
    return render(request, "clinica/cliente_detalle.html", seccion="clientes",
                  t=ClientesService(s).obtener_titular(titular_id))


@router.get("/clientes/{titular_id}/editar")
def cliente_editar(request: Request, titular_id: int, u: UsuarioSesion = UsrClinica, s: Session = Db):
    return render(request, "clinica/cliente_form.html", seccion="clientes",
                  t=ClientesService(s).obtener_titular(titular_id))


@router.post("/clientes/{titular_id}")
async def cliente_actualizar(request: Request, titular_id: int, u: UsuarioSesion = UsrClinica, s: Session = Db):
    f = await formulario(request)
    ClientesService(s).actualizar_titular(titular_id, **{campo: f.get(campo, "") for campo in CAMPOS_TITULAR})
    avisar(request, "Datos del titular actualizados.")
    return ir(f"/clinica/clientes/{titular_id}")


@router.post("/clientes/{titular_id}/{accion}")
def cliente_estado(request: Request, titular_id: int, accion: str, u: UsuarioSesion = UsrClinica,
                   s: Session = Db):
    """``accion``: «baja» (baja lógica) o «reactivar»."""
    svc = ClientesService(s)
    {"baja": svc.dar_de_baja, "reactivar": svc.reactivar}[accion](titular_id)
    avisar(request, "Titular dado de baja (baja lógica)." if accion == "baja" else "Titular reactivado.")
    return ir(f"/clinica/clientes/{titular_id}")

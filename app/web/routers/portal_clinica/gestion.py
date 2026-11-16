"""Portal Clínica › Gestión: clínicas, profesionales, laboratorios, tipos de análisis, vacunas y contenedores."""
from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy.orm import Session

from app.services.catalogos import CATALOGOS, CatalogosService
from app.web.plantillas import render
from app.web.routers._comun import Db, UsrClinica, formulario, ir
from app.web.sesion import UsuarioSesion, avisar

router = APIRouter(prefix="/clinica")


@router.get("/catalogos")
def catalogos_ruta_anterior(request: Request, u: UsuarioSesion = UsrClinica):
    """La sección se llamaba «Catálogos»: la ruta vieja redirige a «Gestión»."""
    return ir("/clinica/gestion" + (f"?{request.url.query}" if request.url.query else ""))


@router.get("/gestion")
def catalogos(request: Request, tab: str = "clinicas", u: UsuarioSesion = UsrClinica, s: Session = Db):
    svc = CatalogosService(s)
    return render(request, "clinica/catalogos.html", seccion="gestion", tab=tab, catalogos=CATALOGOS,
                  cat=svc.catalogo(tab), items=svc.listar(tab))


@router.get("/gestion/{clave}/nuevo")
def catalogo_nuevo(request: Request, clave: str, u: UsuarioSesion = UsrClinica, s: Session = Db):
    svc = CatalogosService(s)
    return render(request, "clinica/catalogo_form.html", seccion="gestion", cat=svc.catalogo(clave), obj=None,
                  clinicas=svc.clinicas())


@router.get("/gestion/{clave}/{obj_id}/editar")
def catalogo_editar(request: Request, clave: str, obj_id: int, u: UsuarioSesion = UsrClinica, s: Session = Db):
    svc = CatalogosService(s)
    cat = svc.catalogo(clave)
    return render(request, "clinica/catalogo_form.html", seccion="gestion", cat=cat,
                  obj=svc.obtener(cat.modelo, obj_id), clinicas=svc.clinicas())


@router.post("/gestion/contenedores/{obj_id}/estado/{accion}")
def contenedor_estado(request: Request, obj_id: int, accion: str, u: UsuarioSesion = UsrClinica, s: Session = Db):
    c = CatalogosService(s).cambiar_estado_contenedor(obj_id, accion)
    avisar(request, f"Contenedor {c.codigo}: {c.estado.etiqueta.lower()}.")
    return ir("/clinica/gestion?tab=contenedores")


@router.post("/gestion/{clave}")
async def catalogo_crear(request: Request, clave: str, u: UsuarioSesion = UsrClinica, s: Session = Db):
    CatalogosService(s).guardar(clave, await formulario(request))
    avisar(request, "Registro creado.")
    return ir(f"/clinica/gestion?tab={clave}")


@router.post("/gestion/{clave}/{obj_id}")
async def catalogo_actualizar(request: Request, clave: str, obj_id: int, u: UsuarioSesion = UsrClinica,
                              s: Session = Db):
    CatalogosService(s).guardar(clave, await formulario(request), obj_id)
    avisar(request, "Registro actualizado.")
    return ir(f"/clinica/gestion?tab={clave}")

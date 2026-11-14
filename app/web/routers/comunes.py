"""Rutas comunes: ingreso (elegir portal + sede + usuario), salida y API auxiliar para formularios."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db import obtener_sesion
from app.domain.atencion import Clinica
from app.domain.excepciones import VeterinariaError
from app.domain.laboratorio import Laboratorio
from app.services.catalogos import CatalogosService
from app.services.clientes import ClientesService
from app.web.plantillas import render
from app.web.sesion import (
    PORTAL_CLINICA, PORTAL_LABORATORIO, UsuarioSesion, avisar, cerrar, iniciar, usuario_actual,
)

router = APIRouter()


@router.get("/")
def ingreso(request: Request, s: Session = Depends(obtener_sesion)):
    cat = CatalogosService(s)
    clinicas = [c for c in cat.clinicas() if c.activa]
    usuarios = {c.id: ["Recepción"] + [f"{p.nombre} {p.apellido}" for p in c.profesionales] for c in clinicas}
    return render(request, "login.html", clinicas=clinicas, laboratorios=[l for l in cat.laboratorios() if l.activo],
                  usuarios=usuarios, actual=usuario_actual(request))


@router.post("/ingresar")
async def ingresar(request: Request, s: Session = Depends(obtener_sesion)):
    form = await request.form()
    portal = form.get("portal")
    usuario = (form.get("usuario") or "").strip()
    if not usuario:
        raise VeterinariaError("Elegí o escribí el nombre de usuario.")
    if portal == PORTAL_CLINICA:
        sede = CatalogosService(s).obtener(Clinica, form.get("clinica_id"))
        iniciar(request, UsuarioSesion(PORTAL_CLINICA, sede.id, sede.nombre, usuario, sede.alta_complejidad))
        avisar(request, f"Bienvenido/a, {usuario}.")
        return RedirectResponse("/clinica", status_code=303)
    if portal == PORTAL_LABORATORIO:
        sede = CatalogosService(s).obtener(Laboratorio, form.get("laboratorio_id"))
        iniciar(request, UsuarioSesion(PORTAL_LABORATORIO, sede.id, sede.nombre, usuario))
        avisar(request, f"Bienvenido/a, {usuario}.")
        return RedirectResponse("/laboratorio", status_code=303)
    raise VeterinariaError("Elegí un portal.")


@router.get("/salir")
def salir(request: Request):
    cerrar(request)
    return RedirectResponse("/", status_code=303)


@router.get("/api/titulares/{titular_id}/mascotas")
def api_mascotas(titular_id: int, s: Session = Depends(obtener_sesion)):
    t = ClientesService(s).obtener_titular(titular_id)
    return JSONResponse([{"id": m.id, "nombre": m.nombre, "especie": m.especie.etiqueta,
                          "pendientes": [v.nombre for v in m.historia_clinica.vacunas_pendientes()]}
                         for m in t.mascotas_activas()])

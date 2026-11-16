"""Portal Clínica › Cirugías: derivaciones enviadas y, en las clínicas de alta complejidad, recibidas."""
from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy.orm import Session

from app.domain import reloj
from app.domain.excepciones import VeterinariaError
from app.services.atenciones import AtencionesService
from app.services.cirugias import CirugiasService
from app.web.plantillas import render
from app.web.routers._comun import Db, UsrClinica, formulario, ir
from app.web.sesion import UsuarioSesion, avisar

router = APIRouter(prefix="/clinica")


@router.get("/cirugias")
def cirugias(request: Request, tab: str = "enviadas", u: UsuarioSesion = UsrClinica, s: Session = Db):
    svc = CirugiasService(s)
    return render(request, "clinica/cirugias.html", seccion="cirugias", tab=tab,
                  enviadas=svc.enviadas(u.clinica_id), recibidas=svc.recibidas(u.clinica_id))


@router.get("/cirugias/nueva")
def cirugia_nueva(request: Request, atencion: int, u: UsuarioSesion = UsrClinica, s: Session = Db):
    a = AtencionesService(s).obtener_atencion(atencion)
    a.validar_admite_derivaciones("derivar a cirugía")
    return render(request, "clinica/cirugia_nueva.html", seccion="cirugias", a=a,
                  clinicas=CirugiasService(s).todas_las_clinicas())


@router.post("/cirugias")
async def cirugia_crear(request: Request, u: UsuarioSesion = UsrClinica, s: Session = Db):
    f = await formulario(request)
    d = CirugiasService(s).derivar(f.get("atencion_id"), f.get("destino_id"), f.get("tipo_cirugia", ""),
                                   f.get("prioridad") or "NORMAL", f.get("diagnostico_presuntivo", ""),
                                   f.get("riesgo_anestesico") or "ASA_I", f.get("estudios_prequirurgicos", ""))
    avisar(request, f"Derivación {d.numero} enviada a {d.destino.nombre}.")
    return ir(f"/clinica/cirugias/{d.id}")


@router.get("/cirugias/{derivacion_id}")
def cirugia_detalle(request: Request, derivacion_id: int, u: UsuarioSesion = UsrClinica, s: Session = Db):
    d = CirugiasService(s).obtener_derivacion(derivacion_id)
    return render(request, "clinica/cirugia_detalle.html", seccion="cirugias", d=d,
                  es_destino=d.destino_id == u.clinica_id, es_origen=d.clinica_origen.id == u.clinica_id,
                  cirujanos=d.destino.profesionales, ahora=reloj.ahora())


@router.post("/cirugias/{derivacion_id}/{accion}")
async def cirugia_accion(request: Request, derivacion_id: int, accion: str, u: UsuarioSesion = UsrClinica,
                         s: Session = Db):
    """Un botón por transición de la derivación: aceptar, rechazar, consentimiento, estudios, programar,
    realizar o cancelar."""
    f = await formulario(request)
    svc = CirugiasService(s)
    acciones = {
        "aceptar": lambda: svc.aceptar(derivacion_id, f.get("cirujano_id")),
        "rechazar": lambda: svc.rechazar(derivacion_id, f.get("motivo", "")),
        "consentimiento": lambda: svc.registrar_consentimiento(derivacion_id, u.usuario),
        "estudios": lambda: svc.registrar_estudios(derivacion_id, f.get("estudios", "")),
        "programar": lambda: svc.programar(derivacion_id, f.get("fecha")),
        "realizar": lambda: svc.registrar_cirugia(derivacion_id, f.get("informe", "")),
        "cancelar": lambda: svc.cancelar(derivacion_id, f.get("motivo", "")),
    }
    if accion not in acciones:
        raise VeterinariaError("Acción desconocida.")
    d = acciones[accion]()
    avisar(request, f"Derivación {d.numero}: {d.estado.etiqueta.lower()}.")
    return ir(f"/clinica/cirugias/{derivacion_id}")

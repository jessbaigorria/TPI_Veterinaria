"""Portal Clínica › Atenciones: listado, registrar atención sin turno (3 casos), detalle y finalizar."""
from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy.orm import Session

from app.domain import reloj
from app.services.atenciones import AtencionesService
from app.services.base import a_fecha
from app.services.clientes import ClientesService
from app.services.mascotas import MascotasService
from app.web.plantillas import render
from app.web.routers._comun import Db, UsrClinica, datos_mascota_nueva, formulario, ir
from app.web.sesion import UsuarioSesion, avisar

router = APIRouter(prefix="/clinica")


@router.get("/atenciones")
def atenciones(request: Request, u: UsuarioSesion = UsrClinica, s: Session = Db):
    q = request.query_params
    lista = AtencionesService(s).listar(u.clinica_id, q.get("estado", ""), q.get("tipo", ""),
                                        a_fecha(q.get("desde")), a_fecha(q.get("hasta")), q.get("q", ""))
    return render(request, "clinica/atenciones.html", seccion="atenciones", atenciones=lista)


@router.get("/atenciones/nueva")
def atencion_nueva(request: Request, u: UsuarioSesion = UsrClinica, s: Session = Db):
    return render(request, "clinica/atencion_nueva.html", seccion="atenciones",
                  titulares=ClientesService(s).buscar(solo_activos=True),
                  profesionales=AtencionesService(s).profesionales(u.clinica_id), ahora=reloj.ahora())


@router.post("/atenciones/registrar")
async def atencion_registrar(request: Request, u: UsuarioSesion = UsrClinica, s: Session = Db):
    f = await formulario(request)
    r = AtencionesService(s).registrar_sin_turno(
        f.get("profesional_id"), u.clinica_id, f.get("tipo") or "CONSULTA", mascota_id=f.get("mascota_id"),
        nueva_mascota=datos_mascota_nueva(f), motivo=f.get("motivo", ""),
        asiste_titular=f.get("asiste_titular", "1"), responsable_presente=f.get("responsable_presente", ""),
        inicio=f.get("inicio") or None, duracion_minutos=f.get("duracion") or 30)
    avisar(request, f"Atención registrada e iniciada para {r.atencion.mascota.nombre}.")
    if r.advertencia:
        avisar(request, r.advertencia + " Quedó constancia en las observaciones.", "warning")
    return ir(f"/clinica/atenciones/{r.atencion.id}")


@router.get("/atenciones/{atencion_id}")
def atencion_detalle(request: Request, atencion_id: int, u: UsuarioSesion = UsrClinica, s: Session = Db):
    a = AtencionesService(s).obtener_atencion(atencion_id)
    return render(request, "clinica/atencion_detalle.html", seccion="atenciones", a=a,
                  pendientes=a.historia.detalle_vacunas_pendientes(),
                  vacunas=MascotasService(s).vacunas_para(a.mascota))


@router.post("/atenciones/{atencion_id}/finalizar")
async def atencion_finalizar(request: Request, atencion_id: int, u: UsuarioSesion = UsrClinica, s: Session = Db):
    form = await request.form()
    vacunas = _vacunas_aplicadas(form)
    AtencionesService(s).finalizar(atencion_id, form.get("diagnostico", ""), form.get("peso"), form.get("importe"),
                                   form.get("observaciones"), vacunas)
    avisar(request, "Atención finalizada." + (f" Se registraron {len(vacunas)} vacuna(s)." if vacunas else ""))
    return ir(f"/clinica/atenciones/{atencion_id}")


# --- auxiliares ----------------------------------------------------------------------------
def _vacunas_aplicadas(form) -> list[dict]:
    """Vacunas tildadas al finalizar una atención de VACUNACIÓN, con su lote y número de dosis."""
    return [{"vacuna_id": vid, "lote": form.get(f"lote_{vid}", ""), "dosis_numero": form.get(f"dosis_{vid}") or 1}
            for vid in form.getlist("vacuna_id")]

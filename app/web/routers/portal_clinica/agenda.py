"""Portal Clínica › Agenda: grilla del día por profesional, reservar, iniciar y cancelar turnos."""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Request
from sqlalchemy.orm import Session

from app.domain import reloj
from app.services.atenciones import AtencionesService
from app.services.base import a_fecha
from app.services.clientes import ClientesService
from app.services.mascotas import MascotasService
from app.web.plantillas import render
from app.web.routers._comun import Db, UsrClinica, formulario, ir
from app.web.sesion import UsuarioSesion, avisar

router = APIRouter(prefix="/clinica")


@router.get("/agenda")
def agenda(request: Request, fecha: str = "", u: UsuarioSesion = UsrClinica, s: Session = Db):
    dia = a_fecha(fecha) or reloj.hoy()
    svc = AtencionesService(s)
    turnos = svc.agenda(u.clinica_id, dia)
    franjas = svc.franjas_agenda(dia)
    return render(request, "clinica/agenda.html", seccion="agenda", dia=dia,
                  profesionales=svc.profesionales(u.clinica_id), turnos=turnos, franjas=franjas,
                  grilla=svc.grilla_agenda(turnos, franjas),
                  anterior=dia - timedelta(days=1), siguiente=dia + timedelta(days=1))


@router.get("/agenda/nuevo")
def turno_nuevo(request: Request, u: UsuarioSesion = UsrClinica, s: Session = Db):
    mascota_id = request.query_params.get("mascota")
    return render(request, "clinica/turno_nuevo.html", seccion="agenda",
                  titulares=ClientesService(s).buscar(solo_activos=True),
                  profesionales=AtencionesService(s).profesionales(u.clinica_id),
                  mascota=MascotasService(s).obtener_mascota(mascota_id) if mascota_id else None)


@router.post("/agenda/reservar")
async def reservar(request: Request, u: UsuarioSesion = UsrClinica, s: Session = Db):
    f = await formulario(request)
    a = AtencionesService(s).reservar_turno(
        f.get("mascota_id"), f.get("profesional_id"), u.clinica_id,
        _fecha_y_hora(f, "hora_inicio"), _fecha_y_hora(f, "hora_fin"), f.get("tipo") or "CONSULTA",
        f.get("motivo", ""), f.get("asiste_titular", "1"), f.get("responsable_presente", ""))
    avisar(request, f"Turno reservado: {a.mascota.nombre} con {a.profesional.nombre_completo()} el "
                    f"{a.fecha_hora_inicio:%d/%m/%Y %H:%M}.")
    _avisar_vacunas_pendientes(request, a)
    return ir(f"/clinica/agenda?fecha={a.fecha_hora_inicio.date()}")


@router.post("/atenciones/{atencion_id}/iniciar")
def iniciar_atencion(request: Request, atencion_id: int, u: UsuarioSesion = UsrClinica, s: Session = Db):
    r = AtencionesService(s).iniciar(atencion_id)
    avisar(request, "Atención iniciada.")
    if r.advertencia:
        avisar(request, r.advertencia + " Quedó constancia en las observaciones.", "warning")
    return ir(f"/clinica/atenciones/{atencion_id}")


@router.post("/atenciones/{atencion_id}/cancelar")
async def cancelar_atencion(request: Request, atencion_id: int, u: UsuarioSesion = UsrClinica, s: Session = Db):
    f = await formulario(request)
    a = AtencionesService(s).cancelar(atencion_id, f.get("motivo", ""))
    avisar(request, "Turno cancelado.")
    return ir(f"/clinica/agenda?fecha={a.fecha_hora_inicio.date()}")


# --- auxiliares ----------------------------------------------------------------------------
def _fecha_y_hora(f: dict, campo_hora: str) -> str | None:
    """Une el campo «fecha» con una hora del formulario (formato ISO), o None si falta alguno."""
    if f.get("fecha") and f.get(campo_hora):
        return f"{f.get('fecha')}T{f.get(campo_hora)}"
    return None


def _avisar_vacunas_pendientes(request: Request, atencion) -> None:
    """Si el turno es de un tipo que se bloquea por vacunas, avisa desde ya cuáles faltan."""
    if not atencion.bloqueara_por_vacunas():
        return
    pendientes = atencion.historia.vacunas_pendientes(atencion.fecha_hora_inicio.date())
    if pendientes:
        avisar(request, f"Atención: {atencion.mascota.nombre} tiene vacunas pendientes ("
                        + ", ".join(v.nombre for v in pendientes)
                        + "). Al iniciar la atención se bloqueará si no se vacuna antes.", "warning")

"""Portal Clínica › Mascotas: ABM (siempre con titular) e historia clínica."""
from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy.orm import Session

from app.services.clientes import ClientesService
from app.services.mascotas import MascotasService
from app.web.plantillas import render
from app.web.routers._comun import Db, UsrClinica, formulario, ir
from app.web.sesion import UsuarioSesion, avisar

router = APIRouter(prefix="/clinica")

CAMPOS_MASCOTA = ("nombre", "especie", "sexo", "fecha_nacimiento", "raza", "peso")


@router.get("/mascotas")
def mascotas(request: Request, q: str = "", especie: str = "", u: UsuarioSesion = UsrClinica, s: Session = Db):
    return render(request, "clinica/mascotas.html", seccion="mascotas",
                  mascotas=MascotasService(s).buscar(q, especie))


@router.get("/mascotas/nueva")
def mascota_nueva(request: Request, u: UsuarioSesion = UsrClinica, s: Session = Db):
    return render(request, "clinica/mascota_form.html", seccion="mascotas", m=None,
                  titulares=ClientesService(s).buscar(solo_activos=True))


@router.post("/mascotas")
async def mascota_crear(request: Request, u: UsuarioSesion = UsrClinica, s: Session = Db):
    f = await formulario(request)
    m = MascotasService(s).crear_mascota(f.get("titular_id") or None, f.get("nombre"), f.get("especie"),
                                         f.get("sexo"), f.get("fecha_nacimiento"), f.get("raza", ""), f.get("peso"),
                                         f.get("alergias", ""), f.get("antecedentes", ""))
    avisar(request, f"{m.nombre} registrada con historia clínica {m.historia_clinica.numero}.")
    return ir(f"/clinica/mascotas/{m.id}")


@router.get("/mascotas/{mascota_id}")
def mascota_detalle(request: Request, mascota_id: int, u: UsuarioSesion = UsrClinica, s: Session = Db):
    svc = MascotasService(s)
    m = svc.obtener_mascota(mascota_id)
    return render(request, "clinica/mascota_detalle.html", seccion="mascotas", m=m, hc=m.historia_clinica,
                  pendientes=m.historia_clinica.detalle_vacunas_pendientes(), vacunas=svc.vacunas_para(m),
                  titulares=ClientesService(s).buscar(solo_activos=True),
                  tab=request.query_params.get("tab", "resumen"))


@router.get("/mascotas/{mascota_id}/editar")
def mascota_editar(request: Request, mascota_id: int, u: UsuarioSesion = UsrClinica, s: Session = Db):
    return render(request, "clinica/mascota_form.html", seccion="mascotas",
                  m=MascotasService(s).obtener_mascota(mascota_id), titulares=[])


@router.post("/mascotas/{mascota_id}")
async def mascota_actualizar(request: Request, mascota_id: int, u: UsuarioSesion = UsrClinica, s: Session = Db):
    f = await formulario(request)
    MascotasService(s).actualizar_mascota(mascota_id, **{campo: f.get(campo) for campo in CAMPOS_MASCOTA})
    avisar(request, "Datos de la mascota actualizados.")
    return ir(f"/clinica/mascotas/{mascota_id}")


@router.post("/mascotas/{mascota_id}/historia")
async def mascota_historia(request: Request, mascota_id: int, u: UsuarioSesion = UsrClinica, s: Session = Db):
    f = await formulario(request)
    MascotasService(s).actualizar_historia(mascota_id, f.get("alergias", ""), f.get("antecedentes", ""),
                                           f.get("observaciones_generales", ""))
    avisar(request, "Historia clínica actualizada.")
    return ir(f"/clinica/mascotas/{mascota_id}")


@router.post("/mascotas/{mascota_id}/vacunas")
async def mascota_vacuna(request: Request, mascota_id: int, u: UsuarioSesion = UsrClinica, s: Session = Db):
    f = await formulario(request)
    MascotasService(s).registrar_vacuna_aplicada(mascota_id, f.get("vacuna_id"), f.get("fecha_aplicacion"),
                                                 f.get("lote", ""), f.get("dosis_numero") or 1)
    avisar(request, "Vacuna registrada en la historia clínica.")
    return ir(f"/clinica/mascotas/{mascota_id}?tab=vacunas")


@router.post("/mascotas/{mascota_id}/titular")
async def mascota_titular(request: Request, mascota_id: int, u: UsuarioSesion = UsrClinica, s: Session = Db):
    f = await formulario(request)
    m = MascotasService(s).cambiar_titular(mascota_id, f.get("titular_id") or None)
    avisar(request, f"Nuevo titular: {m.titular.nombre_completo()}.")
    return ir(f"/clinica/mascotas/{mascota_id}")


@router.post("/mascotas/{mascota_id}/{accion}")
def mascota_estado(request: Request, mascota_id: int, accion: str, u: UsuarioSesion = UsrClinica,
                   s: Session = Db):
    """``accion``: «baja» (baja lógica) o «reactivar»."""
    svc = MascotasService(s)
    {"baja": svc.dar_de_baja, "reactivar": svc.reactivar}[accion](mascota_id)
    avisar(request, "Mascota dada de baja (baja lógica)." if accion == "baja" else "Mascota reactivada.")
    return ir(f"/clinica/mascotas/{mascota_id}")

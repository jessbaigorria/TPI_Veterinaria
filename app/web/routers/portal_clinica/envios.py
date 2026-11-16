"""Portal Clínica › Envíos: armar el remito (laboratorio + contenedor → muestras → precinto),
despachar y confirmar el retiro."""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Request
from sqlalchemy.orm import Session

from app.domain import reloj
from app.domain.estados.estado_remito import EstadoRemito
from app.services.derivaciones import DerivacionesService
from app.services.empaquetado import EmpaquetadoService
from app.services.envios import EnviosService
from app.web.plantillas import render
from app.web.routers._comun import Db, UsrClinica, formulario, ir
from app.web.sesion import UsuarioSesion, avisar

router = APIRouter(prefix="/clinica")

# El filtro "en camino" agrupa Despachado + En tránsito (es un filtro de listado, no una transición).
FILTROS_REMITO = {"RemitoEnTransito": ["RemitoDespachado", "RemitoEnTransito"]}


@router.get("/envios")
def envios(request: Request, estado: str = "", q: str = "", u: UsuarioSesion = UsrClinica, s: Session = Db):
    estados = FILTROS_REMITO.get(estado, [estado] if estado else None)
    return render(request, "clinica/envios.html", seccion="envios", estados_remito=EstadoRemito.todos(),
                  remitos=EmpaquetadoService(s).listar_remitos(clinica_id=u.clinica_id, estados=estados, q=q))


@router.get("/envios/nuevo")
def remito_nuevo(request: Request, u: UsuarioSesion = UsrClinica, s: Session = Db):
    emp = EmpaquetadoService(s)
    return render(request, "clinica/remito_nuevo.html", seccion="envios",
                  laboratorios=DerivacionesService(s).laboratorios(),
                  contenedores=emp.contenedores_disponibles(u.clinica_id),
                  muestras=emp.muestras_para_empaquetar(u.clinica_id))


@router.post("/envios")
async def remito_crear(request: Request, u: UsuarioSesion = UsrClinica, s: Session = Db):
    f = await formulario(request)
    r = EmpaquetadoService(s).crear_remito(u.clinica_id, f.get("laboratorio_id"), f.get("contenedor_id"), u.usuario,
                                           f.get("observaciones", ""))
    avisar(request, f"Remito {r.numero} creado. Paso 2: tildá las muestras a empaquetar.")
    return ir(f"/clinica/envios/{r.id}")


@router.get("/envios/{remito_id}")
def remito_detalle(request: Request, remito_id: int, u: UsuarioSesion = UsrClinica, s: Session = Db):
    emp = EmpaquetadoService(s)
    r = emp.obtener_remito(remito_id)
    return render(request, "clinica/remito_detalle.html", seccion="envios", r=r,
                  candidatas=emp.muestras_para_empaquetar(r.clinica_origen_id, r.laboratorio_id),
                  proximo_precinto=emp.proximo_precinto(), llegada_sugerida=reloj.ahora() + timedelta(hours=4))


@router.post("/envios/{remito_id}/muestras")
async def remito_muestras(request: Request, remito_id: int, u: UsuarioSesion = UsrClinica, s: Session = Db):
    form = await request.form()
    ids = form.getlist("muestra_id")
    EmpaquetadoService(s).agregar_muestras(remito_id, ids, u.usuario)
    avisar(request, f"{len(ids)} muestra(s) empaquetada(s).")
    return ir(f"/clinica/envios/{remito_id}")


@router.post("/envios/{remito_id}/cerrar")
async def remito_cerrar(request: Request, remito_id: int, u: UsuarioSesion = UsrClinica, s: Session = Db):
    f = await formulario(request)
    r = EmpaquetadoService(s).cerrar_remito(remito_id, f.get("codigo_precinto", ""), f.get("temperatura_despacho"),
                                            f.get("colocado_por", ""))
    avisar(request, f"Remito cerrado con el precinto {r.precinto.codigo}.")
    if not r.contenedor.temperatura_adecuada(r.temperatura_despacho):
        avisar(request, f"La temperatura de despacho ({r.temperatura_despacho} °C) está fuera del rango del "
                        f"contenedor ({r.contenedor.rango_texto()}): no se podrá despachar.", "warning")
    return ir(f"/clinica/envios/{remito_id}")


@router.post("/envios/{remito_id}/temperatura")
async def remito_temperatura(request: Request, remito_id: int, u: UsuarioSesion = UsrClinica, s: Session = Db):
    f = await formulario(request)
    r = EmpaquetadoService(s).registrar_temperatura_despacho(remito_id, f.get("temperatura_despacho"))
    if r.contenedor.temperatura_adecuada(r.temperatura_despacho):
        avisar(request, f"Temperatura de despacho registrada: {r.temperatura_despacho} °C. Ya se puede despachar.")
    else:
        avisar(request, f"La nueva medición ({r.temperatura_despacho} °C) sigue fuera del rango del contenedor "
                        f"({r.contenedor.rango_texto()}).", "warning")
    return ir(f"/clinica/envios/{remito_id}")


@router.post("/envios/{remito_id}/despachar")
async def remito_despachar(request: Request, remito_id: int, u: UsuarioSesion = UsrClinica, s: Session = Db):
    f = await formulario(request)
    EnviosService(s).despachar(remito_id, f.get("transportista", ""), f.get("llegada_estimada"), u.usuario,
                               f.get("vehiculo", ""), f.get("observaciones", ""))
    avisar(request, "Remito despachado: las muestras están en tránsito.")
    return ir(f"/clinica/envios/{remito_id}")


@router.post("/envios/{remito_id}/retiro")
def remito_retiro(request: Request, remito_id: int, u: UsuarioSesion = UsrClinica, s: Session = Db):
    EnviosService(s).confirmar_retiro(remito_id)
    avisar(request, "Retiro confirmado: el remito está en tránsito hacia el laboratorio.")
    return ir(f"/clinica/envios/{remito_id}")

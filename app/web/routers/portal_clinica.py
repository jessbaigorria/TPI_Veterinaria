"""Portal Clínica: atención de pacientes, órdenes, empaquetado y despacho, cirugías, facturación,
reportes y catálogos. Las rutas solo traducen formularios y llaman a los servicios; los estados los
cambia el dominio."""
from __future__ import annotations

from datetime import datetime, time, timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app import reportes
from app.db import obtener_sesion
from app.domain import reloj
from app.domain.enums import TipoAtencion
from app.domain.estados.estado_remito import EstadoRemito
from app.domain.excepciones import VeterinariaError
from app.services.atenciones import AtencionesService
from app.services.base import a_fecha
from app.services.catalogos import CATALOGOS, CatalogosService
from app.services.cirugias import CirugiasService
from app.services.clientes import ClientesService
from app.services.derivaciones import DerivacionesService
from app.services.empaquetado import EmpaquetadoService
from app.services.envios import EnviosService
from app.services.facturacion import FacturacionService
from app.services.mascotas import MascotasService
from app.services.resultados import ResultadosService
from app.services.tableros import TablerosService
from app.web.plantillas import render
from app.web.routers import reportes_web
from app.web.formato import moneda
from app.web.sesion import UsuarioSesion, avisar, usuario_clinica

router = APIRouter(prefix="/clinica")
Usr = Depends(usuario_clinica)
Db = Depends(obtener_sesion)


FILTROS_REMITO = {"RemitoEnTransito": ["RemitoDespachado", "RemitoEnTransito"]}


def ir(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=303)


async def formulario(request: Request) -> dict:
    return dict(await request.form())


# ============================================================================ inicio ===
@router.get("")
def inicio(request: Request, u: UsuarioSesion = Usr, s: Session = Db):
    hoy = reloj.hoy()
    return render(request, "clinica/inicio.html", seccion="inicio",
                  kpis=TablerosService(s).kpis_clinica(u.clinica_id),
                  turnos=AtencionesService(s).agenda(u.clinica_id, hoy),
                  resultados=ResultadosService(s).resultados_recientes(u.clinica_id, 6),
                  remitos=EmpaquetadoService(s).listar_remitos(clinica_id=u.clinica_id)[:6])


# ============================================================================ agenda ===
@router.get("/agenda")
def agenda(request: Request, fecha: str = "", u: UsuarioSesion = Usr, s: Session = Db):
    dia = a_fecha(fecha) or reloj.hoy()
    svc = AtencionesService(s)
    profesionales = svc.profesionales(u.clinica_id)
    turnos = svc.agenda(u.clinica_id, dia)
    franjas = [datetime.combine(dia, time(8, 0)) + timedelta(minutes=30 * i) for i in range(22)]  # 08:00 a 18:30
    media_hora = timedelta(minutes=30)
    # se_superpone_con_intervalo ignora los turnos cancelados (regla del dominio).
    grilla = {(a.profesional_id, f): a for a in turnos for f in franjas if a.se_superpone_con_intervalo(f, f + media_hora)}
    return render(request, "clinica/agenda.html", seccion="agenda", dia=dia, profesionales=profesionales,
                  turnos=turnos, franjas=franjas, grilla=grilla, anterior=dia - timedelta(days=1),
                  siguiente=dia + timedelta(days=1))


@router.get("/agenda/nuevo")
def turno_nuevo(request: Request, u: UsuarioSesion = Usr, s: Session = Db):
    return render(request, "clinica/turno_nuevo.html", seccion="agenda",
                  titulares=ClientesService(s).buscar(solo_activos=True),
                  profesionales=AtencionesService(s).profesionales(u.clinica_id),
                  mascota=MascotasService(s).obtener_mascota(request.query_params["mascota"])
                  if request.query_params.get("mascota") else None)


@router.post("/agenda/reservar")
async def reservar(request: Request, u: UsuarioSesion = Usr, s: Session = Db):
    f = await formulario(request)
    inicio = f"{f.get('fecha')}T{f.get('hora_inicio')}" if f.get("fecha") and f.get("hora_inicio") else None
    fin = f"{f.get('fecha')}T{f.get('hora_fin')}" if f.get("fecha") and f.get("hora_fin") else None
    a = AtencionesService(s).reservar_turno(f.get("mascota_id"), f.get("profesional_id"), u.clinica_id, inicio, fin,
                                            f.get("tipo") or "CONSULTA", f.get("motivo", ""),
                                            f.get("asiste_titular", "1"), f.get("responsable_presente", ""))
    avisar(request, f"Turno reservado: {a.mascota.nombre} con {a.profesional.nombre_completo()} el "
                    f"{a.fecha_hora_inicio:%d/%m/%Y %H:%M}.")
    pendientes = a.historia.vacunas_pendientes(a.fecha_hora_inicio.date())
    if pendientes and a.tipo in (TipoAtencion.CONSULTA, TipoAtencion.CONTROL):
        avisar(request, f"Atención: {a.mascota.nombre} tiene vacunas pendientes ("
                        + ", ".join(v.nombre for v in pendientes)
                        + "). Al iniciar la atención se bloqueará si no se vacuna antes.", "warning")
    return ir(f"/clinica/agenda?fecha={a.fecha_hora_inicio.date()}")


@router.post("/atenciones/{atencion_id}/iniciar")
def iniciar_atencion(request: Request, atencion_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    r = AtencionesService(s).iniciar(atencion_id)
    avisar(request, "Atención iniciada.")
    if r.advertencia:
        avisar(request, r.advertencia + " Quedó constancia en las observaciones.", "warning")
    return ir(f"/clinica/atenciones/{atencion_id}")


@router.post("/atenciones/{atencion_id}/cancelar")
async def cancelar_atencion(request: Request, atencion_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    f = await formulario(request)
    a = AtencionesService(s).cancelar(atencion_id, f.get("motivo", ""))
    avisar(request, "Turno cancelado.")
    return ir(f"/clinica/agenda?fecha={a.fecha_hora_inicio.date()}")


# ======================================================================== atenciones ===
@router.get("/atenciones")
def atenciones(request: Request, u: UsuarioSesion = Usr, s: Session = Db):
    q = request.query_params
    lista = AtencionesService(s).listar(u.clinica_id, q.get("estado", ""), q.get("tipo", ""),
                                        a_fecha(q.get("desde")), a_fecha(q.get("hasta")), q.get("q", ""))
    return render(request, "clinica/atenciones.html", seccion="atenciones", atenciones=lista)


@router.get("/atenciones/nueva")
def atencion_nueva(request: Request, u: UsuarioSesion = Usr, s: Session = Db):
    return render(request, "clinica/atencion_nueva.html", seccion="atenciones",
                  titulares=ClientesService(s).buscar(solo_activos=True),
                  profesionales=AtencionesService(s).profesionales(u.clinica_id), ahora=reloj.ahora())


@router.post("/atenciones/registrar")
async def atencion_registrar(request: Request, u: UsuarioSesion = Usr, s: Session = Db):
    f = await formulario(request)
    nueva = None
    if (f.get("nm_nombre") or "").strip():   # se completó la mascota nueva: se crea y se usa esa
        nueva = {"titular_id": f.get("titular_id"), "nombre": f.get("nm_nombre"), "especie": f.get("nm_especie"),
                 "sexo": f.get("nm_sexo"), "fecha_nacimiento": f.get("nm_fecha_nacimiento"),
                 "raza": f.get("nm_raza", ""), "peso": f.get("nm_peso")}
    r = AtencionesService(s).registrar_sin_turno(
        f.get("profesional_id"), u.clinica_id, f.get("tipo") or "CONSULTA", mascota_id=f.get("mascota_id"),
        nueva_mascota=nueva, motivo=f.get("motivo", ""), asiste_titular=f.get("asiste_titular", "1"),
        responsable_presente=f.get("responsable_presente", ""), inicio=f.get("inicio") or None,
        duracion_minutos=f.get("duracion") or 30)
    avisar(request, f"Atención registrada e iniciada para {r.atencion.mascota.nombre}.")
    if r.advertencia:
        avisar(request, r.advertencia + " Quedó constancia en las observaciones.", "warning")
    return ir(f"/clinica/atenciones/{r.atencion.id}")


@router.get("/atenciones/{atencion_id}")
def atencion_detalle(request: Request, atencion_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    a = AtencionesService(s).obtener_atencion(atencion_id)
    pendientes = a.historia.detalle_vacunas_pendientes()
    return render(request, "clinica/atencion_detalle.html", seccion="atenciones", a=a, pendientes=pendientes,
                  vacunas=MascotasService(s).vacunas_para(a.mascota))


@router.post("/atenciones/{atencion_id}/finalizar")
async def atencion_finalizar(request: Request, atencion_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    form = await request.form()
    vacunas = [{"vacuna_id": vid, "lote": form.get(f"lote_{vid}", ""), "dosis_numero": form.get(f"dosis_{vid}") or 1}
               for vid in form.getlist("vacuna_id")]
    AtencionesService(s).finalizar(atencion_id, form.get("diagnostico", ""), form.get("peso"), form.get("importe"),
                                   form.get("observaciones"), vacunas)
    avisar(request, "Atención finalizada." + (f" Se registraron {len(vacunas)} vacuna(s)." if vacunas else ""))
    return ir(f"/clinica/atenciones/{atencion_id}")


# ========================================================================== clientes ===
@router.get("/clientes")
def clientes(request: Request, q: str = "", u: UsuarioSesion = Usr, s: Session = Db):
    return render(request, "clinica/clientes.html", seccion="clientes", titulares=ClientesService(s).buscar(q))


@router.get("/clientes/nuevo")
def cliente_nuevo(request: Request, u: UsuarioSesion = Usr):
    return render(request, "clinica/cliente_form.html", seccion="clientes", t=None)


@router.post("/clientes")
async def cliente_crear(request: Request, u: UsuarioSesion = Usr, s: Session = Db):
    f = await formulario(request)
    t = ClientesService(s).crear_titular(f.get("dni"), f.get("nombre"), f.get("apellido"), f.get("direccion", ""),
                                         f.get("telefono", ""), f.get("email", ""))
    avisar(request, f"Titular {t.nombre_completo()} creado.")
    destino = f.get("next") or ""
    if destino.startswith("/clinica/"):   # volver al formulario de origen con el titular elegido
        return ir(f"{destino}{'&' if '?' in destino else '?'}titular={t.id}")
    return ir(f"/clinica/clientes/{t.id}")


@router.get("/clientes/{titular_id}")
def cliente_detalle(request: Request, titular_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    return render(request, "clinica/cliente_detalle.html", seccion="clientes",
                  t=ClientesService(s).obtener_titular(titular_id))


@router.get("/clientes/{titular_id}/editar")
def cliente_editar(request: Request, titular_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    return render(request, "clinica/cliente_form.html", seccion="clientes",
                  t=ClientesService(s).obtener_titular(titular_id))


@router.post("/clientes/{titular_id}")
async def cliente_actualizar(request: Request, titular_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    f = await formulario(request)
    ClientesService(s).actualizar_titular(titular_id, **{k: f.get(k, "") for k in
                                                         ("dni", "nombre", "apellido", "direccion", "telefono", "email")})
    avisar(request, "Datos del titular actualizados.")
    return ir(f"/clinica/clientes/{titular_id}")


@router.post("/clientes/{titular_id}/{accion}")
def cliente_estado(request: Request, titular_id: int, accion: str, u: UsuarioSesion = Usr, s: Session = Db):
    svc = ClientesService(s)
    {"baja": svc.dar_de_baja, "reactivar": svc.reactivar}[accion](titular_id)
    avisar(request, "Titular dado de baja (baja lógica)." if accion == "baja" else "Titular reactivado.")
    return ir(f"/clinica/clientes/{titular_id}")


# ========================================================================== mascotas ===
@router.get("/mascotas")
def mascotas(request: Request, q: str = "", especie: str = "", u: UsuarioSesion = Usr, s: Session = Db):
    return render(request, "clinica/mascotas.html", seccion="mascotas",
                  mascotas=MascotasService(s).buscar(q, especie))


@router.get("/mascotas/nueva")
def mascota_nueva(request: Request, u: UsuarioSesion = Usr, s: Session = Db):
    return render(request, "clinica/mascota_form.html", seccion="mascotas", m=None,
                  titulares=ClientesService(s).buscar(solo_activos=True))


@router.post("/mascotas")
async def mascota_crear(request: Request, u: UsuarioSesion = Usr, s: Session = Db):
    f = await formulario(request)
    m = MascotasService(s).crear_mascota(f.get("titular_id") or None, f.get("nombre"), f.get("especie"),
                                         f.get("sexo"), f.get("fecha_nacimiento"), f.get("raza", ""), f.get("peso"),
                                         f.get("alergias", ""), f.get("antecedentes", ""))
    avisar(request, f"{m.nombre} registrada con historia clínica {m.historia_clinica.numero}.")
    return ir(f"/clinica/mascotas/{m.id}")


@router.get("/mascotas/{mascota_id}")
def mascota_detalle(request: Request, mascota_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    svc = MascotasService(s)
    m = svc.obtener_mascota(mascota_id)
    return render(request, "clinica/mascota_detalle.html", seccion="mascotas", m=m, hc=m.historia_clinica,
                  pendientes=m.historia_clinica.detalle_vacunas_pendientes(), vacunas=svc.vacunas_para(m),
                  titulares=ClientesService(s).buscar(solo_activos=True), tab=request.query_params.get("tab", "resumen"))


@router.get("/mascotas/{mascota_id}/editar")
def mascota_editar(request: Request, mascota_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    return render(request, "clinica/mascota_form.html", seccion="mascotas",
                  m=MascotasService(s).obtener_mascota(mascota_id), titulares=[])


@router.post("/mascotas/{mascota_id}")
async def mascota_actualizar(request: Request, mascota_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    f = await formulario(request)
    MascotasService(s).actualizar_mascota(mascota_id, **{k: f.get(k) for k in
                                                         ("nombre", "especie", "sexo", "fecha_nacimiento", "raza", "peso")})
    avisar(request, "Datos de la mascota actualizados.")
    return ir(f"/clinica/mascotas/{mascota_id}")


@router.post("/mascotas/{mascota_id}/historia")
async def mascota_historia(request: Request, mascota_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    f = await formulario(request)
    MascotasService(s).actualizar_historia(mascota_id, f.get("alergias", ""), f.get("antecedentes", ""),
                                           f.get("observaciones_generales", ""))
    avisar(request, "Historia clínica actualizada.")
    return ir(f"/clinica/mascotas/{mascota_id}")


@router.post("/mascotas/{mascota_id}/vacunas")
async def mascota_vacuna(request: Request, mascota_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    f = await formulario(request)
    MascotasService(s).registrar_vacuna_aplicada(mascota_id, f.get("vacuna_id"), f.get("fecha_aplicacion"),
                                                 f.get("lote", ""), f.get("dosis_numero") or 1)
    avisar(request, "Vacuna registrada en la historia clínica.")
    return ir(f"/clinica/mascotas/{mascota_id}?tab=vacunas")


@router.post("/mascotas/{mascota_id}/titular")
async def mascota_titular(request: Request, mascota_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    f = await formulario(request)
    m = MascotasService(s).cambiar_titular(mascota_id, f.get("titular_id") or None)
    avisar(request, f"Nuevo titular: {m.titular.nombre_completo()}.")
    return ir(f"/clinica/mascotas/{mascota_id}")


@router.post("/mascotas/{mascota_id}/{accion}")
def mascota_estado(request: Request, mascota_id: int, accion: str, u: UsuarioSesion = Usr, s: Session = Db):
    svc = MascotasService(s)
    {"baja": svc.dar_de_baja, "reactivar": svc.reactivar}[accion](mascota_id)
    avisar(request, "Mascota dada de baja (baja lógica)." if accion == "baja" else "Mascota reactivada.")
    return ir(f"/clinica/mascotas/{mascota_id}")


# =========================================================================== órdenes ===
@router.get("/ordenes")
def ordenes(request: Request, estado: str = "", q: str = "", u: UsuarioSesion = Usr, s: Session = Db):
    return render(request, "clinica/ordenes.html", seccion="ordenes",
                  ordenes=DerivacionesService(s).listar_ordenes(u.clinica_id, estado, q))


@router.get("/ordenes/nueva")
def orden_nueva(request: Request, atencion: int, u: UsuarioSesion = Usr, s: Session = Db):
    svc = DerivacionesService(s)
    return render(request, "clinica/orden_nueva.html", seccion="ordenes",
                  a=AtencionesService(s).obtener_atencion(atencion), laboratorios=svc.laboratorios(),
                  tipos=svc.tipos_analisis())


@router.post("/ordenes")
async def orden_crear(request: Request, u: UsuarioSesion = Usr, s: Session = Db):
    form = await request.form()
    o = DerivacionesService(s).emitir_orden(form.get("atencion_id"), form.get("laboratorio_id"),
                                            form.getlist("analisis_id"), form.get("prioridad") or "NORMAL",
                                            form.get("observaciones", ""))
    avisar(request, f"Orden {o.numero} emitida. Registrá ahora la muestra extraída.")
    return ir(f"/clinica/ordenes/{o.id}")


@router.get("/ordenes/{orden_id}")
def orden_detalle(request: Request, orden_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    o = DerivacionesService(s).obtener_orden(orden_id)
    tipos = sorted({t.tipo_muestra_requerida for t in o.analisis}, key=lambda x: x.value)
    return render(request, "clinica/orden_detalle.html", seccion="ordenes", o=o, tipos_muestra=tipos)


@router.post("/ordenes/{orden_id}/muestras")
async def orden_muestra(request: Request, orden_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    f = await formulario(request)
    m = DerivacionesService(s).registrar_muestra(orden_id, f.get("tipo"), f.get("volumen"),
                                                 observaciones=f.get("observaciones", ""))
    avisar(request, f"Muestra {m.codigo} registrada: {m.estado_actual()}.")
    return ir(f"/clinica/ordenes/{orden_id}")


@router.post("/ordenes/{orden_id}/anular")
async def orden_anular(request: Request, orden_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    f = await formulario(request)
    DerivacionesService(s).anular_orden(orden_id, f.get("motivo", ""))
    avisar(request, "Orden anulada.")
    return ir(f"/clinica/ordenes/{orden_id}")


@router.get("/muestras/{muestra_id}")
def muestra_detalle(request: Request, muestra_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    return render(request, "componentes/muestra_detalle.html", seccion="ordenes", base="base.html",
                  m=DerivacionesService(s).obtener_muestra(muestra_id))


# ============================================================================ envíos ===
@router.get("/envios")
def envios(request: Request, estado: str = "", q: str = "", u: UsuarioSesion = Usr, s: Session = Db):
    # El filtro "en camino" agrupa Despachado + En tránsito (es un filtro de listado, no una transición).
    estados = FILTROS_REMITO.get(estado, [estado] if estado else None)
    return render(request, "clinica/envios.html", seccion="envios", estados_remito=EstadoRemito.todos(),
                  remitos=EmpaquetadoService(s).listar_remitos(clinica_id=u.clinica_id, estados=estados, q=q))


@router.get("/envios/nuevo")
def remito_nuevo(request: Request, u: UsuarioSesion = Usr, s: Session = Db):
    emp = EmpaquetadoService(s)
    return render(request, "clinica/remito_nuevo.html", seccion="envios",
                  laboratorios=DerivacionesService(s).laboratorios(),
                  contenedores=emp.contenedores_disponibles(u.clinica_id),
                  muestras=emp.muestras_para_empaquetar(u.clinica_id))


@router.post("/envios")
async def remito_crear(request: Request, u: UsuarioSesion = Usr, s: Session = Db):
    f = await formulario(request)
    r = EmpaquetadoService(s).crear_remito(u.clinica_id, f.get("laboratorio_id"), f.get("contenedor_id"), u.usuario,
                                           f.get("observaciones", ""))
    avisar(request, f"Remito {r.numero} creado. Paso 2: tildá las muestras a empaquetar.")
    return ir(f"/clinica/envios/{r.id}")


@router.get("/envios/{remito_id}")
def remito_detalle(request: Request, remito_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    emp = EmpaquetadoService(s)
    r = emp.obtener_remito(remito_id)
    return render(request, "clinica/remito_detalle.html", seccion="envios", r=r,
                  candidatas=emp.muestras_para_empaquetar(r.clinica_origen_id, r.laboratorio_id),
                  proximo_precinto=emp.proximo_precinto(), llegada_sugerida=reloj.ahora() + timedelta(hours=4))


@router.post("/envios/{remito_id}/muestras")
async def remito_muestras(request: Request, remito_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    form = await request.form()
    ids = form.getlist("muestra_id")
    EmpaquetadoService(s).agregar_muestras(remito_id, ids, u.usuario)
    avisar(request, f"{len(ids)} muestra(s) empaquetada(s).")
    return ir(f"/clinica/envios/{remito_id}")


@router.post("/envios/{remito_id}/cerrar")
async def remito_cerrar(request: Request, remito_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    f = await formulario(request)
    r = EmpaquetadoService(s).cerrar_remito(remito_id, f.get("codigo_precinto", ""), f.get("temperatura_despacho"),
                                            f.get("colocado_por", ""))
    avisar(request, f"Remito cerrado con el precinto {r.precinto.codigo}.")
    if not r.contenedor.temperatura_adecuada(r.temperatura_despacho):
        avisar(request, f"La temperatura de despacho ({r.temperatura_despacho} °C) está fuera del rango del "
                        f"contenedor ({r.contenedor.rango_texto()}): no se podrá despachar.", "warning")
    return ir(f"/clinica/envios/{remito_id}")


@router.post("/envios/{remito_id}/temperatura")
async def remito_temperatura(request: Request, remito_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    f = await formulario(request)
    r = EmpaquetadoService(s).registrar_temperatura_despacho(remito_id, f.get("temperatura_despacho"))
    if r.contenedor.temperatura_adecuada(r.temperatura_despacho):
        avisar(request, f"Temperatura de despacho registrada: {r.temperatura_despacho} °C. Ya se puede despachar.")
    else:
        avisar(request, f"La nueva medición ({r.temperatura_despacho} °C) sigue fuera del rango del contenedor "
                        f"({r.contenedor.rango_texto()}).", "warning")
    return ir(f"/clinica/envios/{remito_id}")


@router.post("/envios/{remito_id}/despachar")
async def remito_despachar(request: Request, remito_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    f = await formulario(request)
    EnviosService(s).despachar(remito_id, f.get("transportista", ""), f.get("llegada_estimada"), u.usuario,
                               f.get("vehiculo", ""), f.get("observaciones", ""))
    avisar(request, "Remito despachado: las muestras están en tránsito.")
    return ir(f"/clinica/envios/{remito_id}")


@router.post("/envios/{remito_id}/retiro")
def remito_retiro(request: Request, remito_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    EnviosService(s).confirmar_retiro(remito_id)
    avisar(request, "Retiro confirmado: el remito está en tránsito hacia el laboratorio.")
    return ir(f"/clinica/envios/{remito_id}")


# ========================================================================== cirugías ===
@router.get("/cirugias")
def cirugias(request: Request, tab: str = "enviadas", u: UsuarioSesion = Usr, s: Session = Db):
    svc = CirugiasService(s)
    return render(request, "clinica/cirugias.html", seccion="cirugias", tab=tab,
                  enviadas=svc.enviadas(u.clinica_id), recibidas=svc.recibidas(u.clinica_id))


@router.get("/cirugias/nueva")
def cirugia_nueva(request: Request, atencion: int, u: UsuarioSesion = Usr, s: Session = Db):
    return render(request, "clinica/cirugia_nueva.html", seccion="cirugias",
                  a=AtencionesService(s).obtener_atencion(atencion), clinicas=CirugiasService(s).todas_las_clinicas())


@router.post("/cirugias")
async def cirugia_crear(request: Request, u: UsuarioSesion = Usr, s: Session = Db):
    f = await formulario(request)
    d = CirugiasService(s).derivar(f.get("atencion_id"), f.get("destino_id"), f.get("tipo_cirugia", ""),
                                   f.get("prioridad") or "NORMAL", f.get("diagnostico_presuntivo", ""),
                                   f.get("riesgo_anestesico") or "ASA_I", f.get("estudios_prequirurgicos", ""))
    avisar(request, f"Derivación {d.numero} enviada a {d.destino.nombre}.")
    return ir(f"/clinica/cirugias/{d.id}")


@router.get("/cirugias/{derivacion_id}")
def cirugia_detalle(request: Request, derivacion_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    d = CirugiasService(s).obtener_derivacion(derivacion_id)
    return render(request, "clinica/cirugia_detalle.html", seccion="cirugias", d=d,
                  es_destino=d.destino_id == u.clinica_id, es_origen=d.clinica_origen.id == u.clinica_id,
                  cirujanos=d.destino.profesionales, ahora=reloj.ahora())


@router.post("/cirugias/{derivacion_id}/{accion}")
async def cirugia_accion(request: Request, derivacion_id: int, accion: str, u: UsuarioSesion = Usr,
                         s: Session = Db):
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


# ======================================================================= facturación ===
@router.get("/facturacion")
def facturacion(request: Request, estado: str = "", tipo: str = "", u: UsuarioSesion = Usr, s: Session = Db):
    svc = FacturacionService(s)
    return render(request, "clinica/facturacion.html", seccion="facturacion", pendientes=svc.pendientes(u.clinica_id),
                  facturas=svc.listar(u.clinica_id, estado, tipo))


@router.post("/facturacion/{origen}/{origen_id}")
async def facturar(request: Request, origen: str, origen_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    svc = FacturacionService(s)
    if origen == "atencion":
        f = svc.facturar_atencion(origen_id)
    elif origen == "orden":
        f = svc.facturar_orden(origen_id)
    elif origen == "cirugia":
        f = svc.facturar_cirugia(origen_id, (await formulario(request)).get("importe"))
    else:
        raise VeterinariaError("Origen de factura desconocido.")
    avisar(request, f"Comprobante {f.numero} emitido por {moneda(f.total)}.")
    return ir(f"/clinica/facturacion/{f.id}")


@router.get("/facturacion/{factura_id}")
def factura_detalle(request: Request, factura_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    return render(request, "clinica/factura_detalle.html", seccion="facturacion",
                  f=FacturacionService(s).obtener_factura(factura_id))


@router.post("/facturas/{factura_id}/pagar")
async def factura_pagar(request: Request, factura_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    f = await formulario(request)
    FacturacionService(s).registrar_pago(factura_id, f.get("forma_pago") or None)
    avisar(request, "Pago registrado.")
    return ir(f"/clinica/facturacion/{factura_id}")


@router.post("/facturas/{factura_id}/anular")
def factura_anular(request: Request, factura_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    FacturacionService(s).anular(factura_id)
    avisar(request, "Factura anulada.")
    return ir(f"/clinica/facturacion/{factura_id}")


# ========================================================================== reportes ===
@router.get("/reportes")
def reportes_inicio(request: Request, u: UsuarioSesion = Usr):
    return render(request, "clinica/reportes.html", seccion="reportes", titulos=reportes.TITULOS)


@router.get("/reportes/{codigo}")
def reporte(request: Request, codigo: str, u: UsuarioSesion = Usr, s: Session = Db):
    filtro = reportes_web.filtro_desde_query(request, codigo)
    return reportes_web.mostrar(request, s, codigo, "base.html", filtro, clinicas=CatalogosService(s).clinicas(),
                                laboratorios=CatalogosService(s).laboratorios(), portal="clinica",
                                disponibles=list(reportes.TITULOS))


# ========================================================================= catálogos ===
@router.get("/catalogos")
def catalogos(request: Request, tab: str = "clinicas", u: UsuarioSesion = Usr, s: Session = Db):
    svc = CatalogosService(s)
    return render(request, "clinica/catalogos.html", seccion="catalogos", tab=tab, catalogos=CATALOGOS,
                  cat=svc.catalogo(tab), items=svc.listar(tab))


@router.get("/catalogos/{clave}/nuevo")
def catalogo_nuevo(request: Request, clave: str, u: UsuarioSesion = Usr, s: Session = Db):
    svc = CatalogosService(s)
    return render(request, "clinica/catalogo_form.html", seccion="catalogos", cat=svc.catalogo(clave), obj=None,
                  clinicas=svc.clinicas())


@router.get("/catalogos/{clave}/{obj_id}/editar")
def catalogo_editar(request: Request, clave: str, obj_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    svc = CatalogosService(s)
    cat = svc.catalogo(clave)
    return render(request, "clinica/catalogo_form.html", seccion="catalogos", cat=cat,
                  obj=svc.obtener(cat.modelo, obj_id), clinicas=svc.clinicas())


@router.post("/catalogos/contenedores/{obj_id}/estado/{accion}")
def contenedor_estado(request: Request, obj_id: int, accion: str, u: UsuarioSesion = Usr, s: Session = Db):
    c = CatalogosService(s).cambiar_estado_contenedor(obj_id, accion)
    avisar(request, f"Contenedor {c.codigo}: {c.estado.etiqueta.lower()}.")
    return ir("/clinica/catalogos?tab=contenedores")


@router.post("/catalogos/{clave}")
async def catalogo_crear(request: Request, clave: str, u: UsuarioSesion = Usr, s: Session = Db):
    CatalogosService(s).guardar(clave, await formulario(request))
    avisar(request, "Registro creado.")
    return ir(f"/clinica/catalogos?tab={clave}")


@router.post("/catalogos/{clave}/{obj_id}")
async def catalogo_actualizar(request: Request, clave: str, obj_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    CatalogosService(s).guardar(clave, await formulario(request), obj_id)
    avisar(request, "Registro actualizado.")
    return ir(f"/clinica/catalogos?tab={clave}")


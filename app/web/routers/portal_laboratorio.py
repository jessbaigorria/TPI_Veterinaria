"""Portal Laboratorio: bandeja de recepción (verificación de precinto y temperatura), cola de
muestras a analizar, carga de resultados, trazabilidad y reportes de muestras rechazadas y tiempos de tránsito."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import obtener_sesion
from app.domain.estados.estado_remito import RemitoDespachado, RemitoEnTransito
from app.domain.excepciones import VeterinariaError
from app.domain.transporte import RecepcionRemito
from app.services.catalogos import CatalogosService
from app.services.derivaciones import DerivacionesService
from app.services.empaquetado import EmpaquetadoService
from app.services.recepcion import RecepcionService
from app.services.resultados import ResultadosService
from app.services.tableros import TablerosService
from app.web.plantillas import render
from app.web.routers import reportes_web
from app.web.sesion import UsuarioSesion, avisar, usuario_laboratorio

router = APIRouter(prefix="/laboratorio")
Usr = Depends(usuario_laboratorio)
Db = Depends(obtener_sesion)
REPORTES_LAB = {"rechazos": "Muestras rechazadas", "tiempos": "Tiempos de tránsito"}


def ir(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=303)


@router.get("")
def inicio(request: Request, u: UsuarioSesion = Usr, s: Session = Db):
    emp = EmpaquetadoService(s)
    return render(request, "laboratorio/inicio.html", seccion="inicio",
                  kpis=TablerosService(s).kpis_laboratorio(u.laboratorio_id),
                  en_camino=emp.listar_remitos(laboratorio_id=u.laboratorio_id,
                                               estados=[RemitoEnTransito.__name__, RemitoDespachado.__name__]),
                  cola=ResultadosService(s).cola_de_analisis(u.laboratorio_id)[:6],
                  recepciones=RecepcionService(s).listar_recepciones(u.laboratorio_id)[:6])


# ========================================================================= recepción ===
@router.get("/recepcion")
def bandeja(request: Request, u: UsuarioSesion = Usr, s: Session = Db):
    emp = EmpaquetadoService(s)
    return render(request, "laboratorio/recepcion.html", seccion="recepcion",
                  en_transito=emp.listar_remitos(laboratorio_id=u.laboratorio_id, estados=[RemitoEnTransito.__name__]),
                  esperando=emp.listar_remitos(laboratorio_id=u.laboratorio_id, estados=[RemitoDespachado.__name__]))


@router.get("/recepcion/{remito_id}")
def recibir_form(request: Request, remito_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    r = EmpaquetadoService(s).obtener_remito(remito_id)
    if r.laboratorio_id != u.laboratorio_id:
        raise VeterinariaError(f"El remito {r.numero} no está destinado a {u.sede_nombre}.")
    return render(request, "laboratorio/recibir.html", seccion="recepcion", r=r)


@router.post("/recepcion/{remito_id}")
async def recibir(request: Request, remito_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    f = dict(await request.form())
    rec = RecepcionService(s).recibir(remito_id, u.laboratorio_id, f.get("precinto_integro", "0"),
                                      f.get("temperatura"), f.get("recibido_por", ""), f.get("codigo_precinto", ""),
                                      f.get("observaciones", ""))
    tipo = "success" if rec.es_aceptada() else "danger"
    avisar(request, f"Remito {rec.remito.numero}: recepción {rec.resultado.etiqueta.upper()}"
                    + (f" – {rec.motivo_rechazo}" if rec.motivo_rechazo else "."), tipo)
    return ir(f"/laboratorio/recepciones/{rec.id}")


@router.get("/recepciones")
def recepciones(request: Request, resultado: str = "", u: UsuarioSesion = Usr, s: Session = Db):
    return render(request, "laboratorio/recepciones.html", seccion="recepciones",
                  recepciones=RecepcionService(s).listar_recepciones(u.laboratorio_id, resultado))


@router.get("/recepciones/{recepcion_id}")
def recepcion_resultado(request: Request, recepcion_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    rec = RecepcionService(s).obtener(RecepcionRemito, recepcion_id)
    return render(request, "laboratorio/recepcion_resultado.html", seccion="recepciones", rec=rec, r=rec.remito)


# =========================================================================== muestras ===
@router.get("/muestras")
def cola(request: Request, u: UsuarioSesion = Usr, s: Session = Db):
    return render(request, "laboratorio/muestras.html", seccion="muestras",
                  muestras=ResultadosService(s).cola_de_analisis(u.laboratorio_id))


@router.get("/muestras/{muestra_id}")
def muestra_detalle(request: Request, muestra_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    return render(request, "componentes/muestra_detalle.html", seccion="trazabilidad", base="base.html",
                  m=DerivacionesService(s).obtener_muestra(muestra_id))


@router.get("/muestras/{muestra_id}/resultados")
def resultados_form(request: Request, muestra_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    m = DerivacionesService(s).obtener_muestra(muestra_id)
    return render(request, "laboratorio/cargar_resultados.html", seccion="muestras", m=m,
                  analisis=m.analisis_pendientes() or m.analisis_requeridos())


@router.post("/muestras/{muestra_id}/resultados")
async def resultados_guardar(request: Request, muestra_id: int, u: UsuarioSesion = Usr, s: Session = Db):
    form = await request.form()
    datos = [{"tipo_analisis_id": tid, "valores": form.get(f"valores_{tid}", ""), "unidad": form.get(f"unidad_{tid}", ""),
              "valores_referencia": form.get(f"referencia_{tid}", ""),
              "interpretacion": form.get(f"interpretacion_{tid}", "")}
             for tid in form.getlist("tipo_analisis_id")]
    m = ResultadosService(s).cargar_resultados(muestra_id, datos, form.get("analista", ""))
    avisar(request, f"Resultados cargados para {m.codigo}. Estado: {m.estado_actual()}"
                    + (f" (orden {m.orden.numero}: {m.orden.estado.etiqueta.lower()})."))
    return ir("/laboratorio/muestras" if m.estado.es_final() else f"/laboratorio/muestras/{muestra_id}/resultados")


# ====================================================================== trazabilidad ===
@router.get("/trazabilidad")
def trazabilidad(request: Request, codigo: str = "", u: UsuarioSesion = Usr, s: Session = Db):
    codigo = codigo.strip().upper()
    muestra = remito = None
    if codigo:
        muestra = DerivacionesService(s).buscar_muestra_por_codigo(codigo)
        remito = None if muestra else EmpaquetadoService(s).buscar_remito_por_numero(codigo)
        if not muestra and not remito:
            avisar(request, f"No se encontró ninguna muestra ni remito con código {codigo}.", "warning")
    return render(request, "laboratorio/trazabilidad.html", seccion="trazabilidad", codigo=codigo, m=muestra,
                  remito=remito, recientes=EmpaquetadoService(s).listar_remitos(laboratorio_id=u.laboratorio_id)[:8])


# ========================================================================== reportes ===
@router.get("/reportes")
def reportes_inicio(request: Request, u: UsuarioSesion = Usr):
    return render(request, "laboratorio/reportes.html", seccion="reportes", titulos=REPORTES_LAB)


@router.get("/reportes/{codigo}")
def reporte(request: Request, codigo: str, u: UsuarioSesion = Usr, s: Session = Db):
    if codigo not in REPORTES_LAB:
        raise VeterinariaError("El laboratorio tiene disponibles los reportes de muestras rechazadas y de tiempos de tránsito.")
    filtro = reportes_web.filtro_desde_query(request, codigo, laboratorio_id=u.laboratorio_id)
    return reportes_web.mostrar(request, s, codigo, "base.html", filtro, clinicas=CatalogosService(s).clinicas(),
                                laboratorios=CatalogosService(s).laboratorios(), mostrar_laboratorio=False,
                                portal="laboratorio", disponibles=list(REPORTES_LAB))

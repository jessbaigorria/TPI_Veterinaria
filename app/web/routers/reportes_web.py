"""Helper compartido por ambos portales para mostrar reportes (filtros, gráfico, tabla y CSV)."""
from __future__ import annotations

from datetime import timedelta

from fastapi import Request
from fastapi.responses import Response

from app import reportes
from app.domain import reloj
from app.reportes import Filtro, a_csv
from app.services.base import a_fecha
from app.web.plantillas import render


def filtro_desde_query(request: Request, codigo: str, **forzados) -> Filtro:
    q = request.query_params
    hoy = reloj.hoy()
    desde_defecto = None if codigo == "r5" else hoy - timedelta(days=60)
    desde = a_fecha(q.get("desde")) if "desde" in q else desde_defecto
    hasta = a_fecha(q.get("hasta")) or hoy
    filtro = Filtro(desde=desde, hasta=hasta,
                    clinica_id=int(q["clinica_id"]) if q.get("clinica_id") else None,
                    laboratorio_id=int(q["laboratorio_id"]) if q.get("laboratorio_id") else None,
                    especie=q.get("especie") or None)
    for k, v in forzados.items():
        setattr(filtro, k, v)
    return filtro


def mostrar(request: Request, s, codigo: str, plantilla_base: str, filtro: Filtro, **contexto):
    if codigo not in reportes.REPORTES:
        from app.domain.excepciones import VeterinariaError
        raise VeterinariaError(f"Reporte desconocido: {codigo}")
    rep = reportes.generar(codigo, s, filtro)
    if request.query_params.get("formato") == "csv":
        return Response(a_csv(rep), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{codigo}_{reloj.hoy()}.csv"'})
    return render(request, "componentes/reporte.html", rep=rep, codigo=codigo, base=plantilla_base,
                  titulos=reportes.TITULOS, seccion="reportes", **contexto)

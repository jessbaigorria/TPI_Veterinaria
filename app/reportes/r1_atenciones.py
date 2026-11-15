"""Reporte: Atenciones clínicas y derivaciones realizadas (por clínica y mes)."""
from __future__ import annotations

from sqlalchemy import case, exists, func, select
from sqlalchemy.orm import Session

from app.domain.atencion import AtencionClinica, Clinica, DerivacionCirugia
from app.domain.enums import EstadoAtencion, TipoAtencion
from app.domain.laboratorio import OrdenDerivacion
from app.reportes.comun import PALETA, Filtro, Grafico, Reporte, Tabla, porcentaje

REALIZADAS = (EstadoAtencion.EN_PROGRESO, EstadoAtencion.FINALIZADA)
N = len(TipoAtencion)  # columnas por tipo de atención


def generar(s: Session, filtro: Filtro) -> Reporte:
    mes = func.strftime("%Y-%m", AtencionClinica.fecha_hora_inicio).label("mes")
    tiene_orden = exists().where(OrdenDerivacion.atencion_id == AtencionClinica.id)
    tiene_cirugia = exists().where(DerivacionCirugia.atencion_id == AtencionClinica.id)
    por_tipo = [func.sum(case((AtencionClinica.tipo == t, 1), else_=0)).label(t.value) for t in TipoAtencion]
    stmt = (
        select(Clinica.nombre, mes, *por_tipo, func.count(AtencionClinica.id).label("total"),
               func.sum(case((tiene_orden, 1), else_=0)).label("con_orden"),
               func.sum(case((tiene_cirugia, 1), else_=0)).label("con_cirugia"),
               func.sum(case((tiene_orden | tiene_cirugia, 1), else_=0)).label("derivadas"))
        .join(Clinica, AtencionClinica.clinica_id == Clinica.id)
        .where(filtro.en_rango(AtencionClinica.fecha_hora_inicio), AtencionClinica.estado.in_(REALIZADAS))
        .group_by(Clinica.nombre, mes).order_by(mes, Clinica.nombre)
    )
    if filtro.clinica_id:
        stmt = stmt.where(AtencionClinica.clinica_id == filtro.clinica_id)
    filas_db = s.execute(stmt).all()

    tabla = Tabla("Atenciones por clínica y mes",
                  ["Clínica", "Mes", *[t.etiqueta for t in TipoAtencion], "Total", "Con orden de laboratorio",
                   "Derivadas a cirugía", "% derivación"])
    totales = [0] * (len(TipoAtencion) + 4)
    for f in filas_db:
        cuenta_tipos = [int(getattr(f, t.value) or 0) for t in TipoAtencion]
        valores = [*cuenta_tipos, f.total, int(f.con_orden or 0), int(f.con_cirugia or 0), int(f.derivadas or 0)]
        totales = [a + b for a, b in zip(totales, valores)]
        tabla.filas.append([f.nombre, _mes(f.mes), *valores[:-1], porcentaje(f.derivadas, f.total)])
    if tabla.filas:
        tabla.totales = ["Total", "", *totales[:-1], porcentaje(totales[-1], totales[N])]

    etiquetas = [f"{f[0]} · {f[1]}" for f in tabla.filas]
    grafico = Grafico("Atenciones por tipo (barras apiladas por clínica y mes)", "bar", etiquetas,
                      [{"label": t.etiqueta, "data": [fila[2 + i] for fila in tabla.filas],
                        "backgroundColor": PALETA[i]} for i, t in enumerate(TipoAtencion)], apilado=True)
    derivaciones = Grafico("Derivaciones generadas", "bar", etiquetas, [
        {"label": "Con orden de laboratorio", "data": [fila[N + 3] for fila in tabla.filas], "backgroundColor": PALETA[3]},
        {"label": "Derivadas a cirugía", "data": [fila[N + 4] for fila in tabla.filas], "backgroundColor": PALETA[4]},
    ])
    total = totales[N]
    indicadores = [("Atenciones realizadas", str(total)),
                   ("Con orden de laboratorio", str(totales[N + 1])),
                   ("Derivadas a cirugía", str(totales[N + 2])),
                   ("% derivación", f"{porcentaje(totales[N + 3], total)} %")]
    return Reporte("atenciones", "Atenciones y derivaciones",
                   "Atenciones realizadas (en progreso o finalizadas) por clínica y mes, según tipo, y cuántas "
                   "generaron una orden de laboratorio o una derivación a cirugía.",
                   filtro, [tabla], [grafico, derivaciones], indicadores)


def _mes(aaaa_mm: str) -> str:
    anio, mes = aaaa_mm.split("-")
    return f"{mes}/{anio}"

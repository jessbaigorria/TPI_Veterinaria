"""Exportación de reportes a PDF con ReportLab (Python puro: anda en Windows sin instalar nada más).

Cada PDF lleva: encabezado (nombre del reporte, sede y fecha de emisión), filtros aplicados, indicadores,
los gráficos (dibujados con ReportLab) y las tablas con montos en pesos, fechas dd/mm/aaaa y totales."""
from __future__ import annotations

import io
from datetime import date, datetime
from decimal import Decimal

from reportlab.graphics.charts.barcharts import HorizontalBarChart, VerticalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from app.domain import reloj
from app.reportes.comun import Grafico, Reporte
from app.web.formato import fecha, fecha_hora, moneda, numero

COLOR_PRINCIPAL = colors.HexColor("#0f766e")
GRIS = colors.HexColor("#6b7280")
_ESTILOS = getSampleStyleSheet()
TITULO = ParagraphStyle("titulo", parent=_ESTILOS["Title"], fontSize=17, textColor=COLOR_PRINCIPAL, alignment=0,
                        spaceAfter=2)
SUBTITULO = ParagraphStyle("sub", parent=_ESTILOS["Normal"], fontSize=9, textColor=GRIS, leading=12)
SECCION = ParagraphStyle("sec", parent=_ESTILOS["Heading3"], fontSize=11, spaceBefore=8, spaceAfter=4)
CELDA = ParagraphStyle("celda", parent=_ESTILOS["Normal"], fontSize=7.8, leading=9.5)
CELDA_NUM = ParagraphStyle("celda_num", parent=CELDA, alignment=TA_RIGHT)
CELDA_TIT = ParagraphStyle("celda_tit", parent=CELDA, fontName="Helvetica-Bold", textColor=colors.white)


def _valor(v, columna: str) -> str:
    if isinstance(v, Decimal):
        return moneda(v)
    if isinstance(v, datetime):
        return fecha_hora(v)
    if isinstance(v, date):
        return fecha(v)
    if v is None:
        return "–"
    if isinstance(v, float):
        texto = numero(v)
    else:
        texto = str(v)
    if columna.startswith("%") and texto != "–":
        texto += " %"
    return texto


def _es_numero(v) -> bool:
    return isinstance(v, (int, float, Decimal)) and not isinstance(v, bool)


def _color(c, i: int):
    if isinstance(c, list):
        c = c[i % len(c)]
    try:
        return colors.HexColor(c) if isinstance(c, str) else colors.HexColor("#0d9488")
    except ValueError:  # pragma: no cover
        return colors.HexColor("#0d9488")


def _grafico(g: Grafico, ancho: float) -> Drawing | None:
    if not g.etiquetas or not g.series:
        return None
    alto = 62 * mm
    d = Drawing(ancho, alto + 12)
    d.add(String(0, alto + 2, g.titulo, fontName="Helvetica-Bold", fontSize=9, fillColor=colors.black))
    if g.tipo in ("pie", "doughnut"):
        datos = [float(x or 0) for x in g.series[0]["data"]]
        if not any(datos):
            return None
        pie = Pie()
        pie.x, pie.y, pie.width, pie.height = 10, 5, alto - 15, alto - 15
        pie.data = datos
        pie.labels = [f"{e} ({numero(v) if isinstance(v, float) else v})" for e, v in zip(g.etiquetas, g.series[0]["data"])]
        pie.simpleLabels = 1
        pie.slices.strokeColor = colors.white
        for i in range(len(datos)):
            pie.slices[i].fillColor = _color(g.series[0].get("backgroundColor"), i)
            pie.slices[i].fontSize = 7
        d.add(pie)
        return d
    rotadas = not g.horizontal and len(g.etiquetas) > 4
    chart = HorizontalBarChart() if g.horizontal else VerticalBarChart()
    chart.x, chart.y = (95 if g.horizontal else 40), (58 if rotadas else 28)
    chart.width, chart.height = ancho - chart.x - 120, alto - chart.y - 12
    chart.data = [[float(x or 0) for x in s["data"]] for s in g.series]
    etiquetas = [e if len(e) <= 28 else e[:26] + "…" for e in g.etiquetas]
    chart.categoryAxis.categoryNames = etiquetas
    chart.categoryAxis.labels.fontSize = 6.5
    chart.categoryAxis.labels.fontName = "Helvetica"
    chart.valueAxis.labels.fontName = "Helvetica"
    if not g.horizontal:
        chart.categoryAxis.labels.angle = 30 if rotadas else 0
        chart.categoryAxis.labels.boxAnchor = "ne" if rotadas else "n"
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.valueMin = 0
    if g.apilado:
        chart.categoryAxis.style = "stacked"
    for i, s in enumerate(g.series):
        chart.bars[i].fillColor = _color(s.get("backgroundColor"), i)
        chart.bars[i].strokeColor = None
    d.add(chart)
    leyenda = Legend()
    leyenda.x, leyenda.y = ancho - 110, alto - 15
    leyenda.fontSize = 7
    leyenda.fontName = "Helvetica"
    leyenda.alignment = "right"
    leyenda.colorNamePairs = [(_color(s.get("backgroundColor"), i), s["label"]) for i, s in enumerate(g.series)]
    d.add(leyenda)
    return d


def _tabla(tabla, ancho: float) -> Table:
    columnas = tabla.columnas
    encabezado = [Paragraph(c, CELDA_TIT) for c in columnas]
    filas = []
    for fila in tabla.filas:
        filas.append([Paragraph(_valor(v, columnas[i]), CELDA_NUM if _es_numero(v) else CELDA)
                      for i, v in enumerate(fila)])
    datos = [encabezado] + filas
    if tabla.totales:
        datos.append([Paragraph(f"<b>{_valor(v, columnas[i])}</b>", CELDA_NUM if _es_numero(v) else CELDA)
                      for i, v in enumerate(tabla.totales)])
    t = Table(datos, colWidths=[ancho / len(columnas)] * len(columnas), repeatRows=1)
    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRINCIPAL),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d1d5db")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if tabla.totales:
        estilo.append(("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e5e7eb")))
    t.setStyle(TableStyle(estilo))
    return t


def a_pdf(reporte: Reporte, sede: str, filtros: list[tuple[str, str]]) -> bytes:
    buffer = io.BytesIO()
    pagina = landscape(A4)
    doc = SimpleDocTemplate(buffer, pagesize=pagina, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm,
                            bottomMargin=12 * mm, title=reporte.titulo, author="VetRed")
    ancho = pagina[0] - doc.leftMargin - doc.rightMargin
    historia = [
        Paragraph(reporte.titulo, TITULO),
        Paragraph(f"{sede} · Emitido el {fecha_hora(reloj.ahora())}", SUBTITULO),
        Paragraph(reporte.descripcion, SUBTITULO),
        Spacer(1, 4),
        Paragraph("<b>Filtros:</b> " + " · ".join(f"{k}: {v}" for k, v in filtros), SUBTITULO),
    ]
    if reporte.indicadores:
        celdas = [[Paragraph(f"<font size=7 color='#6b7280'>{t}</font><br/><b>{v}</b>", CELDA)
                   for t, v in reporte.indicadores]]
        ind = Table(celdas, colWidths=[ancho / len(reporte.indicadores)] * len(reporte.indicadores))
        ind.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.3, colors.HexColor("#d1d5db")),
                                 ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d1d5db")),
                                 ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        historia += [Spacer(1, 6), ind]
    if reporte.vacio:
        historia += [Spacer(1, 12), Paragraph("No hay registros para mostrar con los filtros elegidos.", SUBTITULO)]
    else:
        graficos = [d for d in (_grafico(g, ancho / 2 - 4 * mm) for g in reporte.graficos) if d is not None]
        if graficos:
            fila = graficos[:2] + [""] * (2 - len(graficos[:2]))
            t = Table([fila], colWidths=[ancho / 2] * 2)
            t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
            historia += [Spacer(1, 8), t, Spacer(1, 6)]
        for tabla in reporte.tablas:
            bloque = [Paragraph(tabla.titulo, SECCION)]
            bloque.append(_tabla(tabla, ancho) if tabla.filas else Paragraph("No hay registros para mostrar.", SUBTITULO))
            historia.append(KeepTogether(bloque) if len(tabla.filas) < 15 else bloque[0])
            if len(tabla.filas) >= 15:
                historia.append(bloque[1])

    def pie_de_pagina(canvas, documento):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(GRIS)
        canvas.drawString(doc.leftMargin, 7 * mm, f"VetRed · {reporte.titulo}")
        canvas.drawRightString(pagina[0] - doc.rightMargin, 7 * mm, f"Página {documento.page}")
        canvas.restoreState()

    doc.build(historia, onFirstPage=pie_de_pagina, onLaterPages=pie_de_pagina)
    return buffer.getvalue()

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
    """Dibuja un gráfico del reporte (torta/dona o barras). None si no hay nada para mostrar."""
    if not g.etiquetas or not g.series:
        return None
    alto = 62 * mm
    if g.tipo in ("pie", "doughnut"):
        return _grafico_torta(g, ancho, alto)
    return _grafico_barras(g, ancho, alto)


def _lienzo(g: Grafico, ancho: float, alto: float) -> Drawing:
    d = Drawing(ancho, alto + 12)
    d.add(String(0, alto + 2, g.titulo, fontName="Helvetica-Bold", fontSize=9, fillColor=colors.black))
    return d


def _grafico_torta(g: Grafico, ancho: float, alto: float) -> Drawing | None:
    serie = g.series[0]
    datos = [float(x or 0) for x in serie["data"]]
    if not any(datos):
        return None
    d = _lienzo(g, ancho, alto)
    pie = Pie()
    pie.x, pie.y, pie.width, pie.height = 10, 5, alto - 15, alto - 15
    pie.data = datos
    pie.labels = [f"{e} ({numero(v) if isinstance(v, float) else v})" for e, v in zip(g.etiquetas, serie["data"])]
    pie.simpleLabels = 1
    pie.slices.strokeColor = colors.white
    for i in range(len(datos)):
        pie.slices[i].fillColor = _color(serie.get("backgroundColor"), i)
        pie.slices[i].fontSize = 7
    d.add(pie)
    return d


def _grafico_barras(g: Grafico, ancho: float, alto: float) -> Drawing:
    d = _lienzo(g, ancho, alto)
    d.add(_barras(g, ancho, alto))
    d.add(_leyenda(g, ancho, alto))
    return d


def _barras(g: Grafico, ancho: float, alto: float):
    rotadas = not g.horizontal and len(g.etiquetas) > 4   # muchas categorías: etiquetas inclinadas
    chart = HorizontalBarChart() if g.horizontal else VerticalBarChart()
    chart.x, chart.y = (95 if g.horizontal else 40), (58 if rotadas else 28)
    chart.width, chart.height = ancho - chart.x - 120, alto - chart.y - 12
    chart.data = [[float(x or 0) for x in s["data"]] for s in g.series]
    chart.categoryAxis.categoryNames = [e if len(e) <= 28 else e[:26] + "…" for e in g.etiquetas]
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
    return chart


def _leyenda(g: Grafico, ancho: float, alto: float) -> Legend:
    leyenda = Legend()
    leyenda.x, leyenda.y = ancho - 110, alto - 15
    leyenda.fontSize = 7
    leyenda.fontName = "Helvetica"
    leyenda.alignment = "right"
    leyenda.colorNamePairs = [(_color(s.get("backgroundColor"), i), s["label"]) for i, s in enumerate(g.series)]
    return leyenda


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
    historia = _encabezado(reporte, sede, filtros)
    if reporte.indicadores:
        historia += [Spacer(1, 6), _indicadores(reporte.indicadores, ancho)]
    if reporte.vacio:
        historia += [Spacer(1, 12), Paragraph("No hay registros para mostrar con los filtros elegidos.", SUBTITULO)]
    else:
        historia += _graficos(reporte, ancho) + _tablas(reporte, ancho)
    pie = _pie_de_pagina(reporte.titulo, doc, pagina)
    doc.build(historia, onFirstPage=pie, onLaterPages=pie)
    return buffer.getvalue()


def _encabezado(reporte: Reporte, sede: str, filtros: list[tuple[str, str]]) -> list:
    return [
        Paragraph(reporte.titulo, TITULO),
        Paragraph(f"{sede} · Emitido el {fecha_hora(reloj.ahora())}", SUBTITULO),
        Paragraph(reporte.descripcion, SUBTITULO),
        Spacer(1, 4),
        Paragraph("<b>Filtros:</b> " + " · ".join(f"{k}: {v}" for k, v in filtros), SUBTITULO),
    ]


def _indicadores(indicadores: list[tuple[str, str]], ancho: float) -> Table:
    """Una fila de recuadros: título chico en gris y valor en negrita."""
    celdas = [[Paragraph(f"<font size=7 color='#6b7280'>{t}</font><br/><b>{v}</b>", CELDA) for t, v in indicadores]]
    tabla = Table(celdas, colWidths=[ancho / len(indicadores)] * len(indicadores))
    tabla.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.3, colors.HexColor("#d1d5db")),
                               ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d1d5db")),
                               ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    return tabla


def _graficos(reporte: Reporte, ancho: float) -> list:
    """Los dos primeros gráficos, uno al lado del otro."""
    graficos = [d for d in (_grafico(g, ancho / 2 - 4 * mm) for g in reporte.graficos) if d is not None]
    if not graficos:
        return []
    fila = graficos[:2] + [""] * (2 - len(graficos[:2]))
    tabla = Table([fila], colWidths=[ancho / 2] * 2)
    tabla.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return [Spacer(1, 8), tabla, Spacer(1, 6)]


def _tablas(reporte: Reporte, ancho: float) -> list:
    """Cada tabla con su título; las cortas (menos de 15 filas) no se parten entre páginas."""
    historia = []
    for tabla in reporte.tablas:
        cuerpo = _tabla(tabla, ancho) if tabla.filas else Paragraph("No hay registros para mostrar.", SUBTITULO)
        bloque = [Paragraph(tabla.titulo, SECCION), cuerpo]
        historia += [KeepTogether(bloque)] if len(tabla.filas) < 15 else bloque
    return historia


def _pie_de_pagina(titulo: str, doc: SimpleDocTemplate, pagina):
    def dibujar(canvas, documento):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(GRIS)
        canvas.drawString(doc.leftMargin, 7 * mm, f"VetRed · {titulo}")
        canvas.drawRightString(pagina[0] - doc.rightMargin, 7 * mm, f"Página {documento.page}")
        canvas.restoreState()

    return dibujar

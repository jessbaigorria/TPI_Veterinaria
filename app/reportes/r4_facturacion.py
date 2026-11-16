"""Reporte: Facturación desglosada por clínica y por servicios de laboratorio."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import case, func, select, type_coerce
from sqlalchemy.orm import Session

from app.domain.base import Dinero
from app.domain.clinica import Clinica
from app.domain.enums import EstadoFactura, TipoComprobante
from app.domain.facturacion import Factura, ItemFactura
from app.domain.laboratorio import TipoAnalisis
from app.reportes.comun import PALETA, Filtro, Grafico, Reporte, Tabla, serie
from app.web.formato import moneda

CERO = Decimal("0.00")
TIPOS = list(TipoComprobante)
DESCRIPCION = ("Comprobantes emitidos en el período (sin anuladas) por clínica emisora y tipo; ranking de "
               "análisis facturados; cobrado (pagadas) vs pendiente (emitidas).")


def generar(s: Session, filtro: Filtro) -> Reporte:
    t_clinica = _tabla_por_clinica(s.execute(_consulta_por_clinica(filtro)).all())
    t_ranking = Tabla("Ranking de análisis de laboratorio más facturados",
                      ["#", "Código", "Análisis", "Cantidad", "Importe"],
                      [[i + 1, f.codigo, f.nombre, int(f.cant), f.importe or CERO]
                       for i, f in enumerate(s.execute(_consulta_ranking(filtro)).all())])
    return Reporte("facturacion", "Facturación por clínica y laboratorio", DESCRIPCION, filtro,
                   [t_clinica, t_ranking], _graficos(t_clinica, t_ranking), _indicadores(t_clinica))


def _vigentes(filtro: Filtro):
    """Condiciones comunes: facturas no anuladas emitidas en el período."""
    return Factura.estado != EstadoFactura.ANULADA, filtro.en_rango(Factura.fecha_emision)


def _consulta_por_clinica(filtro: Filtro):
    """Por clínica: total por tipo de comprobante, total, cobrado, pendiente y cantidad de comprobantes."""
    def suma_si(condicion):
        return type_coerce(func.sum(case((condicion, Factura.total), else_=0)), Dinero)

    stmt = (select(Clinica.nombre,
                   *[suma_si(Factura.tipo == t).label(t.value) for t in TIPOS],
                   type_coerce(func.sum(Factura.total), Dinero).label("total"),
                   suma_si(Factura.estado == EstadoFactura.PAGADA).label("cobrado"),
                   suma_si(Factura.estado == EstadoFactura.EMITIDA).label("pendiente"),
                   func.count(Factura.id).label("n"))
            .join(Clinica, Clinica.id == Factura.clinica_id)
            .where(*_vigentes(filtro))
            .group_by(Clinica.nombre).order_by(Clinica.nombre))
    return filtro.aplicar(stmt, clinica=Factura.clinica_id)


def _consulta_ranking(filtro: Filtro):
    """Análisis más facturados (cantidad e importe de los ítems de factura)."""
    importe_item = type_coerce(func.sum(ItemFactura.precio_unitario * ItemFactura.cantidad), Dinero)
    stmt = (select(TipoAnalisis.codigo, TipoAnalisis.nombre, func.sum(ItemFactura.cantidad).label("cant"),
                   importe_item.label("importe"))
            .join(ItemFactura, ItemFactura.tipo_analisis_id == TipoAnalisis.id)
            .join(Factura, Factura.id == ItemFactura.factura_id)
            .where(*_vigentes(filtro))
            .group_by(TipoAnalisis.codigo, TipoAnalisis.nombre)
            .order_by(importe_item.desc(), TipoAnalisis.nombre))
    return filtro.aplicar(stmt, clinica=Factura.clinica_id)


def _tabla_por_clinica(filas) -> Tabla:
    tabla = Tabla("Total facturado por clínica y tipo de comprobante (excluye anuladas)",
                  ["Clínica", *[t.etiqueta for t in TIPOS], "Total", "Cobrado", "Pendiente", "Comprobantes"])
    for f in filas:
        tabla.filas.append([f.nombre, *[getattr(f, t.value) or CERO for t in TIPOS],
                            f.total or CERO, f.cobrado or CERO, f.pendiente or CERO, f.n])
    if tabla.filas:
        importes = [sum((fila[i] for fila in tabla.filas), CERO) for i in range(1, len(TIPOS) + 4)]
        tabla.totales = ["Total", *importes, sum(fila[-1] for fila in tabla.filas)]
    return tabla


def _graficos(t_clinica: Tabla, t_ranking: Tabla) -> list[Grafico]:
    top = t_ranking.filas[:8]
    return [
        Grafico("Facturación por clínica y tipo de comprobante ($)", "bar", t_clinica.columna(0),
                [serie(t.etiqueta, t_clinica.columna(1 + i), PALETA[i]) for i, t in enumerate(TIPOS)], apilado=True),
        Grafico("Análisis más facturados ($)", "bar", [f[2] for f in top],
                [serie("Importe", [f[4] for f in top], PALETA[1])], horizontal=True),
    ]


def _indicadores(t_clinica: Tabla) -> list[tuple[str, str]]:
    # Totales: ["Total", atención clínica, laboratorio, cirugía, total, cobrado, pendiente, comprobantes]
    tot = t_clinica.totales or ["", CERO, CERO, CERO, CERO, CERO, CERO, 0]
    return [("Total facturado", moneda(tot[4])), ("Cobrado", moneda(tot[5])),
            ("Pendiente de cobro", moneda(tot[6])), ("Servicios de laboratorio", moneda(tot[2]))]

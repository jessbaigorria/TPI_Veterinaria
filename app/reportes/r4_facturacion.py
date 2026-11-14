"""R4 – Facturación desglosada por clínica y por servicios de laboratorio."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import case, func, select, type_coerce
from sqlalchemy.orm import Session

from app.domain.atencion import Clinica
from app.domain.base import Dinero
from app.domain.enums import EstadoFactura, TipoComprobante
from app.domain.facturacion import Factura, ItemFactura
from app.domain.laboratorio import TipoAnalisis
from app.reportes.comun import PALETA, Filtro, Grafico, Reporte, Tabla

CERO = Decimal("0.00")


def generar(s: Session, filtro: Filtro) -> Reporte:
    vigente = Factura.estado != EstadoFactura.ANULADA

    def suma_si(condicion):
        return type_coerce(func.sum(case((condicion, Factura.total), else_=0)), Dinero)

    stmt = (select(Clinica.nombre,
                   *[suma_si(Factura.tipo == t).label(t.value) for t in TipoComprobante],
                   type_coerce(func.sum(Factura.total), Dinero).label("total"),
                   suma_si(Factura.estado == EstadoFactura.PAGADA).label("cobrado"),
                   suma_si(Factura.estado == EstadoFactura.EMITIDA).label("pendiente"),
                   func.count(Factura.id).label("n"))
            .join(Clinica, Clinica.id == Factura.clinica_id)
            .where(vigente, filtro.en_rango(Factura.fecha_emision))
            .group_by(Clinica.nombre).order_by(Clinica.nombre))
    if filtro.clinica_id:
        stmt = stmt.where(Factura.clinica_id == filtro.clinica_id)
    filas = s.execute(stmt).all()

    t_clinica = Tabla("Total facturado por clínica y tipo de comprobante (excluye anuladas)",
                      ["Clínica", *[t.etiqueta for t in TipoComprobante], "Total", "Cobrado", "Pendiente", "Comprobantes"])
    for f in filas:
        t_clinica.filas.append([f.nombre, *[getattr(f, t.value) or CERO for t in TipoComprobante],
                                f.total or CERO, f.cobrado or CERO, f.pendiente or CERO, f.n])
    if t_clinica.filas:
        t_clinica.totales = ["Total", *[sum((fila[i] for fila in t_clinica.filas), CERO)
                                        for i in range(1, len(TipoComprobante) + 4)],
                             sum(fila[-1] for fila in t_clinica.filas)]

    importe_item = type_coerce(func.sum(ItemFactura.precio_unitario * ItemFactura.cantidad), Dinero)
    stmt_r = (select(TipoAnalisis.codigo, TipoAnalisis.nombre, func.sum(ItemFactura.cantidad).label("cant"),
                     importe_item.label("importe"))
              .join(ItemFactura, ItemFactura.tipo_analisis_id == TipoAnalisis.id)
              .join(Factura, Factura.id == ItemFactura.factura_id)
              .where(vigente, filtro.en_rango(Factura.fecha_emision))
              .group_by(TipoAnalisis.codigo, TipoAnalisis.nombre)
              .order_by(importe_item.desc(), TipoAnalisis.nombre))
    if filtro.clinica_id:
        stmt_r = stmt_r.where(Factura.clinica_id == filtro.clinica_id)
    ranking = s.execute(stmt_r).all()
    t_ranking = Tabla("Ranking de análisis de laboratorio más facturados",
                      ["#", "Código", "Análisis", "Cantidad", "Importe"],
                      [[i + 1, f.codigo, f.nombre, int(f.cant), f.importe or CERO] for i, f in enumerate(ranking)])

    graficos = [
        Grafico("Facturación por clínica y tipo de comprobante ($)", "bar", [f[0] for f in t_clinica.filas],
                [{"label": t.etiqueta, "data": [fila[1 + i] for fila in t_clinica.filas], "backgroundColor": PALETA[i]}
                 for i, t in enumerate(TipoComprobante)], apilado=True),
        Grafico("Análisis más facturados ($)", "bar", [f[2] for f in t_ranking.filas[:8]],
                [{"label": "Importe", "data": [f[4] for f in t_ranking.filas[:8]], "backgroundColor": PALETA[1]}],
                horizontal=True),
    ]
    tot = t_clinica.totales or ["", CERO, CERO, CERO, CERO, CERO, CERO, 0]
    indicadores = [("Total facturado", _pesos(tot[4])), ("Cobrado", _pesos(tot[5])), ("Pendiente de cobro", _pesos(tot[6])),
                   ("Servicios de laboratorio", _pesos(tot[2]))]
    return Reporte("R4", "Facturación por clínica y servicios de laboratorio",
                   "Comprobantes emitidos en el período (sin anuladas) por clínica emisora y tipo; ranking de "
                   "análisis facturados; cobrado (pagadas) vs pendiente (emitidas).",
                   filtro, [t_clinica, t_ranking], graficos, indicadores)


def _pesos(v) -> str:
    entero, dec = f"{Decimal(v):,.2f}".split(".")
    return f"$ {entero.replace(',', '.')},{dec}"

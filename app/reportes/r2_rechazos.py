"""Reporte: Muestras rechazadas por fallas en el transporte."""
from __future__ import annotations

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.domain.atencion import Clinica
from app.domain.enums import EstadoPrecinto, ResultadoRecepcion
from app.domain.laboratorio import MuestraBiologica
from app.domain.transporte import Envio, RecepcionRemito, RemitoBiologico
from app.reportes.comun import PALETA, Filtro, Grafico, Reporte, Tabla, porcentaje

MOTIVO_PRECINTO = RecepcionRemito.MOTIVO_PRECINTO
MOTIVO_TEMPERATURA = RecepcionRemito.MOTIVO_TEMPERATURA


def generar(s: Session, filtro: Filtro) -> Reporte:
    # Cantidad de muestras por remito.
    muestras_por_remito = (select(MuestraBiologica.remito_id, func.count(MuestraBiologica.id).label("n"))
                           .where(MuestraBiologica.remito_id.is_not(None))
                           .group_by(MuestraBiologica.remito_id).subquery())
    rechazado = RecepcionRemito.resultado == ResultadoRecepcion.RECHAZADA
    motivo = case((RecepcionRemito.estado_precinto_observado == EstadoPrecinto.ROTO, MOTIVO_PRECINTO),
                  else_=MOTIVO_TEMPERATURA)
    enviadas = func.sum(muestras_por_remito.c.n)
    rechazadas = func.sum(case((rechazado, muestras_por_remito.c.n), else_=0))

    def base(*columnas):
        stmt = (select(*columnas)
                .select_from(RemitoBiologico)
                .join(Envio, Envio.remito_id == RemitoBiologico.id)
                .join(muestras_por_remito, muestras_por_remito.c.remito_id == RemitoBiologico.id)
                .outerjoin(RecepcionRemito, RecepcionRemito.remito_id == RemitoBiologico.id)
                .join(Clinica, Clinica.id == RemitoBiologico.clinica_origen_id)
                .where(filtro.en_rango(Envio.fecha_hora_despacho)))
        if filtro.clinica_id:
            stmt = stmt.where(RemitoBiologico.clinica_origen_id == filtro.clinica_id)
        if filtro.laboratorio_id:
            stmt = stmt.where(RemitoBiologico.laboratorio_id == filtro.laboratorio_id)
        return stmt

    por_clinica = s.execute(base(Clinica.nombre, enviadas.label("env"), rechazadas.label("rech"))
                            .group_by(Clinica.nombre).order_by(Clinica.nombre)).all()
    por_transportista = s.execute(base(Envio.transportista, enviadas.label("env"), rechazadas.label("rech"))
                                  .group_by(Envio.transportista).order_by(Envio.transportista)).all()
    por_motivo = s.execute(base(motivo.label("motivo"), func.count(RemitoBiologico.id).label("remitos"),
                                func.sum(muestras_por_remito.c.n).label("muestras"))
                           .where(rechazado).group_by(motivo).order_by(motivo)).all()

    t_clinica = Tabla("Por clínica de origen", ["Clínica", "Muestras enviadas", "Rechazadas", "% rechazo"],
                      [[f.nombre, int(f.env), int(f.rech), porcentaje(f.rech, f.env)] for f in por_clinica])
    tot_env = sum(int(f.env) for f in por_clinica)
    tot_rech = sum(int(f.rech) for f in por_clinica)
    if t_clinica.filas:
        t_clinica.totales = ["Total", tot_env, tot_rech, porcentaje(tot_rech, tot_env)]
    t_motivo = Tabla("Por motivo de rechazo", ["Motivo", "Remitos", "Muestras rechazadas", "% sobre rechazadas"],
                     [[f.motivo, int(f.remitos), int(f.muestras), porcentaje(f.muestras, tot_rech)] for f in por_motivo])
    t_transp = Tabla("Por transportista", ["Transportista", "Muestras enviadas", "Rechazadas", "% rechazo"],
                     [[f.transportista, int(f.env), int(f.rech), porcentaje(f.rech, f.env)] for f in por_transportista])

    graficos = [
        Grafico("Muestras enviadas vs rechazadas por clínica", "bar", [f[0] for f in t_clinica.filas], [
            {"label": "Enviadas", "data": [f[1] for f in t_clinica.filas], "backgroundColor": PALETA[3]},
            {"label": "Rechazadas", "data": [f[2] for f in t_clinica.filas], "backgroundColor": PALETA[4]}]),
        Grafico("Rechazos por motivo", "doughnut", [f[0] for f in t_motivo.filas], [
            {"label": "Muestras", "data": [f[2] for f in t_motivo.filas], "backgroundColor": [PALETA[4], PALETA[2]]}]),
    ]
    indicadores = [("Muestras enviadas", str(tot_env)), ("Rechazadas", str(tot_rech)),
                   ("% rechazo", f"{porcentaje(tot_rech, tot_env)} %")]
    return Reporte("rechazos", "Muestras rechazadas",
                   "Muestras despachadas en el período y cuántas fueron rechazadas en la recepción del laboratorio "
                   "por precinto roto o temperatura fuera de rango.",
                   filtro, [t_clinica, t_motivo, t_transp], graficos, indicadores)

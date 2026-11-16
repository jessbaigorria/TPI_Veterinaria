"""Reporte: Muestras rechazadas por fallas en el transporte."""
from __future__ import annotations

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.domain.clinica import Clinica
from app.domain.enums import EstadoPrecinto, ResultadoRecepcion
from app.domain.muestra import MuestraBiologica
from app.domain.transporte import Envio, RecepcionRemito, RemitoBiologico
from app.reportes.comun import PALETA, Filtro, Grafico, Reporte, Tabla, porcentaje, serie

MOTIVO_PRECINTO = RecepcionRemito.MOTIVO_PRECINTO
MOTIVO_TEMPERATURA = RecepcionRemito.MOTIVO_TEMPERATURA
DESCRIPCION = ("Muestras despachadas en el período y cuántas fueron rechazadas en la recepción del laboratorio "
               "por precinto roto o temperatura fuera de rango.")


def generar(s: Session, filtro: Filtro) -> Reporte:
    consulta = _ConsultaRechazos(filtro)
    t_clinica = _tabla_por_clinica(s.execute(consulta.por_clinica()).all())
    tot_env, tot_rech = (t_clinica.totales[1], t_clinica.totales[2]) if t_clinica.totales else (0, 0)
    t_motivo = Tabla("Por motivo de rechazo", ["Motivo", "Remitos", "Muestras rechazadas", "% sobre rechazadas"],
                     [[f.motivo, int(f.remitos), int(f.muestras), porcentaje(f.muestras, tot_rech)]
                      for f in s.execute(consulta.por_motivo()).all()])
    t_transp = Tabla("Por transportista", ["Transportista", "Muestras enviadas", "Rechazadas", "% rechazo"],
                     [[f.transportista, int(f.env), int(f.rech), porcentaje(f.rech, f.env)]
                      for f in s.execute(consulta.por_transportista()).all()])
    indicadores = [("Muestras enviadas", str(tot_env)), ("Rechazadas", str(tot_rech)),
                   ("% rechazo", f"{porcentaje(tot_rech, tot_env)} %")]
    return Reporte("rechazos", "Muestras rechazadas", DESCRIPCION, filtro, [t_clinica, t_motivo, t_transp],
                   _graficos(t_clinica, t_motivo), indicadores)


class _ConsultaRechazos:
    """Las tres consultas del reporte comparten el mismo FROM (remitos despachados en el período, con su
    envío, su recepción y la cantidad de muestras) y los mismos filtros; cambian las columnas y el GROUP BY."""

    def __init__(self, filtro: Filtro):
        self.filtro = filtro
        self.muestras_por_remito = (select(MuestraBiologica.remito_id, func.count(MuestraBiologica.id).label("n"))
                                    .where(MuestraBiologica.remito_id.is_not(None))
                                    .group_by(MuestraBiologica.remito_id).subquery())
        self.rechazado = RecepcionRemito.resultado == ResultadoRecepcion.RECHAZADA
        self.motivo = case((RecepcionRemito.estado_precinto_observado == EstadoPrecinto.ROTO, MOTIVO_PRECINTO),
                           else_=MOTIVO_TEMPERATURA)
        self.enviadas = func.sum(self.muestras_por_remito.c.n)
        self.rechazadas = func.sum(case((self.rechazado, self.muestras_por_remito.c.n), else_=0))

    def por_clinica(self):
        return (self._base(Clinica.nombre, self.enviadas.label("env"), self.rechazadas.label("rech"))
                .group_by(Clinica.nombre).order_by(Clinica.nombre))

    def por_transportista(self):
        return (self._base(Envio.transportista, self.enviadas.label("env"), self.rechazadas.label("rech"))
                .group_by(Envio.transportista).order_by(Envio.transportista))

    def por_motivo(self):
        return (self._base(self.motivo.label("motivo"), func.count(RemitoBiologico.id).label("remitos"),
                           func.sum(self.muestras_por_remito.c.n).label("muestras"))
                .where(self.rechazado).group_by(self.motivo).order_by(self.motivo))

    def _base(self, *columnas):
        stmt = (select(*columnas)
                .select_from(RemitoBiologico)
                .join(Envio, Envio.remito_id == RemitoBiologico.id)
                .join(self.muestras_por_remito, self.muestras_por_remito.c.remito_id == RemitoBiologico.id)
                .outerjoin(RecepcionRemito, RecepcionRemito.remito_id == RemitoBiologico.id)
                .join(Clinica, Clinica.id == RemitoBiologico.clinica_origen_id)
                .where(self.filtro.en_rango(Envio.fecha_hora_despacho)))
        return self.filtro.aplicar(stmt, clinica=RemitoBiologico.clinica_origen_id,
                                   laboratorio=RemitoBiologico.laboratorio_id)


def _tabla_por_clinica(por_clinica) -> Tabla:
    tabla = Tabla("Por clínica de origen", ["Clínica", "Muestras enviadas", "Rechazadas", "% rechazo"],
                  [[f.nombre, int(f.env), int(f.rech), porcentaje(f.rech, f.env)] for f in por_clinica])
    if tabla.filas:
        tot_env = sum(int(f.env) for f in por_clinica)
        tot_rech = sum(int(f.rech) for f in por_clinica)
        tabla.totales = ["Total", tot_env, tot_rech, porcentaje(tot_rech, tot_env)]
    return tabla


def _graficos(t_clinica: Tabla, t_motivo: Tabla) -> list[Grafico]:
    return [
        Grafico("Muestras enviadas vs rechazadas por clínica", "bar", t_clinica.columna(0), [
            serie("Enviadas", t_clinica.columna(1), PALETA[3]),
            serie("Rechazadas", t_clinica.columna(2), PALETA[4])]),
        Grafico("Rechazos por motivo", "doughnut", t_motivo.columna(0), [
            serie("Muestras", t_motivo.columna(2), [PALETA[4], PALETA[2]])]),
    ]

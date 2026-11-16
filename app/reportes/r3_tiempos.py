"""Reporte: Tiempo promedio de tránsito y de procesamiento de muestras (en horas)."""
from __future__ import annotations

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, aliased

from app.domain.clinica import Clinica
from app.domain.estados.estado_muestra import Analizada, Recibida
from app.domain.laboratorio import OrdenDerivacion, TipoAnalisis, orden_analisis
from app.domain.muestra import HistorialEstadoMuestraFila, MuestraBiologica
from app.domain.transporte import Envio, RemitoBiologico
from app.reportes.comun import PALETA, Filtro, Grafico, Reporte, Tabla, horas, serie

DESCRIPCION = ("Tránsito = llegada real − despacho del envío. Procesamiento = momento en que la muestra quedó "
               "Analizada − momento en que quedó Recibida (tomado del historial inmutable).")


def generar(s: Session, filtro: Filtro) -> Reporte:
    filas_t = s.execute(_consulta_transito(filtro)).all()
    filas_p = s.execute(_consulta_procesamiento(filtro)).all()
    t_transito = Tabla("Tránsito (despacho → llegada) por clínica de origen",
                       ["Clínica de origen", "Envíos", "Promedio (h)", "Mínimo (h)", "Máximo (h)"],
                       [[f.nombre, f.n, _r(f.prom), _r(f.min), _r(f.max)] for f in filas_t])
    t_proceso = Tabla("Procesamiento en laboratorio (recibida → analizada) por tipo de análisis",
                      ["Tipo de análisis", "Muestras", "Promedio (h)", "Mínimo (h)", "Máximo (h)", "Estimado (h)"],
                      [[f.nombre, f.n, _r(f.prom), _r(f.min), _r(f.max), f.tiempo_estimado_horas] for f in filas_p])
    prom_transito, prom_proceso = _promedio_ponderado(filas_t), _promedio_ponderado(filas_p)
    indicadores = [("Envíos recibidos", str(sum(f.n for f in filas_t))),
                   ("Tránsito promedio", f"{_r(prom_transito) if prom_transito is not None else '-'} h"),
                   ("Procesamiento promedio", f"{_r(prom_proceso) if prom_proceso is not None else '-'} h")]
    return Reporte("tiempos", "Tiempos de tránsito", DESCRIPCION, filtro, [t_transito, t_proceso],
                   _graficos(t_transito, t_proceso), indicadores)


def _consulta_transito(filtro: Filtro):
    """Llegada real − despacho de cada envío, agrupado por clínica de origen."""
    transito = horas(Envio.fecha_hora_llegada_real, Envio.fecha_hora_despacho)
    stmt = (select(Clinica.nombre, func.count(Envio.id).label("n"), func.avg(transito).label("prom"),
                   func.min(transito).label("min"), func.max(transito).label("max"))
            .join(RemitoBiologico, Envio.remito_id == RemitoBiologico.id)
            .join(Clinica, Clinica.id == RemitoBiologico.clinica_origen_id)
            .where(Envio.fecha_hora_llegada_real.is_not(None), filtro.en_rango(Envio.fecha_hora_llegada_real))
            .group_by(Clinica.nombre).order_by(Clinica.nombre))
    return filtro.aplicar(stmt, clinica=RemitoBiologico.clinica_origen_id,
                          laboratorio=RemitoBiologico.laboratorio_id)


def _consulta_procesamiento(filtro: Filtro):
    """fecha(Analizada) − fecha(Recibida) tomadas del historial, agrupado por tipo de análisis."""
    recibida = _primera_vez_en(Recibida.nombre)
    analizada = _primera_vez_en(Analizada.nombre)
    proceso = horas(analizada.c.f, recibida.c.f)
    stmt = (select(TipoAnalisis.nombre, TipoAnalisis.tiempo_estimado_horas,
                   func.count(MuestraBiologica.id).label("n"), func.avg(proceso).label("prom"),
                   func.min(proceso).label("min"), func.max(proceso).label("max"))
            .select_from(MuestraBiologica)
            .join(recibida, recibida.c.muestra_id == MuestraBiologica.id)
            .join(analizada, analizada.c.muestra_id == MuestraBiologica.id)
            .join(OrdenDerivacion, OrdenDerivacion.id == MuestraBiologica.orden_id)
            .join(orden_analisis, orden_analisis.c.orden_id == OrdenDerivacion.id)
            .join(TipoAnalisis, and_(TipoAnalisis.id == orden_analisis.c.tipo_analisis_id,
                                     TipoAnalisis.tipo_muestra_requerida == MuestraBiologica.tipo))
            .join(RemitoBiologico, RemitoBiologico.id == MuestraBiologica.remito_id)
            .where(analizada.c.f >= filtro.inicio, analizada.c.f < filtro.fin)
            .group_by(TipoAnalisis.nombre, TipoAnalisis.tiempo_estimado_horas).order_by(TipoAnalisis.nombre))
    return filtro.aplicar(stmt, clinica=RemitoBiologico.clinica_origen_id,
                          laboratorio=OrdenDerivacion.laboratorio_id)


def _primera_vez_en(nombre_estado: str):
    """Subconsulta (muestra_id, f): cuándo entró cada muestra por primera vez al estado indicado."""
    h = aliased(HistorialEstadoMuestraFila)
    return (select(h.muestra_id, func.min(h.fecha_hora).label("f"))
            .where(h.estado_nuevo == nombre_estado).group_by(h.muestra_id).subquery())


def _graficos(t_transito: Tabla, t_proceso: Tabla) -> list[Grafico]:
    return [
        Grafico("Tránsito promedio por clínica (h)", "bar", t_transito.columna(0), [
            serie("Promedio (h)", t_transito.columna(2), PALETA[2]),
            serie("Máximo (h)", t_transito.columna(4), PALETA[4])]),
        Grafico("Procesamiento promedio por análisis (h)", "bar", t_proceso.columna(0), [
            serie("Promedio (h)", t_proceso.columna(2), PALETA[1]),
            serie("Estimado (h)", t_proceso.columna(5), PALETA[5])], horizontal=True),
    ]


def _promedio_ponderado(filas) -> float | None:
    """Promedio general a partir de los promedios por grupo, ponderados por la cantidad de cada grupo."""
    total = sum(f.n for f in filas)
    return (sum((f.prom or 0) * f.n for f in filas) / total) if total else None


def _r(valor):
    return round(float(valor), 1) if valor is not None else None

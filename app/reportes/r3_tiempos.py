"""Reporte: Tiempo promedio de tránsito y de procesamiento de muestras (en horas)."""
from __future__ import annotations

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, aliased

from app.domain.clinica import Clinica
from app.domain.estados.estado_muestra import Analizada, Recibida
from app.domain.laboratorio import OrdenDerivacion, TipoAnalisis, orden_analisis
from app.domain.muestra import HistorialEstadoMuestraFila, MuestraBiologica
from app.domain.transporte import Envio, RemitoBiologico
from app.reportes.comun import PALETA, Filtro, Grafico, Reporte, Tabla, horas


def _r(valor):
    return round(float(valor), 1) if valor is not None else None


def generar(s: Session, filtro: Filtro) -> Reporte:
    # --- tránsito: llegada real − despacho, por clínica de origen ---------------------
    transito = horas(Envio.fecha_hora_llegada_real, Envio.fecha_hora_despacho)
    stmt_t = (select(Clinica.nombre, func.count(Envio.id).label("n"), func.avg(transito).label("prom"),
                     func.min(transito).label("min"), func.max(transito).label("max"))
              .join(RemitoBiologico, Envio.remito_id == RemitoBiologico.id)
              .join(Clinica, Clinica.id == RemitoBiologico.clinica_origen_id)
              .where(Envio.fecha_hora_llegada_real.is_not(None), filtro.en_rango(Envio.fecha_hora_llegada_real))
              .group_by(Clinica.nombre).order_by(Clinica.nombre))
    if filtro.clinica_id:
        stmt_t = stmt_t.where(RemitoBiologico.clinica_origen_id == filtro.clinica_id)
    if filtro.laboratorio_id:
        stmt_t = stmt_t.where(RemitoBiologico.laboratorio_id == filtro.laboratorio_id)
    filas_t = s.execute(stmt_t).all()
    t_transito = Tabla("Tránsito (despacho → llegada) por clínica de origen",
                       ["Clínica de origen", "Envíos", "Promedio (h)", "Mínimo (h)", "Máximo (h)"],
                       [[f.nombre, f.n, _r(f.prom), _r(f.min), _r(f.max)] for f in filas_t])

    # --- procesamiento: fecha(Analizada) − fecha(Recibida) desde el historial -----------
    h_rec = aliased(HistorialEstadoMuestraFila)
    h_ana = aliased(HistorialEstadoMuestraFila)
    recibida = (select(h_rec.muestra_id, func.min(h_rec.fecha_hora).label("f"))
                .where(h_rec.estado_nuevo == Recibida.nombre).group_by(h_rec.muestra_id).subquery())
    analizada = (select(h_ana.muestra_id, func.min(h_ana.fecha_hora).label("f"))
                 .where(h_ana.estado_nuevo == Analizada.nombre).group_by(h_ana.muestra_id).subquery())
    proceso = horas(analizada.c.f, recibida.c.f)
    stmt_p = (select(TipoAnalisis.nombre, TipoAnalisis.tiempo_estimado_horas,
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
    if filtro.clinica_id:
        stmt_p = stmt_p.where(RemitoBiologico.clinica_origen_id == filtro.clinica_id)
    if filtro.laboratorio_id:
        stmt_p = stmt_p.where(OrdenDerivacion.laboratorio_id == filtro.laboratorio_id)
    filas_p = s.execute(stmt_p).all()
    t_proceso = Tabla("Procesamiento en laboratorio (recibida → analizada) por tipo de análisis",
                      ["Tipo de análisis", "Muestras", "Promedio (h)", "Mínimo (h)", "Máximo (h)", "Estimado (h)"],
                      [[f.nombre, f.n, _r(f.prom), _r(f.min), _r(f.max), f.tiempo_estimado_horas] for f in filas_p])

    graficos = [
        Grafico("Tránsito promedio por clínica (h)", "bar", [f[0] for f in t_transito.filas], [
            {"label": "Promedio (h)", "data": [f[2] for f in t_transito.filas], "backgroundColor": PALETA[2]},
            {"label": "Máximo (h)", "data": [f[4] for f in t_transito.filas], "backgroundColor": PALETA[4]}]),
        Grafico("Procesamiento promedio por análisis (h)", "bar", [f[0] for f in t_proceso.filas], [
            {"label": "Promedio (h)", "data": [f[2] for f in t_proceso.filas], "backgroundColor": PALETA[1]},
            {"label": "Estimado (h)", "data": [f[5] for f in t_proceso.filas], "backgroundColor": PALETA[5]}],
            horizontal=True),
    ]
    total_envios = sum(f.n for f in filas_t)
    prom_transito = (sum((f.prom or 0) * f.n for f in filas_t) / total_envios) if total_envios else None
    total_proc = sum(f.n for f in filas_p)
    prom_proc = (sum((f.prom or 0) * f.n for f in filas_p) / total_proc) if total_proc else None
    indicadores = [("Envíos recibidos", str(total_envios)),
                   ("Tránsito promedio", f"{_r(prom_transito) if prom_transito is not None else '-'} h"),
                   ("Procesamiento promedio", f"{_r(prom_proc) if prom_proc is not None else '-'} h")]
    return Reporte("tiempos", "Tiempos de tránsito",
                   "Tránsito = llegada real − despacho del envío. Procesamiento = momento en que la muestra quedó "
                   "Analizada − momento en que quedó Recibida (tomado del historial inmutable).",
                   filtro, [t_transito, t_proceso], graficos, indicadores)

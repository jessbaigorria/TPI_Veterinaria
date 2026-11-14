"""KPIs de la pantalla de inicio de cada portal (consultas agregadas de solo lectura)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta

from sqlalchemy import func, or_, select

from app.domain import reloj
from app.domain.atencion import AtencionClinica, DerivacionCirugia
from app.domain.enums import EstadoAtencion, EstadoDerivacionCirugia
from app.domain.estados.estado_muestra import Analizada, Extraida, Recibida, Rechazada
from app.domain.estados.estado_remito import RemitoArmado, RemitoDespachado, RemitoEnTransito
from app.domain.laboratorio import HistorialEstadoMuestraFila, MuestraBiologica, OrdenDerivacion, ResultadoAnalisis
from app.domain.transporte import Envio, RemitoBiologico
from app.reportes.comun import horas
from app.services.base import ServicioBase


@dataclass
class Kpi:
    titulo: str
    valor: str | int
    icono: str
    color: str
    enlace: str = ""
    alerta: bool = False


class TablerosService(ServicioBase):
    def _hoy(self):
        inicio = datetime.combine(reloj.hoy(), time.min)
        return inicio, inicio + timedelta(days=1)

    def kpis_clinica(self, clinica_id: int) -> list[Kpi]:
        cid = int(clinica_id)
        s = self.s
        ini, fin = self._hoy()
        hace7 = reloj.ahora() - timedelta(days=7)
        de_clinica = (select(MuestraBiologica.id).join(MuestraBiologica.orden).join(OrdenDerivacion.atencion)
                      .where(AtencionClinica.clinica_id == cid))
        turnos = s.scalar(select(func.count(AtencionClinica.id)).where(
            AtencionClinica.clinica_id == cid, AtencionClinica.fecha_hora_inicio >= ini,
            AtencionClinica.fecha_hora_inicio < fin, AtencionClinica.estado != EstadoAtencion.CANCELADA))
        en_curso = s.scalar(select(func.count(AtencionClinica.id)).where(
            AtencionClinica.clinica_id == cid, AtencionClinica.estado == EstadoAtencion.EN_PROGRESO))
        extraidas = s.scalar(select(func.count()).select_from(
            de_clinica.where(MuestraBiologica.estado_codigo == Extraida.__name__).subquery()))
        armados = s.scalar(select(func.count(RemitoBiologico.id)).where(
            RemitoBiologico.clinica_origen_id == cid, RemitoBiologico.estado_codigo == RemitoArmado.__name__))
        en_transito = s.scalar(select(func.count(RemitoBiologico.id)).where(
            RemitoBiologico.clinica_origen_id == cid,
            RemitoBiologico.estado_codigo.in_([RemitoDespachado.__name__, RemitoEnTransito.__name__])))
        rechazadas = s.scalar(select(func.count(HistorialEstadoMuestraFila.id)).where(
            HistorialEstadoMuestraFila.estado_nuevo == Rechazada.nombre, HistorialEstadoMuestraFila.fecha_hora >= hace7,
            HistorialEstadoMuestraFila.muestra_id.in_(de_clinica)))
        resultados = s.scalar(select(func.count(ResultadoAnalisis.id)).where(
            ResultadoAnalisis.fecha_hora >= hace7, ResultadoAnalisis.muestra_id.in_(de_clinica)))
        abiertas = [EstadoDerivacionCirugia.SOLICITADA, EstadoDerivacionCirugia.ACEPTADA,
                    EstadoDerivacionCirugia.PROGRAMADA]
        cirugias = s.scalar(select(func.count(DerivacionCirugia.id)).join(DerivacionCirugia.atencion).where(
            DerivacionCirugia.estado.in_(abiertas),
            or_(AtencionClinica.clinica_id == cid, DerivacionCirugia.destino_id == cid)))
        return [
            Kpi("Turnos de hoy", turnos, "calendar-check", "teal", "/clinica/agenda"),
            Kpi("Atenciones en curso", en_curso, "heart-pulse", "primary", "/clinica/atenciones?estado=EN_PROGRESO"),
            Kpi("Muestras sin empaquetar", extraidas, "droplet-half", "secondary", "/clinica/envios/nuevo"),
            Kpi("Remitos armados", armados, "box-seam", "secondary", "/clinica/envios?estado=RemitoArmado"),
            Kpi("Remitos en camino", en_transito, "truck", "warning", "/clinica/envios?estado=RemitoEnTransito"),
            Kpi("Rechazadas (7 días)", rechazadas, "exclamation-octagon", "danger",
                "/clinica/ordenes", alerta=bool(rechazadas)),
            Kpi("Resultados nuevos (7 días)", resultados, "clipboard2-pulse", "success", "/clinica/ordenes"),
            Kpi("Cirugías pendientes", cirugias, "bandaid", "purple", "/clinica/cirugias"),
        ]

    def kpis_laboratorio(self, laboratorio_id: int) -> list[Kpi]:
        lid = int(laboratorio_id)
        s = self.s
        ini, fin = self._hoy()
        hace7 = reloj.ahora() - timedelta(days=7)
        del_lab = select(MuestraBiologica.id).join(MuestraBiologica.orden).where(OrdenDerivacion.laboratorio_id == lid)
        en_camino = s.scalar(select(func.count(RemitoBiologico.id)).where(
            RemitoBiologico.laboratorio_id == lid,
            RemitoBiologico.estado_codigo.in_([RemitoDespachado.__name__, RemitoEnTransito.__name__])))
        pendientes = s.scalar(select(func.count()).select_from(
            del_lab.where(MuestraBiologica.estado_codigo == Recibida.__name__).subquery()))
        analizadas_hoy = s.scalar(select(func.count(HistorialEstadoMuestraFila.id)).where(
            HistorialEstadoMuestraFila.estado_nuevo == Analizada.nombre, HistorialEstadoMuestraFila.fecha_hora >= ini,
            HistorialEstadoMuestraFila.fecha_hora < fin, HistorialEstadoMuestraFila.muestra_id.in_(del_lab)))
        rechazadas = s.scalar(select(func.count(HistorialEstadoMuestraFila.id)).where(
            HistorialEstadoMuestraFila.estado_nuevo == Rechazada.nombre, HistorialEstadoMuestraFila.fecha_hora >= hace7,
            HistorialEstadoMuestraFila.muestra_id.in_(del_lab)))
        inicio_mes = datetime.combine(reloj.hoy().replace(day=1), time.min)
        promedio = s.scalar(select(func.avg(horas(Envio.fecha_hora_llegada_real, Envio.fecha_hora_despacho)))
                            .join(RemitoBiologico, RemitoBiologico.id == Envio.remito_id)
                            .where(RemitoBiologico.laboratorio_id == lid, Envio.fecha_hora_llegada_real >= inicio_mes))
        return [
            Kpi("Remitos en camino", en_camino, "truck", "warning", "/laboratorio/recepcion"),
            Kpi("Muestras por analizar", pendientes, "hourglass-split", "info", "/laboratorio/muestras"),
            Kpi("Analizadas hoy", analizadas_hoy, "check2-circle", "success", "/laboratorio/trazabilidad"),
            Kpi("Rechazadas (7 días)", rechazadas, "exclamation-octagon", "danger", "/laboratorio/recepciones",
                alerta=bool(rechazadas)),
            Kpi("Tránsito promedio (mes)", f"{promedio:.1f} h" if promedio is not None else "–", "stopwatch",
                "purple", "/laboratorio/reportes/r3"),
        ]

"""KPIs de la pantalla de inicio de cada portal (consultas agregadas de solo lectura)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta

from sqlalchemy import func, or_, select

from app.domain import reloj
from app.domain.atencion import AtencionClinica
from app.domain.cirugia import DerivacionCirugia
from app.domain.enums import EstadoAtencion, EstadoDerivacionCirugia
from app.domain.estados.estado_muestra import Analizada, Extraida, Recibida, Rechazada
from app.domain.estados.estado_remito import RemitoArmado, RemitoDespachado, RemitoEnTransito
from app.domain.laboratorio import OrdenDerivacion
from app.domain.muestra import HistorialEstadoMuestraFila, MuestraBiologica, ResultadoAnalisis
from app.domain.transporte import Envio, RemitoBiologico
from app.reportes.comun import horas
from app.services.base import ServicioBase

EN_CAMINO = [RemitoDespachado.__name__, RemitoEnTransito.__name__]
CIRUGIAS_ABIERTAS = [EstadoDerivacionCirugia.SOLICITADA, EstadoDerivacionCirugia.ACEPTADA,
                     EstadoDerivacionCirugia.PROGRAMADA]
Historial = HistorialEstadoMuestraFila


@dataclass
class Kpi:
    titulo: str
    valor: str | int
    icono: str
    color: str
    enlace: str = ""
    alerta: bool = False


class TablerosService(ServicioBase):
    # --- portal clínica --------------------------------------------------------------------
    def kpis_clinica(self, clinica_id: int) -> list[Kpi]:
        cid = int(clinica_id)
        muestras = self._muestras_de_clinica(cid)
        rechazadas = self._cambios_a_estado(Rechazada, muestras, desde=self._hace_7_dias())
        return [
            Kpi("Turnos de hoy", self._turnos_de_hoy(cid), "calendar-check", "teal", "/clinica/agenda"),
            Kpi("Atenciones en curso", self._atenciones_en_curso(cid), "heart-pulse", "primary",
                "/clinica/atenciones?estado=EN_PROGRESO"),
            Kpi("Muestras sin empaquetar", self._muestras_en_estado(muestras, Extraida), "droplet-half", "secondary",
                "/clinica/envios/nuevo"),
            Kpi("Remitos armados", self._remitos_de_clinica(cid, [RemitoArmado.__name__]), "box-seam", "secondary",
                "/clinica/envios?estado=RemitoArmado"),
            Kpi("Remitos en camino", self._remitos_de_clinica(cid, EN_CAMINO), "truck", "warning",
                "/clinica/envios?estado=RemitoEnTransito"),
            Kpi("Rechazadas (7 días)", rechazadas, "exclamation-octagon", "danger", "/clinica/ordenes",
                alerta=bool(rechazadas)),
            Kpi("Resultados nuevos (7 días)", self._resultados_recientes(muestras), "clipboard2-pulse", "success",
                "/clinica/ordenes"),
            Kpi("Cirugías pendientes", self._cirugias_pendientes(cid), "bandaid", "purple", "/clinica/cirugias"),
        ]

    def _muestras_de_clinica(self, cid: int):
        """Subconsulta con los id de las muestras extraídas en atenciones de la clínica."""
        return (select(MuestraBiologica.id).join(MuestraBiologica.orden).join(OrdenDerivacion.atencion)
                .where(AtencionClinica.clinica_id == cid))

    def _turnos_de_hoy(self, cid: int) -> int:
        inicio, fin = self._hoy()
        return self.s.scalar(select(func.count(AtencionClinica.id)).where(
            AtencionClinica.clinica_id == cid, AtencionClinica.fecha_hora_inicio >= inicio,
            AtencionClinica.fecha_hora_inicio < fin, AtencionClinica.estado != EstadoAtencion.CANCELADA))

    def _atenciones_en_curso(self, cid: int) -> int:
        return self.s.scalar(select(func.count(AtencionClinica.id)).where(
            AtencionClinica.clinica_id == cid, AtencionClinica.estado == EstadoAtencion.EN_PROGRESO))

    def _remitos_de_clinica(self, cid: int, estados: list[str]) -> int:
        return self.s.scalar(select(func.count(RemitoBiologico.id)).where(
            RemitoBiologico.clinica_origen_id == cid, RemitoBiologico.estado_codigo.in_(estados)))

    def _resultados_recientes(self, muestras) -> int:
        return self.s.scalar(select(func.count(ResultadoAnalisis.id)).where(
            ResultadoAnalisis.fecha_hora >= self._hace_7_dias(), ResultadoAnalisis.muestra_id.in_(muestras)))

    def _cirugias_pendientes(self, cid: int) -> int:
        """Derivaciones abiertas que la clínica envió o que tiene que resolver como destino."""
        return self.s.scalar(select(func.count(DerivacionCirugia.id)).join(DerivacionCirugia.atencion).where(
            DerivacionCirugia.estado.in_(CIRUGIAS_ABIERTAS),
            or_(AtencionClinica.clinica_id == cid, DerivacionCirugia.destino_id == cid)))

    # --- portal laboratorio -------------------------------------------------------------------
    def kpis_laboratorio(self, laboratorio_id: int) -> list[Kpi]:
        lid = int(laboratorio_id)
        muestras = self._muestras_de_laboratorio(lid)
        inicio, fin = self._hoy()
        rechazadas = self._cambios_a_estado(Rechazada, muestras, desde=self._hace_7_dias())
        promedio = self._transito_promedio_del_mes(lid)
        return [
            Kpi("Remitos en camino", self._remitos_hacia_laboratorio(lid), "truck", "warning",
                "/laboratorio/recepcion"),
            Kpi("Muestras por analizar", self._muestras_en_estado(muestras, Recibida), "hourglass-split", "info",
                "/laboratorio/muestras"),
            Kpi("Analizadas hoy", self._cambios_a_estado(Analizada, muestras, desde=inicio, hasta=fin),
                "check2-circle", "success", "/laboratorio/trazabilidad"),
            Kpi("Rechazadas (7 días)", rechazadas, "exclamation-octagon", "danger", "/laboratorio/recepciones",
                alerta=bool(rechazadas)),
            Kpi("Tránsito promedio (mes)", f"{promedio:.1f} h" if promedio is not None else "–", "stopwatch",
                "purple", "/laboratorio/reportes/tiempos"),
        ]

    def _muestras_de_laboratorio(self, lid: int):
        """Subconsulta con los id de las muestras derivadas al laboratorio."""
        return select(MuestraBiologica.id).join(MuestraBiologica.orden).where(OrdenDerivacion.laboratorio_id == lid)

    def _remitos_hacia_laboratorio(self, lid: int) -> int:
        return self.s.scalar(select(func.count(RemitoBiologico.id)).where(
            RemitoBiologico.laboratorio_id == lid, RemitoBiologico.estado_codigo.in_(EN_CAMINO)))

    def _transito_promedio_del_mes(self, lid: int) -> float | None:
        """Horas promedio entre despacho y llegada de los envíos recibidos desde el 1° del mes."""
        inicio_mes = datetime.combine(reloj.hoy().replace(day=1), time.min)
        return self.s.scalar(select(func.avg(horas(Envio.fecha_hora_llegada_real, Envio.fecha_hora_despacho)))
                             .join(RemitoBiologico, RemitoBiologico.id == Envio.remito_id)
                             .where(RemitoBiologico.laboratorio_id == lid, Envio.fecha_hora_llegada_real >= inicio_mes))

    # --- comunes ------------------------------------------------------------------------------
    def _muestras_en_estado(self, muestras, estado) -> int:
        """Cuántas de las ``muestras`` (subconsulta de id) están hoy en el ``estado`` indicado."""
        en_estado = muestras.where(MuestraBiologica.estado_codigo == estado.__name__)
        return self.s.scalar(select(func.count()).select_from(en_estado.subquery()))

    def _cambios_a_estado(self, estado, muestras, desde: datetime, hasta: datetime | None = None) -> int:
        """Cuántas de las ``muestras`` pasaron al ``estado`` desde ``desde`` (según el historial inmutable)."""
        stmt = select(func.count(Historial.id)).where(
            Historial.estado_nuevo == estado.nombre, Historial.fecha_hora >= desde, Historial.muestra_id.in_(muestras))
        if hasta is not None:
            stmt = stmt.where(Historial.fecha_hora < hasta)
        return self.s.scalar(stmt)

    @staticmethod
    def _hoy() -> tuple[datetime, datetime]:
        inicio = datetime.combine(reloj.hoy(), time.min)
        return inicio, inicio + timedelta(days=1)

    @staticmethod
    def _hace_7_dias() -> datetime:
        return reloj.ahora() - timedelta(days=7)

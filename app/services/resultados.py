"""Proceso 7 (parte 1): registrar resultados de análisis."""
from __future__ import annotations

from sqlalchemy import case, select

from app.domain import validaciones
from app.domain.atencion import AtencionClinica
from app.domain.estados.estado_muestra import Recibida
from app.domain.excepciones import VeterinariaError
from app.domain.laboratorio import OrdenDerivacion, TipoAnalisis
from app.domain.muestra import MuestraBiologica, ResultadoAnalisis
from app.services.base import ServicioBase, texto, transaccional


class ResultadosService(ServicioBase):
    @transaccional
    def cargar_resultados(self, muestra_id, resultados: list[dict], analista) -> MuestraBiologica:
        """Un bloque por análisis compatible con el tipo de muestra; al completar todos → Analizada.
        Si la muestra está Rechazada, el dominio lanza MuestraRechazadaError.
        ``analista``: persona que carga los resultados (solo letras)."""
        usuario = validaciones.nombre_persona(analista, "Analista")
        muestra = self.obtener(MuestraBiologica, muestra_id)
        cargados = [d for d in resultados if texto(d.get("valores"))]
        if not cargados:
            # Igual se le pide al dominio, para que una muestra rechazada informe su error real.
            pendientes = muestra.analisis_pendientes() or muestra.analisis_requeridos()
            muestra.registrar_resultado(ResultadoAnalisis(pendientes[0], ""), usuario)
            raise VeterinariaError("Cargá al menos un resultado.")
        for d in cargados:
            r = ResultadoAnalisis(self.obtener(TipoAnalisis, d["tipo_analisis_id"]), texto(d.get("valores")),
                                  texto(d.get("unidad")), texto(d.get("valores_referencia")),
                                  texto(d.get("interpretacion")), analista=usuario)
            muestra.registrar_resultado(r, usuario)
        return muestra

    def cola_de_analisis(self, laboratorio_id) -> list[MuestraBiologica]:
        """Muestras Recibidas del laboratorio: URGENTE primero y luego por antigüedad."""
        urgente_primero = case((OrdenDerivacion.prioridad == "URGENTE", 0), else_=1)
        stmt = (select(MuestraBiologica).join(MuestraBiologica.orden)
                .where(OrdenDerivacion.laboratorio_id == int(laboratorio_id),
                       MuestraBiologica.estado_codigo == Recibida.__name__)
                .order_by(urgente_primero, MuestraBiologica.fecha_hora_extraccion))
        return list(self.s.scalars(stmt))

    def resultados_recientes(self, clinica_id, limite=10) -> list[ResultadoAnalisis]:
        stmt = (select(ResultadoAnalisis).join(ResultadoAnalisis.muestra).join(MuestraBiologica.orden)
                .join(OrdenDerivacion.atencion).where(AtencionClinica.clinica_id == int(clinica_id))
                .order_by(ResultadoAnalisis.fecha_hora.desc()).limit(limite))
        return list(self.s.scalars(stmt))

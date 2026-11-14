"""Proceso 3 (parte 2): emitir órdenes de derivación de laboratorio y registrar muestras."""
from __future__ import annotations

from sqlalchemy import select

from app.domain.atencion import AtencionClinica
from app.domain.enums import EstadoOrden, Prioridad, TipoMuestra
from app.domain.laboratorio import Laboratorio, MuestraBiologica, OrdenDerivacion, TipoAnalisis
from app.repositories.numerador import Numerador
from app.services.base import ServicioBase, a_float, texto, transaccional


class DerivacionesService(ServicioBase):
    @transaccional
    def emitir_orden(self, atencion_id, laboratorio_id, analisis_ids, prioridad=Prioridad.NORMAL,
                     observaciones="") -> OrdenDerivacion:
        atencion = self.obtener(AtencionClinica, atencion_id)
        analisis = [self.obtener(TipoAnalisis, i) for i in (analisis_ids or [])]
        orden = atencion.emitir_orden_derivacion(self.repo(Laboratorio).obtener_opcional(laboratorio_id),
                                                 analisis, Prioridad(prioridad or Prioridad.NORMAL),
                                                 texto(observaciones),
                                                 numero=self.numerador.siguiente(Numerador.ORDEN))
        self.s.add(orden)
        return orden

    @transaccional
    def registrar_muestra(self, orden_id, tipo, volumen, usuario, observaciones="") -> MuestraBiologica:
        orden = self.obtener(OrdenDerivacion, orden_id)
        muestra = orden.registrar_muestra(TipoMuestra(tipo), a_float(volumen, "volumen"), usuario,
                                          codigo=self.numerador.siguiente(Numerador.MUESTRA),
                                          observaciones=texto(observaciones))
        return muestra

    @transaccional
    def anular_orden(self, orden_id, motivo) -> OrdenDerivacion:
        orden = self.obtener(OrdenDerivacion, orden_id)
        orden.anular(texto(motivo))
        return orden

    # --- consultas --------------------------------------------------------------------
    def obtener_orden(self, orden_id) -> OrdenDerivacion:
        return self.obtener(OrdenDerivacion, orden_id)

    def obtener_muestra(self, muestra_id) -> MuestraBiologica:
        return self.obtener(MuestraBiologica, muestra_id)

    def buscar_muestra_por_codigo(self, codigo: str) -> MuestraBiologica | None:
        return self.s.scalars(select(MuestraBiologica).where(MuestraBiologica.codigo == codigo.strip().upper())).first()

    def listar_ordenes(self, clinica_id=None, estado: str = "", q: str = "") -> list[OrdenDerivacion]:
        stmt = select(OrdenDerivacion).join(OrdenDerivacion.atencion)
        if clinica_id:
            stmt = stmt.where(AtencionClinica.clinica_id == int(clinica_id))
        if estado:
            stmt = stmt.where(OrdenDerivacion.estado == EstadoOrden(estado))
        if q:
            stmt = stmt.where(OrdenDerivacion.numero.like(f"%{q.strip()}%"))
        return list(self.s.scalars(stmt.order_by(OrdenDerivacion.fecha_emision.desc())))

    def laboratorios(self) -> list[Laboratorio]:
        return list(self.s.scalars(select(Laboratorio).where(Laboratorio.activo.is_(True)).order_by(Laboratorio.nombre)))

    def tipos_analisis(self) -> list[TipoAnalisis]:
        return list(self.s.scalars(select(TipoAnalisis).order_by(TipoAnalisis.nombre)))

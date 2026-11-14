"""Proceso 7 (parte 2): emitir comprobantes de atención, laboratorio y cirugía; pagos y anulaciones."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from app.domain.atencion import AtencionClinica, DerivacionCirugia
from app.domain.enums import EstadoAtencion, EstadoDerivacionCirugia, EstadoOrden, FormaPago
from app.domain.facturacion import Factura
from app.domain.laboratorio import OrdenDerivacion
from app.repositories.numerador import Numerador
from app.services.base import ServicioBase, transaccional


@dataclass
class Pendientes:
    atenciones: list[AtencionClinica]
    ordenes: list[OrdenDerivacion]
    cirugias: list[DerivacionCirugia]

    @property
    def total(self) -> int:
        return len(self.atenciones) + len(self.ordenes) + len(self.cirugias)


class FacturacionService(ServicioBase):
    @transaccional
    def facturar_atencion(self, atencion_id) -> Factura:
        a = self.obtener(AtencionClinica, atencion_id)
        f = a.emitir_comprobante_atencion(numero=self.numerador.siguiente(Numerador.FACTURA))
        self.s.add(f)
        return f

    @transaccional
    def facturar_orden(self, orden_id) -> Factura:
        o = self.obtener(OrdenDerivacion, orden_id)
        f = o.emitir_comprobante(numero=self.numerador.siguiente(Numerador.FACTURA))
        self.s.add(f)
        return f

    @transaccional
    def facturar_cirugia(self, derivacion_id, importe) -> Factura:
        d = self.obtener(DerivacionCirugia, derivacion_id)
        f = d.emitir_comprobante(importe, numero=self.numerador.siguiente(Numerador.FACTURA))
        self.s.add(f)
        return f

    @transaccional
    def registrar_pago(self, factura_id, forma_pago) -> Factura:
        f = self.obtener(Factura, factura_id)
        f.registrar_pago(FormaPago(forma_pago) if forma_pago else None)
        return f

    @transaccional
    def anular(self, factura_id) -> Factura:
        f = self.obtener(Factura, factura_id)
        f.anular()
        return f

    # --- consultas --------------------------------------------------------------------
    def pendientes(self, clinica_id) -> Pendientes:
        cid = int(clinica_id)
        atenciones = self.s.scalars(
            select(AtencionClinica).where(AtencionClinica.clinica_id == cid,
                                          AtencionClinica.estado == EstadoAtencion.FINALIZADA,
                                          AtencionClinica.importe > 0)
            .order_by(AtencionClinica.fecha_hora_inicio.desc()))
        ordenes = self.s.scalars(
            select(OrdenDerivacion).join(OrdenDerivacion.atencion)
            .where(AtencionClinica.clinica_id == cid, OrdenDerivacion.estado == EstadoOrden.COMPLETADA)
            .order_by(OrdenDerivacion.fecha_emision.desc()))
        cirugias = self.s.scalars(
            select(DerivacionCirugia).where(DerivacionCirugia.destino_id == cid,
                                            DerivacionCirugia.estado == EstadoDerivacionCirugia.REALIZADA))
        return Pendientes(
            atenciones=[a for a in atenciones if not a.tiene_factura_vigente()],
            ordenes=[o for o in ordenes if not o.tiene_factura_vigente() and o.resultados()],
            cirugias=[d for d in cirugias if not d.tiene_factura_vigente()],
        )

    def listar(self, clinica_id=None, estado: str = "", tipo: str = "") -> list[Factura]:
        stmt = select(Factura)
        if clinica_id:
            stmt = stmt.where(Factura.clinica_id == int(clinica_id))
        if estado:
            stmt = stmt.where(Factura.estado == estado)
        if tipo:
            stmt = stmt.where(Factura.tipo == tipo)
        return list(self.s.scalars(stmt.order_by(Factura.fecha_emision.desc())))

    def obtener_factura(self, factura_id) -> Factura:
        return self.obtener(Factura, factura_id)

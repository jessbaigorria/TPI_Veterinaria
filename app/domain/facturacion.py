"""Facturación: Factura (comprobante), ItemFactura y ConFacturas (lo que comparten las entidades facturables)."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain import reloj
from app.domain.base import Base, Dinero, EnumCol, a_decimal
from app.domain.enums import EstadoFactura, FormaPago, TipoComprobante
from app.domain.excepciones import VeterinariaError

if TYPE_CHECKING:  # pragma: no cover
    from app.domain.atencion import AtencionClinica
    from app.domain.cirugia import DerivacionCirugia
    from app.domain.clinica import Clinica
    from app.domain.laboratorio import OrdenDerivacion, TipoAnalisis
    from app.domain.personas import Titular


class ConFacturas:
    """Comportamiento común de lo que se factura (atención, orden de derivación y cirugía).

    La clase que lo usa debe tener la relación ``facturas``. Una factura anulada no cuenta:
    después de anularla se puede volver a facturar.
    """

    def factura_vigente(self) -> "Factura | None":
        return next((f for f in self.facturas if f.estado is not EstadoFactura.ANULADA), None)

    def tiene_factura_vigente(self) -> bool:
        return self.factura_vigente() is not None

    def _validar_sin_factura_vigente(self, mensaje: str) -> None:
        """Impide facturar dos veces: ``mensaje`` describe qué ya fue facturado."""
        vigente = self.factura_vigente()
        if vigente is not None:
            raise VeterinariaError(f"{mensaje} ({vigente.numero}).")


class Factura(Base):
    __tablename__ = "factura"

    _TRANSICIONES = {
        EstadoFactura.EMITIDA: {EstadoFactura.PAGADA, EstadoFactura.ANULADA},
        EstadoFactura.PAGADA: set(),
        EstadoFactura.ANULADA: set(),
    }

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[Optional[str]] = mapped_column(String(20), unique=True)
    fecha_emision: Mapped[datetime] = mapped_column(DateTime, index=True)
    tipo: Mapped[TipoComprobante] = mapped_column(EnumCol(TipoComprobante))
    total: Mapped[Decimal] = mapped_column(Dinero, default=Decimal("0"))
    forma_pago: Mapped[Optional[FormaPago]] = mapped_column(EnumCol(FormaPago), nullable=True)
    estado: Mapped[EstadoFactura] = mapped_column(EnumCol(EstadoFactura))
    fecha_pago: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    titular_id: Mapped[int] = mapped_column(ForeignKey("titular.id"), nullable=False)
    clinica_id: Mapped[int] = mapped_column(ForeignKey("clinica.id"), nullable=False)
    atencion_id: Mapped[Optional[int]] = mapped_column(ForeignKey("atencion_clinica.id"), nullable=True)
    orden_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orden_derivacion.id"), nullable=True)
    derivacion_id: Mapped[Optional[int]] = mapped_column(ForeignKey("derivacion_cirugia.id"), nullable=True)

    items: Mapped[list["ItemFactura"]] = relationship(back_populates="factura", cascade="all, delete-orphan",
                                                      order_by="ItemFactura.id")
    titular: Mapped["Titular"] = relationship(back_populates="facturas")
    clinica: Mapped["Clinica"] = relationship()
    atencion: Mapped[Optional["AtencionClinica"]] = relationship(back_populates="facturas")
    orden: Mapped[Optional["OrdenDerivacion"]] = relationship(back_populates="facturas")
    derivacion: Mapped[Optional["DerivacionCirugia"]] = relationship(back_populates="facturas")

    def __init__(self, tipo: TipoComprobante, titular: "Titular", clinica: "Clinica",
                 numero: str | None = None, atencion=None, orden=None, derivacion=None):
        if titular is None or clinica is None:
            raise VeterinariaError("La factura necesita titular y clínica emisora.")
        self.numero = numero
        self.fecha_emision = reloj.ahora()
        self.tipo = TipoComprobante(tipo)
        self.estado = EstadoFactura.EMITIDA
        self.total = Decimal("0")
        self.titular = titular
        self.clinica = clinica
        self.atencion = atencion
        self.orden = orden
        self.derivacion = derivacion

    def agregar_item(self, descripcion: str, cantidad: int, precio, tipo_analisis: "TipoAnalisis | None" = None
                     ) -> "ItemFactura":
        self._validar_transicion_posible("modificar")
        item = ItemFactura(descripcion=descripcion, cantidad=cantidad, precio_unitario=precio,
                           tipo_analisis=tipo_analisis)
        self.items.append(item)
        return item

    def calcular_total(self) -> Decimal:
        if not self.items:
            raise VeterinariaError("La factura debe tener al menos un ítem.")
        self.total = sum((i.subtotal() for i in self.items), Decimal("0.00"))
        return self.total

    def registrar_pago(self, f: FormaPago) -> None:
        self._validar_transicion(EstadoFactura.PAGADA)
        if not f:
            raise VeterinariaError("Hay que indicar la forma de pago.")
        self.forma_pago = FormaPago(f)
        self.fecha_pago = reloj.ahora()
        self.estado = EstadoFactura.PAGADA

    def anular(self) -> None:
        self._validar_transicion(EstadoFactura.ANULADA)
        self.estado = EstadoFactura.ANULADA

    def transiciones_posibles(self) -> set[EstadoFactura]:
        return set(self._TRANSICIONES[self.estado])

    def _validar_transicion(self, nuevo: EstadoFactura) -> None:
        if nuevo not in self._TRANSICIONES[self.estado]:
            raise VeterinariaError(
                f"La factura {self.numero} está {self.estado.etiqueta.lower()}: no puede pasar a "
                f"{nuevo.etiqueta.lower()}."
            )

    def _validar_transicion_posible(self, accion: str) -> None:
        if not self._TRANSICIONES[self.estado]:
            raise VeterinariaError(f"No se puede {accion} una factura {self.estado.etiqueta.lower()}.")


class ItemFactura(Base):
    __tablename__ = "item_factura"

    id: Mapped[int] = mapped_column(primary_key=True)
    descripcion: Mapped[str] = mapped_column(String(200))
    cantidad: Mapped[int] = mapped_column(Integer, default=1)
    precio_unitario: Mapped[Decimal] = mapped_column(Dinero)
    factura_id: Mapped[int] = mapped_column(ForeignKey("factura.id"), nullable=False)
    tipo_analisis_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tipo_analisis.id"), nullable=True)

    factura: Mapped[Factura] = relationship(back_populates="items")
    tipo_analisis: Mapped[Optional["TipoAnalisis"]] = relationship()

    def __init__(self, descripcion: str, cantidad: int, precio_unitario, tipo_analisis=None):
        if not (descripcion or "").strip():
            raise VeterinariaError("El ítem necesita una descripción.")
        cantidad = int(cantidad)
        precio = a_decimal(precio_unitario)
        if cantidad <= 0 or precio < 0:
            raise VeterinariaError("Cantidad y precio del ítem deben ser positivos.")
        self.descripcion = descripcion
        self.cantidad = cantidad
        self.precio_unitario = precio
        self.tipo_analisis = tipo_analisis

    def subtotal(self) -> Decimal:
        return (a_decimal(self.precio_unitario) * self.cantidad).quantize(Decimal("0.01"))

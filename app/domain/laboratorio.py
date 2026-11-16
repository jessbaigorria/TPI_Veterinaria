"""Derivación y laboratorio: Laboratorio, TipoAnalisis y OrdenDerivacion.

La muestra biológica (contexto del patrón State) y su historial están en ``muestra.py``.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain import reloj
from app.domain.base import Base, Dinero, EnumCol
from app.domain.enums import EstadoOrden, EstadoPrecinto, Prioridad, TipoComprobante, TipoMuestra
from app.domain.excepciones import VeterinariaError
from app.domain.facturacion import ConFacturas, Factura

if TYPE_CHECKING:  # pragma: no cover
    from app.domain.atencion import AtencionClinica
    from app.domain.clinica import Clinica
    from app.domain.muestra import MuestraBiologica, ResultadoAnalisis
    from app.domain.transporte import RecepcionRemito, RemitoBiologico


orden_analisis = Table(
    "orden_analisis",
    Base.metadata,
    Column("orden_id", ForeignKey("orden_derivacion.id"), primary_key=True),
    Column("tipo_analisis_id", ForeignKey("tipo_analisis.id"), primary_key=True),
)


class TipoAnalisis(Base):
    __tablename__ = "tipo_analisis"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True)
    nombre: Mapped[str] = mapped_column(String(120))
    descripcion: Mapped[str] = mapped_column(Text, default="")
    precio: Mapped[Decimal] = mapped_column(Dinero)
    tipo_muestra_requerida: Mapped[TipoMuestra] = mapped_column(EnumCol(TipoMuestra))
    temperatura_min: Mapped[float] = mapped_column(Float, default=2.0)
    temperatura_max: Mapped[float] = mapped_column(Float, default=8.0)
    tiempo_estimado_horas: Mapped[int] = mapped_column(Integer, default=24)

    def __repr__(self) -> str:
        return f"<TipoAnalisis {self.codigo}>"


class Laboratorio(Base):
    __tablename__ = "laboratorio"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), unique=True)
    direccion: Mapped[str] = mapped_column(String(160), default="")
    telefono: Mapped[str] = mapped_column(String(40), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    responsable: Mapped[str] = mapped_column(String(120), default="")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    def recibir_remito(self, r: "RemitoBiologico", precinto_integro: bool, temp: float, usuario: str,
                       observaciones: str = "") -> "RecepcionRemito":
        """Proceso 6: recepción con verificación del precinto y de la temperatura."""
        from app.domain.transporte import RecepcionRemito

        if r.laboratorio is not self:
            raise VeterinariaError(f"El remito {r.numero} está destinado a {r.laboratorio.nombre}.")
        if temp is None:
            raise VeterinariaError("Hay que registrar la temperatura medida al recibir.")
        recepcion = RecepcionRemito(
            estado_precinto_observado=EstadoPrecinto.INTEGRO if precinto_integro else EstadoPrecinto.ROTO,
            temperatura_recepcion=float(temp),
            usuario_receptor=usuario,
        )
        recepcion.procesar(r, observaciones=observaciones)
        return recepcion

    def __repr__(self) -> str:
        return f"<Laboratorio {self.nombre}>"


class OrdenDerivacion(ConFacturas, Base):
    __tablename__ = "orden_derivacion"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[Optional[str]] = mapped_column(String(20), unique=True)
    fecha_emision: Mapped[datetime] = mapped_column(DateTime, index=True)
    prioridad: Mapped[Prioridad] = mapped_column(EnumCol(Prioridad))
    observaciones: Mapped[str] = mapped_column(Text, default="")  # indicaciones clínicas
    estado: Mapped[EstadoOrden] = mapped_column(EnumCol(EstadoOrden))
    atencion_id: Mapped[int] = mapped_column(ForeignKey("atencion_clinica.id"), nullable=False)
    laboratorio_id: Mapped[int] = mapped_column(ForeignKey("laboratorio.id"), nullable=False)

    atencion: Mapped["AtencionClinica"] = relationship(back_populates="ordenes")
    laboratorio: Mapped[Laboratorio] = relationship()
    analisis: Mapped[list[TipoAnalisis]] = relationship(secondary=orden_analisis, order_by=TipoAnalisis.nombre)
    muestras: Mapped[list["MuestraBiologica"]] = relationship(back_populates="orden", cascade="all",
                                                              order_by="MuestraBiologica.id")
    facturas: Mapped[list[Factura]] = relationship(back_populates="orden")

    _ESTADOS_ABIERTOS = {EstadoOrden.EMITIDA, EstadoOrden.EN_PROCESO}
    _ESTADOS_CERRADOS = {EstadoOrden.COMPLETADA, EstadoOrden.ANULADA}

    def __init__(self, atencion: "AtencionClinica", laboratorio: Laboratorio,
                 prioridad: Prioridad = Prioridad.NORMAL, observaciones: str = "", numero: str | None = None):
        if laboratorio is None:
            raise VeterinariaError("Hay que elegir el laboratorio de destino.")
        if not laboratorio.activo:
            raise VeterinariaError(f"El laboratorio {laboratorio.nombre} no está activo.")
        self.numero = numero
        self.fecha_emision = reloj.ahora()
        self.prioridad = Prioridad(prioridad)
        self.observaciones = observaciones or ""
        self.estado = EstadoOrden.EMITIDA
        self.laboratorio = laboratorio
        self.atencion = atencion

    # --- navegación -------------------------------------------------------------
    @property
    def clinica(self) -> "Clinica":
        return self.atencion.clinica

    @property
    def mascota(self):
        return self.atencion.mascota

    @property
    def titular(self):
        return self.atencion.titular

    # --- métodos del diagrama -------------------------------------------------
    def agregar_analisis(self, t: TipoAnalisis) -> None:
        if self.estado is not EstadoOrden.EMITIDA or self.muestras:
            raise VeterinariaError("Solo se agregan análisis a una orden emitida sin muestras.")
        if t not in self.analisis:
            self.analisis.append(t)

    def registrar_muestra(self, tipo: TipoMuestra, volumen: float, usuario: str,
                          codigo: str | None = None, observaciones: str = "") -> "MuestraBiologica":
        """Registra la extracción: la muestra nace Extraída con su primer registro de historial."""
        from app.domain.muestra import MuestraBiologica

        if self.estado not in self._ESTADOS_ABIERTOS:
            raise VeterinariaError(f"La orden {self.numero} está {self.estado.etiqueta.lower()}.")
        tipo = TipoMuestra(tipo)
        if not self.analisis_para(tipo):
            requeridos = ", ".join(sorted({t.tipo_muestra_requerida.etiqueta for t in self.analisis}))
            raise VeterinariaError(
                f"Ningún análisis de la orden usa muestras de {tipo.etiqueta.lower()} (requiere: {requeridos})."
            )
        if any(m.tipo is tipo for m in self.muestras):
            raise VeterinariaError(f"La orden ya tiene una muestra de {tipo.etiqueta.lower()}.")
        if volumen is None or float(volumen) <= 0:
            raise VeterinariaError("El volumen de la muestra debe ser mayor que cero.")
        muestra = MuestraBiologica(tipo=tipo, volumen=float(volumen), codigo=codigo, observaciones=observaciones)
        self.muestras.append(muestra)
        muestra._nacer(usuario)
        return muestra

    def actualizar_estado(self) -> None:
        """EMITIDA → EN_PROCESO cuando alguna muestra sale; → COMPLETADA cuando todas son finales
        y están cubiertos todos los tipos de muestra que pide la orden. La invoca el observer."""
        if self.estado in self._ESTADOS_CERRADOS:
            return
        if self.muestras and all(m.estado.es_final() for m in self.muestras) and not self.tipos_sin_muestra():
            self.estado = EstadoOrden.COMPLETADA
        elif any(m.estado.fue_despachada() for m in self.muestras):
            self.estado = EstadoOrden.EN_PROCESO

    def anular(self, motivo: str) -> None:
        if self.estado in self._ESTADOS_CERRADOS:
            raise VeterinariaError(f"La orden {self.numero} ya está {self.estado.etiqueta.lower()}.")
        if any(m.remito is not None for m in self.muestras):
            raise VeterinariaError("No se puede anular: hay muestras empaquetadas o despachadas.")
        if not (motivo or "").strip():
            raise VeterinariaError("Para anular la orden hay que indicar el motivo.")
        self.observaciones = f"{self.observaciones}\nANULADA: {motivo.strip()}".strip()
        self.estado = EstadoOrden.ANULADA

    # --- auxiliares (ver DECISIONES.md) ---------------------------------------------
    def analisis_para(self, tipo: TipoMuestra) -> list[TipoAnalisis]:
        return [t for t in self.analisis if t.tipo_muestra_requerida is tipo]

    def tipos_sin_muestra(self) -> list[TipoMuestra]:
        registrados = {m.tipo for m in self.muestras}
        return sorted({t.tipo_muestra_requerida for t in self.analisis} - registrados, key=lambda x: x.value)

    def esta_abierta(self) -> bool:
        return self.estado in self._ESTADOS_ABIERTOS

    def facturable(self) -> bool:
        """Completada, con análisis realizados y sin comprobante vigente."""
        completada = self.estado is EstadoOrden.COMPLETADA
        return completada and not self.tiene_factura_vigente() and bool(self.resultados())

    def resultados(self) -> list["ResultadoAnalisis"]:
        return [r for m in self.muestras for r in m.resultados]

    def emitir_comprobante(self, numero: str | None = None) -> Factura:
        """Comprobante SERVICIO_LABORATORIO: un ítem por análisis con resultado
        (no se cobra lo rechazado por fallas de transporte)."""
        if self.estado is not EstadoOrden.COMPLETADA:
            raise VeterinariaError("Solo se facturan órdenes completadas.")
        self._validar_sin_factura_vigente("Esta orden ya fue facturada")
        resultados = self.resultados()
        if not resultados:
            raise VeterinariaError(f"La orden {self.numero} no tiene análisis realizados (muestras rechazadas): "
                                   "no hay nada para facturar.")
        factura = Factura(tipo=TipoComprobante.SERVICIO_LABORATORIO, titular=self.titular, clinica=self.clinica,
                          numero=numero, orden=self)
        for r in resultados:
            factura.agregar_item(f"{r.tipo_analisis.nombre} ({r.muestra.codigo})", 1, r.tipo_analisis.precio,
                                 r.tipo_analisis)
        factura.calcular_total()
        return factura

    def __repr__(self) -> str:
        return f"<OrdenDerivacion {self.numero} {self.estado.value}>"

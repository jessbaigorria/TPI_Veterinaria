"""Derivación y laboratorio: OrdenDerivacion, TipoAnalisis, MuestraBiologica,
HistorialEstadoMuestra (inmutable), ResultadoAnalisis y Laboratorio."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Table, Text, event
from sqlalchemy.orm import Mapped, mapped_column, reconstructor, relationship

from app.domain import reloj
from app.domain.base import Base, Dinero, EnumCol
from app.domain.enums import (
    EstadoFactura, EstadoOrden, EstadoPrecinto, Prioridad, TipoComprobante, TipoMuestra,
)
from app.domain.estados.estado_muestra import EstadoMuestra, Extraida, Rechazada
from app.domain.excepciones import TransicionInvalidaError, VeterinariaError
from app.domain.facturacion import Factura

if TYPE_CHECKING:  # pragma: no cover
    from app.domain.atencion import AtencionClinica, Clinica
    from app.domain.observadores.observadores_muestra import ObservadorMuestra
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


class OrdenDerivacion(Base):
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

    def tiene_factura_vigente(self) -> bool:
        return any(f.estado is not EstadoFactura.ANULADA for f in self.facturas)

    def facturable(self) -> bool:
        """Completada, con análisis realizados y sin comprobante vigente."""
        return self.estado is EstadoOrden.COMPLETADA and not self.tiene_factura_vigente() and bool(self.resultados())

    def resultados(self) -> list["ResultadoAnalisis"]:
        return [r for m in self.muestras for r in m.resultados]

    def emitir_comprobante(self, numero: str | None = None) -> Factura:
        """Comprobante SERVICIO_LABORATORIO: un ítem por análisis con resultado
        (no se cobra lo rechazado por fallas de transporte)."""
        if self.estado is not EstadoOrden.COMPLETADA:
            raise VeterinariaError("Solo se facturan órdenes completadas.")
        if self.tiene_factura_vigente():
            vigente = next(f for f in self.facturas if f.estado is not EstadoFactura.ANULADA)
            raise VeterinariaError(f"Esta orden ya fue facturada ({vigente.numero}).")
        resultados = self.resultados()
        if not resultados:
            raise VeterinariaError(
                f"La orden {self.numero} no tiene análisis realizados (muestras rechazadas): no hay nada para facturar."
            )
        factura = Factura(tipo=TipoComprobante.SERVICIO_LABORATORIO, titular=self.titular, clinica=self.clinica,
                          numero=numero, orden=self)
        for r in resultados:
            factura.agregar_item(f"{r.tipo_analisis.nombre} ({r.muestra.codigo})", 1, r.tipo_analisis.precio,
                                 r.tipo_analisis)
        factura.calcular_total()
        return factura

    def __repr__(self) -> str:
        return f"<OrdenDerivacion {self.numero} {self.estado.value}>"


class MuestraBiologica(Base):
    """Sujeto del patrón Observer y contexto del patrón State.

    Los métodos públicos de transición SOLO delegan en ``self._estado``.
    ``_cambiar_estado`` es el único lugar donde cambia el estado.
    """

    __tablename__ = "muestra_biologica"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[Optional[str]] = mapped_column(String(20), unique=True)
    tipo: Mapped[TipoMuestra] = mapped_column(EnumCol(TipoMuestra))
    fecha_hora_extraccion: Mapped[datetime] = mapped_column(DateTime)
    volumen: Mapped[float] = mapped_column(Float)
    observaciones: Mapped[str] = mapped_column(Text, default="")
    # El estado se persiste como string (nombre de la clase) y se rehidrata en _rehidratar_estado.
    estado_codigo: Mapped[str] = mapped_column("estado", String(40), index=True)
    orden_id: Mapped[int] = mapped_column(ForeignKey("orden_derivacion.id"), nullable=False)
    remito_id: Mapped[Optional[int]] = mapped_column(ForeignKey("remito_biologico.id"), nullable=True)

    orden: Mapped[OrdenDerivacion] = relationship(back_populates="muestras")
    remito: Mapped[Optional["RemitoBiologico"]] = relationship(back_populates="muestras")
    resultados: Mapped[list["ResultadoAnalisis"]] = relationship(
        back_populates="muestra", cascade="all", order_by="ResultadoAnalisis.id"
    )
    filas_historial: Mapped[list["HistorialEstadoMuestraFila"]] = relationship(
        back_populates="muestra", cascade="save-update, merge", order_by="HistorialEstadoMuestraFila.id"
    )

    def __init__(self, tipo: TipoMuestra, volumen: float, codigo: str | None = None, observaciones: str = ""):
        self.codigo = codigo
        self.tipo = TipoMuestra(tipo)
        self.volumen = volumen
        self.observaciones = observaciones or ""
        self.fecha_hora_extraccion = reloj.ahora()
        self._estado: EstadoMuestra | None = None  # se asigna en _nacer()

    @reconstructor
    def _rehidratar_estado(self) -> None:
        """Al cargar desde la base, reconstruye el objeto estado a partir del string."""
        self._estado = EstadoMuestra.desde_nombre(self.estado_codigo)

    # --- State: transiciones (solo delegan) -----------------------------------------
    def empaquetar(self, r: "RemitoBiologico", usuario: str) -> None:
        self._estado.empaquetar(self, r, usuario)

    def despachar(self, usuario: str) -> None:
        self._estado.despachar(self, usuario)

    def recibir(self, usuario: str) -> None:
        self._estado.recibir(self, usuario)

    def rechazar(self, motivo: str, usuario: str) -> None:
        self._estado.rechazar(self, motivo, usuario)

    def registrar_resultado(self, r: "ResultadoAnalisis", usuario: str) -> None:
        self._estado.analizar(self, r, usuario)

    @property
    def estado(self) -> EstadoMuestra:
        return self._estado

    def estado_actual(self) -> str:
        return self._estado.nombre

    def historial(self) -> tuple["HistorialEstadoMuestra", ...]:
        """Trazabilidad inmutable: tupla de dataclasses congeladas."""
        return tuple(HistorialEstadoMuestra.desde_fila(f) for f in self.filas_historial)

    # --- Observer ------------------------------------------------------------------
    def agregar_observador(self, o: "ObservadorMuestra") -> None:
        observadores = self._observadores()
        if o not in observadores:
            observadores.append(o)

    def _cambiar_estado(self, nuevo: EstadoMuestra, motivo: str, usuario: str) -> None:
        """«~cambiar_estado» del diagrama: ÚNICO lugar donde cambia el estado. Solo lo usan los estados."""
        anterior = self._estado
        self._estado = nuevo
        self.estado_codigo = nuevo.codigo
        self._notificar(anterior, nuevo, motivo, usuario)

    def _notificar(self, anterior, nuevo, motivo, usuario) -> None:
        for o in list(self._observadores()):
            o.actualizar(self, anterior, nuevo, motivo, usuario)

    def _observadores(self) -> list["ObservadorMuestra"]:
        # No persistido: vive en el __dict__ de la instancia.
        return self.__dict__.setdefault("_lista_observadores", [])

    # --- auxiliares usados por los estados ------------------------------------------
    def _nacer(self, usuario: str) -> None:
        """Primer registro del historial: — → Extraída."""
        if self._estado is not None:
            raise TransicionInvalidaError(f"La muestra {self.codigo} ya fue registrada.")
        self._cambiar_estado(Extraida(), "Extracción en consulta", usuario)

    def _agregar_resultado(self, resultado: "ResultadoAnalisis", usuario: str) -> None:
        if resultado.tipo_analisis not in self.analisis_pendientes():
            raise VeterinariaError(
                f"{resultado.tipo_analisis.nombre} no está pendiente para la muestra {self.codigo}."
            )
        if not (resultado.valores or "").strip():
            raise VeterinariaError(f"Hay que cargar los valores de {resultado.tipo_analisis.nombre}.")
        resultado.analista = resultado.analista or usuario
        self.resultados.append(resultado)

    def _validar_orden_vigente(self) -> None:
        if not self.orden.esta_abierta():
            raise VeterinariaError(f"La orden {self.orden.numero} está {self.orden.estado.etiqueta.lower()}.")

    # --- consultas -------------------------------------------------------------------
    def analisis_requeridos(self) -> list[TipoAnalisis]:
        return self.orden.analisis_para(self.tipo)

    def analisis_pendientes(self) -> list[TipoAnalisis]:
        hechos = {r.tipo_analisis for r in self.resultados}
        return [t for t in self.analisis_requeridos() if t not in hechos]

    def acciones(self) -> list[str]:
        return self._estado.acciones_disponibles()

    def motivo_rechazo(self) -> str:
        rechazos = [h for h in self.filas_historial if h.estado_nuevo == Rechazada.nombre]
        return rechazos[-1].motivo if rechazos else ""

    def fecha_de_estado(self, nombre_estado: str) -> datetime | None:
        fechas = [h.fecha_hora for h in self.filas_historial if h.estado_nuevo == nombre_estado]
        return fechas[-1] if fechas else None

    def __repr__(self) -> str:
        return f"<MuestraBiologica {self.codigo} {self.estado_codigo}>"


class HistorialEstadoMuestraFila(Base):
    """Fila persistida del historial (tabla ``historial_estado_muestra``).

    Inmutable en tres capas: (1) esta clase no permite modificar atributos una vez
    construida y el dominio expone la dataclass congelada ``HistorialEstadoMuestra``;
    (2) el repositorio solo agrega/lista y hay listeners que bloquean update/delete;
    (3) triggers de SQLite abortan UPDATE/DELETE.
    """

    __tablename__ = "historial_estado_muestra"

    id: Mapped[int] = mapped_column(primary_key=True)
    muestra_id: Mapped[int] = mapped_column(ForeignKey("muestra_biologica.id"), nullable=False, index=True)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    estado_anterior: Mapped[str] = mapped_column(String(40), nullable=False)
    estado_nuevo: Mapped[str] = mapped_column(String(40), nullable=False)
    motivo: Mapped[str] = mapped_column(Text, default="")
    usuario: Mapped[str] = mapped_column(String(120), nullable=False)

    muestra: Mapped[MuestraBiologica] = relationship(back_populates="filas_historial")

    _CAMPOS_INMUTABLES = frozenset({"fecha_hora", "estado_anterior", "estado_nuevo", "motivo", "usuario",
                                    "muestra", "muestra_id"})

    def __init__(self, muestra, fecha_hora, estado_anterior, estado_nuevo, motivo, usuario):
        object.__setattr__(self, "_construyendo", True)
        try:
            self.fecha_hora = fecha_hora
            self.estado_anterior = estado_anterior
            self.estado_nuevo = estado_nuevo
            self.motivo = motivo
            self.usuario = usuario
            self.muestra = muestra
        finally:
            object.__setattr__(self, "_construyendo", False)

    def __setattr__(self, nombre, valor):
        if nombre in self._CAMPOS_INMUTABLES and not self.__dict__.get("_construyendo", False):
            raise VeterinariaError("El historial de estados de la muestra es inmutable: no se puede modificar.")
        super().__setattr__(nombre, valor)

    def __delattr__(self, nombre):
        raise VeterinariaError("El historial de estados de la muestra es inmutable: no se puede modificar.")


@dataclass(frozen=True)
class HistorialEstadoMuestra:
    """«inmutable» del diagrama: registro de trazabilidad de solo lectura."""

    fecha_hora: datetime
    estado_anterior: str
    estado_nuevo: str
    motivo: str
    usuario: str

    @classmethod
    def desde_fila(cls, f: HistorialEstadoMuestraFila) -> "HistorialEstadoMuestra":
        return cls(f.fecha_hora, f.estado_anterior, f.estado_nuevo, f.motivo, f.usuario)


class ResultadoAnalisis(Base):
    __tablename__ = "resultado_analisis"

    id: Mapped[int] = mapped_column(primary_key=True)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime)
    valores: Mapped[str] = mapped_column(Text)
    unidad: Mapped[str] = mapped_column(String(40), default="")
    valores_referencia: Mapped[str] = mapped_column(String(200), default="")
    interpretacion: Mapped[str] = mapped_column(Text, default="")
    analista: Mapped[str] = mapped_column(String(120), default="")
    muestra_id: Mapped[int] = mapped_column(ForeignKey("muestra_biologica.id"), nullable=False)
    tipo_analisis_id: Mapped[int] = mapped_column(ForeignKey("tipo_analisis.id"), nullable=False)

    muestra: Mapped[MuestraBiologica] = relationship(back_populates="resultados")
    tipo_analisis: Mapped[TipoAnalisis] = relationship()

    def __init__(self, tipo_analisis: TipoAnalisis, valores: str, unidad: str = "", valores_referencia: str = "",
                 interpretacion: str = "", analista: str = ""):
        if tipo_analisis is None:
            raise VeterinariaError("El resultado debe indicar el tipo de análisis.")
        self.tipo_analisis = tipo_analisis
        self.valores = valores or ""
        self.unidad = unidad or ""
        self.valores_referencia = valores_referencia or ""
        self.interpretacion = interpretacion or ""
        self.analista = analista or ""
        self.fecha_hora = reloj.ahora()


@event.listens_for(MuestraBiologica, "refresh")
def _rehidratar_al_refrescar(target, context, attrs):  # pragma: no cover - por consistencia
    target._rehidratar_estado()

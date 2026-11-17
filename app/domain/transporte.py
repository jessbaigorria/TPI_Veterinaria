"""Transporte y cadena de custodia: Contenedor, RemitoBiologico, Precinto, Envio, RecepcionRemito."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, event
from sqlalchemy.orm import Mapped, mapped_column, reconstructor, relationship

from app.domain import reloj
from app.domain.base import Base, EnumCol
from app.domain.enums import EstadoContenedor, EstadoPrecinto, ResultadoRecepcion
from app.domain.estados.estado_remito import EstadoRemito, Armado
from app.domain.excepciones import TransicionInvalidaError, VeterinariaError

if TYPE_CHECKING:  # pragma: no cover
    from app.domain.clinica import Clinica
    from app.domain.laboratorio import Laboratorio
    from app.domain.muestra import MuestraBiologica


class Contenedor(Base):
    """Conservadora isotérmica."""

    __tablename__ = "contenedor"

    _TRANSICIONES = {
        EstadoContenedor.DISPONIBLE: {EstadoContenedor.EN_USO, EstadoContenedor.EN_MANTENIMIENTO},
        EstadoContenedor.EN_USO: {EstadoContenedor.DISPONIBLE},
        EstadoContenedor.EN_MANTENIMIENTO: {EstadoContenedor.DISPONIBLE},
    }

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True)
    capacidad: Mapped[int] = mapped_column(Integer)
    temperatura_min: Mapped[float] = mapped_column(Float)
    temperatura_max: Mapped[float] = mapped_column(Float)
    estado: Mapped[EstadoContenedor] = mapped_column(EnumCol(EstadoContenedor))
    clinica_id: Mapped[int] = mapped_column(ForeignKey("clinica.id"), nullable=False)

    clinica: Mapped["Clinica"] = relationship(back_populates="contenedores")

    def __init__(self, codigo: str, capacidad: int, temperatura_min: float, temperatura_max: float,
                 clinica: "Clinica", estado: EstadoContenedor = EstadoContenedor.DISPONIBLE):
        if int(capacidad) <= 0:
            raise VeterinariaError("La capacidad del contenedor debe ser positiva.")
        if float(temperatura_min) > float(temperatura_max):
            raise VeterinariaError("La temperatura mínima no puede superar a la máxima.")
        self.codigo = codigo
        self.capacidad = int(capacidad)
        self.temperatura_min = float(temperatura_min)
        self.temperatura_max = float(temperatura_max)
        self.estado = EstadoContenedor(estado)
        self.clinica = clinica

    def asignar(self) -> None:
        self._transicionar(EstadoContenedor.EN_USO, "asignar")

    def liberar(self) -> None:
        self._transicionar(EstadoContenedor.DISPONIBLE, "liberar")

    def temperatura_adecuada(self, t: float | None) -> bool:
        return t is not None and self.temperatura_min <= float(t) <= self.temperatura_max

    # auxiliares (ver DECISIONES.md)
    def enviar_a_mantenimiento(self) -> None:
        self._transicionar(EstadoContenedor.EN_MANTENIMIENTO, "enviar a mantenimiento")

    def habilitar(self) -> None:
        """Vuelve a DISPONIBLE un contenedor que estaba en mantenimiento."""
        if not self.en_mantenimiento():
            raise VeterinariaError(f"El contenedor {self.codigo} no está en mantenimiento.")
        self._transicionar(EstadoContenedor.DISPONIBLE, "habilitar")

    def en_mantenimiento(self) -> bool:
        return self.estado is EstadoContenedor.EN_MANTENIMIENTO

    def puede_ir_a_mantenimiento(self) -> bool:
        return EstadoContenedor.EN_MANTENIMIENTO in self._TRANSICIONES[self.estado]

    def esta_disponible(self) -> bool:
        return EstadoContenedor.EN_USO in self._TRANSICIONES[self.estado]

    def rango_texto(self) -> str:
        return f"{self.temperatura_min:g}–{self.temperatura_max:g} °C"

    def _transicionar(self, nuevo: EstadoContenedor, accion: str) -> None:
        if nuevo not in self._TRANSICIONES[self.estado]:
            raise VeterinariaError(
                f"No se puede {accion} el contenedor {self.codigo}: está {self.estado.etiqueta.lower()}."
            )
        self.estado = nuevo


class RemitoBiologico(Base):
    """Contexto del patrón State del remito."""

    __tablename__ = "remito_biologico"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[Optional[str]] = mapped_column(String(20), unique=True)
    fecha_emision: Mapped[datetime] = mapped_column(DateTime, index=True)
    temperatura_despacho: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    observaciones: Mapped[str] = mapped_column(Text, default="")
    usuario_armador: Mapped[str] = mapped_column(String(120))
    estado_codigo: Mapped[str] = mapped_column("estado", String(40), index=True)
    clinica_origen_id: Mapped[int] = mapped_column(ForeignKey("clinica.id"), nullable=False)
    laboratorio_id: Mapped[int] = mapped_column(ForeignKey("laboratorio.id"), nullable=False)
    contenedor_id: Mapped[int] = mapped_column(ForeignKey("contenedor.id"), nullable=False)

    clinica_origen: Mapped["Clinica"] = relationship()
    laboratorio: Mapped["Laboratorio"] = relationship()
    contenedor: Mapped[Contenedor] = relationship()
    muestras: Mapped[list["MuestraBiologica"]] = relationship(back_populates="remito",
                                                              order_by="MuestraBiologica.id")
    precinto: Mapped[Optional["Precinto"]] = relationship(back_populates="remito", uselist=False,
                                                          cascade="all, delete-orphan")
    envio: Mapped[Optional["Envio"]] = relationship(back_populates="remito", uselist=False,
                                                    cascade="all, delete-orphan")
    recepcion: Mapped[Optional["RecepcionRemito"]] = relationship(back_populates="remito", uselist=False,
                                                                  cascade="all, delete-orphan")

    def __init__(self, clinica_origen: "Clinica", laboratorio: "Laboratorio", contenedor: Contenedor,
                 usuario_armador: str, numero: str | None = None, observaciones: str = ""):
        if clinica_origen is None or laboratorio is None or contenedor is None:
            raise VeterinariaError("El remito necesita clínica de origen, laboratorio y contenedor.")
        if contenedor.clinica is not clinica_origen:
            raise VeterinariaError(f"El contenedor {contenedor.codigo} no pertenece a {clinica_origen.nombre}.")
        if not contenedor.esta_disponible():
            raise VeterinariaError(
                f"El contenedor {contenedor.codigo} está {contenedor.estado.etiqueta.lower()}: elegí otro."
            )
        if not laboratorio.activo:
            raise VeterinariaError(f"El laboratorio {laboratorio.nombre} no está activo.")
        self.numero = numero
        self.fecha_emision = reloj.ahora()
        self.observaciones = observaciones or ""
        self.usuario_armador = usuario_armador
        self.clinica_origen = clinica_origen
        self.laboratorio = laboratorio
        self.contenedor = contenedor
        self._estado = Armado()
        self.estado_codigo = self._estado.codigo

    @reconstructor
    def _rehidratar_estado(self) -> None:
        self._estado = EstadoRemito.desde_nombre(self.estado_codigo)

    # --- State: métodos del diagrama (solo delegan) ---------------------------------
    def agregar_muestra(self, m: "MuestraBiologica", usuario: str | None = None) -> None:
        self._estado.agregar_muestra(self, m, usuario or self.usuario_armador)

    def cerrar(self, p: "Precinto", temperatura_despacho: float | None = None) -> None:
        self._estado.cerrar(self, p)
        # Después de la transición: si el cierre no es válido, la temperatura medida no cambia.
        if temperatura_despacho is not None:
            self.temperatura_despacho = float(temperatura_despacho)

    def registrar_temperatura_despacho(self, temperatura: float) -> None:
        """Nueva medición de la temperatura de despacho (solo en Armado, ya precintado)."""
        self._estado.registrar_temperatura_despacho(self, temperatura)

    def despachar(self, e: "Envio", usuario: str | None = None) -> None:
        self._estado.despachar(self, e, usuario or self.usuario_armador)

    def iniciar_transito(self) -> None:
        self._estado.iniciar_transito(self)

    def recibir(self, r: "RecepcionRemito") -> None:
        self._estado.recibir(self, r)

    @property
    def estado(self) -> EstadoRemito:
        return self._estado

    def estado_actual(self) -> str:
        return self._estado.nombre

    def acciones(self) -> list[str]:
        return self._estado.acciones_disponibles(self)

    def _cambiar_estado(self, nuevo: EstadoRemito) -> None:
        """Único lugar donde cambia el estado del remito. Solo lo usan las clases de estado."""
        self._estado = nuevo
        self.estado_codigo = nuevo.codigo

    def __repr__(self) -> str:
        return f"<RemitoBiologico {self.numero} {self.estado_codigo}>"


class Precinto(Base):
    """Precinto sanitario: nace INTEGRO al cerrar el remito y se verifica una sola vez al recibir."""

    __tablename__ = "precinto"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(30), unique=True)
    fecha_colocacion: Mapped[datetime] = mapped_column(DateTime)
    estado: Mapped[EstadoPrecinto] = mapped_column(EnumCol(EstadoPrecinto))
    fecha_verificacion: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    usuario_colocador: Mapped[str] = mapped_column(String(120))
    observaciones: Mapped[str] = mapped_column(Text, default="")
    remito_id: Mapped[int] = mapped_column(ForeignKey("remito_biologico.id"), unique=True, nullable=False)

    remito: Mapped[RemitoBiologico] = relationship(back_populates="precinto")

    def __init__(self, codigo: str, usuario_colocador: str, observaciones: str = ""):
        if not (codigo or "").strip():
            raise VeterinariaError("El precinto necesita un código.")
        self.codigo = codigo.strip()
        self.usuario_colocador = usuario_colocador
        self.observaciones = observaciones or ""
        self.fecha_colocacion = reloj.ahora()
        self.estado = EstadoPrecinto.INTEGRO

    def verificar(self, integro: bool, usuario: str, observaciones: str = "") -> None:
        if self.fecha_verificacion is not None:
            raise VeterinariaError(f"El precinto {self.codigo} ya fue verificado.")
        self.estado = EstadoPrecinto.INTEGRO if integro else EstadoPrecinto.ROTO
        self.fecha_verificacion = reloj.ahora()
        nota = f"Verificado por {usuario}: {'íntegro' if integro else 'ROTO'}."
        if observaciones:
            nota += f" {observaciones}"
        self.observaciones = f"{self.observaciones}\n{nota}".strip()

    def esta_integro(self) -> bool:
        return self.estado is EstadoPrecinto.INTEGRO


class Envio(Base):
    __tablename__ = "envio"

    id: Mapped[int] = mapped_column(primary_key=True)
    fecha_hora_despacho: Mapped[datetime] = mapped_column(DateTime)
    fecha_hora_estimada_llegada: Mapped[datetime] = mapped_column(DateTime)
    fecha_hora_llegada_real: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    transportista: Mapped[str] = mapped_column(String(120))
    vehiculo: Mapped[str] = mapped_column(String(80), default="")
    observaciones: Mapped[str] = mapped_column(Text, default="")
    remito_id: Mapped[int] = mapped_column(ForeignKey("remito_biologico.id"), unique=True, nullable=False)

    remito: Mapped[RemitoBiologico] = relationship(back_populates="envio")

    def __init__(self, transportista: str, fecha_hora_estimada_llegada: datetime, vehiculo: str = "",
                 observaciones: str = "", fecha_hora_despacho: datetime | None = None):
        if not (transportista or "").strip():
            raise VeterinariaError("Hay que indicar el transportista.")
        self.fecha_hora_despacho = fecha_hora_despacho or reloj.ahora()
        if fecha_hora_estimada_llegada is None or fecha_hora_estimada_llegada <= self.fecha_hora_despacho:
            raise VeterinariaError("La llegada estimada debe ser posterior al despacho.")
        self.fecha_hora_estimada_llegada = fecha_hora_estimada_llegada
        self.transportista = transportista.strip()
        self.vehiculo = vehiculo or ""
        self.observaciones = observaciones or ""

    def registrar_llegada(self, fecha_hora: datetime) -> None:
        if self.fecha_hora_llegada_real is not None:
            raise VeterinariaError("La llegada del envío ya fue registrada.")
        if fecha_hora < self.fecha_hora_despacho:
            raise VeterinariaError("La llegada no puede ser anterior al despacho.")
        self.fecha_hora_llegada_real = fecha_hora

    def tiempo_transito(self) -> timedelta | None:
        if self.fecha_hora_llegada_real is None:
            return None
        return self.fecha_hora_llegada_real - self.fecha_hora_despacho

    def horas_transito(self) -> float | None:
        t = self.tiempo_transito()
        return None if t is None else round(t.total_seconds() / 3600, 1)


class RecepcionRemito(Base):
    __tablename__ = "recepcion_remito"

    id: Mapped[int] = mapped_column(primary_key=True)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime, index=True)
    estado_precinto_observado: Mapped[EstadoPrecinto] = mapped_column(EnumCol(EstadoPrecinto))
    temperatura_recepcion: Mapped[float] = mapped_column(Float)
    resultado: Mapped[Optional[ResultadoRecepcion]] = mapped_column(EnumCol(ResultadoRecepcion), nullable=True)
    motivo_rechazo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    usuario_receptor: Mapped[str] = mapped_column(String(120))
    remito_id: Mapped[int] = mapped_column(ForeignKey("remito_biologico.id"), unique=True, nullable=False)

    remito: Mapped[RemitoBiologico] = relationship(back_populates="recepcion")

    MOTIVO_PRECINTO = "Precinto roto"
    MOTIVO_TEMPERATURA = "Temperatura fuera de rango"

    def __init__(self, estado_precinto_observado: EstadoPrecinto, temperatura_recepcion: float,
                 usuario_receptor: str, fecha_hora: datetime | None = None):
        self.estado_precinto_observado = EstadoPrecinto(estado_precinto_observado)
        self.temperatura_recepcion = float(temperatura_recepcion)
        self.usuario_receptor = usuario_receptor
        self.fecha_hora = fecha_hora or reloj.ahora()

    def procesar(self, remito: RemitoBiologico, observaciones: str = "") -> None:
        """Verifica precinto y temperatura, decide ACEPTADA/RECHAZADA y ordena al remito recibir."""
        if remito.precinto is None:
            raise TransicionInvalidaError(f"El remito {remito.numero} no tiene precinto: no puede recibirse.")
        integro = self.estado_precinto_observado is EstadoPrecinto.INTEGRO
        remito.precinto.verificar(integro, self.usuario_receptor, observaciones)
        motivos = []
        if not integro:
            motivos.append(self.MOTIVO_PRECINTO)
        if not remito.contenedor.temperatura_adecuada(self.temperatura_recepcion):
            motivos.append(f"{self.MOTIVO_TEMPERATURA} ({self.temperatura_recepcion:g} °C; admitido "
                           f"{remito.contenedor.rango_texto()})")
        self.resultado = ResultadoRecepcion.RECHAZADA if motivos else ResultadoRecepcion.ACEPTADA
        self.motivo_rechazo = "; ".join(motivos) or None
        remito.recibir(self)

    def es_aceptada(self) -> bool:
        return self.resultado is ResultadoRecepcion.ACEPTADA

    def motivo_principal(self) -> str | None:
        """Clasificación para el reporte R2."""
        if self.es_aceptada():
            return None
        return self.MOTIVO_PRECINTO if self.estado_precinto_observado is EstadoPrecinto.ROTO else self.MOTIVO_TEMPERATURA


@event.listens_for(RemitoBiologico, "refresh")
def _rehidratar_remito(target, context, attrs):  # pragma: no cover
    target._rehidratar_estado()

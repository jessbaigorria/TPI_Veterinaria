"""Clientes, mascotas e historia clínica: Titular, Mascota, HistoriaClinica, Vacuna, AplicacionVacuna."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column, object_session, relationship

from app.domain import reloj, validaciones
from app.domain.base import Base, EnumCol
from app.domain.enums import Especie, Sexo
from app.domain.excepciones import MascotaSinTitularError, VeterinariaError

if TYPE_CHECKING:  # pragma: no cover
    from app.domain.atencion import AtencionClinica
    from app.domain.cirugia import DerivacionCirugia
    from app.domain.facturacion import Factura
    from app.domain.laboratorio import OrdenDerivacion
    from app.domain.muestra import ResultadoAnalisis


class Titular(Base):
    """Cliente responsable de una o más mascotas."""

    __tablename__ = "titular"

    id: Mapped[int] = mapped_column(primary_key=True)
    dni: Mapped[str] = mapped_column(String(20), unique=True)
    nombre: Mapped[str] = mapped_column(String(80))
    apellido: Mapped[str] = mapped_column(String(80))
    direccion: Mapped[str] = mapped_column(String(160), default="")
    telefono: Mapped[str] = mapped_column(String(40), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    fecha_alta: Mapped[date] = mapped_column(Date)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    mascotas: Mapped[list["Mascota"]] = relationship(back_populates="titular", order_by="Mascota.nombre")
    facturas: Mapped[list["Factura"]] = relationship(back_populates="titular")

    def __init__(self, dni: str, nombre: str, apellido: str, direccion: str = "", telefono: str = "",
                 email: str = "", fecha_alta: date | None = None, activo: bool = True):
        self.actualizar_datos(dni, nombre, apellido, direccion, telefono, email)
        self.fecha_alta = fecha_alta or reloj.hoy()
        self.activo = activo

    def actualizar_datos(self, dni: str, nombre: str, apellido: str, direccion: str, telefono: str,
                         email: str) -> None:
        """Todos los datos son obligatorios: DNI de 7 u 8 dígitos (se guardan solo los dígitos), nombre y
        apellido solo letras, teléfono de 8 a 15 dígitos y email válido. Lanza DatosInvalidosError."""
        self.dni = validaciones.dni(dni)
        self.nombre = validaciones.nombre_persona(nombre, "Nombre", minimo=2)
        self.apellido = validaciones.nombre_persona(apellido, "Apellido", minimo=2)
        self.direccion = validaciones.obligatorio(direccion, "Dirección")
        self.telefono = validaciones.telefono(telefono)
        self.email = validaciones.email(email)

    # --- métodos del diagrama -------------------------------------------------
    def agregar_mascota(self, m: "Mascota") -> None:
        if m not in self.mascotas:
            self.mascotas.append(m)

    def mascotas_activas(self) -> list["Mascota"]:
        return [m for m in self.mascotas if m.activa]

    def dar_de_baja_mascota(self, m: "Mascota") -> None:
        """Baja lógica de una mascota del titular (no se borra: tiene historia)."""
        if m not in self.mascotas:
            raise VeterinariaError(f"{m.nombre} no pertenece a {self.nombre_completo()}.")
        m.activa = False

    # --- auxiliares ------------------------------------------------------------
    def nombre_completo(self) -> str:
        return f"{self.apellido}, {self.nombre}"

    def dar_de_baja(self) -> None:
        """Baja lógica del titular y de todas sus mascotas."""
        self.activo = False
        for m in self.mascotas:
            m.activa = False

    def reactivar(self) -> None:
        self.activo = True

    def __repr__(self) -> str:
        return f"<Titular {self.dni} {self.nombre_completo()}>"


class Mascota(Base):
    __tablename__ = "mascota"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80))
    especie: Mapped[Especie] = mapped_column(EnumCol(Especie))
    raza: Mapped[str] = mapped_column(String(80), default="")
    sexo: Mapped[Sexo] = mapped_column(EnumCol(Sexo))
    fecha_nacimiento: Mapped[date] = mapped_column(Date)
    peso: Mapped[float] = mapped_column(Float, default=0.0)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    titular_id: Mapped[int] = mapped_column(ForeignKey("titular.id"), nullable=False)

    titular: Mapped[Titular] = relationship(back_populates="mascotas")
    historia_clinica: Mapped["HistoriaClinica"] = relationship(
        back_populates="mascota", uselist=False, cascade="all, delete-orphan"
    )

    def __init__(self, titular: Titular | None, nombre: str, especie: Especie, sexo: Sexo,
                 fecha_nacimiento: date, raza: str = "", peso: float = 0.0,
                 numero_historia: str | None = None, alergias: str = "", antecedentes: str = ""):
        # Validación 1: toda mascota debe tener un responsable asociado.
        if titular is None:
            raise MascotaSinTitularError("No se puede registrar una mascota sin titular responsable.")
        if not titular.activo:
            raise MascotaSinTitularError(f"El titular {titular.nombre_completo()} está dado de baja.")
        self.nombre = self.validar_nombre(nombre)
        if fecha_nacimiento is None or fecha_nacimiento > reloj.hoy():
            raise VeterinariaError("La fecha de nacimiento es obligatoria y no puede ser futura.")
        self.especie = Especie(especie)
        self.sexo = Sexo(sexo)
        self.fecha_nacimiento = fecha_nacimiento
        self.raza = self.validar_raza(raza)
        self.peso = float(peso or 0)
        self.activa = True
        titular.agregar_mascota(self)
        # Composición 1–1: la historia clínica nace con la mascota.
        self.historia_clinica = HistoriaClinica(numero=numero_historia, alergias=alergias,
                                                antecedentes=antecedentes)

    @staticmethod
    def validar_nombre(nombre) -> str:
        """Obligatorio, solo letras y espacios (mínimo 2)."""
        return validaciones.nombre_persona(nombre, "Nombre de la mascota", minimo=2)

    @staticmethod
    def validar_raza(raza) -> str:
        """Opcional; si se carga, solo letras y espacios (mínimo 2)."""
        return validaciones.nombre_persona(raza, "Raza", minimo=2) if (raza or "").strip() else ""

    def edad_en_semanas(self, fecha: date | None = None) -> int:
        fecha = fecha or reloj.hoy()
        return max(0, (fecha - self.fecha_nacimiento).days // 7)

    def cambiar_titular(self, t: Titular | None) -> None:
        if t is None:
            raise MascotaSinTitularError("La mascota debe quedar asociada a un titular.")
        if not t.activo:
            raise MascotaSinTitularError(f"El titular {t.nombre_completo()} está dado de baja.")
        if t is self.titular:
            return
        self.titular.mascotas.remove(self)
        t.agregar_mascota(self)

    # --- auxiliares ------------------------------------------------------------
    def edad_texto(self) -> str:
        dias = (reloj.hoy() - self.fecha_nacimiento).days
        anios, resto = divmod(dias, 365)
        meses = resto // 30
        if anios:
            return f"{anios} año{'s' if anios != 1 else ''}" + (f" {meses} m" if meses else "")
        if meses:
            return f"{meses} mes{'es' if meses != 1 else ''}"
        return f"{dias // 7} sem"

    def __repr__(self) -> str:
        return f"<Mascota {self.nombre} ({self.especie.value})>"


class Vacuna(Base):
    """Esquema de vacunación (catálogo)."""

    __tablename__ = "vacuna"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80))
    especie: Mapped[Especie] = mapped_column(EnumCol(Especie))
    obligatoria: Mapped[bool] = mapped_column(Boolean, default=True)
    edad_minima_semanas: Mapped[int] = mapped_column(Integer, default=0)
    intervalo_refuerzo_dias: Mapped[int] = mapped_column(Integer, default=365)

    def corresponde_a(self, m: Mascota, fecha: date | None = None) -> bool:
        return self.especie == m.especie and m.edad_en_semanas(fecha) >= self.edad_minima_semanas

    def __repr__(self) -> str:
        return f"<Vacuna {self.nombre} {self.especie.value}>"


class AplicacionVacuna(Base):
    __tablename__ = "aplicacion_vacuna"

    id: Mapped[int] = mapped_column(primary_key=True)
    fecha_aplicacion: Mapped[date] = mapped_column(Date)
    lote: Mapped[str] = mapped_column(String(40), default="")
    dosis_numero: Mapped[int] = mapped_column(Integer, default=1)
    fecha_proxima_dosis: Mapped[date] = mapped_column(Date)
    historia_id: Mapped[int] = mapped_column(ForeignKey("historia_clinica.id"), nullable=False)
    vacuna_id: Mapped[int] = mapped_column(ForeignKey("vacuna.id"), nullable=False)

    historia: Mapped["HistoriaClinica"] = relationship(back_populates="aplicaciones")
    vacuna: Mapped[Vacuna] = relationship()

    def __init__(self, vacuna: Vacuna, fecha_aplicacion: date | None = None, lote: str = "",
                 dosis_numero: int = 1):
        if vacuna is None:
            raise VeterinariaError("Hay que indicar la vacuna aplicada.")
        self.vacuna = vacuna
        self.fecha_aplicacion = fecha_aplicacion or reloj.hoy()
        if self.fecha_aplicacion > reloj.hoy():
            raise VeterinariaError("La fecha de aplicación no puede ser futura.")
        self.lote = lote or ""
        self.dosis_numero = int(dosis_numero or 1)
        self.fecha_proxima_dosis = self.fecha_aplicacion + timedelta(days=vacuna.intervalo_refuerzo_dias)

    def esta_vigente(self, fecha: date | None = None) -> bool:
        fecha = fecha or reloj.hoy()
        return self.fecha_aplicacion <= fecha <= self.fecha_proxima_dosis


@dataclass(frozen=True)
class DetalleVacunaPendiente:
    """Auxiliar para el R5 y la UI: por qué una vacuna está pendiente."""

    vacuna: Vacuna
    ultima_aplicacion: Optional[AplicacionVacuna]
    vencida_desde: date
    dias_atraso: int

    @property
    def motivo(self) -> str:
        return "Vencida" if self.ultima_aplicacion else "Nunca aplicada"


class HistoriaClinica(Base):
    __tablename__ = "historia_clinica"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[Optional[str]] = mapped_column(String(20), unique=True)
    fecha_registro: Mapped[date] = mapped_column(Date)
    alergias: Mapped[str] = mapped_column(Text, default="")
    antecedentes: Mapped[str] = mapped_column(Text, default="")
    observaciones_generales: Mapped[str] = mapped_column(Text, default="")
    mascota_id: Mapped[int] = mapped_column(ForeignKey("mascota.id"), unique=True, nullable=False)

    mascota: Mapped[Mascota] = relationship(back_populates="historia_clinica")
    atenciones: Mapped[list["AtencionClinica"]] = relationship(
        back_populates="historia", order_by="AtencionClinica.fecha_hora_inicio"
    )
    aplicaciones: Mapped[list[AplicacionVacuna]] = relationship(
        back_populates="historia", cascade="all, delete-orphan", order_by=AplicacionVacuna.fecha_aplicacion
    )

    def __init__(self, numero: str | None = None, alergias: str = "", antecedentes: str = "",
                 observaciones_generales: str = ""):
        self.numero = numero
        self.fecha_registro = reloj.hoy()
        self.alergias = alergias or ""
        self.antecedentes = antecedentes or ""
        self.observaciones_generales = observaciones_generales or ""

    # --- métodos del diagrama -------------------------------------------------
    def agregar_atencion(self, a: "AtencionClinica") -> None:
        if a not in self.atenciones:
            self.atenciones.append(a)

    def registrar_vacuna(self, a: AplicacionVacuna) -> None:
        if a.vacuna.especie != self.mascota.especie:
            raise VeterinariaError(
                f"La vacuna {a.vacuna.nombre} es para {a.vacuna.especie.etiqueta.lower()}, "
                f"no para {self.mascota.especie.etiqueta.lower()}."
            )
        self.aplicaciones.append(a)

    def vacunas_pendientes(self, fecha: date | None = None,
                           catalogo: list[Vacuna] | None = None) -> list[Vacuna]:
        """Vacunas obligatorias que corresponden a la mascota y no tienen aplicación vigente."""
        return [d.vacuna for d in self.detalle_vacunas_pendientes(fecha, catalogo)]

    def atenciones_en_periodo(self, desde, hasta) -> list["AtencionClinica"]:
        return [a for a in self.atenciones if reloj.en_periodo(a.fecha_hora_inicio, desde, hasta)]

    def ultima_atencion(self) -> "AtencionClinica | None":
        validas = [a for a in self.atenciones if a.esta_realizada()]
        return max(validas, key=lambda a: a.fecha_hora_inicio) if validas else None

    def ordenes_derivacion(self) -> list["OrdenDerivacion"]:
        return [o for a in self.atenciones for o in a.ordenes]

    def resultados_laboratorio(self) -> list["ResultadoAnalisis"]:
        return [r for o in self.ordenes_derivacion() for m in o.muestras for r in m.resultados]

    def derivaciones_cirugia(self) -> list["DerivacionCirugia"]:
        return [d for a in self.atenciones for d in a.derivaciones]

    # --- auxiliares ------------------------------------------------------------
    def detalle_vacunas_pendientes(self, fecha: date | None = None,
                                   catalogo: list[Vacuna] | None = None) -> list[DetalleVacunaPendiente]:
        fecha = fecha or reloj.hoy()
        if catalogo is None:
            catalogo = self._catalogo_vacunas_obligatorias()
        pendientes = []
        for v in catalogo:
            if not v.obligatoria or not v.corresponde_a(self.mascota, fecha):
                continue
            aplicaciones = [a for a in self.aplicaciones if a.vacuna is v and a.fecha_aplicacion <= fecha]
            if any(a.esta_vigente(fecha) for a in aplicaciones):
                continue
            ultima = max(aplicaciones, key=lambda a: a.fecha_aplicacion) if aplicaciones else None
            if ultima:
                vencida_desde = ultima.fecha_proxima_dosis
            else:
                vencida_desde = self.mascota.fecha_nacimiento + timedelta(weeks=v.edad_minima_semanas)
            pendientes.append(DetalleVacunaPendiente(v, ultima, vencida_desde, max(0, (fecha - vencida_desde).days)))
        return pendientes

    def _catalogo_vacunas_obligatorias(self) -> list[Vacuna]:
        sesion = object_session(self) or object_session(self.mascota)
        if sesion is None:
            return []
        return list(sesion.scalars(select(Vacuna).where(Vacuna.obligatoria.is_(True)).order_by(Vacuna.nombre)))

    def facturas(self) -> list["Factura"]:
        """Comprobantes de atenciones, órdenes y cirugías de esta historia (más recientes primero)."""
        fs = [f for a in self.atenciones for f in a.facturas]
        fs += [f for o in self.ordenes_derivacion() for f in o.facturas]
        fs += [f for d in self.derivaciones_cirugia() for f in d.facturas]
        return sorted(fs, key=lambda f: f.fecha_emision, reverse=True)

    def ultima_aplicacion(self, v: Vacuna) -> AplicacionVacuna | None:
        apps = [a for a in self.aplicaciones if a.vacuna is v]
        return max(apps, key=lambda a: a.fecha_aplicacion) if apps else None

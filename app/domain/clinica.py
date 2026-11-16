"""Clínicas de la red y sus profesionales: Clinica y Profesional."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain import reloj
from app.domain.base import Base

if TYPE_CHECKING:  # pragma: no cover
    from app.domain.atencion import AtencionClinica
    from app.domain.transporte import Contenedor


class Clinica(Base):
    __tablename__ = "clinica"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), unique=True)
    direccion: Mapped[str] = mapped_column(String(160), default="")
    localidad: Mapped[str] = mapped_column(String(80), default="")
    telefono: Mapped[str] = mapped_column(String(40), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    alta_complejidad: Mapped[bool] = mapped_column(Boolean, default=False)

    profesionales: Mapped[list["Profesional"]] = relationship(back_populates="clinica",
                                                              order_by="Profesional.apellido")
    atenciones: Mapped[list["AtencionClinica"]] = relationship(back_populates="clinica")
    contenedores: Mapped[list["Contenedor"]] = relationship(back_populates="clinica",
                                                            order_by="Contenedor.codigo")

    def agregar_profesional(self, p: "Profesional") -> None:
        if p not in self.profesionales:
            self.profesionales.append(p)

    def atenciones_en_periodo(self, desde, hasta) -> list["AtencionClinica"]:
        en_periodo = (a for a in self.atenciones if reloj.en_periodo(a.fecha_hora_inicio, desde, hasta))
        return sorted(en_periodo, key=lambda a: a.fecha_hora_inicio)

    def __repr__(self) -> str:
        return f"<Clinica {self.nombre}>"


class Profesional(Base):
    __tablename__ = "profesional"

    id: Mapped[int] = mapped_column(primary_key=True)
    legajo: Mapped[str] = mapped_column(String(20), unique=True)
    matricula: Mapped[str] = mapped_column(String(20))
    dni: Mapped[str] = mapped_column(String(20))
    nombre: Mapped[str] = mapped_column(String(80))
    apellido: Mapped[str] = mapped_column(String(80))
    especialidad: Mapped[str] = mapped_column(String(80), default="Clínica general")
    telefono: Mapped[str] = mapped_column(String(40), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    clinica_id: Mapped[int] = mapped_column(ForeignKey("clinica.id"), nullable=False)

    clinica: Mapped[Clinica] = relationship(back_populates="profesionales")
    atenciones: Mapped[list["AtencionClinica"]] = relationship(back_populates="profesional")

    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellido}"

    def esta_disponible(self, inicio: datetime, fin: datetime,
                        excluir: "AtencionClinica | None" = None) -> bool:
        """Validación 4: recorre las atenciones del profesional buscando superposiciones."""
        return not any(a.se_superpone_con_intervalo(inicio, fin) for a in self.atenciones if a is not excluir)

    def __repr__(self) -> str:
        return f"<Profesional {self.legajo} {self.nombre_completo()}>"

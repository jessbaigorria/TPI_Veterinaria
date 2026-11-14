"""Numeración automática (string única): HC-000001, ORD-000001, M-000001, REM-000001, PRE-000001,
FAC-000001, CIR-000001. Se guarda el último número por prefijo en la tabla ``secuencia``."""
from __future__ import annotations

from sqlalchemy import Integer, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.domain.base import Base


class Secuencia(Base):
    __tablename__ = "secuencia"

    prefijo: Mapped[str] = mapped_column(String(10), primary_key=True)
    ultimo: Mapped[int] = mapped_column(Integer, default=0)


class Numerador:
    HISTORIA = "HC"
    ORDEN = "ORD"
    MUESTRA = "M"
    REMITO = "REM"
    PRECINTO = "PRE"
    FACTURA = "FAC"
    CIRUGIA = "CIR"

    def __init__(self, sesion: Session):
        self.sesion = sesion

    def siguiente(self, prefijo: str) -> str:
        sec = self.sesion.get(Secuencia, prefijo)
        if sec is None:
            sec = Secuencia(prefijo=prefijo, ultimo=0)
            self.sesion.add(sec)
        sec.ultimo += 1
        return f"{prefijo}-{sec.ultimo:06d}"

    def proximo(self, prefijo: str) -> str:
        """Muestra el próximo número sin consumirlo (para precargar formularios)."""
        sec = self.sesion.get(Secuencia, prefijo)
        return f"{prefijo}-{(sec.ultimo if sec else 0) + 1:06d}"

"""Numeración automática (string única): HC-000001, ORD-000001, M-000001, REM-000001, PRE-000001,
FAC-000001, CIR-000001. Se guarda el último número por prefijo en la tabla ``secuencia``."""
from __future__ import annotations

from sqlalchemy import Integer, String, select, text
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
        # Upsert atómico en la misma transacción del caso de uso (se revierte con el rollback).
        ultimo = self.sesion.execute(
            text("INSERT INTO secuencia (prefijo, ultimo) VALUES (:p, 1) "
                 "ON CONFLICT(prefijo) DO UPDATE SET ultimo = ultimo + 1 RETURNING ultimo"),
            {"p": prefijo},
        ).scalar_one()
        return f"{prefijo}-{ultimo:06d}"

    def proximo(self, prefijo: str) -> str:
        """Muestra el próximo número sin consumirlo (para precargar formularios)."""
        ultimo = self.sesion.execute(select(Secuencia.ultimo).where(Secuencia.prefijo == prefijo)).scalar()
        return f"{prefijo}-{(ultimo or 0) + 1:06d}"

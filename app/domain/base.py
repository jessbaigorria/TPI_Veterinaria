"""Base declarativa de SQLAlchemy y tipos de columna compartidos."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import Enum as SAEnum, Integer
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import TypeDecorator


class Base(DeclarativeBase):
    pass


class Dinero(TypeDecorator):
    """Decimal persistido como centavos enteros (exacto en SQLite y en SUM())."""

    impl = Integer
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        valor = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return int(valor * 100)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return (Decimal(int(value)) / Decimal(100)).quantize(Decimal("0.01"))


def EnumCol(enum_cls):
    """Columna enum guardada como texto (nombre del valor)."""
    return SAEnum(enum_cls, native_enum=False, length=30, validate_strings=True)


def a_decimal(valor) -> Decimal:
    if valor is None or valor == "":
        return Decimal("0.00")
    return Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

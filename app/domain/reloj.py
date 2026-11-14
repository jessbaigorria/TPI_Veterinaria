"""Reloj inyectable.

Todo el dominio obtiene la fecha/hora actual de acá. El seed (y los tests)
pueden fijar el reloj para fechar eventos en el pasado y que el historial de
estados quede consistente.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timedelta

_fijo: datetime | None = None


def ahora() -> datetime:
    """Fecha y hora actual (o la fijada), sin microsegundos."""
    if _fijo is not None:
        return _fijo
    return datetime.now().replace(microsecond=0)


def hoy() -> date:
    return ahora().date()


def fijar(momento: datetime) -> None:
    global _fijo
    _fijo = momento.replace(microsecond=0)


def avanzar(**delta) -> datetime:
    """Avanza el reloj fijado (por ejemplo ``avanzar(hours=3)``)."""
    if _fijo is None:
        raise RuntimeError("El reloj no está fijado")
    fijar(_fijo + timedelta(**delta))
    return _fijo


def liberar() -> None:
    global _fijo
    _fijo = None


def esta_fijo() -> bool:
    return _fijo is not None


@contextmanager
def fijado(momento: datetime):
    """Context manager: fija el reloj y lo restaura al salir."""
    global _fijo
    anterior = _fijo
    fijar(momento)
    try:
        yield
    finally:
        _fijo = anterior

"""Infraestructura común de los servicios: unidad de trabajo y helpers."""
from __future__ import annotations

from datetime import date, datetime
from functools import wraps
from typing import Type, TypeVar

from sqlalchemy.orm import Session

from app.domain.excepciones import DatosInvalidosError, VeterinariaError
from app.repositories.base import Repositorio
from app.repositories.numerador import Numerador

T = TypeVar("T")


def transaccional(metodo):
    """Ejecuta el caso de uso en una transacción: commit al terminar, rollback ante cualquier error.
    Las llamadas anidadas (un servicio que usa otro) comparten la transacción externa."""

    @wraps(metodo)
    def envoltura(self, *args, **kwargs):
        sesion = self.s
        profundidad = sesion.info.get("_tx", 0)
        sesion.info["_tx"] = profundidad + 1
        try:
            with sesion.no_autoflush:  # se construye el grafo completo y se persiste al final
                resultado = metodo(self, *args, **kwargs)
            if profundidad == 0:
                sesion.commit()
            return resultado
        except Exception:
            if profundidad == 0:
                sesion.rollback()
            raise
        finally:
            sesion.info["_tx"] = profundidad

    return envoltura


class ServicioBase:
    def __init__(self, sesion: Session):
        self.s = sesion
        self.numerador = Numerador(sesion)

    def repo(self, modelo: Type[T]) -> Repositorio[T]:
        return Repositorio(self.s, modelo)

    def obtener(self, modelo: Type[T], id_) -> T:
        return Repositorio(self.s, modelo).obtener(id_)


# --- conversión de datos de formularios (los routers pasan strings) ------------------
def texto(valor) -> str:
    return (valor or "").strip() if isinstance(valor, str) or valor is None else str(valor)


def a_fecha(valor) -> date | None:
    if valor in (None, ""):
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(str(valor)[:10])
    except ValueError as exc:
        raise VeterinariaError(f"Fecha inválida: {valor}") from exc


def a_fecha_hora(valor) -> datetime | None:
    if valor in (None, ""):
        return None
    if isinstance(valor, datetime):
        return valor
    try:
        return datetime.fromisoformat(str(valor)).replace(second=0, microsecond=0)
    except ValueError as exc:
        raise VeterinariaError(f"Fecha y hora inválida: {valor}") from exc


def validar_rango_fechas(desde, hasta, obligatorias: bool = False) -> None:
    """«Hasta» no puede ser anterior a «Desde» (y en reportes las dos son obligatorias)."""
    if obligatorias and (desde is None or hasta is None):
        raise DatosInvalidosError("Las fechas «Desde» y «Hasta» son obligatorias.")
    if desde is not None and hasta is not None and hasta < desde:
        raise DatosInvalidosError("La fecha «Hasta» no puede ser anterior a la fecha «Desde».")


def a_float(valor, campo: str = "valor") -> float | None:
    if valor in (None, ""):
        return None
    try:
        return float(str(valor).replace(",", "."))
    except ValueError as exc:
        raise VeterinariaError(f"El {campo} debe ser numérico.") from exc


def a_bool(valor) -> bool:
    if isinstance(valor, bool):
        return valor
    return str(valor).lower() in ("1", "true", "si", "sí", "on", "yes")

"""Repositorio genérico (consultas comunes) para los agregados del dominio."""
from __future__ import annotations

from typing import Generic, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.excepciones import VeterinariaError

T = TypeVar("T")


class Repositorio(Generic[T]):
    def __init__(self, sesion: Session, modelo: Type[T]):
        self.sesion = sesion
        self.modelo = modelo

    def obtener(self, id_: int | str | None) -> T:
        if id_ in (None, ""):
            raise VeterinariaError(f"Falta indicar {self._nombre()}.")
        obj = self.sesion.get(self.modelo, int(id_))
        if obj is None:
            raise VeterinariaError(f"No existe {self._nombre()} #{id_}.")
        return obj

    def obtener_opcional(self, id_) -> T | None:
        if id_ in (None, ""):
            return None
        return self.sesion.get(self.modelo, int(id_))

    def buscar_por(self, **filtros) -> T | None:
        return self.sesion.scalars(select(self.modelo).filter_by(**filtros)).first()

    def listar(self, *condiciones, orden=None) -> list[T]:
        stmt = select(self.modelo).where(*condiciones)
        if orden is not None:
            stmt = stmt.order_by(*(orden if isinstance(orden, (list, tuple)) else [orden]))
        return list(self.sesion.scalars(stmt))

    def agregar(self, obj: T) -> T:
        self.sesion.add(obj)
        return obj

    def _nombre(self) -> str:
        return self.modelo.__name__

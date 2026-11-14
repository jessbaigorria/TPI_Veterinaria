"""Repositorio del historial de estados de la muestra: SOLO inserción (capa 2 de inmutabilidad).

No existen ``actualizar()`` ni ``eliminar()``. Además se registran listeners de
SQLAlchemy que impiden UPDATE/DELETE de filas del historial a través del ORM.
"""
from __future__ import annotations

from sqlalchemy import event, select
from sqlalchemy.orm import Session, object_session

from app.domain.excepciones import VeterinariaError
from app.domain.laboratorio import HistorialEstadoMuestra, HistorialEstadoMuestraFila


class HistorialInmutableError(VeterinariaError):
    """Intento de modificar o borrar el historial (lo lanzan los listeners del ORM)."""


class HistorialRepository:
    def __init__(self, sesion: Session | None = None):
        self._sesion = sesion

    def agregar(self, fila: HistorialEstadoMuestraFila) -> None:
        sesion = self._sesion or object_session(fila.muestra)
        if sesion is not None:
            sesion.add(fila)
        # Si la muestra todavía no está en una sesión, la fila queda vinculada a ella
        # y se persiste en cascada cuando se agregue la muestra.

    def listar_por_muestra(self, muestra_id: int) -> tuple[HistorialEstadoMuestra, ...]:
        if self._sesion is None:
            raise VeterinariaError("El repositorio de historial necesita una sesión para listar.")
        filas = self._sesion.scalars(
            select(HistorialEstadoMuestraFila)
            .where(HistorialEstadoMuestraFila.muestra_id == muestra_id)
            .order_by(HistorialEstadoMuestraFila.id)
        )
        return tuple(HistorialEstadoMuestra.desde_fila(f) for f in filas)


@event.listens_for(HistorialEstadoMuestraFila, "before_update")
def _bloquear_update(mapper, connection, target):
    raise HistorialInmutableError("El historial de estados es inmutable: UPDATE bloqueado por el ORM.")


@event.listens_for(HistorialEstadoMuestraFila, "before_delete")
def _bloquear_delete(mapper, connection, target):
    raise HistorialInmutableError("El historial de estados es inmutable: DELETE bloqueado por el ORM.")

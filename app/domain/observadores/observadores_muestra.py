"""Patrón Observer – trazabilidad.

``MuestraBiologica`` (sujeto) notifica en ``_cambiar_estado`` a sus observadores:

* ``RegistroHistorial``: crea el ``HistorialEstadoMuestra`` (fila inmutable) a través
  de un repositorio que SOLO agrega. Es la única clase que escribe historial.
* ``ActualizadorEstadoOrden``: recalcula el estado de la orden de derivación
  (EMITIDA → EN_PROCESO → COMPLETADA).

Los observadores se adjuntan en un único lugar: ``app/services/fabrica_observadores.py``.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Protocol

from app.domain import reloj

if TYPE_CHECKING:  # pragma: no cover
    from app.domain.estados.estado_muestra import EstadoMuestra
    from app.domain.laboratorio import HistorialEstadoMuestraFila, MuestraBiologica


class RepositorioHistorial(Protocol):
    """Lo único que RegistroHistorial necesita del repositorio: agregar."""

    def agregar(self, fila: "HistorialEstadoMuestraFila") -> None: ...


class ObservadorMuestra(ABC):
    """«interface» del diagrama."""

    @abstractmethod
    def actualizar(self, muestra: "MuestraBiologica", anterior: "EstadoMuestra | None",
                   nuevo: "EstadoMuestra", motivo: str, usuario: str) -> None:
        """Se invoca después de cada cambio de estado de la muestra."""


class RegistroHistorial(ObservadorMuestra):
    """«crea» HistorialEstadoMuestra en cada transición."""

    SIN_ESTADO = "—"

    def __init__(self, repositorio: RepositorioHistorial):
        self._repositorio = repositorio

    def actualizar(self, muestra, anterior, nuevo, motivo, usuario):
        from app.domain.laboratorio import HistorialEstadoMuestraFila

        fila = HistorialEstadoMuestraFila(
            muestra=muestra,
            fecha_hora=reloj.ahora(),
            estado_anterior=anterior.nombre if anterior is not None else self.SIN_ESTADO,
            estado_nuevo=nuevo.nombre,
            motivo=motivo or "",
            usuario=usuario or "sistema",
        )
        self._repositorio.agregar(fila)


class ActualizadorEstadoOrden(ObservadorMuestra):
    """Pasa la orden a EN_PROCESO / COMPLETADA según el estado de sus muestras."""

    def actualizar(self, muestra, anterior, nuevo, motivo, usuario):
        if muestra.orden is not None:
            muestra.orden.actualizar_estado()

"""Único lugar donde se adjuntan los observadores a las muestras (patrón Observer).

Se engancha a los eventos ``init`` (creación) y ``load`` (lectura desde la base) de
``MuestraBiologica``; así toda muestra, nueva o cargada, tiene sus dos observadores:
``RegistroHistorial`` (con el repositorio de solo inserción) y ``ActualizadorEstadoOrden``.
"""
from __future__ import annotations

from sqlalchemy import event
from sqlalchemy.orm import Session

from app.domain.laboratorio import MuestraBiologica
from app.domain.observadores.observadores_muestra import ActualizadorEstadoOrden, RegistroHistorial
from app.repositories.historial import HistorialRepository


def adjuntar_observadores(muestra: MuestraBiologica, sesion: Session | None = None) -> None:
    if muestra.__dict__.get("_observadores_adjuntos"):
        return
    muestra.agregar_observador(RegistroHistorial(HistorialRepository(sesion)))
    muestra.agregar_observador(ActualizadorEstadoOrden())
    muestra.__dict__["_observadores_adjuntos"] = True


@event.listens_for(MuestraBiologica, "init")
def _al_crear(target, args, kwargs):
    adjuntar_observadores(target)


@event.listens_for(MuestraBiologica, "load")
def _al_cargar(target, context):
    adjuntar_observadores(target, context.session)

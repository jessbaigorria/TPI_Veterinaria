"""PATRÓN STATE: ciclo de vida de la muestra biológica y del remito biológico.

Los estados concretos del remito se importan desde ``estado_remito`` (``EnTransito`` es un estado de
los dos ciclos: el de la muestra se reexporta acá, el del remito no)."""
from .estado_muestra import (  # noqa: F401
    Analizada, Empaquetada, EnTransito, EstadoMuestra, Extraida, Recibida, Rechazada,
)
from .estado_remito import EstadoRemito  # noqa: F401

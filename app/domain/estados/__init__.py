"""PATRÓN STATE: ciclo de vida de la muestra biológica y del remito biológico."""
from .estado_muestra import (  # noqa: F401
    Analizada, Empaquetada, EnTransito, EstadoMuestra, Extraida, Recibida, Rechazada,
)
from .estado_remito import (  # noqa: F401
    EstadoRemito, RemitoArmado, RemitoDespachado, RemitoEnTransito, RemitoRecibido,
    RemitoRecibidoConObservaciones,
)

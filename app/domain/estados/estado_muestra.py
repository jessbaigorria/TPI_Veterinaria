"""Patrón State – ciclo de vida de MuestraBiologica.

    [creación] → Extraida --empaquetar--> Empaquetada --despachar--> EnTransito --recibir--> Recibida --analizar--> Analizada
                                                                        └--rechazar--> Rechazada

La clase base implementa TODAS las transiciones lanzando ``TransicionInvalidaError``;
cada estado concreto redefine solo las que permite. Los estados no guardan datos:
toda la información vive en la muestra. El único punto donde la muestra cambia
de estado es ``MuestraBiologica._cambiar_estado`` (que notifica a los observadores).
"""
from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING

from app.domain.excepciones import MuestraRechazadaError, TransicionInvalidaError, VeterinariaError

if TYPE_CHECKING:  # pragma: no cover
    from app.domain.laboratorio import MuestraBiologica, ResultadoAnalisis
    from app.domain.transporte import RemitoBiologico


class EstadoMuestra(ABC):
    """Estado abstracto de la muestra. ``nombre`` es el texto que ve el usuario."""

    nombre: str = ""
    _registro: dict[str, type["EstadoMuestra"]] = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        EstadoMuestra._registro[cls.__name__] = cls

    # --- persistencia (no decide comportamiento) ---------------------------------
    @property
    def codigo(self) -> str:
        """Nombre de la clase; es lo que se guarda en la columna ``estado``."""
        return type(self).__name__

    @classmethod
    def desde_nombre(cls, codigo: str) -> "EstadoMuestra":
        """Rehidrata el objeto estado a partir del string persistido."""
        try:
            return cls._registro[codigo]()
        except KeyError as exc:  # pragma: no cover - dato corrupto
            raise VeterinariaError(f"Estado de muestra desconocido: {codigo}") from exc

    @classmethod
    def todos(cls) -> list["EstadoMuestra"]:
        return [c() for c in cls._registro.values()]

    # --- transiciones (versión base = inválida) ---------------------------------
    def empaquetar(self, m: "MuestraBiologica", remito: "RemitoBiologico", usuario: str) -> None:
        self._invalida("empaquetar", m)

    def despachar(self, m: "MuestraBiologica", usuario: str) -> None:
        self._invalida("despachar", m)

    def recibir(self, m: "MuestraBiologica", usuario: str) -> None:
        self._invalida("recibir", m)

    def rechazar(self, m: "MuestraBiologica", motivo: str, usuario: str) -> None:
        self._invalida("rechazar", m)

    def analizar(self, m: "MuestraBiologica", resultado: "ResultadoAnalisis", usuario: str) -> None:
        self._invalida("analizar", m)

    def es_final(self) -> bool:
        return False

    # --- consultas auxiliares para la UI / la orden (ver DECISIONES.md) ----------
    def acciones_disponibles(self) -> list[str]:
        """Acciones que la UI puede ofrecer en este estado (la base no permite ninguna)."""
        return []

    def fue_despachada(self) -> bool:
        """True si la muestra ya salió de la clínica (lo usa OrdenDerivacion)."""
        return False

    def _invalida(self, accion: str, m: "MuestraBiologica") -> None:
        raise TransicionInvalidaError(
            f"No se puede {accion} la muestra {m.codigo}: está {self.nombre}."
        )

    def __eq__(self, otro) -> bool:  # dos instancias del mismo estado son iguales
        return type(self) is type(otro)

    def __hash__(self) -> int:
        return hash(type(self))

    def __repr__(self) -> str:
        return f"<{self.codigo}>"


class Extraida(EstadoMuestra):
    nombre = "Extraída"

    def empaquetar(self, m, remito, usuario):
        m.remito = remito
        m._cambiar_estado(Empaquetada(), f"Empaquetada en el remito {remito.numero}", usuario)

    def acciones_disponibles(self):
        return ["empaquetar"]


class Empaquetada(EstadoMuestra):
    nombre = "Empaquetada"

    def despachar(self, m, usuario):
        m._cambiar_estado(EnTransito(), "Despachada al laboratorio", usuario)

    def acciones_disponibles(self):
        return ["despachar"]


class EnTransito(EstadoMuestra):
    nombre = "En tránsito"

    def recibir(self, m, usuario):
        m._cambiar_estado(Recibida(), "Recibida en el laboratorio (precinto íntegro)", usuario)

    def rechazar(self, m, motivo, usuario):
        if not motivo:
            raise VeterinariaError("Para rechazar una muestra hay que indicar el motivo.")
        m._cambiar_estado(Rechazada(), motivo, usuario)

    def acciones_disponibles(self):
        return ["recibir", "rechazar"]

    def fue_despachada(self):
        return True


class Recibida(EstadoMuestra):
    nombre = "Recibida"

    def analizar(self, m, resultado, usuario):
        # Se agregan los resultados de a uno; la muestra pasa a Analizada cuando
        # tiene resultado para todos los análisis de la orden que usan su tipo.
        m._agregar_resultado(resultado, usuario)
        if not m.analisis_pendientes():
            m._cambiar_estado(Analizada(), "Resultados cargados", usuario)

    def acciones_disponibles(self):
        return ["cargar_resultado"]

    def fue_despachada(self):
        return True


class Analizada(EstadoMuestra):
    nombre = "Analizada"

    def es_final(self):
        return True

    def fue_despachada(self):
        return True


class Rechazada(EstadoMuestra):
    nombre = "Rechazada"

    def es_final(self):
        return True

    def fue_despachada(self):
        return True

    def analizar(self, m, resultado, usuario):
        raise MuestraRechazadaError(
            f"La muestra {m.codigo} fue rechazada ({m.motivo_rechazo() or 'sin motivo'}): "
            "no se pueden registrar resultados."
        )

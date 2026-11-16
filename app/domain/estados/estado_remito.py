"""Patrón State – ciclo de vida de RemitoBiologico.

    [creación] → RemitoArmado --despachar(envio)--> RemitoDespachado --iniciar_transito()--> RemitoEnTransito
                                                         --recibir(recepcion)--> RemitoRecibido
                                                         --recibir(recepcion)--> RemitoRecibidoConObservaciones

El estado del remito coordina el de sus muestras (tabla 5.3 de context.md):
despachar → muestras En tránsito; recibir → muestras Recibidas o Rechazadas.
``agregar_muestra`` y ``cerrar`` también se resuelven con State (solo válidos en Armado).
"""
from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING

from app.domain.excepciones import TransicionInvalidaError, VeterinariaError

if TYPE_CHECKING:  # pragma: no cover
    from app.domain.muestra import MuestraBiologica
    from app.domain.transporte import Envio, Precinto, RecepcionRemito, RemitoBiologico


class EstadoRemito(ABC):
    nombre: str = ""
    _registro: dict[str, type["EstadoRemito"]] = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        EstadoRemito._registro[cls.__name__] = cls

    @property
    def codigo(self) -> str:
        return type(self).__name__

    @classmethod
    def desde_nombre(cls, codigo: str) -> "EstadoRemito":
        try:
            return cls._registro[codigo]()
        except KeyError as exc:  # pragma: no cover
            raise VeterinariaError(f"Estado de remito desconocido: {codigo}") from exc

    @classmethod
    def todos(cls) -> list["EstadoRemito"]:
        return [c() for c in cls._registro.values()]

    # --- transiciones (base = inválida) ---------------------------------------
    def agregar_muestra(self, r: "RemitoBiologico", m: "MuestraBiologica", usuario: str) -> None:
        self._invalida("agregar muestras a", r)

    def cerrar(self, r: "RemitoBiologico", precinto: "Precinto") -> None:
        self._invalida("cerrar con precinto", r)

    def despachar(self, r: "RemitoBiologico", envio: "Envio", usuario: str) -> None:
        self._invalida("despachar", r)

    def registrar_temperatura_despacho(self, r: "RemitoBiologico", temperatura: float) -> None:
        self._invalida("volver a medir la temperatura de despacho de", r)

    def iniciar_transito(self, r: "RemitoBiologico") -> None:
        self._invalida("iniciar el tránsito de", r)

    def recibir(self, r: "RemitoBiologico", recepcion: "RecepcionRemito") -> None:
        self._invalida("recibir", r)

    def es_final(self) -> bool:
        return False

    def acciones_disponibles(self, r: "RemitoBiologico") -> list[str]:
        return []

    def _invalida(self, accion: str, r: "RemitoBiologico") -> None:
        raise TransicionInvalidaError(f"No se puede {accion} el remito {r.numero}: está {self.nombre}.")

    def __eq__(self, otro) -> bool:
        return type(self) is type(otro)

    def __hash__(self) -> int:
        return hash(type(self))

    def __repr__(self) -> str:
        return f"<{self.codigo}>"


class RemitoArmado(EstadoRemito):
    nombre = "Armado"

    def agregar_muestra(self, r, m, usuario):
        if r.precinto is not None:
            raise TransicionInvalidaError(
                f"El remito {r.numero} ya fue cerrado con el precinto {r.precinto.codigo}: no admite más muestras."
            )
        if len(r.muestras) >= r.contenedor.capacidad:
            raise VeterinariaError(
                f"El contenedor {r.contenedor.codigo} tiene capacidad para {r.contenedor.capacidad} muestras."
            )
        if m.orden.laboratorio is not r.laboratorio:
            raise VeterinariaError(
                f"La muestra {m.codigo} está destinada a {m.orden.laboratorio.nombre}, "
                f"no a {r.laboratorio.nombre}."
            )
        if m.orden.clinica is not r.clinica_origen:
            raise VeterinariaError(f"La muestra {m.codigo} no pertenece a {r.clinica_origen.nombre}.")
        m._validar_orden_vigente()
        m.empaquetar(r, usuario)  # la muestra decide (Extraida → Empaquetada)

    def cerrar(self, r, precinto):
        if r.precinto is not None:
            raise TransicionInvalidaError(f"El remito {r.numero} ya tiene precinto {r.precinto.codigo}.")
        if not r.muestras:
            raise TransicionInvalidaError(f"El remito {r.numero} no tiene muestras: no se puede cerrar.")
        r.contenedor.asignar()  # DISPONIBLE → EN_USO
        r.precinto = precinto

    def registrar_temperatura_despacho(self, r, temperatura):
        # Mientras no salió, la conservadora se puede volver a enfriar/medir: la muestra no se pierde.
        if r.precinto is None:
            raise TransicionInvalidaError(
                f"El remito {r.numero} todavía no está cerrado: la temperatura se registra al cerrarlo."
            )
        if temperatura is None:
            raise VeterinariaError("Hay que indicar la temperatura medida.")
        r.temperatura_despacho = float(temperatura)

    def despachar(self, r, envio, usuario):
        if not r.muestras:
            raise TransicionInvalidaError(f"El remito {r.numero} no tiene muestras.")
        if r.precinto is None:
            raise TransicionInvalidaError(f"El remito {r.numero} no está cerrado con precinto.")
        if not r.contenedor.temperatura_adecuada(r.temperatura_despacho):
            raise TransicionInvalidaError(
                f"La temperatura de despacho ({r.temperatura_despacho} °C) está fuera del rango del "
                f"contenedor ({r.contenedor.temperatura_min}–{r.contenedor.temperatura_max} °C)."
            )
        r.envio = envio
        r._cambiar_estado(RemitoDespachado())
        for m in r.muestras:
            m.despachar(usuario)  # Empaquetada → En tránsito

    def acciones_disponibles(self, r):
        if r.precinto is None:
            return ["agregar_muestra", "cerrar"] if r.muestras else ["agregar_muestra"]
        return ["despachar", "registrar_temperatura"]


class RemitoDespachado(EstadoRemito):
    nombre = "Despachado"

    def iniciar_transito(self, r):
        r._cambiar_estado(RemitoEnTransito())

    def acciones_disponibles(self, r):
        return ["iniciar_transito"]


class RemitoEnTransito(EstadoRemito):
    nombre = "En tránsito"

    def recibir(self, r, recepcion):
        r.recepcion = recepcion
        r.envio.registrar_llegada(recepcion.fecha_hora)
        r.contenedor.liberar()
        usuario = recepcion.usuario_receptor
        if recepcion.es_aceptada():
            r._cambiar_estado(RemitoRecibido())
            for m in r.muestras:
                m.recibir(usuario)
        else:
            r._cambiar_estado(RemitoRecibidoConObservaciones())
            for m in r.muestras:
                m.rechazar(recepcion.motivo_rechazo, usuario)

    def acciones_disponibles(self, r):
        return ["recibir"]


class RemitoRecibido(EstadoRemito):
    nombre = "Recibido"

    def es_final(self):
        return True


class RemitoRecibidoConObservaciones(EstadoRemito):
    nombre = "Recibido con observaciones"

    def es_final(self):
        return True

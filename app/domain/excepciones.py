"""Excepciones del dominio (hoja "opciones" del diagrama).

Todas heredan de ``VeterinariaError``; la UI la captura en un único lugar
(``app/main.py``) y muestra el mensaje en un aviso rojo.
"""


class VeterinariaError(Exception):
    """Error de negocio genérico. También se usa para validaciones menores
    (campos obligatorios, capacidad del contenedor, doble facturación...)."""

    def __init__(self, mensaje: str):
        super().__init__(mensaje)
        self.mensaje = mensaje

    def __str__(self) -> str:
        return self.mensaje


class MascotaSinTitularError(VeterinariaError):
    """Validación 1: toda mascota debe tener un responsable asociado."""


class TurnoSuperpuestoError(VeterinariaError):
    """Validación 4: el profesional ya tiene otra atención que se superpone."""


class TransicionInvalidaError(VeterinariaError):
    """Transición no permitida en el ciclo de vida de la muestra o del remito.
    La lanza la clase base del patrón State."""


class MuestraRechazadaError(VeterinariaError):
    """Validación 2: no se puede registrar un resultado sobre una muestra rechazada."""


class VacunasPendientesError(VeterinariaError):
    """Validación 5: la mascota tiene vacunas obligatorias faltantes o vencidas."""

    def __init__(self, mensaje: str, vacunas=None, mascota=None):
        super().__init__(mensaje)
        self.vacunas = list(vacunas or [])
        self.mascota = mascota
        # Datos planos (la UI los usa después del rollback, cuando los objetos ORM ya expiraron).
        self.nombres_vacunas = [v.nombre for v in self.vacunas]
        self.mascota_id = getattr(mascota, "id", None)
        self.mascota_nombre = getattr(mascota, "nombre", "")


class DerivacionCirugiaError(VeterinariaError):
    """Validación del proceso opcional de derivación a cirugía de alta complejidad."""

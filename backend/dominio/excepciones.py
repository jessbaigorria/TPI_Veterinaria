class VeterinariaError(Exception):
    """Excepción base del sistema."""

class MascotaSinTitularError(VeterinariaError):
    """Mascota no asociada a un Titular"""

class TurnoSuperpuestoError(VeterinariaError):
    """Se quiere guardar un Turno en un horario ocupado"""

class TransicionInvalidaError(VeterinariaError):
    """Transicion Invalida"""

class MuestraRechazadaError(VeterinariaError):
    """La Muestra ha sido Rechazada"""

class VacunasPendientesError(VeterinariaError):
    """La Mascota tiene Vacunas Pendientes"""

class DerivacionCirugiaError(VeterinariaError):
    """Error al Derivar una Cirugia"""
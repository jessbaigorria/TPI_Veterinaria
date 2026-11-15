"""Enumeraciones del diagrama de clases (hoja "Diagrama de clases").

Todas heredan de ``str`` para que se persistan y se muestren por su nombre.
``etiqueta`` devuelve el texto legible para la UI.
"""
from enum import Enum


class _EnumBase(str, Enum):
    @property
    def etiqueta(self) -> str:
        return _ETIQUETAS.get(self.value, self.value.replace("_", " ").capitalize())

    def __str__(self) -> str:  # pragma: no cover - comodidad en templates
        return self.value


class Especie(_EnumBase):
    PERRO = "PERRO"
    GATO = "GATO"
    AVE = "AVE"
    CONEJO = "CONEJO"
    OTRO = "OTRO"


class Sexo(_EnumBase):
    MACHO = "MACHO"
    HEMBRA = "HEMBRA"


class TipoAtencion(_EnumBase):
    CONSULTA = "CONSULTA"
    CONTROL = "CONTROL"
    URGENCIA = "URGENCIA"
    VACUNACION = "VACUNACION"
    CIRUGIA = "CIRUGIA"   # agregado en la ronda de correcciones (ver DECISIONES.md)
    OTRO = "OTRO"         # agregado en la ronda de correcciones (ver DECISIONES.md)


class EstadoAtencion(_EnumBase):
    RESERVADA = "RESERVADA"
    EN_PROGRESO = "EN_PROGRESO"
    FINALIZADA = "FINALIZADA"
    CANCELADA = "CANCELADA"


class Prioridad(_EnumBase):
    NORMAL = "NORMAL"
    URGENTE = "URGENTE"


class EstadoOrden(_EnumBase):
    EMITIDA = "EMITIDA"
    EN_PROCESO = "EN_PROCESO"
    COMPLETADA = "COMPLETADA"
    ANULADA = "ANULADA"


class TipoMuestra(_EnumBase):
    SANGRE = "SANGRE"
    ORINA = "ORINA"
    HECES = "HECES"
    TEJIDO = "TEJIDO"
    HISOPADO = "HISOPADO"
    OTRO = "OTRO"


class EstadoContenedor(_EnumBase):
    DISPONIBLE = "DISPONIBLE"
    EN_USO = "EN_USO"
    EN_MANTENIMIENTO = "EN_MANTENIMIENTO"


class EstadoPrecinto(_EnumBase):
    INTEGRO = "INTEGRO"
    ROTO = "ROTO"


class ResultadoRecepcion(_EnumBase):
    ACEPTADA = "ACEPTADA"
    RECHAZADA = "RECHAZADA"


class TipoComprobante(_EnumBase):
    ATENCION_CLINICA = "ATENCION_CLINICA"
    SERVICIO_LABORATORIO = "SERVICIO_LABORATORIO"
    CIRUGIA = "CIRUGIA"


class FormaPago(_EnumBase):
    EFECTIVO = "EFECTIVO"
    TARJETA = "TARJETA"
    TRANSFERENCIA = "TRANSFERENCIA"


class EstadoFactura(_EnumBase):
    EMITIDA = "EMITIDA"
    PAGADA = "PAGADA"
    ANULADA = "ANULADA"


class EstadoDerivacionCirugia(_EnumBase):
    SOLICITADA = "SOLICITADA"
    ACEPTADA = "ACEPTADA"
    PROGRAMADA = "PROGRAMADA"
    REALIZADA = "REALIZADA"
    RECHAZADA = "RECHAZADA"
    CANCELADA = "CANCELADA"


class RiesgoAnestesico(_EnumBase):
    ASA_I = "ASA_I"
    ASA_II = "ASA_II"
    ASA_III = "ASA_III"
    ASA_IV = "ASA_IV"
    ASA_V = "ASA_V"

    @property
    def nivel(self) -> int:
        return ["ASA_I", "ASA_II", "ASA_III", "ASA_IV", "ASA_V"].index(self.value) + 1


_ETIQUETAS = {
    "EN_PROGRESO": "En progreso",
    "EN_PROCESO": "En proceso",
    "EN_USO": "En uso",
    "EN_MANTENIMIENTO": "En mantenimiento",
    "INTEGRO": "Íntegro",
    "VACUNACION": "Vacunación",
    "ATENCION_CLINICA": "Atención clínica",
    "SERVICIO_LABORATORIO": "Servicio de laboratorio",
    "CIRUGIA": "Cirugía",
    "ASA_I": "ASA I",
    "ASA_II": "ASA II",
    "ASA_III": "ASA III",
    "ASA_IV": "ASA IV",
    "ASA_V": "ASA V",
}

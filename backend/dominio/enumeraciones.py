from enum import Enum 

class Especie(Enum):
    PERRO = "Perro"
    GATO = "Gato"
    AVE = "Ave"
    CONEJO = "Conejo"
    OTRO = "Otro"

class Sexo(Enum):
    MACHO = "Macho"
    HEMBRA = "Hembra"

class TipoAtencion(Enum):
    CONSULTA = "Consulta"
    CONTROL = "Control"
    URGENCIA = "Urgencia"
    VACUNACION = "Vacunacion"

class Prioridad(Enum):
    NORMAL = "Normal"
    URGENTE = "Urgente"

class TipoMuestra(Enum):
    SANGRE = "Sangre"
    ORINA = "Orina"
    HECES = "Heces"
    TEJIDO = "Tejido"
    HISOPADO = "Hisopado"
    OTRO = "Otro"

class ResultadoRecepcion(Enum):
    ACEPTADA = "Aceptada"
    RECHAZADA = "Rechazada"

class FormaPago(Enum):
    EFECTIVO = "Efectivo"
    TARJETA = "Tarjeta"
    TRANSFERENCIA = "Transferencia"

class TipoComprobante(Enum):
    ATENCION_CLINICA = "Atencion Clinica"
    SERVICIO_LABORATORIO = "Servicio Laboratorio"
    CIRUGIA = "Cirugia"

class RiesgoAnestesico(Enum):
    ASA_I = "ASA I"
    ASA_II = "ASA II"
    ASA_III = "ASA III"
    ASA_IV = "ASA IV"
    ASA_V = "ASA V"

class EstadoAtencion(Enum):
    RESERVADA = "Reservada"
    EN_PROGRESO = "En Progreso"
    FINALIZADA = "Finalizada"
    CANCELADA = "Cancelada"

class EstadoOrden(Enum):
    EMITIDA = "Emitida"
    EN_PROCESO = "En Proceso"
    COMPLETADA = "Completada"
    ANULADA = "Anulada"

class EstadoContenedor(Enum):
    DISPONIBLE = "Disponible"
    EN_USO = "En Uso"
    EN_MANTENIMIENTO = "En Mantenimiento"

class EstadoPrecinto(Enum):
    INTEGRO = "Integro"
    ROTO = "Roto"

class EstadoFactura(Enum):
    EMITIDA = "Emitida"
    PAGADA = "Pagada"
    ANULADA = "Anulada"

class EstadoDerivacionCirugia(Enum):
    SOLICITADA = "Solicitada"
    ACEPTADA = "Aceptada"
    PROGRAMADA = "Programada"
    REALIZADA = "Realizada"
    RECHAZADA = "Rechazada"
    CANCELADA = "Cancelada"
import re
from excepciones import DatosInvalidosError


def validar_telefono(telefono):
    """Acepta formatos como '388 4123456', '+54 9 388 412-3456' o '(0388) 412-3456'.
    Devuelve el teléfono limpio: solo dígitos y un '+' opcional al inicio."""
    if not telefono or not telefono.strip():
        raise DatosInvalidosError("El teléfono no puede estar vacío")

    telefono = telefono.strip()
    if not re.fullmatch(r"\+?[\d\s\-()]+", telefono):
        raise DatosInvalidosError("El teléfono solo puede tener dígitos, espacios, guiones y paréntesis")

    limpio = re.sub(r"[\s\-()]", "", telefono)      # saca espacios, guiones y paréntesis
    cantidad_digitos = len(limpio.lstrip("+"))
    if not 8 <= cantidad_digitos <= 13:
        raise DatosInvalidosError("El teléfono debe tener entre 8 y 13 dígitos")
    return limpio


def validar_email(email):
    if not email or not email.strip():
        raise DatosInvalidosError("El email no puede estar vacío")

    email = email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise DatosInvalidosError(f"El email '{email}' no tiene un formato válido")
    return email
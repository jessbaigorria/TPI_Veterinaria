"""Validaciones de formato de datos (la regla real; los formularios repiten estas reglas en HTML/JS).

Todas lanzan ``DatosInvalidosError`` con un mensaje claro para el usuario."""
from __future__ import annotations

import re

from app.domain.excepciones import DatosInvalidosError

LETRAS = "A-Za-zÁÉÍÓÚÜÑáéíóúüñ"
_SOLO_LETRAS = re.compile(rf"^[{LETRAS}]+(?: [{LETRAS}]+)*$")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")

# Patrones equivalentes para el atributo HTML ``pattern`` (se usan en las plantillas).
PATRON_HTML_LETRAS = rf"[{LETRAS} ]{{3,}}"
PATRON_HTML_LETRAS_2 = rf"[{LETRAS} ]{{2,}}"


def _texto(valor) -> str:
    return " ".join((valor or "").split())


def nombre_persona(valor, campo: str, minimo: int = 3) -> str:
    """Solo letras (con tildes y ñ) y espacios, mínimo ``minimo`` caracteres."""
    texto = _texto(valor)
    if not texto:
        raise DatosInvalidosError(f"El campo «{campo}» es obligatorio.")
    if not _SOLO_LETRAS.match(texto):
        raise DatosInvalidosError(f"El campo «{campo}» solo admite letras y espacios.")
    if len(texto) < minimo:
        raise DatosInvalidosError(f"El campo «{campo}» debe tener al menos {minimo} letras.")
    return texto


def obligatorio(valor, campo: str) -> str:
    texto = _texto(valor)
    if not texto:
        raise DatosInvalidosError(f"El campo «{campo}» es obligatorio.")
    return texto


def dni(valor) -> str:
    """Se aceptan puntos/espacios al escribir; se guardan solo los dígitos (7 u 8)."""
    crudo = (valor or "").strip()
    if not crudo:
        raise DatosInvalidosError("El campo «DNI» es obligatorio.")
    if re.search(r"[^\d .]", crudo):
        raise DatosInvalidosError("El DNI solo admite números.")
    digitos = re.sub(r"\D", "", crudo)
    if len(digitos) not in (7, 8):
        raise DatosInvalidosError("El DNI debe tener 7 u 8 dígitos.")
    return digitos


def telefono(valor) -> str:
    crudo = (valor or "").strip()
    if not crudo:
        raise DatosInvalidosError("El campo «Teléfono» es obligatorio.")
    if not crudo.isdigit():
        raise DatosInvalidosError("El teléfono solo admite números (sin espacios ni guiones).")
    if not 8 <= len(crudo) <= 15:
        raise DatosInvalidosError("El teléfono debe tener entre 8 y 15 dígitos.")
    return crudo


def email(valor) -> str:
    texto = (valor or "").strip()
    if not texto:
        raise DatosInvalidosError("El campo «Email» es obligatorio.")
    if not _EMAIL.match(texto):
        raise DatosInvalidosError("El email no tiene un formato válido (ejemplo: nombre@correo.com).")
    return texto.lower()

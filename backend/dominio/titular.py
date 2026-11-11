from __future__ import annotations
from datetime import date 
import re
from excepciones import DatosInvalidosError
from validaciones import validar_email, validar_telefono


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mascota import Mascota


class Titular:
    def __init__(self, dni, nombre, apellido, direccion, telefono, email):
        self._dni = self._validar_dni(dni)
        self.nombre = nombre
        self.apellido = apellido 
        self.direccion = direccion 
        self.telefono = telefono
        self.email = email
        self._fecha_alta = date.today()
        self._activo = True 
        self._mascotas = []

    @property
    def nombre(self):
        return self._nombre

    @nombre.setter
    def nombre(self, nombre):
        if not nombre or not isinstance(nombre, str):
            raise DatosInvalidosError("Nombre Invalido...")
        self._nombre = nombre

    @property
    def apellido(self):
        return self._apellido
    @apellido.setter
    def apellido(self, apellido):
        if not apellido or not isinstance(apellido, str):
            raise DatosInvalidosError("Apellido Invalido...")
        self._apellido = apellido

    @property
    def direccion(self):
        return self._direccion
    @direccion.setter
    def direccion(self, direccion):
        if not direccion or not isinstance(direccion, str):
            raise DatosInvalidosError("Dirección Invalida...")
        self._direccion = direccion

    @property
    def telefono(self):
        return self._telefono
    @telefono.setter
    def telefono(self, telefono):
        if not isinstance(telefono, str):
            raise DatosInvalidosError("Telefono debe ser un string...")
        self._telefono = validar_telefono(telefono)
            

    @property
    def email(self):
        return self._email
    @email.setter
    def email(self, email):
        if not isinstance(email, str):
            raise DatosInvalidosError("Email debe ser un string...")
        self._email = validar_email(email)

    @property
    def dni(self):
        return self._dni

    @property
    def fecha_alta(self):
        return self._fecha_alta

    @property
    def activo(self):
        return self._activo

    @staticmethod
    def _validar_dni(dni):
        if isinstance(dni, str):
            dni = dni.strip().replace(".", "")
            if not re.fullmatch(r"\d{7,8}", dni):
                raise DatosInvalidosError("EL DNI debe tener 7 u 8 dígitos numéricos...")
            return dni
        else:
            raise DatosInvalidosError("DNI debe ser un string...")
    
    def agregar_mascota(self, mascota:Mascota):
        self._mascotas.append(mascota)

    def quitar_mascota(self, mascota:Mascota):
        self._mascotas.remove(mascota)
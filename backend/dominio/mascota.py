from enumeraciones import Especie, Sexo
from datetime import date
from excepciones import DatosInvalidosError, MascotaSinTitularError
from titular import Titular

class Mascota:
    def __init__(self, titular:Titular, nombre, especie:Especie, sexo: Sexo, 
                 raza, fecha_nacimiento, peso):
        if not isinstance(titular, Titular):
            raise MascotaSinTitularError("La mascota debe tener un titular...")
        
        self.nombre = nombre
        self._especie = especie
        self._raza = raza 
        self._sexo = sexo
        self._fecha_nacimiento = fecha_nacimiento
        self.peso = peso 
        self._activa = True

        self._titular = titular 
        titular.agregar_mascota(self)

    @property
    def nombre(self):
        return self._nombre 

    @nombre.setter
    def nombre(self, nombre):
        if not nombre or not isinstance(nombre, str):
            raise DatosInvalidosError("Nombre invalido...")
        self._nombre = nombre

    @property
    def peso(self):
        return self._peso

    @peso.setter
    def peso(self, peso):
        if not peso or not isinstance(peso, (float, int)):
            raise DatosInvalidosError("Peso invalido...")
        elif peso <= 0:
            raise DatosInvalidosError("El peso no puede ser menor/igual a cero...")
        self._peso = peso

    @property
    def titular(self):
        return self._titular
    @property
    def activa(self):
        return self._activa
    @property
    def especie(self):
        return self._especie

    def edad_en_semanas(self):
        edad = (date.today()-self._fecha_nacimiento).days // 7
        return edad

    def cambiar_titular(self, nuevo:Titular):
        if nuevo is self._titular:
            return
        self._titular.quitar_mascota(self)
        self._titular = nuevo
        nuevo.agregar_mascota(self)

    def dar_de_baja(self):
        self._activa = False

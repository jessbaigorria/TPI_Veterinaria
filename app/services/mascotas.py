"""Proceso 2: administrar mascotas y sus historias clínicas (incluye vacunas aplicadas)."""
from __future__ import annotations

from sqlalchemy import or_, select

from app.domain.enums import Especie, Sexo
from app.domain.excepciones import MascotaSinTitularError, VeterinariaError
from app.domain.personas import AplicacionVacuna, Mascota, Titular, Vacuna
from app.repositories.numerador import Numerador
from app.services.base import ServicioBase, a_fecha, a_float, texto, transaccional


class MascotasService(ServicioBase):
    @transaccional
    def crear_mascota(self, titular_id, nombre, especie, sexo, fecha_nacimiento, raza="", peso=None,
                      alergias="", antecedentes="") -> Mascota:
        titular = self.repo(Titular).obtener_opcional(titular_id)
        if titular is None:
            # Validación 1: la regla vive en Mascota.__init__; acá solo traducimos "no elegido".
            Mascota(None, texto(nombre), Especie.OTRO, Sexo.MACHO, a_fecha(fecha_nacimiento))
        if not especie or not sexo:
            raise VeterinariaError("Especie y sexo son obligatorios.")
        m = Mascota(titular, texto(nombre), Especie(especie), Sexo(sexo), a_fecha(fecha_nacimiento),
                    raza=texto(raza), peso=a_float(peso, "peso") or 0.0,
                    numero_historia=self.numerador.siguiente(Numerador.HISTORIA),
                    alergias=texto(alergias), antecedentes=texto(antecedentes))
        self.s.add(m)
        return m

    @transaccional
    def actualizar_mascota(self, mascota_id, **datos) -> Mascota:
        m = self.obtener(Mascota, mascota_id)
        if "nombre" in datos:
            m.nombre = Mascota.validar_nombre(datos["nombre"])
        if datos.get("especie"):
            m.especie = Especie(datos["especie"])
        if datos.get("sexo"):
            m.sexo = Sexo(datos["sexo"])
        if datos.get("fecha_nacimiento"):
            m.fecha_nacimiento = a_fecha(datos["fecha_nacimiento"])
        if "raza" in datos:
            m.raza = Mascota.validar_raza(datos["raza"])
        if datos.get("peso") not in (None, ""):
            m.peso = a_float(datos["peso"], "peso")
        return m

    @transaccional
    def cambiar_titular(self, mascota_id, titular_id) -> Mascota:
        m = self.obtener(Mascota, mascota_id)
        m.cambiar_titular(self.repo(Titular).obtener_opcional(titular_id))
        return m

    @transaccional
    def dar_de_baja(self, mascota_id) -> Mascota:
        m = self.obtener(Mascota, mascota_id)
        m.titular.dar_de_baja_mascota(m)
        return m

    @transaccional
    def reactivar(self, mascota_id) -> Mascota:
        m = self.obtener(Mascota, mascota_id)
        if not m.titular.activo:
            raise MascotaSinTitularError("El titular está dado de baja: reactivá primero al titular.")
        m.activa = True
        return m

    @transaccional
    def actualizar_historia(self, mascota_id, alergias="", antecedentes="", observaciones_generales="") -> Mascota:
        m = self.obtener(Mascota, mascota_id)
        hc = m.historia_clinica
        hc.alergias = texto(alergias)
        hc.antecedentes = texto(antecedentes)
        hc.observaciones_generales = texto(observaciones_generales)
        return m

    @transaccional
    def registrar_vacuna_aplicada(self, mascota_id, vacuna_id, fecha_aplicacion=None, lote="",
                                  dosis_numero=1) -> AplicacionVacuna:
        """Registra una vacuna en la historia clínica (por ejemplo, antecedentes de otra veterinaria)."""
        m = self.obtener(Mascota, mascota_id)
        aplicacion = AplicacionVacuna(self.obtener(Vacuna, vacuna_id), a_fecha(fecha_aplicacion), texto(lote),
                                      int(dosis_numero or 1))
        m.historia_clinica.registrar_vacuna(aplicacion)
        return aplicacion

    def buscar(self, q: str = "", especie: str = "", solo_activas: bool = False) -> list[Mascota]:
        stmt = select(Mascota).join(Mascota.titular).order_by(Mascota.nombre)
        if q:
            patron = f"%{q.strip()}%"
            stmt = stmt.where(or_(Mascota.nombre.like(patron), Mascota.raza.like(patron),
                                  Titular.apellido.like(patron), Titular.nombre.like(patron),
                                  Titular.dni.like(patron)))
        if especie:
            stmt = stmt.where(Mascota.especie == Especie(especie))
        if solo_activas:
            stmt = stmt.where(Mascota.activa.is_(True))
        return list(self.s.scalars(stmt))

    def obtener_mascota(self, mascota_id) -> Mascota:
        return self.obtener(Mascota, mascota_id)

    def vacunas_para(self, mascota: Mascota) -> list[Vacuna]:
        return list(self.s.scalars(select(Vacuna).where(Vacuna.especie == mascota.especie).order_by(Vacuna.nombre)))

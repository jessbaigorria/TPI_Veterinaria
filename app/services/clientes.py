"""Proceso 1: administrar clientes (titulares)."""
from __future__ import annotations

from sqlalchemy import or_, select

from app.domain.excepciones import VeterinariaError
from app.domain.personas import Titular
from app.services.base import ServicioBase, texto, transaccional


class ClientesService(ServicioBase):
    @transaccional
    def crear_titular(self, dni, nombre, apellido, direccion="", telefono="", email="") -> Titular:
        dni = texto(dni)
        if self.repo(Titular).buscar_por(dni=dni):
            raise VeterinariaError(f"Ya existe un titular con DNI {dni}.")
        t = Titular(dni=dni, nombre=texto(nombre), apellido=texto(apellido), direccion=texto(direccion),
                    telefono=texto(telefono), email=texto(email))
        self.s.add(t)
        return t

    @transaccional
    def actualizar_titular(self, titular_id, **datos) -> Titular:
        t = self.obtener(Titular, titular_id)
        nuevo_dni = texto(datos.get("dni", t.dni))
        otro = self.repo(Titular).buscar_por(dni=nuevo_dni)
        if otro is not None and otro is not t:
            raise VeterinariaError(f"Ya existe otro titular con DNI {nuevo_dni}.")
        for campo in ("nombre", "apellido"):
            if campo in datos and not texto(datos[campo]):
                raise VeterinariaError(f"El {campo} es obligatorio.")
        t.dni = nuevo_dni
        for campo in ("nombre", "apellido", "direccion", "telefono", "email"):
            if campo in datos:
                setattr(t, campo, texto(datos[campo]))
        return t

    @transaccional
    def dar_de_baja(self, titular_id) -> Titular:
        t = self.obtener(Titular, titular_id)
        t.dar_de_baja()
        return t

    @transaccional
    def reactivar(self, titular_id) -> Titular:
        t = self.obtener(Titular, titular_id)
        t.reactivar()
        return t

    def buscar(self, q: str = "", solo_activos: bool = False) -> list[Titular]:
        stmt = select(Titular).order_by(Titular.apellido, Titular.nombre)
        if q:
            patron = f"%{q.strip()}%"
            stmt = stmt.where(or_(Titular.dni.like(patron), Titular.nombre.like(patron),
                                  Titular.apellido.like(patron), Titular.email.like(patron)))
        if solo_activos:
            stmt = stmt.where(Titular.activo.is_(True))
        return list(self.s.scalars(stmt))

    def obtener_titular(self, titular_id) -> Titular:
        return self.obtener(Titular, titular_id)

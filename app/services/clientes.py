"""Proceso 1: administrar clientes (titulares)."""
from __future__ import annotations

from sqlalchemy import or_, select

from app.domain import validaciones
from app.domain.excepciones import DatosInvalidosError
from app.domain.personas import Titular
from app.services.base import ServicioBase, transaccional


class ClientesService(ServicioBase):
    @transaccional
    def crear_titular(self, dni, nombre, apellido, direccion="", telefono="", email="") -> Titular:
        t = Titular(dni=dni, nombre=nombre, apellido=apellido, direccion=direccion, telefono=telefono, email=email)
        self._validar_dni_unico(t.dni)
        self.s.add(t)
        return t

    @transaccional
    def actualizar_titular(self, titular_id, **datos) -> Titular:
        t = self.obtener(Titular, titular_id)
        valores = {campo: datos.get(campo, getattr(t, campo))
                   for campo in ("dni", "nombre", "apellido", "direccion", "telefono", "email")}
        dni_nuevo = validaciones.dni(valores["dni"])
        self._validar_dni_unico(dni_nuevo, excepto=t)
        t.actualizar_datos(**valores)
        return t

    def _validar_dni_unico(self, dni: str, excepto: Titular | None = None) -> None:
        otro = self.repo(Titular).buscar_por(dni=dni)
        if otro is not None and otro is not excepto:
            raise DatosInvalidosError(f"Ya existe un titular con DNI {dni} ({otro.nombre_completo()}).")

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

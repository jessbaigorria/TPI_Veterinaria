"""Proceso 4: empaquetar muestras en conservadoras (contenedores) con remito y precinto."""
from __future__ import annotations

from sqlalchemy import select

from app.domain import validaciones
from app.domain.atencion import AtencionClinica
from app.domain.clinica import Clinica
from app.domain.enums import EstadoContenedor
from app.domain.estados.estado_muestra import Extraida
from app.domain.estados.estado_remito import RemitoArmado
from app.domain.excepciones import VeterinariaError
from app.domain.laboratorio import Laboratorio, OrdenDerivacion
from app.domain.muestra import MuestraBiologica
from app.domain.transporte import Contenedor, Precinto, RemitoBiologico
from app.repositories.numerador import Numerador
from app.services.base import ServicioBase, a_float, texto, transaccional


class EmpaquetadoService(ServicioBase):
    @transaccional
    def crear_remito(self, clinica_id, laboratorio_id, contenedor_id, usuario, observaciones="") -> RemitoBiologico:
        contenedor = self.repo(Contenedor).obtener_opcional(contenedor_id)
        if contenedor is not None and contenedor in self._contenedores_reservados():
            raise VeterinariaError(f"El contenedor {contenedor.codigo} ya está asignado a un remito en armado.")
        remito = RemitoBiologico(self.obtener(Clinica, clinica_id),
                                 self.repo(Laboratorio).obtener_opcional(laboratorio_id), contenedor,
                                 usuario, numero=self.numerador.siguiente(Numerador.REMITO),
                                 observaciones=texto(observaciones))
        self.s.add(remito)
        return remito

    @transaccional
    def agregar_muestras(self, remito_id, muestra_ids, usuario) -> RemitoBiologico:
        remito = self.obtener(RemitoBiologico, remito_id)
        if not muestra_ids:
            raise VeterinariaError("Tildá al menos una muestra para empaquetar.")
        for mid in muestra_ids:
            remito.agregar_muestra(self.obtener(MuestraBiologica, mid), usuario)
        return remito

    @transaccional
    def cerrar_remito(self, remito_id, codigo_precinto, temperatura_despacho, colocado_por) -> RemitoBiologico:
        """``colocado_por``: persona que coloca el precinto (solo letras)."""
        usuario = validaciones.nombre_persona(colocado_por, "Colocado por")
        remito = self.obtener(RemitoBiologico, remito_id)
        codigo = texto(codigo_precinto) or self.numerador.siguiente(Numerador.PRECINTO)
        if codigo == self.numerador.proximo(Numerador.PRECINTO):
            self.numerador.siguiente(Numerador.PRECINTO)
        if self.repo(Precinto).buscar_por(codigo=codigo):
            raise VeterinariaError(f"Ya existe un precinto con código {codigo}.")
        temperatura = a_float(temperatura_despacho, "temperatura de despacho")
        if temperatura is None:
            raise VeterinariaError("Hay que registrar la temperatura de despacho.")
        remito.cerrar(Precinto(codigo, usuario), temperatura)
        return remito

    @transaccional
    def registrar_temperatura_despacho(self, remito_id, temperatura) -> RemitoBiologico:
        remito = self.obtener(RemitoBiologico, remito_id)
        remito.registrar_temperatura_despacho(a_float(temperatura, "temperatura de despacho"))
        return remito

    # --- consultas --------------------------------------------------------------------
    def muestras_para_empaquetar(self, clinica_id, laboratorio_id=None) -> list[MuestraBiologica]:
        """Muestras Extraídas de la clínica (y del laboratorio de destino, si se indica)."""
        stmt = (select(MuestraBiologica).join(MuestraBiologica.orden).join(OrdenDerivacion.atencion)
                .where(AtencionClinica.clinica_id == int(clinica_id),
                       MuestraBiologica.estado_codigo == Extraida.__name__,
                       OrdenDerivacion.estado.in_(["EMITIDA", "EN_PROCESO"]))
                .order_by(OrdenDerivacion.prioridad.desc(), MuestraBiologica.id))
        if laboratorio_id:
            stmt = stmt.where(OrdenDerivacion.laboratorio_id == int(laboratorio_id))
        return list(self.s.scalars(stmt))

    def contenedores_disponibles(self, clinica_id) -> list[Contenedor]:
        reservados = self._contenedores_reservados()
        stmt = select(Contenedor).where(Contenedor.clinica_id == int(clinica_id),
                                        Contenedor.estado == EstadoContenedor.DISPONIBLE).order_by(Contenedor.codigo)
        return [c for c in self.s.scalars(stmt) if c not in reservados]

    def _contenedores_reservados(self) -> set[Contenedor]:
        """Contenedores elegidos por remitos en armado todavía sin precinto."""
        stmt = select(RemitoBiologico).where(RemitoBiologico.estado_codigo == RemitoArmado.__name__)
        return {r.contenedor for r in self.s.scalars(stmt) if r.precinto is None}

    def obtener_remito(self, remito_id) -> RemitoBiologico:
        return self.obtener(RemitoBiologico, remito_id)

    def proximo_precinto(self) -> str:
        return self.numerador.proximo(Numerador.PRECINTO)

    def listar_remitos(self, clinica_id=None, laboratorio_id=None, estados: list[str] | None = None,
                       q: str = "") -> list[RemitoBiologico]:
        stmt = select(RemitoBiologico)
        if clinica_id:
            stmt = stmt.where(RemitoBiologico.clinica_origen_id == int(clinica_id))
        if laboratorio_id:
            stmt = stmt.where(RemitoBiologico.laboratorio_id == int(laboratorio_id))
        if estados:
            stmt = stmt.where(RemitoBiologico.estado_codigo.in_(estados))
        if q:
            stmt = stmt.where(RemitoBiologico.numero.like(f"%{q.strip()}%"))
        return list(self.s.scalars(stmt.order_by(RemitoBiologico.fecha_emision.desc())))

    def buscar_remito_por_numero(self, numero: str) -> RemitoBiologico | None:
        return self.repo(RemitoBiologico).buscar_por(numero=numero.strip().upper())

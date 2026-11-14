"""Proceso 3 (parte 1): agenda de turnos y registro de atenciones clínicas.

La agenda se resuelve con lo mínimo: una AtencionClinica en estado RESERVADA es un turno.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from sqlalchemy import select

from app.domain import reloj
from app.domain.atencion import AtencionClinica, Clinica, Profesional
from app.domain.enums import EstadoAtencion, TipoAtencion
from app.domain.excepciones import VeterinariaError
from app.domain.personas import AplicacionVacuna, Mascota, Vacuna
from app.services.base import ServicioBase, a_bool, a_fecha_hora, a_float, texto, transaccional
from app.services.mascotas import MascotasService


@dataclass
class ResultadoInicio:
    atencion: AtencionClinica
    vacunas_pendientes: list[Vacuna] = field(default_factory=list)

    @property
    def advertencia(self) -> str | None:
        if not self.vacunas_pendientes:
            return None
        return ("Atención iniciada con vacunas pendientes: "
                + ", ".join(v.nombre for v in self.vacunas_pendientes) + ".")


class AtencionesService(ServicioBase):
    DURACION_POR_DEFECTO = timedelta(minutes=30)

    # --- agenda (turnos) ----------------------------------------------------------------
    @transaccional
    def reservar_turno(self, mascota_id, profesional_id, clinica_id, inicio, fin=None,
                       tipo=TipoAtencion.CONSULTA, motivo="", asiste_titular=True,
                       responsable_presente="") -> AtencionClinica:
        inicio = a_fecha_hora(inicio)
        fin = a_fecha_hora(fin) or (inicio + self.DURACION_POR_DEFECTO if inicio else None)
        a = AtencionClinica(self.obtener(Mascota, mascota_id), self.obtener(Clinica, clinica_id),
                            self.obtener(Profesional, profesional_id), inicio, fin, TipoAtencion(tipo),
                            observaciones=texto(motivo), asiste_titular=a_bool(asiste_titular),
                            responsable_presente=texto(responsable_presente))
        self.s.add(a)
        return a

    @transaccional
    def iniciar(self, atencion_id) -> ResultadoInicio:
        a = self.obtener(AtencionClinica, atencion_id)
        pendientes = a.iniciar()
        return ResultadoInicio(a, pendientes)

    @transaccional
    def cancelar(self, atencion_id, motivo) -> AtencionClinica:
        a = self.obtener(AtencionClinica, atencion_id)
        a.cancelar(texto(motivo))
        return a

    # --- registro de atención sin turno (casos 1, 2 y 3 del formulario) ----------------
    @transaccional
    def registrar_sin_turno(self, profesional_id, clinica_id, tipo, mascota_id=None, nueva_mascota=None,
                            motivo="", asiste_titular=True, responsable_presente="", inicio=None,
                            duracion_minutos=30) -> ResultadoInicio:
        """Crea la atención y la inicia en el momento (urgencia/espontánea), validando superposición
        y vacunas. ``nueva_mascota`` (dict) permite el caso 2: cliente frecuente con mascota nueva."""
        if nueva_mascota:
            mascota = MascotasService(self.s).crear_mascota(**nueva_mascota)
            self.s.flush()
            mascota_id = mascota.id
        inicio = a_fecha_hora(inicio) or reloj.ahora()
        fin = inicio + timedelta(minutes=int(duracion_minutos or 30))
        a = self.reservar_turno(mascota_id, profesional_id, clinica_id, inicio, fin, tipo, motivo,
                                asiste_titular, responsable_presente)
        return ResultadoInicio(a, a.iniciar())

    @transaccional
    def finalizar(self, atencion_id, diagnostico, peso=None, importe=None, observaciones=None,
                  vacunas_aplicadas: list[dict] | None = None) -> AtencionClinica:
        """Cierra la atención. En VACUNACION registra las aplicaciones en la historia clínica."""
        a = self.obtener(AtencionClinica, atencion_id)
        for datos in vacunas_aplicadas or []:
            if a.tipo is not TipoAtencion.VACUNACION:
                raise VeterinariaError("Solo las atenciones de vacunación registran vacunas aplicadas.")
            aplicacion = AplicacionVacuna(self.obtener(Vacuna, datos["vacuna_id"]), a.fecha_hora_inicio.date(),
                                          texto(datos.get("lote")), int(datos.get("dosis_numero") or 1))
            a.historia.registrar_vacuna(aplicacion)
        a.finalizar(texto(diagnostico), a_float(peso, "peso"), importe, observaciones)
        return a

    # --- consultas ------------------------------------------------------------------
    def obtener_atencion(self, atencion_id) -> AtencionClinica:
        return self.obtener(AtencionClinica, atencion_id)

    def agenda(self, clinica_id, dia: date) -> list[AtencionClinica]:
        desde = datetime.combine(dia, datetime.min.time())
        stmt = (select(AtencionClinica)
                .where(AtencionClinica.clinica_id == int(clinica_id),
                       AtencionClinica.fecha_hora_inicio >= desde,
                       AtencionClinica.fecha_hora_inicio < desde + timedelta(days=1))
                .order_by(AtencionClinica.fecha_hora_inicio))
        return list(self.s.scalars(stmt))

    def listar(self, clinica_id=None, estado: str = "", tipo: str = "", desde=None, hasta=None,
               q: str = "", limite: int = 300) -> list[AtencionClinica]:
        stmt = select(AtencionClinica).join(AtencionClinica.historia).join(Mascota)
        if clinica_id:
            stmt = stmt.where(AtencionClinica.clinica_id == int(clinica_id))
        if estado:
            stmt = stmt.where(AtencionClinica.estado == EstadoAtencion(estado))
        if tipo:
            stmt = stmt.where(AtencionClinica.tipo == TipoAtencion(tipo))
        if desde:
            stmt = stmt.where(AtencionClinica.fecha_hora_inicio >= datetime.combine(desde, datetime.min.time()))
        if hasta:
            stmt = stmt.where(AtencionClinica.fecha_hora_inicio < datetime.combine(hasta, datetime.min.time())
                              + timedelta(days=1))
        if q:
            stmt = stmt.where(Mascota.nombre.like(f"%{q.strip()}%"))
        stmt = stmt.order_by(AtencionClinica.fecha_hora_inicio.desc()).limit(limite)
        return list(self.s.scalars(stmt))

    def profesionales(self, clinica_id) -> list[Profesional]:
        return list(self.s.scalars(select(Profesional).where(Profesional.clinica_id == int(clinica_id))
                                   .order_by(Profesional.apellido)))

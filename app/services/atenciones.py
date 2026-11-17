"""Proceso 3 (parte 1): agenda de turnos y registro de atenciones clínicas.

La agenda se resuelve con lo mínimo: una AtencionClinica en estado RESERVADA es un turno.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from sqlalchemy import select

from app.domain import reloj
from app.domain.atencion import AtencionClinica
from app.domain.clinica import Clinica, Profesional
from app.domain.enums import EstadoAtencion, TipoAtencion
from app.domain.excepciones import DatosInvalidosError, VeterinariaError
from app.domain.personas import AplicacionVacuna, Mascota, Vacuna
from app.services.base import (
    ServicioBase, a_bool, a_fecha_hora, a_float, texto, transaccional, validar_rango_fechas,
)
from app.services.mascotas import MascotasService

MEDIA_HORA = timedelta(minutes=30)


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

    # --- agenda (turnos) ----------------------------------------------------------------
    @transaccional
    def reservar_turno(self, mascota_id, profesional_id, clinica_id, inicio, fin=None,
                       tipo=TipoAtencion.CONSULTA, motivo="", asiste_titular=True,
                       responsable_presente="", nueva_mascota=None) -> AtencionClinica:
        """``nueva_mascota`` (dict): mascota del titular que todavía no estaba registrada."""
        mascota = self._mascota_elegida_o_nueva(mascota_id, nueva_mascota)
        a = AtencionClinica.reservar(mascota, self.obtener(Clinica, clinica_id),
                                     self.obtener(Profesional, profesional_id), a_fecha_hora(inicio),
                                     a_fecha_hora(fin), TipoAtencion(tipo), observaciones=texto(motivo),
                                     asiste_titular=a_bool(asiste_titular),
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
                            duracion_minutos=None) -> ResultadoInicio:
        """Crea la atención y la inicia en el momento (urgencia/espontánea), validando superposición
        y vacunas. ``nueva_mascota`` (dict) permite el caso 2: cliente frecuente con mascota nueva."""
        mascota = self._mascota_elegida_o_nueva(mascota_id, nueva_mascota)
        inicio = a_fecha_hora(inicio) or reloj.ahora().replace(second=0)
        try:
            minutos = int(duracion_minutos) if duracion_minutos not in (None, "") else None
        except ValueError as exc:
            raise DatosInvalidosError("La duración debe ser un número de minutos.") from exc
        if minutos is not None and minutos <= 0:
            raise DatosInvalidosError("La duración debe ser mayor que cero.")
        fin = inicio + timedelta(minutes=minutos) if minutos else None
        a = AtencionClinica.registrar_sin_turno(mascota, self.obtener(Clinica, clinica_id),
                                                self.obtener(Profesional, profesional_id), inicio, fin,
                                                TipoAtencion(tipo), observaciones=texto(motivo),
                                                asiste_titular=a_bool(asiste_titular),
                                                responsable_presente=texto(responsable_presente))
        self.s.add(a)
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

    def _mascota_elegida_o_nueva(self, mascota_id, nueva_mascota: dict | None) -> Mascota:
        """La mascota elegida del titular o, si no se eligió ninguna, la mascota nueva (nunca las dos)."""
        if nueva_mascota and mascota_id:
            raise DatosInvalidosError("Ya elegiste una mascota del titular: no se puede cargar además una mascota nueva.")
        if nueva_mascota:
            mascota = MascotasService(self.s).crear_mascota(**nueva_mascota)
            self.s.flush()
            return mascota
        if not mascota_id:
            raise DatosInvalidosError("Elegí una mascota del titular o completá los datos de la mascota nueva.")
        return self.obtener(Mascota, mascota_id)

    # --- consultas ------------------------------------------------------------------
    def obtener_atencion(self, atencion_id) -> AtencionClinica:
        return self.obtener(AtencionClinica, atencion_id)

    def franjas_agenda(self, dia: date) -> list[datetime]:
        """Franjas de 30 minutos del horario de atención del día (08:00, 08:30, … 18:30)."""
        inicio = datetime.combine(dia, AtencionClinica.HORA_APERTURA)
        cierre = datetime.combine(dia, AtencionClinica.HORA_CIERRE)
        return [inicio + MEDIA_HORA * i for i in range((cierre - inicio) // MEDIA_HORA)]

    @staticmethod
    def grilla_agenda(turnos: list[AtencionClinica], franjas: list[datetime]) -> dict:
        """(profesional_id, franja) → turno que la ocupa. Los cancelados no ocupan lugar (regla del dominio)."""
        return {(a.profesional_id, f): a for a in turnos for f in franjas
                if a.se_superpone_con_intervalo(f, f + MEDIA_HORA)}

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
        validar_rango_fechas(desde, hasta)
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

"""Proceso opcional: derivaciones para cirugías de alta complejidad entre clínicas de la red."""
from __future__ import annotations

from sqlalchemy import or_, select

from app.domain.atencion import AtencionClinica
from app.domain.cirugia import DerivacionCirugia
from app.domain.clinica import Clinica, Profesional
from app.domain.enums import Prioridad, RiesgoAnestesico
from app.repositories.numerador import Numerador
from app.services.base import ServicioBase, a_fecha_hora, texto, transaccional


class CirugiasService(ServicioBase):
    @transaccional
    def derivar(self, atencion_id, destino_id, tipo_cirugia, prioridad=Prioridad.NORMAL,
                diagnostico_presuntivo="", riesgo_anestesico=RiesgoAnestesico.ASA_I,
                estudios_prequirurgicos="") -> DerivacionCirugia:
        a = self.obtener(AtencionClinica, atencion_id)
        d = a.derivar_a_cirugia(self.repo(Clinica).obtener_opcional(destino_id), texto(tipo_cirugia),
                                Prioridad(prioridad or Prioridad.NORMAL),
                                diagnostico_presuntivo=texto(diagnostico_presuntivo),
                                riesgo_anestesico=RiesgoAnestesico(riesgo_anestesico or RiesgoAnestesico.ASA_I),
                                estudios_prequirurgicos=texto(estudios_prequirurgicos),
                                numero=self.numerador.siguiente(Numerador.CIRUGIA))
        self.s.add(d)
        return d

    @transaccional
    def aceptar(self, derivacion_id, cirujano_id) -> DerivacionCirugia:
        d = self.obtener(DerivacionCirugia, derivacion_id)
        d.aceptar(self.repo(Profesional).obtener_opcional(cirujano_id))
        return d

    @transaccional
    def rechazar(self, derivacion_id, motivo) -> DerivacionCirugia:
        d = self.obtener(DerivacionCirugia, derivacion_id)
        d.rechazar(texto(motivo))
        return d

    @transaccional
    def registrar_consentimiento(self, derivacion_id, usuario) -> DerivacionCirugia:
        d = self.obtener(DerivacionCirugia, derivacion_id)
        d.registrar_consentimiento(usuario)
        return d

    @transaccional
    def registrar_estudios(self, derivacion_id, estudios) -> DerivacionCirugia:
        d = self.obtener(DerivacionCirugia, derivacion_id)
        d.registrar_estudios_prequirurgicos(texto(estudios))
        return d

    @transaccional
    def programar(self, derivacion_id, fecha) -> DerivacionCirugia:
        d = self.obtener(DerivacionCirugia, derivacion_id)
        d.programar(a_fecha_hora(fecha))
        return d

    @transaccional
    def registrar_cirugia(self, derivacion_id, informe) -> DerivacionCirugia:
        d = self.obtener(DerivacionCirugia, derivacion_id)
        d.registrar_cirugia(texto(informe))
        return d

    @transaccional
    def cancelar(self, derivacion_id, motivo) -> DerivacionCirugia:
        d = self.obtener(DerivacionCirugia, derivacion_id)
        d.cancelar(texto(motivo))
        return d

    # --- consultas --------------------------------------------------------------------
    def enviadas(self, clinica_id) -> list[DerivacionCirugia]:
        stmt = (select(DerivacionCirugia).join(DerivacionCirugia.atencion)
                .where(AtencionClinica.clinica_id == int(clinica_id))
                .order_by(DerivacionCirugia.fecha_solicitud.desc()))
        return list(self.s.scalars(stmt))

    def recibidas(self, clinica_id) -> list[DerivacionCirugia]:
        stmt = (select(DerivacionCirugia).where(DerivacionCirugia.destino_id == int(clinica_id))
                .order_by(DerivacionCirugia.fecha_solicitud.desc()))
        return list(self.s.scalars(stmt))

    def obtener_derivacion(self, derivacion_id) -> DerivacionCirugia:
        return self.obtener(DerivacionCirugia, derivacion_id)

    def clinicas_alta_complejidad(self) -> list[Clinica]:
        return list(self.s.scalars(select(Clinica).where(Clinica.activa.is_(True),
                                                         Clinica.alta_complejidad.is_(True))))

    def todas_las_clinicas(self) -> list[Clinica]:
        return list(self.s.scalars(select(Clinica).where(Clinica.activa.is_(True)).order_by(Clinica.nombre)))

    def de_mi_clinica(self, clinica_id) -> list[DerivacionCirugia]:
        stmt = (select(DerivacionCirugia).join(DerivacionCirugia.atencion)
                .where(or_(AtencionClinica.clinica_id == int(clinica_id),
                           DerivacionCirugia.destino_id == int(clinica_id))))
        return list(self.s.scalars(stmt))

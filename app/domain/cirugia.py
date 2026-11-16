"""Proceso opcional: derivación a cirugía de alta complejidad (DerivacionCirugia).

Tiene estados simples (enum). Sus transiciones se validan con la tabla ``_TRANSICIONES``.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain import reloj
from app.domain.base import Base, EnumCol, a_decimal
from app.domain.clinica import Clinica, Profesional
from app.domain.enums import EstadoDerivacionCirugia, Prioridad, RiesgoAnestesico, TipoComprobante
from app.domain.excepciones import DerivacionCirugiaError, VeterinariaError
from app.domain.facturacion import ConFacturas, Factura

if TYPE_CHECKING:  # pragma: no cover
    from app.domain.atencion import AtencionClinica


class DerivacionCirugia(ConFacturas, Base):
    """Derivación a una clínica de alta complejidad de la red."""

    __tablename__ = "derivacion_cirugia"

    _E = EstadoDerivacionCirugia
    _TRANSICIONES = {
        _E.SOLICITADA: {_E.ACEPTADA, _E.RECHAZADA},
        _E.ACEPTADA: {_E.PROGRAMADA, _E.CANCELADA},
        _E.PROGRAMADA: {_E.REALIZADA, _E.CANCELADA},
        _E.REALIZADA: set(),
        _E.RECHAZADA: set(),
        _E.CANCELADA: set(),
    }
    _ESTADOS_QUE_ADMITEN_CONSENTIMIENTO = {_E.SOLICITADA, _E.ACEPTADA}

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[Optional[str]] = mapped_column(String(20), unique=True)
    fecha_solicitud: Mapped[datetime] = mapped_column(DateTime)
    tipo_cirugia: Mapped[str] = mapped_column(String(160))
    diagnostico_presuntivo: Mapped[str] = mapped_column(Text, default="")
    prioridad: Mapped[Prioridad] = mapped_column(EnumCol(Prioridad))
    riesgo_anestesico: Mapped[RiesgoAnestesico] = mapped_column(EnumCol(RiesgoAnestesico))
    estudios_prequirurgicos: Mapped[str] = mapped_column(Text, default="")
    consentimiento_firmado: Mapped[bool] = mapped_column(Boolean, default=False)
    consentimiento_registrado_por: Mapped[str] = mapped_column(String(120), default="")
    fecha_programada: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    estado: Mapped[EstadoDerivacionCirugia] = mapped_column(EnumCol(EstadoDerivacionCirugia))
    motivo_rechazo: Mapped[str] = mapped_column(Text, default="")
    informe_quirurgico: Mapped[str] = mapped_column(Text, default="")
    atencion_id: Mapped[int] = mapped_column(ForeignKey("atencion_clinica.id"), nullable=False)
    destino_id: Mapped[int] = mapped_column(ForeignKey("clinica.id"), nullable=False)
    cirujano_id: Mapped[Optional[int]] = mapped_column(ForeignKey("profesional.id"), nullable=True)

    atencion: Mapped["AtencionClinica"] = relationship(back_populates="derivaciones")
    destino: Mapped[Clinica] = relationship()
    cirujano: Mapped[Optional[Profesional]] = relationship()
    facturas: Mapped[list[Factura]] = relationship(back_populates="derivacion")

    def __init__(self, atencion: "AtencionClinica", destino: Clinica, tipo_cirugia: str,
                 prioridad: Prioridad = Prioridad.NORMAL, diagnostico_presuntivo: str = "",
                 riesgo_anestesico: RiesgoAnestesico = RiesgoAnestesico.ASA_I,
                 estudios_prequirurgicos: str = "", numero: str | None = None):
        self._validar_destino(destino)
        if not (tipo_cirugia or "").strip():
            raise DerivacionCirugiaError("Hay que indicar el tipo de cirugía.")
        self.numero = numero
        self.fecha_solicitud = reloj.ahora()
        self.tipo_cirugia = tipo_cirugia.strip()
        self.prioridad = Prioridad(prioridad)
        self.diagnostico_presuntivo = diagnostico_presuntivo or ""
        self.riesgo_anestesico = RiesgoAnestesico(riesgo_anestesico)
        self.estudios_prequirurgicos = estudios_prequirurgicos or ""
        self.consentimiento_firmado = False
        self.consentimiento_registrado_por = ""
        self.estado = EstadoDerivacionCirugia.SOLICITADA
        self.motivo_rechazo = ""
        self.informe_quirurgico = ""
        self.destino = destino
        self.atencion = atencion

    @staticmethod
    def _validar_destino(destino: Clinica | None) -> None:
        """Validación 6 (opcional): el destino debe ser una clínica activa de alta complejidad."""
        if destino is None:
            raise DerivacionCirugiaError("Hay que elegir la clínica de destino.")
        if not destino.alta_complejidad:
            raise DerivacionCirugiaError(f"{destino.nombre} no está habilitada para cirugías de alta complejidad.")
        if not destino.activa:
            raise DerivacionCirugiaError(f"{destino.nombre} no está activa.")

    @property
    def mascota(self):
        return self.atencion.mascota

    @property
    def clinica_origen(self) -> Clinica:
        return self.atencion.clinica

    # --- métodos del diagrama -------------------------------------------------
    def registrar_consentimiento(self, usuario: str) -> None:
        if self.estado not in self._ESTADOS_QUE_ADMITEN_CONSENTIMIENTO:
            raise DerivacionCirugiaError(
                f"No se puede registrar el consentimiento: la derivación está {self.estado.etiqueta.lower()}."
            )
        self.consentimiento_firmado = True
        self.consentimiento_registrado_por = usuario or ""

    def aceptar(self, cirujano: Profesional) -> None:
        self._validar_transicion(self._E.ACEPTADA)
        if cirujano is None or cirujano.clinica is not self.destino:
            raise DerivacionCirugiaError(f"El cirujano debe pertenecer a {self.destino.nombre}.")
        self.cirujano = cirujano
        self.estado = self._E.ACEPTADA

    def rechazar(self, motivo: str) -> None:
        self._validar_transicion(self._E.RECHAZADA)
        if not (motivo or "").strip():
            raise DerivacionCirugiaError("Para rechazar la derivación hay que indicar el motivo.")
        self.motivo_rechazo = motivo.strip()
        self.estado = self._E.RECHAZADA

    def programar(self, fecha: datetime) -> None:
        self._validar_transicion(self._E.PROGRAMADA)
        if not self.consentimiento_firmado:
            raise DerivacionCirugiaError("No se puede programar la cirugía sin el consentimiento firmado del titular.")
        riesgo_alto = self.riesgo_anestesico.nivel >= RiesgoAnestesico.ASA_III.nivel
        if riesgo_alto and not self.estudios_prequirurgicos.strip():
            raise DerivacionCirugiaError(
                f"Con riesgo anestésico {self.riesgo_anestesico.etiqueta} hay que cargar los estudios "
                "prequirúrgicos antes de programar."
            )
        if fecha is None or fecha < reloj.ahora():
            raise DerivacionCirugiaError("La fecha programada debe ser futura.")
        self.fecha_programada = fecha
        self.estado = self._E.PROGRAMADA

    def registrar_cirugia(self, informe: str) -> None:
        self._validar_transicion(self._E.REALIZADA)
        if not (informe or "").strip():
            raise DerivacionCirugiaError("Hay que cargar el informe quirúrgico.")
        self.informe_quirurgico = informe.strip()
        self.estado = self._E.REALIZADA

    def cancelar(self, motivo: str) -> None:
        self._validar_transicion(self._E.CANCELADA)
        if not (motivo or "").strip():
            raise DerivacionCirugiaError("Para cancelar hay que indicar el motivo.")
        self.motivo_rechazo = f"Cancelada: {motivo.strip()}"
        self.estado = self._E.CANCELADA

    def emitir_comprobante(self, importe=None, numero: str | None = None) -> Factura:
        if self.estado is not self._E.REALIZADA:
            raise DerivacionCirugiaError("Solo se facturan cirugías realizadas.")
        importe = a_decimal(importe)
        if importe <= 0:
            raise VeterinariaError("Hay que ingresar el importe de la cirugía.")
        self._validar_sin_factura_vigente("Esta cirugía ya fue facturada")
        factura = Factura(tipo=TipoComprobante.CIRUGIA, titular=self.atencion.titular, clinica=self.destino,
                          numero=numero, derivacion=self)
        factura.agregar_item(f"Cirugía: {self.tipo_cirugia} – {self.mascota.nombre}", 1, importe)
        factura.calcular_total()
        return factura

    # --- auxiliares (ver DECISIONES.md) --------------------------------------------
    def registrar_estudios_prequirurgicos(self, estudios: str) -> None:
        if self.estado not in self._ESTADOS_QUE_ADMITEN_CONSENTIMIENTO:
            raise DerivacionCirugiaError("Los estudios se cargan antes de programar la cirugía.")
        self.estudios_prequirurgicos = (estudios or "").strip()

    def transiciones_posibles(self) -> set[EstadoDerivacionCirugia]:
        return set(self._TRANSICIONES[self.estado])

    def admite_consentimiento(self) -> bool:
        return self.estado in self._ESTADOS_QUE_ADMITEN_CONSENTIMIENTO and not self.consentimiento_firmado

    def esta_realizada(self) -> bool:
        return self.estado is EstadoDerivacionCirugia.REALIZADA

    def _validar_transicion(self, nuevo: EstadoDerivacionCirugia) -> None:
        if nuevo not in self._TRANSICIONES[self.estado]:
            raise DerivacionCirugiaError(
                f"La derivación {self.numero or ''} está {self.estado.etiqueta.lower()}: "
                f"no puede pasar a {nuevo.etiqueta.lower()}."
            )

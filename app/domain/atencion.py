"""Atención clínica y derivación a cirugía: Clinica, Profesional, AtencionClinica, DerivacionCirugia.

AtencionClinica y DerivacionCirugia tienen estados simples (enum). Sus transiciones
se validan con una tabla ``_TRANSICIONES`` (no con if por estado).
"""
from __future__ import annotations

from datetime import datetime, time, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain import reloj, validaciones
from app.domain.base import Base, Dinero, EnumCol, a_decimal
from app.domain.enums import (
    EstadoAtencion, EstadoDerivacionCirugia, Prioridad, RiesgoAnestesico,
    TipoAtencion, TipoComprobante,
)
from app.domain.excepciones import (
    AtencionNoModificableError, DatosInvalidosError, DerivacionCirugiaError, TurnoSuperpuestoError, VacunasPendientesError, VeterinariaError,
)
from app.domain.facturacion import ConFacturas, Factura
from app.domain.personas import HistoriaClinica, Vacuna, _en_periodo

if TYPE_CHECKING:  # pragma: no cover
    from app.domain.laboratorio import Laboratorio, OrdenDerivacion, TipoAnalisis
    from app.domain.personas import Mascota, Titular
    from app.domain.transporte import Contenedor


class Clinica(Base):
    __tablename__ = "clinica"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), unique=True)
    direccion: Mapped[str] = mapped_column(String(160), default="")
    localidad: Mapped[str] = mapped_column(String(80), default="")
    telefono: Mapped[str] = mapped_column(String(40), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    alta_complejidad: Mapped[bool] = mapped_column(Boolean, default=False)

    profesionales: Mapped[list["Profesional"]] = relationship(back_populates="clinica",
                                                              order_by="Profesional.apellido")
    atenciones: Mapped[list["AtencionClinica"]] = relationship(back_populates="clinica")
    contenedores: Mapped[list["Contenedor"]] = relationship(back_populates="clinica",
                                                            order_by="Contenedor.codigo")

    def agregar_profesional(self, p: "Profesional") -> None:
        if p not in self.profesionales:
            self.profesionales.append(p)

    def atenciones_en_periodo(self, desde, hasta) -> list["AtencionClinica"]:
        return sorted((a for a in self.atenciones if _en_periodo(a.fecha_hora_inicio, desde, hasta)),
                      key=lambda a: a.fecha_hora_inicio)

    def __repr__(self) -> str:
        return f"<Clinica {self.nombre}>"


class Profesional(Base):
    __tablename__ = "profesional"

    id: Mapped[int] = mapped_column(primary_key=True)
    legajo: Mapped[str] = mapped_column(String(20), unique=True)
    matricula: Mapped[str] = mapped_column(String(20))
    dni: Mapped[str] = mapped_column(String(20))
    nombre: Mapped[str] = mapped_column(String(80))
    apellido: Mapped[str] = mapped_column(String(80))
    especialidad: Mapped[str] = mapped_column(String(80), default="Clínica general")
    telefono: Mapped[str] = mapped_column(String(40), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    clinica_id: Mapped[int] = mapped_column(ForeignKey("clinica.id"), nullable=False)

    clinica: Mapped[Clinica] = relationship(back_populates="profesionales")
    atenciones: Mapped[list["AtencionClinica"]] = relationship(back_populates="profesional")

    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellido}"

    def esta_disponible(self, inicio: datetime, fin: datetime,
                        excluir: "AtencionClinica | None" = None) -> bool:
        """Validación 4: recorre las atenciones del profesional buscando superposiciones."""
        return not any(a.se_superpone_con_intervalo(inicio, fin) for a in self.atenciones if a is not excluir)

    def __repr__(self) -> str:
        return f"<Profesional {self.legajo} {self.nombre_completo()}>"


class AtencionClinica(ConFacturas, Base):
    """La atención en estado RESERVADA funciona como turno de la agenda."""

    __tablename__ = "atencion_clinica"

    _TRANSICIONES = {
        EstadoAtencion.RESERVADA: {EstadoAtencion.EN_PROGRESO, EstadoAtencion.CANCELADA},
        EstadoAtencion.EN_PROGRESO: {EstadoAtencion.FINALIZADA},
        EstadoAtencion.FINALIZADA: set(),
        EstadoAtencion.CANCELADA: set(),
    }
    _ESTADOS_QUE_OCUPAN_AGENDA = {EstadoAtencion.RESERVADA, EstadoAtencion.EN_PROGRESO, EstadoAtencion.FINALIZADA}
    _ESTADOS_REALIZADOS = {EstadoAtencion.EN_PROGRESO, EstadoAtencion.FINALIZADA}
    # Órdenes de laboratorio y derivaciones a cirugía solo mientras la atención está en curso.
    _ESTADOS_QUE_ADMITEN_DERIVAR = {EstadoAtencion.EN_PROGRESO}
    _TIPOS_QUE_BLOQUEAN_POR_VACUNAS = {TipoAtencion.CONSULTA, TipoAtencion.CONTROL}
    _TIPOS_CON_ADVERTENCIA = {TipoAtencion.URGENCIA, TipoAtencion.CIRUGIA, TipoAtencion.OTRO}

    # Horario de atención y duración máxima por tipo (ronda de correcciones, ver DECISIONES.md).
    HORA_APERTURA = time(8, 0)
    HORA_CIERRE = time(19, 0)
    DURACION_MAXIMA_MINUTOS = {
        TipoAtencion.CONSULTA: 30, TipoAtencion.CONTROL: 30, TipoAtencion.VACUNACION: 30,
        TipoAtencion.CIRUGIA: 60, TipoAtencion.OTRO: 60, TipoAtencion.URGENCIA: 60,
    }
    # Las urgencias no se reservan: se registran como atención sin turno.
    TIPOS_RESERVABLES = (TipoAtencion.CONSULTA, TipoAtencion.CONTROL, TipoAtencion.VACUNACION,
                         TipoAtencion.CIRUGIA, TipoAtencion.OTRO)

    id: Mapped[int] = mapped_column(primary_key=True)
    fecha_hora_inicio: Mapped[datetime] = mapped_column(DateTime, index=True)
    fecha_hora_fin: Mapped[datetime] = mapped_column(DateTime)
    tipo: Mapped[TipoAtencion] = mapped_column(EnumCol(TipoAtencion))
    estado: Mapped[EstadoAtencion] = mapped_column(EnumCol(EstadoAtencion))
    diagnostico: Mapped[str] = mapped_column(Text, default="")      # lo que dice el médico
    observaciones: Mapped[str] = mapped_column(Text, default="")    # lo que dice el cliente
    peso_registrado: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    importe: Mapped[Decimal] = mapped_column(Dinero, default=Decimal("0"))
    asiste_titular: Mapped[bool] = mapped_column(Boolean, default=True)
    responsable_presente: Mapped[str] = mapped_column(String(120), default="")
    historia_id: Mapped[int] = mapped_column(ForeignKey("historia_clinica.id"), nullable=False)
    clinica_id: Mapped[int] = mapped_column(ForeignKey("clinica.id"), nullable=False)
    profesional_id: Mapped[int] = mapped_column(ForeignKey("profesional.id"), nullable=False)

    historia: Mapped[HistoriaClinica] = relationship(back_populates="atenciones")
    clinica: Mapped[Clinica] = relationship(back_populates="atenciones")
    profesional: Mapped[Profesional] = relationship(back_populates="atenciones")
    ordenes: Mapped[list["OrdenDerivacion"]] = relationship(back_populates="atencion",
                                                            order_by="OrdenDerivacion.id")
    derivaciones: Mapped[list["DerivacionCirugia"]] = relationship(back_populates="atencion",
                                                                   order_by="DerivacionCirugia.id")
    facturas: Mapped[list[Factura]] = relationship(back_populates="atencion")

    def __init__(self, mascota: "Mascota", clinica: Clinica, profesional: Profesional,
                 fecha_hora_inicio: datetime, fecha_hora_fin: datetime | None = None,
                 tipo: TipoAtencion = TipoAtencion.CONSULTA, observaciones: str = "",
                 asiste_titular: bool = True, responsable_presente: str = ""):
        if mascota is None:
            raise VeterinariaError("Hay que elegir la mascota.")
        if not mascota.activa:
            raise VeterinariaError(f"{mascota.nombre} está dada de baja.")
        if profesional is None or clinica is None:
            raise VeterinariaError("Hay que elegir la clínica y el profesional.")
        if profesional.clinica is not clinica:
            raise VeterinariaError(f"{profesional.nombre_completo()} no trabaja en {clinica.nombre}.")
        if fecha_hora_inicio is None:
            raise DatosInvalidosError("Hay que indicar la fecha y hora de inicio.")
        tipo = TipoAtencion(tipo)
        fecha_hora_fin = fecha_hora_fin or self.fin_sugerido(fecha_hora_inicio, tipo)
        self._validar_horario(fecha_hora_inicio, fecha_hora_fin, tipo)
        if not asiste_titular:
            if not (responsable_presente or "").strip():
                raise DatosInvalidosError("Si no asiste el titular hay que indicar quién es el responsable presente.")
            responsable_presente = validaciones.nombre_persona(responsable_presente, "Responsable presente")
        # Validación 4: sin superposición de turnos del profesional.
        if not profesional.esta_disponible(fecha_hora_inicio, fecha_hora_fin):
            choque = next(a for a in profesional.atenciones
                          if a.se_superpone_con_intervalo(fecha_hora_inicio, fecha_hora_fin))
            raise TurnoSuperpuestoError(
                f"{profesional.nombre_completo()} ya tiene un turno de {choque.fecha_hora_inicio:%H:%M} a "
                f"{choque.fecha_hora_fin:%H:%M} del {choque.fecha_hora_inicio:%d/%m/%Y} "
                f"({choque.mascota.nombre}). Elegí otro horario u otro profesional."
            )
        self.fecha_hora_inicio = fecha_hora_inicio
        self.fecha_hora_fin = fecha_hora_fin
        self.tipo = tipo
        self.estado = EstadoAtencion.RESERVADA
        self.observaciones = observaciones or ""
        self.diagnostico = ""
        self.importe = Decimal("0")
        self.asiste_titular = bool(asiste_titular)
        self.responsable_presente = "" if asiste_titular else responsable_presente.strip()
        self.clinica = clinica
        self.profesional = profesional
        mascota.historia_clinica.agregar_atencion(self)

    # --- fábricas: turno reservado o atención sin turno (ver DECISIONES.md) --------------
    @classmethod
    def reservar(cls, mascota: "Mascota", clinica: Clinica, profesional: Profesional, fecha_hora_inicio: datetime,
                 fecha_hora_fin: datetime | None = None, tipo: TipoAtencion = TipoAtencion.CONSULTA,
                 **kwargs) -> "AtencionClinica":
        """Turno de la agenda: solo para hoy en un horario posterior al actual o para fechas futuras,
        y nunca de tipo urgencia."""
        tipo = TipoAtencion(tipo)
        if tipo not in cls.TIPOS_RESERVABLES:
            raise DatosInvalidosError("Las urgencias no se reservan: se registran como atención sin turno previo.")
        if fecha_hora_inicio is not None and fecha_hora_inicio <= reloj.ahora():
            raise DatosInvalidosError(
                "Los turnos se reservan para hoy en un horario posterior al actual o para una fecha futura."
            )
        return cls(mascota, clinica, profesional, fecha_hora_inicio, fecha_hora_fin, tipo, **kwargs)

    @classmethod
    def registrar_sin_turno(cls, mascota: "Mascota", clinica: Clinica, profesional: Profesional,
                            fecha_hora_inicio: datetime | None = None, fecha_hora_fin: datetime | None = None,
                            tipo: TipoAtencion = TipoAtencion.URGENCIA, **kwargs) -> "AtencionClinica":
        """Atención sin turno previo: la fecha y hora de inicio es la actual (por defecto) o una pasada."""
        fecha_hora_inicio = fecha_hora_inicio or reloj.ahora().replace(second=0)
        if fecha_hora_inicio > reloj.ahora():
            raise DatosInvalidosError("Una atención sin turno previo no puede tener fecha y hora de inicio futura.")
        return cls(mascota, clinica, profesional, fecha_hora_inicio, fecha_hora_fin, tipo, **kwargs)

    @classmethod
    def duracion_maxima(cls, tipo: TipoAtencion) -> timedelta:
        return timedelta(minutes=cls.DURACION_MAXIMA_MINUTOS[TipoAtencion(tipo)])

    @classmethod
    def fin_sugerido(cls, inicio: datetime, tipo: TipoAtencion) -> datetime:
        """Inicio + duración máxima del tipo, sin pasar del cierre (19:00)."""
        cierre = datetime.combine(inicio.date(), cls.HORA_CIERRE)
        return min(inicio + cls.duracion_maxima(tipo), max(cierre, inicio + timedelta(minutes=5)))

    @classmethod
    def _validar_horario(cls, inicio: datetime, fin: datetime, tipo: TipoAtencion) -> None:
        if fin <= inicio:
            raise DatosInvalidosError("La hora de fin debe ser posterior a la de inicio.")
        maximo = cls.DURACION_MAXIMA_MINUTOS[tipo]
        if fin - inicio > timedelta(minutes=maximo):
            raise DatosInvalidosError(f"Una atención de tipo {tipo.etiqueta.lower()} dura como máximo {maximo} minutos.")
        if (inicio.time() < cls.HORA_APERTURA or fin.date() != inicio.date() or fin.time() > cls.HORA_CIERRE):
            raise DatosInvalidosError("El horario de atención es de 08:00 a 19:00: la atención debe empezar y "
                                      "terminar dentro de ese horario.")

    # --- propiedades de navegación ----------------------------------------------
    @property
    def mascota(self) -> "Mascota":
        return self.historia.mascota

    @property
    def titular(self) -> "Titular":
        return self.historia.mascota.titular

    # --- métodos del diagrama -------------------------------------------------
    def iniciar(self) -> list[Vacuna]:
        """RESERVADA → EN_PROGRESO. Corre el control de vacunas (validación 5).

        Devuelve las vacunas pendientes cuando se permite atender igual (urgencia o vacunación).
        """
        self._validar_transicion(EstadoAtencion.EN_PROGRESO)
        pendientes = self.verificar_vacunas_obligatorias()
        if pendientes and self.tipo in self._TIPOS_CON_ADVERTENCIA:
            nota = "Atendida por urgencia con vacunas pendientes: " + ", ".join(v.nombre for v in pendientes)
            self.observaciones = f"{self.observaciones}\n{nota}".strip()
        self.estado = EstadoAtencion.EN_PROGRESO
        return pendientes

    def finalizar(self, diagnostico: str, peso_registrado: float | None = None,
                  importe=None, observaciones: str | None = None) -> None:
        """EN_PROGRESO → FINALIZADA. Exige diagnóstico e importe mayor a cero; después la atención no se modifica."""
        self._validar_transicion(EstadoAtencion.FINALIZADA)
        if not (diagnostico or "").strip():
            raise DatosInvalidosError("Para finalizar la atención hay que cargar el diagnóstico.")
        self.diagnostico = diagnostico.strip()
        if observaciones is not None:
            self.observaciones = observaciones
        if peso_registrado:
            self.peso_registrado = float(peso_registrado)
            self.mascota.peso = float(peso_registrado)
        importe = a_decimal(importe) if importe not in (None, "") else None
        if importe is None or importe <= 0:
            raise DatosInvalidosError("El importe es obligatorio y debe ser mayor a cero.")
        self.importe = importe
        self.estado = EstadoAtencion.FINALIZADA

    def cancelar(self, motivo: str) -> None:
        self._validar_transicion(EstadoAtencion.CANCELADA)
        if not (motivo or "").strip():
            raise VeterinariaError("Para cancelar un turno hay que indicar el motivo.")
        self.observaciones = f"{self.observaciones}\nCancelado: {motivo.strip()}".strip()
        self.estado = EstadoAtencion.CANCELADA

    def se_superpone_con(self, otra: "AtencionClinica") -> bool:
        if otra is self or otra.estado not in self._ESTADOS_QUE_OCUPAN_AGENDA:
            return False
        return self.se_superpone_con_intervalo(otra.fecha_hora_inicio, otra.fecha_hora_fin)

    def verificar_vacunas_obligatorias(self) -> list[Vacuna]:
        """Validación 5. CONSULTA/CONTROL con pendientes → VacunasPendientesError.
        URGENCIA y VACUNACION se permiten y devuelven la lista de pendientes."""
        pendientes = self.historia.vacunas_pendientes(fecha=self.fecha_hora_inicio.date())
        if pendientes and self.tipo in self._TIPOS_QUE_BLOQUEAN_POR_VACUNAS:
            raise VacunasPendientesError(
                f"{self.mascota.nombre} tiene vacunas obligatorias pendientes o vencidas: "
                + ", ".join(v.nombre for v in pendientes)
                + ". Registrá una atención de VACUNACIÓN antes de la consulta/control.",
                vacunas=pendientes, mascota=self.mascota,
            )
        return pendientes

    def emitir_orden_derivacion(self, lab: "Laboratorio", analisis: list["TipoAnalisis"],
                                prioridad: Prioridad = Prioridad.NORMAL, observaciones: str = "",
                                numero: str | None = None) -> "OrdenDerivacion":
        from app.domain.laboratorio import OrdenDerivacion

        self._validar_admite_derivar("emitir una orden de laboratorio")
        orden = OrdenDerivacion(atencion=self, laboratorio=lab, prioridad=prioridad,
                                observaciones=observaciones, numero=numero)
        for t in analisis or []:
            orden.agregar_analisis(t)
        if not orden.analisis:
            raise VeterinariaError("La orden debe solicitar al menos un análisis.")
        self.ordenes.append(orden)
        return orden

    def derivar_a_cirugia(self, destino: Clinica, tipo: str, prioridad: Prioridad = Prioridad.NORMAL,
                          diagnostico_presuntivo: str = "",
                          riesgo_anestesico: RiesgoAnestesico = RiesgoAnestesico.ASA_I,
                          estudios_prequirurgicos: str = "", numero: str | None = None) -> "DerivacionCirugia":
        self._validar_admite_derivar("derivar a cirugía")
        derivacion = DerivacionCirugia(atencion=self, destino=destino, tipo_cirugia=tipo, prioridad=prioridad,
                                       diagnostico_presuntivo=diagnostico_presuntivo,
                                       riesgo_anestesico=riesgo_anestesico,
                                       estudios_prequirurgicos=estudios_prequirurgicos, numero=numero)
        self.derivaciones.append(derivacion)
        return derivacion

    def emitir_comprobante_atencion(self, numero: str | None = None) -> Factura:
        if self.estado is not EstadoAtencion.FINALIZADA:
            raise VeterinariaError("Solo se facturan atenciones finalizadas.")
        if self.importe is None or self.importe <= 0:
            raise VeterinariaError("La atención no tiene importe para facturar.")
        self._validar_sin_factura_vigente("Esta atención ya fue facturada")
        factura = Factura(tipo=TipoComprobante.ATENCION_CLINICA, titular=self.titular, clinica=self.clinica,
                          numero=numero, atencion=self)
        factura.agregar_item(f"{self.tipo.etiqueta} – {self.mascota.nombre} "
                             f"({self.fecha_hora_inicio:%d/%m/%Y})", 1, self.importe)
        factura.calcular_total()
        return factura

    # --- auxiliares ------------------------------------------------------------
    def se_superpone_con_intervalo(self, inicio: datetime, fin: datetime) -> bool:
        """Dos intervalos se superponen si a.inicio < b.fin y b.inicio < a.fin (se ignoran CANCELADAS)."""
        if self.estado not in self._ESTADOS_QUE_OCUPAN_AGENDA:
            return False
        return self.fecha_hora_inicio < fin and inicio < self.fecha_hora_fin

    def esta_realizada(self) -> bool:
        return self.estado in self._ESTADOS_REALIZADOS

    def admite_derivaciones(self) -> bool:
        """True si se pueden emitir órdenes de laboratorio o derivar a cirugía (solo EN_PROGRESO)."""
        return self.estado in self._ESTADOS_QUE_ADMITEN_DERIVAR

    def validar_admite_derivaciones(self, accion: str) -> None:
        """Lanza AtencionNoModificableError si la atención no está en curso."""
        self._validar_admite_derivar(accion)

    def transiciones_posibles(self) -> set[EstadoAtencion]:
        return set(self._TRANSICIONES[self.estado])

    def esta_finalizada(self) -> bool:
        return self.estado is EstadoAtencion.FINALIZADA

    def bloqueara_por_vacunas(self) -> bool:
        """True si todavía no se inició y su tipo bloquea con vacunas pendientes (para avisar en la UI)."""
        return (EstadoAtencion.EN_PROGRESO in self._TRANSICIONES[self.estado]
                and self.tipo in self._TIPOS_QUE_BLOQUEAN_POR_VACUNAS)

    def _validar_transicion(self, nuevo: EstadoAtencion) -> None:
        if self.estado is EstadoAtencion.FINALIZADA:
            raise AtencionNoModificableError("Esta atención ya está finalizada y no se puede modificar.")
        if nuevo not in self._TRANSICIONES[self.estado]:
            raise VeterinariaError(
                f"La atención está {self.estado.etiqueta.lower()}: no puede pasar a {nuevo.etiqueta.lower()}."
            )

    def _validar_admite_derivar(self, accion: str) -> None:
        if self.estado is EstadoAtencion.FINALIZADA:
            raise AtencionNoModificableError(f"Esta atención ya está finalizada: no se puede {accion}.")
        if self.estado not in self._ESTADOS_QUE_ADMITEN_DERIVAR:
            raise AtencionNoModificableError(f"Para {accion} la atención tiene que estar en curso.")

    def __repr__(self) -> str:
        return f"<AtencionClinica {self.id} {self.tipo.value} {self.estado.value}>"


class DerivacionCirugia(ConFacturas, Base):
    """Proceso opcional: derivación a una clínica de alta complejidad de la red."""

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

    atencion: Mapped[AtencionClinica] = relationship(back_populates="derivaciones")
    destino: Mapped[Clinica] = relationship()
    cirujano: Mapped[Optional[Profesional]] = relationship()
    facturas: Mapped[list[Factura]] = relationship(back_populates="derivacion")

    def __init__(self, atencion: AtencionClinica, destino: Clinica, tipo_cirugia: str,
                 prioridad: Prioridad = Prioridad.NORMAL, diagnostico_presuntivo: str = "",
                 riesgo_anestesico: RiesgoAnestesico = RiesgoAnestesico.ASA_I,
                 estudios_prequirurgicos: str = "", numero: str | None = None):
        # Validación 6 (opcional): el destino debe ser de alta complejidad.
        if destino is None:
            raise DerivacionCirugiaError("Hay que elegir la clínica de destino.")
        if not destino.alta_complejidad:
            raise DerivacionCirugiaError(
                f"{destino.nombre} no está habilitada para cirugías de alta complejidad."
            )
        if not destino.activa:
            raise DerivacionCirugiaError(f"{destino.nombre} no está activa.")
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
        if self.riesgo_anestesico.nivel >= RiesgoAnestesico.ASA_III.nivel and not self.estudios_prequirurgicos.strip():
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

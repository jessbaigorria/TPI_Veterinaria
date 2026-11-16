"""Etapa 7 del seed: la agenda de hoy y mañana (la atención RESERVADA es el turno)."""
from __future__ import annotations

from datetime import datetime, time, timedelta

from app.domain.enums import TipoAtencion
from app.seed.datos import TURNOS_RESERVADOS
from app.seed.sembrador import Sembrador


def sembrar_agenda_de_hoy(sem: Sembrador) -> None:
    c, p, m = sem.clinica, sem.prof, sem.mascota
    sem.en(0, 7, 30)
    sem.atender(0, 8, c["centro"], m["Kira"], TipoAtencion.CONTROL, prof=p["perez"], minuto=30)
    sem.atender(0, 8, c["norte"], m["Simba"], TipoAtencion.CONSULTA, prof=p["medina"])
    for dia, hora, minuto, clinica, prof, mascota, tipo, motivo in TURNOS_RESERVADOS:
        inicio = sem.horario_libre(p[prof], datetime.combine(sem.hoy + timedelta(days=dia), time(hora, minuto)))
        sem.ate.reservar_turno(m[mascota].id, p[prof].id, c[clinica].id, inicio, inicio + timedelta(minutes=30),
                               tipo, motivo)
    # Una atención en curso (iniciada a las 9:00 por la Dra. Pérez).
    primero = next(a for a in sem.ate.agenda(c["centro"].id, sem.hoy)
                   if a.profesional is p["perez"] and a.fecha_hora_inicio.hour == 9)
    sem.en(0, 9, 0)
    sem.ate.iniciar(primero.id)

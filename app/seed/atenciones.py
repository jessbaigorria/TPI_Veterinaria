"""Etapa 3 del seed: atenciones de rutina de los últimos 60 días, urgencias y un turno cancelado."""
from __future__ import annotations

from datetime import datetime, time, timedelta

from app.domain.enums import TipoAtencion
from app.seed.datos import CON_VACUNAS_PENDIENTES, TIPOS_DE_RUTINA
from app.seed.sembrador import Sembrador

DOMINGO = 6


def sembrar_atenciones_de_rutina(sem: Sembrador) -> None:
    c, p, m = sem.clinica, sem.prof, sem.mascota
    _rutina_de_60_dias(sem)
    # Rocco y Mía: solo urgencias (quedan con vacunas pendientes y advertencia en observaciones).
    sem.atender(-50, 18, c["centro"], m["Rocco"], TipoAtencion.URGENCIA, prof=p["perez"],
                diagnostico="Herida cortante en almohadilla")
    sem.atender(-22, 18, c["norte"], m["Mía"], TipoAtencion.URGENCIA, prof=p["medina"],
                diagnostico="Vómitos por ingesta de cuerpo extraño", asiste_titular=False,
                responsable="Vecina autorizada por la titular")
    # Un turno cancelado.
    sem.en(-30, 8)
    turno = sem.ate.reservar_turno(m["Nina"].id, p["diaz"].id, c["centro"].id,
                                   datetime.combine(sem.hoy + timedelta(days=-29), time(16, 30)), tipo="CONTROL")
    sem.ate.cancelar(turno.id, "La titular avisó que no puede asistir")


def _rutina_de_60_dias(sem: Sembrador) -> None:
    """~40 atenciones en las 3 clínicas (de lunes a sábado), con mascotas que tienen las vacunas al día."""
    al_dia = [mascota for nombre, mascota in sem.mascota.items() if nombre not in CON_VACUNAS_PENDIENTES]
    for dia in range(-60, 0):
        if (sem.hoy + timedelta(days=dia)).weekday() == DOMINGO:
            continue
        for clinica in sem.clinica.values():
            if sem.rnd.random() < 0.24:
                tipo = sem.rnd.choice(TIPOS_DE_RUTINA)
                mascota = sem.rnd.choice(al_dia)
                sem.atender(dia, sem.rnd.choice([9, 10, 11, 12]), clinica, mascota, tipo,
                            asiste_titular=sem.rnd.random() > 0.15, responsable="Familiar del titular")

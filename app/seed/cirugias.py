"""Etapa 5 del seed: derivaciones a cirugía al Hospital Veterinario Sur, una por estado."""
from __future__ import annotations

from datetime import datetime, time, timedelta

from app.domain import reloj
from app.domain.enums import FormaPago, Prioridad, RiesgoAnestesico, TipoAtencion
from app.seed.sembrador import Sembrador


def sembrar_cirugias(sem: Sembrador) -> None:
    _realizada_y_pagada(sem)
    _realizada_pendiente_de_cobro(sem)
    _rechazada(sem)
    _cancelada(sem)
    _programada(sem)
    _aceptada_sin_consentimiento(sem)
    _solicitada(sem)


def _realizada_y_pagada(sem: Sembrador) -> None:
    c, p, m = sem.clinica, sem.prof, sem.mascota
    d = sem.derivar_cirugia(-45, c["centro"], m["Thor"], p["perez"], "Fractura de fémur derecho",
                            "Osteosíntesis de fémur", Prioridad.URGENTE, "Fractura diafisaria de fémur",
                            RiesgoAnestesico.ASA_II, "Rx y hemograma prequirúrgico normales",
                            tipo=TipoAtencion.URGENCIA)
    sem.mas_tarde(hours=2)
    sem.cir.aceptar(d.id, p["ferreyra"].id)
    sem.cir.registrar_consentimiento(d.id, "Recepción Sur")
    sem.cir.programar(d.id, reloj.ahora() + timedelta(days=1))
    sem.en(-44, 14)
    sem.cir.registrar_cirugia(d.id, "Se coloca placa y tornillos. Sin complicaciones. Alta a las 24 h.")
    factura = sem.fac.facturar_cirugia(d.id, 185000)
    sem.mas_tarde(days=2)
    sem.fac.registrar_pago(factura.id, FormaPago.TARJETA)


def _realizada_pendiente_de_cobro(sem: Sembrador) -> None:
    """ASA III: necesita los estudios prequirúrgicos antes de programar."""
    c, p, m = sem.clinica, sem.prof, sem.mascota
    d = sem.derivar_cirugia(-30, c["norte"], m["Simba"], p["sosa"], "Obstrucción uretral recurrente",
                            "Uretrostomía perineal", Prioridad.NORMAL, "Obstrucción uretral",
                            RiesgoAnestesico.ASA_III)
    sem.mas_tarde(hours=3)
    sem.cir.aceptar(d.id, p["rios"].id)
    sem.cir.registrar_consentimiento(d.id, "Recepción Norte")
    sem.cir.registrar_estudios(d.id, "Ecografía abdominal, ionograma y perfil renal")
    sem.cir.programar(d.id, reloj.ahora() + timedelta(days=2))
    sem.en(-28, 10)
    sem.cir.registrar_cirugia(d.id, "Uretrostomía sin complicaciones. Sonda 48 h.")
    sem.fac.facturar_cirugia(d.id, 210000)


def _rechazada(sem: Sembrador) -> None:
    c, p, m = sem.clinica, sem.prof, sem.mascota
    d = sem.derivar_cirugia(-20, c["centro"], m["Luna"], p["diaz"], "Tumor mamario", "Mastectomía radical",
                            Prioridad.NORMAL, "Neoplasia mamaria", RiesgoAnestesico.ASA_IV)
    sem.mas_tarde(hours=5)
    sem.cir.rechazar(d.id, "Paciente con riesgo ASA IV: primero estabilizar y reevaluar con cardiología")


def _cancelada(sem: Sembrador) -> None:
    c, p, m = sem.clinica, sem.prof, sem.mascota
    d = sem.derivar_cirugia(-14, c["norte"], m["Kira"], p["sosa"], "Luxación de rótula", "Trocleoplastia",
                            Prioridad.NORMAL, "Luxación patelar grado III", RiesgoAnestesico.ASA_I)
    sem.mas_tarde(hours=2)
    sem.cir.aceptar(d.id, p["ferreyra"].id)
    sem.cir.cancelar(d.id, "El titular decidió posponer la cirugía")


def _programada(sem: Sembrador) -> None:
    """Programada para dentro de 3 días."""
    c, p, m = sem.clinica, sem.prof, sem.mascota
    d = sem.derivar_cirugia(-8, c["norte"], m["Coco"], p["sosa"], "Cuerpo extraño gástrico", "Gastrotomía",
                            Prioridad.URGENTE, "Cuerpo extraño", RiesgoAnestesico.ASA_II)
    sem.mas_tarde(hours=1)
    sem.cir.aceptar(d.id, p["rios"].id)
    sem.cir.registrar_consentimiento(d.id, "Recepción Norte")
    sem.cir.programar(d.id, datetime.combine(sem.hoy + timedelta(days=3), time(9, 0)))


def _aceptada_sin_consentimiento(sem: Sembrador) -> None:
    """Para la demo de la validación: no se puede programar sin consentimiento."""
    c, p, m = sem.clinica, sem.prof, sem.mascota
    d = sem.derivar_cirugia(-4, c["centro"], m["Bruno"], p["acosta"], "Masa esplénica", "Esplenectomía",
                            Prioridad.URGENTE, "Masa esplénica", RiesgoAnestesico.ASA_III)
    sem.mas_tarde(hours=2)
    sem.cir.aceptar(d.id, p["rios"].id)


def _solicitada(sem: Sembrador) -> None:
    """Pendiente de respuesta del hospital."""
    c, p, m = sem.clinica, sem.prof, sem.mascota
    sem.derivar_cirugia(-2, c["centro"], m["Max"], p["perez"], "Rotura de ligamento cruzado",
                        "Cirugía de ligamento cruzado (TPLO)", Prioridad.NORMAL, "Rotura de LCA",
                        RiesgoAnestesico.ASA_II)

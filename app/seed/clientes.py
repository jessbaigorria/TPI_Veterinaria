"""Etapa 2 del seed: titulares, mascotas, vacunas aplicadas e historias clínicas."""
from __future__ import annotations

from datetime import timedelta

from app.seed.datos import CON_VACUNAS_PENDIENTES, HISTORIAS, MASCOTAS, TITULARES, VACUNAS_ESPECIALES
from app.seed.sembrador import Sembrador


def sembrar_clientes(sem: Sembrador) -> None:
    sem.en(-70, 9)
    sem.titular = {datos[2]: sem.cli.crear_titular(*datos) for datos in TITULARES}  # por apellido
    for apellido, nombre, especie, sexo, anios, raza, peso, alergias in MASCOTAS:
        nacimiento = sem.hoy - timedelta(days=int(anios * 365))
        sem.mascota[nombre] = sem.mas.crear_mascota(sem.titular[apellido].id, nombre, especie, sexo, nacimiento,
                                                    raza, peso, alergias=alergias)
    _vacunas_al_dia(sem)
    for nombre, vacuna, hace_dias, lote, dosis in VACUNAS_ESPECIALES:
        sem.mas.registrar_vacuna_aplicada(sem.mascota[nombre].id, sem.vacuna[vacuna].id,
                                          sem.hoy - timedelta(days=hace_dias), lote, dosis)
    for nombre, (alergias, antecedentes, observaciones) in HISTORIAS.items():
        sem.mas.actualizar_historia(sem.mascota[nombre].id, alergias, antecedentes, observaciones)


def _vacunas_al_dia(sem: Sembrador) -> None:
    """La mayoría de las mascotas tiene el esquema al día (aplicado hace 80–260 días)."""
    for nombre, mascota in sem.mascota.items():
        if nombre in CON_VACUNAS_PENDIENTES:
            continue
        for vacuna in sem.esquema_de(mascota):
            dias = sem.rnd.randint(80, 260)
            sem.mas.registrar_vacuna_aplicada(mascota.id, vacuna.id, sem.hoy - timedelta(days=dias),
                                              f"L{sem.rnd.randint(1000, 9999)}", 2)

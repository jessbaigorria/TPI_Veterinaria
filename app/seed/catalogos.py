"""Etapa 1 del seed: clínicas, laboratorio, profesionales, vacunas, tipos de análisis y contenedores."""
from __future__ import annotations

from app.seed.datos import (
    ANALISIS, CLINICAS, CONTENEDOR_EN_MANTENIMIENTO, CONTENEDORES, LABORATORIO, PROFESIONALES,
    PROFESIONALES_DE_RUTINA, VACUNAS,
)
from app.seed.sembrador import Sembrador


def sembrar_catalogos(sem: Sembrador) -> None:
    sem.en(-75, 8)
    c = sem.cat
    sem.clinica = {clave: c.guardar("clinicas", dict(datos)) for clave, datos in CLINICAS.items()}
    sem.lab = c.guardar("laboratorios", dict(LABORATORIO))

    for clave, legajo, nombre, apellido, clinica, especialidad in PROFESIONALES:
        sem.prof[clave] = c.guardar("profesionales", {
            "legajo": legajo, "matricula": f"MP-{legajo}", "dni": f"2{legajo}0{legajo}",
            "nombre": nombre, "apellido": apellido, "especialidad": especialidad,
            "telefono": f"351-55{legajo}", "email": f"{apellido.lower()}@vetred.com.ar",
            "clinica_id": sem.clinica[clinica].id})
    sem.de_rutina = {sem.clinica[clinica].id: [sem.prof[p] for p in profesionales]
                     for clinica, profesionales in PROFESIONALES_DE_RUTINA.items()}

    for clave, nombre, especie, obligatoria, semanas in VACUNAS:
        sem.vacuna[clave] = c.guardar("vacunas", {
            "nombre": nombre, "especie": especie, "obligatoria": "1" if obligatoria else "",
            "edad_minima_semanas": semanas, "intervalo_refuerzo_dias": 365})

    for codigo, nombre, precio, tipo, tmin, tmax, horas, descripcion in ANALISIS:
        sem.analisis[codigo] = c.guardar("analisis", {
            "codigo": codigo, "nombre": nombre, "descripcion": descripcion, "precio": precio,
            "tipo_muestra_requerida": tipo, "temperatura_min": tmin, "temperatura_max": tmax,
            "tiempo_estimado_horas": horas})

    for codigo, clinica, capacidad, tmin, tmax in CONTENEDORES:
        sem.contenedor[codigo] = c.guardar("contenedores", {
            "codigo": codigo, "capacidad": capacidad, "temperatura_min": tmin, "temperatura_max": tmax,
            "clinica_id": sem.clinica[clinica].id})
    c.cambiar_estado_contenedor(sem.contenedor[CONTENEDOR_EN_MANTENIMIENTO].id, "mantenimiento")

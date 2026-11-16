"""Etapa 4 del seed: derivaciones al laboratorio con remitos y muestras en todos los estados.

El orden importa: los remitos se numeran al crearse (REM-000003 es el del precinto roto y
REM-000004 el de la temperatura fuera de rango, como cuenta el README).
"""
from __future__ import annotations

from app.domain.enums import Prioridad, TipoAtencion
from app.seed.datos import OPERADORES_LAB, TRANSPORTISTAS
from app.seed.sembrador import Sembrador


def sembrar_laboratorio(sem: Sembrador) -> None:
    c, k, p, m = sem.clinica, sem.contenedor, sem.prof, sem.mascota
    sem.ciclo_completo(-55, c["centro"], k["CEN-01"], m["Firulais"], {"SANGRE": ["HEM", "REN"]}, p["perez"],
                       transito_h=2.5)
    sem.ciclo_completo(-48, c["norte"], k["NOR-01"], m["Michi"], {"ORINA": ["URI"], "SANGRE": ["HEM"]},
                       p["medina"], transito_h=4.0)
    _remito_con_precinto_roto(sem)
    # Remito con TEMPERATURA FUERA DE RANGO.
    sem.ciclo_completo(-33, c["norte"], k["NOR-01"], m["Simba"], {"SANGRE": ["HEM"]}, p["sosa"],
                       transito_h=6.5, temp=12.5)
    sem.ciclo_completo(-25, c["sur"], k["SUR-02"], m["Bruno"], {"TEJIDO": ["HIS"]}, p["ferreyra"],
                       transito_h=2.0, temp=19.0, proceso_h=(40, 60), temp_despacho=20.0)
    sem.ciclo_completo(-18, c["centro"], k["CEN-03"], m["Nina"], {"SANGRE": ["HEM", "REN"], "ORINA": ["URI"]},
                       p["acosta"], transito_h=3.0)
    sem.ciclo_completo(-10, c["norte"], k["NOR-01"], m["Coco"], {"SANGRE": ["HEP"]}, p["sosa"], transito_h=5.0)
    # Recibidos pendientes de análisis (cola del laboratorio).
    sem.ciclo_completo(-5, c["centro"], k["CEN-01"], m["Max"], {"SANGRE": ["HEM", "REN"]}, p["perez"],
                       transito_h=3.5, analizar=False, prioridad=Prioridad.URGENTE,
                       tipo_atencion=TipoAtencion.URGENCIA)
    sem.ciclo_completo(-3, c["norte"], k["NOR-01"], m["Kira"], {"HISOPADO": ["CIT"]}, p["medina"],
                       transito_h=4.5, analizar=False)
    _remito_en_transito(sem)
    _remito_despachado_esperando_retiro(sem)
    _remito_armado(sem)
    _muestra_extraida_de_hoy(sem)


def _remito_con_precinto_roto(sem: Sembrador) -> None:
    """Dos órdenes (Luna y Thor) en el mismo remito: el precinto llega roto → todas las muestras rechazadas."""
    c, k, p, m = sem.clinica, sem.contenedor, sem.prof, sem.mascota
    heces = sem.orden_con_muestra(-40, 15, c["centro"], m["Luna"], p["diaz"], ["COP"], "HECES",
                                  "Diarrea crónica; se pide coproparasitológico")
    sangre = sem.orden_con_muestra(-40, 16, c["centro"], m["Thor"], p["perez"], ["HEP"], "SANGRE",
                                   "Control prequirúrgico")
    sem.mas_tarde(hours=1)
    remito = sem.remito(c["centro"], k["CEN-02"], [heces, sangre], "Recepción Centro")
    sem.despachar(remito, "Recepción Centro", transportista=TRANSPORTISTAS[1])
    sem.mas_tarde(minutes=30)
    sem.env.confirmar_retiro(remito.id)
    sem.mas_tarde(hours=3, minutes=10)
    sem.recibir(remito, integro=False, temp=6.0, operador=OPERADORES_LAB[1])


def _remito_en_transito(sem: Sembrador) -> None:
    """En tránsito hacia el laboratorio (para recibirlo en la demo)."""
    c, k, p, m = sem.clinica, sem.contenedor, sem.prof, sem.mascota
    orina = sem.orden_con_muestra(-2, 15, c["centro"], m["Lola"], p["acosta"], ["URI"], "ORINA",
                                  "Sospecha de infección urinaria")
    sem.mas_tarde(hours=1)
    remito = sem.remito(c["centro"], k["CEN-01"], [orina], "Recepción Centro")
    sem.despachar(remito, "Recepción Centro", horas_estimadas=30)
    sem.mas_tarde(minutes=45)
    sem.env.confirmar_retiro(remito.id)


def _remito_despachado_esperando_retiro(sem: Sembrador) -> None:
    c, k, p, m = sem.clinica, sem.contenedor, sem.prof, sem.mascota
    sangre = sem.orden_con_muestra(-1, 15, c["norte"], m["Tom"], p["medina"], ["HEM", "REN"], "SANGRE",
                                   "Gato geronte: chequeo renal")
    sem.mas_tarde(hours=1)
    remito = sem.remito(c["norte"], k["NOR-01"], [sangre], "Recepción Norte")
    sem.despachar(remito, "Recepción Norte", horas_estimadas=26)


def _remito_armado(sem: Sembrador) -> None:
    """Remito armado con una muestra empaquetada, todavía sin cerrar con precinto."""
    c, k, p, m = sem.clinica, sem.contenedor, sem.prof, sem.mascota
    sangre = sem.orden_con_muestra(-1, 16, c["sur"], m["Rocky"], p["luna"], ["REN"], "SANGRE",
                                   "Evaluación prequirúrgica", obs="Prequirúrgico: evaluar función renal")
    remito = sem.emp.crear_remito(c["sur"].id, sem.lab.id, k["SUR-01"].id, "Recepción Sur")
    sem.emp.agregar_muestras(remito.id, [sangre.id], "Recepción Sur")


def _muestra_extraida_de_hoy(sem: Sembrador) -> None:
    """Orden de hoy con la muestra Extraída, sin empaquetar."""
    c, p, m = sem.clinica, sem.prof, sem.mascota
    sem.orden_con_muestra(0, 8, c["centro"], m["Pompón"], p["diaz"], ["HEM", "HEP"], "SANGRE",
                          "Dermatitis; se pide laboratorio", obs="Prurito generalizado; descartar hepatopatía")

"""Reportes R1–R5 (consultas agregadas)."""
from app.reportes import r1_atenciones, r2_rechazos, r3_tiempos, r4_facturacion, r5_vacunas
from app.reportes.comun import Filtro, Reporte, a_csv  # noqa: F401

REPORTES = {
    "r1": r1_atenciones.generar,
    "r2": r2_rechazos.generar,
    "r3": r3_tiempos.generar,
    "r4": r4_facturacion.generar,
    "r5": r5_vacunas.generar,
}

TITULOS = {
    "r1": "Atenciones y derivaciones",
    "r2": "Muestras rechazadas por transporte",
    "r3": "Tiempos de tránsito y procesamiento",
    "r4": "Facturación por clínica y laboratorio",
    "r5": "Vacunas pendientes por mascota",
}


def generar(codigo: str, sesion, filtro: Filtro) -> Reporte:
    return REPORTES[codigo](sesion, filtro)

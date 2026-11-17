"""Reportes (consultas agregadas). Se identifican por nombre en la interfaz y en las rutas."""
from app.reportes import r1_atenciones, r2_rechazos, r3_tiempos, r4_facturacion, r5_vacunas
from app.reportes.comun import Filtro, Reporte  # noqa: F401

REPORTES = {
    "atenciones": r1_atenciones.generar,
    "rechazos": r2_rechazos.generar,
    "tiempos": r3_tiempos.generar,
    "facturacion": r4_facturacion.generar,
    "vacunas": r5_vacunas.generar,
}

TITULOS = {
    "atenciones": "Atenciones y derivaciones",
    "rechazos": "Muestras rechazadas",
    "tiempos": "Tiempos de tránsito",
    "facturacion": "Facturación por clínica y laboratorio",
    "vacunas": "Vacunas pendientes",
}


def generar(codigo: str, sesion, filtro: Filtro) -> Reporte:
    return REPORTES[codigo](sesion, filtro)

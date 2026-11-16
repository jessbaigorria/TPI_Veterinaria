"""Portal Clínica: atención de pacientes, órdenes, empaquetado y despacho, cirugías, facturación,
reportes y gestión. Un módulo por sección del menú.

Las rutas solo traducen formularios y llaman a los servicios; los estados los cambia el dominio.
El orden de las secciones importa: FastAPI resuelve las rutas en el orden en que se registran.
"""
from fastapi import APIRouter

from app.web.routers.portal_clinica import (
    agenda, atenciones, cirugias, clientes, envios, facturacion, gestion, inicio, mascotas, ordenes, reportes,
)

SECCIONES = (inicio, agenda, atenciones, clientes, mascotas, ordenes, envios, cirugias, facturacion, reportes,
             gestion)

router = APIRouter()
for seccion in SECCIONES:
    router.include_router(seccion.router)

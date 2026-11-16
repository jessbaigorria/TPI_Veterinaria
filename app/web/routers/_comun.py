"""Helpers compartidos por las rutas de los dos portales."""
from __future__ import annotations

from fastapi import Depends, Request
from fastapi.responses import RedirectResponse

from app.db import obtener_sesion
from app.web.sesion import usuario_clinica, usuario_laboratorio

# Dependencias de FastAPI: sesión de base de datos y usuario de cada portal.
Db = Depends(obtener_sesion)
UsrClinica = Depends(usuario_clinica)
UsrLaboratorio = Depends(usuario_laboratorio)


def ir(url: str) -> RedirectResponse:
    """POST → redirect → GET (303), para que recargar la página no repita la acción."""
    return RedirectResponse(url, status_code=303)


async def formulario(request: Request) -> dict:
    return dict(await request.form())


def destino_interno(destino: str | None, defecto: str, prefijo: str) -> str:
    """Vuelve a la pantalla indicada solo si es una ruta interna del portal (si no, al defecto)."""
    return destino if destino and destino.startswith(prefijo) else defecto

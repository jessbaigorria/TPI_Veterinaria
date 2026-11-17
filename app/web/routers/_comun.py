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


def datos_mascota_nueva(f: dict) -> dict | None:
    """Sección «Nueva mascota» de los formularios de atención y turno (campos «nm_…»), o None si no
    se completó el nombre."""
    if not (f.get("nm_nombre") or "").strip():
        return None
    return {"titular_id": f.get("titular_id"), "nombre": f.get("nm_nombre"), "especie": f.get("nm_especie"),
            "sexo": f.get("nm_sexo"), "fecha_nacimiento": f.get("nm_fecha_nacimiento"),
            "raza": f.get("nm_raza", ""), "peso": f.get("nm_peso")}


def destino_interno(destino: str | None, defecto: str, prefijo: str) -> str:
    """Vuelve a la pantalla indicada solo si es una ruta interna del portal (si no, al defecto)."""
    return destino if destino and destino.startswith(prefijo) else defecto

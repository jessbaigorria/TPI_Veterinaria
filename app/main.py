"""Aplicación FastAPI: dos portales (Clínica y Laboratorio) sobre los mismos datos.

Manejo global de ``VeterinariaError``: en un único lugar se captura la excepción de negocio
y se muestra el mensaje en un aviso rojo sin romper la pantalla."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app import db
from app.domain.excepciones import VacunasPendientesError, VeterinariaError
from app.web.plantillas import render
from app.web.routers import comunes, portal_clinica, portal_laboratorio
from app.web.sesion import avisar, guardar_formulario

ESTATICOS = Path(__file__).resolve().parent / "web" / "static"


def crear_app(url_db: str | None = None, motor=None) -> FastAPI:
    db.configurar(url_db, motor)
    app = FastAPI(title="VetRed – Red de Clínicas y Laboratorio", docs_url=None, redoc_url=None)
    app.add_middleware(SessionMiddleware, secret_key=os.environ.get("VETERINARIA_SECRET", "tp-dao-grupo-30"),
                       session_cookie="vetred_sesion", max_age=60 * 60 * 12)
    app.mount("/static", StaticFiles(directory=str(ESTATICOS)), name="static")

    @app.middleware("http")
    async def sin_cache(request: Request, call_next):
        # Las pantallas siempre se piden de nuevo (al volver atrás no se ven listados viejos).
        respuesta = await call_next(request)
        if respuesta.headers.get("content-type", "").startswith("text/html"):
            respuesta.headers["Cache-Control"] = "no-store"
        return respuesta
    app.include_router(comunes.router)
    app.include_router(portal_clinica.router)
    app.include_router(portal_laboratorio.router)

    @app.exception_handler(VeterinariaError)
    async def manejar_error_negocio(request: Request, exc: VeterinariaError):
        extra = {}
        if isinstance(exc, VacunasPendientesError) and exc.mascota_id is not None:
            extra = {"vacunas": exc.nombres_vacunas, "mascota_id": exc.mascota_id, "mascota": exc.mascota_nombre}
        avisar(request, str(exc), "danger", **extra)
        if request.method == "POST":
            try:
                guardar_formulario(request, dict(await request.form()))
            except Exception:  # pragma: no cover
                pass
            destino = request.headers.get("referer") or "/"
            return RedirectResponse(destino, status_code=303)
        referer = request.headers.get("referer")
        if referer and referer != str(request.url):
            return RedirectResponse(referer, status_code=303)
        return render(request, "error.html", status_code=400, titulo="No se pudo completar la operación")

    return app


app = crear_app()

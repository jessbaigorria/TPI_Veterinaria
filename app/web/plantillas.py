"""Configuración de Jinja2 (filtros, globales) y helper para renderizar con el contexto común."""
from __future__ import annotations

from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.domain import enums, reloj
from app.web import formato
from app.web.sesion import tomar_formulario, tomar_mensajes, usuario_actual

DIRECTORIO = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(DIRECTORIO))
env = templates.env
env.filters.update(
    fecha=formato.fecha, fecha_hora=formato.fecha_hora, hora=formato.hora, moneda=formato.moneda,
    numero=formato.numero, celda=formato.valor_celda, color_muestra=formato.color_muestra,
    color_remito=formato.color_remito, color_enum=formato.color_enum, color_nombre=formato.color_nombre_estado,
    etiqueta=formato.etiqueta,
)
env.globals.update(enums=enums, reloj=reloj, NOMBRES_REMITO=formato.NOMBRES_REMITO,
                   NOMBRES_MUESTRA=formato.NOMBRES_MUESTRA)


def render(request: Request, plantilla: str, status_code: int = 200, **contexto):
    previo = tomar_formulario(request)
    contexto.setdefault("seccion", "")
    return templates.TemplateResponse(
        request, plantilla,
        {"u": usuario_actual(request), "mensajes": tomar_mensajes(request), "previo": previo,
         "query": dict(request.query_params), **contexto},
        status_code=status_code,
    )

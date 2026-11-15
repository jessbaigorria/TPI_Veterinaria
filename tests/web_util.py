"""Utilidades compartidas por los tests web (app con el seed cargado)."""
from __future__ import annotations

import re
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select

from app import db
from app.domain import reloj
from app.domain.atencion import Clinica
from app.domain.laboratorio import Laboratorio
from app.seed import sembrar


def crear_entorno(hoy: date | None = None):
    reloj.liberar()
    eng = db.crear_engine("sqlite://")
    db.init_db(eng)
    s = db.crear_fabrica_sesiones(eng)()
    sembrar(s, hoy or date.today())
    from app.main import crear_app
    return TestClient(crear_app(motor=eng)), s


def uno(s, modelo, **filtros):
    s.expire_all()
    return s.scalars(select(modelo).filter_by(**filtros)).one()


def post(c, url, data=None, desde="/clinica"):
    return c.post(url, data=data or {}, headers={"referer": f"http://testserver{desde}"})


def login_clinica(c, s, nombre="Clínica Centro"):
    c.post("/ingresar", data={"portal": "clinica", "clinica_id": uno(s, Clinica, nombre=nombre).id})


def login_lab(c, s):
    c.post("/ingresar", data={"portal": "laboratorio", "laboratorio_id": s.scalars(select(Laboratorio)).first().id})


def texto_visible(html: str) -> str:
    """Texto que ve el usuario (sin scripts, estilos ni etiquetas)."""
    html = re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>", " ", html)
    return re.sub(r"<[^>]+>", " ", html)


def aviso_rojo(html: str) -> str:
    m = re.search(r'(?s)<div class="alert alert-danger[^"]*"[^>]*>(.*?)<button', html)
    return " ".join(re.sub(r"<[^>]+>", " ", m.group(1)).split()) if m else ""

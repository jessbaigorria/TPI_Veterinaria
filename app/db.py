"""Engine, sesión e inicialización de la base (incluye triggers de inmutabilidad del historial)."""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.domain  # noqa: F401  (registra los mapeos)
import app.repositories  # noqa: F401  (tabla secuencia + listeners del historial)
import app.services.fabrica_observadores  # noqa: F401  (adjunta observadores a las muestras)
from app.domain.base import Base

RAIZ = Path(__file__).resolve().parent.parent
URL_POR_DEFECTO = f"sqlite:///{RAIZ / 'veterinaria.db'}"

TRIGGERS_HISTORIAL = (
    """
    CREATE TRIGGER IF NOT EXISTS historial_no_update
    BEFORE UPDATE ON historial_estado_muestra
    BEGIN
        SELECT RAISE(ABORT, 'El historial de estados de la muestra es inmutable (UPDATE prohibido)');
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS historial_no_delete
    BEFORE DELETE ON historial_estado_muestra
    BEGIN
        SELECT RAISE(ABORT, 'El historial de estados de la muestra es inmutable (DELETE prohibido)');
    END;
    """,
)


def _activar_foreign_keys(dbapi_conn, _record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def crear_engine(url: str | None = None) -> Engine:
    url = url or os.environ.get("VETERINARIA_DB_URL", URL_POR_DEFECTO)
    kwargs: dict = {"connect_args": {"check_same_thread": False}}
    if url in ("sqlite://", "sqlite:///:memory:"):
        kwargs["poolclass"] = StaticPool
    engine = create_engine(url, **kwargs)
    event.listen(engine, "connect", _activar_foreign_keys)
    return engine


def init_db(engine: Engine) -> None:
    """Crea las tablas y los triggers que hacen inmutable el historial (capa 3)."""
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        for ddl in TRIGGERS_HISTORIAL:
            conn.execute(text(ddl))


def reset_db(engine: Engine) -> None:
    Base.metadata.drop_all(engine)
    init_db(engine)


def crear_fabrica_sesiones(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, autoflush=True)


# --- configuración global usada por la aplicación web -------------------------------
engine: Engine | None = None
SessionLocal: sessionmaker[Session] | None = None


def configurar(url: str | None = None, motor: Engine | None = None) -> Engine:
    global engine, SessionLocal
    engine = motor or crear_engine(url)
    init_db(engine)
    SessionLocal = crear_fabrica_sesiones(engine)
    return engine


def obtener_sesion():
    """Dependencia de FastAPI: una sesión por request."""
    if SessionLocal is None:
        configurar()
    sesion = SessionLocal()
    try:
        yield sesion
    finally:
        sesion.close()

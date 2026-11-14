import pytest

from app import db as db_mod
from app.domain import reloj
from tests.fabricas import AHORA, Mundo


@pytest.fixture(autouse=True)
def reloj_fijo():
    reloj.fijar(AHORA)
    yield
    reloj.liberar()


@pytest.fixture
def engine():
    eng = db_mod.crear_engine("sqlite://")
    db_mod.init_db(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def sesion(engine):
    s = db_mod.crear_fabrica_sesiones(engine)()
    yield s
    s.close()


@pytest.fixture
def mundo():
    """Objetos de dominio sin base de datos (dominio puro)."""
    return Mundo()


@pytest.fixture
def mundo_db(sesion):
    """Mismo grafo pero persistido en una SQLite en memoria."""
    return Mundo(sesion)

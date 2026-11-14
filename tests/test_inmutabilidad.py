"""Trazabilidad inmutable – capas 2 (repositorio + listeners ORM) y 3 (triggers SQLite)."""
import pytest
from sqlalchemy import delete, text, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import attributes

from app.domain.laboratorio import HistorialEstadoMuestraFila
from app.repositories.historial import HistorialInmutableError, HistorialRepository


def test_repositorio_solo_agrega_y_lista(sesion, base):
    repo = HistorialRepository(sesion)
    assert not hasattr(repo, "actualizar")
    assert not hasattr(repo, "eliminar")
    m = base.muestra()
    h = repo.listar_por_muestra(m.id)
    assert isinstance(h, tuple) and len(h) == 1 and h[0].estado_nuevo == "Extraída"


def test_update_por_orm_bloqueado_por_listener(sesion, base):
    m = base.muestra()
    fila = m.filas_historial[0]
    attributes.set_attribute(fila, "motivo", "adulterado")  # saltea el bloqueo del dominio
    with pytest.raises(HistorialInmutableError):
        sesion.flush()
    sesion.rollback()


def test_delete_por_orm_bloqueado_por_listener(sesion, base):
    m = base.muestra()
    sesion.delete(m.filas_historial[0])
    with pytest.raises(HistorialInmutableError):
        sesion.flush()
    sesion.rollback()


def test_update_por_sql_directo_falla(sesion, base):
    base.muestra()
    with pytest.raises((OperationalError, IntegrityError), match="inmutable"):
        sesion.execute(text("UPDATE historial_estado_muestra SET motivo='x'"))
    sesion.rollback()
    with pytest.raises((OperationalError, IntegrityError), match="inmutable"):
        sesion.execute(update(HistorialEstadoMuestraFila).values(usuario="hacker"))
    sesion.rollback()


def test_delete_por_sql_directo_falla(sesion, base):
    base.muestra()
    with pytest.raises((OperationalError, IntegrityError), match="inmutable"):
        sesion.execute(text("DELETE FROM historial_estado_muestra"))
    sesion.rollback()
    with pytest.raises((OperationalError, IntegrityError), match="inmutable"):
        sesion.execute(delete(HistorialEstadoMuestraFila))
    sesion.rollback()
    assert sesion.execute(text("select count(*) from historial_estado_muestra")).scalar() == 1


def test_historial_y_estado_en_la_misma_transaccion(engine, base):
    m = base.muestra()
    base.remito_en_transito([m])
    with engine.connect() as c:
        filas = c.exec_driver_sql("select estado_nuevo from historial_estado_muestra where muestra_id=? order by id",
                                  (m.id,)).scalars().all()
    assert filas == ["Extraída", "Empaquetada", "En tránsito"]

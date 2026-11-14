"""Trazabilidad inmutable – capa 1 (dominio)."""
import dataclasses

import pytest

from app.domain.excepciones import VeterinariaError


def test_historial_devuelve_tupla_de_objetos_congelados(mundo):
    m = mundo.muestra()
    h = m.historial()
    assert isinstance(h, tuple)
    with pytest.raises(dataclasses.FrozenInstanceError):
        h[0].estado_nuevo = "Analizada"
    with pytest.raises(AttributeError):
        h.append  # noqa: B018 - las tuplas no se pueden extender


def test_fila_de_historial_no_admite_cambios(mundo):
    m = mundo.muestra()
    fila = m.filas_historial[0]
    for campo in ("estado_nuevo", "estado_anterior", "motivo", "usuario", "fecha_hora"):
        with pytest.raises(VeterinariaError):
            setattr(fila, campo, "x")
    with pytest.raises(VeterinariaError):
        del fila.motivo

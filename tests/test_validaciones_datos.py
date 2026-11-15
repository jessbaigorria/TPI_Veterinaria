"""Validaciones de formato de datos (app/domain/validaciones.py)."""
import pytest

from app.domain import validaciones as v
from app.domain.excepciones import DatosInvalidosError, VeterinariaError


def test_datos_invalidos_hereda_de_veterinaria_error():
    assert issubclass(DatosInvalidosError, VeterinariaError)


@pytest.mark.parametrize("valor", ["Ana", "María José Núñez", "  Lucía   Ibarra "])
def test_nombre_persona_valido(valor):
    assert v.nombre_persona(valor, "Analista") == " ".join(valor.split())


@pytest.mark.parametrize("valor,mensaje", [("", "obligatorio"), ("5", "solo admite letras"), ("Ana2", "solo admite letras"),
                                           ("lab.gomez", "solo admite letras"), ("Al", "al menos 3")])
def test_nombre_persona_invalido(valor, mensaje):
    with pytest.raises(DatosInvalidosError, match=mensaje):
        v.nombre_persona(valor, "Analista")

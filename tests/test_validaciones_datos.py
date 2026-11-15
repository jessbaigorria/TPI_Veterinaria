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


# --- Bloque F: titular -----------------------------------------------------------------------
@pytest.mark.parametrize("valor,esperado", [("28456123", "28456123"), ("28 456 123", "28456123"),
                                            ("28.456.123", "28456123"), ("8 456 123", "8456123")])
def test_dni_valido_guarda_solo_digitos(valor, esperado):
    assert v.dni(valor) == esperado


@pytest.mark.parametrize("valor,mensaje", [("", "obligatorio"), ("abc12345", "solo admite números"),
                                           ("123456", "7 u 8 dígitos"), ("123456789", "7 u 8 dígitos")])
def test_dni_invalido(valor, mensaje):
    with pytest.raises(DatosInvalidosError, match=mensaje):
        v.dni(valor)


@pytest.mark.parametrize("valor,mensaje", [("", "obligatorio"), ("351-422", "solo admite números"),
                                           ("35142a1100", "solo admite números"), ("1234567", "entre 8 y 15"),
                                           ("1234567890123456", "entre 8 y 15")])
def test_telefono_invalido(valor, mensaje):
    with pytest.raises(DatosInvalidosError, match=mensaje):
        v.telefono(valor)


def test_telefono_y_email_validos():
    assert v.telefono("3514221100") == "3514221100"
    assert v.email("Juan@Mail.com") == "juan@mail.com"
    for malo in ("juan", "juan@", "juan@mail", "@mail.com"):
        with pytest.raises(DatosInvalidosError, match="formato válido"):
            v.email(malo)


def test_titular_exige_todos_los_campos():
    from app.domain.personas import Titular
    base = dict(dni="30111222", nombre="Juan", apellido="García", direccion="Colón 100", telefono="3511000000",
                email="juan@mail.com")
    assert Titular(**base).dni == "30111222"
    for campo in base:
        with pytest.raises(DatosInvalidosError):
            Titular(**{**base, campo: ""})
    with pytest.raises(DatosInvalidosError, match="solo admite letras"):
        Titular(**{**base, "nombre": "Juan2"})


def test_servicio_dni_no_se_repite(sesion, base):
    from app.services.clientes import ClientesService
    with pytest.raises(DatosInvalidosError, match="Ya existe un titular con DNI 30111222"):
        ClientesService(sesion).crear_titular("30 111 222", "Otro", "Titular", "Calle 1", "3512000000", "otro@mail.com")
    t = ClientesService(sesion).crear_titular("7654321", "Ana", "Paz", "Calle 2", "3513000000", "ana@mail.com")
    with pytest.raises(DatosInvalidosError, match="Ya existe"):
        ClientesService(sesion).actualizar_titular(t.id, dni="30111222")
    ClientesService(sesion).actualizar_titular(t.id, telefono="3519999999")
    assert t.telefono == "3519999999" and t.dni == "7654321"

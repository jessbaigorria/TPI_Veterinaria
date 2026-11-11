import pytest

from titular import Titular
from excepciones import DatosInvalidosError


def crear_titular(**cambios):
    datos = dict(
        dni="30111222",
        nombre="Juan",
        apellido="Pérez",
        direccion="Belgrano 123",
        telefono="388 412-3456",
        email="juan@mail.com",
    )
    datos.update(cambios)
    return Titular(**datos)


# ---------- creación correcta ----------
def test_crear_titular_valido():
    t = crear_titular()
    assert t.dni == "30111222"
    assert t.nombre == "Juan"
    assert t.apellido == "Pérez"
    assert t.direccion == "Belgrano 123"
    assert t.telefono == "3884123456"        # el teléfono se guarda limpio
    assert t.email == "juan@mail.com"
    assert t.activo is True


# ---------- tipos de datos ----------
@pytest.mark.parametrize("campo", ["nombre", "apellido", "direccion"])
@pytest.mark.parametrize("valor_invalido", [123, None, 4.5, ["Juan"], ""])
def test_campos_de_texto_rechazan_tipos_invalidos(campo, valor_invalido):
    with pytest.raises(DatosInvalidosError):
        crear_titular(**{campo: valor_invalido})


@pytest.mark.parametrize("valor_invalido", [3884123456, None, 4.5])
def test_telefono_debe_ser_string(valor_invalido):
    with pytest.raises(DatosInvalidosError):
        crear_titular(telefono=valor_invalido)


@pytest.mark.parametrize("valor_invalido", [123, None, ["a@b.com"]])
def test_email_debe_ser_string(valor_invalido):
    with pytest.raises(DatosInvalidosError):
        crear_titular(email=valor_invalido)


@pytest.mark.parametrize("valor_invalido", [30111222, None, 30111222.0])
def test_dni_debe_ser_string(valor_invalido):
    with pytest.raises(DatosInvalidosError):
        crear_titular(dni=valor_invalido)


# ---------- formato del DNI ----------
@pytest.mark.parametrize("dni_invalido", [
    "123456",        # le faltan números (6)
    "123456789",     # le sobran números (9)
    "12a45678",      # tiene una letra
    "1234-5678",     # separador no permitido
    "",              # vacío
    "   ",           # solo espacios
])
def test_dni_con_formato_invalido(dni_invalido):
    with pytest.raises(DatosInvalidosError):
        crear_titular(dni=dni_invalido)


@pytest.mark.parametrize("dni_valido", ["1234567", "12345678"])   # 7 y 8 dígitos
def test_dni_valido_de_7_u_8_digitos(dni_valido):
    assert crear_titular(dni=dni_valido).dni == dni_valido


@pytest.mark.parametrize("entrada", ["30.111.222", " 30111222 "])
def test_dni_se_normaliza(entrada):
    assert crear_titular(dni=entrada).dni == "30111222"


# ---------- extras (avisar) ----------
def test_dni_es_solo_lectura():
    t = crear_titular()
    with pytest.raises(AttributeError):
        t.dni = "99999999"


def test_email_invalido_lanza_error():
    with pytest.raises(DatosInvalidosError):
        crear_titular(email="juan@mail")
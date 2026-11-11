from datetime import date, timedelta

import pytest

from enumeraciones import Especie, Sexo
from excepciones import DatosInvalidosError, MascotaSinTitularError
from mascota import Mascota
from titular import Titular


@pytest.fixture
def titular():
    return Titular("30111222", "Juan", "Pérez", "Belgrano 123",
                   "388 412-3456", "juan@mail.com")


def crear_mascota(titular, **cambios):
    datos = dict(
        titular=titular,
        nombre="Rex",
        especie=Especie.PERRO,
        sexo=Sexo.MACHO,
        raza="Labrador",
        fecha_nacimiento=date(2022, 3, 1),
        peso=28.5,
    )
    datos.update(cambios)
    return Mascota(**datos)


# ---------- creación correcta ----------
def test_crear_mascota_valida(titular):
    m = crear_mascota(titular)
    assert m.nombre == "Rex"
    assert m.especie is Especie.PERRO
    assert m.peso == 28.5
    assert m.titular is titular
    assert m.activa is True


# ---------- sin titular ----------
@pytest.mark.parametrize("titular_invalido", [None, "Juan", 123])
def test_mascota_sin_titular_falla(titular_invalido):
    with pytest.raises(MascotaSinTitularError):
        crear_mascota(titular_invalido)


# ---------- tipos de datos básicos ----------
@pytest.mark.parametrize("nombre_invalido", [123, None, 4.5, ["Rex"], ""])
def test_nombre_debe_ser_string_no_vacio(titular, nombre_invalido):
    with pytest.raises(DatosInvalidosError):
        crear_mascota(titular, nombre=nombre_invalido)


@pytest.mark.parametrize("peso_invalido", ["28.5", None, [28.5]])
def test_peso_debe_ser_numerico(titular, peso_invalido):
    with pytest.raises(DatosInvalidosError):
        crear_mascota(titular, peso=peso_invalido)


# ---------- peso <= 0 ----------
@pytest.mark.parametrize("peso_invalido", [0.0, -1.5, -30.0])
def test_peso_menor_o_igual_a_cero_falla(titular, peso_invalido):
    with pytest.raises(DatosInvalidosError):
        crear_mascota(titular, peso=peso_invalido)


def test_setter_de_peso_tambien_valida(titular):
    m = crear_mascota(titular)
    with pytest.raises(DatosInvalidosError):
        m.peso = -2.0
    assert m.peso == 28.5          # el valor anterior no se modificó


# ---------- edad en semanas ----------
def test_edad_en_semanas_exacta(titular):
    m = crear_mascota(titular, fecha_nacimiento=date.today() - timedelta(weeks=10))
    assert m.edad_en_semanas() == 10


def test_edad_en_semanas_redondea_hacia_abajo(titular):
    m = crear_mascota(titular, fecha_nacimiento=date.today() - timedelta(days=76))
    assert m.edad_en_semanas() == 10      # 76 días = 10 semanas y 6 días


def test_edad_en_semanas_recien_nacida(titular):
    m = crear_mascota(titular, fecha_nacimiento=date.today())
    assert m.edad_en_semanas() == 0


# ---------- extras (avisar) ----------
def test_mascota_queda_registrada_en_su_titular(titular):
    m = crear_mascota(titular)
    assert m in titular._mascotas


def test_cambiar_titular_actualiza_ambos_lados(titular):
    otro = Titular("20999888", "Ana", "Gómez", "Mitre 45", "388 411-0000", "ana@mail.com")
    m = crear_mascota(titular)
    m.cambiar_titular(otro)
    assert m.titular is otro
    assert m in otro._mascotas
    assert m not in titular._mascotas


def test_dar_de_baja(titular):
    m = crear_mascota(titular)
    m.dar_de_baja()
    assert m.activa is False
"""Segunda ronda de correcciones del grupo ("Errores y cosas a mejorar"), verificada por HTTP con el seed."""
from datetime import timedelta

import pytest

from app.domain import reloj
from app.domain.clinica import Profesional
from app.domain.personas import Mascota, Titular
from tests.web_util import aviso_rojo, crear_entorno, login_clinica, post, texto_visible, uno


@pytest.fixture(scope="module")
def entorno():
    c, s = crear_entorno()
    yield c, s
    s.close()


@pytest.fixture(autouse=True)
def reloj_real():
    reloj.liberar()
    yield


def _manana():
    return (reloj.hoy() + timedelta(days=1)).isoformat()


# --- 2 y 3: «Nueva mascota» en atención sin turno y en reservar turno ------------------------------
def test_atencion_sin_turno_textos(entorno):
    c, s = entorno
    login_clinica(c, s)
    visible = texto_visible(c.get("/clinica/atenciones/nueva").text)
    assert "Nueva mascota" in visible and "cliente frecuente" not in visible
    assert "Motivo" in visible and "anamnesis" not in visible


def test_seccion_mascota_nueva_valida_letras_en_el_html(entorno):
    c, s = entorno
    login_clinica(c, s)
    for url in ("/clinica/atenciones/nueva", "/clinica/agenda/nuevo"):
        html = c.get(url).text
        for campo in ("nm_nombre", "nm_raza"):
            etiqueta = html.split(f'name="{campo}"', 1)[1].split(">", 1)[0]
            assert "pattern=" in etiqueta, (url, campo)
        assert "data-seccion-nueva" in html and "data-mascota-nueva" in html


def test_reservar_turno_ofrece_crear_titular_y_vuelve_con_el_titular(entorno):
    c, s = entorno
    login_clinica(c, s)
    html = c.get("/clinica/agenda/nuevo").text
    assert 'href="/clinica/clientes/nuevo?next=/clinica/agenda/nuevo"' in html
    r = c.post("/clinica/clientes", data={"dni": "40999111", "nombre": "Bruno", "apellido": "Quiroga",
                                          "direccion": "Belgrano 10", "telefono": "3514111111",
                                          "email": "bruno@mail.com", "next": "/clinica/agenda/nuevo"},
               follow_redirects=False)
    t = uno(s, Titular, dni="40999111")
    assert r.headers["location"] == f"/clinica/agenda/nuevo?titular={t.id}"
    assert f'<option value="{t.id}" selected>' in c.get(r.headers["location"]).text


def _turno(s, **extra):
    perez = uno(s, Profesional, apellido="Pérez")
    t = uno(s, Titular, dni="40999111") if "titular_id" not in extra else None
    datos = {"titular_id": t.id if t else "", "mascota_id": "", "profesional_id": perez.id, "tipo": "CONSULTA",
             "fecha": _manana(), "hora_inicio": "16:00", "hora_fin": "16:30", "asiste_titular": "1"}
    datos.update(extra)
    return datos


def test_reservar_turno_con_mascota_nueva(entorno):
    c, s = entorno
    login_clinica(c, s)
    datos = _turno(s, nm_nombre="Canela", nm_especie="PERRO", nm_sexo="HEMBRA", nm_fecha_nacimiento="2024-02-01")
    html = post(c, "/clinica/agenda/reservar", datos, "/clinica/agenda/nuevo").text
    assert "Turno reservado: Canela" in html
    assert uno(s, Mascota, nombre="Canela").titular.dni == "40999111"


def test_reservar_turno_rechaza_mascota_elegida_y_nueva(entorno):
    c, s = entorno
    login_clinica(c, s)
    canela = uno(s, Mascota, nombre="Canela")
    datos = _turno(s, mascota_id=canela.id, nm_nombre="Otra", nm_especie="GATO", nm_sexo="MACHO",
                   nm_fecha_nacimiento="2024-02-01", hora_inicio="17:00", hora_fin="17:30")
    html = post(c, "/clinica/agenda/reservar", datos, "/clinica/agenda/nuevo").text
    assert "Ya elegiste una mascota" in aviso_rojo(html)
    assert s.query(Mascota).filter_by(nombre="Otra").count() == 0


def test_mascota_nueva_con_numeros_se_rechaza(entorno):
    c, s = entorno
    login_clinica(c, s)
    datos = _turno(s, nm_nombre="Firu2", nm_especie="PERRO", nm_sexo="MACHO", nm_fecha_nacimiento="2024-02-01",
                   hora_inicio="18:00", hora_fin="18:30")
    html = post(c, "/clinica/agenda/reservar", datos, "/clinica/agenda/nuevo").text
    assert "solo admite letras" in aviso_rojo(html)


# --- 7 y 8: Gestión ---------------------------------------------------------------------------------
def test_editar_profesional_rechaza_email_y_telefono_invalidos(entorno):
    c, s = entorno
    login_clinica(c, s)
    sosa = uno(s, Profesional, apellido="Sosa")
    url = f"/clinica/gestion/profesionales/{sosa.id}"
    html = c.get(f"{url}/editar").text
    assert 'type="email"' in html and 'type="tel"' in html
    datos = {"legajo": sosa.legajo, "matricula": sosa.matricula, "dni": sosa.dni, "nombre": sosa.nombre,
             "apellido": sosa.apellido, "especialidad": sosa.especialidad, "clinica_id": sosa.clinica_id,
             "telefono": sosa.telefono, "email": "sosavetred"}
    assert "formato válido" in aviso_rojo(post(c, url, datos, f"{url}/editar").text)
    assert "solo admite números" in aviso_rojo(post(c, url, {**datos, "email": sosa.email, "telefono": "HGDHD"},
                                                    f"{url}/editar").text)
    assert uno(s, Profesional, apellido="Sosa").email == "sosa@vetred.com.ar"


def test_clinica_de_alta_complejidad_muestra_el_interruptor_fijo(entorno):
    from app.domain.clinica import Clinica
    c, s = entorno
    login_clinica(c, s)
    sur = uno(s, Clinica, nombre="Hospital Veterinario Sur")
    html = c.get(f"/clinica/gestion/clinicas/{sur.id}/editar").text
    assert 'name="alta_complejidad" value="1"' in html and "checked disabled" in html
    assert "no se puede desactivar" in html
    centro = uno(s, Clinica, nombre="Clínica Centro")
    html = c.get(f"/clinica/gestion/clinicas/{centro.id}/editar").text
    assert 'type="checkbox" name="alta_complejidad"' in html and "checked disabled" not in html

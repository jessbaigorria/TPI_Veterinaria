"""Ronda de correcciones del grupo ("Errores y cosas a mejorar"), verificada por HTTP con el seed."""
import pytest
from sqlalchemy import select

from app.domain import reloj
from app.domain.laboratorio import MuestraBiologica
from app.domain.transporte import RemitoBiologico
from tests.web_util import aviso_rojo, crear_entorno, login_clinica, login_lab, post, texto_visible, uno


@pytest.fixture(scope="module")
def entorno():
    c, s = crear_entorno()
    yield c, s
    s.close()


@pytest.fixture(autouse=True)
def reloj_real():
    reloj.liberar()
    yield


# ---------------------------------------------------------------- Bloque A: inicio de sesión
def test_a1_a2_login_solo_sede(entorno):
    c, s = entorno
    html = c.get("/").text
    assert 'name="usuario"' not in html            # sin selector de usuario ni nombre de operador
    assert "Ingresar al Portal Clínica" in html and "Ingresar al Portal Laboratorio" in html
    assert 'class="login-centro"' in html            # A3: tarjetas centradas


def test_a4_barra_superior_muestra_solo_la_sede(entorno):
    c, s = entorno
    login_clinica(c, s)
    visible = texto_visible(c.get("/clinica").text)
    assert "Clínica Centro" in visible and "Cambiar" in visible
    assert "Operador" not in visible and "Recepción" not in visible.split("Inicio")[0]


def test_a4_recepcion_pide_recibido_por(entorno):
    c, s = entorno
    login_lab(c, s)
    r = uno(s, RemitoBiologico, numero="REM-000010")
    url = f"/laboratorio/recepcion/{r.id}"
    assert 'name="recibido_por"' in c.get(url).text
    html = post(c, url, {"precinto_integro": "1", "temperatura": "5", "recibido_por": "123"}, url).text
    assert "solo admite letras" in aviso_rojo(html)
    assert uno(s, RemitoBiologico, numero="REM-000010").estado_actual() == "En tránsito"   # no se recibió
    post(c, url, {"precinto_integro": "1", "temperatura": "5", "recibido_por": "Andrea Gomez",
                  "codigo_precinto": r.precinto.codigo}, url)
    rem = uno(s, RemitoBiologico, numero="REM-000010")
    assert rem.recepcion.usuario_receptor == "Andrea Gomez"
    assert rem.muestras[0].historial()[-1].usuario == "Andrea Gomez"


def test_a4_resultados_piden_analista(entorno):
    c, s = entorno
    login_lab(c, s)
    m = uno(s, MuestraBiologica, codigo="M-000012")
    t = m.analisis_pendientes()[0]
    url = f"/laboratorio/muestras/{m.id}/resultados"
    assert 'name="analista"' in c.get(url).text
    html = post(c, url, {"tipo_analisis_id": [t.id], f"valores_{t.id}": "Normal", "analista": ""}, url).text
    assert "obligatorio" in aviso_rojo(html)
    post(c, url, {"tipo_analisis_id": [t.id], f"valores_{t.id}": "Normal", "analista": "Lucia Ibarra"}, url)
    m = uno(s, MuestraBiologica, codigo="M-000012")
    assert m.estado_actual() == "Analizada" and m.resultados[0].analista == "Lucia Ibarra"


def test_a4_cerrar_remito_pide_colocado_por(entorno):
    c, s = entorno
    login_clinica(c, s, "Hospital Veterinario Sur")
    r = uno(s, RemitoBiologico, numero="REM-000012")
    url = f"/clinica/envios/{r.id}"
    assert 'name="colocado_por"' in c.get(url).text
    html = post(c, f"{url}/cerrar", {"temperatura_despacho": "4", "colocado_por": "x1"}, url).text
    assert "solo admite letras" in aviso_rojo(html)
    post(c, f"{url}/cerrar", {"temperatura_despacho": "4", "colocado_por": "Tomas Ferreyra"}, url)
    assert uno(s, RemitoBiologico, numero="REM-000012").precinto.usuario_colocador == "Tomas Ferreyra"


def test_a4_auditoria_usa_sede_o_profesional(entorno):
    c, s = entorno
    login_clinica(c, s)
    from app.domain.laboratorio import OrdenDerivacion
    o = uno(s, OrdenDerivacion, numero="ORD-000014")
    m = o.muestras[0]
    assert m.historial()[0].usuario == o.atencion.profesional.nombre_completo()   # extracción: el profesional


# ---------------------------------------------------------------- Bloque B: combobox y filtros
PANTALLAS_CON_SELECTORES = ["/clinica/atenciones/nueva", "/clinica/agenda/nuevo", "/clinica/mascotas/nueva",
                            "/clinica/envios/nuevo", "/clinica/atenciones", "/clinica/facturacion",
                            "/clinica/ordenes", "/clinica/mascotas"]


def test_b1_tom_select_en_toda_la_app(entorno):
    c, s = entorno
    login_clinica(c, s)
    for url in PANTALLAS_CON_SELECTORES:
        html = c.get(url).text
        assert "tom-select" in html and 'class="form-select' in html, url
        assert "data-filtra" not in html, url          # sin el cuadro de búsqueda separado


def test_b2_api_devuelve_solo_mascotas_activas(entorno):
    c, s = entorno
    login_clinica(c, s)
    from app.domain.personas import Mascota, Titular
    t = uno(s, Titular, apellido="García")
    baja = uno(s, Mascota, nombre="Firulais")
    post(c, f"/clinica/mascotas/{baja.id}/baja", {}, f"/clinica/mascotas/{baja.id}")
    nombres = [m["nombre"] for m in c.get(f"/api/titulares/{t.id}/mascotas").json()]
    assert "Firulais" not in nombres and "Rocco" in nombres
    post(c, f"/clinica/mascotas/{baja.id}/reactivar", {}, f"/clinica/mascotas/{baja.id}")


def test_b3_profesionales_agrupados_por_especialidad(entorno):
    c, s = entorno
    login_clinica(c, s)
    for url in ("/clinica/agenda/nuevo", "/clinica/atenciones/nueva"):
        html = c.get(url).text
        assert '<optgroup label="Dermatología">' in html and '<optgroup label="Clínica general">' in html
        assert "(Clínica general)" not in html and "(Dermatología)" not in html


def test_b4_filtros_dicen_todos(entorno):
    c, s = entorno
    login_clinica(c, s)
    html = c.get("/clinica/atenciones").text
    assert ">Todos los estados<" in html and ">Todos los tipos<" in html
    html = c.get("/clinica/facturacion").text
    assert ">Todos los estados<" in html and ">Todos los tipos<" in html
    assert '<option value="">Estado</option>' not in html and '<option value="">Tipo</option>' not in html


def test_b5_sin_lupa_emoji(entorno):
    c, s = entorno
    login_clinica(c, s)
    for url in PANTALLAS_CON_SELECTORES + ["/clinica/clientes"]:
        html = c.get(url).text
        assert "🔎" not in html, url
    assert "bi-search text-secondary" in c.get("/clinica/clientes").text

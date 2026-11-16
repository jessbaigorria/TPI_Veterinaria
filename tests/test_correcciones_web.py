"""Ronda de correcciones del grupo ("Errores y cosas a mejorar"), verificada por HTTP con el seed."""
import pytest
from sqlalchemy import select

from app.domain import reloj
from app.domain.muestra import MuestraBiologica
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


# ---------------------------------------------------------------- Bloque C: fechas y horarios por HTTP
def test_c1_listado_rango_invertido_muestra_error(entorno):
    c, s = entorno
    login_clinica(c, s)
    html = c.get("/clinica/atenciones?desde=2026-12-10&hasta=2026-12-01",
                 headers={"referer": "http://testserver/clinica/atenciones"}).text
    assert "no puede ser anterior" in aviso_rojo(html)


def test_c2_listado_vacio_muestra_estado_vacio(entorno):
    c, s = entorno
    login_clinica(c, s)
    html = c.get("/clinica/atenciones?desde=2001-01-01&hasta=2001-01-02").text
    assert "No hay registros para mostrar" in html and "<tbody>" not in html


def test_c3_reservar_turno_sin_urgencia_y_con_cirugia_otro(entorno):
    c, s = entorno
    login_clinica(c, s)
    html = c.get("/clinica/agenda/nuevo").text
    tipos = html.split('name="tipo"')[1].split("</select>")[0]
    assert ">Urgencia<" not in tipos and ">Cirugía<" in tipos and ">Otro<" in tipos
    html = c.get("/clinica/atenciones/nueva").text
    tipos = html.split('name="tipo"')[1].split("</select>")[0]
    assert ">Urgencia<" in tipos and ">Cirugía<" in tipos and ">Otro<" in tipos


def test_c5_campos_de_hora_sin_step_de_15(entorno):
    c, s = entorno
    login_clinica(c, s)
    html = c.get("/clinica/agenda/nuevo").text
    assert 'step="900"' not in html and 'step="300"' in html and 'min="08:00"' in html


def test_c7_turno_en_el_pasado_rechazado(entorno):
    c, s = entorno
    login_clinica(c, s)
    from app.domain.personas import Mascota
    m = uno(s, Mascota, nombre="Nina")
    ayer = (reloj.hoy() - __import__("datetime").timedelta(days=1)).isoformat()
    html = post(c, "/clinica/agenda/reservar", {"titular_id": m.titular_id, "mascota_id": m.id,
                                                "profesional_id": m.historia_clinica.atenciones[0].profesional_id,
                                                "tipo": "CONSULTA", "fecha": ayer, "hora_inicio": "10:00",
                                                "hora_fin": "10:30"}, "/clinica/agenda/nuevo").text
    assert "posterior al actual" in aviso_rojo(html)


# ---------------------------------------------------------------- Bloque D: Registrar atención médica
def _datos_atencion(s, mascota="Michi", **extra):
    from app.domain.clinica import Profesional
    from app.domain.personas import Mascota
    m = uno(s, Mascota, nombre=mascota)
    perez = uno(s, Profesional, apellido="Pérez")
    inicio = (reloj.ahora() - __import__("datetime").timedelta(days=3)).replace(hour=11, minute=0)
    datos = {"titular_id": m.titular_id, "mascota_id": m.id, "profesional_id": perez.id, "tipo": "URGENCIA",
             "inicio": inicio.strftime("%Y-%m-%dT%H:%M"), "duracion": "30", "asiste_titular": "1"}
    datos.update(extra)
    return datos


def test_d1_d2_d6_titulo_sin_recuadros_tecnicos(entorno):
    c, s = entorno
    login_clinica(c, s)
    html = c.get("/clinica/atenciones/nueva").text
    assert "Registrar atención médica sin turno previo" in html
    assert "Caso 1" not in html and "Caso 2" not in html and "Caso 3" not in html
    assert "Al registrar se controla" not in html


def test_d3_crear_titular_y_volver_con_el_titular_elegido(entorno):
    c, s = entorno
    login_clinica(c, s)
    html = c.get("/clinica/atenciones/nueva").text
    titular, resto = html.split('name="titular_id"', 1)[1].split("</select>", 1)
    assert 'href="/clinica/clientes/nuevo?next=/clinica/atenciones/nueva"' in resto.split('name="mascota_id"')[0]
    assert 'name="next" value="/clinica/atenciones/nueva"' in c.get("/clinica/clientes/nuevo?next=/clinica/atenciones/nueva").text
    r = c.post("/clinica/clientes", data={"dni": "40111222", "nombre": "Delfina", "apellido": "Paz",
                                          "direccion": "San Martín 100", "telefono": "3514000000",
                                          "email": "delfina@mail.com", "next": "/clinica/atenciones/nueva"},
               follow_redirects=False)
    from app.domain.personas import Titular
    t = uno(s, Titular, dni="40111222")
    assert r.headers["location"] == f"/clinica/atenciones/nueva?titular={t.id}"
    html = c.get(r.headers["location"]).text
    assert f'<option value="{t.id}" selected>' in html


def test_d4_nueva_mascota_desplegada_y_validada(entorno):
    c, s = entorno
    login_clinica(c, s)
    html = c.get("/clinica/atenciones/nueva").text
    assert 'name="nm_nombre"' in html and 'id="nueva_mascota"' not in html     # sin interruptor: ya desplegada
    datos = _datos_atencion(s, mascota_id="")
    datos["mascota_id"] = ""
    html = post(c, "/clinica/atenciones/registrar", datos, "/clinica/atenciones/nueva").text
    assert "Elegí una mascota del titular o completá los datos de la mascota nueva" in aviso_rojo(html)
    datos.update({"nm_nombre": "Pelusa", "nm_especie": "GATO", "nm_sexo": "HEMBRA",
                  "nm_fecha_nacimiento": "2025-01-10"})
    post(c, "/clinica/atenciones/registrar", datos, "/clinica/atenciones/nueva")
    from app.domain.personas import Mascota
    assert uno(s, Mascota, nombre="Pelusa").historia_clinica.atenciones


def test_d5_responsable_presente_solo_letras(entorno):
    c, s = entorno
    login_clinica(c, s)
    html = c.get("/clinica/atenciones/nueva").text
    assert 'name="responsable_presente"' in html and 'minlength="3"' in html and "pattern=" in html
    datos = _datos_atencion(s, asiste_titular="0", responsable_presente="5")
    html = post(c, "/clinica/atenciones/registrar", datos, "/clinica/atenciones/nueva").text
    assert "solo admite letras" in aviso_rojo(html)
    datos = _datos_atencion(s, asiste_titular="0", responsable_presente="Lu")
    html = post(c, "/clinica/atenciones/registrar", datos, "/clinica/atenciones/nueva").text
    assert "al menos 3" in aviso_rojo(html)


# ---------------------------------------------------------------- Bloque E: atención finalizada e importes
def _atencion(s, estado):
    from app.domain.atencion import AtencionClinica
    from app.domain.enums import EstadoAtencion
    s.expire_all()
    return s.scalars(select(AtencionClinica).where(AtencionClinica.estado == EstadoAtencion(estado),
                                                   AtencionClinica.clinica.has(nombre="Clínica Centro"))).first()


def test_e1_importe_obligatorio_y_mayor_a_cero(entorno):
    c, s = entorno
    login_clinica(c, s)
    a = _atencion(s, "EN_PROGRESO")
    url = f"/clinica/atenciones/{a.id}"
    html = c.get(url).text
    assert 'name="importe" required min="0.01"' in html
    for importe in ("", "0"):
        html = post(c, f"{url}/finalizar", {"diagnostico": "Sano", "importe": importe}, url).text
        assert "importe es obligatorio y debe ser mayor a cero" in aviso_rojo(html)
    assert _atencion(s, "EN_PROGRESO") is not None


def test_e2_atencion_finalizada_no_emite_ordenes_ni_derivaciones(entorno):
    c, s = entorno
    login_clinica(c, s)
    a = _atencion(s, "FINALIZADA")
    html = c.get(f"/clinica/atenciones/{a.id}").text
    assert "Emitir orden de laboratorio" not in html and "Derivar a cirugía" not in html
    assert "Emitir comprobante" in html or "Ver comprobante" in html
    html = c.get(f"/clinica/ordenes/nueva?atencion={a.id}", headers={"referer": f"http://testserver/clinica/atenciones/{a.id}"}).text
    assert "ya está finalizada" in aviso_rojo(html)
    from app.domain.laboratorio import Laboratorio, TipoAnalisis
    html = post(c, "/clinica/ordenes", {"atencion_id": a.id, "laboratorio_id": s.scalars(select(Laboratorio)).first().id,
                                        "analisis_id": [s.scalars(select(TipoAnalisis)).first().id]},
                f"/clinica/atenciones/{a.id}").text
    assert "ya está finalizada" in aviso_rojo(html)
    html = post(c, "/clinica/cirugias", {"atencion_id": a.id, "destino_id": 3, "tipo_cirugia": "Biopsia"},
                f"/clinica/atenciones/{a.id}").text
    assert "ya está finalizada" in aviso_rojo(html)


def test_e3_en_curso_ofrece_ordenes_y_derivaciones_antes_de_finalizar(entorno):
    c, s = entorno
    login_clinica(c, s)
    html = c.get(f"/clinica/atenciones/{_atencion(s, 'EN_PROGRESO').id}").text
    assert "Emitir orden de laboratorio" in html and "Derivar a cirugía" in html
    assert html.index("Órdenes de laboratorio") < html.index("Finalizar atención")
    assert "Emitir comprobante" not in html


def test_e4_seed_sin_finalizadas_sin_importe_ni_derivaciones_posteriores(entorno):
    c, s = entorno
    from app.domain.atencion import AtencionClinica
    from app.domain.enums import EstadoAtencion
    for a in s.scalars(select(AtencionClinica).where(AtencionClinica.estado == EstadoAtencion.FINALIZADA)):
        assert a.importe and a.importe > 0
        for o in a.ordenes:
            assert o.fecha_emision <= a.fecha_hora_fin
        for d in a.derivaciones:
            assert d.fecha_solicitud <= a.fecha_hora_fin


# ---------------------------------------------------------------- Bloque F: titulares y mascotas
TITULAR_OK = {"dni": "41 222 333", "nombre": "Rocío", "apellido": "Benítez", "direccion": "Ituzaingó 300",
              "telefono": "3515550000", "email": "rocio@mail.com"}


def test_f1_formulario_titular_con_validaciones_html(entorno):
    c, s = entorno
    login_clinica(c, s)
    html = c.get("/clinica/clientes/nuevo").text
    for nombre in ("dni", "nombre", "apellido", "direccion", "telefono", "email"):
        bloque = html.split(f'name="{nombre}"', 1)[1].split(">", 1)[0]
        assert "required" in bloque, nombre
    assert "data-mascara-dni" in html and 'pattern="[0-9]{8,15}"' in html and 'type="email"' in html


@pytest.mark.parametrize("campo,valor,mensaje", [("dni", "12ab5678", "solo admite números"),
                                                 ("dni", "", "obligatorio"),
                                                 ("telefono", "351-555", "solo admite números"),
                                                 ("telefono", "", "obligatorio"),
                                                 ("email", "rocio@", "formato válido"),
                                                 ("direccion", "", "obligatorio"),
                                                 ("nombre", "R0cío", "solo admite letras")])
def test_f1_alta_titular_invalida_muestra_mensaje(entorno, campo, valor, mensaje):
    c, s = entorno
    login_clinica(c, s)
    html = post(c, "/clinica/clientes", {**TITULAR_OK, campo: valor}, "/clinica/clientes/nuevo").text
    assert mensaje in aviso_rojo(html)


def test_f1_alta_titular_guarda_solo_digitos_y_no_repite(entorno):
    c, s = entorno
    login_clinica(c, s)
    post(c, "/clinica/clientes", TITULAR_OK, "/clinica/clientes/nuevo")
    from app.domain.personas import Titular
    t = uno(s, Titular, dni="41222333")
    assert "41 222 333" in c.get(f"/clinica/clientes/{t.id}").text
    html = post(c, "/clinica/clientes", {**TITULAR_OK, "email": "otra@mail.com"}, "/clinica/clientes/nuevo").text
    assert "Ya existe un titular con DNI 41222333" in aviso_rojo(html)


def test_f2_baja_con_modal_que_lista_mascotas(entorno):
    c, s = entorno
    login_clinica(c, s)
    from app.domain.personas import Titular
    t = uno(s, Titular, apellido="García")
    html = c.get(f"/clinica/clientes/{t.id}").text
    assert f'data-confirm="¿Confirmás dar de baja a {t.nombre_completo()}?"' in html
    assert "También se van a dar de baja sus 2 mascotas:" in html and "Rocco" in html
    assert 'id="modal-confirmar"' in html and ">Aceptar<" in html and ">Cancelar<" in html
    assert "confirm(" not in c.get("/static/app.js").text


def test_f3_nueva_mascota_sin_textos_tecnicos_y_titular_preseleccionado(entorno):
    c, s = entorno
    login_clinica(c, s)
    from app.domain.personas import Titular
    t = uno(s, Titular, apellido="García")
    html = c.get(f"/clinica/mascotas/nueva?titular={t.id}").text
    assert "MascotaSinTitularError" not in html and "dominio" not in html and "Validación:" not in html
    assert f'<option value="{t.id}" selected>' in html
    assert 'href="/clinica/clientes/nuevo?next=/clinica/mascotas/nueva"' in html
    html = post(c, "/clinica/mascotas", {"titular_id": "", "nombre": "Sola", "especie": "GATO", "sexo": "HEMBRA",
                                         "fecha_nacimiento": "2024-01-01"}, "/clinica/mascotas/nueva").text
    assert "sin titular responsable" in aviso_rojo(html)


# ---------------------------------------------------------------- Bloque G: órdenes y badges
def test_g1_boton_registrar_muestra(entorno):
    c, s = entorno
    login_clinica(c, s)
    from app.domain.laboratorio import OrdenDerivacion
    html = c.get(f"/clinica/ordenes/{uno(s, OrdenDerivacion, numero='ORD-000014').id}").text
    assert ">Registrar muestra</button>" in html and "nace Extraída" not in html


def test_g2_badges_alineados_en_encabezados(entorno):
    c, s = entorno
    login_clinica(c, s)
    from app.domain.laboratorio import OrdenDerivacion
    html = c.get(f"/clinica/ordenes/{uno(s, OrdenDerivacion, numero='ORD-000009').id}").text
    assert 'class="d-flex align-items-center flex-wrap gap-2 acciones-encabezado"' in html
    css = c.get("/static/estilos.css").text
    regla = css.split(".badge.estado {", 1)[1].split("}", 1)[0]
    assert "align-items: center" in regla and "height: auto" in regla


# ---------------------------------------------------------------- Bloque H: reportes
REPORTES = ("atenciones", "rechazos", "tiempos", "facturacion", "vacunas")


def test_h1_h2_sin_siglas_r1_r5(entorno):
    import re
    c, s = entorno
    login_clinica(c, s)
    paginas = ["/clinica/reportes"] + [f"/clinica/reportes/{r}" for r in REPORTES]
    for url in paginas:
        visible = texto_visible(c.get(url).text)
        assert not re.search(r"\bR[1-5]\b", visible), url
    indice = c.get("/clinica/reportes").text
    for nombre in ("Atenciones y derivaciones", "Muestras rechazadas", "Tiempos de tránsito",
                   "Facturación por clínica y laboratorio", "Vacunas pendientes"):
        assert nombre in indice
    login_lab(c, s)
    for url in ("/laboratorio/reportes", "/laboratorio/reportes/rechazos", "/laboratorio/reportes/tiempos"):
        visible = texto_visible(c.get(url).text)
        assert not re.search(r"\bR[1-5]\b", visible), url
    html = c.get("/laboratorio/reportes/rechazos").text
    assert ">Muestras rechazadas</a>" in html and ">Tiempos de tránsito</a>" in html


def test_h3_fechas_obligatorias_y_rango(entorno):
    c, s = entorno
    login_clinica(c, s)
    html = c.get("/clinica/reportes/atenciones").text
    assert html.count('type="date"') == 2 and html.count(" required") >= 2
    desde = html.split('name="desde" required value="')[1][:10]
    hasta = html.split('name="hasta" required')[1].split('value="')[1][:10]
    from datetime import date
    assert (date.fromisoformat(hasta) - date.fromisoformat(desde)).days == 30
    ref = {"referer": "http://testserver/clinica/reportes"}
    html = c.get("/clinica/reportes/atenciones?desde=2026-05-10&hasta=2026-05-01", headers=ref).text
    assert "no puede ser anterior" in aviso_rojo(html)
    html = c.get("/clinica/reportes/atenciones?desde=&hasta=2026-05-01", headers=ref).text
    assert "obligatorias" in aviso_rojo(html)


def test_h4_exportar_pdf(entorno):
    c, s = entorno
    login_clinica(c, s)
    assert "Exportar PDF" in c.get("/clinica/reportes/facturacion").text
    for r in REPORTES:
        resp = c.get(f"/clinica/reportes/{r}?formato=pdf")
        assert resp.status_code == 200 and resp.headers["content-type"] == "application/pdf", r
        assert resp.content.startswith(b"%PDF") and len(resp.content) > 2000, r
        assert f'filename="{r}_' in resp.headers["content-disposition"]
    login_lab(c, s)
    resp = c.get("/laboratorio/reportes/tiempos?formato=pdf")
    assert resp.content.startswith(b"%PDF")


def test_h4_pdf_contenido():
    """El PDF lleva nombre del reporte, sede, filtros, montos en pesos y fechas dd/mm/aaaa."""
    from datetime import date
    from decimal import Decimal
    from app.reportes.comun import Filtro, Grafico, Reporte, Tabla
    from app.reportes.pdf import a_pdf
    rep = Reporte("facturacion", "Facturación por clínica y laboratorio", "desc", Filtro(date(2026, 1, 1), date(2026, 1, 31)),
                  [Tabla("Totales", ["Clínica", "Fecha", "Total"], [["Clínica Centro", date(2026, 1, 5), Decimal("12500")]],
                         ["Total", "", Decimal("12500")])],
                  [Grafico("Facturación", "bar", ["Clínica Centro"], [{"label": "Total", "data": [Decimal("12500")]}])],
                  [("Total facturado", "$ 12.500,00")])
    from reportlab import rl_config
    anterior, rl_config.pageCompression = rl_config.pageCompression, 0   # PDF sin comprimir para leer el texto
    try:
        texto = a_pdf(rep, "Clínica Centro", [("Desde", "01/01/2026"), ("Hasta", "31/01/2026")])
    finally:
        rl_config.pageCompression = anterior
    for esperado in (b"Facturaci", b"Cl\\355nica Centro", b"01/01/2026", b"31/01/2026", b"$ 12.500,00", b"05/01/2026"):
        assert esperado in texto, esperado


# ---------------------------------------------------------------- Bloque I: gestión y facturación
def test_i1_catalogos_ahora_es_gestion(entorno):
    c, s = entorno
    login_clinica(c, s)
    html = c.get("/clinica/gestion").text
    assert 'href="/clinica/gestion"' in html and ">Gestión</h3>" in html.replace(' class="titulo-seccion"', "")
    assert "Catálogos" not in texto_visible(html)
    r = c.get("/clinica/catalogos?tab=vacunas", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/clinica/gestion?tab=vacunas"
    assert "Gestión" in c.get("/clinica/gestion/clinicas/nuevo").text


def test_i2_emitir_desde_pendientes_actualiza_la_lista(entorno):
    import re
    c, s = entorno
    login_clinica(c, s)
    html = c.get("/clinica/facturacion").text
    total_antes = int(re.search(r"data-contador-pendientes>(\d+)<", html).group(1))
    atencion_id = re.search(r'action="/clinica/facturacion/atencion/(\d+)"', html).group(1)
    r = c.post(f"/clinica/facturacion/atencion/{atencion_id}", data={"volver": "/clinica/facturacion"},
               follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/clinica/facturacion"     # POST → redirect → GET
    html = c.get("/clinica/facturacion").text
    assert re.search(r"Comprobante FAC-\d{6} emitido", html)
    assert f'action="/clinica/facturacion/atencion/{atencion_id}"' not in html             # ya no está pendiente
    assert int(re.search(r"data-contador-pendientes>(\d+)<", html).group(1)) == total_antes - 1
    assert c.get("/clinica/facturacion").headers["cache-control"] == "no-store"
    html = post(c, f"/clinica/facturacion/atencion/{atencion_id}", {"volver": "/clinica/facturacion"},
                "/clinica/facturacion").text
    msg = aviso_rojo(html)
    assert re.match(r"Esta atención ya fue facturada \(FAC-\d{6}\)\.", msg) and "VeterinariaError" not in html


def test_i2_pago_y_anulacion_con_mensaje_claro(entorno):
    import re
    c, s = entorno
    login_clinica(c, s)
    from app.domain.enums import EstadoFactura
    from app.domain.facturacion import Factura
    s.expire_all()
    f = s.scalars(select(Factura).where(Factura.estado == EstadoFactura.EMITIDA, Factura.clinica_id == 1)).first()
    html = post(c, f"/clinica/facturas/{f.id}/pagar", {"forma_pago": "EFECTIVO"}, f"/clinica/facturacion/{f.id}").text
    assert f"Pago del comprobante {f.numero} registrado" in html and "Pagada" in html


def test_gestion_precio_negativo_rechazado_al_crear_y_editar(entorno):
    c, s = entorno
    login_clinica(c, s)
    datos = {"codigo": "TST", "nombre": "Prueba", "precio": "-10", "tipo_muestra_requerida": "SANGRE",
             "temperatura_min": "2", "temperatura_max": "8", "tiempo_estimado_horas": "4"}
    html = post(c, "/clinica/gestion/analisis", datos, "/clinica/gestion/analisis/nuevo").text
    assert "no puede ser negativo" in aviso_rojo(html)
    from app.domain.laboratorio import TipoAnalisis
    hem = uno(s, TipoAnalisis, codigo="HEM")
    html = post(c, f"/clinica/gestion/analisis/{hem.id}", {**datos, "codigo": "HEM"}, f"/clinica/gestion/analisis/{hem.id}/editar").text
    assert "no puede ser negativo" in aviso_rojo(html)

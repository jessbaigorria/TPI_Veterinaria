"""Escenario de demo de la sección 11 de context.md, recorrido de punta a punta por HTTP
(TestClient) sobre la app con el seed cargado. Cada paso verifica el resultado esperado,
incluidos los errores de validación que se muestran en la UI."""
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app import db
from app.domain import reloj
from app.domain.atencion import AtencionClinica, Clinica, DerivacionCirugia, Profesional
from app.domain.enums import EstadoOrden
from app.domain.laboratorio import Laboratorio, MuestraBiologica, OrdenDerivacion, TipoAnalisis
from app.domain.personas import Mascota, Vacuna
from app.domain.transporte import Contenedor, RemitoBiologico
from app.seed import sembrar

HOY = date.today()
DIA = HOY + timedelta(days=2)


@pytest.fixture(scope="module")
def demo():
    reloj.liberar()
    eng = db.crear_engine("sqlite://")
    db.init_db(eng)
    s = db.crear_fabrica_sesiones(eng)()
    sembrar(s, HOY)
    from app.main import crear_app
    yield TestClient(crear_app(motor=eng)), s
    s.close()


@pytest.fixture(autouse=True)
def reloj_real():
    reloj.liberar()
    yield


def uno(s, modelo, **filtros):
    s.expire_all()
    return s.scalars(select(modelo).filter_by(**filtros)).one()


def post(c, url, data, desde="/clinica"):
    return c.post(url, data=data, headers={"referer": f"http://testserver{desde}"})


def login_clinica(c, s, nombre, usuario):
    post(c, "/ingresar", {"portal": "clinica", "clinica_id": uno(s, Clinica, nombre=nombre).id, "usuario": usuario})


def login_lab(c, s):
    post(c, "/ingresar", {"portal": "laboratorio", "laboratorio_id": s.scalars(select(Laboratorio)).first().id,
                          "usuario": "Gómez (bioquímico)"})


def ciclo_laboratorio(c, s, atencion_id, integro: bool, contenedor: str):
    """Pasos 4 a 6: orden (hemograma + perfil renal) → muestra → remito → despacho → recepción."""
    hem, ren = uno(s, TipoAnalisis, codigo="HEM"), uno(s, TipoAnalisis, codigo="REN")
    lab = s.scalars(select(Laboratorio)).first()
    r = post(c, "/clinica/ordenes", {"atencion_id": atencion_id, "laboratorio_id": lab.id,
                                     "analisis_id": [hem.id, ren.id], "prioridad": "NORMAL",
                                     "observaciones": "Control general"})
    assert "Orden ORD-" in r.text
    orden = s.scalars(select(OrdenDerivacion).order_by(OrdenDerivacion.id.desc())).first()
    s.refresh(orden)
    r = post(c, f"/clinica/ordenes/{orden.id}/muestras", {"tipo": "SANGRE", "volumen": "3"})
    assert "Extraída" in r.text
    muestra = s.scalars(select(MuestraBiologica).order_by(MuestraBiologica.id.desc())).first()
    # Paso 5: armar remito, cerrar con precinto, despachar y confirmar retiro.
    r = post(c, "/clinica/envios", {"laboratorio_id": lab.id, "contenedor_id": uno(s, Contenedor, codigo=contenedor).id})
    remito = s.scalars(select(RemitoBiologico).order_by(RemitoBiologico.id.desc())).first()
    r = post(c, f"/clinica/envios/{remito.id}/muestras", {"muestra_id": [muestra.id]})
    assert "Empaquetada" in r.text
    r = post(c, f"/clinica/envios/{remito.id}/cerrar", {"codigo_precinto": "", "temperatura_despacho": "4", "colocado_por": "Marta Suarez"})
    assert "cerrado con el precinto PRE-" in r.text
    r = post(c, f"/clinica/envios/{remito.id}/despachar", {
        "transportista": "Logística Fría SRL", "vehiculo": "AE123KD",
        "llegada_estimada": (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M")})
    assert "En tránsito" in r.text
    r = post(c, f"/clinica/envios/{remito.id}/retiro", {})
    assert uno(s, RemitoBiologico, id=remito.id).estado_actual() == "En tránsito"
    # Paso 6: Portal Laboratorio.
    login_lab(c, s)
    assert remito.numero in c.get("/laboratorio/recepcion").text
    precinto = uno(s, RemitoBiologico, id=remito.id).precinto.codigo
    r = post(c, f"/laboratorio/recepcion/{remito.id}", {"codigo_precinto": precinto,
                                                       "precinto_integro": "1" if integro else "0",
                                                       "temperatura": "5", "recibido_por": "Andrea Gomez"},
             "/laboratorio/recepcion")
    return orden.id, muestra.id, remito.id, r


def test_escenario_de_demo(demo):
    c, s = demo
    # 1) Turno y turno superpuesto ------------------------------------------------------
    login_clinica(c, s, "Clínica Centro", "Laura Pérez")
    perez = uno(s, Profesional, apellido="Pérez")
    firulais, rocco = uno(s, Mascota, nombre="Firulais"), uno(s, Mascota, nombre="Rocco")
    turno = {"titular_id": firulais.titular_id, "mascota_id": firulais.id, "profesional_id": perez.id,
             "tipo": "CONSULTA", "fecha": DIA.isoformat(), "hora_inicio": "14:00", "motivo": "Control de piel",
             "asiste_titular": "1"}
    r = post(c, "/clinica/agenda/reservar", turno, "/clinica/agenda/nuevo")
    assert "Turno reservado" in r.text
    r = post(c, "/clinica/agenda/reservar", {**turno, "mascota_id": rocco.id, "hora_inicio": "14:15"},
             "/clinica/agenda/nuevo")
    assert "ya tiene un turno de" in r.text and "alert-danger" in r.text

    # 2) Vacunas: CONTROL bloqueado → VACUNACIÓN → CONTROL pasa ----------------------------
    atencion = {"titular_id": rocco.titular_id, "mascota_id": rocco.id, "profesional_id": perez.id,
                "tipo": "CONTROL", "inicio": f"{HOY}T19:00", "duracion": "30", "asiste_titular": "1"}
    r = post(c, "/clinica/atenciones/registrar", atencion, "/clinica/atenciones/nueva")
    assert "tiene vacunas obligatorias pendientes" in r.text and "Antirrábica" in r.text
    assert "Reservar turno de VACUNACIÓN" in r.text
    r = post(c, "/clinica/atenciones/registrar", {**atencion, "tipo": "VACUNACION", "inicio": f"{HOY}T19:30"},
             "/clinica/atenciones/nueva")
    vac = s.scalars(select(AtencionClinica).order_by(AtencionClinica.id.desc())).first()
    vacunas = [v.id for v in s.scalars(select(Vacuna).where(Vacuna.especie == rocco.especie,
                                                             Vacuna.obligatoria.is_(True)))]
    datos = {"diagnostico": "Se aplican refuerzos", "importe": "9000", "vacuna_id": vacunas}
    datos.update({f"lote_{v}": f"LT{v}" for v in vacunas})
    r = post(c, f"/clinica/atenciones/{vac.id}/finalizar", datos)
    assert "Se registraron 2 vacuna(s)" in r.text
    r = post(c, "/clinica/atenciones/registrar", {**atencion, "inicio": f"{HOY}T20:00"}, "/clinica/atenciones/nueva")
    assert "Atención registrada e iniciada" in r.text
    control = s.scalars(select(AtencionClinica).order_by(AtencionClinica.id.desc())).first()

    # 3) Mascota sin titular ---------------------------------------------------------------
    r = post(c, "/clinica/mascotas", {"titular_id": "", "nombre": "Huérfano", "especie": "GATO", "sexo": "MACHO",
                                      "fecha_nacimiento": "2024-05-01"}, "/clinica/mascotas/nueva")
    assert "sin titular responsable" in r.text

    # 4–6) Orden, muestra, remito, recepción OK, resultados → Analizada y orden COMPLETADA ----
    orden_id, muestra_id, remito_id, r = ciclo_laboratorio(c, s, control.id, integro=True, contenedor="CEN-02")
    assert "ACEPTADA" in r.text and "Recibida" in r.text
    m = uno(s, MuestraBiologica, id=muestra_id)
    datos = {"tipo_analisis_id": [t.id for t in m.analisis_pendientes()], "analista": "Andrea Gomez"}
    for t in m.analisis_pendientes():
        datos.update({f"valores_{t.id}": "Dentro de valores normales", f"unidad_{t.id}": "-"})
    r = post(c, f"/laboratorio/muestras/{muestra_id}/resultados", datos, "/laboratorio/muestras")
    assert "Estado: Analizada" in r.text
    assert uno(s, OrdenDerivacion, id=orden_id).estado is EstadoOrden.COMPLETADA  # Observer

    # 7) Mismo circuito con precinto roto → rechazadas → MuestraRechazadaError ---------------
    login_clinica(c, s, "Clínica Centro", "Laura Pérez")
    orden2_id, muestra2_id, remito2_id, r = ciclo_laboratorio(c, s, control.id, integro=False, contenedor="CEN-03")
    assert "RECHAZADA" in r.text and "Precinto roto" in r.text
    assert uno(s, RemitoBiologico, id=remito2_id).estado_actual() == "Recibido con observaciones"
    assert uno(s, MuestraBiologica, id=muestra2_id).estado_actual() == "Rechazada"
    hem = uno(s, TipoAnalisis, codigo="HEM")
    r = post(c, f"/laboratorio/muestras/{muestra2_id}/resultados",
             {"tipo_analisis_id": [hem.id], f"valores_{hem.id}": "x", "analista": "Andrea Gomez"}, f"/laboratorio/muestras/{muestra2_id}/resultados")
    assert "fue rechazada" in r.text and "no se pueden registrar resultados" in r.text

    # 8) Línea de tiempo de ambas muestras (historial inmutable) --------------------------
    for mid, ultimo in ((muestra_id, "Analizada"), (muestra2_id, "Rechazada")):
        m = uno(s, MuestraBiologica, id=mid)
        r = c.get(f"/laboratorio/trazabilidad?codigo={m.codigo}")
        assert r.status_code == 200 and "Historial inmutable" in r.text
        assert [h.estado_nuevo for h in m.historial()][-1] == ultimo
        assert m.historial()[0].estado_anterior == "—"

    # 9) Cirugía de alta complejidad entre dos clínicas ---------------------------------------
    login_clinica(c, s, "Clínica Centro", "Laura Pérez")
    sur = uno(s, Clinica, nombre="Hospital Veterinario Sur")
    norte = uno(s, Clinica, nombre="Clínica Norte")
    r = post(c, "/clinica/cirugias", {"atencion_id": control.id, "destino_id": norte.id, "tipo_cirugia": "Biopsia"})
    assert "no está habilitada para cirugías de alta complejidad" in r.text
    r = post(c, "/clinica/cirugias", {"atencion_id": control.id, "destino_id": sur.id, "tipo_cirugia": "Nodulectomía",
                                      "riesgo_anestesico": "ASA_II", "prioridad": "NORMAL"})
    d = s.scalars(select(DerivacionCirugia).order_by(DerivacionCirugia.id.desc())).first()
    login_clinica(c, s, "Hospital Veterinario Sur", "Diego Ríos")
    assert d.numero in c.get("/clinica/cirugias?tab=recibidas").text
    cirujano = uno(s, Profesional, apellido="Ríos")
    post(c, f"/clinica/cirugias/{d.id}/aceptar", {"cirujano_id": cirujano.id})
    fecha = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%dT10:00")
    r = post(c, f"/clinica/cirugias/{d.id}/programar", {"fecha": fecha}, f"/clinica/cirugias/{d.id}")
    assert "sin el consentimiento firmado" in r.text and "alert-danger" in r.text
    post(c, f"/clinica/cirugias/{d.id}/consentimiento", {})
    r = post(c, f"/clinica/cirugias/{d.id}/programar", {"fecha": fecha})
    assert "programada" in r.text
    r = post(c, f"/clinica/cirugias/{d.id}/realizar", {"informe": "Exéresis completa, sin complicaciones."})
    assert "realizada" in r.text
    r = post(c, f"/clinica/facturacion/cirugia/{d.id}", {"importe": "120000"})
    assert "Comprobante FAC-" in r.text and "$ 120.000,00" in r.text

    # 10) Facturar atención y laboratorio; abrir los 5 reportes -----------------------------
    login_clinica(c, s, "Clínica Centro", "Laura Pérez")
    post(c, f"/clinica/atenciones/{control.id}/finalizar", {"diagnostico": "Paciente sano", "importe": "12000"})
    r = post(c, f"/clinica/facturacion/atencion/{control.id}", {})
    assert "Comprobante FAC-" in r.text
    r = post(c, f"/clinica/facturacion/atencion/{control.id}", {}, f"/clinica/atenciones/{control.id}")
    assert "Esta atención ya fue facturada" in r.text  # no se factura dos veces
    r = post(c, f"/clinica/facturacion/orden/{orden_id}", {})
    assert "Comprobante FAC-" in r.text and "Hemograma completo" in r.text
    r = post(c, f"/clinica/facturacion/orden/{orden2_id}", {}, "/clinica/facturacion")
    assert "nada para facturar" in r.text  # no se cobran muestras rechazadas
    for i in range(1, 6):
        r = c.get(f"/clinica/reportes/r{i}")
        assert r.status_code == 200 and "data-grafico" in r.text

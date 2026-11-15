"""Smoke test web: las páginas principales de ambos portales responden 200 con el seed cargado,
y los errores de negocio se muestran en un aviso rojo sin romper la pantalla."""
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app import db
from app.domain import reloj
from app.domain.atencion import AtencionClinica, Clinica, DerivacionCirugia
from app.domain.facturacion import Factura
from app.domain.laboratorio import Laboratorio, MuestraBiologica, OrdenDerivacion
from app.domain.personas import Mascota, Titular
from app.domain.transporte import RecepcionRemito, RemitoBiologico
from app.seed import sembrar


@pytest.fixture(scope="module")
def entorno():
    reloj.liberar()
    eng = db.crear_engine("sqlite://")
    db.init_db(eng)
    s = db.crear_fabrica_sesiones(eng)()
    sembrar(s, date.today())
    from app.main import crear_app
    app = crear_app(motor=eng)
    yield app, s
    s.close()


@pytest.fixture(autouse=True)
def reloj_real():
    reloj.liberar()  # la app trabaja con la hora real (el seed es relativo a hoy)
    yield


def _login_clinica(client, s, nombre="Clínica Centro", usuario="Laura Pérez"):
    c = s.scalars(select(Clinica).where(Clinica.nombre == nombre)).one()
    r = client.post("/ingresar", data={"portal": "clinica", "clinica_id": c.id, "usuario": usuario})
    assert r.status_code == 200  # sigue la redirección
    return c


def _login_lab(client, s):
    lab = s.scalars(select(Laboratorio)).first()
    client.post("/ingresar", data={"portal": "laboratorio", "laboratorio_id": lab.id, "usuario": "Gómez"})
    return lab


def test_ingreso_y_proteccion(entorno):
    app, s = entorno
    client = TestClient(app)
    assert client.get("/").status_code == 200
    r = client.get("/clinica", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/"


def test_paginas_portal_clinica(entorno):
    app, s = entorno
    client = TestClient(app)
    _login_clinica(client, s)
    ids = lambda modelo: [x.id for x in s.scalars(select(modelo)).all()]
    paginas = ["/clinica", "/clinica/agenda", "/clinica/agenda/nuevo", "/clinica/atenciones", "/clinica/atenciones/nueva",
               "/clinica/clientes", "/clinica/clientes/nuevo", "/clinica/mascotas", "/clinica/mascotas/nueva",
               "/clinica/ordenes", "/clinica/envios", "/clinica/envios/nuevo", "/clinica/cirugias",
               "/clinica/cirugias?tab=recibidas", "/clinica/facturacion", "/clinica/reportes", "/clinica/catalogos"]
    paginas += [f"/clinica/reportes/r{i}" for i in range(1, 6)]
    paginas += [f"/clinica/catalogos?tab={t}" for t in ("clinicas", "profesionales", "laboratorios", "analisis",
                                                         "vacunas", "contenedores")]
    paginas += [f"/clinica/catalogos/{t}/nuevo" for t in ("clinicas", "profesionales", "analisis", "contenedores")]
    paginas += [f"/clinica/atenciones/{i}" for i in ids(AtencionClinica)]
    paginas += [f"/clinica/clientes/{i}" for i in ids(Titular)] + [f"/clinica/clientes/{ids(Titular)[0]}/editar"]
    paginas += [f"/clinica/mascotas/{i}?tab={t}" for i in ids(Mascota)[:4]
                for t in ("resumen", "atenciones", "vacunas", "laboratorio", "cirugias", "facturas")]
    paginas += [f"/clinica/mascotas/{ids(Mascota)[0]}/editar"]
    paginas += [f"/clinica/ordenes/{i}" for i in ids(OrdenDerivacion)]
    paginas += [f"/clinica/muestras/{i}" for i in ids(MuestraBiologica)]
    paginas += [f"/clinica/envios/{i}" for i in ids(RemitoBiologico)]
    paginas += [f"/clinica/cirugias/{i}" for i in ids(DerivacionCirugia)]
    paginas += [f"/clinica/facturacion/{i}" for i in ids(Factura)]
    from app.domain.enums import EstadoAtencion
    en_curso = s.scalars(select(AtencionClinica).where(AtencionClinica.estado == EstadoAtencion.EN_PROGRESO)).first()
    paginas += [f"/clinica/atenciones/nueva?mascota={ids(Mascota)[1]}&tipo=VACUNACION",
                f"/clinica/ordenes/nueva?atencion={en_curso.id}",
                f"/clinica/cirugias/nueva?atencion={en_curso.id}",
                f"/clinica/catalogos/contenedores/{s.scalars(select(RemitoBiologico)).first().contenedor_id}/editar"]
    for url in paginas:
        r = client.get(url)
        assert r.status_code == 200, url
    assert "VetRed · Clínica" in client.get("/clinica").text


def test_paginas_portal_laboratorio(entorno):
    app, s = entorno
    client = TestClient(app)
    _login_lab(client, s)
    paginas = ["/laboratorio", "/laboratorio/recepcion", "/laboratorio/muestras", "/laboratorio/trazabilidad",
               "/laboratorio/recepciones", "/laboratorio/reportes", "/laboratorio/reportes/r2", "/laboratorio/reportes/r3",
               "/laboratorio/trazabilidad?codigo=M-000001", "/laboratorio/trazabilidad?codigo=REM-000001",
               "/laboratorio/trazabilidad?codigo=NOEXISTE"]
    paginas += [f"/laboratorio/recepciones/{r.id}" for r in s.scalars(select(RecepcionRemito))]
    paginas += [f"/laboratorio/muestras/{m.id}" for m in s.scalars(select(MuestraBiologica))]
    paginas += [f"/laboratorio/muestras/{m.id}/resultados" for m in s.scalars(select(MuestraBiologica))]
    paginas += [f"/laboratorio/recepcion/{r.id}" for r in s.scalars(select(RemitoBiologico))]
    for url in paginas:
        assert client.get(url).status_code == 200, url
    assert "VetRed · Laboratorio" in client.get("/laboratorio").text
    # el laboratorio no ve los reportes de la clínica
    assert client.get("/laboratorio/reportes/r4").status_code == 400


def test_csv_de_reportes(entorno):
    app, s = entorno
    client = TestClient(app)
    _login_clinica(client, s)
    for i in range(1, 6):
        r = client.get(f"/clinica/reportes/r{i}?formato=csv")
        assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
        assert r.text.startswith("﻿R")


def test_error_de_negocio_se_muestra_en_aviso_rojo(entorno):
    app, s = entorno
    client = TestClient(app)
    _login_clinica(client, s)
    r = client.post("/clinica/mascotas", data={"titular_id": "", "nombre": "Sin dueño", "especie": "GATO",
                                               "sexo": "HEMBRA", "fecha_nacimiento": "2024-01-01"},
                    headers={"referer": "http://testserver/clinica/mascotas/nueva"})
    assert r.status_code == 200
    assert "sin titular responsable" in r.text and "alert-danger" in r.text
    assert "MascotaSinTitularError" not in r.text  # sin nombres técnicos en la UI
    assert 'value="Sin dueño"' in r.text  # el formulario conserva lo cargado

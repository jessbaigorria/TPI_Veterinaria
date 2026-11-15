"""Reportes R1–R5 con datos armados en el test: devuelven los números esperados."""
from datetime import timedelta
from decimal import Decimal

import pytest

from app import reportes
from app.domain import reloj
from app.domain.enums import FormaPago
from app.reportes import Filtro, a_csv
from app.services.atenciones import AtencionesService
from app.services.cirugias import CirugiasService
from app.services.facturacion import FacturacionService


@pytest.fixture
def escenario(sesion, base):
    """4 atenciones realizadas + 1 cancelada; 3 remitos (1 aceptado, 1 precinto roto, 1 temperatura);
    tiempos controlados con el reloj; facturas (1 pagada, 1 emitida, 1 anulada)."""
    at = AtencionesService(sesion)
    a1 = base.atencion()                                       # urgencia con orden de laboratorio
    a2 = base.atencion()                                       # urgencia con cirugía
    a3 = base.atencion()                                       # urgencia simple
    vac = at.registrar_sin_turno(base.perez.id, base.centro.id, "VACUNACION", mascota_id=base.rocco.id,
                                 inicio=base.proxima_hora()).atencion
    from datetime import datetime
    cancelada = at.reservar_turno(base.firulais.id, base.diaz.id, base.centro.id, datetime(2026, 3, 11, 10, 0),
                                  tipo="CONTROL")
    at.cancelar(cancelada.id, "No vino")
    CirugiasService(sesion).derivar(a2.id, base.sur.id, "Cesárea")

    from app.services.derivaciones import DerivacionesService
    orden = DerivacionesService(sesion).emitir_orden(a1.id, base.lab.id, [base.hemograma.id, base.renal.id,
                                                                          base.orina.id])
    sangre, orina = base.muestra(orden, "SANGRE"), base.muestra(orden, "ORINA")
    r_ok = base.remito_en_transito([sangre, orina])          # despacho en t0
    reloj.avanzar(hours=3)
    base.recibir(r_ok)                                        # tránsito 3 h
    reloj.avanzar(hours=2)
    base.analizar(sangre)                                     # procesamiento 2 h
    reloj.avanzar(hours=4)
    base.analizar(orina)                                      # procesamiento 6 h

    r_roto = base.remito_en_transito([base.muestra(base.orden([base.hemograma]))])
    reloj.avanzar(hours=5)
    base.recibir(r_roto, integro=False)                       # tránsito 5 h
    r_temp = base.remito_en_transito([base.muestra(base.orden([base.hemograma]))])
    reloj.avanzar(hours=1)
    base.recibir(r_temp, temp=14)                             # tránsito 1 h

    fs = FacturacionService(sesion)
    at.finalizar(a3.id, "Ok", importe=10000)
    f_pagada = fs.facturar_atencion(a3.id)
    fs.registrar_pago(f_pagada.id, FormaPago.EFECTIVO)
    fs.facturar_orden(orden.id)                               # 8000 + 9500 + 6000 = 23500 emitida
    at.finalizar(vac.id, "Vacunas", importe=5000)
    fs.anular(fs.facturar_atencion(vac.id).id)                # anulada: no suma
    return base


def _filtro(**kw):
    return Filtro(desde=reloj.hoy() - timedelta(days=30), hasta=reloj.hoy() + timedelta(days=1), **kw)


def test_r1_atenciones_y_derivaciones(sesion, escenario):
    r = reportes.generar("r1", sesion, _filtro())
    filas = r.tablas[0].filas
    assert len(filas) == 1
    clinica, mes, consulta, control, urgencia, vacunacion, cirugia, otro, total, con_orden, con_cirugia, pct = filas[0]
    assert clinica == "Clínica Centro" and mes == "03/2026"
    # 3 urgencias de escenario + 2 urgencias de base.orden() para los remitos rechazados
    assert (consulta, control, urgencia, vacunacion, cirugia, otro) == (0, 0, 5, 1, 0, 0)
    assert total == 6                      # la cancelada no cuenta
    assert (con_orden, con_cirugia) == (3, 1)
    assert pct == round(100 * 4 / 6, 1)
    assert r.graficos[0].apilado


def test_r1_filtra_por_clinica(sesion, escenario):
    assert reportes.generar("r1", sesion, _filtro(clinica_id=escenario.norte.id)).tablas[0].filas == []


def test_r2_rechazos_por_transporte(sesion, escenario):
    r = reportes.generar("r2", sesion, _filtro(laboratorio_id=escenario.lab.id))
    por_clinica, por_motivo, por_transportista = r.tablas
    assert por_clinica.filas == [["Clínica Centro", 4, 2, 50.0]]
    assert por_motivo.filas == [["Precinto roto", 1, 1, 50.0], ["Temperatura fuera de rango", 1, 1, 50.0]]
    assert por_transportista.filas == [["Logística Fría", 4, 2, 50.0]]


def test_r3_tiempos(sesion, escenario):
    r = reportes.generar("r3", sesion, _filtro())
    transito, proceso = r.tablas
    assert transito.filas == [["Clínica Centro", 3, 3.0, 1.0, 5.0]]
    proc = {f[0]: f for f in proceso.filas}
    assert proc["Hemograma completo"][1:5] == [1, 2.0, 2.0, 2.0]
    assert proc["Perfil renal"][1:5] == [1, 2.0, 2.0, 2.0]
    assert proc["Urianálisis"][1:5] == [1, 6.0, 6.0, 6.0]


def test_r4_facturacion(sesion, escenario):
    r = reportes.generar("r4", sesion, _filtro())
    por_clinica, ranking = r.tablas
    fila = por_clinica.filas[0]
    assert fila[0] == "Clínica Centro"
    assert fila[1:8] == [Decimal("10000.00"), Decimal("23500.00"), Decimal("0.00"), Decimal("33500.00"),
                         Decimal("10000.00"), Decimal("23500.00"), 2]
    assert [f[1] for f in ranking.filas] == ["REN", "HEM", "URI"]
    assert ranking.filas[0][4] == Decimal("9500.00")


def test_r5_vacunas_pendientes(sesion, escenario):
    # La atención de VACUNACION del escenario se finalizó sin registrar vacunas: siguen pendientes.
    r = reportes.generar("r5", sesion, Filtro(hasta=reloj.hoy()))
    filas = r.tablas[0].filas
    assert {(f[0], f[6], f[7]) for f in filas} == {("Rocco", "Antirrábica", "Vencida"),
                                                   ("Rocco", "Séxtuple", "Nunca aplicada")}
    antirrabica = next(f for f in filas if f[6] == "Antirrábica")
    from tests.fabricas import AHORA
    assert antirrabica[8] == AHORA.date() - timedelta(days=500) + timedelta(days=365)
    assert antirrabica[9] == (reloj.hoy() - antirrabica[8]).days
    assert antirrabica[10] == "Clínica Centro"
    assert reportes.generar("r5", sesion, Filtro(hasta=reloj.hoy(), especie="GATO")).tablas[0].filas == []


def test_csv(sesion, escenario):
    texto = a_csv(reportes.generar("r4", sesion, _filtro()))
    assert texto.startswith("﻿R4")
    assert "Clínica Centro;10000,00;23500,00" in texto


def test_reportes_vacios_no_fallan(sesion):
    for codigo in reportes.REPORTES:
        rep = reportes.generar(codigo, sesion, _filtro())
        assert rep.vacio
        for g in rep.graficos:
            g.config()

"""Etapa 6 del seed: comprobantes (pagados, pendientes de cobro y uno anulado y reemplazado)."""
from __future__ import annotations

from datetime import timedelta

from app.domain import reloj
from app.domain.enums import FormaPago, TipoAtencion
from app.seed.sembrador import Sembrador


def sembrar_facturacion(sem: Sembrador) -> None:
    """Factura ~75 % de las atenciones finalizadas y todas las órdenes completadas con resultados."""
    for clinica in sem.clinica.values():
        pendientes = sem.fac.pendientes(clinica.id)
        _facturar_atenciones(sem, pendientes.atenciones)
        _facturar_ordenes(sem, pendientes.ordenes)
    _factura_anulada_y_reemplazada(sem)


def _facturar_atenciones(sem: Sembrador, atenciones) -> None:
    """Las de los últimos dos días quedan sin facturar; el 80 % de lo facturado se cobra."""
    for a in sorted(atenciones, key=lambda x: x.fecha_hora_inicio):
        if a.fecha_hora_inicio.date() >= sem.hoy - timedelta(days=1) or sem.rnd.random() > 0.75:
            continue
        reloj.fijar(a.fecha_hora_fin + timedelta(minutes=10))
        factura = sem.fac.facturar_atencion(a.id)
        if sem.rnd.random() < 0.8:
            sem.fac.registrar_pago(factura.id, sem.rnd.choice(list(FormaPago)))


def _facturar_ordenes(sem: Sembrador, ordenes) -> None:
    for orden in ordenes:
        ultimo_resultado = max(r.fecha_hora for r in orden.resultados())
        reloj.fijar(ultimo_resultado + timedelta(hours=2))
        factura = sem.fac.facturar_orden(orden.id)
        if sem.rnd.random() < 0.6:
            sem.fac.registrar_pago(factura.id, FormaPago.TRANSFERENCIA)


def _factura_anulada_y_reemplazada(sem: Sembrador) -> None:
    atencion = sem.atender(-12, 13, sem.clinica["centro"], sem.mascota["Firulais"], TipoAtencion.CONTROL,
                           prof=sem.prof["acosta"])
    reloj.fijar(atencion.fecha_hora_fin + timedelta(minutes=5))
    anulada = sem.fac.facturar_atencion(atencion.id)
    sem.fac.anular(anulada.id)
    reemplazo = sem.fac.facturar_atencion(atencion.id)
    sem.fac.registrar_pago(reemplazo.id, FormaPago.EFECTIVO)

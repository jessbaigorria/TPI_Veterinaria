"""Datos de prueba: se crean A TRAVÉS DE LOS SERVICIOS (no con INSERTs) fijando el reloj
inyectable para fechar 60 días de historia. Así el historial de estados queda consistente.

Uso:
    python -m app.seed            # crea la base si está vacía
    python -m app.seed --reset    # borra todo y vuelve a sembrar

Organización: ``datos.py`` tiene los datos fijos, ``sembrador.py`` las operaciones de alto nivel
(atender, emitir una orden, armar y despachar un remito…) y hay un módulo por etapa, que se
ejecutan en el orden de ``ETAPAS``.
"""
from __future__ import annotations

import argparse
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import db
from app.domain import reloj
from app.domain.atencion import AtencionClinica
from app.domain.clinica import Clinica
from app.domain.personas import Titular
from app.seed.agenda import sembrar_agenda_de_hoy
from app.seed.atenciones import sembrar_atenciones_de_rutina
from app.seed.catalogos import sembrar_catalogos
from app.seed.cirugias import sembrar_cirugias
from app.seed.clientes import sembrar_clientes
from app.seed.facturacion import sembrar_facturacion
from app.seed.laboratorio import sembrar_laboratorio
from app.seed.sembrador import Sembrador

ETAPAS = (
    sembrar_catalogos,
    sembrar_clientes,
    sembrar_atenciones_de_rutina,
    sembrar_laboratorio,
    sembrar_cirugias,
    sembrar_facturacion,
    sembrar_agenda_de_hoy,
)


def sembrar(s: Session, hoy: date | None = None) -> Sembrador:
    sem = Sembrador(s, hoy or date.today())
    try:
        for etapa in ETAPAS:
            etapa(sem)
    finally:
        reloj.liberar()
    return sem


def base_vacia(s: Session) -> bool:
    return (s.scalar(select(func.count(Clinica.id))) or 0) == 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Carga los datos de prueba de VetRed.")
    parser.add_argument("--reset", action="store_true", help="borra la base y vuelve a sembrar")
    args = parser.parse_args(argv)
    engine = db.crear_engine()
    if args.reset:
        db.reset_db(engine)
    else:
        db.init_db(engine)
    s = db.crear_fabrica_sesiones(engine)()
    try:
        if not base_vacia(s):
            print("La base ya tiene datos: no se siembra (usá --reset para regenerarla).")
            return
        sem = sembrar(s)
        titulares = s.scalar(select(func.count(Titular.id)))
        atenciones = s.scalar(select(func.count(AtencionClinica.id)))
        print(f"Seed cargado: {titulares} titulares, {len(sem.mascota)} mascotas, {atenciones} atenciones.")
    finally:
        s.close()

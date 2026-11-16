"""Modelo de dominio rico (entidades SQLAlchemy + State + Observer en Python puro).

Importar este paquete registra todos los mapeos ORM.
"""
from app.domain.atencion import AtencionClinica  # noqa: F401
from app.domain.base import Base  # noqa: F401
from app.domain.cirugia import DerivacionCirugia  # noqa: F401
from app.domain.clinica import Clinica, Profesional  # noqa: F401
from app.domain.facturacion import Factura, ItemFactura  # noqa: F401
from app.domain.personas import AplicacionVacuna, HistoriaClinica, Mascota, Titular, Vacuna  # noqa: F401
from app.domain.laboratorio import (  # noqa: F401
    HistorialEstadoMuestra, HistorialEstadoMuestraFila, Laboratorio, MuestraBiologica, OrdenDerivacion,
    ResultadoAnalisis, TipoAnalisis,
)
from app.domain.transporte import Contenedor, Envio, Precinto, RecepcionRemito, RemitoBiologico  # noqa: F401

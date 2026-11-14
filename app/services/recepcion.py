"""Proceso 6: recepción en el laboratorio verificando el precinto (y la temperatura)."""
from __future__ import annotations

from sqlalchemy import select

from app.domain.laboratorio import Laboratorio
from app.domain.transporte import RecepcionRemito, RemitoBiologico
from app.services.base import ServicioBase, a_bool, a_float, texto, transaccional


class RecepcionService(ServicioBase):
    @transaccional
    def recibir(self, remito_id, laboratorio_id, precinto_integro, temperatura, usuario,
                codigo_precinto_leido: str = "", observaciones: str = "") -> RecepcionRemito:
        remito = self.obtener(RemitoBiologico, remito_id)
        lab = self.obtener(Laboratorio, laboratorio_id)
        integro = a_bool(precinto_integro)
        obs = texto(observaciones)
        leido = texto(codigo_precinto_leido).upper()
        if leido and remito.precinto is not None and leido != remito.precinto.codigo.upper():
            # Un precinto con otro número es un precinto violado/reemplazado: se trata como roto.
            integro = False
            obs = f"Código leído {leido} no coincide con el esperado {remito.precinto.codigo}. {obs}".strip()
        return lab.recibir_remito(remito, integro, a_float(temperatura, "temperatura"), usuario, obs)

    def listar_recepciones(self, laboratorio_id, resultado: str = "") -> list[RecepcionRemito]:
        stmt = (select(RecepcionRemito).join(RecepcionRemito.remito)
                .where(RemitoBiologico.laboratorio_id == int(laboratorio_id)))
        if resultado:
            stmt = stmt.where(RecepcionRemito.resultado == resultado)
        return list(self.s.scalars(stmt.order_by(RecepcionRemito.fecha_hora.desc())))

"""Proceso 5: registrar la cadena de envío desde la clínica hacia el laboratorio central."""
from __future__ import annotations

from app.domain.excepciones import VeterinariaError
from app.domain.transporte import Envio, RemitoBiologico
from app.services.base import ServicioBase, a_fecha_hora, texto, transaccional


class EnviosService(ServicioBase):
    @transaccional
    def despachar(self, remito_id, transportista, llegada_estimada, usuario, vehiculo="",
                  observaciones="") -> RemitoBiologico:
        remito = self.obtener(RemitoBiologico, remito_id)
        llegada = a_fecha_hora(llegada_estimada)
        if llegada is None:
            raise VeterinariaError("Hay que indicar la llegada estimada.")
        envio = Envio(texto(transportista), llegada, texto(vehiculo), texto(observaciones))
        remito.despachar(envio, usuario)
        return remito

    @transaccional
    def confirmar_retiro(self, remito_id) -> RemitoBiologico:
        """El transportista retiró la conservadora: el remito pasa a En tránsito."""
        remito = self.obtener(RemitoBiologico, remito_id)
        remito.iniciar_transito()
        return remito

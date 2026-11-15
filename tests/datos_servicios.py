"""Datos base creados a través de los servicios (para tests de fase 2 en adelante)."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from app.domain import reloj
from app.domain.enums import TipoAtencion
from app.services.atenciones import AtencionesService
from app.services.catalogos import CatalogosService
from app.services.clientes import ClientesService
from app.services.derivaciones import DerivacionesService
from app.services.empaquetado import EmpaquetadoService
from app.services.envios import EnviosService
from app.services.mascotas import MascotasService
from app.services.recepcion import RecepcionService
from app.services.resultados import ResultadosService


class Base:
    def __init__(self, s):
        self.s = s
        cat = CatalogosService(s)
        self.centro = cat.guardar("clinicas", {"nombre": "Clínica Centro", "activa": "1"})
        self.norte = cat.guardar("clinicas", {"nombre": "Clínica Norte", "activa": "1"})
        self.sur = cat.guardar("clinicas", {"nombre": "Hospital Veterinario Sur", "activa": "1",
                                            "alta_complejidad": "1"})
        prof = lambda leg, nom, ape, cli, esp="Clínica general": cat.guardar("profesionales", {
            "legajo": leg, "matricula": "MP" + leg, "dni": leg, "nombre": nom, "apellido": ape,
            "especialidad": esp, "clinica_id": cli.id})
        self.perez = prof("100", "Laura", "Pérez", self.centro)
        self.diaz = prof("101", "Martín", "Díaz", self.centro)
        self.norte_vet = prof("200", "Carla", "Sosa", self.norte)
        self.cirujano = prof("300", "Diego", "Ríos", self.sur, "Cirugía")
        self.lab = cat.guardar("laboratorios", {"nombre": "Laboratorio Central", "activo": "1"})
        an = lambda cod, nom, precio, tipo: cat.guardar("analisis", {
            "codigo": cod, "nombre": nom, "precio": precio, "tipo_muestra_requerida": tipo,
            "temperatura_min": 2, "temperatura_max": 8, "tiempo_estimado_horas": 24})
        self.hemograma = an("HEM", "Hemograma completo", "8000", "SANGRE")
        self.renal = an("REN", "Perfil renal", "9500", "SANGRE")
        self.orina = an("URI", "Urianálisis", "6000", "ORINA")
        vac = lambda nom, esp, obl, edad: cat.guardar("vacunas", {
            "nombre": nom, "especie": esp, "obligatoria": "1" if obl else "", "edad_minima_semanas": edad,
            "intervalo_refuerzo_dias": 365})
        self.antirrabica = vac("Antirrábica", "PERRO", True, 12)
        self.sextuple = vac("Séxtuple", "PERRO", True, 8)
        self.lepto = vac("Leptospirosis", "PERRO", False, 12)
        self.antirrabica_gato = vac("Antirrábica felina", "GATO", True, 12)
        self.contenedor = cat.guardar("contenedores", {"codigo": "C-1", "capacidad": 6, "temperatura_min": 2,
                                                       "temperatura_max": 8, "clinica_id": self.centro.id})
        self.contenedor2 = cat.guardar("contenedores", {"codigo": "C-2", "capacidad": 6, "temperatura_min": 2,
                                                        "temperatura_max": 8, "clinica_id": self.centro.id})
        self.titular = ClientesService(s).crear_titular("30111222", "Juan", "García", "Colón 100", "3511000000", "juan@mail.com")
        ms = MascotasService(s)
        self.firulais = ms.crear_mascota(self.titular.id, "Firulais", "PERRO", "MACHO", date(2022, 1, 1))
        # Firulais con vacunas al día
        for v in (self.antirrabica, self.sextuple):
            ms.registrar_vacuna_aplicada(self.firulais.id, v.id, reloj.hoy() - timedelta(days=30), "L1")
        # Rocco con vacunas vencidas
        self.rocco = ms.crear_mascota(self.titular.id, "Rocco", "PERRO", "MACHO", date(2020, 5, 1))
        ms.registrar_vacuna_aplicada(self.rocco.id, self.antirrabica.id, reloj.hoy() - timedelta(days=500), "L0")
        self._hora = 0

    def proxima_hora(self) -> datetime:
        self._hora += 1
        return reloj.ahora().replace(hour=8) - timedelta(days=2) + timedelta(hours=self._hora)

    def atencion(self, mascota=None, tipo=TipoAtencion.URGENCIA, profesional=None):
        r = AtencionesService(self.s).registrar_sin_turno(
            (profesional or self.perez).id, self.centro.id, tipo, mascota_id=(mascota or self.firulais).id,
            inicio=self.proxima_hora())
        return r.atencion

    def orden(self, analisis=None):
        a = self.atencion()
        return DerivacionesService(self.s).emitir_orden(a.id, self.lab.id,
                                                        [t.id for t in (analisis or [self.hemograma, self.renal])])

    def muestra(self, orden=None, tipo="SANGRE"):
        orden = orden or self.orden()
        return DerivacionesService(self.s).registrar_muestra(orden.id, tipo, 3, "dra.perez")

    def remito_en_transito(self, muestras, contenedor=None, temperatura=4):
        emp = EmpaquetadoService(self.s)
        r = emp.crear_remito(self.centro.id, self.lab.id, (contenedor or self.contenedor).id, "recepcion")
        emp.agregar_muestras(r.id, [m.id for m in muestras], "recepcion")
        emp.cerrar_remito(r.id, "", temperatura, "recepcion")
        env = EnviosService(self.s)
        env.despachar(r.id, "Logística Fría", reloj.ahora() + timedelta(hours=3), "recepcion", "Furgón")
        env.confirmar_retiro(r.id)
        return r

    def recibir(self, remito, integro=True, temp=5):
        return RecepcionService(self.s).recibir(remito.id, self.lab.id, integro, temp, "Lucas Gomez")

    def analizar(self, muestra):
        return ResultadosService(self.s).cargar_resultados(
            muestra.id, [{"tipo_analisis_id": t.id, "valores": "OK"} for t in muestra.analisis_pendientes()],
            "Lucas Gomez")

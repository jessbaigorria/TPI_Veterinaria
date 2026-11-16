"""Fábricas de objetos de dominio para los tests (sin pasar por servicios)."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from app.domain import reloj
from app.domain.atencion import AtencionClinica
from app.domain.clinica import Clinica, Profesional
from app.domain.enums import Especie, Prioridad, Sexo, TipoAtencion, TipoMuestra
from app.domain.laboratorio import Laboratorio, TipoAnalisis
from app.domain.personas import Mascota, Titular, Vacuna
from app.domain.transporte import Contenedor, Envio, Precinto, RemitoBiologico

AHORA = datetime(2026, 3, 10, 9, 0)


class Mundo:
    """Grafo mínimo de dominio: clínica, profesional, titular, mascota, laboratorio, análisis."""

    def __init__(self, sesion=None):
        self.sesion = sesion
        self.clinica = Clinica(nombre="Clínica Centro", localidad="Centro", activa=True, alta_complejidad=False)
        self.hospital = Clinica(nombre="Hospital Veterinario Sur", localidad="Sur", activa=True, alta_complejidad=True)
        self.vet = Profesional(legajo="P1", matricula="MP1", dni="1", nombre="Ana", apellido="Pérez")
        self.clinica.agregar_profesional(self.vet)
        self.vet2 = Profesional(legajo="P2", matricula="MP2", dni="2", nombre="Luis", apellido="Gómez")
        self.clinica.agregar_profesional(self.vet2)
        self.cirujano = Profesional(legajo="P3", matricula="MP3", dni="3", nombre="Sara", apellido="Ruiz",
                                    especialidad="Cirugía")
        self.hospital.agregar_profesional(self.cirujano)
        self.titular = Titular(dni="30111222", nombre="Juan", apellido="García", direccion="Colón 100",
                               telefono="3511000000", email="juan@mail.com", fecha_alta=date(2025, 1, 1))
        self.mascota = Mascota(self.titular, "Pompón", Especie.PERRO, Sexo.MACHO, date(2022, 1, 1), peso=10)
        self.lab = Laboratorio(nombre="Laboratorio Central", activo=True)
        self.hemograma = TipoAnalisis(codigo="HEM", nombre="Hemograma", precio=Decimal("8000"),
                                      tipo_muestra_requerida=TipoMuestra.SANGRE, temperatura_min=2,
                                      temperatura_max=8, tiempo_estimado_horas=24)
        self.renal = TipoAnalisis(codigo="REN", nombre="Perfil renal", precio=Decimal("9500"),
                                  tipo_muestra_requerida=TipoMuestra.SANGRE, temperatura_min=2,
                                  temperatura_max=8, tiempo_estimado_horas=24)
        self.orina = TipoAnalisis(codigo="URI", nombre="Urianálisis", precio=Decimal("6000"),
                                  tipo_muestra_requerida=TipoMuestra.ORINA, temperatura_min=2,
                                  temperatura_max=8, tiempo_estimado_horas=24)
        self.contenedor = Contenedor("CONT-1", 6, 2, 8, self.clinica)
        self.vacunas = [
            Vacuna(nombre="Antirrábica", especie=Especie.PERRO, obligatoria=True, edad_minima_semanas=12,
                   intervalo_refuerzo_dias=365),
            Vacuna(nombre="Séxtuple", especie=Especie.PERRO, obligatoria=True, edad_minima_semanas=8,
                   intervalo_refuerzo_dias=365),
        ]
        self._n = 0
        if sesion is not None:
            sesion.add_all([self.clinica, self.hospital, self.titular, self.lab, self.hemograma, self.renal,
                            self.orina, self.contenedor, *self.vacunas])
            sesion.flush()

    def _num(self, prefijo):
        self._n += 1
        return f"{prefijo}-{self._n:06d}"

    def atencion(self, inicio=None, tipo=TipoAtencion.URGENCIA, profesional=None, mascota=None, minutos=30):
        if inicio is None:
            self._turno = getattr(self, "_turno", -1) + 1
            inicio = reloj.ahora() - timedelta(days=1) + timedelta(hours=self._turno)
        a = AtencionClinica(mascota or self.mascota, self.clinica, profesional or self.vet, inicio,
                            inicio + timedelta(minutes=minutos), tipo)
        return a

    def atencion_en_progreso(self):
        a = self.atencion()
        a.iniciar()
        return a

    def orden(self, analisis=None, prioridad=Prioridad.NORMAL):
        a = self.atencion_en_progreso()
        return a.emitir_orden_derivacion(self.lab, analisis or [self.hemograma, self.renal], prioridad,
                                         numero=self._num("ORD"))

    def muestra(self, orden=None, tipo=TipoMuestra.SANGRE, usuario="dra.perez"):
        orden = orden or self.orden()
        return orden.registrar_muestra(tipo, 3.0, usuario, codigo=self._num("M"))

    def remito(self, contenedor=None):
        return RemitoBiologico(self.clinica, self.lab, contenedor or self.contenedor, "recepcion",
                               numero=self._num("REM"))

    def remito_cerrado(self, muestras, temperatura=4.0):
        r = self.remito()
        for m in muestras:
            r.agregar_muestra(m)
        r.cerrar(Precinto(self._num("PRE"), "recepcion"), temperatura)
        return r

    def remito_en_transito(self, muestras, temperatura=4.0):
        r = self.remito_cerrado(muestras, temperatura)
        r.despachar(self.envio())
        r.iniciar_transito()
        return r

    @staticmethod
    def envio(horas=3):
        return Envio("Logística Fría SRL", reloj.ahora() + timedelta(hours=horas), "Furgón AB123CD")

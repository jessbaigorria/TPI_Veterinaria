"""Sembrador: servicios, reloj y operaciones de alto nivel que usan todas las etapas del seed.

Todo se hace a través de los servicios (como lo haría un usuario), moviendo el reloj inyectable
para fechar cada evento en el pasado.

Los datos salen de un ``random.Random`` con semilla fija: el seed es reproducible y la demo del
README (por ejemplo REM-000003 con precinto roto) siempre muestra lo mismo. Por eso el orden de
las llamadas al azar no debe cambiar.
"""
from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.domain import reloj
from app.domain.enums import Prioridad, TipoAtencion
from app.seed.datos import (
    DIAGNOSTICOS_FIJOS, DIAGNOSTICOS_SORTEABLES, ESQUEMA_OBLIGATORIO, IMPORTES, MOTIVOS_FIJOS, MOTIVOS_SORTEABLES,
    OPERADORES_LAB, RESULTADOS, TRANSPORTISTAS,
)
from app.services.atenciones import AtencionesService
from app.services.catalogos import CatalogosService
from app.services.cirugias import CirugiasService
from app.services.clientes import ClientesService
from app.services.derivaciones import DerivacionesService
from app.services.empaquetado import EmpaquetadoService
from app.services.envios import EnviosService
from app.services.facturacion import FacturacionService
from app.services.mascotas import MascotasService
from app.services.recepcion import RecepcionService
from app.services.resultados import ResultadosService


class Sembrador:
    def __init__(self, s: Session, hoy: date):
        self.s = s
        self.hoy = hoy
        self.rnd = random.Random(30)
        self.ocupados: set[tuple[int, datetime]] = set()
        # servicios
        self.cat = CatalogosService(s)
        self.cli = ClientesService(s)
        self.mas = MascotasService(s)
        self.ate = AtencionesService(s)
        self.der = DerivacionesService(s)
        self.emp = EmpaquetadoService(s)
        self.env = EnviosService(s)
        self.rec = RecepcionService(s)
        self.res = ResultadosService(s)
        self.fac = FacturacionService(s)
        self.cir = CirugiasService(s)
        # lo que van creando las etapas, por clave
        self.clinica: dict = {}
        self.lab = None
        self.prof: dict = {}
        self.de_rutina: dict[int, list] = {}     # clinica_id → profesionales de las atenciones de rutina
        self.vacuna: dict = {}
        self.analisis: dict = {}
        self.contenedor: dict = {}
        self.titular: dict = {}
        self.mascota: dict = {}

    # --- reloj --------------------------------------------------------------------------
    def en(self, dia: int, hora: int, minuto: int = 0) -> datetime:
        """Fija el reloj en «hoy + dia» a la hora indicada."""
        momento = datetime.combine(self.hoy + timedelta(days=dia), time(hora, minuto))
        reloj.fijar(momento)
        return momento

    @staticmethod
    def mas_tarde(**delta) -> datetime:
        return reloj.avanzar(**delta)

    # --- atenciones ----------------------------------------------------------------------
    def atender(self, dia, hora, clinica, mascota, tipo=TipoAtencion.CONSULTA, prof=None, minuto=0,
                diagnostico="", motivo="", finalizar=True, asiste_titular=True, responsable=""):
        """Registra una atención sin turno (y, si ``finalizar``, la cierra con diagnóstico e importe)."""
        prof = prof or self.rnd.choice(self.de_rutina[clinica.id])
        inicio = self.horario_libre(prof, datetime.combine(self.hoy + timedelta(days=dia), time(hora, minuto)))
        reloj.fijar(inicio)
        r = self.ate.registrar_sin_turno(prof.id, clinica.id, tipo, mascota_id=mascota.id, inicio=inicio,
                                         motivo=motivo or self._motivo(tipo), asiste_titular=asiste_titular,
                                         responsable_presente=responsable)
        if finalizar:
            reloj.fijar(inicio + timedelta(minutes=25))
            vacunas = self._vacunas_a_aplicar(mascota, inicio.date()) if tipo is TipoAtencion.VACUNACION else []
            self.ate.finalizar(r.atencion.id, diagnostico or self._diagnostico(tipo),
                               peso=round(mascota.peso * self.rnd.uniform(0.97, 1.03), 1),
                               importe=IMPORTES[tipo] + self.rnd.choice([0, 500, 1500, 2500]),
                               vacunas_aplicadas=vacunas)
        return r.atencion

    def cerrar(self, atencion, diagnostico):
        """Finaliza (con importe) una atención que quedó en curso para emitir órdenes o derivaciones."""
        reloj.fijar(max(reloj.ahora(), atencion.fecha_hora_inicio + timedelta(minutes=25)))
        self.ate.finalizar(atencion.id, diagnostico, importe=IMPORTES[atencion.tipo] + 1500)

    def esquema_de(self, mascota) -> list:
        """Vacunas obligatorias de la especie de la mascota."""
        claves = ESQUEMA_OBLIGATORIO["PERRO" if mascota.especie.value == "PERRO" else "GATO"]
        return [self.vacuna[c] for c in claves]

    def horario_libre(self, prof, inicio: datetime) -> datetime:
        """Primer horario libre del profesional desde ``inicio`` (de a 30 minutos)."""
        while (prof.id, inicio) in self.ocupados:
            inicio += timedelta(minutes=30)
        self.ocupados.add((prof.id, inicio))
        return inicio

    def _vacunas_a_aplicar(self, mascota, fecha: date) -> list[dict]:
        pendientes = mascota.historia_clinica.vacunas_pendientes(fecha) or self.esquema_de(mascota)[:1]
        return [{"vacuna_id": v.id, "lote": f"L{self.rnd.randint(1000, 9999)}", "dosis_numero": 2}
                for v in pendientes]

    def _motivo(self, tipo: TipoAtencion) -> str:
        return self._sortear(MOTIVOS_SORTEABLES, MOTIVOS_FIJOS, tipo)

    def _diagnostico(self, tipo: TipoAtencion) -> str:
        return self._sortear(DIAGNOSTICOS_SORTEABLES, DIAGNOSTICOS_FIJOS, tipo)

    def _sortear(self, sorteables: dict, fijos: dict, tipo: TipoAtencion) -> str:
        # Se sortea una opción de CADA lista aunque se use una sola: así lo hacía la primera versión
        # del seed y se conserva la misma secuencia aleatoria (los datos de la demo no cambian).
        sorteados = {t: self.rnd.choice(opciones) for t, opciones in sorteables.items()}
        return sorteados[tipo] if tipo in sorteados else fijos[tipo]

    # --- laboratorio: orden → muestra → remito → envío → recepción → resultados ----------------
    def orden(self, atencion, codigos, prioridad=Prioridad.NORMAL, obs="Descartar patología sistémica"):
        return self.der.emitir_orden(atencion.id, self.lab.id, [self.analisis[c].id for c in codigos], prioridad, obs)

    def muestra(self, orden, tipo, usuario, volumen=3.0):
        return self.der.registrar_muestra(orden.id, tipo, volumen, usuario)

    def orden_con_muestra(self, dia, hora, clinica, mascota, prof, codigos, tipo_muestra, diagnostico,
                          obs="Descartar patología sistémica"):
        """Atención en curso → orden de laboratorio → muestra extraída → atención finalizada."""
        atencion = self.atender(dia, hora, clinica, mascota, prof=prof, finalizar=False)
        orden = self.orden(atencion, codigos, obs=obs)
        muestra = self.muestra(orden, tipo_muestra, prof.nombre_completo())
        self.ate.finalizar(atencion.id, diagnostico, importe=IMPORTES[atencion.tipo])
        return muestra

    def remito(self, clinica, contenedor, muestras, usuario, temp=4.5):
        """Arma el remito, empaqueta las muestras y lo cierra con precinto y temperatura de despacho."""
        r = self.emp.crear_remito(clinica.id, self.lab.id, contenedor.id, usuario)
        self.mas_tarde(minutes=20)
        self.emp.agregar_muestras(r.id, [m.id for m in muestras], usuario)
        self.mas_tarde(minutes=10)
        self.emp.cerrar_remito(r.id, "", temp, usuario)
        return r

    def despachar(self, remito, usuario, horas_estimadas=4, transportista=None):
        nombre, vehiculo = transportista or self.rnd.choice(TRANSPORTISTAS)
        self.env.despachar(remito.id, nombre, reloj.ahora() + timedelta(hours=horas_estimadas), usuario, vehiculo)

    def recibir(self, remito, integro=True, temp=5.0, operador=None):
        return self.rec.recibir(remito.id, self.lab.id, integro, temp, operador or OPERADORES_LAB[0],
                                codigo_precinto_leido=remito.precinto.codigo if integro else "")

    def analizar(self, muestra, operador=None):
        datos = []
        for t in muestra.analisis_pendientes():
            valores, unidad, ref, interp = RESULTADOS[t.codigo]
            datos.append({"tipo_analisis_id": t.id, "valores": valores, "unidad": unidad,
                          "valores_referencia": ref, "interpretacion": interp})
        self.res.cargar_resultados(muestra.id, datos, operador or self.rnd.choice(OPERADORES_LAB))

    def ciclo_completo(self, dia, clinica, contenedor, mascota, codigos_por_tipo, prof,
                       transito_h=3.0, proceso_h=(5, 9), integro=True, temp=5.0, analizar=True,
                       prioridad=Prioridad.NORMAL, tipo_atencion=TipoAtencion.CONSULTA, temp_despacho=4.5):
        """Recorrido completo de una derivación: atención → orden → muestras → remito → despacho →
        retiro → recepción (aceptada o rechazada) → resultados."""
        usuario_clinica = prof.nombre_completo()
        recepcionista = "Recepción " + clinica.nombre.split()[-1]
        atencion = self.atender(dia, 15, clinica, mascota, tipo_atencion, prof=prof, finalizar=False)
        orden = self.orden(atencion, [c for cs in codigos_por_tipo.values() for c in cs], prioridad)
        self.mas_tarde(minutes=10)
        muestras = [self.muestra(orden, tipo, usuario_clinica) for tipo in codigos_por_tipo]
        self.mas_tarde(minutes=15)
        self.ate.finalizar(atencion.id, "Se solicitan estudios de laboratorio", importe=IMPORTES[tipo_atencion])
        self.mas_tarde(hours=1)
        r = self.remito(clinica, contenedor, muestras, recepcionista, temp_despacho)
        self.mas_tarde(minutes=30)
        self.despachar(r, recepcionista)
        self.mas_tarde(minutes=40)
        self.env.confirmar_retiro(r.id)
        self.mas_tarde(minutes=int(transito_h * 60) - 40)
        rec = self.recibir(r, integro, temp)
        if analizar and rec.es_aceptada():
            for m in muestras:
                self.mas_tarde(minutes=self.rnd.randint(proceso_h[0] * 60, proceso_h[1] * 60))
                self.analizar(m)
        return atencion, orden, r

    # --- cirugías -----------------------------------------------------------------------------
    def derivar_cirugia(self, dia, clinica, mascota, prof, diagnostico, cirugia, prioridad, presuntivo, riesgo,
                        estudios="", tipo=TipoAtencion.CONSULTA):
        """Atención en curso → derivación al Hospital Veterinario Sur → atención finalizada."""
        atencion = self.atender(dia, 17, clinica, mascota, tipo, prof=prof, finalizar=False)
        derivacion = self.cir.derivar(atencion.id, self.clinica["sur"].id, cirugia, prioridad, presuntivo, riesgo,
                                      estudios)
        self.cerrar(atencion, diagnostico)  # la derivación se emite con la atención en curso
        return derivacion

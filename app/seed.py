"""Datos de prueba: se crean A TRAVÉS DE LOS SERVICIOS (no con INSERTs) fijando el reloj
inyectable para fechar 60 días de historia. Así el historial de estados queda consistente.

Uso:
    python -m app.seed            # crea la base si está vacía
    python -m app.seed --reset    # borra todo y vuelve a sembrar
"""
from __future__ import annotations

import argparse
import random
from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import db
from app.domain import reloj
from app.domain.atencion import AtencionClinica, Clinica, Profesional
from app.domain.enums import FormaPago, Prioridad, RiesgoAnestesico, TipoAtencion
from app.domain.personas import Titular
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

LAB_NOMBRE = "Laboratorio Central de Diagnóstico Veterinario"
OPERADORES_LAB = ["Andrea Gómez", "Lucía Ibarra"]
TRANSPORTISTAS = [("Logística Fría SRL", "Furgón refrigerado AE 123 KD"),
                  ("BioExpress Córdoba", "Utilitario AF 456 GT")]

IMPORTES = {TipoAtencion.CONSULTA: 15000, TipoAtencion.CONTROL: 12000, TipoAtencion.URGENCIA: 25000,
            TipoAtencion.VACUNACION: 9000}

RESULTADOS = {
    "HEM": ("Hto 42 %; GR 6,8 M/µL; GB 11.200/µL; Plaq 310.000/µL", "", "Hto 37–55 %; GB 6.000–17.000/µL",
            "Sin alteraciones significativas."),
    "REN": ("Urea 38 mg/dL; Creatinina 1,1 mg/dL", "mg/dL", "Urea 20–50; Creat 0,5–1,5", "Función renal conservada."),
    "HEP": ("ALT 62 U/L; FA 140 U/L; Bilirrubina 0,3 mg/dL", "U/L", "ALT 10–100; FA 20–150", "Dentro de rango."),
    "URI": ("Densidad 1.030; pH 6,5; proteínas negativo; sedimento sin particularidades", "", "Densidad 1.015–1.045",
            "Urianálisis normal."),
    "COP": ("Se observan huevos de Toxocara spp.", "", "Negativo", "Parasitosis intestinal: desparasitar."),
    "CIT": ("Células inflamatorias mixtas, sin atipias", "", "—", "Proceso inflamatorio benigno."),
    "HIS": ("Lipoma subcutáneo, márgenes libres", "", "—", "Lesión benigna."),
}


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

    # --- reloj --------------------------------------------------------------------------
    def en(self, dia: int, hora: int, minuto: int = 0) -> datetime:
        momento = datetime.combine(self.hoy + timedelta(days=dia), time(hora, minuto))
        reloj.fijar(momento)
        return momento

    @staticmethod
    def mas_tarde(**delta) -> datetime:
        return reloj.avanzar(**delta)

    # --- catálogos ---------------------------------------------------------------------
    def catalogos(self):
        self.en(-75, 8)
        c = self.cat
        self.centro = c.guardar("clinicas", {"nombre": "Clínica Centro", "direccion": "Av. Colón 1250",
                                             "localidad": "Córdoba Centro", "telefono": "351-422-1100",
                                             "email": "centro@vetred.com.ar", "activa": "1"})
        self.norte = c.guardar("clinicas", {"nombre": "Clínica Norte", "direccion": "Av. Rafael Núñez 4800",
                                            "localidad": "Cerro de las Rosas", "telefono": "351-481-2200",
                                            "email": "norte@vetred.com.ar", "activa": "1"})
        self.sur = c.guardar("clinicas", {"nombre": "Hospital Veterinario Sur", "direccion": "Av. Vélez Sarsfield 3300",
                                          "localidad": "Barrio Jardín", "telefono": "351-466-3300",
                                          "email": "hospital@vetred.com.ar", "activa": "1", "alta_complejidad": "1"})
        self.lab = c.guardar("laboratorios", {"nombre": LAB_NOMBRE, "direccion": "Bv. San Juan 900",
                                              "telefono": "351-425-9000", "email": "recepcion@labcentral.com.ar",
                                              "responsable": "Bioq. Andrea Gómez", "activo": "1"})

        def prof(legajo, nombre, apellido, clinica, especialidad):
            return c.guardar("profesionales", {
                "legajo": legajo, "matricula": f"MP-{legajo}", "dni": f"2{legajo}0{legajo}",
                "nombre": nombre, "apellido": apellido, "especialidad": especialidad,
                "telefono": f"351-55{legajo}", "email": f"{apellido.lower()}@vetred.com.ar", "clinica_id": clinica.id})

        self.perez = prof("1001", "Laura", "Pérez", self.centro, "Clínica general")
        self.diaz = prof("1002", "Martín", "Díaz", self.centro, "Dermatología")
        self.acosta = prof("1003", "Julieta", "Acosta", self.centro, "Clínica general")
        self.sosa = prof("2001", "Carla", "Sosa", self.norte, "Clínica general")
        self.medina = prof("2002", "Pablo", "Medina", self.norte, "Felinos")
        self.rios = prof("3001", "Diego", "Ríos", self.sur, "Cirugía")
        self.luna_vet = prof("3002", "Valeria", "Luna", self.sur, "Anestesiología")
        self.ferreyra = prof("3003", "Tomás", "Ferreyra", self.sur, "Traumatología y cirugía")
        self.vets = {self.centro.id: [self.perez, self.diaz, self.acosta], self.norte.id: [self.sosa, self.medina],
                     self.sur.id: [self.luna_vet, self.ferreyra]}

        def vac(nombre, especie, obligatoria, semanas, dias=365):
            return c.guardar("vacunas", {"nombre": nombre, "especie": especie, "obligatoria": "1" if obligatoria else "",
                                         "edad_minima_semanas": semanas, "intervalo_refuerzo_dias": dias})

        self.v_antirrabica = vac("Antirrábica", "PERRO", True, 12)
        self.v_sextuple = vac("Séxtuple (polivalente)", "PERRO", True, 8)
        self.v_lepto = vac("Leptospirosis", "PERRO", False, 12)
        self.v_antirrabica_gato = vac("Antirrábica felina", "GATO", True, 12)
        self.v_triple = vac("Triple felina", "GATO", True, 8)

        def an(codigo, nombre, precio, tipo, tmin, tmax, horas, desc):
            return c.guardar("analisis", {"codigo": codigo, "nombre": nombre, "descripcion": desc, "precio": precio,
                                          "tipo_muestra_requerida": tipo, "temperatura_min": tmin,
                                          "temperatura_max": tmax, "tiempo_estimado_horas": horas})

        self.a = {
            "HEM": an("HEM", "Hemograma completo", "8500", "SANGRE", 2, 8, 6, "Recuento y fórmula leucocitaria"),
            "REN": an("REN", "Perfil renal", "9800", "SANGRE", 2, 8, 12, "Urea, creatinina, fósforo"),
            "HEP": an("HEP", "Perfil hepático", "10500", "SANGRE", 2, 8, 12, "ALT, AST, FA, bilirrubina"),
            "URI": an("URI", "Urianálisis", "6200", "ORINA", 2, 8, 8, "Físico-químico y sedimento"),
            "COP": an("COP", "Coproparasitológico", "5400", "HECES", 2, 8, 24, "Seriado de materia fecal"),
            "CIT": an("CIT", "Citología", "11000", "HISOPADO", 2, 8, 24, "Citología exfoliativa/hisopado"),
            "HIS": an("HIS", "Histopatología", "18500", "TEJIDO", 15, 25, 72, "Biopsia fijada en formol"),
        }

        def cont(codigo, clinica, capacidad, tmin=2, tmax=8):
            return c.guardar("contenedores", {"codigo": codigo, "capacidad": capacidad, "temperatura_min": tmin,
                                              "temperatura_max": tmax, "clinica_id": clinica.id})

        self.cen1 = cont("CEN-01", self.centro, 8)
        self.cen2 = cont("CEN-02", self.centro, 6)
        self.cen3 = cont("CEN-03", self.centro, 10)
        self.nor1 = cont("NOR-01", self.norte, 6)
        self.nor2 = cont("NOR-02", self.norte, 6)
        self.sur1 = cont("SUR-01", self.sur, 8)
        self.sur2 = cont("SUR-02", self.sur, 6, 15, 25)   # temperatura ambiente (histopatología en formol)
        self.cat.cambiar_estado_contenedor(self.nor2.id, "mantenimiento")

    # --- clientes y mascotas ----------------------------------------------------------------
    def clientes(self):
        self.en(-70, 9)
        datos = [
            ("28456123", "Juan", "García", "Bv. Chacabuco 450", "351-155-1001", "juan.garcia@mail.com"),
            ("31222987", "María", "López", "Obispo Trejo 1020", "351-155-1002", "maria.lopez@mail.com"),
            ("25987456", "Carlos", "Fernández", "Av. Sabattini 2300", "351-155-1003", "cfernandez@mail.com"),
            ("33654789", "Ana", "Martínez", "Rondeau 870", "351-155-1004", "ana.martinez@mail.com"),
            ("29874123", "Lucía", "Romero", "Av. Recta Martinoli 6100", "351-155-1005", "lucia.romero@mail.com"),
            ("35123654", "Diego", "Suárez", "Lima 340", "351-155-1006", "dsuarez@mail.com"),
            ("27456321", "Sofía", "Torres", "Av. Fuerza Aérea 2900", "351-155-1007", "sofia.torres@mail.com"),
            ("30789654", "Martín", "Herrera", "Av. Colón 3800", "351-155-1008", "mherrera@mail.com"),
            ("32147852", "Valentina", "Castro", "Bv. San Juan 1500", "351-155-1009", "vcastro@mail.com"),
            ("26369258", "Jorge", "Molina", "Av. Vélez Sarsfield 5100", "351-155-1010", "jmolina@mail.com"),
            ("34852963", "Paula", "Navarro", "Caseros 2200", "351-155-1011", "pnavarro@mail.com"),
        ]
        self.t = {d[2]: self.cli.crear_titular(*d) for d in datos}

        hoy = self.hoy

        def m(titular, nombre, especie, sexo, anios, raza, peso, alergias=""):
            nac = hoy - timedelta(days=int(anios * 365))
            return self.mas.crear_mascota(self.t[titular].id, nombre, especie, sexo, nac, raza, peso, alergias=alergias)

        self.m = {
            "Firulais": m("García", "Firulais", "PERRO", "MACHO", 4, "Mestizo", 18.5),
            "Rocco": m("García", "Rocco", "PERRO", "MACHO", 6, "Bóxer", 29.0),
            "Michi": m("López", "Michi", "GATO", "HEMBRA", 3, "Común europeo", 4.1),
            "Thor": m("Fernández", "Thor", "PERRO", "MACHO", 5, "Labrador", 32.0, "Penicilina"),
            "Luna": m("Martínez", "Luna", "PERRO", "HEMBRA", 8, "Caniche", 7.2),
            "Simba": m("Romero", "Simba", "GATO", "MACHO", 2, "Siamés", 4.8),
            "Bruno": m("Suárez", "Bruno", "PERRO", "MACHO", 9, "Golden Retriever", 34.0),
            "Nina": m("Torres", "Nina", "PERRO", "HEMBRA", 3, "Beagle", 12.3),
            "Coco": m("Herrera", "Coco", "PERRO", "MACHO", 7, "Cocker", 14.0),
            "Max": m("Castro", "Max", "PERRO", "MACHO", 5, "Pastor alemán", 36.0),
            "Kira": m("Molina", "Kira", "PERRO", "HEMBRA", 4, "Border collie", 19.0),
            "Lola": m("Navarro", "Lola", "PERRO", "HEMBRA", 2, "Bulldog francés", 11.0),
            "Tom": m("López", "Tom", "GATO", "MACHO", 6, "Persa", 5.0),
            "Mía": m("Fernández", "Mía", "GATO", "HEMBRA", 1, "Común europeo", 3.2),
            "Pompón": m("Romero", "Pompón", "PERRO", "MACHO", 3, "Caniche toy", 4.0),
            "Rocky": m("Navarro", "Rocky", "PERRO", "MACHO", 10, "Rottweiler", 41.0),
            "Toby": m("Herrera", "Toby", "PERRO", "MACHO", 0.4, "Mestizo", 6.0),  # cachorro sin vacunar
        }
        # Vacunas: la mayoría al día (aplicadas hace 70–250 días); algunas vencidas o faltantes.
        pendientes = {"Rocco", "Mía", "Toby"}
        for nombre, mascota in self.m.items():
            if nombre in pendientes:
                continue
            for v in self._vacunas_de(mascota):
                dias = self.rnd.randint(80, 260)
                self.mas.registrar_vacuna_aplicada(mascota.id, v.id, hoy - timedelta(days=dias),
                                                   f"L{self.rnd.randint(1000, 9999)}", 2)
        # Rocco: antirrábica y séxtuple vencidas (aplicadas hace más de un año).
        self.mas.registrar_vacuna_aplicada(self.m["Rocco"].id, self.v_antirrabica.id, hoy - timedelta(days=420), "L0420", 3)
        self.mas.registrar_vacuna_aplicada(self.m["Rocco"].id, self.v_sextuple.id, hoy - timedelta(days=400), "L0400", 3)
        # Mía: solo antirrábica; le falta la triple felina.
        self.mas.registrar_vacuna_aplicada(self.m["Mía"].id, self.v_antirrabica_gato.id, hoy - timedelta(days=100), "L0100", 1)
        self.mas.actualizar_historia(self.m["Thor"].id, "Penicilina", "Displasia de cadera leve", "Paciente dócil.")
        self.mas.actualizar_historia(self.m["Bruno"].id, "", "Hipotiroidismo en tratamiento", "")

    def _vacunas_de(self, mascota):
        if mascota.especie.value == "PERRO":
            return [self.v_antirrabica, self.v_sextuple]
        return [self.v_antirrabica_gato, self.v_triple]

    # --- helpers de atención -----------------------------------------------------------------
    def _libre(self, prof: Profesional, inicio: datetime) -> datetime:
        while (prof.id, inicio) in self.ocupados:
            inicio += timedelta(minutes=30)
        self.ocupados.add((prof.id, inicio))
        return inicio

    def atender(self, dia, hora, clinica, mascota, tipo=TipoAtencion.CONSULTA, prof=None, minuto=0,
                diagnostico="", motivo="", finalizar=True, asiste_titular=True, responsable=""):
        prof = prof or self.rnd.choice(self.vets[clinica.id])
        inicio = self._libre(prof, datetime.combine(self.hoy + timedelta(days=dia), time(hora, minuto)))
        reloj.fijar(inicio)
        r = self.ate.registrar_sin_turno(prof.id, clinica.id, tipo, mascota_id=mascota.id, inicio=inicio,
                                         motivo=motivo or self._motivo(tipo), asiste_titular=asiste_titular,
                                         responsable_presente=responsable)
        if finalizar:
            reloj.fijar(inicio + timedelta(minutes=25))
            vacunas = []
            if tipo is TipoAtencion.VACUNACION:
                vacunas = [{"vacuna_id": v.id, "lote": f"L{self.rnd.randint(1000, 9999)}", "dosis_numero": 2}
                           for v in mascota.historia_clinica.vacunas_pendientes(inicio.date()) or self._vacunas_de(mascota)[:1]]
            self.ate.finalizar(r.atencion.id, diagnostico or self._diagnostico(tipo),
                               peso=round(mascota.peso * self.rnd.uniform(0.97, 1.03), 1),
                               importe=IMPORTES[tipo] + self.rnd.choice([0, 500, 1500, 2500]),
                               vacunas_aplicadas=vacunas)
        return r.atencion

    def _motivo(self, tipo):
        return {TipoAtencion.CONSULTA: self.rnd.choice(["Decaimiento y poco apetito", "Picazón en orejas",
                                                        "Vómitos desde ayer", "Cojera de miembro posterior"]),
                TipoAtencion.CONTROL: self.rnd.choice(["Control anual", "Control post tratamiento", "Control de peso"]),
                TipoAtencion.URGENCIA: self.rnd.choice(["Traumatismo", "Intoxicación sospechada", "Dificultad respiratoria"]),
                TipoAtencion.VACUNACION: "Plan de vacunación"}[tipo]

    def _diagnostico(self, tipo):
        return {TipoAtencion.CONSULTA: self.rnd.choice(["Otitis externa", "Gastroenteritis aguda", "Dermatitis alérgica",
                                                        "Esguince leve"]),
                TipoAtencion.CONTROL: "Paciente en buen estado general",
                TipoAtencion.URGENCIA: self.rnd.choice(["Contusión sin fracturas", "Cuadro gastrointestinal agudo",
                                                        "Crisis respiratoria compensada"]),
                TipoAtencion.VACUNACION: "Se aplican vacunas del esquema"}[tipo]

    # --- flujo de laboratorio --------------------------------------------------------------
    def orden(self, atencion, codigos, prioridad=Prioridad.NORMAL, obs="Descartar patología sistémica"):
        return self.der.emitir_orden(atencion.id, self.lab.id, [self.a[c].id for c in codigos], prioridad, obs)

    def muestra(self, orden, tipo, usuario, volumen=3.0):
        return self.der.registrar_muestra(orden.id, tipo, volumen, usuario)

    def remito(self, clinica, contenedor, muestras, usuario, temp=4.5):
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

    def ciclo_completo(self, dia, clinica, contenedor, mascota, codigos_por_tipo, prof, usuario_clinica,
                       transito_h=3.0, proceso_h=(5, 9), integro=True, temp=5.0, analizar=True,
                       prioridad=Prioridad.NORMAL, tipo_atencion=TipoAtencion.CONSULTA, temp_despacho=4.5):
        atencion = self.atender(dia, 15, clinica, mascota, tipo_atencion, prof=prof, finalizar=False)
        orden = self.orden(atencion, [c for cs in codigos_por_tipo.values() for c in cs], prioridad)
        self.mas_tarde(minutes=10)
        muestras = [self.muestra(orden, tipo, usuario_clinica) for tipo in codigos_por_tipo]
        self.mas_tarde(minutes=15)
        self.ate.finalizar(atencion.id, "Se solicitan estudios de laboratorio", importe=IMPORTES[tipo_atencion])
        self.mas_tarde(hours=1)
        r = self.remito(clinica, contenedor, muestras, "Recepción " + clinica.nombre.split()[-1], temp_despacho)
        self.mas_tarde(minutes=30)
        self.despachar(r, "Recepción " + clinica.nombre.split()[-1])
        self.mas_tarde(minutes=40)
        self.env.confirmar_retiro(r.id)
        self.mas_tarde(minutes=int(transito_h * 60) - 40)
        rec = self.recibir(r, integro, temp)
        if analizar and rec.es_aceptada():
            for m in muestras:
                self.mas_tarde(minutes=self.rnd.randint(proceso_h[0] * 60, proceso_h[1] * 60))
                self.analizar(m)
        return atencion, orden, r

    # --- historia -------------------------------------------------------------------------
    def historia(self):
        m = self.m
        # 1) Atenciones de rutina en las 3 clínicas (~40 en 60 días).
        clinicas = [self.centro, self.norte, self.sur]
        al_dia = [x for k, x in m.items() if k not in {"Rocco", "Mía", "Toby"}]
        tipos = [TipoAtencion.CONSULTA] * 4 + [TipoAtencion.CONTROL] * 3 + [TipoAtencion.URGENCIA] * 2 + [
            TipoAtencion.VACUNACION]
        self.atenciones_rutina = []
        for dia in range(-60, 0):
            if (self.hoy + timedelta(days=dia)).weekday() == 6:
                continue
            for clinica in clinicas:
                if self.rnd.random() < 0.24:
                    tipo = self.rnd.choice(tipos)
                    mascota = self.rnd.choice(al_dia)
                    a = self.atender(dia, self.rnd.choice([9, 10, 11, 12]), clinica, mascota, tipo,
                                     asiste_titular=self.rnd.random() > 0.15, responsable="Familiar del titular")
                    self.atenciones_rutina.append(a)
        # Rocco y Mía: solo urgencias (quedan con vacunas pendientes y advertencia en observaciones).
        self.atender(-50, 18, self.centro, m["Rocco"], TipoAtencion.URGENCIA, prof=self.perez,
                     diagnostico="Herida cortante en almohadilla")
        self.atender(-22, 18, self.norte, m["Mía"], TipoAtencion.URGENCIA, prof=self.medina,
                     diagnostico="Vómitos por ingesta de cuerpo extraño", asiste_titular=False,
                     responsable="Vecina autorizada por la titular")
        # Un turno cancelado.
        reloj.fijar(datetime.combine(self.hoy + timedelta(days=-30), time(8, 0)))
        t = self.ate.reservar_turno(m["Nina"].id, self.diaz.id, self.centro.id,
                                    datetime.combine(self.hoy + timedelta(days=-29), time(16, 30)), tipo="CONTROL")
        self.ate.cancelar(t.id, "La titular avisó que no puede asistir")

        # 2) Laboratorio: remitos en todos los estados.
        V = OPERADORES_LAB
        self.ciclo_completo(-55, self.centro, self.cen1, m["Firulais"], {"SANGRE": ["HEM", "REN"]}, self.perez,
                            "Laura Pérez", transito_h=2.5)
        self.ciclo_completo(-48, self.norte, self.nor1, m["Michi"], {"ORINA": ["URI"], "SANGRE": ["HEM"]},
                            self.medina, "Pablo Medina", transito_h=4.0)
        # Remito con PRECINTO ROTO: dos órdenes (Luna y Thor) en el mismo remito → todas rechazadas.
        a1 = self.atender(-40, 15, self.centro, m["Luna"], prof=self.diaz, finalizar=False)
        o1 = self.orden(a1, ["COP"])
        mu1 = self.muestra(o1, "HECES", "Martín Díaz")
        self.ate.finalizar(a1.id, "Diarrea crónica; se pide coproparasitológico", importe=15000)
        a2 = self.atender(-40, 16, self.centro, m["Thor"], prof=self.perez, finalizar=False)
        o2 = self.orden(a2, ["HEP"])
        mu2 = self.muestra(o2, "SANGRE", "Laura Pérez")
        self.ate.finalizar(a2.id, "Control prequirúrgico", importe=15000)
        self.mas_tarde(hours=1)
        r = self.remito(self.centro, self.cen2, [mu1, mu2], "Recepción Centro")
        self.despachar(r, "Recepción Centro", transportista=TRANSPORTISTAS[1])
        self.mas_tarde(minutes=30)
        self.env.confirmar_retiro(r.id)
        self.mas_tarde(hours=3, minutes=10)
        self.recibir(r, integro=False, temp=6.0, operador=V[1])
        # Remito con TEMPERATURA FUERA DE RANGO.
        self.ciclo_completo(-33, self.norte, self.nor1, m["Simba"], {"SANGRE": ["HEM"]}, self.sosa, "Carla Sosa",
                            transito_h=6.5, temp=12.5)
        self.ciclo_completo(-25, self.sur, self.sur2, m["Bruno"], {"TEJIDO": ["HIS"]}, self.ferreyra,
                            "Tomás Ferreyra", transito_h=2.0, temp=19.0, proceso_h=(40, 60), temp_despacho=20.0)
        self.ciclo_completo(-18, self.centro, self.cen3, m["Nina"], {"SANGRE": ["HEM", "REN"], "ORINA": ["URI"]},
                            self.acosta, "Julieta Acosta", transito_h=3.0)
        self.ciclo_completo(-10, self.norte, self.nor1, m["Coco"], {"SANGRE": ["HEP"]}, self.sosa, "Carla Sosa",
                            transito_h=5.0)
        # Recibidos pendientes de análisis (cola del laboratorio).
        self.ciclo_completo(-5, self.centro, self.cen1, m["Max"], {"SANGRE": ["HEM", "REN"]}, self.perez,
                            "Laura Pérez", transito_h=3.5, analizar=False, prioridad=Prioridad.URGENTE,
                            tipo_atencion=TipoAtencion.URGENCIA)
        self.ciclo_completo(-3, self.norte, self.nor1, m["Kira"], {"HISOPADO": ["CIT"]}, self.medina,
                            "Pablo Medina", transito_h=4.5, analizar=False)
        # En tránsito hacia el laboratorio (para recibir en la demo).
        a = self.atender(-2, 15, self.centro, m["Lola"], prof=self.acosta, finalizar=False)
        o = self.orden(a, ["URI"])
        mu = self.muestra(o, "ORINA", "Julieta Acosta")
        self.ate.finalizar(a.id, "Sospecha de infección urinaria", importe=15000)
        self.mas_tarde(hours=1)
        r = self.remito(self.centro, self.cen1, [mu], "Recepción Centro")
        self.despachar(r, "Recepción Centro", horas_estimadas=30)
        self.mas_tarde(minutes=45)
        self.env.confirmar_retiro(r.id)
        # Despachado, esperando retiro del transportista.
        a = self.atender(-1, 15, self.norte, m["Tom"], prof=self.medina, finalizar=False)
        o = self.orden(a, ["HEM", "REN"])
        mu = self.muestra(o, "SANGRE", "Pablo Medina")
        self.ate.finalizar(a.id, "Gato geronte: chequeo renal", importe=15000)
        self.mas_tarde(hours=1)
        r = self.remito(self.norte, self.nor1, [mu], "Recepción Norte")
        self.despachar(r, "Recepción Norte", horas_estimadas=26)
        # Armado (con una muestra empaquetada, sin cerrar).
        a = self.atender(-1, 16, self.sur, m["Rocky"], prof=self.luna_vet, finalizar=False)
        o = self.orden(a, ["REN"], obs="Prequirúrgico: evaluar función renal")
        mu = self.muestra(o, "SANGRE", "Valeria Luna")
        self.ate.finalizar(a.id, "Evaluación prequirúrgica", importe=15000)
        r = self.emp.crear_remito(self.sur.id, self.lab.id, self.sur1.id, "Recepción Sur")
        self.emp.agregar_muestras(r.id, [mu.id], "Recepción Sur")
        # Orden de hoy con muestra Extraída sin empaquetar.
        a = self.atender(0, 8, self.centro, m["Pompón"], prof=self.diaz, finalizar=False)
        o = self.orden(a, ["HEM", "HEP"], obs="Prurito generalizado; descartar hepatopatía")
        self.muestra(o, "SANGRE", "Martín Díaz")
        self.ate.finalizar(a.id, "Dermatitis; se pide laboratorio", importe=15000)

    def cirugias(self):
        m = self.m
        c = self.cir
        # Realizada y facturada (pagada).
        a = self.atender(-45, 17, self.centro, m["Thor"], TipoAtencion.URGENCIA, prof=self.perez,
                         diagnostico="Fractura de fémur derecho")
        d = c.derivar(a.id, self.sur.id, "Osteosíntesis de fémur", Prioridad.URGENTE, "Fractura diafisaria de fémur",
                      RiesgoAnestesico.ASA_II, "Rx y hemograma prequirúrgico normales")
        self.mas_tarde(hours=2)
        c.aceptar(d.id, self.ferreyra.id)
        c.registrar_consentimiento(d.id, "Recepción Sur")
        c.programar(d.id, reloj.ahora() + timedelta(days=1))
        self.en(-44, 14)
        c.registrar_cirugia(d.id, "Se coloca placa y tornillos. Sin complicaciones. Alta a las 24 h.")
        f = self.fac.facturar_cirugia(d.id, 185000)
        self.mas_tarde(days=2)
        self.fac.registrar_pago(f.id, FormaPago.TARJETA)
        # Realizada, facturada y pendiente de cobro (ASA III con estudios).
        a = self.atender(-30, 17, self.norte, m["Simba"], prof=self.sosa, diagnostico="Obstrucción uretral recurrente")
        d = c.derivar(a.id, self.sur.id, "Uretrostomía perineal", Prioridad.NORMAL, "Obstrucción uretral",
                      RiesgoAnestesico.ASA_III)
        self.mas_tarde(hours=3)
        c.aceptar(d.id, self.rios.id)
        c.registrar_consentimiento(d.id, "Recepción Norte")
        c.registrar_estudios(d.id, "Ecografía abdominal, ionograma y perfil renal")
        c.programar(d.id, reloj.ahora() + timedelta(days=2))
        self.en(-28, 10)
        c.registrar_cirugia(d.id, "Uretrostomía sin complicaciones. Sonda 48 h.")
        self.fac.facturar_cirugia(d.id, 210000)
        # Rechazada.
        a = self.atender(-20, 17, self.centro, m["Luna"], prof=self.diaz, diagnostico="Tumor mamario")
        d = c.derivar(a.id, self.sur.id, "Mastectomía radical", Prioridad.NORMAL, "Neoplasia mamaria",
                      RiesgoAnestesico.ASA_IV)
        self.mas_tarde(hours=5)
        c.rechazar(d.id, "Paciente con riesgo ASA IV: primero estabilizar y reevaluar con cardiología")
        # Cancelada.
        a = self.atender(-14, 17, self.norte, m["Kira"], prof=self.sosa, diagnostico="Luxación de rótula")
        d = c.derivar(a.id, self.sur.id, "Trocleoplastia", Prioridad.NORMAL, "Luxación patelar grado III",
                      RiesgoAnestesico.ASA_I)
        self.mas_tarde(hours=2)
        c.aceptar(d.id, self.ferreyra.id)
        c.cancelar(d.id, "El titular decidió posponer la cirugía")
        # Programada a futuro.
        a = self.atender(-8, 17, self.norte, m["Coco"], prof=self.sosa, diagnostico="Cuerpo extraño gástrico")
        d = c.derivar(a.id, self.sur.id, "Gastrotomía", Prioridad.URGENTE, "Cuerpo extraño", RiesgoAnestesico.ASA_II)
        self.mas_tarde(hours=1)
        c.aceptar(d.id, self.rios.id)
        c.registrar_consentimiento(d.id, "Recepción Norte")
        c.programar(d.id, datetime.combine(self.hoy + timedelta(days=3), time(9, 0)))
        # Aceptada sin consentimiento (para la demo de la validación).
        a = self.atender(-4, 17, self.centro, m["Bruno"], prof=self.acosta, diagnostico="Masa esplénica")
        d = c.derivar(a.id, self.sur.id, "Esplenectomía", Prioridad.URGENTE, "Masa esplénica", RiesgoAnestesico.ASA_III)
        self.mas_tarde(hours=2)
        c.aceptar(d.id, self.rios.id)
        # Solicitada (pendiente de respuesta del hospital).
        a = self.atender(-2, 17, self.centro, m["Max"], prof=self.perez, diagnostico="Rotura de ligamento cruzado")
        c.derivar(a.id, self.sur.id, "Cirugía de ligamento cruzado (TPLO)", Prioridad.NORMAL,
                  "Rotura de LCA", RiesgoAnestesico.ASA_II)

    def facturacion(self):
        """Factura ~75 % de las atenciones finalizadas y todas las órdenes completadas con resultados."""
        for clinica in (self.centro, self.norte, self.sur):
            pendientes = self.fac.pendientes(clinica.id)
            for a in sorted(pendientes.atenciones, key=lambda x: x.fecha_hora_inicio):
                if a.fecha_hora_inicio.date() >= self.hoy - timedelta(days=1) or self.rnd.random() > 0.75:
                    continue
                reloj.fijar(a.fecha_hora_fin + timedelta(minutes=10))
                f = self.fac.facturar_atencion(a.id)
                if self.rnd.random() < 0.8:
                    self.fac.registrar_pago(f.id, self.rnd.choice(list(FormaPago)))
            for o in pendientes.ordenes:
                ultimo = max(r.fecha_hora for r in o.resultados())
                reloj.fijar(ultimo + timedelta(hours=2))
                f = self.fac.facturar_orden(o.id)
                if self.rnd.random() < 0.6:
                    self.fac.registrar_pago(f.id, FormaPago.TRANSFERENCIA)
        # Una factura anulada (y reemplazada).
        a = self.atender(-12, 13, self.centro, self.m["Firulais"], TipoAtencion.CONTROL, prof=self.acosta)
        reloj.fijar(a.fecha_hora_fin + timedelta(minutes=5))
        f = self.fac.facturar_atencion(a.id)
        self.fac.anular(f.id)
        f2 = self.fac.facturar_atencion(a.id)
        self.fac.registrar_pago(f2.id, FormaPago.EFECTIVO)

    def agenda_de_hoy(self):
        """Turnos de hoy y mañana (la atención RESERVADA es el turno)."""
        m = self.m
        self.en(0, 7, 30)
        self.atender(0, 8, self.centro, m["Kira"], TipoAtencion.CONTROL, prof=self.perez, minuto=30)
        self.atender(0, 8, self.norte, m["Simba"], TipoAtencion.CONSULTA, prof=self.medina)
        reservas = [
            (0, 9, 0, self.centro, self.perez, m["Firulais"], "CONTROL", "Control anual"),
            (0, 10, 0, self.centro, self.perez, m["Nina"], "CONSULTA", "Picazón en orejas"),
            (0, 11, 30, self.centro, self.perez, m["Luna"], "CONTROL", "Control oncológico"),
            (0, 10, 0, self.centro, self.diaz, m["Thor"], "CONSULTA", "Lesión en piel"),
            (0, 12, 0, self.centro, self.diaz, m["Pompón"], "CONTROL", "Ver resultados"),
            (0, 16, 0, self.centro, self.acosta, m["Max"], "CONSULTA", "Dolor articular"),
            (0, 17, 0, self.centro, self.acosta, m["Mía"], "VACUNACION", "Triple felina"),
            (0, 11, 0, self.norte, self.sosa, m["Coco"], "CONTROL", "Control postquirúrgico"),
            (0, 15, 0, self.norte, self.medina, m["Tom"], "CONSULTA", "Control renal"),
            (1, 9, 30, self.centro, self.perez, m["Max"], "CONTROL", "Control"),
            (1, 10, 30, self.sur, self.ferreyra, m["Bruno"], "CONSULTA", "Evaluación prequirúrgica"),
        ]
        for dia, h, mi, clinica, prof, mascota, tipo, motivo in reservas:
            inicio = self._libre(prof, datetime.combine(self.hoy + timedelta(days=dia), time(h, mi)))
            self.ate.reservar_turno(mascota.id, prof.id, clinica.id, inicio, inicio + timedelta(minutes=30), tipo,
                                    motivo)
        # Una atención en curso (iniciada a las 9:00 por la Dra. Pérez).
        primero = next(a for a in self.ate.agenda(self.centro.id, self.hoy)
                       if a.profesional is self.perez and a.fecha_hora_inicio.hour == 9)
        self.en(0, 9, 0)
        self.ate.iniciar(primero.id)


def sembrar(s: Session, hoy: date | None = None) -> Sembrador:
    hoy = hoy or date.today()
    sem = Sembrador(s, hoy)
    try:
        sem.catalogos()
        sem.clientes()
        sem.historia()
        sem.cirugias()
        sem.facturacion()
        sem.agenda_de_hoy()
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
        resumen = {
            "titulares": s.scalar(select(func.count(Titular.id))),
            "atenciones": s.scalar(select(func.count(AtencionClinica.id))),
        }
        print(f"Seed cargado: {resumen['titulares']} titulares, {len(sem.m)} mascotas, "
              f"{resumen['atenciones']} atenciones.")
    finally:
        s.close()


if __name__ == "__main__":
    main()

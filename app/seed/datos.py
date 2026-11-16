"""Datos fijos del seed: catálogos, clientes, mascotas, textos sorteables y turnos de hoy."""
from __future__ import annotations

from app.domain.enums import TipoAtencion

# --- catálogos -----------------------------------------------------------------------------
CLINICAS = {  # clave → datos del formulario de Gestión
    "centro": {"nombre": "Clínica Centro", "direccion": "Av. Colón 1250", "localidad": "Córdoba Centro",
               "telefono": "351-422-1100", "email": "centro@vetred.com.ar", "activa": "1"},
    "norte": {"nombre": "Clínica Norte", "direccion": "Av. Rafael Núñez 4800", "localidad": "Cerro de las Rosas",
              "telefono": "351-481-2200", "email": "norte@vetred.com.ar", "activa": "1"},
    "sur": {"nombre": "Hospital Veterinario Sur", "direccion": "Av. Vélez Sarsfield 3300",
            "localidad": "Barrio Jardín", "telefono": "351-466-3300", "email": "hospital@vetred.com.ar",
            "activa": "1", "alta_complejidad": "1"},
}

LAB_NOMBRE = "Laboratorio Central de Diagnóstico Veterinario"
LABORATORIO = {"nombre": LAB_NOMBRE, "direccion": "Bv. San Juan 900", "telefono": "351-425-9000",
               "email": "recepcion@labcentral.com.ar", "responsable": "Bioq. Andrea Gómez", "activo": "1"}

PROFESIONALES = [  # (clave, legajo, nombre, apellido, clínica, especialidad)
    ("perez", "1001", "Laura", "Pérez", "centro", "Clínica general"),
    ("diaz", "1002", "Martín", "Díaz", "centro", "Dermatología"),
    ("acosta", "1003", "Julieta", "Acosta", "centro", "Clínica general"),
    ("sosa", "2001", "Carla", "Sosa", "norte", "Clínica general"),
    ("medina", "2002", "Pablo", "Medina", "norte", "Felinos"),
    ("rios", "3001", "Diego", "Ríos", "sur", "Cirugía"),
    ("luna", "3002", "Valeria", "Luna", "sur", "Anestesiología"),
    ("ferreyra", "3003", "Tomás", "Ferreyra", "sur", "Traumatología y cirugía"),
]

# Quiénes atienden las consultas de rutina en cada clínica (Ríos solo opera).
PROFESIONALES_DE_RUTINA = {"centro": ["perez", "diaz", "acosta"], "norte": ["sosa", "medina"],
                           "sur": ["luna", "ferreyra"]}

VACUNAS = [  # (clave, nombre, especie, obligatoria, edad mínima en semanas) — refuerzo anual
    ("antirrabica", "Antirrábica", "PERRO", True, 12),
    ("sextuple", "Séxtuple (polivalente)", "PERRO", True, 8),
    ("lepto", "Leptospirosis", "PERRO", False, 12),
    ("antirrabica_gato", "Antirrábica felina", "GATO", True, 12),
    ("triple", "Triple felina", "GATO", True, 8),
]
ESQUEMA_OBLIGATORIO = {"PERRO": ["antirrabica", "sextuple"], "GATO": ["antirrabica_gato", "triple"]}

ANALISIS = [  # (código, nombre, precio, muestra, temp. mín, temp. máx, horas estimadas, descripción)
    ("HEM", "Hemograma completo", "8500", "SANGRE", 2, 8, 6, "Recuento y fórmula leucocitaria"),
    ("REN", "Perfil renal", "9800", "SANGRE", 2, 8, 12, "Urea, creatinina, fósforo"),
    ("HEP", "Perfil hepático", "10500", "SANGRE", 2, 8, 12, "ALT, AST, FA, bilirrubina"),
    ("URI", "Urianálisis", "6200", "ORINA", 2, 8, 8, "Físico-químico y sedimento"),
    ("COP", "Coproparasitológico", "5400", "HECES", 2, 8, 24, "Seriado de materia fecal"),
    ("CIT", "Citología", "11000", "HISOPADO", 2, 8, 24, "Citología exfoliativa/hisopado"),
    ("HIS", "Histopatología", "18500", "TEJIDO", 15, 25, 72, "Biopsia fijada en formol"),
]

CONTENEDORES = [  # (código, clínica, capacidad, temp. mín, temp. máx)
    ("CEN-01", "centro", 8, 2, 8),
    ("CEN-02", "centro", 6, 2, 8),
    ("CEN-03", "centro", 10, 2, 8),
    ("NOR-01", "norte", 6, 2, 8),
    ("NOR-02", "norte", 6, 2, 8),
    ("SUR-01", "sur", 8, 2, 8),
    ("SUR-02", "sur", 6, 15, 25),   # temperatura ambiente (histopatología en formol)
]
CONTENEDOR_EN_MANTENIMIENTO = "NOR-02"

# --- clientes y mascotas ---------------------------------------------------------------------
TITULARES = [  # (dni, nombre, apellido, dirección, teléfono, email)
    ("28456123", "Juan", "García", "Bv. Chacabuco 450", "3511551001", "juan.garcia@mail.com"),
    ("31222987", "María", "López", "Obispo Trejo 1020", "3511551002", "maria.lopez@mail.com"),
    ("25987456", "Carlos", "Fernández", "Av. Sabattini 2300", "3511551003", "cfernandez@mail.com"),
    ("33654789", "Ana", "Martínez", "Rondeau 870", "3511551004", "ana.martinez@mail.com"),
    ("29874123", "Lucía", "Romero", "Av. Recta Martinoli 6100", "3511551005", "lucia.romero@mail.com"),
    ("35123654", "Diego", "Suárez", "Lima 340", "3511551006", "dsuarez@mail.com"),
    ("27456321", "Sofía", "Torres", "Av. Fuerza Aérea 2900", "3511551007", "sofia.torres@mail.com"),
    ("30789654", "Martín", "Herrera", "Av. Colón 3800", "3511551008", "mherrera@mail.com"),
    ("32147852", "Valentina", "Castro", "Bv. San Juan 1500", "3511551009", "vcastro@mail.com"),
    ("26369258", "Jorge", "Molina", "Av. Vélez Sarsfield 5100", "3511551010", "jmolina@mail.com"),
    ("34852963", "Paula", "Navarro", "Caseros 2200", "3511551011", "pnavarro@mail.com"),
]

MASCOTAS = [  # (apellido del titular, nombre, especie, sexo, edad en años, raza, peso, alergias)
    ("García", "Firulais", "PERRO", "MACHO", 4, "Mestizo", 18.5, ""),
    ("García", "Rocco", "PERRO", "MACHO", 6, "Bóxer", 29.0, ""),
    ("López", "Michi", "GATO", "HEMBRA", 3, "Común europeo", 4.1, ""),
    ("Fernández", "Thor", "PERRO", "MACHO", 5, "Labrador", 32.0, "Penicilina"),
    ("Martínez", "Luna", "PERRO", "HEMBRA", 8, "Caniche", 7.2, ""),
    ("Romero", "Simba", "GATO", "MACHO", 2, "Siamés", 4.8, ""),
    ("Suárez", "Bruno", "PERRO", "MACHO", 9, "Golden Retriever", 34.0, ""),
    ("Torres", "Nina", "PERRO", "HEMBRA", 3, "Beagle", 12.3, ""),
    ("Herrera", "Coco", "PERRO", "MACHO", 7, "Cocker", 14.0, ""),
    ("Castro", "Max", "PERRO", "MACHO", 5, "Pastor alemán", 36.0, ""),
    ("Molina", "Kira", "PERRO", "HEMBRA", 4, "Border collie", 19.0, ""),
    ("Navarro", "Lola", "PERRO", "HEMBRA", 2, "Bulldog francés", 11.0, ""),
    ("López", "Tom", "GATO", "MACHO", 6, "Persa", 5.0, ""),
    ("Fernández", "Mía", "GATO", "HEMBRA", 1, "Común europeo", 3.2, ""),
    ("Romero", "Pompón", "PERRO", "MACHO", 3, "Caniche toy", 4.0, ""),
    ("Navarro", "Rocky", "PERRO", "MACHO", 10, "Rottweiler", 41.0, ""),
    ("Herrera", "Toby", "PERRO", "MACHO", 0.4, "Mestizo", 6.0, ""),  # cachorro sin vacunar
]

# Mascotas para la demo de la validación de vacunas (no reciben el esquema al día).
CON_VACUNAS_PENDIENTES = {"Rocco", "Mía", "Toby"}
VACUNAS_ESPECIALES = [  # (mascota, vacuna, aplicada hace N días, lote, dosis)
    ("Rocco", "antirrabica", 420, "L0420", 3),        # vencida
    ("Rocco", "sextuple", 400, "L0400", 3),           # vencida
    ("Mía", "antirrabica_gato", 100, "L0100", 1),     # le falta la triple felina
]
HISTORIAS = {  # mascota → (alergias, antecedentes, observaciones generales)
    "Thor": ("Penicilina", "Displasia de cadera leve", "Paciente dócil."),
    "Bruno": ("", "Hipotiroidismo en tratamiento", ""),
}

# --- atenciones --------------------------------------------------------------------------------
IMPORTES = {TipoAtencion.CONSULTA: 15000, TipoAtencion.CONTROL: 12000, TipoAtencion.URGENCIA: 25000,
            TipoAtencion.VACUNACION: 9000}

# Textos que se sortean para las atenciones. Los que no tienen variantes son fijos.
MOTIVOS_SORTEABLES = {
    TipoAtencion.CONSULTA: ["Decaimiento y poco apetito", "Picazón en orejas", "Vómitos desde ayer",
                            "Cojera de miembro posterior"],
    TipoAtencion.CONTROL: ["Control anual", "Control post tratamiento", "Control de peso"],
    TipoAtencion.URGENCIA: ["Traumatismo", "Intoxicación sospechada", "Dificultad respiratoria"],
}
MOTIVOS_FIJOS = {TipoAtencion.VACUNACION: "Plan de vacunación"}
DIAGNOSTICOS_SORTEABLES = {
    TipoAtencion.CONSULTA: ["Otitis externa", "Gastroenteritis aguda", "Dermatitis alérgica", "Esguince leve"],
    TipoAtencion.URGENCIA: ["Contusión sin fracturas", "Cuadro gastrointestinal agudo",
                            "Crisis respiratoria compensada"],
}
DIAGNOSTICOS_FIJOS = {TipoAtencion.CONTROL: "Paciente en buen estado general",
                      TipoAtencion.VACUNACION: "Se aplican vacunas del esquema"}

TIPOS_DE_RUTINA = ([TipoAtencion.CONSULTA] * 4 + [TipoAtencion.CONTROL] * 3 + [TipoAtencion.URGENCIA] * 2
                   + [TipoAtencion.VACUNACION])

# --- laboratorio ---------------------------------------------------------------------------------
OPERADORES_LAB = ["Andrea Gómez", "Lucía Ibarra"]
TRANSPORTISTAS = [("Logística Fría SRL", "Furgón refrigerado AE 123 KD"),
                  ("BioExpress Córdoba", "Utilitario AF 456 GT")]

RESULTADOS = {  # código de análisis → (valores, unidad, valores de referencia, interpretación)
    "HEM": ("Hto 42 %; GR 6,8 M/µL; GB 11.200/µL; Plaq 310.000/µL", "", "Hto 37–55 %; GB 6.000–17.000/µL",
            "Sin alteraciones significativas."),
    "REN": ("Urea 38 mg/dL; Creatinina 1,1 mg/dL", "mg/dL", "Urea 20–50; Creat 0,5–1,5",
            "Función renal conservada."),
    "HEP": ("ALT 62 U/L; FA 140 U/L; Bilirrubina 0,3 mg/dL", "U/L", "ALT 10–100; FA 20–150", "Dentro de rango."),
    "URI": ("Densidad 1.030; pH 6,5; proteínas negativo; sedimento sin particularidades", "",
            "Densidad 1.015–1.045", "Urianálisis normal."),
    "COP": ("Se observan huevos de Toxocara spp.", "", "Negativo", "Parasitosis intestinal: desparasitar."),
    "CIT": ("Células inflamatorias mixtas, sin atipias", "", "—", "Proceso inflamatorio benigno."),
    "HIS": ("Lipoma subcutáneo, márgenes libres", "", "—", "Lesión benigna."),
}

# --- agenda de hoy y mañana ----------------------------------------------------------------------
TURNOS_RESERVADOS = [  # (día, hora, minuto, clínica, profesional, mascota, tipo, motivo)
    (0, 9, 0, "centro", "perez", "Firulais", "CONTROL", "Control anual"),
    (0, 10, 0, "centro", "perez", "Nina", "CONSULTA", "Picazón en orejas"),
    (0, 11, 30, "centro", "perez", "Luna", "CONTROL", "Control oncológico"),
    (0, 10, 0, "centro", "diaz", "Thor", "CONSULTA", "Lesión en piel"),
    (0, 12, 0, "centro", "diaz", "Pompón", "CONTROL", "Ver resultados"),
    (0, 16, 0, "centro", "acosta", "Max", "CONSULTA", "Dolor articular"),
    (0, 17, 0, "centro", "acosta", "Mía", "VACUNACION", "Triple felina"),
    (0, 11, 0, "norte", "sosa", "Coco", "CONTROL", "Control postquirúrgico"),
    (0, 15, 0, "norte", "medina", "Tom", "CONSULTA", "Control renal"),
    (1, 9, 30, "centro", "perez", "Max", "CONTROL", "Control"),
    (1, 10, 30, "sur", "ferreyra", "Bruno", "CONSULTA", "Evaluación prequirúrgica"),
]

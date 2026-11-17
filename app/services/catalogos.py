"""Catálogos: alta/edición simple de clínicas, profesionales, laboratorios, tipos de análisis,
vacunas (esquema obligatorio) y contenedores.

Cada catálogo se describe con sus campos (``CATALOGOS``); la pantalla de Gestión y la conversión
de los datos del formulario se arman a partir de esa descripción.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from app.domain import validaciones
from app.domain.base import a_decimal
from app.domain.clinica import Clinica, Profesional
from app.domain.enums import Especie, TipoMuestra
from app.domain.excepciones import DatosInvalidosError, VeterinariaError
from app.domain.laboratorio import Laboratorio, TipoAnalisis
from app.domain.personas import Vacuna
from app.domain.transporte import Contenedor
from app.services.base import ServicioBase, a_bool, a_float, texto, transaccional


@dataclass(frozen=True)
class Campo:
    nombre: str
    etiqueta: str
    tipo: str = "text"          # text | number | bool | select | decimal | tel | email
    opciones: tuple = ()
    requerido: bool = True
    entero: bool = False        # number: se guarda como int si el valor no tiene decimales


@dataclass(frozen=True)
class Catalogo:
    clave: str
    titulo: str
    modelo: type
    campos: tuple[Campo, ...]
    columnas: tuple[str, ...]


ESPECIES = tuple((e.value, e.etiqueta) for e in Especie)
TIPOS_MUESTRA = tuple((t.value, t.etiqueta) for t in TipoMuestra)

CATALOGOS: dict[str, Catalogo] = {
    "clinicas": Catalogo("clinicas", "Clínicas", Clinica, (
        Campo("nombre", "Nombre"), Campo("direccion", "Dirección", requerido=False),
        Campo("localidad", "Localidad", requerido=False), Campo("telefono", "Teléfono", "tel", requerido=False),
        Campo("email", "Email", "email", requerido=False), Campo("activa", "Activa", "bool"),
        Campo("alta_complejidad", "Alta complejidad", "bool")),
        ("nombre", "localidad", "telefono", "alta_complejidad", "activa")),
    "profesionales": Catalogo("profesionales", "Profesionales", Profesional, (
        Campo("legajo", "Legajo"), Campo("matricula", "Matrícula"), Campo("dni", "DNI"),
        Campo("nombre", "Nombre"), Campo("apellido", "Apellido"), Campo("especialidad", "Especialidad"),
        Campo("telefono", "Teléfono", "tel", requerido=False), Campo("email", "Email", "email", requerido=False),
        Campo("clinica_id", "Clínica", "select")),
        ("legajo", "matricula", "apellido", "nombre", "especialidad", "clinica")),
    "laboratorios": Catalogo("laboratorios", "Laboratorios", Laboratorio, (
        Campo("nombre", "Nombre"), Campo("direccion", "Dirección", requerido=False),
        Campo("telefono", "Teléfono", "tel", requerido=False), Campo("email", "Email", "email", requerido=False),
        Campo("responsable", "Responsable", requerido=False), Campo("activo", "Activo", "bool")),
        ("nombre", "direccion", "responsable", "activo")),
    "analisis": Catalogo("analisis", "Tipos de análisis", TipoAnalisis, (
        Campo("codigo", "Código"), Campo("nombre", "Nombre"), Campo("descripcion", "Descripción", requerido=False),
        Campo("precio", "Precio", "decimal"),
        Campo("tipo_muestra_requerida", "Muestra requerida", "select", TIPOS_MUESTRA),
        Campo("temperatura_min", "Temp. mín (°C)", "number"), Campo("temperatura_max", "Temp. máx (°C)", "number"),
        Campo("tiempo_estimado_horas", "Tiempo estimado (h)", "number", entero=True)),
        ("codigo", "nombre", "tipo_muestra_requerida", "precio", "temperatura_min", "temperatura_max")),
    "vacunas": Catalogo("vacunas", "Vacunas (esquema)", Vacuna, (
        Campo("nombre", "Nombre"), Campo("especie", "Especie", "select", ESPECIES),
        Campo("obligatoria", "Obligatoria", "bool"),
        Campo("edad_minima_semanas", "Edad mínima (semanas)", "number", entero=True),
        Campo("intervalo_refuerzo_dias", "Refuerzo cada (días)", "number", entero=True)),
        ("nombre", "especie", "obligatoria", "edad_minima_semanas", "intervalo_refuerzo_dias")),
    "contenedores": Catalogo("contenedores", "Contenedores", Contenedor, (
        Campo("codigo", "Código"), Campo("capacidad", "Capacidad (muestras)", "number", entero=True),
        Campo("temperatura_min", "Temp. mín (°C)", "number"), Campo("temperatura_max", "Temp. máx (°C)", "number"),
        Campo("clinica_id", "Clínica", "select")),
        ("codigo", "clinica", "capacidad", "temperatura_min", "temperatura_max", "estado")),
}

# Teléfono y email: si se cargan, con el mismo formato que los de los titulares (app/domain/validaciones.py).
VALIDADORES_DE_FORMATO = {"tel": validaciones.telefono, "email": validaciones.email}

# Campos select que guardan un enum del dominio (el formulario manda el valor como texto).
CAMPOS_ENUM = {TipoAnalisis: ("tipo_muestra_requerida", TipoMuestra), Vacuna: ("especie", Especie)}


class CatalogosService(ServicioBase):
    def catalogo(self, clave: str) -> Catalogo:
        if clave not in CATALOGOS:
            raise VeterinariaError(f"Catálogo desconocido: {clave}")
        return CATALOGOS[clave]

    def listar(self, clave: str) -> list:
        modelo = self.catalogo(clave).modelo
        orden = getattr(modelo, "nombre", None) or getattr(modelo, "codigo")
        return list(self.s.scalars(select(modelo).order_by(orden)))

    def clinicas(self) -> list[Clinica]:
        return list(self.s.scalars(select(Clinica).order_by(Clinica.nombre)))

    def laboratorios(self) -> list[Laboratorio]:
        return list(self.s.scalars(select(Laboratorio).order_by(Laboratorio.nombre)))

    @transaccional
    def guardar(self, clave: str, datos: dict, id_=None):
        """Crea (sin ``id_``) o actualiza un registro del catálogo con los datos del formulario."""
        cat = self.catalogo(clave)
        valores = {campo.nombre: _convertir_campo(campo, datos.get(campo.nombre)) for campo in cat.campos}
        _a_enums(cat.modelo, valores)
        if id_:
            obj = self.obtener(cat.modelo, id_)
            self._actualizar(obj, valores)
        else:
            obj = self._crear(cat.modelo, valores)
            self.s.add(obj)
        return obj

    @transaccional
    def cambiar_estado_contenedor(self, contenedor_id, accion: str) -> Contenedor:
        """``accion``: «mantenimiento» o «habilitar»."""
        c = self.obtener(Contenedor, contenedor_id)
        {"mantenimiento": c.enviar_a_mantenimiento, "habilitar": c.habilitar}[accion]()
        return c

    # --- alta y edición ------------------------------------------------------------------
    def _crear(self, modelo: type, v: dict):
        if modelo is Profesional:
            clinica = self.obtener(Clinica, v.pop("clinica_id"))
            profesional = Profesional(**v)
            clinica.agregar_profesional(profesional)
            return profesional
        if modelo is Contenedor:
            return Contenedor(v["codigo"], v["capacidad"], v["temperatura_min"], v["temperatura_max"],
                              self.obtener(Clinica, v["clinica_id"]))
        return modelo(**v)

    def _actualizar(self, obj, v: dict) -> None:
        if isinstance(obj, Contenedor):
            if v["temperatura_min"] > v["temperatura_max"] or v["capacidad"] <= 0:
                raise VeterinariaError("Revisá capacidad y rango de temperatura.")
            v["clinica"] = self.obtener(Clinica, v.pop("clinica_id"))
        if isinstance(obj, Profesional):
            self.obtener(Clinica, v.pop("clinica_id")).agregar_profesional(obj)
        for campo, valor in v.items():
            setattr(obj, campo, valor)


# --- conversión de los datos del formulario --------------------------------------------------
def _convertir_campo(campo: Campo, crudo):
    if campo.tipo == "bool":
        return a_bool(crudo) if crudo is not None else False
    if campo.requerido and texto(crudo) == "":
        raise VeterinariaError(f"El campo «{campo.etiqueta}» es obligatorio.")
    if campo.tipo == "number":
        return _numero(campo, crudo)
    if campo.tipo == "decimal":
        return _importe(campo, crudo)
    if campo.tipo == "select" and campo.nombre.endswith("_id"):
        return int(crudo)
    if campo.tipo in VALIDADORES_DE_FORMATO and texto(crudo):
        return VALIDADORES_DE_FORMATO[campo.tipo](crudo)
    return texto(crudo)


def _numero(campo: Campo, crudo) -> float | int | None:
    valor = a_float(crudo, campo.etiqueta)
    if campo.entero and valor is not None and valor.is_integer():
        return int(valor)
    return valor


def _importe(campo: Campo, crudo):
    try:
        valor = a_decimal(str(crudo).replace(",", "."))
    except Exception as exc:
        raise DatosInvalidosError(f"El campo «{campo.etiqueta}» debe ser un número.") from exc
    if valor < 0:
        raise DatosInvalidosError(f"El campo «{campo.etiqueta}» no puede ser negativo.")
    return valor


def _a_enums(modelo: type, valores: dict) -> None:
    if modelo in CAMPOS_ENUM:
        campo, enum = CAMPOS_ENUM[modelo]
        valores[campo] = enum(valores[campo])

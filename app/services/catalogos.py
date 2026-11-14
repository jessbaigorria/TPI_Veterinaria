"""Catálogos: alta/edición simple de clínicas, profesionales, laboratorios, tipos de análisis,
vacunas (esquema obligatorio) y contenedores."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select

from app.domain.atencion import Clinica, Profesional
from app.domain.base import a_decimal
from app.domain.enums import Especie, TipoMuestra
from app.domain.excepciones import VeterinariaError
from app.domain.laboratorio import Laboratorio, TipoAnalisis
from app.domain.personas import Vacuna
from app.domain.transporte import Contenedor
from app.services.base import ServicioBase, a_bool, a_float, texto, transaccional


@dataclass(frozen=True)
class Campo:
    nombre: str
    etiqueta: str
    tipo: str = "text"          # text | number | bool | select | decimal
    opciones: tuple = ()
    requerido: bool = True


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
        Campo("localidad", "Localidad", requerido=False), Campo("telefono", "Teléfono", requerido=False),
        Campo("email", "Email", requerido=False), Campo("activa", "Activa", "bool"),
        Campo("alta_complejidad", "Alta complejidad", "bool")),
        ("nombre", "localidad", "telefono", "alta_complejidad", "activa")),
    "profesionales": Catalogo("profesionales", "Profesionales", Profesional, (
        Campo("legajo", "Legajo"), Campo("matricula", "Matrícula"), Campo("dni", "DNI"),
        Campo("nombre", "Nombre"), Campo("apellido", "Apellido"), Campo("especialidad", "Especialidad"),
        Campo("telefono", "Teléfono", requerido=False), Campo("email", "Email", requerido=False),
        Campo("clinica_id", "Clínica", "select")),
        ("legajo", "matricula", "apellido", "nombre", "especialidad", "clinica")),
    "laboratorios": Catalogo("laboratorios", "Laboratorios", Laboratorio, (
        Campo("nombre", "Nombre"), Campo("direccion", "Dirección", requerido=False),
        Campo("telefono", "Teléfono", requerido=False), Campo("email", "Email", requerido=False),
        Campo("responsable", "Responsable", requerido=False), Campo("activo", "Activo", "bool")),
        ("nombre", "direccion", "responsable", "activo")),
    "analisis": Catalogo("analisis", "Tipos de análisis", TipoAnalisis, (
        Campo("codigo", "Código"), Campo("nombre", "Nombre"), Campo("descripcion", "Descripción", requerido=False),
        Campo("precio", "Precio", "decimal"),
        Campo("tipo_muestra_requerida", "Muestra requerida", "select", TIPOS_MUESTRA),
        Campo("temperatura_min", "Temp. mín (°C)", "number"), Campo("temperatura_max", "Temp. máx (°C)", "number"),
        Campo("tiempo_estimado_horas", "Tiempo estimado (h)", "number")),
        ("codigo", "nombre", "tipo_muestra_requerida", "precio", "temperatura_min", "temperatura_max")),
    "vacunas": Catalogo("vacunas", "Vacunas (esquema)", Vacuna, (
        Campo("nombre", "Nombre"), Campo("especie", "Especie", "select", ESPECIES),
        Campo("obligatoria", "Obligatoria", "bool"), Campo("edad_minima_semanas", "Edad mínima (semanas)", "number"),
        Campo("intervalo_refuerzo_dias", "Refuerzo cada (días)", "number")),
        ("nombre", "especie", "obligatoria", "edad_minima_semanas", "intervalo_refuerzo_dias")),
    "contenedores": Catalogo("contenedores", "Contenedores", Contenedor, (
        Campo("codigo", "Código"), Campo("capacidad", "Capacidad (muestras)", "number"),
        Campo("temperatura_min", "Temp. mín (°C)", "number"), Campo("temperatura_max", "Temp. máx (°C)", "number"),
        Campo("clinica_id", "Clínica", "select")),
        ("codigo", "clinica", "capacidad", "temperatura_min", "temperatura_max", "estado")),
}


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
        cat = self.catalogo(clave)
        valores = self._convertir(cat, datos)
        if id_:
            obj = self.obtener(cat.modelo, id_)
            self._actualizar(cat, obj, valores)
        else:
            obj = self._crear(cat, valores)
            self.s.add(obj)
        return obj

    @transaccional
    def cambiar_estado_contenedor(self, contenedor_id, accion: str) -> Contenedor:
        c = self.obtener(Contenedor, contenedor_id)
        {"mantenimiento": c.enviar_a_mantenimiento, "habilitar": c.habilitar}[accion]()
        return c

    # --- auxiliares -------------------------------------------------------------------
    def _convertir(self, cat: Catalogo, datos: dict) -> dict:
        valores = {}
        for campo in cat.campos:
            crudo = datos.get(campo.nombre)
            if campo.tipo == "bool":
                valores[campo.nombre] = a_bool(crudo) if crudo is not None else False
                continue
            if campo.requerido and texto(crudo) == "":
                raise VeterinariaError(f"El campo «{campo.etiqueta}» es obligatorio.")
            if campo.tipo == "number":
                valor = a_float(crudo, campo.etiqueta)
                valores[campo.nombre] = int(valor) if valor is not None and valor.is_integer() and campo.nombre in (
                    "capacidad", "edad_minima_semanas", "intervalo_refuerzo_dias", "tiempo_estimado_horas") else valor
            elif campo.tipo == "decimal":
                valores[campo.nombre] = a_decimal(str(crudo).replace(",", "."))
            elif campo.tipo == "select" and campo.nombre.endswith("_id"):
                valores[campo.nombre] = int(crudo)
            else:
                valores[campo.nombre] = texto(crudo)
        return valores

    def _crear(self, cat: Catalogo, v: dict):
        if cat.modelo is Profesional:
            clinica = self.obtener(Clinica, v.pop("clinica_id"))
            p = Profesional(**v)
            clinica.agregar_profesional(p)
            return p
        if cat.modelo is Contenedor:
            return Contenedor(v["codigo"], v["capacidad"], v["temperatura_min"], v["temperatura_max"],
                              self.obtener(Clinica, v["clinica_id"]))
        if cat.modelo is TipoAnalisis:
            v["tipo_muestra_requerida"] = TipoMuestra(v["tipo_muestra_requerida"])
        if cat.modelo is Vacuna:
            v["especie"] = Especie(v["especie"])
        return cat.modelo(**v)

    def _actualizar(self, cat: Catalogo, obj, v: dict) -> None:
        if cat.modelo is Contenedor:
            if v["temperatura_min"] > v["temperatura_max"] or v["capacidad"] <= 0:
                raise VeterinariaError("Revisá capacidad y rango de temperatura.")
            v["clinica"] = self.obtener(Clinica, v.pop("clinica_id"))
        if cat.modelo is Profesional:
            clinica = self.obtener(Clinica, v.pop("clinica_id"))
            clinica.agregar_profesional(obj)
        if cat.modelo is TipoAnalisis:
            v["tipo_muestra_requerida"] = TipoMuestra(v["tipo_muestra_requerida"])
            if Decimal(v["precio"]) < 0:
                raise VeterinariaError("El precio no puede ser negativo.")
        if cat.modelo is Vacuna:
            v["especie"] = Especie(v["especie"])
        for k, valor in v.items():
            setattr(obj, k, valor)

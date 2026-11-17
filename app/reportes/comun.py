"""Estructuras comunes de los reportes: filtros y resultado (tablas + gráficos)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import func

from app.domain import reloj


@dataclass
class Filtro:
    desde: date | None = None
    hasta: date | None = None
    clinica_id: int | None = None
    laboratorio_id: int | None = None
    especie: str | None = None

    @classmethod
    def ultimos_dias(cls, dias: int = 90, **kw) -> "Filtro":
        hoy = reloj.hoy()
        return cls(desde=hoy - timedelta(days=dias), hasta=hoy, **kw)

    @property
    def inicio(self) -> datetime:
        return datetime.combine(self.desde or date(2000, 1, 1), time.min)

    @property
    def fin(self) -> datetime:
        """Exclusivo: el día siguiente a ``hasta`` a las 00:00."""
        return datetime.combine((self.hasta or reloj.hoy()) + timedelta(days=1), time.min)

    def en_rango(self, columna):
        return (columna >= self.inicio) & (columna < self.fin)

    def aplicar(self, stmt, clinica=None, laboratorio=None):
        """Agrega al SELECT los filtros opcionales de clínica y de laboratorio, comparando contra las
        columnas indicadas (cada reporte sabe qué columna representa la clínica o el laboratorio)."""
        if clinica is not None and self.clinica_id:
            stmt = stmt.where(clinica == self.clinica_id)
        if laboratorio is not None and self.laboratorio_id:
            stmt = stmt.where(laboratorio == self.laboratorio_id)
        return stmt


@dataclass
class Tabla:
    titulo: str
    columnas: list[str]
    filas: list[list] = field(default_factory=list)
    totales: list | None = None

    def columna(self, indice: int) -> list:
        """Valores de una columna (para armar los gráficos a partir de la tabla)."""
        return [fila[indice] for fila in self.filas]


@dataclass
class Grafico:
    titulo: str
    tipo: str                    # bar | pie | doughnut | line
    etiquetas: list[str]
    series: list[dict]           # [{"label": str, "data": [...]}]
    apilado: bool = False
    horizontal: bool = False

    def config(self) -> dict:
        """Configuración lista para Chart.js."""
        opciones: dict = {"responsive": True, "maintainAspectRatio": False,
                          "plugins": {"legend": {"position": "bottom"}, "title": {"display": False}}}
        if self.tipo == "bar":
            opciones["scales"] = {"x": {"stacked": self.apilado}, "y": {"stacked": self.apilado, "beginAtZero": True}}
            if self.horizontal:
                opciones["indexAxis"] = "y"
        return {"type": self.tipo, "data": {"labels": self.etiquetas,
                                            "datasets": [_serializable(s) for s in self.series]},
                "options": opciones}


@dataclass
class Reporte:
    codigo: str
    titulo: str
    descripcion: str
    filtro: Filtro
    tablas: list[Tabla] = field(default_factory=list)
    graficos: list[Grafico] = field(default_factory=list)
    indicadores: list[tuple[str, str]] = field(default_factory=list)

    @property
    def vacio(self) -> bool:
        return all(not t.filas for t in self.tablas)


def serie(etiqueta: str, datos: list, color) -> dict:
    """Serie de un gráfico de Chart.js (``color`` puede ser uno o una lista, uno por barra/porción)."""
    return {"label": etiqueta, "data": datos, "backgroundColor": color}


def horas(expr_fin, expr_inicio):
    """Diferencia en horas entre dos columnas DateTime (SQLite: julianday)."""
    return (func.julianday(expr_fin) - func.julianday(expr_inicio)) * 24.0


def porcentaje(parte, total) -> float:
    return round(100.0 * float(parte or 0) / float(total), 1) if total else 0.0


def _serializable(serie: dict) -> dict:
    s = dict(serie)
    s["data"] = [float(x) if isinstance(x, Decimal) else x for x in s.get("data", [])]
    return s


PALETA = ["#0d9488", "#7c3aed", "#f59e0b", "#3b82f6", "#ef4444", "#10b981", "#6366f1", "#ec4899"]

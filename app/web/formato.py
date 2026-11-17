"""Filtros de Jinja2: fechas dd/mm/aaaa HH:MM, montos en pesos y colores fijos de los badges."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from app.domain.estados.estado_muestra import EstadoMuestra
from app.domain.estados.estado_remito import EstadoRemito

# Colores fijos de estado (CSS: .estado-<clave>). No deciden comportamiento: solo pintan.
COLOR_MUESTRA = {"Extraida": "gris", "Empaquetada": "azul", "EnTransito": "naranja", "Recibida": "celeste",
                 "Analizada": "verde", "Rechazada": "rojo"}
COLOR_REMITO = {"Armado": "gris", "Despachado": "azul", "EnTransito": "naranja",
                "Recibido": "verde", "RecibidoConObservaciones": "rojo"}
COLOR_POR_NOMBRE = {e.nombre: COLOR_MUESTRA[e.codigo] for e in EstadoMuestra.todos()}
COLOR_POR_NOMBRE["—"] = "gris"
COLOR_ENUM = {
    # atención
    "RESERVADA": "azul", "EN_PROGRESO": "naranja", "FINALIZADA": "verde", "CANCELADA": "gris",
    # orden
    "EMITIDA": "azul", "EN_PROCESO": "naranja", "COMPLETADA": "verde", "ANULADA": "gris",
    # factura
    "PAGADA": "verde",
    # cirugía
    "SOLICITADA": "azul", "ACEPTADA": "celeste", "PROGRAMADA": "violeta", "REALIZADA": "verde", "RECHAZADA": "rojo",
    # contenedor / precinto / recepción
    "DISPONIBLE": "verde", "EN_USO": "naranja", "EN_MANTENIMIENTO": "gris", "INTEGRO": "verde", "ROTO": "rojo",
    # resultado de la recepción (se distingue de la cirugía ACEPTADA por el tipo de enum)
    "ResultadoRecepcion.ACEPTADA": "verde", "ResultadoRecepcion.RECHAZADA": "rojo",
    "EstadoFactura.ANULADA": "rojo",
    # prioridad
    "NORMAL": "gris", "URGENTE": "rojo",
}


def fecha(valor) -> str:
    if not valor:
        return "–"
    if isinstance(valor, datetime):
        valor = valor.date()
    return valor.strftime("%d/%m/%Y") if isinstance(valor, date) else str(valor)


def fecha_hora(valor) -> str:
    if not valor:
        return "–"
    return valor.strftime("%d/%m/%Y %H:%M") if isinstance(valor, datetime) else fecha(valor)


def hora(valor) -> str:
    return valor.strftime("%H:%M") if valor else "–"


def dni(valor) -> str:
    """DNI con el formato de la máscara: ## ### ### (o # ### ### si tiene 7 dígitos)."""
    d = "".join(ch for ch in str(valor or "") if ch.isdigit())
    return f"{d[:-6]} {d[-6:-3]} {d[-3:]}" if len(d) >= 7 else (d or "–")


def moneda(valor) -> str:
    if valor is None or valor == "":
        return "–"
    entero, dec = f"{Decimal(str(valor)):,.2f}".split(".")
    return f"$ {entero.replace(',', '.')},{dec}"


def numero(valor) -> str:
    if valor is None:
        return "–"
    if isinstance(valor, float):
        return f"{valor:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return str(valor)


def valor_celda(valor) -> str:
    """Formato genérico para las tablas de reportes."""
    if isinstance(valor, Decimal):
        return moneda(valor)
    if isinstance(valor, datetime):
        return fecha_hora(valor)
    if isinstance(valor, date):
        return fecha(valor)
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    if isinstance(valor, float):
        return numero(valor)
    return "–" if valor is None else str(valor)


def color_muestra(muestra_o_codigo) -> str:
    codigo = getattr(muestra_o_codigo, "estado_codigo", muestra_o_codigo)
    return COLOR_MUESTRA.get(codigo, "gris")


def color_remito(remito_o_codigo) -> str:
    codigo = getattr(remito_o_codigo, "estado_codigo", remito_o_codigo)
    return COLOR_REMITO.get(codigo, "gris")


def color_enum(valor) -> str:
    clave = f"{type(valor).__name__}.{getattr(valor, 'value', valor)}"
    return COLOR_ENUM.get(clave) or COLOR_ENUM.get(getattr(valor, "value", valor), "gris")


def color_nombre_estado(nombre: str) -> str:
    return COLOR_POR_NOMBRE.get(nombre, "gris")


def etiqueta(valor) -> str:
    return getattr(valor, "etiqueta", str(valor) if valor is not None else "–")


NOMBRES_REMITO = {e.codigo: e.nombre for e in EstadoRemito.todos()}
NOMBRES_MUESTRA = {e.codigo: e.nombre for e in EstadoMuestra.todos()}

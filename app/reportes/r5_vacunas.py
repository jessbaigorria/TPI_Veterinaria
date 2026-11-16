"""Reporte: Vacunas pendientes por mascota (faltantes o vencidas)."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.domain import reloj
from app.domain.atencion import AtencionClinica
from app.domain.clinica import Clinica
from app.domain.enums import EstadoAtencion, Especie
from app.domain.personas import HistoriaClinica, Mascota, Titular, Vacuna
from app.reportes.comun import PALETA, Filtro, Grafico, Reporte, Tabla, serie

COL_DIAS_ATRASO = 9
DESCRIPCION = ("Mascotas activas con vacunas obligatorias (según especie y edad) sin aplicación vigente a la "
               "fecha de corte («Hasta»). «Desde» filtra por fecha de vencimiento.")


def generar(s: Session, filtro: Filtro) -> Reporte:
    corte = filtro.hasta or reloj.hoy()
    catalogo = list(s.scalars(select(Vacuna).where(Vacuna.obligatoria.is_(True))))
    tabla = Tabla("Mascotas activas con vacunas obligatorias faltantes o vencidas",
                  ["Mascota", "Especie", "Edad", "Titular", "Teléfono", "Email", "Vacuna", "Situación",
                   "Vencida desde", "Días de atraso", "Clínica última atención"])
    por_vacuna: dict[str, int] = {}
    mascotas_con_pendientes = set()
    for mascota, clinica in s.execute(_consulta_mascotas(filtro)).all():
        for d in mascota.historia_clinica.detalle_vacunas_pendientes(corte, catalogo):
            if filtro.desde and d.vencida_desde < filtro.desde:
                continue
            tabla.filas.append(_fila(mascota, d, clinica))
            etiqueta = f"{d.vacuna.nombre} ({d.vacuna.especie.etiqueta})"
            por_vacuna[etiqueta] = por_vacuna.get(etiqueta, 0) + 1
            mascotas_con_pendientes.add(mascota.id)
    tabla.filas.sort(key=lambda f: -f[COL_DIAS_ATRASO])
    grafico = Grafico("Pendientes por vacuna", "bar", list(por_vacuna),
                      [serie("Mascotas", list(por_vacuna.values()), PALETA[4])])
    atraso_maximo = max(tabla.columna(COL_DIAS_ATRASO), default=0)
    indicadores = [("Mascotas con pendientes", str(len(mascotas_con_pendientes))),
                   ("Vacunas pendientes", str(len(tabla.filas))),
                   ("Atraso máximo", f"{atraso_maximo} días")]
    return Reporte("vacunas", "Vacunas pendientes", DESCRIPCION, filtro, [tabla], [grafico], indicadores)


def _consulta_mascotas(filtro: Filtro):
    """Mascotas activas (de titulares activos) con la clínica de su última atención realizada."""
    ultima = (select(AtencionClinica.historia_id, func.max(AtencionClinica.fecha_hora_inicio).label("f"))
              .where(AtencionClinica.estado.in_([EstadoAtencion.EN_PROGRESO, EstadoAtencion.FINALIZADA]))
              .group_by(AtencionClinica.historia_id).subquery())
    clinica_ultima = (select(AtencionClinica.historia_id, Clinica.id.label("clinica_id"),
                             Clinica.nombre.label("clinica"), ultima.c.f)
                      .join(ultima, (ultima.c.historia_id == AtencionClinica.historia_id)
                            & (ultima.c.f == AtencionClinica.fecha_hora_inicio))
                      .join(Clinica, Clinica.id == AtencionClinica.clinica_id).subquery())
    stmt = (select(Mascota, clinica_ultima.c.clinica)
            .join(Titular).join(HistoriaClinica)
            .outerjoin(clinica_ultima, clinica_ultima.c.historia_id == HistoriaClinica.id)
            .where(Mascota.activa.is_(True), Titular.activo.is_(True))
            .options(selectinload(Mascota.historia_clinica).selectinload(HistoriaClinica.aplicaciones))
            .order_by(Titular.apellido, Mascota.nombre))
    if filtro.especie:
        stmt = stmt.where(Mascota.especie == Especie(filtro.especie))
    return filtro.aplicar(stmt, clinica=clinica_ultima.c.clinica_id)


def _fila(mascota: Mascota, detalle, clinica: str | None) -> list:
    t = mascota.titular
    return [mascota.nombre, mascota.especie.etiqueta, mascota.edad_texto(), t.nombre_completo(), t.telefono,
            t.email, detalle.vacuna.nombre, detalle.motivo, detalle.vencida_desde, detalle.dias_atraso,
            clinica or "Sin atenciones"]

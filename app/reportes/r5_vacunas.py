"""R5 – Vacunas pendientes por mascota (faltantes o vencidas)."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.domain import reloj
from app.domain.atencion import AtencionClinica, Clinica
from app.domain.enums import EstadoAtencion, Especie
from app.domain.personas import HistoriaClinica, Mascota, Titular, Vacuna
from app.reportes.comun import PALETA, Filtro, Grafico, Reporte, Tabla


def generar(s: Session, filtro: Filtro) -> Reporte:
    corte = filtro.hasta or reloj.hoy()
    catalogo = list(s.scalars(select(Vacuna).where(Vacuna.obligatoria.is_(True))))

    # Clínica de la última atención realizada de cada historia (consulta agregada).
    ultima = (select(AtencionClinica.historia_id, func.max(AtencionClinica.fecha_hora_inicio).label("f"))
              .where(AtencionClinica.estado.in_([EstadoAtencion.EN_PROGRESO, EstadoAtencion.FINALIZADA]))
              .group_by(AtencionClinica.historia_id).subquery())
    clinica_ultima = (select(AtencionClinica.historia_id, Clinica.id.label("clinica_id"),
                             Clinica.nombre.label("clinica"), ultima.c.f)
                      .join(ultima, (ultima.c.historia_id == AtencionClinica.historia_id)
                            & (ultima.c.f == AtencionClinica.fecha_hora_inicio))
                      .join(Clinica, Clinica.id == AtencionClinica.clinica_id).subquery())
    stmt = (select(Mascota, clinica_ultima.c.clinica_id, clinica_ultima.c.clinica, clinica_ultima.c.f)
            .join(Titular).join(HistoriaClinica)
            .outerjoin(clinica_ultima, clinica_ultima.c.historia_id == HistoriaClinica.id)
            .where(Mascota.activa.is_(True), Titular.activo.is_(True))
            .options(selectinload(Mascota.historia_clinica).selectinload(HistoriaClinica.aplicaciones))
            .order_by(Titular.apellido, Mascota.nombre))
    if filtro.especie:
        stmt = stmt.where(Mascota.especie == Especie(filtro.especie))
    if filtro.clinica_id:
        stmt = stmt.where(clinica_ultima.c.clinica_id == filtro.clinica_id)

    tabla = Tabla("Mascotas activas con vacunas obligatorias faltantes o vencidas",
                  ["Mascota", "Especie", "Edad", "Titular", "Teléfono", "Email", "Vacuna", "Situación",
                   "Vencida desde", "Días de atraso", "Clínica última atención"])
    por_vacuna: dict[str, int] = {}
    mascotas_con_pendientes = set()
    for mascota, _cid, clinica, _f in s.execute(stmt).all():
        for d in mascota.historia_clinica.detalle_vacunas_pendientes(corte, catalogo):
            if filtro.desde and d.vencida_desde < filtro.desde:
                continue
            t = mascota.titular
            tabla.filas.append([mascota.nombre, mascota.especie.etiqueta, mascota.edad_texto(), t.nombre_completo(),
                                t.telefono, t.email, d.vacuna.nombre, d.motivo, d.vencida_desde, d.dias_atraso,
                                clinica or "Sin atenciones"])
            etiqueta = f"{d.vacuna.nombre} ({d.vacuna.especie.etiqueta})"
            por_vacuna[etiqueta] = por_vacuna.get(etiqueta, 0) + 1
            mascotas_con_pendientes.add(mascota.id)
    tabla.filas.sort(key=lambda f: -f[9])
    grafico = Grafico("Pendientes por vacuna", "bar", list(por_vacuna), [
        {"label": "Mascotas", "data": list(por_vacuna.values()), "backgroundColor": PALETA[4]}])
    indicadores = [("Mascotas con pendientes", str(len(mascotas_con_pendientes))),
                   ("Vacunas pendientes", str(len(tabla.filas))),
                   ("Atraso máximo", f"{max((f[9] for f in tabla.filas), default=0)} días")]
    return Reporte("R5", "Vacunas pendientes por mascota",
                   "Mascotas activas con vacunas obligatorias (según especie y edad) sin aplicación vigente a la "
                   "fecha de corte («Hasta»). «Desde» filtra por fecha de vencimiento.",
                   filtro, [tabla], [grafico], indicadores)

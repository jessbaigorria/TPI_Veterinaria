"""Portal Clínica › Reportes: los cinco reportes con filtros, gráfico, tabla y exportación."""
from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy.orm import Session

from app import reportes
from app.services.catalogos import CatalogosService
from app.web.plantillas import render
from app.web.routers import reportes_web
from app.web.routers._comun import Db, UsrClinica
from app.web.sesion import UsuarioSesion

router = APIRouter(prefix="/clinica")


@router.get("/reportes")
def reportes_inicio(request: Request, u: UsuarioSesion = UsrClinica):
    return render(request, "clinica/reportes.html", seccion="reportes", titulos=reportes.TITULOS)


@router.get("/reportes/{codigo}")
def reporte(request: Request, codigo: str, u: UsuarioSesion = UsrClinica, s: Session = Db):
    filtro = reportes_web.filtro_desde_query(request, codigo)
    catalogos = CatalogosService(s)
    return reportes_web.mostrar(request, s, codigo, "base.html", filtro, clinicas=catalogos.clinicas(),
                                laboratorios=catalogos.laboratorios(), portal="clinica",
                                disponibles=list(reportes.TITULOS))

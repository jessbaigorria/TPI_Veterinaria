"""Portal Clínica › Inicio: indicadores, turnos del día, resultados recientes y últimos remitos."""
from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy.orm import Session

from app.domain import reloj
from app.services.atenciones import AtencionesService
from app.services.empaquetado import EmpaquetadoService
from app.services.resultados import ResultadosService
from app.services.tableros import TablerosService
from app.web.plantillas import render
from app.web.routers._comun import Db, UsrClinica
from app.web.sesion import UsuarioSesion

router = APIRouter(prefix="/clinica")


@router.get("")
def inicio(request: Request, u: UsuarioSesion = UsrClinica, s: Session = Db):
    return render(request, "clinica/inicio.html", seccion="inicio",
                  kpis=TablerosService(s).kpis_clinica(u.clinica_id),
                  turnos=AtencionesService(s).agenda(u.clinica_id, reloj.hoy()),
                  resultados=ResultadosService(s).resultados_recientes(u.clinica_id, 6),
                  remitos=EmpaquetadoService(s).listar_remitos(clinica_id=u.clinica_id)[:6])

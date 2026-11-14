"""Usuario de la sesión (sin contraseñas): portal + clínica/laboratorio + nombre de usuario.

El nombre se usa en todos los campos de auditoría (usuario, usuario_armador, usuario_colocador,
usuario_receptor, analista)."""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, Request

PORTAL_CLINICA = "clinica"
PORTAL_LABORATORIO = "laboratorio"


@dataclass
class UsuarioSesion:
    portal: str
    sede_id: int
    sede_nombre: str
    usuario: str
    alta_complejidad: bool = False

    @property
    def clinica_id(self) -> int:
        return self.sede_id

    @property
    def laboratorio_id(self) -> int:
        return self.sede_id


def usuario_actual(request: Request) -> UsuarioSesion | None:
    datos = request.session.get("usuario")
    return UsuarioSesion(**datos) if datos else None


def iniciar(request: Request, u: UsuarioSesion) -> None:
    request.session["usuario"] = u.__dict__


def cerrar(request: Request) -> None:
    request.session.pop("usuario", None)


def _exigir(request: Request, portal: str) -> UsuarioSesion:
    u = usuario_actual(request)
    if u is None or u.portal != portal:
        raise HTTPException(status_code=303, headers={"Location": "/"})
    return u


def usuario_clinica(request: Request) -> UsuarioSesion:
    return _exigir(request, PORTAL_CLINICA)


def usuario_laboratorio(request: Request) -> UsuarioSesion:
    return _exigir(request, PORTAL_LABORATORIO)


# --- mensajes (flash) --------------------------------------------------------------------
def avisar(request: Request, texto: str, tipo: str = "success", **extra) -> None:
    mensajes = request.session.setdefault("mensajes", [])
    mensajes.append({"tipo": tipo, "texto": texto, **extra})
    request.session["mensajes"] = mensajes


def tomar_mensajes(request: Request) -> list[dict]:
    return request.session.pop("mensajes", [])


def guardar_formulario(request: Request, datos: dict) -> None:
    request.session["form_previo"] = {k: v for k, v in datos.items() if isinstance(v, str) and len(v) < 500}


def tomar_formulario(request: Request) -> dict:
    return request.session.pop("form_previo", {})

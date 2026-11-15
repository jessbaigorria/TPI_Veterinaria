"""Reglas generales de la interfaz verificadas sobre los archivos: sin emojis de color, sin confirm()/alert(),
sin siglas R1–R5 ni textos técnicos visibles, y sin decidir transiciones con if estado == fuera de estados/."""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent / "app"
PLANTILLAS = list((RAIZ / "web" / "templates").rglob("*.html"))
JS = list((RAIZ / "web" / "static").rglob("*.js"))
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐]")


def _contenido(rutas):
    return {p: p.read_text(encoding="utf-8") for p in rutas}


def test_sin_emojis_de_color():
    for p, texto in _contenido(PLANTILLAS + JS).items():
        assert not EMOJI.search(texto), p


def test_sin_confirm_ni_alert_del_navegador():
    for p, texto in _contenido(PLANTILLAS + JS).items():
        assert not re.search(r"(?<![\w.-])(confirm|alert)\(", texto), p


def test_sin_siglas_ni_textos_tecnicos_en_plantillas():
    prohibidos = ["nace Extraída", "MascotaSinTitularError", "VeterinariaError:", "dominio",
                  "TurnoSuperpuestoError", "VacunasPendientesError", "DerivacionCirugiaError", "MuestraRechazadaError"]
    for p, texto in _contenido(PLANTILLAS).items():
        for palabra in prohibidos:
            assert palabra not in texto, (p, palabra)
        assert not re.search(r"\bR[1-5]\b", texto), p


def test_sin_if_estado_para_decidir_transiciones_fuera_de_estados():
    patron = re.compile(r"if\b[^\n]*\bestado(_codigo)?\s*(==|!=)")
    for p in RAIZ.rglob("*.py"):
        if "estados" in p.parts:
            continue
        for n, linea in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            assert not patron.search(linea), f"{p}:{n}: {linea.strip()}"
    for p, texto in _contenido(PLANTILLAS).items():
        assert not re.search(r"\{%[^%]*\bestado(\.value)?\s*(==|!=)", texto), p

# dashboard/routen/prognosen.py
import asyncio
import json
import os
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
_HIER = Path(__file__).resolve().parent.parent.parent
_templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))
_UEBERSPRINGEN = {".venv", "node_modules", "__pycache__", "tests", "test_dashboard", ".git"}


def _prognosen_lesen() -> list[dict]:
    ergebnisse = []
    for ordner, unterordner, dateien in os.walk(_HIER):
        unterordner[:] = sorted(d for d in unterordner if d not in _UEBERSPRINGEN)
        if "prognose.json" not in dateien:
            continue
        pfad = Path(ordner) / "prognose.json"
        try:
            d = json.loads(pfad.read_text(encoding="utf-8"))
        except Exception:
            continue
        for eintrag in (d if isinstance(d, list) else [d]):
            if isinstance(eintrag, dict):
                eintrag["_quelle"] = str(pfad.relative_to(_HIER))
                ergebnisse.append(eintrag)
    return ergebnisse


@router.get("/prognosen", response_class=HTMLResponse)
async def prognosen_seite(request: Request):
    return _templates.TemplateResponse(request, "prognosen.html", {"prognosen": await asyncio.to_thread(_prognosen_lesen)})

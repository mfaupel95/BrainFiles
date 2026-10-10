# dashboard/routen/training.py
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sse_starlette.sse import EventSourceResponse

from dashboard.quellen import jobs as _jobs
from dashboard.schutz import gleiche_herkunft

router = APIRouter()
_HIER = Path(__file__).resolve().parent.parent.parent
_PY = str(_HIER / "scanner" / ".venv" / "Scripts" / "python.exe")
_LOGS = _HIER / "backtest_laeufe"
_LAUF = _HIER / "verbesserer" / "lauf.py"
_templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

# Spuren, fuer die der Verbesserer-Lauf (verbesserer/lauf.py --spur) existiert.
_SPUREN = ("spur1",)


def _spur(spur: str) -> str:
    if spur not in _SPUREN:
        raise HTTPException(status_code=400, detail="unbekannte Spur")
    return spur


@router.get("/training", response_class=HTMLResponse)
async def training_seite(request: Request):
    return _templates.TemplateResponse(request, "training.html", {"spuren": list(_SPUREN)})


@router.post("/api/training/run", dependencies=[Depends(gleiche_herkunft)])
async def training_starten(spur: str = Form(...)):
    _spur(spur)
    log = _LOGS / f"training-{spur}.log"
    try:
        _jobs.starte(f"training-{spur}", [_PY, str(_LAUF), "--spur", spur, "--ohne-kerzen-abruf"],
                     cwd=_LAUF.parent, logdatei=log)
    except _jobs.JobLaeuftSchon:
        return JSONResponse({"ok": False, "meldung": "Lauf läuft schon"}, status_code=409)
    return JSONResponse({"ok": True, "log": log.name})


@router.get("/api/training/log/{spur}")
async def training_log(spur: str):
    _spur(spur)
    return EventSourceResponse(
        _jobs.log_strom(f"training-{spur}", _LOGS / f"training-{spur}.log", max_runden=600))

# dashboard/routen/backtest.py
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sse_starlette.sse import EventSourceResponse

from dashboard.quellen import jobs as _jobs
from dashboard.schutz import gleiche_herkunft

router = APIRouter()
_HIER = Path(__file__).resolve().parent.parent.parent  # Agenten/Handel/
_PY = str(_HIER / "scanner" / ".venv" / "Scripts" / "python.exe")
_LOGS = _HIER / "backtest_laeufe"
_templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

# Nur Spuren mit eigenem Ruecktest-Skript (CLI: --tage N).
_BACKTESTS = {"xperp": _HIER / "verbesserer" / "xperp_ruecktest.py"}


def _spur(spur: str) -> str:
    if spur not in _BACKTESTS:
        raise HTTPException(status_code=400, detail="kein Backtest fuer diese Spur")
    return spur


@router.get("/backtest", response_class=HTMLResponse)
async def backtest_seite(request: Request):
    return _templates.TemplateResponse(request, "backtest.html", {"spuren": sorted(_BACKTESTS)})


@router.post("/api/backtest/run", dependencies=[Depends(gleiche_herkunft)])
async def backtest_starten(spur: str = Form(...), tage: int = Form(30, ge=7, le=365)):
    _spur(spur)
    log = _LOGS / f"{spur}-letzter.log"
    try:
        _jobs.starte(f"backtest-{spur}", [_PY, str(_BACKTESTS[spur]), "--tage", str(tage)],
                     cwd=_BACKTESTS[spur].parent, logdatei=log)
    except _jobs.JobLaeuftSchon:
        return JSONResponse({"ok": False, "meldung": "Lauf läuft schon"}, status_code=409)
    return JSONResponse({"ok": True, "log": log.name})


@router.get("/api/backtest/log/{spur}")
async def backtest_log(spur: str):
    _spur(spur)
    return EventSourceResponse(_jobs.log_strom(f"backtest-{spur}", _LOGS / f"{spur}-letzter.log"))

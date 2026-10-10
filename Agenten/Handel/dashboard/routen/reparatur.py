# dashboard/routen/reparatur.py
import asyncio
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from dashboard.quellen import reparatur as _rep
from dashboard.schutz import gleiche_herkunft

router = APIRouter()
_templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/reparatur", response_class=HTMLResponse)
async def reparatur_seite(request: Request):
    return _templates.TemplateResponse(request, "reparatur.html", {"befunde": await asyncio.to_thread(_rep.alle_checks)})


@router.post("/api/repair/{check_id}", dependencies=[Depends(gleiche_herkunft)])
async def repair(check_id: str):
    return JSONResponse(_rep.fix_ausfuehren(check_id))

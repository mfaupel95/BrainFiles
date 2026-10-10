# dashboard/routen/steuerung.py
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from dashboard.quellen import prozesse as _prozesse
from dashboard.quellen import spuren as _spuren

router = APIRouter()
_templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))
_PROZESSE = ("dauerlauf", "omnitrade")


def gleiche_herkunft(request: Request) -> None:
    """CSRF-Schutz: schreibende Aufrufe nur von der eigenen Seite (Origin == Host)."""
    origin = request.headers.get("origin")
    if origin and urlparse(origin).netloc != request.headers.get("host", ""):
        raise HTTPException(status_code=403, detail="fremde Herkunft")


def _bekannt(name: str) -> str:
    if name not in _PROZESSE:
        raise HTTPException(status_code=404, detail="unbekannter Prozess")
    return name


@router.get("/steuerung", response_class=HTMLResponse)
async def steuerung_seite(request: Request):
    return _templates.TemplateResponse(request, "steuerung.html", {
        "spuren": _spuren.get_spuren(),
        "prozesse": _prozesse.systemprozesse(),
    })


@router.post("/api/spur/{spur_id}/notaus", dependencies=[Depends(gleiche_herkunft)])
async def spur_not_aus_api(spur_id: str):
    return JSONResponse(_prozesse.spur_not_aus(spur_id))


@router.post("/api/prozess/{name}/start", dependencies=[Depends(gleiche_herkunft)])
async def prozess_starten(name: str):
    _prozesse.system_starten(_bekannt(name))
    return {"ok": True}


@router.post("/api/prozess/{name}/stop", dependencies=[Depends(gleiche_herkunft)])
async def prozess_stoppen(name: str):
    _prozesse.system_stoppen(_bekannt(name))
    return {"ok": True}

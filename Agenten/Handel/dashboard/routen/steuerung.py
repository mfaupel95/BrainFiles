# dashboard/routen/steuerung.py
import asyncio
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from dashboard.quellen import prozesse as _prozesse
from dashboard.quellen import spuren as _spuren
from dashboard.schutz import gleiche_herkunft

router = APIRouter()
_templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))
_PROZESSE = ("dauerlauf", "omnitrade")


def _bekannt(name: str) -> str:
    if name not in _PROZESSE:
        raise HTTPException(status_code=404, detail="unbekannter Prozess")
    return name


@router.get("/steuerung", response_class=HTMLResponse)
async def steuerung_seite(request: Request):
    return _templates.TemplateResponse(request, "steuerung.html", {
        "spuren": await asyncio.to_thread(_spuren.get_spuren),
        "prozesse": await asyncio.to_thread(_prozesse.systemprozesse),
    })


@router.post("/api/spur/{spur_id}/notaus", dependencies=[Depends(gleiche_herkunft)])
async def spur_not_aus_api(spur_id: str):
    erg = _prozesse.spur_not_aus(spur_id)
    return JSONResponse(erg, status_code=erg.get("status", 200 if erg["ok"] else 500))


@router.post("/api/prozess/{name}/start", dependencies=[Depends(gleiche_herkunft)])
async def prozess_starten(name: str):
    if not await asyncio.to_thread(_prozesse.system_starten, _bekannt(name)):
        return JSONResponse({"ok": False, "meldung": f"{name} läuft schon"}, status_code=409)
    return {"ok": True}


@router.post("/api/prozess/{name}/stop", dependencies=[Depends(gleiche_herkunft)])
async def prozess_stoppen(name: str):
    _prozesse.system_stoppen(_bekannt(name))
    return {"ok": True}

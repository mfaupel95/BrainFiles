# dashboard/routen/monitor.py
import asyncio
import json
import time
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sse_starlette.sse import EventSourceResponse

from dashboard.quellen import spuren as _spuren

router = APIRouter()
_templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

_INTERVALL_S = 5      # Takt des Stroms
_MAX_EVENTS = None    # None = endlos; Tests setzen eine Zahl


@router.get("/", response_class=HTMLResponse)
async def monitor(request: Request):
    return _templates.TemplateResponse(
        request, "monitor.html", {"spuren": _spuren.get_spuren()})


async def _spuren_generator():
    n = 0
    while _MAX_EVENTS is None or n < _MAX_EVENTS:
        t0 = time.monotonic()
        # sammle() braucht Sekunden - im Thread, damit der Server nicht stillsteht
        daten = await asyncio.to_thread(_spuren.get_spuren)
        yield {"event": "spuren", "data": json.dumps(daten, ensure_ascii=False, default=str)}
        n += 1
        # Takt = Abstand der Updates, nicht Pause nach der Abfrage
        await asyncio.sleep(max(0.0, _INTERVALL_S - (time.monotonic() - t0)))


@router.get("/stream")
async def stream():
    return EventSourceResponse(_spuren_generator())

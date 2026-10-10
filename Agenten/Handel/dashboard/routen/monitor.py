# dashboard/routen/monitor.py
import asyncio
import json
import time
import weakref
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

# Ein sammle() je Takt fuer alle Clients (jede Abfrage kostet Sekunden).
_cache: dict = {}
_sperren = weakref.WeakKeyDictionary()  # eine Sperre je Event-Loop (Locks sind loop-gebunden)


def _sperre() -> asyncio.Lock:
    loop = asyncio.get_running_loop()
    if loop not in _sperren:
        _sperren[loop] = asyncio.Lock()
    return _sperren[loop]


async def _aktuell() -> list:
    """Spurstand, hoechstens einmal je Takt neu gelesen (im Thread, blockiert die Loop nicht)."""
    async with _sperre():
        jetzt = time.monotonic()
        if "daten" in _cache and jetzt - _cache["t"] < _INTERVALL_S * 0.8:
            return _cache["daten"]
        daten = await asyncio.to_thread(_spuren.get_spuren)
        _cache.update(t=time.monotonic(), daten=daten)
        return daten


@router.get("/", response_class=HTMLResponse)
async def monitor(request: Request):
    return _templates.TemplateResponse(request, "monitor.html", {"spuren": await _aktuell()})


async def _spuren_generator():
    n = 0
    while _MAX_EVENTS is None or n < _MAX_EVENTS:
        t0 = time.monotonic()
        daten = await _aktuell()
        yield {"event": "spuren", "data": json.dumps(daten, ensure_ascii=False, default=str)}
        n += 1
        # Takt = Abstand der Updates, nicht Pause nach der Abfrage
        await asyncio.sleep(max(0.0, _INTERVALL_S - (time.monotonic() - t0)))


@router.get("/stream")
async def stream():
    return EventSourceResponse(_spuren_generator())

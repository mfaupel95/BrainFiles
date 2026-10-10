# dashboard/schutz.py - gemeinsamer Schutz fuer schreibende Aufrufe
from urllib.parse import urlparse

from fastapi import HTTPException, Request


def gleiche_herkunft(request: Request) -> None:
    """CSRF-Schutz: schreibende Aufrufe nur von der eigenen Seite (Origin == Host)."""
    origin = request.headers.get("origin")
    if origin and urlparse(origin).netloc != request.headers.get("host", ""):
        raise HTTPException(status_code=403, detail="fremde Herkunft")

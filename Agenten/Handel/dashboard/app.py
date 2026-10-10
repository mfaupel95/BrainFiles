# dashboard/app.py
import base64
import secrets
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.staticfiles import StaticFiles

HIER = Path(__file__).resolve().parent


def _basic_auth(passwort: str):
    def _check(request: Request):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Basic "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": "Basic realm=dashboard"},
            )
        try:
            _, pw = base64.b64decode(auth[6:]).decode().split(":", 1)
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                headers={"WWW-Authenticate": "Basic realm=dashboard"})
        if not secrets.compare_digest(pw, passwort):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                headers={"WWW-Authenticate": "Basic realm=dashboard"})
    return _check


def create_app(lan: bool = False, passwort: str = "") -> FastAPI:
    deps = [Depends(_basic_auth(passwort))] if lan and passwort else []
    app = FastAPI(title="Omnitrade Dashboard", dependencies=deps)
    app.mount("/static", StaticFiles(directory=str(HIER / "static")), name="static")

    from dashboard.routen import monitor, steuerung, backtest, training, prognosen, reparatur
    for modul in (monitor, steuerung, backtest, training, prognosen, reparatur):
        app.include_router(modul.router)

    return app

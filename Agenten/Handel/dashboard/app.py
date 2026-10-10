# dashboard/app.py
import base64
import secrets
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

HIER = Path(__file__).resolve().parent

# Localhost-Modus: nur diese Host-Header (gegen DNS-Rebinding, siehe schutz.py).
LOKALE_HOSTS = ["localhost", "127.0.0.1"]


def _auth_ok(request: Request, passwort: str) -> bool:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Basic "):
        return False
    try:
        _, pw = base64.b64decode(auth[6:]).decode().split(":", 1)
    except Exception:
        return False
    return secrets.compare_digest(pw, passwort)


def create_app(lan: bool = False, passwort: str = "") -> FastAPI:
    if lan and not passwort:
        raise ValueError("LAN-Modus braucht ein Passwort (DASHBOARD_PASS)")
    app = FastAPI(title="Omnitrade Dashboard")
    app.mount("/static", StaticFiles(directory=str(HIER / "static")), name="static")

    from dashboard.routen import monitor, steuerung, backtest, training, prognosen, reparatur
    for modul in (monitor, steuerung, backtest, training, prognosen, reparatur):
        app.include_router(modul.router)

    if lan:
        # Middleware statt Dependency: gilt auch fuer /static und jede kuenftige Route.
        @app.middleware("http")
        async def _basic_auth(request: Request, call_next):
            if not _auth_ok(request, passwort):
                return Response(status_code=401, headers={"WWW-Authenticate": "Basic realm=dashboard"})
            return await call_next(request)
    else:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=LOKALE_HOSTS)

    return app

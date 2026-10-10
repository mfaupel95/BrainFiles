# dashboard/__main__.py
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn
from dashboard.app import create_app

_PORT = int(os.environ.get("DASHBOARD_PORT", "7788"))
_LAN = "--lan" in sys.argv
_PASS = os.environ.get("DASHBOARD_PASS", "")

if _LAN and not _PASS:
    print("FEHLER: --lan benötigt DASHBOARD_PASS-Umgebungsvariable.", file=sys.stderr)
    sys.exit(1)

app = create_app(lan=_LAN, passwort=_PASS)

if __name__ == "__main__":
    host = "0.0.0.0" if _LAN else "127.0.0.1"
    print(f"Dashboard: http://{'localhost' if not _LAN else '0.0.0.0'}:{_PORT}")
    uvicorn.run(app, host=host, port=_PORT, log_level="warning")

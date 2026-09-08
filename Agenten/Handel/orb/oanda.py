"""Zugang zu OANDA v20 (REST v3) - Kerzen, Preise, Instrumentdetails,
signierte Orders. Nur Standardbibliothek, ein Bearer-Header, kein eigenes .venv.
Vorbild: kraken/kraken.py (gleiche Aufgabenteilung, andere Boerse, kein HMAC -
OANDA authentifiziert mit einem Personal Access Token).

Practice- und Live-Host stehen in wachen.json, nie hartkodiert. Ein 401 hat
zwei Ursachen und die Meldung unterscheidet sie: Token abgelaufen ODER ein
Practice-Token gegen den Live-Host (SPEC.md, Fallen).
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HIER = Path(__file__).resolve().parent
WACHEN = HIER / "wachen.json"
KOPF = {"User-Agent": "MaxHirn-Handel/1.0"}
MAX_FEHLER = 5

# Test-Seam: die einzige Stelle, die wirklich ins Netz geht. Tests ersetzen sie.
_oeffne = None


class OandaFehler(RuntimeError):
    """Fachlicher Fehler aus einer gueltigen OANDA-Antwort. Kein Wiederholen."""


class OandaAuthFehler(OandaFehler):
    """401. Meldung unterscheidet abgelaufenen Token von Practice-gegen-Live."""


def _aus_registry(name):
    try:
        import winreg
    except ImportError:
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            wert, _ = winreg.QueryValueEx(k, name)
            return str(wert).strip() or None
    except OSError:
        return None


def _variable(name):
    return (os.environ.get(name) or "").strip() or _aus_registry(name)


def token():
    return _variable("OANDA_TOKEN")


def konto_id():
    return _variable("OANDA_KONTO_ID")


def zugang_vorhanden():
    return bool(token() and konto_id())


def _wachen():
    return json.loads(WACHEN.read_text(encoding="utf-8"))


def host(live):
    w = _wachen()
    return w["oanda_host_live"] if live else w["oanda_host_papier"]


def _urlopen(req, timeout):
    fn = _oeffne or urllib.request.urlopen
    return fn(req, timeout=timeout)


def _roh_json(url, *, method="GET", body=None):
    tok = token()
    if not tok:
        raise OandaFehler("OANDA_TOKEN nicht gesetzt")
    kopf = dict(KOPF)
    kopf["Authorization"] = "Bearer " + tok
    daten = None
    if body is not None:
        kopf["Content-Type"] = "application/json"
        daten = json.dumps(body).encode()
    req = urllib.request.Request(url, data=daten, headers=kopf, method=method)
    try:
        with _urlopen(req, 20) as antwort:
            return json.loads(antwort.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 401:
            if "fxtrade" in url:
                raise OandaAuthFehler(
                    "OANDA 401 gegen den Live-Host - Verdacht: ein Practice-Token "
                    "gegen fxtrade. Fuer Papier muss oanda_host_papier verwendet "
                    "werden.") from None
            raise OandaAuthFehler(
                "OANDA 401 gegen den Practice-Host - der Token ist abgelaufen "
                "oder falsch. Neuen Personal Access Token im OANDA-Konto ziehen.") from None
        raise OandaFehler("OANDA HTTP %d auf %s" % (e.code, method)) from None


def _mit_wiederholung(fn, *a, **kw):
    fehler = 0
    while True:
        try:
            return fn(*a, **kw)
        except OandaFehler:
            raise
        except Exception as e:  # noqa: BLE001 - Transportfehler, wird gezaehlt
            fehler += 1
            if fehler >= MAX_FEHLER:
                raise
            print("  OANDA-Transportfehler %d/%d: %s" % (fehler, MAX_FEHLER, e),
                  file=sys.stderr)
            time.sleep(1.5 * fehler)

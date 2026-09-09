"""Zugang zu OKX - oeffentliche Kursdaten und (optional) signierte Orders.

Oeffentliche Endpunkte brauchen keinen Schluessel. Die signierten kommen erst
zum Einsatz, wenn handeln.py mit --live laeuft UND wachen.json handel_erlaubt
auf true steht UND die drei Schluessel gesetzt sind.

Zwei Fallen, aus Wissen/Handelsbots.md:
  - OKX antwortet ohne User-Agent mit HTTP 403. Deshalb HEADERS.
  - Fehlversuche zaehlen, sonst haengt eine Schleife bei einem Ausfall endlos.

Schluessel werden aus der Prozessumgebung gelesen, ersatzweise direkt aus der
Windows-Registry (HKCU\\Environment) - genauso wie es der Kraken-MCP macht,
weil ein von Claude gestarteter Prozess die Benutzervariablen nicht geerbt
bekommt (siehe Wissen/Verbindungen.md).
"""

import base64
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone


def _env(name):
    return os.environ.get(name) or None


def _live_basis():
    """Host fuer echte Orders: OKX_BASE (EEA/global), sonst www.okx.com."""
    return _env("OKX_BASE") or "https://www.okx.com"


# Echte Orders nutzen den LIVE-Key (OKX_LIVE_API_*), nie den DEMO-Key.
# Der Scanner hat keinen Demo-/Live-Schalter je Aufruf: paper rechnet einfach
# nur lokal, live signiert. Deshalb liest diese Datei fuer signierte Calls
# IMMER den Live-Key und den Basis-Host aus OKX_BASE.
LI = ("OKX_LIVE_API_KEY", "OKX_LIVE_API_SECRET", "OKX_LIVE_API_PASSPHRASE")

HEADERS = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
MAX_FEHLER = 6


class OKXFehler(RuntimeError):
    """Fachlicher Fehler aus einer gueltigen OKX-Antwort (code != 0).
    Wird NICHT wiederholt - ein falscher instId wird beim zehnten Versuch
    auch nicht existieren."""


# --- Schluessel -------------------------------------------------------------

def _aus_registry(name):
    try:
        import winreg
    except ImportError:
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            wert, _ = winreg.QueryValueEx(k, name)
            return wert or None
    except OSError:
        return None


def _variable(name):
    return os.environ.get(name) or _aus_registry(name)


def schluessel_vorhanden():
    # Fuer echte Orders massgeblich: der LIVE-Key. Der DEMO-Key genuegt nicht.
    return all(_variable(n) for n in LI)


# --- HTTP ------------------------------------------------------------------

def _roh(pfad, methode="GET", body=None, signiert=False):
    url = _live_basis() + pfad
    daten = json.dumps(body) if body else ""
    kopf = dict(HEADERS)

    if signiert:
        key = _variable(LI[0])
        secret = _variable(LI[1])
        pw = _variable(LI[2])
        if not (key and secret and pw):
            raise RuntimeError("OKX-LIVE-Schluessel fehlen (Key/Secret/Passphrase)")
        ts = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        ts = ts.replace("+00:00", "Z")
        vortext = ts + methode + pfad + daten
        sig = base64.b64encode(
            hmac.new(secret.encode(), vortext.encode(), hashlib.sha256).digest()
        ).decode()
        kopf.update({
            "OK-ACCESS-KEY": key,
            "OK-ACCESS-SIGN": sig,
            "OK-ACCESS-TIMESTAMP": ts,
            "OK-ACCESS-PASSPHRASE": pw,
        })

    req = urllib.request.Request(
        url, data=daten.encode() if daten else None, headers=kopf, method=methode)
    try:
        with urllib.request.urlopen(req, timeout=20) as antwort:
            d = json.loads(antwort.read().decode())
    except urllib.error.HTTPError as e:
        # OKX legt auch bei 4xx eine JSON-Antwort mit code/msg bei. 401/403 auf
        # eine signierte Abfrage ist ein Schluesselproblem (falsche Passphrase,
        # falsches Secret, Key inaktiv, IP nicht freigegeben) - das heilt kein
        # Wiederholen. Als OKXFehler werfen, den _mit_wiederholung durchreicht.
        if signiert and e.code in (401, 403):
            try:
                f = json.loads(e.read().decode())
                raise OKXFehler("OKX %s: %s (HTTP %d - Schluessel/Passphrase/IP pruefen)"
                                % (f.get("code"), f.get("msg") or f, e.code)) from None
            except (ValueError, AttributeError):
                raise OKXFehler("OKX HTTP %d auf signierte Abfrage - "
                                "Schluessel/Passphrase/IP pruefen" % e.code) from None
        raise
    if d.get("code") not in ("0", 0):
        raise OKXFehler("OKX %s: %s" % (d.get("code"), d.get("msg") or d))
    return d.get("data", [])


def _mit_wiederholung(*a, **kw):
    fehler = 0
    while True:
        try:
            return _roh(*a, **kw)
        except OKXFehler:
            raise  # fachlich, nicht durch Wiederholen zu heilen
        except Exception as e:  # noqa: BLE001 - Transportfehler, wird gezaehlt
            fehler += 1
            if fehler >= MAX_FEHLER:
                raise
            print("  OKX-Transportfehler %d/%d: %s" % (fehler, MAX_FEHLER, e),
                  file=sys.stderr)
            time.sleep(1.5 * fehler)


# --- oeffentlich ---------------------------------------------------------------

def kerzen(inst, bar="1D", anzahl=300):
    """Tageskerzen, aufsteigend sortiert als [ts, open, high, low, close, vol]."""
    pfad = "/api/v5/market/candles?" + urllib.parse.urlencode(
        {"instId": inst, "bar": bar, "limit": min(anzahl, 300)})
    roh = _mit_wiederholung(pfad)
    reihen = [[int(r[0])] + [float(x) for x in r[1:6]] for r in roh]
    reihen.sort(key=lambda r: r[0])
    return reihen


def letzter_kurs(inst):
    pfad = "/api/v5/market/ticker?instId=" + inst
    d = _mit_wiederholung(pfad)
    return float(d[0]["last"])


# --- signiert (nur mit Schluessel + --live) --------------------------------

def guthaben_usdt():
    d = _mit_wiederholung("/api/v5/account/balance?ccy=USDT", signiert=True)
    if not d or not d[0].get("details"):
        return 0.0
    return float(d[0]["details"][0].get("availBal") or 0.0)


def markt_kauf(inst, usdt):
    """Market-Kauf ueber einen festen USDT-Betrag. Gibt ordId zurueck."""
    body = {"instId": inst, "tdMode": "cash", "side": "buy",
            "ordType": "market", "sz": str(usdt), "tgtCcy": "quote_ccy"}
    d = _roh("/api/v5/trade/order", "POST", body, signiert=True)
    return d[0]["ordId"]


def order_details(inst, ord_id):
    pfad = "/api/v5/trade/order?" + urllib.parse.urlencode(
        {"instId": inst, "ordId": ord_id})
    return _mit_wiederholung(pfad, signiert=True)[0]


def markt_verkauf(inst, basismenge):
    body = {"instId": inst, "tdMode": "cash", "side": "sell",
            "ordType": "market", "sz": str(basismenge)}
    d = _roh("/api/v5/trade/order", "POST", body, signiert=True)
    return d[0]["ordId"]


def stop_setzen(inst, basismenge, stop_preis):
    """Conditional-Order als Notausstieg. Loest als Market aus (slOrdPx -1)."""
    body = {"instId": inst, "tdMode": "cash", "side": "sell",
            "ordType": "conditional", "sz": str(basismenge),
            "slTriggerPx": str(stop_preis), "slOrdPx": "-1"}
    d = _roh("/api/v5/trade/order-algo", "POST", body, signiert=True)
    return d[0]["algoId"]


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    inst = sys.argv[1] if len(sys.argv) > 1 else "BTC-USDT"
    k = kerzen(inst)
    print("%s: %d Tageskerzen, %s bis %s" % (
        inst, len(k),
        time.strftime("%Y-%m-%d", time.localtime(k[0][0] / 1000)),
        time.strftime("%Y-%m-%d", time.localtime(k[-1][0] / 1000))))
    print("letzter Schluss: %.4f" % k[-1][4])
    print("Schluessel gesetzt:", schluessel_vorhanden())

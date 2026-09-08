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


# --- Kerzen -----------------------------------------------------------------
# M15-Kerzen fuer den ORB-Bereich. OANDA liefert je Abruf hoechstens
# MAX_JE_ABRUF Kerzen; ueber einen laengeren Zeitraum wird paginiert, indem der
# Cursor jeweils hinter die zuletzt gelieferte Kerze gesetzt wird (from ist bei
# OANDA inklusive). Eine noch laufende Kerze (complete:false) ist kein Signal
# und wird verworfen - weder in die Rueckgabe noch in den Cache.

MAX_JE_ABRUF = 5000
GRAN_SEKUNDEN = {"M15": 900, "M1": 60, "M5": 300, "H1": 3600, "D": 86400}


def _parse_kerze(c):
    from datetime import datetime, timezone
    t = c["time"][:19]  # "2025-07-15T07:00:00" ohne Nanosekunden + Z
    m = c["mid"]
    return {"zeit": datetime.fromisoformat(t).replace(tzinfo=timezone.utc),
            "o": float(m["o"]), "h": float(m["h"]),
            "l": float(m["l"]), "c": float(m["c"]),
            "complete": bool(c["complete"])}


def _kerzen_seite(oanda_inst, granularity, von, bis, live=False):
    import urllib.parse
    p = urllib.parse.urlencode({
        "granularity": granularity, "price": "M",
        "from": von.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "to": bis.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": MAX_JE_ABRUF,
    })
    url = "%s/v3/instruments/%s/candles?%s" % (host(live), oanda_inst, p)
    d = _mit_wiederholung(_roh_json, url)
    return [_parse_kerze(c) for c in d.get("candles", [])]


def _cache_datei(cache_dir, oanda_inst, granularity):
    return cache_dir / ("%s_%s.json" % (oanda_inst, granularity))


def _cache_laden(pfad):
    """Gibt {"von": dt, "bis": dt, "kerzen": [kerze, ...]} oder None zurueck.

    Der abgedeckte Bereich wird mitgespeichert: nur so weiss ein zweiter Lauf,
    dass er einen Abschnitt schon vollstaendig abgefragt hat - auch wenn der
    Markt darin gar keine (oder nur schon fertige) Kerzen hatte."""
    from datetime import datetime, timezone
    if not pfad.exists():
        return None
    roh = json.loads(pfad.read_text(encoding="utf-8"))
    for c in roh["kerzen"]:
        c["zeit"] = datetime.fromisoformat(c["zeit"]).replace(tzinfo=timezone.utc)
    roh["von"] = datetime.fromisoformat(roh["von"]).replace(tzinfo=timezone.utc)
    roh["bis"] = datetime.fromisoformat(roh["bis"]).replace(tzinfo=timezone.utc)
    return roh


def _cache_speichern(pfad, von, bis, kerzen_liste):
    pfad.parent.mkdir(parents=True, exist_ok=True)
    roh = {
        "von": von.strftime("%Y-%m-%dT%H:%M:%S"),
        "bis": bis.strftime("%Y-%m-%dT%H:%M:%S"),
        # Sicherheitsnetz: eine laufende Kerze landet nie im Cache.
        "kerzen": [dict(c, zeit=c["zeit"].strftime("%Y-%m-%dT%H:%M:%S"))
                   for c in kerzen_liste if c["complete"]],
    }
    pfad.write_text(json.dumps(roh, ensure_ascii=False), encoding="utf-8")


def kerzen(oanda_inst, *, von, bis, granularity="M15", cache_dir=None, live=False):
    """M15-Kerzen [von, bis), aufsteigend, ohne Duplikate, ohne complete:false.

    Paginiert in MAX_JE_ABRUF-Bloecken ueber from/to. Mit cache_dir wird der
    Bestand lueckenlos zwischengespeichert; ein zweiter Lauf ueber denselben
    (oder einen engeren) Bereich geht nicht mehr ins Netz."""
    from datetime import timedelta
    gran_s = GRAN_SEKUNDEN[granularity]

    vorhanden = {}
    abgedeckt_von = abgedeckt_bis = None
    cache_pfad = _cache_datei(cache_dir, oanda_inst, granularity) if cache_dir else None
    if cache_pfad:
        cache = _cache_laden(cache_pfad)
        if cache:
            for c in cache["kerzen"]:
                vorhanden[c["zeit"]] = c
            abgedeckt_von, abgedeckt_bis = cache["von"], cache["bis"]

    gedeckt = (abgedeckt_von is not None
               and abgedeckt_von <= von and abgedeckt_bis >= bis)
    if not gedeckt:
        cursor = von
        while cursor < bis:
            seite = _kerzen_seite(oanda_inst, granularity, cursor, bis, live)
            if not seite:
                break
            for c in seite:
                if c["complete"]:
                    vorhanden[c["zeit"]] = c
            naechster = seite[-1]["zeit"] + timedelta(seconds=gran_s)
            if naechster <= cursor:  # kein Fortschritt -> Abbruch
                break
            cursor = naechster

        if cache_pfad:
            neu_von = min(von, abgedeckt_von) if abgedeckt_von else von
            neu_bis = max(bis, abgedeckt_bis) if abgedeckt_bis else bis
            _cache_speichern(cache_pfad, neu_von, neu_bis,
                             [vorhanden[t] for t in sorted(vorhanden)])

    return [vorhanden[t] for t in sorted(vorhanden) if von <= t < bis]

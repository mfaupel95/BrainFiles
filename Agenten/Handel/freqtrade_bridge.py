"""Bruecke zum lokalen FreqTrade-Bot - rein lesend.

WARUM DIESE DATEI EXISTIERT
---------------------------
FreqTrade laeuft seit 29.09.2026 als Docker-Container im Probebetrieb
(`Agenten/Handel/freqtrade/`, dry_run, API nur auf 127.0.0.1:8080). Die
Handelszentrale soll ihn als weiteres System anzeigen (Plan:
Werkstatt/PLAN-handelszentrale-erweiterung-2026-09-29.md, Abschnitt 2).

RAHMEN
------
* **Nur lesen.** Jeder Aufruf ist ein GET auf einen Endpunkt aus `ERLAUBT`.
  `forceenter`, `forceexit`, `start`, `stop` gibt es hier bewusst nicht - ob
  die Zentrale ueber FreqTrade handeln darf, ist offene Frage 3 im Plan.
  `tests/test_freqtrade_bridge.py` prueft das am Quelltext.
* **Zugang** kommt aus der Bot-Konfiguration `freqtrade/user_data/config.json`
  (nicht versioniert) oder aus den Umgebungsvariablen `FREQTRADE_URL`,
  `FREQTRADE_USER`, `FREQTRADE_PASSWORD`, `FREQTRADE_CONFIG`. Kein Passwort
  im Code.
* **Offline ist kein Absturz.** `lage()` liefert dann `erreichbar: False`
  mit Grund - die Zentrale zeigt ein Warnzeichen statt zu haengen.

Nur Standardbibliothek (urllib), wie `moondev_daten.py`.

Aufruf:  python freqtrade_bridge.py      -> Kurzlage als JSON
"""

import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

HANDEL = os.path.dirname(os.path.abspath(__file__))
KONFIG = os.path.join(HANDEL, "freqtrade", "user_data", "config.json")
URL = "http://127.0.0.1:8080"
ZEITGRENZE = 10

# Einzige Endpunkte, die diese Bruecke kennt - alle lesend.
ERLAUBT = frozenset({
    "ping", "version", "show_config", "status", "count", "profit", "balance",
    "trades", "performance", "daily", "whitelist", "locks", "health",
})


class FreqtradeFehler(Exception):
    """Der Bot ist nicht erreichbar oder hat abgelehnt."""


def zugang(pfad=None):
    """(url, benutzer, passwort) aus Umgebung, sonst aus der Bot-Konfiguration."""
    pfad = pfad or os.environ.get("FREQTRADE_CONFIG") or KONFIG
    api = {}
    if os.path.exists(pfad):
        with open(pfad, encoding="utf-8") as f:
            api = json.load(f).get("api_server", {})
    url = os.environ.get("FREQTRADE_URL") or URL
    benutzer = os.environ.get("FREQTRADE_USER") or api.get("username", "")
    passwort = os.environ.get("FREQTRADE_PASSWORD") or api.get("password", "")
    return url.rstrip("/"), benutzer, passwort


def hole(endpunkt, zugangsdaten=None, zeitgrenze=ZEITGRENZE, **felder):
    """GET /api/v1/<endpunkt>. Wirft FreqtradeFehler statt zu raten."""
    if endpunkt not in ERLAUBT:
        raise ValueError("Endpunkt %r ist nicht freigegeben (nur lesend)" % endpunkt)
    url, benutzer, passwort = zugangsdaten or zugang()
    adresse = "%s/api/v1/%s" % (url, endpunkt)
    if felder:
        adresse += "?" + urllib.parse.urlencode(felder)
    kopf = {"Accept": "application/json"}
    if benutzer:
        paar = ("%s:%s" % (benutzer, passwort)).encode("utf-8")
        kopf["Authorization"] = "Basic " + base64.b64encode(paar).decode("ascii")
    anfrage = urllib.request.Request(adresse, headers=kopf, method="GET")
    try:
        with urllib.request.urlopen(anfrage, timeout=zeitgrenze) as antwort:
            return json.loads(antwort.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        raise FreqtradeFehler("HTTP %s bei /%s" % (e.code, endpunkt)) from e
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise FreqtradeFehler("nicht erreichbar: %s" % getattr(e, "reason", e)) from e


def offene_trades(zugangsdaten=None):
    return hole("status", zugangsdaten)


def trades(anzahl=50, zugangsdaten=None):
    return hole("trades", zugangsdaten, limit=int(anzahl))


def tagesbilanz(tage=7, zugangsdaten=None):
    return hole("daily", zugangsdaten, timescale=int(tage))


def lage(zugangsdaten=None):
    """Kurzlage fuer die Zentrale. Wirft nie; offline -> erreichbar False."""
    try:
        zd = zugangsdaten or zugang()
        konfig = hole("show_config", zd)
        gewinn = hole("profit", zd)
        guthaben = hole("balance", zd)
        offen = hole("status", zd)
    except (FreqtradeFehler, OSError, ValueError) as e:
        return {"erreichbar": False, "fehler": str(e)}
    return {
        "erreichbar": True,
        "dry_run": konfig.get("dry_run"),
        "zustand": konfig.get("state"),
        "boerse": konfig.get("exchange"),
        "strategie": konfig.get("strategy"),
        "zeitrahmen": konfig.get("timeframe"),
        "offene_trades": len(offen),
        "trades_gesamt": gewinn.get("trade_count", 0),
        "gewinn_geschlossen": gewinn.get("profit_closed_coin", 0.0),
        "gewinn_gesamt": gewinn.get("profit_all_coin", 0.0),
        "waehrung": guthaben.get("stake", konfig.get("stake_currency")),
        "guthaben": guthaben.get("total", 0.0),
    }


if __name__ == "__main__":
    ergebnis = lage()
    print(json.dumps(ergebnis, indent=2, ensure_ascii=False))
    sys.exit(0 if ergebnis["erreichbar"] else 1)

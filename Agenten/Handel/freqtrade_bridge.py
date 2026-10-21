"""Bruecke zum lokalen FreqTrade-Bot - rein lesend.

WARUM DIESE DATEI EXISTIERT
---------------------------
FreqTrade laeuft seit 29.09.2026 als Docker-Container im Probebetrieb
(`Agenten/Handel/freqtrade/`, dry_run, API nur auf 127.0.0.1). Die
Handelszentrale soll ihn als weiteres System anzeigen (Plan:
Werkstatt/PLAN-handelszentrale-erweiterung-2026-09-29.md, Abschnitt 2).

SEIT 30.09.2026 SIND ES MEHRERE BOTS
------------------------------------
Am 30.09.2026 liefen drei Bot-Container (8081 trading-agent, 8082 topmovers,
8083 marktlage-regime) und der Basis-Container auf 8080 ANTWORTETE NICHT
(gemessen: Verbindung abgelehnt). Diese Bruecke zeigte trotzdem nur 8080 -
der Reiter war damit permanent taub, obwohl drei Bots liefen. Die Bot-Liste
steht in `freqtrade/bots.json` (dieselbe Tabelle, die `bots.py` zum Starten
benutzt); `bots()` und `uebersicht()` lesen sie, eine zweite Liste gibt es
bewusst nicht.

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
BOTS_KONFIG = os.path.join(HANDEL, "freqtrade", "bots.json")
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


def bots(pfad=None):
    """Die startbaren Bots aus `freqtrade/bots.json` - EINE Wahrheit.

    Die Zentrale fuehrt keine eigene Bot-Liste: `bots.py` startet die Container
    aus genau dieser Datei, also zeigt die Bruecke auch dieselbe. Fehlt die
    Datei oder ist sie kaputt, kommt eine leere Liste zurueck - die Uebersicht
    ist dann leer, aber erfunden wird kein Bot.
    """
    pfad = pfad or os.environ.get("FREQTRADE_BOTS") or BOTS_KONFIG
    try:
        with open(pfad, encoding="utf-8") as f:
            inhalt = json.load(f)
    except (OSError, ValueError):
        return []
    aus = []
    for b in (inhalt.get("bots") if isinstance(inhalt, dict) else None) or []:
        if not isinstance(b, dict) or not b.get("name") or not b.get("port"):
            continue
        try:
            port = int(b["port"])
        except (TypeError, ValueError):
            continue
        aus.append({"name": str(b["name"]), "port": port,
                    "strategie": str(b.get("strategie") or "?"),
                    "zeitrahmen": str(b.get("zeitrahmen") or "?"),
                    "container": str(b.get("container") or ""),
                    "max_open_trades": b.get("max_open_trades"),
                    # Haus-Spur hinter einem HausSpur-Bot (seit 10.10.2026),
                    # leer bei den Moon-Dev-Bots - der Leitstand zeigt sie an.
                    "hausspur": str(b.get("hausspur") or "")})
    return aus


def _bot_name_fuer_port(port: int) -> str | None:
    """Der Bot-Name zu einer Portnummer aus `bots.json` - eine Wahrheit."""
    for b in bots():
        if int(b["port"]) == int(port):
            return str(b["name"])
    return None


def auf_satz_zugang(port: int, pfad: str | None = None):
    """(url, benutzer, passwort) aus der AUFSATZ-Datei `config.<name>.json`.

    Jeder Bot traegt dort seine EIGENEN Zufallswerte (geschrieben von
    `bots.py configs`). Seit 01.10.2026 laedt `bots_starten.sh` diesen
    Aufsatz in den Container, und die Container akzeptieren ihn (gemessen
    02.10.2026: show_config 200 mit dem Aufsatz-Passwort, 401 mit dem
    Basis-Passwort auf 8081-8083). Fehlt die Datei oder traegt sie keine
    Zugangsdaten, ist das Ergebnis None - dann gilt die Basis-config.json.
    """
    name = _bot_name_fuer_port(port)
    if not name:
        return None
    basis = os.path.dirname(pfad or os.environ.get("FREQTRADE_CONFIG") or KONFIG)
    aufsatz = os.path.join(basis, "config.%s.json" % name)
    if not os.path.exists(aufsatz):
        return None
    try:
        with open(aufsatz, encoding="utf-8") as f:
            api = json.load(f).get("api_server", {})
    except (OSError, ValueError):
        return None
    if not api.get("username") or not api.get("password"):
        return None
    url = os.environ.get("FREQTRADE_URL") or URL
    return url.rstrip("/"), api["username"], api["password"]


def zugang_fuer(port, pfad=None):
    """(url, benutzer, passwort) fuer EINE Portnummer.

    Der Port kommt vom Bot, die Anmeldung aus seiner AUFSATZ-Datei
    `config.<name>.json` (eigene Zufallswerte je Bot, seit 01.10.2026 vom
    Starter geladen und von den Containern akzeptiert - gemessen 02.10.2026:
    show_config 200 mit dem Aufsatz-Passwort, 401 mit dem Basis-Passwort auf
    8081-8083). Faellt der Aufsatz aus (Datei fehlt, keine Zugangsdaten),
    gilt die Basis-`config.json`.
    """
    url, benutzer, passwort = zugang(pfad)
    # Reihenfolge (gemessen 01.10.2026, dieselbe Lehre wie `hole`, `zugang`):
    #   1. Umgebungs-Variablen FREQTRADE_USER/FREQTRADE_PASSWORD - ein Aufrufer
    #      mit eigenem Zugang hat IMMER recht (der Test `test_umgebung_...`
    #      setzt genau das).
    #   2. der AUFSATZ `config.<name>.json` - eigene Zufallswerte je Bot, seit
    #      01.10.2026 vom Starter tatsaechlich in den Container geladen.
    #   3. die Basis-`config.json` - die einzige Anmeldung der Alt-Container.
    if not (os.environ.get("FREQTRADE_USER") or os.environ.get("FREQTRADE_PASSWORD")):
        aufsatz = auf_satz_zugang(port, pfad)
        if aufsatz:
            url, benutzer, passwort = aufsatz
    teile = urllib.parse.urlsplit(url)
    if not teile.scheme or not teile.hostname:
        return url, benutzer, passwort
    neu = teile._replace(netloc="%s:%d" % (teile.hostname, int(port)))
    return urllib.parse.urlunsplit(neu), benutzer, passwort


def hole(endpunkt, zugangsdaten=None, zeitgrenze=ZEITGRENZE, **felder):
    """GET /api/v1/<endpunkt>. Wirft FreqtradeFehler statt zu raten.

    Ein 401 ist seit dem Umbau (01.10.2026) ein echter Fehler, kein Hinweis
    auf einen Alt-Container: die Container akzeptieren ihre eigenen
    Aufsatz-Passwoerter (gemessen 02.10.2026: show_config 200 mit dem
    Aufsatz-Passwort, 401 mit dem Basis-Passwort auf 8081-8083). Der fruehere
    Rueckfall auf die Basis-config.json ist gestrichen - er wuerde einen
    echten Anmeldefehler still verschlucken.
    """
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


def lage_fuer(bot):
    """Kurzlage EINES Bots aus `bots()` - Port vom Bot, Zugang von der Basis."""
    return lage(zugang_fuer(bot["port"]))


def uebersicht(zeitgrenze=4, bot_liste=None):
    """Eine Zeile je Bot aus `bots()`: Modus, Zustand, offene Trades, G/V.

    Drei billige Aufrufe je Bot (`show_config`, `count`, `profit`) - kein
    `balance`/`status`, das haengt bei vollen Bots laenger. Ein nicht
    erreichbarer Bot bekommt trotzdem eine Zeile mit `erreichbar: False` und
    Grund: die Uebersicht soll zeigen, WELCHER Bot nicht antwortet, statt ihn
    zu verschlucken. Wirft nie.
    """
    aus = []
    for b in (bot_liste if bot_liste is not None else bots()):
        zeile = {"name": b["name"], "port": b["port"],
                 "strategie": b.get("strategie") or "?",
                 "zeitrahmen": b.get("zeitrahmen") or "?",
                 "max": b.get("max_open_trades"),
                 "erreichbar": False, "dry_run": None, "zustand": "?",
                 "offen": None, "trades": None, "gewinn": None, "fehler": ""}
        zugang = zugang_fuer(b["port"])
        try:
            konfig = hole("show_config", zugang, zeitgrenze=zeitgrenze)
            zahl = hole("count", zugang, zeitgrenze=zeitgrenze)
            gewinn = hole("profit", zugang, zeitgrenze=zeitgrenze)
        except (FreqtradeFehler, OSError, ValueError) as e:
            zeile["fehler"] = str(getattr(e, "reason", e))[:90] or type(e).__name__
            aus.append(zeile)
            continue
        zeile.update(erreichbar=True, dry_run=konfig.get("dry_run"),
                     zustand=konfig.get("state") or "?",
                     offen=zahl.get("current"),
                     trades=gewinn.get("trade_count"),
                     gewinn=gewinn.get("profit_closed_coin"))
        aus.append(zeile)
    return aus


if __name__ == "__main__":
    listen = bots()
    print("Bots aus %s: %s" % (BOTS_KONFIG,
                               ", ".join("%s:%s" % (b["name"], b["port"])
                                         for b in listen) or "keine"))
    zeilen = uebersicht(bot_liste=listen)
    print(json.dumps(zeilen, indent=2, ensure_ascii=False))
    # Exit 0, wenn EINER antwortet: die Bruecke ist brauchbar, auch wenn die
    # Basis-Instanz (8080) nicht laeuft - das war der Dauerzustand am 30.09.
    sys.exit(0 if any(z["erreichbar"] for z in zeilen) else 1)

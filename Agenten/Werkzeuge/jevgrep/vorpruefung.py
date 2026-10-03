"""Vorschalter fuer jevgrep: erst pruefen, dann Geld ausgeben.

Drei Dinge, die eine Suche teuer oder nutzlos machen, werden VOR dem Lauf geprueft:

1. **Anbieter** — laeuft die Bruecke (lokaler Endpunkt)? Antwortet der Dienst
   ueberhaupt, und wenn nein, mit welchem Grund (429 Kontingent, 402 kein Guthaben,
   403 Cloudflare)? Ein Testaufruf mit einer winzigen Frage kostet fast nichts.
2. **Wurzelgroesse** — `jg files` ist kostenlos und sagt, wie viele Dateien eine Suche
   lesen wuerde. Zu grosse Wurzeln werden abgelehnt (Schwelle, --trotzdem uebergeht).
3. **Kostenschaetzung** — aus der gemessenen Beziehung (1,7 MiB Wurzel ≈ 447.000 Token
   ≈ 1,8 US-Cent) wird der erwartete Betrag genannt.

Aufruf (macht der Wurzel-Aufrufer jevgrep.cmd automatisch vor jeder Suche):
    python vorpruefung.py "Wie wird X entschieden?" Agenten\\Handel\\scanner
    python vorpruefung.py --leise ...            # nur bei Problemen sprechen
    python vorpruefung.py --trotzdem ...         # grosse Wurzel zulassen
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HIER = Path(__file__).resolve().parent
WURZEL_DIR = HIER.parents[2]
JG = HIER / "node_modules" / "@dzhng" / "jevgrep" / "dist" / "bin" / "index.js"
WACHE = WURZEL_DIR / "Agenten" / "Hermes" / "scripts" / "jev-bruecke-wache.py"

# Gemessen am 01.10.2026 (Suche ueber Agenten/Handel/scanner, 66 Dateien, 1,7 MiB):
# 70 Anfragen, 447.049 Token, 1,8 US-Cent bei 0,04 USD/1M. Daraus das Verhaeltnis
# Token je Byte Wurzel - bewusst grob, es soll nur vor Ueberraschungen schuetzen.
TOKEN_JE_BYTE = 0.25
PREIS_JE_1M = {"mercury": 0.04, "jev": 0.042, "opencode": 0.042, "zen": 0.042,
               "typesafe": 0.04, "vercel": 0.04, "bruecke": 0.04, "lokal": 0.0}

# Ab hier ist eine Suche kein Blick mehr, sondern ein Lauf.
MAX_DATEIEN = 300
MAX_MIB = 60.0

SUBCOMMANDS = {"files", "auth", "doctor", "skill", "--help", "-h", "--version", "help"}
BRUECKEN_PORT = 8742


def anmeldung() -> dict:
    basis = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    p = Path(basis) / "jevgrep" / "credentials.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def testfrage(basis: str, modell: str, schluessel: str, frist: float = 45.0) -> tuple[bool, str]:
    """Eine winzige noul-Frage an DENSELBEN Endpunkt, den jevgrep benutzt."""
    koerper = json.dumps({
        "model": modell,
        "state": "def f(x):\n    return x + 1",
        "questions": {"q": {"type": "noul", "instructions": "Ist das Quelltext?"}},
    }).encode("utf-8")
    kopf = {"content-type": "application/json"}
    if schluessel:
        kopf["authorization"] = "Bearer " + schluessel
    req = urllib.request.Request(basis.rstrip("/") + "/systemone", data=koerper,
                                 headers=kopf, method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=frist) as r:
            daten = json.loads(r.read().decode("utf-8", "replace"))
        antworten = daten.get("answers") or {}
        if not antworten:
            return False, "Antwort ohne answers"
        return True, "%.1f s" % (time.time() - t0)
    except urllib.error.HTTPError as e:
        roh = e.read().decode("utf-8", "replace")[:200]
        grund = {
            429: "Kontingent aufgebraucht (429)",
            402: "kein Guthaben (402)",
            401: "Schluessel abgelehnt (401)",
            403: "Zugriff abgelehnt (403 - oft Cloudflare, nicht der Schluessel)",
            404: "Endpunkt oder Modell nicht gefunden (404)",
            500: "Dienstfehler (500)",
        }.get(e.code, "HTTP %s" % e.code)
        return False, "%s | %s" % (grund, roh)
    except Exception as e:                                      # noqa: BLE001
        return False, "%s: %s" % (type(e).__name__, e)


def bruecke_sicherstellen(basis: str, leise: bool = False) -> None:
    """Lokaler Bruecken-Endpunkt, der nicht antwortet: die Wache startet ihn.

    Nur fuer den BRUECKEN-Port - ein fremder lokaler Endpunkt (Testattrappe) wird
    nicht angefasst.
    """
    if str(BRUECKEN_PORT) not in basis:
        return
    try:
        with urllib.request.urlopen(
                basis.rstrip("/").replace("/v1", "") + "/gesundheit", timeout=4) as r:
            if r.status == 200:
                return
    except Exception:                                           # noqa: BLE001
        pass
    if not WACHE.is_file():
        return
    if not leise:
        print("Bruecke antwortet nicht - starte sie ueber die Wache ...", flush=True)
    try:
        subprocess.run([sys.executable, str(WACHE)], timeout=90,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:                                           # noqa: BLE001
        pass


def wurzel_aus(argv: list[str]) -> str | None:
    """Der Suchordner: der letzte Eintrag, der keine Option ist."""
    kandidaten = [a for a in argv if not a.startswith("-")]
    if len(kandidaten) >= 2:
        return kandidaten[-1]
    return None


def wurzelgroesse(ordner: str, frist: float = 120.0) -> tuple[int, float] | None:
    """`jg files` - kostenlos, kein Netz, kein Schluessel."""
    try:
        r = subprocess.run(
            ["node", str(JG), "files", ordner], capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=frist,
            # jevgrep loest den Wurzelpfad gegen das ARBEITSVERZEICHNIS des Aufrufers
            # auf - nicht gegen den Installationsordner.
            cwd=os.getcwd(),
        )
    except Exception:                                           # noqa: BLE001
        return None
    m = re.search(r"([\d,\.]+) files eligible \(([\d,\.]+) ([KMGT]?i?B)\)", r.stdout or "")
    if not m:
        return None
    dateien = int(m.group(1).replace(",", "").replace(".", ""))
    wert = float(m.group(2).replace(",", "."))
    faktor = {"B": 1 / 1024 / 1024, "KiB": 1 / 1024, "MiB": 1.0, "GiB": 1024.0,
              "TiB": 1024.0 * 1024}.get(m.group(3), 0.0)
    return dateien, wert * faktor


def heute() -> tuple[int, float]:
    """Was heute schon ausgegeben wurde: (Anfragen, US-Dollar) aus dem Bruecken-Protokoll."""
    log = WURZEL_DIR / "Agenten" / "Hermes" / "cache" / "jev-bruecke.log"
    if not log.is_file():
        return 0, 0.0
    heute_datum = time.strftime("%Y-%m-%d")
    anfragen, zeichen = 0, 0
    try:
        with log.open(encoding="utf-8", errors="replace") as f:
            for zeile in f:
                if heute_datum not in zeile[:40]:
                    continue
                try:
                    d = json.loads(zeile)
                except ValueError:
                    continue
                anfragen += 1
                zeichen += int(d.get("zustand_zeichen") or 0)
    except OSError:
        return 0, 0.0
    return anfragen, zeichen / 3.5 / 1e6 * 0.04


def pruefen(argv: list[str]) -> int:
    """Die Vorpruefung als Funktion (damit der Aufrufer sie ohne Prozessstart nutzt)."""
    leise = "--leise" in argv
    trotzdem = "--trotzdem" in argv
    argv = [a for a in argv if a not in ("--leise", "--trotzdem")]

    if argv and argv[0] in SUBCOMMANDS:
        return 0                                    # Subkommandos laufen ungeprueft

    daten = anmeldung()
    basis = daten.get("baseURL") or ""
    modell = daten.get("model") or ""
    schluessel = daten.get("apiKey") or ""
    if not basis:
        print("jevgrep ist nicht angemeldet. Erst anmelden:\n"
              "  python Agenten\\Werkzeuge\\jevgrep\\von_opencode_anmelden.py --anwenden\n"
              "  oder  Agenten\\Werkzeuge\\jevgrep\\bruecke-mercury.cmd  +  auth auf 127.0.0.1:8742")
        return 1

    bruecke_sicherstellen(basis, leise)
    ok, meldung = testfrage(basis, modell, schluessel)
    if not ok:
        print("Anbieter antwortet nicht - keine Suche gestartet.")
        print("  Endpunkt: %s | Modell: %s" % (basis, modell))
        print("  Grund: %s" % meldung)
        print("  Nachsehen: python Agenten\\Werkzeuge\\jevgrep\\pruefe_bruecke.py")
        return 1

    ordner = wurzel_aus(argv)
    kopf = "Anbieter %s ueber %s antwortet (%s)" % (modell, basis, meldung)
    if not ordner:
        if not leise:
            print(kopf + " | keine Wurzel angegeben - jevgrep nimmt das aktuelle Verzeichnis")
        return 0

    groesse = wurzelgroesse(ordner)
    if groesse is None:
        if not leise:
            print(kopf + " | Wurzelgroesse nicht messbar (%s)" % ordner)
        return 0
    dateien, mib = groesse
    token = mib * 1024 * 1024 * TOKEN_JE_BYTE
    preis = PREIS_JE_1M.get((modell or "").lower(), 0.04)
    kosten = token / 1e6 * preis

    if (dateien > MAX_DATEIEN or mib > MAX_MIB) and not trotzdem:
        print("Wurzel zu gross - keine Suche gestartet.")
        print("  %s: %d Dateien, %.1f MiB" % (ordner, dateien, mib))
        print("  Das waeren grob %.1f Mio. Token und %.2f US-Dollar." % (token / 1e6, kosten))
        print("  Grenzen: %d Dateien / %.0f MiB. Kleiner waehlen oder mit --trotzdem erzwingen."
              % (MAX_DATEIEN, MAX_MIB))
        return 1

    if not leise:
        n_heute, dollar_heute = heute()
        print("%s | Wurzel %s: %d Dateien, %.1f MiB | grob %.1f Mio. Token, %.2f US-Dollar"
              % (kopf, ordner, dateien, mib, token / 1e6, kosten))
        if n_heute:
            print("  heute schon %d Anfragen ueber die Bruecke, grob %.2f US-Dollar"
                  % (n_heute, dollar_heute))
    return 0


if __name__ == "__main__":
    sys.exit(pruefen(sys.argv[1:]))
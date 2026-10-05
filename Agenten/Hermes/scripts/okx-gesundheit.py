"""OKX-Gesundheit-Wache: sind die lesenden OKX-Kanaele erreichbar?

Waechter-Muster (wie bus-waechter): **leere Ausgabe = alles gut**, dann wird
nichts gesendet. Ausgabe gibt es nur bei Abweichung - dann steht der Befund
in der Telegram-Nachricht.

WARUM
-----
Der Handel laeuft ueber zwei lesende OKX-Kanaele: die Spuren (OKX-REST in
Handel/) und die onchainos-CLI (OKX-DEX, okx-dex-market). Faellt einer aus,
merkt es niemand, solange die Spuren gerade keine Runde haben. Diese Wache
prueft beide Kanaele ohne Schluessel und meldet nur den Ausfall.

Grenzen (bewusst):
- KEIN Schluessel, KEIN Kontostand: Guthaben/Wallet braucht Zugangsdaten,
  die hier bewusst nicht liegen (Wissen/Zugaenge.md ist die einzige Ablage).
- Die MCP-Kanaele prueft systempruefung.ps1; eine zweite Pruefung hier waere
  eine zweite Wahrheit.

Fehlerrichtung:
  --cli <pfad>  onchainos-CLI-Pfad ueberschreiben (oder eine tote Datei)
  --nur-api      nur die REST-API pruefen, ohne CLI-Aufruf

Aufruf:
  python Agenten/Hermes/scripts/okx-gesundheit.py
"""
import argparse
import json
import os
import subprocess
import sys
# Die Haus-Bremse: okx_takt begrenzt ALLE OKX-Abrufe des Hauses
# prozessuebergreifend (Datei in Agenten/Handel/cache), damit
# Wache, Zentrale und die drei Dauerlauf-Stufen sich nicht
# gegenseitig in die Drosselung laufen. Gemessen 05.10.2026:
# 6 parallene Threads -> 93x 'OKX 50011', nacheinander -> 0.
import os as _os, sys as _sys
# Die Haus-Bremse gegen OKX-Drosselung. Sie liegt in Agenten/Handel/ und wird
# ueber den PFAD geladen (importlib), nicht ueber sys.path: diese Datei laeuft
# aus Agenten/Hermes/scripts/, wo der Handel-Ordner nicht im Pfad steht. Genau
# darum nehmen es die Spuren (sys.path.append) und die Werkzeuge hier
# (importlib) auf zwei Wegen - Einer waere an einer Stelle falsch.
_s = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(
    _os.path.abspath(__file__)))), "Handel", "okx_takt.py")
if not os.path.exists(_s):
    raise RuntimeError("Haus-Bremse fehlt: %s" % _s)
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("okx_takt", _s)
okx_takt = _ilu.module_from_spec(_spec)
_sys.modules["okx_takt"] = okx_takt
_spec.loader.exec_module(okx_takt)

import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ONCHAINOS = os.environ.get("ONCHAINOS", "") or "onchainos"
OKX_ZEIT = "https://www.okx.com/api/v5/public/time"


def api_erreichbar(url=OKX_ZEIT, zeitgrenze=15):
    """True, wenn die URL mit 200 und lesbarem JSON antwortet."""
    try:
        anfrage = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 okx-gesundheit"})
        okx_takt.reserviere()
        with urllib.request.urlopen(anfrage, timeout=zeitgrenze) as r:
            if r.status != 200:
                return False
            json.loads(r.read().decode("utf-8", "replace"))
            return True
    except (OSError, ValueError, urllib.error.URLError):
        return False


def onchainos_lebt(zeitgrenze=30):
    """True, wenn die onchainos-CLI antwortet (read-only memepump-Aufruf)."""
    try:
        r = subprocess.run(
            [ONCHAINOS, "memepump", "tokens", "--chain", "solana"],
            capture_output=True, text=True, timeout=zeitgrenze,
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    except (OSError, subprocess.SubprocessError):
        return False
    if r.returncode != 0:
        return False
    try:
        d = json.loads(r.stdout or "")
    except ValueError:
        return False
    return bool(d.get("ok") and d.get("data"))


def pruefen(cli=ONCHAINOS, nur_api=False, api_url=OKX_ZEIT):
    """Liste deutscher Befundzeilen - leer, wenn alles in Ordnung ist."""
    global ONCHAINOS
    befunde = []
    if not api_erreichbar(url=api_url):
        befunde.append("OKX-REST (public/time) antwortet nicht.")
    if not nur_api:
        if not onchainos_lebt():
            befunde.append("onchainos-CLI (%s) antwortet nicht." % cli)
    return befunde


def main():
    ap = argparse.ArgumentParser(description="OKX-Gesundheit (lautlos, solange alles erreichbar ist)")
    ap.add_argument("--cli", default=None, help="onchainos-CLI-Pfad (Fehlerrichtung)")
    ap.add_argument("--api-url", default=None,
                    help="andere REST-URL (Fehlerrichtung)")
    ap.add_argument("--nur-api", action="store_true",
                    help="nur REST-API pruefen, ohne CLI (Fehlerrichtung)")
    ap.add_argument("--alles", action="store_true",
                    help="auch ohne Befund die Zahlen zeigen (Abnahme)")
    args = ap.parse_args()

    global ONCHAINOS
    if args.cli:
        ONCHAINOS = args.cli
    befunde = pruefen(cli=ONCHAINOS, nur_api=args.nur_api,
                      api_url=args.api_url or OKX_ZEIT)
    if not befunde:
        if args.alles:
            print("OKX-Gesundheit: kein Befund - REST und onchainos-CLI erreichbar.")
        return 0
    print("\n".join(["OKX-Gesundheit: %d Befund(e)" % len(befunde)] +
                    ["- %s" % b for b in befunde] +
                    ["Nichts davon ist geaendert worden; die Wache meldet nur."]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
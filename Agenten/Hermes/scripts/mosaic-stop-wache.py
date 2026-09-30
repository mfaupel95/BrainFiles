#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wache auf die Boersen-Stops der Spur mosaic (T-207).

WARUM: Am 30.09.2026 trugen die drei Kraken-Stops der Spur (BTC/ETH/SOL, rund
258 EUR) an der Boerse den Status ``canceled``, waehrend ``zustand.json``
weiter ``boersen_stop_fehlt: false`` meldete. Ein Feld im Buch ist eine
Behauptung, die altert - gefunden wurde das nur, weil jemand von Hand in
``kraken/spot_stops.py`` nachsah. Ohne Wache ist "Stop steht" nicht von
"Stop ist weg" zu unterscheiden, und die Stille sieht in beiden Faellen gleich
aus.

Diese Wache liest die BOERSE, nicht das Buch: sie ruft denselben Abgleich wie
der Zyklus (``mosaic/boersenabgleich.py``) im VORSCHAUMODUS - kein Stop wird
gesetzt, keine Position gebucht, keine Order ausgeloest. Sie meldet nur, was
nicht in Ordnung ist:

  1. eine Live-Position ohne wirksamen Stop an der Boerse,
  2. eine Position, die an der Boerse nicht mehr existiert (Stop gefeuert oder
     von Hand verkauft) und deshalb im Buch zu viel steht,
  3. ein Waisenstop (Buch kennt die Kennung, keine Live-Position mehr),
  4. eine unlesbare Boerse/Guthaben/Stop - dann steht die Aussage offen,
     statt stillschweigend "alles gut" zu bedeuten.

LEERE AUSGABE = nichts senden (Watchdog-Muster). Dieselbe Feststellung wird
hoechstens alle MELDE_PAUSE_H wiederholt; der Schluessel enthaelt nur Position
und Art der Stoerung, KEINE Zahlen - sonst gilt ein wachsender Kurs als neue
Meldung.

Aufruf (Hermes-Cron, no_agent, alle 30 Minuten):
    python mosaic-stop-wache.py            # melden, was nicht stimmt
    python mosaic-stop-wache.py --jetzt    # zeigen, nichts schreiben
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import importlib.util
import json
import sys
from pathlib import Path

HERMES = Path(__file__).resolve().parents[1]
HANDEL = HERMES.parents[0] / "Handel"
MOSAIC = HANDEL / "mosaic"
CACHE = HERMES / "cache"
MERKDATEI = CACHE / "mosaic-stop-wache.json"

MELDE_PAUSE_H = 6           # dieselbe Feststellung hoechstens alle 6 Stunden
GUT = ("ok", "nachgesetzt", "ausgebucht")     # Lagen, die kein Handeln brauchen
TEXT = {
    "stop_fehlt": "OHNE wirksamen Stop an der Boerse",
    "fehlt_weiter": "ohne Stop und ohne Moeglichkeit, einen zu setzen",
    "weg": "an der Boerse nicht mehr vorhanden - das Buch steht zu hoch",
    "weg_ohne_beleg": "weg, aber ohne belegbaren Ausstiegspreis",
    "unklar_boerse": "Boerse nicht unterstuetzt",
    "unklar_bestand": "Bestand nicht lesbar",
    "unklar_stop": "Stop-Zustand nicht lesbar",
    "waisen": "Stop ohne Position",
}


# --- Hausmodul ueber den Pfad laden (der Name liegt auch im scanner) --------

def _lade(name, pfad):
    schluessel = "%s@%s" % (name, str(pfad))
    if schluessel in sys.modules:
        return sys.modules[schluessel]
    spec = importlib.util.spec_from_file_location(schluessel, str(pfad))
    modul = importlib.util.module_from_spec(spec)
    sys.modules[schluessel] = modul
    spec.loader.exec_module(modul)
    return modul


def _lies(pfad):
    with open(pfad, "r", encoding="utf-8") as f:
        return json.load(f)


# --- Entscheidung (reine Funktionen, ohne Netz pruefbar) --------------------

def text_aus_bilanz(bilanz):
    """Die Meldung zu einem Abgleich-Ergebnis. Leer = alles in Ordnung."""
    zeilen = []
    befunde = bilanz.get("befunde") or []
    schlecht = [b for b in befunde if b.get("lage") not in GUT]
    for b in schlecht:
        zeilen.append("%s (%s): %s%s"
                      % (b.get("inst"), b.get("boerse"),
                         TEXT.get(b.get("lage"), b.get("lage")),
                         " - " + b["text"] if b.get("text") else ""))
    # Eine unlesbare Boerse/Guthaben/Stop steht schon als eigene Lage in der
    # Liste - eine zweite Regel dafuer waere eine zweite Wahrheit.
    return zeilen


def neu_zu_melden(zeilen, merk, jetzt=None):
    """Nur, was nicht schon in den letzten MELDE_PAUSE_H gemeldet wurde.

    Schluessel = die Meldung OHNE Zahlen (Position + Art der Stoerung), damit
    ein wandernder Kurs nicht jede Runde als neue Feststellung gilt.
    """
    jetzt = jetzt or dt.datetime.now()
    grenze = jetzt - dt.timedelta(hours=MELDE_PAUSE_H)
    gemeldet = {}
    for k, v in (merk.get("gemeldet") or {}).items():
        try:
            wann = dt.datetime.fromisoformat(v)
        except ValueError:
            continue
        if wann >= grenze:
            gemeldet[k] = v
    raus = []
    for z in zeilen:
        k = _schluessel(z)
        if k in gemeldet:
            continue
        gemeldet[k] = jetzt.isoformat(timespec="seconds")
        raus.append(z)
    return raus, {"gemeldet": gemeldet, "stand": jetzt.isoformat(timespec="seconds")}


def _schluessel(zeile):
    kopf = zeile.split(":")[0].strip()
    art = "unbekannt"
    for lage, text in TEXT.items():
        if text in zeile:
            art = lage
            break
    return "%s|%s" % (kopf, art)


# --- Lauf ------------------------------------------------------------------

def sammle(zustand_pfad, wachen_pfad):
    """Vorschau-Abgleich gegen die echte Boerse. Schreibt und ordert nichts."""
    ba = _lade("mosaic_boersenabgleich",
               MOSAIC / "boersenabgleich.py")
    z = _lies(zustand_pfad)
    w = _lies(wachen_pfad) if Path(wachen_pfad).exists() else {}
    roh = w.get("boersen") or ([w["boerse"]] if w.get("boerse") else [])
    standard = str(roh[0]).strip().lower() if roh else "kraken"
    # Auf einer KOPIE arbeiten: der Abgleich schreibt ein Merkmal ins Buch.
    bilanz = ba.pruefe(copy.deepcopy(z), anwenden=False, journal=None,
                       standard=standard, quote=w.get("kraken_quote"))
    return bilanz


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jetzt", action="store_true",
                    help="melden ohne Merkdatei zu schreiben")
    ap.add_argument("--zustand", default=str(MOSAIC / "zustand.json"))
    ap.add_argument("--wachen", default=str(MOSAIC / "wachen.json"))
    a = ap.parse_args(argv)

    try:
        bilanz = sammle(a.zustand, a.wachen)
    except Exception as e:                                     # noqa: BLE001
        print("mosaic-Stop-Wache: Abgleich nicht moeglich (%s: %s)"
              % (type(e).__name__, e))
        return 0

    zeilen = text_aus_bilanz(bilanz)
    if not zeilen:
        return 0                       # leere Ausgabe = nichts senden

    if a.jetzt:
        for z in zeilen:
            print(z)
        return 0

    try:
        merk = _lies(MERKDATEI)
    except Exception:                                          # noqa: BLE001
        merk = {}
    raus, neuer_merk = neu_zu_melden(zeilen, merk)
    try:
        CACHE.mkdir(parents=True, exist_ok=True)
        with open(MERKDATEI, "w", encoding="utf-8", newline="\n") as f:
            json.dump(neuer_merk, f, indent=2, ensure_ascii=False)
            f.write("\n")
    except Exception:                                          # noqa: BLE001
        pass
    for z in raus:
        print("mosaic: %s" % z)
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
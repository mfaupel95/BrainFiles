"""Haelt die Radar-Datenbank frisch - der Sammler, nicht die Spur.

Die Handelsspur `robinhood_radar` liest NUR (siehe deren lesen.py). Damit sie
etwas zu lesen hat, muss der Radar selbst sammeln. Das macht dieser Lauf:

  1. `discover --trenches`  - die kostenlose Wallet-Liste (rhtrenches.com),
     nur wenn die letzte Sammlung aelter als `DISCOVER_STUNDEN` ist.
  2. `track`               - die On-Chain-Spur der verfolgten Wallets
     (oeffentliches RPC auf Chain 4663, kein Schluessel).
  3. `enrich-tokens`       - die gehaltenen Token benennen und bepreisen
     (GeckoTerminal, der einzige Kursgeber fuer Chain 4663; DexScreener
     indexiert sie nicht). Ohne diesen Schritt bliebe `tokens.price_usd`
     leer und die Positionen stuenden ohne Kurs da (T-299).

Kein Schluessel noetig, keine Kosten. Rueckgabe 0, wenn nichts zu melden ist -
der Hermes-Cron sendet nur, was hier auf stdout steht (Watchdog-Muster:
leere Ausgabe = nichts senden).

Aufruf:
    python Agenten/Hermes/scripts/radar-sammeln.py
    python Agenten/Hermes/scripts/radar-sammeln.py --immer     # auch ohne Neuigkeit melden
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time

HIER = os.path.dirname(os.path.abspath(__file__))
WURZEL = os.path.dirname(os.path.dirname(os.path.dirname(HIER)))  # BrainFiles
REPO = os.path.join(WURZEL, "Werkstatt", "Repos", "fomo-robinhood-radar")
PYTHON = os.path.join(REPO, ".venv", "Scripts", "python.exe")
DB = os.path.join(REPO, "fomo_agent.db")
DISCOVER_STUNDEN = 24.0


def _umgebung() -> dict:
    """Umgebung des Radars: PYTHONHOME/PYTHONPATH raus, UTF-8 rein."""
    env = dict(os.environ)
    for name in ("PYTHONHOME", "PYTHONPATH"):
        env.pop(name, None)
    env["PYTHONIOENCODING"] = "utf-8"
    return env


# 04.10.2026: 300 -> 900 s. Die drei Aufrufe brauchen zusammen ~39 s
# (track 5-31 s, enrich-tokens 7 s, discover 1 s). Die gemessenen 349 s
# waren KEINE langsame Arbeit, sondern 95 haengende Runs in der Radar-DB
# - jeder Abbruch hinterliess einen Run ohne `finished_at`, der naechste
# Lauf sah offen Arbeit und wurde langsamer, bis er selbst abbrach.
# Nach dem Schliessen: track 5 s. 900 s laesst Luft fuer einen echten
# Haenger (Netz, RPC), ohne einen endlosen Zweig zu erlauben.
FRIST_S = 900


def _ruf(args: list[str], frist: int = None) -> tuple[int, str]:
    frist = FRIST_S if frist is None else frist
    a = [PYTHON, "-m", "fomo_agent.cli"] + args
    try:
        p = subprocess.run(a, cwd=REPO, env=_umgebung(), capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           timeout=frist)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:                                          # noqa: BLE001
        return 1, "Aufruf %s fehlgeschlagen: %s" % (" ".join(args), e)


def _letzte_sammlung(kind: str) -> float:
    """Wann lief diese Sammlung zuletzt? 0.0 = noch nie."""
    if not os.path.exists(DB):
        return 0.0
    try:
        con = sqlite3.connect("file:%s?mode=ro" % DB.replace("\\", "/"), uri=True)
        try:
            r = con.execute("SELECT MAX(finished_at) FROM runs WHERE kind = ?",
                            (kind,)).fetchone()
        finally:
            con.close()
        return float(r[0]) if r and r[0] else 0.0
    except Exception:                                               # noqa: BLE001
        return 0.0


def _kurz(text: str, grenze: int = 300) -> str:
    text = (text or "").strip().replace("\r", "")
    return text[-grenze:] if len(text) > grenze else text


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--immer", action="store_true",
                   help="auch ohne Neuigkeit eine Zeile ausgeben")
    a = p.parse_args()

    if not os.path.exists(PYTHON):
        print("radar-sammeln: Radar-venv fehlt (%s)" % PYTHON)
        return 1

    meldung, fehler = [], []

    altern = (time.time() - _letzte_sammlung("discover_trenches")) / 3600.0
    if altern >= DISCOVER_STUNDEN:
        rc, aus = _ruf(["discover", "--trenches"])
        if rc != 0:
            fehler.append("discover: %s" % _kurz(aus))
        else:
            meldung.append("Wallet-Liste erneuert: %s" % _kurz(aus, 200))

    rc, aus = _ruf(["track"])
    if rc != 0:
        fehler.append("track: %s" % _kurz(aus))
    else:
        try:
            # Die Zusammenfassung ist die LETZTE Zeile, die mit '{' beginnt -
            # davor steht Log-Text, der ebenfalls Zahlen enthaelt.
            zeilen = [z for z in aus.strip().splitlines()
                      if z.strip().startswith("{")]
            zahlen = json.loads(zeilen[-1])
            neu = int(zahlen.get("trades", 0))
            if neu or a.immer:
                meldung.append("Radar-Spur: %s Wallets, %s Fuellungen, "
                               "%s Fehler" % (zahlen.get("wallets"),
                                              zahlen.get("trades"),
                                              zahlen.get("errors")))
        except Exception:                                           # noqa: BLE001
            if a.immer:
                meldung.append("Radar-Spur: %s" % _kurz(aus))

    # Kurse: die gehaltenen Token benennen und bepreisen. Ohne diesen Schritt
    # bliebe tokens.price_usd leer (T-299) - GeckoTerminal ist der einzige
    # Kursgeber fuer Chain 4663, DexScreener indexiert sie nicht.
    rc, aus = _ruf(["enrich-tokens"])
    if rc != 0:
        fehler.append("enrich-tokens: %s" % _kurz(aus))
    else:
        try:
            zeilen = [z for z in aus.strip().splitlines()
                      if z.strip().startswith("{")]
            zahlen = json.loads(zeilen[-1])
            benannt = int(zahlen.get("named", 0))
            gepreist = int(zahlen.get("priced", 0))
            if benannt or gepreist or a.immer:
                meldung.append("Kurse: %s benannt, %s gepreist" % (benannt, gepreist))
        except Exception:                                           # noqa: BLE001
            if a.immer:
                meldung.append("Kurse: %s" % _kurz(aus))

    if fehler:
        print("radar-sammeln FEHLER:")
        for f in fehler:
            print("  " + f)
        return 1
    if meldung:
        print("radar-sammeln:")
        for m in meldung:
            print("  " + m)
    return 0


if __name__ == "__main__":
    sys.exit(main())
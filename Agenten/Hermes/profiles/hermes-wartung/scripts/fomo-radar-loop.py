"""Meldet NEUE Fuellungen der FOMO-Radar-Kohorte seit dem letzten Lauf.

Die Spur sammelt selbst (Hermes-Cron `radar-sammler`, alle 20 Minuten, ueber
`Agenten/Hermes/scripts/radar-sammeln.py`). Dieser Lauf sammelt NICHT - er liest
die Radar-DB nur. Zwei Sammler auf derselben DB waeren Doppelarbeit auf
demselben Schreibpfad (der `radar-sammeln.py`-Kopf nennt genau diese Falle).

PRUEFKRITERIUM IN EINER ZEILE
  Leere Ausgabe = keine neue Fuellung UND kein geaenderter Gesundheitsbefund.
  Der Normalfall schweigt; nur die Veraenderung wird gemeldet.

WARUM KEIN MODELLLAUF
  Der erste Versuch (Job `fomo-radar Loop` im Profil `bots`, 11.10.2026) liess
  einen Agenten `fomo-radar run` aufrufen. `run` ist eine Polling-Schleife und
  endete nach 303 s im Timeout; der Agent suchte sich danach selbst Dateien
  zusammen und sah den Fremd-Klon nicht, weil er in `profiles/` startete.
  Zahlen aus einer Datenbank brauchen kein Modell.

ZUSTAND
  `Agenten/Hermes/cache/fomo-radar-loop/letzter-stand.json` (gitignoriert):
  hoechster gesehener Fuellungs-Zeitstempel plus der Gesundheitsbefund des
  letzten Laufs. `--merkdatei` zeigt woanders hin - damit ist der Fehlerfall
  pruefbar, ohne die echte Merkdatei zu verdrehen.

AUFRUF
    python Agenten/Hermes/scripts/fomo-radar-loop.py
    python Agenten/Hermes/scripts/fomo-radar-loop.py --alles
    python Agenten/Hermes/scripts/fomo-radar-loop.py --merkdatei <pfad>
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
FRIST_HEALTH_S = 180
# So viele Zeilen hoechstens je Richtung - ein Bericht, keine Datenhalde.
MAX_ZEILEN = 8
REPO_NAME = "fomo-robinhood-radar"


def _wurzel_finden() -> str:
    """BrainFiles-Wurzel: aufwaerts suchen statt Ebenen zaehlen.

    Das Skript liegt je nach Einbau in `Agenten/Hermes/scripts/` ODER in
    `Agenten/Hermes/profiles/<profil>/scripts/` - eine feste Zahl von
    `dirname`-Aufrufen waere in der einen der beiden Ablagen falsch.
    """
    aus_umgebung = os.environ.get("BRAINFILES_WURZEL")
    if aus_umgebung and os.path.isdir(aus_umgebung):
        return aus_umgebung
    d = HIER
    for _ in range(8):
        if os.path.isdir(os.path.join(d, "Werkstatt", "Repos", REPO_NAME)):
            return d
        eltern = os.path.dirname(d)
        if eltern == d:
            break
        d = eltern
    return os.path.dirname(os.path.dirname(os.path.dirname(HIER)))


WURZEL = _wurzel_finden()
REPO = os.path.join(WURZEL, "Werkstatt", "Repos", REPO_NAME)
PYTHON = os.path.join(REPO, ".venv", "Scripts", "python.exe")
DB = os.path.join(REPO, "fomo_agent.db")
MERK = os.path.join(WURZEL, "Agenten", "Hermes", "cache",
                    "fomo-radar-loop", "letzter-stand.json")


def _umgebung() -> dict:
    """Umgebung des Radars: PYTHONHOME/PYTHONPATH raus, UTF-8 rein."""
    env = dict(os.environ)
    for name in ("PYTHONHOME", "PYTHONPATH"):
        env.pop(name, None)
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def _merk_lesen(pfad: str) -> dict:
    try:
        with open(pfad, encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else {}
    except Exception:                                               # noqa: BLE001
        return {}


def _merk_schreiben(pfad: str, daten: dict) -> None:
    try:
        os.makedirs(os.path.dirname(pfad), exist_ok=True)
        tmp = pfad + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(daten, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, pfad)
    except Exception as exc:                                        # noqa: BLE001
        print("fomo-radar-loop: Merkdatei nicht schreibbar (%s)" % exc)


def _neue_fuellungen(seit_ts: int) -> tuple[list, int]:
    """Fuellungen mit ts > seit_ts, gruppiert nach Token und Seite.

    Rueckgabe: (Zeilen als Liste von dicts, hoechster gesehener Zeitstempel).
    """
    con = sqlite3.connect("file:%s?mode=ro" % DB.replace("\\", "/"), uri=True)
    try:
        hoechste = con.execute("SELECT COALESCE(MAX(ts), 0) FROM trades").fetchone()[0]
        zeilen = con.execute(
            """
            SELECT t.mint,
                   COALESCE(k.symbol, '') AS symbol,
                   t.side,
                   COUNT(*)               AS n,
                   COALESCE(SUM(t.usd_value), 0) AS usd,
                   COUNT(DISTINCT t.address)     AS wallets
              FROM trades t
              LEFT JOIN tokens k ON k.mint = t.mint
             WHERE t.ts > ?
             GROUP BY t.mint, t.side
             ORDER BY usd DESC
            """,
            (int(seit_ts),),
        ).fetchall()
    finally:
        con.close()
    return ([{"mint": r[0], "symbol": r[1], "side": r[2], "n": r[3],
              "usd": r[4], "wallets": r[5]} for r in zeilen], int(hoechste or 0))


def _gesundheit() -> list:
    """Der Radar-eigene Gesundheitsbericht: Namen der fehlenden Pruefungen."""
    try:
        p = subprocess.run([PYTHON, "-m", "fomo_agent.cli", "health"],
                           cwd=REPO, env=_umgebung(), capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           timeout=FRIST_HEALTH_S)
        roh = (p.stdout or "") + (p.stderr or "")
    except Exception as exc:                                        # noqa: BLE001
        return ["health nicht abrufbar: %s" % exc]
    fehlt = []
    for z in roh.splitlines():
        s = z.strip()
        if s.startswith("BAD") or s.startswith("WARN") or s.startswith("FAIL"):
            # Statuswort weg - es wird beim Melden neu gesetzt, sonst stuende
            # "BAD  BAD fomo collection" in der Meldung.
            fehlt.append(" ".join(s.split()[1:3]))
    return fehlt


def _zaehlen() -> int:
    try:
        con = sqlite3.connect("file:%s?mode=ro" % DB.replace("\\", "/"), uri=True)
        try:
            return int(con.execute("SELECT COUNT(*) FROM trades").fetchone()[0])
        finally:
            con.close()
    except Exception:                                               # noqa: BLE001
        return 0


def _kurz(z: dict) -> str:
    name = z["symbol"] or z["mint"][:12]
    seite = "Kauf" if z["side"] == "buy" else "Verkauf"
    return "  %-10s %-8s %2d Fuellung(en), %d Wallet(s), $%s" % (
        name, seite, z["n"], z["wallets"], format(round(z["usd"]), ",d"))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--alles", action="store_true",
                   help="Zahlen auch ausgeben, wenn nichts neu ist")
    p.add_argument("--merkdatei", default=MERK,
                   help="Merkspeicher (Vorgabe: cache/fomo-radar-loop/letzter-stand.json)")
    a = p.parse_args()

    if not os.path.exists(PYTHON):
        print("fomo-radar-loop: Radar-venv fehlt (%s)" % PYTHON)
        return 1
    if not os.path.exists(DB):
        print("fomo-radar-loop: Radar-DB fehlt (%s)" % DB)
        return 1

    alt = _merk_lesen(a.merkdatei)
    seit_ts = int(alt.get("letzte_ts") or 0)
    alt_gesundheit = list(alt.get("gesundheit") or [])
    # Erster Lauf: die Merkdatei fehlt. Dann ist der Bestand die Grundlinie -
    # ihn als "neu" auszugeben waere ein Fehlalarm ueber 4600 Fuellungen.
    erster_lauf = seit_ts == 0

    try:
        zeilen, hoechste = _neue_fuellungen(seit_ts)
    except Exception as exc:                                        # noqa: BLE001
        print("fomo-radar-loop: Radar-DB nicht lesbar (%s)" % exc)
        return 1

    gesundheit = _gesundheit()

    aus = []
    if zeilen and not erster_lauf:
        summe = sum(z["usd"] for z in zeilen)
        kaeufe = sum(z["n"] for z in zeilen if z["side"] == "buy")
        verkaeufe = sum(z["n"] for z in zeilen if z["side"] == "sell")
        aus.append("FOMO-Radar: %d neue Fuellung(en) (%d Kauf, %d Verkauf), $%s"
                   % (kaeufe + verkaeufe, kaeufe, verkaeufe,
                      format(round(summe), ",d")))
        for z in zeilen[:MAX_ZEILEN]:
            aus.append(_kurz(z))
        if len(zeilen) > MAX_ZEILEN:
            aus.append("  ... %d weitere Token" % (len(zeilen) - MAX_ZEILEN))

    neu_gesundheit = [g for g in gesundheit if g not in alt_gesundheit]
    weg_gesundheit = [g for g in alt_gesundheit if g not in gesundheit]
    if (neu_gesundheit or weg_gesundheit) and not erster_lauf:
        if neu_gesundheit:
            aus.append("Radar-Gesundheit: neue Befunde")
            for g in neu_gesundheit:
                aus.append("  BAD  " + g)
        if weg_gesundheit:
            aus.append("Radar-Gesundheit: erledigt")
            for g in weg_gesundheit:
                aus.append("  ok   " + g)

    if a.alles and not aus:
        aus.append("FOMO-Radar: nichts neu seit %s (%d Fuellungen in der DB, "
                   "%d Gesundheitsbefund(e))"
                   % (time.strftime("%d.%m. %H:%M", time.localtime(seit_ts))
                      if seit_ts else "je",
                      _zaehlen(), len(gesundheit)))

    if aus:
        print("\n".join(aus))

    _merk_schreiben(a.merkdatei, {"letzte_ts": max(seit_ts, hoechste),
                                  "gesundheit": gesundheit,
                                  "stand": int(time.time())})
    return 0


if __name__ == "__main__":
    sys.exit(main())

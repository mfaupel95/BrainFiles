"""Wache fuer die omnitrade-Rust-Laeufe (`Werkstatt/omnitrade`).

Laeuft als Hermes-Cron OHNE Modell (`no_agent`): **leere Ausgabe = alles gut**.

Seit 01.10.2026 deckt die Wache ALLE `status/live*.json` ab, nicht nur die
erste Datei.

Aufruf:
    python Agenten/Hermes/scripts/omnitrade-lauf-wache.py          # Waechter
    python ... --alle                                              # alle zeigen
    python ... --grenze-s 0                                        # Alarmrichtung
    python ... --status PFAD                                       # nur eine Datei
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HIER = Path(__file__).resolve()
WURZEL = HIER.parents[3]  # scripts -> Hermes -> Agenten -> BrainFiles
HANDEL = WURZEL / "Agenten" / "Handel"

if str(HANDEL) not in sys.path:
    sys.path.insert(0, str(HANDEL))

_b_spec = importlib.util.spec_from_file_location(
    "omnitrade_bridge", str(HANDEL / "omnitrade_bridge.py"))
BRUECKE = importlib.util.module_from_spec(_b_spec)
_b_spec.loader.exec_module(BRUECKE)

_l_spec = importlib.util.spec_from_file_location(
    "omnitrade_lauf", str(HANDEL / "omnitrade_lauf.py"))
LAUF = importlib.util.module_from_spec(_l_spec)
_l_spec.loader.exec_module(LAUF)

_r_spec = importlib.util.spec_from_file_location(
    "lesen", str(HANDEL / "omnitrade" / "lesen.py"))
LESEN = importlib.util.module_from_spec(_r_spec)
_r_spec.loader.exec_module(LESEN)

MERKDATEI = WURZEL / "Agenten" / "Hermes" / "cache" / "omnitrade-lauf-wache.json"
WIEDERHOLUNG_STUNDEN = 6.0
STARTBEFEHL = "omnitrade.cmd start"
LEBT = None


def _lebt(pid: int) -> bool:
    if LEBT is not None:
        return bool(LEBT(pid))
    return LAUF.pid_lebt(pid)


def _alter_text(alter_s: float | None) -> str:
    if alter_s is None:
        return "Alter unbekannt"
    if alter_s < 120:
        return "%.0f s" % alter_s
    return "%.0f min" % (alter_s / 60.0)


def _dateien(pfad: str | None = None) -> list[str]:
    """Alle Statusdateien (live*.json), aelteste zuerst."""
    if pfad:
        if os.path.isfile(pfad):
            return [pfad]
        try:
            namen = sorted(os.listdir(pfad))
        except OSError:
            return []
        aus = []
        for n in namen:
            if n.startswith("live") and n.endswith(".json"):
                aus.append(os.path.join(pfad, n))
        return aus
    return LESEN.dateien()


def _lauf_anzeige(datei: str, grenze_s: float | None = None) -> dict:
    jetzt = time.time()
    lage = BRUECKE.lage(datei=datei, jetzt_ms=jetzt * 1000)
    name = os.path.basename(datei)
    pid = lage.get("pid")
    state = lage.get("state")
    alter_s = lage.get("alter_s")
    aus: dict = {
        "ok": False, "datei": datei, "name": name,
        "symbol": lage.get("symbol"), "inst": None,
        "state": state, "pid": pid, "alter_s": alter_s,
        "laeuft": False, "art": "unbekannt", "grund": "", "fehler": "",
    }
    if not lage.get("ok"):
        aus["fehler"] = lage.get("fehler") or "unbekannt"
        aus["art"] = "kaputt"
        aus["grund"] = aus["fehler"]
        return aus
    symbol = aus["symbol"]
    inst = LESEN.instrument(symbol) if symbol else None
    aus["inst"] = inst
    u = LAUF.beurteile(lage=lage, lebt=LEBT or LAUF.pid_lebt, alt_grenze_s=grenze_s)
    aus["laeuft"] = bool(u.get("laeuft"))
    if aus["laeuft"]:
        aus["art"] = "laeuft"
        aus["grund"] = "laeuft, PID %s, %s" % (pid, _alter_text(alter_s))
        return aus
    grund = u.get("grund") or "unbekannt"
    pid_lebt = _lebt(pid) if pid else False
    if pid and pid_lebt and ("haengt" in grund.lower()):
        aus["art"] = "haengt"
        aus["grund"] = "PID %s lebt, Datei haengt seit %s" % (pid, _alter_text(alter_s))
    elif not pid:
        aus["art"] = "kaputt"
        aus["grund"] = "keine PID"
    elif state and state != "running":
        aus["art"] = "beendet"
        aus["grund"] = "Zustand %r, PID %s" % (state, pid)
    elif not pid_lebt:
        aus["art"] = "beendet"
        aus["grund"] = "PID %s tot, Datei auf running" % pid
    else:
        aus["art"] = "beendet"
        aus["grund"] = grund
    return aus


def alle_befunde(grenze_s: float | None = None) -> list[dict]:
    dateien = _dateien()
    if not dateien:
        return []
    reihe = {"laeuft": 0, "haengt": 1, "beendet": 2, "kaputt": 3}
    aus = []
    for d in dateien:
        e = _lauf_anzeige(d, grenze_s=grenze_s)
        e["_ord"] = reihe.get(e.get("art", "unbekannt"), 9)
        aus.append(e)
    aus.sort(key=lambda x: (x["_ord"], x.get("name", "")))
    for e in aus:
        e.pop("_ord", None)
    return aus


def _meldung_erzeugen(befunde: list[dict]) -> list[str]:
    if not befunde:
        return []
    laufend = sum(1 for b in befunde if b.get("art") == "laeuft")
    non = [b for b in befunde if b.get("art") != "laeuft"]
    if not non:
        return []
    z = []
    z.append("omnitrade-Laeufe: %d/%d laufen, %d stehen" % (laufend, len(befunde), len(non)))
    for b in non:
        z.append("  %s [%s] %s - %s" % (b.get("name","?"), b.get("art","?").upper(),
                  b.get("inst") or b.get("symbol") or "?", b.get("grund","")))
    z.append("Starten: %s" % STARTBEFEHL)
    return z


def _merker() -> dict:
    try:
        with open(MERKDATEI, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _merke(stand: dict) -> None:
    try:
        MERKDATEI.parent.mkdir(parents=True, exist_ok=True)
        with open(MERKDATEI, "w", encoding="utf-8", newline="\n") as f:
            json.dump(stand, f, ensure_ascii=False, indent=1, sort_keys=True)
    except OSError:
        pass


def entdopple(zeilen, merker, stunden=WIEDERHOLUNG_STUNDEN, jetzt=None):
    jetzt = jetzt or datetime.now(timezone.utc)
    neu, zu = {}, []
    for z in zeilen:
        sk = re.sub(r"\d+", "#", z)[:90]
        alt = merker.get(sk)
        faellig = True
        if alt:
            try:
                t = datetime.fromisoformat(alt)
                if t.tzinfo is None:
                    t = t.replace(tzinfo=timezone.utc)
                faellig = (jetzt - t).total_seconds() >= stunden * 3600
            except ValueError:
                faellig = True
        neu[sk] = jetzt.isoformat(timespec="seconds") if faellig else alt
        if faellig:
            zu.append(z)
    for sk, t in list(neu.items()):
        try:
            ti = datetime.fromisoformat(t)
            if ti.tzinfo is None:
                ti = ti.replace(tzinfo=timezone.utc)
            if (jetzt - ti).days > 30:
                del neu[sk]
        except (ValueError, TypeError):
            del neu[sk]
    return zu, neu


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Wache fuer omnitrade-Laeufe")
    p.add_argument("--grenze-s", type=float, default=None,
                   help="Alter fuer haengend (0 = alles)")
    p.add_argument("--status", default=None, help="Nur diese eine Datei")
    p.add_argument("--alle", action="store_true", help="Auch gesunde zeigen")
    a = p.parse_args(argv)

    if a.status:
        e = _lauf_anzeige(a.status, grenze_s=a.grenze_s)
        if e.get("laeuft"):
            if a.alle:
                print("omnitrade-Lauf %s laeuft (PID %s, %s)"
                      % (e.get("name","?"), e.get("pid"),
                         _alter_text(e.get("alter_s"))))
            return 0
        zu = _meldung_erzeugen([e])
    else:
        bef = alle_befunde(grenze_s=a.grenze_s)
        if not bef:
            if a.alle:
                print("omnitrade-Statusordner leer")
            return 0
        zeilen = _meldung_erzeugen(bef)
        if zeilen:
            zu, nm = entdopple(zeilen, _merker())
            _merke(nm)
        else:
            zu = []
        if a.alle:
            lf = sum(1 for b in bef if b.get("art") == "laeuft")
            nf = [b for b in bef if b.get("art") != "laeuft"]
            print("omnitrade: %d laufen, %d stehen (%d gesamt)" % (lf, len(nf), len(bef)))
            for b in bef:
                name = b.get("name","?")
                inst = (b.get("inst") or b.get("symbol") or "?").ljust(12)
                art = b.get("art","?").upper().ljust(6)
                pid = str(b.get("pid") or "-").ljust(6)
                state = b.get("state") or "-"
                alter = _alter_text(b.get("alter_s")).ljust(12)
                print("  %s %s %s PID %s %s %s" % (art, inst, name, pid, alter, state))
            return 0

    if zu:
        if not a.status:
            print("omnitrade-Laeufe stehen")
        for z in zu:
            print("  " + z)
    return 0


if __name__ == "__main__":
    sys.exit(main())

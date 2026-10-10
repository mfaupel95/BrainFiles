#!/usr/bin/env python3
"""Platz-Wache (no_agent, woechentlich).

Meldet nur Posten, die eine Schwelle reissen - leere Ausgabe = nichts senden.
Die Schwellen stehen unten in SCHWELLEN, damit sie an einer Stelle aenderbar
sind (Zahlen gehoeren nicht in den Code verstreut).

Warum nicht `du`: ein `du` ueber ein inhaltsadressiertes Store (pnpm) braucht
mehrere Minuten und wuerde die Wache blockieren. Hier laeuft jede Messung mit
eigener Zeitgrenze; was nicht fertig wird, heisst "(nicht gemessen)" und zaehlt
NICHT als 0. Reparse-Punkte (Junctions) werden uebersprungen - genau die haben
die Groessenmessung mit `du` schon einmal verfaelscht.

Aufruf (immer):
  python platz-wache.py            # nur Posten ueber Schwelle (Cron-Betrieb)
  python platz-wache.py --immer    # vollstaendige Tabelle, auch ohne Schwelle
  python platz-wache.py --json     # Zustand fuer Werkzeuge
  python platz-wache.py --ohne-aufraeumen   # nur messen, nichts loeschen

RESERVE (Max, 30.09.2026): Auf C: werden 30 GB FREI gehalten. Anlass war der
Ausfall desselben Tages - ein Desktop-Build braucht rund 20 GB transient, C:
lief dabei auf 0,1 GB und der Update-Schwanz brach mit "No space left on device"
ab, der Desktop kam in eine Bootschleife. Faellt der freie Platz unter die
Reserve, raeumt diese Wache von selbst auf - aber NUR die vier erlaubten,
reproduzierbaren Posten (Temp aelter als 24 h, CrashDumps, uv-Cache,
npm-Cache). node_modules und .venv werden NIE angefasst (Hausregel), und
waehrend eines laufenden Builds/Updates wird gar nicht geloescht.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parent.parent.parent  # Agenten/Hermes/scripts -> BrainFiles
ZUSTAND = HIER.parent / "cache" / "platz-wache.json"

# Posten, Schwelle, Zeitgrenze (s) fuer die Messung
SCHWELLEN = {
    "frei_c_gb": 30.0,          # Reserve C: in GB (kleiner ist schlecht)
    "frei_q_gb": 30.0,          # freier Platz Q: (Ausser-Haus-Platte)
    "caches_gb": 3.0,           # pip + npm-cache + pnpm + uv zusammen
    "muell_gb": 2.0,            # CrashDumps + Temp zusammen
    "log_mb_einzeln": 200.0,    # groesste Agenten-Logdatei
    "backups_gb": 1.5,          # Agenten/_Backups
    "lock_minuten": 60,         # .git/index.lock-Alter (von Hand pruefen)
}

LAUFWERKE = {"C:": "frei_c_gb", "Q:": "frei_q_gb"}
CACHE_ORDNER = ["pip", "npm-cache", "pnpm", "uv"]
MUELL_ORDNER = ["CrashDumps", "Temp"]
LOG_GLOBS = ["Agenten/Handel/*.log", "Agenten/Routinen/logs/*.log"]


def _ist_verweis(eintrag: os.DirEntry) -> bool:
    """Junction/Symlink erkennen (os.path.isjunction gibt es erst ab 3.12)."""
    try:
        st = eintrag.stat(follow_symlinks=False)
    except OSError:
        return True
    attrs = getattr(st, "st_file_attributes", 0)
    return bool(attrs & 0x400) or eintrag.is_symlink()  # FILE_ATTRIBUTE_REPARSE_POINT


def groesse(pfad: Path, budget_s: float) -> int | None:
    """Summe der Dateigroessen unter pfad; None = Zeitgrenze gerissen."""
    if not pfad.exists():
        return 0
    ende = time.monotonic() + budget_s
    summe = 0
    stapel = [pfad]
    while stapel:
        if time.monotonic() > ende:
            return None
        jetzt = stapel.pop()
        try:
            with os.scandir(jetzt) as it:
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=False):
                            if not _ist_verweis(e):
                                stapel.append(Path(e.path))
                        elif e.is_file(follow_symlinks=False):
                            summe += e.stat(follow_symlinks=False).st_size
                    except OSError:
                        continue
        except OSError:
            continue
    return summe


def frei_gb(laufwerk: str) -> float | None:
    try:
        return round(shutil.disk_usage(laufwerk + os.sep).free / 1024**3, 1)
    except OSError:
        return None


def logdateien() -> list[tuple[float, str]]:
    treffer = []
    for muster in LOG_GLOBS:
        for p in WURZEL.glob(muster):
            try:
                treffer.append((p.stat().st_size / 1024**2, str(p.relative_to(WURZEL))))
            except OSError:
                continue
    return sorted(treffer, reverse=True)


def index_lock() -> tuple[float, bool] | None:
    lock = WURZEL / ".git" / "index.lock"
    if not lock.exists():
        return None
    alter_min = (time.time() - lock.stat().st_mtime) / 60
    echte = 0
    try:
        ps = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'git.exe' "
             "-and $_.CommandLine -notmatch 'fsmonitor' } | Measure-Object).Count"],
            capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        echte = int(ps.stdout.strip() or 0)
    except Exception:
        echte = -1
    return alter_min, echte == 0


# --- Reserve: aufraeumen, wenn C: unter die Schwelle faellt -----------------

# Spuren eines laufenden Baus/Updates. Liegt eine vor, wird NICHTS geloescht -
# ein "uv cache clean" mitten im Build zerstoert ihn (Lehre vom 30.09.2026).
BAU_WOERTER = (
    "source_completion", "hermes_cli.main update", "electron-builder",
    "npm-cli.js run build", "vite build", "uv.exe",
)
TEMP_MINDESTALTER_H = 24.0


def hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", str(WURZEL / "Agenten" / "Hermes")))


def bau_marker() -> list[Path]:
    """Dateien, deren blosse Existenz 'hier laeuft ein Update' heisst."""
    h = hermes_home()
    return [h / ".hermes-update-in-progress"] + sorted(h.glob("installs/*/source-completion-pending"))


def bau_laeuft(marker: list[Path], kommandos: list[str]) -> bool:
    """Reine Entscheidung - Zeugen werden hereingereicht, damit sie pruefbar ist."""
    if any(p.exists() for p in marker):
        return True
    return any(w in k for k in kommandos for w in BAU_WOERTER)


def aufraeum_schritte() -> list[tuple[str, str]]:
    """Die ERLAUBTEN Posten - eine Stelle, damit die Regel pruefbar bleibt.

    Bewusst NICHT dabei: node_modules, .venv, pnpm-Store, Modelle, Sicherungen.
    """
    return [
        ("temp", "Temp-Dateien aelter als 24 h"),
        ("crashdumps", "CrashDumps"),
        ("uv", "uv cache clean"),
        ("npm", "npm cache clean --force"),
    ]


def _prozess_kommandos() -> list[str]:
    try:
        ps = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process | ForEach-Object { $_.CommandLine }"],
            capture_output=True, text=True, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        return [z for z in ps.stdout.splitlines() if z.strip()]
    except Exception:
        return []


def _dateien_loeschen(wurzel: Path, mindestalter_h: float, budget_s: float = 30.0) -> int:
    """Loescht Dateien unter wurzel, die aelter als mindestalter_h sind."""
    if not wurzel.exists():
        return 0
    grenze = time.time() - mindestalter_h * 3600
    ende = time.monotonic() + budget_s
    frei = 0
    stapel = [wurzel]
    while stapel and time.monotonic() < ende:
        jetzt = stapel.pop()
        try:
            with os.scandir(jetzt) as it:
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=False):
                            if not _ist_verweis(e):
                                stapel.append(Path(e.path))
                            continue
                        st = e.stat(follow_symlinks=False)
                        if st.st_mtime < grenze:
                            frei += st.st_size
                            os.unlink(e.path)
                    except OSError:
                        continue
        except OSError:
            continue
    return frei


def _schritt_ausfuehren(name: str, basis: Path, darf_loeschen: bool) -> int | None:
    """Ein erlaubter Posten. Rueckgabe: freigegebene Bytes, None = uebersprungen."""
    if name == "temp":
        return _dateien_loeschen(basis / "Temp", TEMP_MINDESTALTER_H)
    if name == "crashdumps":
        return _dateien_loeschen(basis / "CrashDumps", 0.0)
    if not darf_loeschen:
        return None
    befehl = (["uv", "cache", "clean"] if name == "uv"
              else ["npm", "cache", "clean", "--force"])
    vorher = frei_gb("C:") or 0.0
    try:
        subprocess.run(befehl, capture_output=True, text=True, timeout=600, shell=False, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except Exception:
        return None
    nachher = frei_gb("C:") or 0.0
    return int(max(0.0, nachher - vorher) * 1024**3)


def reserve_aufraeumen(stand: dict, trocken: bool = False) -> list[str]:
    """Raeumt auf, wenn C: unter der Reserve liegt. Rueckgabe: Meldungszeilen."""
    frei = stand.get("frei_c_gb")
    if frei is None or frei >= SCHWELLEN["frei_c_gb"]:
        return []
    basis = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local")))
    laeuft = bau_laeuft(bau_marker(), _prozess_kommandos())
    zeilen = [f"Reserve verletzt: C: {frei} GB frei (Ziel {SCHWELLEN['frei_c_gb']} GB)"]
    if laeuft:
        zeilen.append("  ein Build/Update laeuft - es wird NICHT geloescht")
        return zeilen
    gesamt = 0
    for name, beschreibung in aufraeum_schritte():
        if trocken:
            zeilen.append(f"  wuerde: {beschreibung}")
            continue
        frei_bytes = _schritt_ausfuehren(name, basis, darf_loeschen=True)
        if frei_bytes is None:
            zeilen.append(f"  {beschreibung}: uebersprungen")
            continue
        gesamt += frei_bytes
        zeilen.append(f"  {beschreibung}: {frei_bytes / 1024**3:.2f} GB")
    if not trocken:
        danach = frei_gb("C:")
        zeilen.append(f"  freigegeben: {gesamt / 1024**3:.2f} GB - C: jetzt {danach} GB frei")
    return zeilen


def messen() -> dict:
    stand: dict = {"zeit": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")}
    for laufwerk, schluessel in LAUFWERKE.items():
        stand[schluessel] = frei_gb(laufwerk)
    stand["laufwerke"] = {lw: frei_gb(lw) for lw in LAUFWERKE}

    cache_summe, cache_teile = 0, {}
    basis = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local")))
    for name in CACHE_ORDNER:
        wert = groesse(basis / name, 20.0 if name != "pnpm" else 60.0)
        cache_teile[name] = None if wert is None else round(wert / 1024**2)
        if wert is not None:
            cache_summe += wert
    stand["caches_mb"] = cache_teile
    stand["caches_gb"] = round(cache_summe / 1024**3, 2)

    muell_summe, muell_teile = 0, {}
    for name in MUELL_ORDNER:
        wert = groesse(basis / name, 30.0)
        muell_teile[name] = None if wert is None else round(wert / 1024**2)
        if wert is not None:
            muell_summe += wert
    stand["muell_mb"] = muell_teile
    stand["muell_gb"] = round(muell_summe / 1024**3, 2)

    logs = logdateien()
    stand["log_groesste_mb"] = round(logs[0][0], 1) if logs else 0.0
    stand["log_groesste"] = logs[0][1] if logs else None
    stand["log_top"] = [(round(m, 1), n) for m, n in logs[:5]]
    stand["log_gesamt_mb"] = round(sum(m for m, _ in logs), 1)

    stand["backups_gb"] = round(
        (groesse(WURZEL / "Agenten" / "_Backups", 60.0) or 0) / 1024**3, 2)
    stand["index_lock"] = index_lock()
    return stand


def befund(stand: dict) -> list[str]:
    zeilen = []
    c = stand.get("frei_c_gb")
    if c is not None and c < SCHWELLEN["frei_c_gb"]:
        zeilen.append(f"C: nur noch {c} GB frei (Schwelle {SCHWELLEN['frei_c_gb']} GB)")
    q = stand.get("frei_q_gb")
    if q is not None and q < SCHWELLEN["frei_q_gb"]:
        zeilen.append(f"Q: nur noch {q} GB frei (Ausser-Haus-Kopie, Schwelle {SCHWELLEN['frei_q_gb']} GB)")
    if stand["caches_gb"] >= SCHWELLEN["caches_gb"]:
        teile = ", ".join(f"{k} {v} MB" for k, v in stand["caches_mb"].items() if v)
        un = [k for k, v in stand["caches_mb"].items() if v is None]
        zeilen.append(f"Caches {stand['caches_gb']} GB ({teile}"
                      + (f"; nicht gemessen: {', '.join(un)}" if un else "") + ")")
    if stand["muell_gb"] >= SCHWELLEN["muell_gb"]:
        teile = ", ".join(f"{k} {v} MB" for k, v in stand["muell_mb"].items() if v)
        zeilen.append(f"Muell {stand['muell_gb']} GB ({teile}) - CrashDumps/Temp leeren")
    if stand["log_groesste_mb"] >= SCHWELLEN["log_mb_einzeln"]:
        zeilen.append(f"Logdatei {stand['log_groesste']} {stand['log_groesste_mb']} MB "
                      f"(Schwelle {SCHWELLEN['log_mb_einzeln']} MB)")
    if stand["backups_gb"] >= SCHWELLEN["backups_gb"]:
        zeilen.append(f"Agenten/_Backups {stand['backups_gb']} GB (Notfallkopien pruefen)")
    lock = stand.get("index_lock")
    if lock and lock[0] >= SCHWELLEN["lock_minuten"] and lock[1]:
        zeilen.append(f".git/index.lock ist {int(lock[0])} min alt und kein echter "
                      f"git-Prozess laeuft - umbenennen")
    return zeilen


def tabelle(stand: dict) -> str:
    z = [
        "Platz-Wache - vollstaendige Messung",
        f"Zeit: {stand['zeit']}",
        "Laufwerke frei: " + ", ".join(f"{k} {v} GB" for k, v in stand["laufwerke"].items()),
        "Caches: " + ", ".join(f"{k} {v if v is not None else 'nicht gemessen'} MB"
                               for k, v in stand["caches_mb"].items())
        + f" = {stand['caches_gb']} GB",
        "Muell: " + ", ".join(f"{k} {v if v is not None else 'nicht gemessen'} MB"
                              for k, v in stand["muell_mb"].items())
        + f" = {stand['muell_gb']} GB",
        f"Logs: groesste {stand['log_groesste_mb']} MB ({stand['log_groesste']}), "
        f"zusammen {stand['log_gesamt_mb']} MB",
        f"Agenten/_Backups: {stand['backups_gb']} GB",
        "index.lock: " + ("keine" if not stand["index_lock"]
                          else f"{int(stand['index_lock'][0])} min, echte git-Prozesse: "
                               f"{'keine' if stand['index_lock'][1] else 'laufen'}"),
        "Schwellen: " + ", ".join(f"{k}={v}" for k, v in SCHWELLEN.items()),
    ]
    return "\n".join(z)


def main() -> int:
    immer = "--immer" in sys.argv
    als_json = "--json" in sys.argv
    ohne_aufraeumen = "--ohne-aufraeumen" in sys.argv
    trocken = "--trocken" in sys.argv
    stand = messen()
    reserve_zeilen: list[str] = []
    if not ohne_aufraeumen and not als_json:
        reserve_zeilen = reserve_aufraeumen(stand, trocken=trocken)
        if reserve_zeilen and not trocken:
            stand = messen()          # nach dem Aufraeumen neu messen
    zeilen = reserve_zeilen + befund(stand)
    try:
        ZUSTAND.parent.mkdir(parents=True, exist_ok=True)
        alt = json.loads(ZUSTAND.read_text(encoding="utf-8")) if ZUSTAND.exists() else {}
        ZUSTAND.write_text(json.dumps({"letzte": stand, "davor": alt.get("letzte"),
                                       "letzte_meldung": zeilen,
                                       "gemeldet_am": datetime.now().astimezone().isoformat(timespec="seconds")
                                       if zeilen else alt.get("gemeldet_am")},
                                      ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass  # ein Zustandsfehler darf die Messung nicht verhindern

    if als_json:
        print(json.dumps(stand, ensure_ascii=False, indent=2))
        return 0
    if zeilen:
        print("Platz-Wache: " + str(len(zeilen)) + " Posten ueber Schwelle")
        for z in zeilen:
            print("  - " + z)
        print(tabelle(stand))
    elif immer:
        print(tabelle(stand))
        print("Kein Posten ueber Schwelle.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Bestandsaufnahme fuer einen Sammelauftrag - NUR LESEND.

Klopft die Quellen ab, die in Max' BrainFiles unerledigte Arbeit verraten, und
schreibt am Ende ein Skelett fuer die Uebergabedatei
(`Werkstatt/Austausch/<JJJJ-MM-TT>/<thema>.md`) nach stdout. Es wird nichts
angelegt, nichts geaendert, nichts geloescht - die Datei entsteht erst durch
`write_file` des Agenten, nachdem er die Punkte bewertet hat.

Aufruf ueber das terminal-Werkzeug, aus der Repo-Wurzel:
    python Agenten/Hermes/skills/brainfiles/sammelauftrag/scripts/sammeln.py

Optionen:
    --wurzel PFAD   abweichende Repo-Wurzel (sonst automatisch gesucht)
    --ruhig         nur das Skelett ausgeben
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------- Grundlagen

def wurzel_finden(start: Path) -> Path:
    """Aufwaerts bis zu dem Ordner, der MaxHirn und Agenten enthaelt."""
    p = start.resolve()
    for _ in range(10):
        if (p / "MaxHirn").is_dir() and (p / "Agenten").is_dir():
            return p
        if p.parent == p:
            break
        p = p.parent
    raise SystemExit("Repo-Wurzel nicht gefunden (MaxHirn/ + Agenten/ fehlen) - --wurzel nutzen")


def lauf(cmd, cwd=None, zeit=60):
    """Kommando ausfuehren, Ausgabe als Text. Fehler sind kein Abbruch."""
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           errors="replace", timeout=zeit, shell=False)
        return (r.stdout or "") + (r.stderr or "")
    except Exception as e:                                    # noqa: BLE001
        return "<nicht lesbar: %s>" % e


def kopf(text):
    print("\n=== %s ===" % text)


# -------------------------------------------------------------- Die Quellen

def git_stand(w):
    kopf("Git: uncommittete Arbeit (jeder Treffer ist ein Kandidat)")
    stand = lauf(["git", "status", "--porcelain"], cwd=w).strip()
    print(stand if stand else "(Arbeitsbaum sauber)")
    kopf("Git: letzte Commits")
    print(lauf(["git", "log", "--oneline", "-15"], cwd=w).rstrip())


def routinen_logs(w, tage=14, grenze=40):
    kopf("Routinen-Protokolle: ENDE FEHLER in den letzten %d Tagen" % tage)
    ordner = w / "Agenten" / "Routinen" / "logs"
    grenze_zeit = datetime.now() - timedelta(days=tage)
    treffer = 0
    for datei in sorted(ordner.glob("*.log")) if ordner.is_dir() else []:
        if datetime.fromtimestamp(datei.stat().st_mtime) < grenze_zeit:
            continue
        try:
            for i, zeile in enumerate(datei.read_text(encoding="utf-8", errors="replace").splitlines()):
                if "ENDE FEHLER" in zeile:
                    print("%-42s %s" % (datei.name, zeile.strip()[:150]))
                    treffer += 1
                    if treffer >= grenze:
                        print("   ... (abgeschnitten bei %d)" % grenze)
                        return
        except OSError as e:
            print("%-42s <nicht lesbar: %s>" % (datei.name, e))
    print("(keine Fehlerzeile gefunden)" if not treffer else "")


def cron_auftraege(w):
    kopf("Hermes: geplante Cron-Auftraege")
    p = w / "Agenten" / "Hermes" / "cron" / "jobs.json"
    if not p.is_file():
        print("(keine jobs.json)")
        return
    try:
        daten = json.loads(p.read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError) as e:
        print("<nicht lesbar: %s>" % e)
        return
    auftraege = daten if isinstance(daten, list) else daten.get("jobs", [])
    if not auftraege:
        print("(keine Auftraege)")
    for a in auftraege:
        # FELDNAMEN: last_run_at / next_run_at / state / last_status. Ein
        # a.get("last_run") gibt es nicht - es liefert immer None und liest
        # sich wie "nie gelaufen". Genau dieser Fehlalarm ist am 15.09.2026
        # passiert (der Auftrag war gelaufen, Ergebnis im cron/output/).
        print("- %-34s %-16s %s" % (str(a.get("name") or a.get("job_id"))[:34],
                                    str(a.get("schedule"))[:16],
                                    "pausiert" if a.get("paused") else "aktiv"))
        print("    state=%s  letzter Lauf=%s  Status=%s  naechster=%s"
              % (a.get("state"), a.get("last_run_at") or "(nie gelaufen)",
                 a.get("last_status"), a.get("next_run_at") or "-"))
    aus = w / "Agenten" / "Hermes" / "cron" / "output"
    if aus.is_dir():
        jung = sorted(aus.glob("*.txt"), key=lambda f: f.stat().st_mtime, reverse=True)[:5]
        print("  letzte Ausgaben: %s" % ", ".join(f.name for f in jung))


def routinen_geplant(w):
    kopf("Wissen/Routinen.md: Zeilen mit Status-Wort")
    p = w / "MaxHirn" / "Wissen" / "Routinen.md"
    if not p.is_file():
        print("(nicht gefunden)")
        return
    for zeile in p.read_text(encoding="utf-8", errors="replace").splitlines():
        if any(m in zeile for m in ("vorbereitet", "**geändert**", "**geaendert**",
                                    "gelöscht", "geloescht", "noch nicht eingeplant",
                                    "nicht angelegt")):
            print("  %s" % zeile.strip()[:170])
    print("  (Zeilen mit 'eingeplant' gelten als erledigt; hier stehen nur die unfertigen)")


def aufgaben_windows():
    kopf("Windows-Aufgabenplanung: MaxHirn-*/BrainFiles-*")
    ps = ("Get-ScheduledTask | Where-Object { $_.TaskName -like '*MaxHirn*' -or "
          "$_.TaskName -like '*BrainFiles*' } | ForEach-Object { "
          "$i = $_ | Get-ScheduledTaskInfo; "
          "'{0,-36} {1,-9} {2}' -f $_.TaskName, $_.State, $i.LastTaskResult }")
    print(lauf(["powershell", "-NoProfile", "-Command", ps], zeit=120).rstrip())
    print("  LastTaskResult: 0 = sauber | 267009 = laeuft gerade | 267014 / 1073807364 =")
    print("  Prozess von aussen beendet (typisch fuer Dauerlaeufe beim Herunterfahren) |")
    print("  2147946720 = Aufgabe laeuft schon (IgnoreNew) | 3221225786 = abgebrochen")


def uebergaben(w):
    kopf("Werkstatt/Austausch: was liegt da")
    a = w / "Werkstatt" / "Austausch"
    if not a.is_dir():
        print("(kein Austausch-Ordner)")
        return
    for d in sorted(a.iterdir(), reverse=True)[:5]:
        if d.is_dir():
            inhalt = ", ".join(sorted(f.name for f in d.iterdir())[:6]) or "(leer)"
            print("- %s/  %s" % (d.name, inhalt[:140]))
        else:
            print("- %s" % d.name)
    kopf("Werkstatt/Sitzungen und Werkstatt/Protokolle")
    for name in ("Sitzungen", "Protokolle"):
        o = w / "Werkstatt" / name
        if o.is_dir():
            eintraege = sorted(o.iterdir(), reverse=True)[:6]
            print("- %-12s %s" % (name + ":", ", ".join(e.name for e in eintraege)[:140]))


def fremde_dateien(w, minuten=10):
    kopf("Frisch angefasste Dateien (< %d min) - fremde Sitzung moeglicherweise mittendrin" % minuten)
    grenze = datetime.now() - timedelta(minutes=minuten)
    ps = ("git -C '%s' status --porcelain | ForEach-Object { $p = $_.Substring(3).Trim(); "
          "if (Test-Path $p) { $f = Get-Item $p; "
          "if ($f.LastWriteTime -gt (Get-Date).AddMinutes(-%d)) { "
          "'{0}  {1}' -f $f.LastWriteTime.ToString('HH:mm:ss'), $p } } }" % (w, minuten))
    aus = lauf(["powershell", "-NoProfile", "-Command", ps], zeit=120).rstrip()
    print(aus if aus.strip() else "(keine)")


# --------------------------------------------------------------- Skelett

def skelett(datum):
    kopf("Skelett fuer Werkstatt/Austausch/%s/<thema>.md" % datum)
    print("""---
id: %s-sammelauftrag
title: 'Sammelauftrag <Thema>'
tags: [betrieb, uebergabe]
created: %s
updated: %s
related: []
summary: 'Was offen ist, woran Erledigung zu sehen ist.'
---

# Sammelauftrag <Thema>

Stand %s. Quellen: <git status / Sitzung X / Protokoll Y>.

## Offen

| # | Auftrag | Beleg | Fertig woran zu sehen | Pruefkommando | Weg |
|---|---|---|---|---|---|
| 1 |  |  |  |  | Routine/Auftrag/Entscheidung |

## Nicht aufgenommen (kein Fertig-Kriterium)

- 

## Nicht angefasst

- Fremde Aenderungen im Arbeitsbaum: 
- Laufende Prozesse: 

## Entscheidung von Max noetig

- 
""" % (datum.replace("-", ""), datum, datum, datum))


# ------------------------------------------------------------------ Haupt

def main():
    ap = argparse.ArgumentParser(description="Bestandsaufnahme fuer einen Sammelauftrag (nur lesend)")
    ap.add_argument("--wurzel")
    ap.add_argument("--ruhig", action="store_true", help="nur das Skelett")
    args = ap.parse_args()

    w = Path(args.wurzel).resolve() if args.wurzel else wurzel_finden(Path(__file__).parent)
    datum = datetime.now().strftime("%Y-%m-%d")
    print("# Bestandsaufnahme %s\n# Wurzel: %s" % (datetime.now().strftime("%Y-%m-%d %H:%M"), w))
    print("# Dieses Skript liest nur. Schreiben tut der Agent nach der Bewertung.")

    if not args.ruhig:
        git_stand(w)
        fremde_dateien(w)
        routinen_logs(w)
        aufgaben_windows()
        cron_auftraege(w)
        uebergaben(w)
        routinen_geplant(w)
    skelett(datum)


if __name__ == "__main__":
    main()

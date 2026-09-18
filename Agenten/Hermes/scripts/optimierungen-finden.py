"""Optimierungen finden: welche Routine lahmt, welche Leiche steht noch herum?

Laeuft als geplante Aufgabe (`MaxHirn-Optimierungen-Finden`) und meldet ueber
den Bus. **Leere Ausgabe heisst: nichts zu tun** - dann passiert auch nichts
(Watchdog-Muster wie bus-waechter und omniroute-waechter).

WARUM
-----
Am 16.09.2026 lagen drei Dinge gleichzeitig schief, und keines davon hat
jemand gemeldet:

1. Die Sicherung um 20:00 wurde von aussen beendet (LastTaskResult
   0xC000013A). Im Protokoll steht nur die Kopfzeile - die Ende-Zeile fehlt.
   Ein abgebrochener Lauf sieht in jeder Uebersicht wie ein Ausbleiben aus;
   der Bus kann ihn nicht melden, weil das Ende-Ereignis nie geschrieben wird.
2. Die Zweitkopie lief um 21:08 nach und scheiterte (robocopy-Code 11).
3. Aufgaben sind doppelt oder tot: `DCA-Faelligkeit` und
   `MaxHirn-DCA-Pruefung` tun dasselbe, `Hermes_Gateway` steht deaktiviert
   herum, seit sein Nachfolger laeuft (siehe Routinen.md).

Das ist der Auftrag dieser Routine: die *Routinen selbst* nachmessen - nicht
die Daten, nicht die Hardware. Die Systempruefung (07:00) macht das nicht: sie
sieht eine Aufgabe mit Ergebniscode 3221225786 als "fehlerfrei" an, weil das
fuer sie ein von-aussen-beendeter Lauf ist.

WAS ES TUT (nur lesend)
-----------------------
1. Aufgaben der Aufgabenplanung lesen (Name, State, LastTaskResult, letzter
   Lauf, Aktion) und je Aufgabe das Protokoll aus `Routinen/logs` suchen.
2. Befund A - Lauf ohne Ende: Protokoll des letzten Laufs hat keine
   Ende-Zeile und die Aufgabe laeuft nicht gerade.
3. Befund B - Lauf mit Fehler: letzte Protokollzeile meldet FEHLER
   (Wochenuebersicht der fehlgeschlagenen Laeufe).
4. Befund C - Leiche: Aufgabe ist deaktiviert, oder ihre Aktion zeigt auf
   eine Datei, die es nicht mehr gibt.
5. Befund D - Prozess-Drift: Python-Prozesse je Familie (Hermes, MCP,
   Dauerlauf) mit Speicher, dazu MCP-Server ohne lebenden Elternprozess
   (echte Waisen). Gemeldet wird nur die *Veraenderung* gegenueber dem
   letzten Lauf (`Routinen/logs/optimierungen-finden-state.json`).
6. Nichts aendern, nichts loeschen, nichts starten - nur melden.

Aufruf:
    python Agenten/Hermes/scripts/optimierungen-finden.py
    python Agenten/Hermes/scripts/optimierungen-finden.py --alles
        -> auch ohne Befund die Zahlen zeigen (fuer die Abnahme)
    python Agenten/Hermes/scripts/optimierungen-finden.py --ohne-state
        -> Drift gegen nichts rechnen und den Zustand nicht schreiben
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HIER = Path(__file__).resolve()
WURZEL = HIER.parents[3]                        # Agenten/Hermes/scripts/ -> BrainFiles
LOGS = WURZEL / "Agenten" / "Routinen" / "logs"
STATE = LOGS / "optimierungen-finden-state.json"

# Von aussen beendet - kein Skriptfehler, aber auch kein Ende.
KILL_CODES = {
    3221225786: "0xC000013A von aussen beendet",
    1073807364: "0x40010004 von aussen beendet",
    267014: "0x00041306 von aussen beendet",
    267009: "0x00041301 laeuft gerade",
}

# Aufgabenname -> abweichender Protokollname (Wrapper heisst anders als das Log).
LOG_ALIAS = {"dca-pruefung": "dca"}

# Bewusst stehen gelassene Leichen. `Hermes_Gateway` zeigt auf die Altanlage
# (C:\Hermes) und startet nichts mehr; er ist als Admin registriert und laesst
# sich nur mit Admin-Rechten entfernen (siehe gateway-service\Hermes_Gateway.vbs,
# Wissen\Routinen.md). Jede Woche dieselbe Zeile waere Rauschen - deshalb steht
# er hier, statt gemeldet zu werden.
# `MaxHirn-MoonDev-Agent` ebenso: die alte Einzelaufgabe wurde am 17.09.2026
# ABSICHTLICH stillgelegt, ihr Nachfolger ist `MaxHirn-MoonDev-Dauerlauf`
# (Treiber moondev_dauerlauf.py). Sie liegt nur noch als leiser Beleg herum.
KNOWN_LEICHEN = {"Hermes_Gateway", "MaxHirn-MoonDev-Agent"}

PS = r"""
$t = @(Get-ScheduledTask -ErrorAction SilentlyContinue |
  Where-Object { $_.TaskName -match '^(MaxHirn|BrainFiles|Hermes|DCA)' } |
  ForEach-Object {
    $i = $_ | Get-ScheduledTaskInfo
    $a = (($_.Actions | ForEach-Object { ($_.Execute + ' ' + $_.Arguments) }) -join ' ; ')
    [pscustomobject]@{
      Name   = $_.TaskName
      State  = [string]$_.State
      Code   = [int64]$i.LastTaskResult
      Lauf   = $i.LastRunTime.ToString('yyyy-MM-dd HH:mm:ss')
      Aktion = $a
    }
  })
$p = @(Get-CimInstance Win32_Process |
  Where-Object { $_.Name -like 'python*' } |
  ForEach-Object {
    $c = $_.CommandLine; if (-not $c) { $c = '' }
    [pscustomobject]@{
      Pid = [int]$_.ProcessId
      Pp  = [int]$_.ParentProcessId
      Mb  = [int]($_.WorkingSetSize / 1MB)
      Cmd = $c.Substring(0, [Math]::Min(140, $c.Length))
    }
  })
$lebt = @(Get-CimInstance Win32_Process | Select-Object -ExpandProperty ProcessId)
[pscustomobject]@{ Aufgaben = $t; Prozesse = $p; Lebt = $lebt } |
  ConvertTo-Json -Depth 5 -Compress
"""


def messen():
    """Alle Angaben in einem PowerShell-Aufruf holen (schnell, ein Zutritt)."""
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", PS],
                           capture_output=True, text=True, timeout=180,
                           errors="replace")
    except (OSError, subprocess.SubprocessError) as e:
        return None, "Aufgabenplanung/Prozesse nicht lesbar: %s" % e
    roh = (r.stdout or "").strip()
    if not roh:
        return None, "PowerShell lieferte nichts: %s" % (r.stderr or "").strip()[:200]
    try:
        daten = json.loads(roh)
    except ValueError as e:
        return None, "Antwort nicht lesbar (%s)" % e
    daten["Aufgaben"] = daten.get("Aufgaben") or []
    daten["Prozesse"] = daten.get("Prozesse") or []
    daten["Lebt"] = set(daten.get("Lebt") or [])
    return daten, None


def protokoll_fuer(aufgabe):
    """(Pfad, Text) des Protokolls zum letzten Lauf - oder (None, '').

    Nur die Wrapper, die je Lauf neu schreiben, sind hier brauchbar: sie
    beginnen mit '=== Lauf ... ===' und enden mit einer ENDE-Zeile. Ein
    Dauerlauf-Protokoll (waechst endlos) und ein Bericht (.md) haben keine
    Ende-Zeile - ohne die Kopfzeilen-Bedingung waeren sie Dauerbefunde.
    """
    m = re.search(r"([A-Za-z]:\\[^\"']*?\.ps1)", aufgabe.get("Aktion") or "")
    if not m:
        return None, ""
    stem = Path(m.group(1)).stem
    stem = LOG_ALIAS.get(stem, stem)
    pfad = LOGS / ("%s-letzter-lauf.log" % stem)
    if not pfad.exists():
        return None, ""
    try:
        return pfad, pfad.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return pfad, ""


def zeilen(text):
    """Nicht-leere Zeilen ohne BOM. Die Wrapper schreiben mit `Set-Content
    -Encoding UTF8` und setzen damit ein BOM vor die erste Zeile - ohne das
    Abschneiden erkennt die Kopfzeilen-Pruefung die eigene Kopfzeile nicht."""
    raus = []
    for z in (text or "").splitlines():
        z = z.lstrip("\ufeff \t").rstrip()
        if z:
            raus.append(z)
    return raus


def gruppe(cmd):
    """Prozessfamilie aus der Kommandozeile."""
    if "MCP-Server" in cmd:
        return "MCP-Server"
    if "dauerlauf" in cmd:
        return "Dauerlauf"
    if "hermes_cli" in cmd or "bin\\hermes" in cmd:
        return "Hermes"
    if "unsloth" in cmd:
        return "Unsloth"
    if "Bus\\bus.py" in cmd or "skillsbot" in cmd:
        return "Bus"
    return "sonstige"


def main():
    ap = argparse.ArgumentParser(
        description="Optimierungen finden (lautlos, solange nichts anliegt)")
    ap.add_argument("--alles", action="store_true",
                    help="auch bei leerem Befund die Zahlen zeigen (Abnahme)")
    ap.add_argument("--ohne-state", action="store_true",
                    help="Drift gegen nichts rechnen, Zustand nicht schreiben")
    args = ap.parse_args()

    daten, fehler = messen()
    if daten is None:
        print("Optimierungen finden: %s" % fehler)
        return 1

    befunde = []
    nachgesehen = 0

    # --- A/B: Laeufe ohne Ende, Laeufe mit Fehler -------------------------
    for a in sorted(daten["Aufgaben"], key=lambda x: x["Name"]):
        pfad, text = protokoll_fuer(a)
        if not pfad:
            continue
        zl = zeilen(text)
        if not zl or not zl[0].upper().startswith("=== LAUF"):
            continue
        nachgesehen += 1
        ende = any(z.upper().startswith("ENDE") for z in zl)
        code = int(a.get("Code") or 0)
        if not ende and a["State"] != "Running":
            hinweis = KILL_CODES.get(code, "Ergebniscode %s" % code)
            befunde.append("Lauf ohne Ende: %s, letzter Lauf %s (%s). Protokoll %s "
                           "beginnt \"%s\" und hat keine Ende-Zeile."
                           % (a["Name"], a["Lauf"], hinweis, pfad.name, zl[0][:40]))
        elif ende and "FEHLER" in zl[-1].upper():
            befunde.append("Lauf mit Fehler: %s am %s - \"%s\""
                           % (a["Name"], a["Lauf"], zl[-1][:130]))

    # --- C: Leichen ------------------------------------------------------
    for a in sorted(daten["Aufgaben"], key=lambda x: x["Name"]):
        if a["State"] == "Disabled" and a["Name"] not in KNOWN_LEICHEN:
            befunde.append("Leiche: Aufgabe %s ist deaktiviert, aber noch registriert." % a["Name"])
        for m in re.finditer(r"([A-Za-z]:\\[^\"']*?\.(?:ps1|py))", a.get("Aktion") or ""):
            ziel = Path(m.group(1))
            if not ziel.exists():
                befunde.append("Toter Verweis: Aufgabe %s ruft %s - Datei fehlt."
                               % (a["Name"], m.group(1)))
                break

    # --- D: Prozess-Drift ------------------------------------------------
    proz = daten["Prozesse"]
    lebende_ids = daten["Lebt"]
    familien = {}
    for p in proz:
        f = gruppe(p.get("Cmd") or "")
        e = familien.setdefault(f, {"n": 0, "mb": 0})
        e["n"] += 1
        e["mb"] += int(p.get("Mb") or 0)
    waisen = [p for p in proz
              if "MCP-Server" in (p.get("Cmd") or "") and p.get("Pp") not in lebende_ids]
    gesamt_mb = sum(int(p.get("Mb") or 0) for p in proz)

    # --- E: die Cron-Automatik selbst (zweiter Zutritt) ------------------
    # Ein Waechter darf nicht am selben Mechanismus haengen wie das, was er
    # bewacht. Der Hermes-Cron `automatik-waechter` prueft genau diese Frage,
    # laeuft aber IM Scheduler, den er prueft - faellt der Scheduler aus,
    # schweigt er mit. Diese Windows-Aufgabe ruft dieselbe Pruefung auf, also
    # meldet der Ausfall ueber den anderen Weg. Dieselbe Funktion, kein
    # zweiter Nachbau (der wuerde nur seine eigene Formel pruefen).
    cron_zahl = {}
    try:
        import importlib.util
        _pfad = HIER.parent / "automatik-waechter.py"
        _spec = importlib.util.spec_from_file_location("automatik_waechter", _pfad)
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        cron_befunde, cron_zahl = _mod.befunde_holen()
        befunde.extend(cron_befunde)
    except Exception as e:      # ein Befund darf nie die ganze Runde kosten
        befunde.append("Cron-Automatik nicht pruefbar: %s: %s"
                       % (type(e).__name__, e))

    zahlen = {
        "datum": datetime.now().strftime("%Y-%m-%d"),
        "gesamt_mb": gesamt_mb,
        "gesamt_n": len(proz),
        "familien": {k: v["n"] for k, v in familien.items()},
        "mcp_waisen": len(waisen),
    }

    for p in waisen[:5]:
        befunde.append("Verwaister MCP-Server: PID %s ohne lebenden Elternprozess (%s MB)."
                       % (p.get("Pid"), p.get("Mb")))

    vorher = None
    if not args.ohne_state and STATE.exists():
        try:
            vorher = json.loads(STATE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            vorher = None
    if vorher:
        alt_mb = int(vorher.get("gesamt_mb") or 0)
        alt_n = int(vorher.get("gesamt_n") or 0)
        if alt_mb and gesamt_mb > alt_mb + 500:
            befunde.append("Prozess-Speicher gewachsen: %d MB auf %d MB (%d Prozesse, vorher %d) "
                            "gegenueber %s." % (alt_mb, gesamt_mb, len(proz), alt_n,
                                                vorher.get("datum", "?")))
        elif alt_n and len(proz) > alt_n + 10:
            befunde.append("Prozess-Zahl gewachsen: %d auf %d (Speicher %d MB). "
                            "Gegenueber %s." % (alt_n, len(proz), gesamt_mb,
                                                vorher.get("datum", "?")))
    if not args.ohne_state:
        try:
            STATE.write_text(json.dumps(zahlen, ensure_ascii=False, indent=1),
                             encoding="utf-8", newline="")
        except OSError:
            pass

    if not befunde:
        if args.alles:
            print("Optimierungen finden: kein Befund. %d Aufgaben mit Protokoll "
                  "nachgesehen, %d Python-Prozesse, %d MB, MCP-Waisen %d, "
                  "Cron-Auftraege %d aktiv / %d geprueft."
                  % (nachgesehen, len(proz), gesamt_mb, len(waisen),
                     cron_zahl.get("aktiv", 0), cron_zahl.get("geprueft", 0)))
        return 0

    print("Optimierungen finden - Befund %s" % datetime.now().strftime("%d.%m.%Y"))
    for b in befunde:
        print("- %s" % b)
    print("Nichts davon ist geaendert worden; entscheiden bleibt Handarbeit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

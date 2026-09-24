"""Wache fuer liegengebliebene Git-Sperren (.git/index.lock).

Laeuft als Hermes-Cron OHNE Modell (`no_agent`): **leere Ausgabe heisst alles
gut**, es wird nichts gesendet (Watchdog-Muster wie bus-waechter.py,
spiegelfrist-wache.py). Gemeldet wird nur, was wirklich klemmt.

WARUM ES DIESEN WÄCHTER GIBT
----------------------------
Eine 0 Byte grosse `.git/index.lock` ohne lebenden Committer ist kein
Betriebsunfall, sondern eine DAUERBRECHSE. Sie faellt nur dort auf, wo jemand
aktiv committen will - und die taegliche Fremdarbeit-Routine
(`Agenten/Routinen/fremdarbeit-einziehen.ps1`, 20:40) bricht bei einer
liegenden Sperre mit **Exitcode 0** und der Zeile `ENDE uebersprungen` ab.
Die Aufgabenplanung meldet damit Erfolg.

Gemessen am 24.09.2026: Skip am 23.09. 20:40 wegen einer verwaisten Sperre,
danach lagen 44 Dateien bis zu 44 h im Arbeitsbaum; ein Handlauf holte 51
ruhende Dateien in 64 s. Im `.git/` hatten sich 22 umbenannte Sperren
angesammelt - jede war einmal ein stiller Ausfall.

DIESER WÄCHTER PRUEFT DREI DINGE
--------------------------------
1. Liegt eine `index.lock` aelter als FRIST_MIN (Standard 10)?
2. Sagt das letzte Log der Fremdarbeit-Routine `uebersprungen`?
   (Das ist die FOLGE der Sperre - und die Zeile wird bei jedem Lauf
   ueberschrieben, also nur hier sichtbar.)
3. Waechst die Zahl der weggeraeumten Sperren (`index.lock.verwaist-*`)?
   Gemeldet wird nur der ZUWACHS, nicht der Bestand.

WAS ES NICHT TUT
----------------
Es raeumt NICHTS weg und committet nichts. Eine Sperre umzubenennen ist ein
Eingriff in fremde Arbeit - das entscheidet ein Mensch oder eine Sitzung mit
Kontext (Regel: nur umbenennen, nie loeschen). Der Waechter meldet nur.

Aufruf:
    python Agenten/Hermes/scripts/sperren-wache.py              # echter Waechter
    python Agenten/Hermes/scripts/sperren-wache.py --alle       # auch den geprueften Umfang
    python Agenten/Hermes/scripts/sperren-wache.py --frist 0    # Alarmrichtung pruefen
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve()
WURZEL = HIER.parents[3]                      # Agenten/Hermes/scripts/ -> BrainFiles
MERKDATEI = WURZEL / "Agenten" / "Hermes" / "cache" / "sperren-wache.json"
FREMDARBEIT_LOG = (WURZEL / "Agenten" / "Routinen" / "logs"
                   / "fremdarbeit-letzter-lauf.log")

# Beobachtete Repositories. BrainFiles ist das Haupt-Repo; nautilus ist ein
# EIGENES Repo im Baum (dort bricht ein liegengebliebener Index genauso).
REPOS = [WURZEL, WURZEL / "Agenten" / "Handel" / "nautilus"]

FRIST_MIN = 10.0
WIEDERHOLUNG_STUNDEN = 6.0
VERWAIST_MUSTER = "index.lock.verwaist-"


def alter_minuten(pfad):
    """Alter in Minuten, oder None wenn nicht messbar."""
    try:
        return (time.time() - os.path.getmtime(pfad)) / 60.0
    except OSError:
        return None


def echte_git_prozesse():
    """Zahl der `git.exe` OHNE `fsmonitor` - oder None, wenn nicht messbar.

    Die blosse ZAHL der `git.exe` ist kein Kriterium: `git fsmonitor--daemon`
    laeuft dauerhaft und beweist keine parallele Sitzung. Erst der Filter auf
    die Kommandozeile trennt echte Committer von Dauerlaeufern.
    """
    befehl = (
        "Get-CimInstance Win32_Process -Filter \"Name='git.exe'\" | "
        "Where-Object { $_.CommandLine -notlike '*fsmonitor*' } | "
        "Measure-Object | Select-Object -ExpandProperty Count"
    )
    for exe in ("powershell", "pwsh"):
        try:
            aus = subprocess.run([exe, "-NoProfile", "-Command", befehl],
                                 capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.SubprocessError):
            continue
        if aus.returncode != 0:
            continue
        text = (aus.stdout or "").strip().splitlines()
        if text:
            try:
                return int(text[-1].strip())
            except ValueError:
                continue
    return None


def sperren_in(repo):
    """(aktive Sperren, Zahl der weggeraeumten Sperren) fuer EIN Repo."""
    git = Path(repo) / ".git"
    if not git.is_dir():
        return [], 0
    aktiv = []
    sperre = git / "index.lock"
    if sperre.exists():
        aktiv.append(sperre)
    weg = 0
    try:
        for name in os.listdir(git):
            if name.startswith(VERWAIST_MUSTER):
                weg += 1
    except OSError:
        pass
    return aktiv, weg


def befund(repos=None, frist=FRIST_MIN, prozesse="unbekannt"):
    """Zeilen, die gemeldet werden muessen. Leere Liste = alles gut.

    Rueckgabe: (zeilen, geprueft, verwaist_gesamt)
    """
    repos = REPOS if repos is None else repos
    zeilen = []
    geprueft = 0
    verwaist_gesamt = 0
    for repo in repos:
        aktiv, weg = sperren_in(repo)
        verwaist_gesamt += weg
        if not (Path(repo) / ".git").is_dir():
            continue
        geprueft += 1
        for sperre in aktiv:
            alter = alter_minuten(sperre)
            if alter is None or alter < frist:
                continue
            groesse = 0
            try:
                groesse = os.path.getsize(sperre)
            except OSError:
                pass
            hinweis = ""
            if prozesse == 0:
                hinweis = " (kein echter git-Prozess)"
            elif isinstance(prozesse, int) and prozesse > 0:
                hinweis = " (%d git-Prozess(e) ohne fsmonitor laufen)" % prozesse
            zeilen.append(
                "%s: .git/index.lock liegt seit %.0f min (%d Byte)%s"
                % (Path(repo).name, alter, groesse, hinweis))
    return zeilen, geprueft, verwaist_gesamt


def skip_zeile(log=None):
    """Letzte ENDE-Zeile der Fremdarbeit-Routine, wenn sie uebersprungen hat.

    Das Log wird bei JEDEM Lauf ueberschrieben - ein Skip ist nur bis zum
    naechsten Lauf sichtbar. Genau deshalb wird er hier mitgelesen.

    Der Pfad wird zur LAUFZEIT aus dem Modul gelesen, nicht als Default-Argument
    gebunden: ein Default wird beim Laden des Moduls ausgewertet und liesse sich
    von einem Test nicht mehr umbiegen (drei Tests liefen deshalb ins Leere).
    """
    if log is None:
        log = FREMDARBEIT_LOG
    try:
        with open(log, encoding="utf-8", errors="replace") as f:
            zeilen = [z.strip() for z in f if z.strip()]
    except OSError:
        return None
    for z in reversed(zeilen):
        if "ENDE uebersprungen" in z:
            return z
        if z.startswith("ENDE"):
            return None                      # letzter Lauf war in Ordnung
    return None


def _merker():
    try:
        with open(MERKDATEI, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _merke(stand):
    try:
        MERKDATEI.parent.mkdir(parents=True, exist_ok=True)
        with open(MERKDATEI, "w", encoding="utf-8", newline="\n") as f:
            json.dump(stand, f, ensure_ascii=False, indent=1, sort_keys=True)
    except OSError:
        pass                                  # Merken ist Komfort


def entdopple(zeilen, merker, stunden=WIEDERHOLUNG_STUNDEN):
    """Weg, was innerhalb der Frist schon gemeldet wurde. (zu_melden, neu).

    Schluessel ist der Text VOR dem Doppelpunkt (Repo bzw. Herkunft), damit
    ein wachsender Rueckstand dieselbe Feststellung bleibt statt mit jeder
    Minute eine neue Meldung zu werden.
    """
    jetzt = datetime.now(timezone.utc)
    neu, zu = {}, []
    for z in zeilen:
        schluessel = z.split(":")[0]
        alt = merker.get(schluessel)
        faellig = True
        if alt:
            try:
                t = datetime.fromisoformat(alt)
                if t.tzinfo is None:
                    t = t.replace(tzinfo=timezone.utc)
                faellig = (jetzt - t).total_seconds() >= stunden * 3600
            except ValueError:
                faellig = True
        neu[schluessel] = jetzt.isoformat(timespec="seconds") if faellig else alt
        if faellig:
            zu.append(z)
    for schluessel, t in list(neu.items()):
        try:
            ti = datetime.fromisoformat(t)
            if ti.tzinfo is None:
                ti = ti.replace(tzinfo=timezone.utc)
            if (jetzt - ti).days > 7:
                del neu[schluessel]
        except (ValueError, TypeError):
            del neu[schluessel]
    return zu, neu


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--frist", type=float, default=FRIST_MIN,
                   help="Minuten, die eine Sperre alt sein muss "
                        "(0 = alles melden, Alarmrichtung pruefen)")
    p.add_argument("--alle", action="store_true",
                   help="auch den geprueften Umfang nennen")
    p.add_argument("--ohne-prozesse", action="store_true",
                   help="Prozessabfrage ueberspringen (fuer Tests)")
    a = p.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    prozesse = "unbekannt" if a.ohne_prozesse else echte_git_prozesse()
    zeilen, geprueft, verwaist = befund(frist=a.frist, prozesse=prozesse)

    skip = skip_zeile()
    if skip:
        zeilen.append("Fremdarbeit: " + skip)

    merker = _merker()
    vorher = merker.get("_verwaist_gesamt")
    if isinstance(vorher, int) and verwaist > vorher:
        zeilen.append("Sperren: %d neue weggeraeumte Sperre(n) "
                      "(index.lock.verwaist-*), Bestand %d"
                      % (verwaist - vorher, verwaist))
    merker["_verwaist_gesamt"] = verwaist

    if zeilen:
        zu_melden, neuer_merker = entdopple(zeilen, merker)
        neuer_merker["_verwaist_gesamt"] = verwaist
        _merke(neuer_merker)
    else:
        zu_melden = []
        _merke(merker)

    if zu_melden:
        print("Git-Sperre klemmt:")
        for z in zu_melden:
            print("  " + z)
        print("Eine verwaiste Sperre umbenennen (nie loeschen), danach die "
              "Fremdarbeit-Routine von Hand nachziehen.")
    elif a.alle:
        print("%d Repository(s) geprueft, keine klemende Sperre "
              "(%d weggeraeumte Sperren im Bestand)"
              % (geprueft, verwaist))
    return 0


if __name__ == "__main__":
    sys.exit(main())

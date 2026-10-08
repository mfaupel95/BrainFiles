#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GBrain-Maintenance-Waechter (Routine gbrain-maintenance-2e8fa54d-6f9f-4726-89e9-caf8a624b61a).

Laeuft als Hermes-Cron OHNE Modell (`no_agent`): **leere Ausgabe heisst alles
gut** und es wird nichts gesendet (Watchdog-Muster). Ausgabe gibt es nur, wenn
der GBrain-Doctor einen echten Fehler meldet, der Launcher nicht erreichbar
ist, oder der Faktbestand gefallen ist.

WARUM
-----
Die maintenance.md der Installation verlangt genau EINE native Routine mit der
Routine-ID oben, die `doctor --fast --json` faehrt und Fehler meldet. Bezahlte
Embedding-/Extraction-Wartung bleibt ein separater Nutzerentscheid - dieser
Waechter startet NIE serve/cron/daemon und ruft keine bezahlten Pfade auf.

DIE FAKTENZAHL IST DER EIGENTLICHE WAECHTER (gemessen 08.10.2026)
-----------------------------------------------------------------
`gbrain stats` und `gbrain list` zaehlen SEITEN, nicht Fakten. Ein Gehirn, das
nur ueber die Memory-Verben gefuellt wurde, meldet dort **0**, obwohl der
Bestand da ist (gemessen: 0 Seiten gegen 44 aktive Fakten, ids bis #51). Wer
sich auf `stats` verlaesst, sieht einen Verlust nicht - und `gbrain doctor`
empfiehlt bei genau diesem Bestand `gbrain reinit-pglite`, was laut eigener
Ausgabe *"drops every embedding in your brain"* bedeutet und die Fakten
mitnimmt.

Deshalb prueft diese Wache DREI Dinge:

1. `doctor --fast --json` - wie von der Installation verlangt.
2. `recall` - die Zahl der AKTIVEN FAKTEN gegen die Merkdatei
   `gbrain-wache-stand.json` neben diesem Skript. Faellt die Zahl, wird
   gemeldet und zusaetzlich der volle Doctor gefahren, damit die Meldung die
   Ursache gleich mitliefert. Wachsen ist kein Befund.
3. Einen Tripwire: nennt die Doctor-Ausgabe einen LOESCHENDEN Befehl
   (`reinit`, `wipe`, `drop table`, `truncate`), wird gewarnt - VOR der
   Ausfuehrung, nicht danach.

WAS ES TUT
----------
1. `wsl.exe -d archlinux /workspace/gbrain/bin/gbrain doctor --fast --json`
   ueber den absoluten Launcher (derselbe Weg wie jede Memory-Operation).
2. Launcher nicht erreichbar (wsl.exe fehlt, Distro weg, Exit != 0): Befund
   ausgeben.
3. Doctor-Status ist "error"/"fail" oder ein Check ist nicht ok: die
   fehlgeschlagenen Checks ausgeben.
4. Faktbestand aus `recall` zaehlen und mit der Merkdatei vergleichen.
5. Nur Warnungen (status "warnings", health_score hoch, keine error-Checks):
   schweigen - Warnungen wie "serve IPC socket not present" sind bei einer
   reinen CLI-Installation der Normalfall und kein Fehler.

Aufruf:
    python Agenten/Hermes/scripts/gbrain-maintenance-wache.py
    python Agenten/Hermes/scripts/gbrain-maintenance-wache.py --stand-zeigen
    python Agenten/Hermes/scripts/gbrain-maintenance-wache.py --stand-setzen
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LAUNCHER = ["wsl.exe", "-d", "archlinux", "/workspace/gbrain/bin/gbrain"]
ROUTINE_ID = "gbrain-maintenance-2e8fa54d-6f9f-4726-89e9-caf8a624b61a"

HIER = Path(__file__).resolve().parent
STAND = HIER / "gbrain-wache-stand.json"

# Ein Befund dieser Woerter in einer Doctor-Ausgabe ist eine Vorwarnung, keine
# Diagnose: `reinit-pglite` loescht den Bestand, die anderen sind Loeschwege.
LOESCHENDE_WOERTER = ("reinit", "wipe", "drop table", "truncate")

# Der Bestand schwankt im Betrieb: Sitzungen schreiben Fakten UND nehmen welche
# zurueck (`forget`). Gemessen 08.10.2026: 46 -> 41 innerhalb einer Stunde, ohne
# jeden Verlust - alles gewollte Ruecknahmen. Erst ein Rueckgang ueber diese
# Schwelle ist ein Befund; darunter wird der Stand nur nachgefuehrt.
RUECKGANG_SCHWELLE = 3


def lauf(argumente, frist=180):
    """Faehrt den Launcher; liefert (rc, stdout, stderr). rc=-1 = nicht erreichbar."""
    try:
        p = subprocess.run(LAUNCHER + argumente, capture_output=True, text=True,
                           timeout=frist)
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return -1, "", "wsl.exe nicht gefunden (WSL2 fehlt?)"
    except subprocess.TimeoutExpired:
        return -1, "", "Aufruf ueberschritt %d s: %s" % (frist, " ".join(argumente))


def doctor_fast():
    """Faehrt doctor --fast --json; liefert (rc, stdout, stderr)."""
    return lauf(["doctor", "--fast", "--json"], frist=120)


def fakten_zaehlen():
    """Zahl der AKTIVEN Fakten aus `recall`, oder None wenn nicht lesbar.

    Bewusst NICHT `stats`: das zaehlt Seiten und meldet bei einem reinen
    Faktengehirn 0 (gemessen 08.10.2026).
    """
    rc, out, _ = lauf(["recall"], frist=180)
    if rc != 0:
        return None
    return sum(1 for z in out.splitlines() if "id=" in z and "(fact" in z)


def stand_lesen():
    if STAND.exists():
        try:
            return json.loads(STAND.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def stand_schreiben(fakten, hoechste=None):
    """Merkdatei fortschreiben.

    `fakten` ist der letzte Stand, `hoechste` der bisher hoechste - der bleibt
    stehen, auch wenn der Bestand durch gewollte Ruecknahmen sinkt. Gemeldet
    wird gegen den Hoechststand, damit ein schleichender Verlust nicht durch
    normales Auf und Ab verdeckt wird.
    """
    alt = stand_lesen()
    if hoechste is None:
        hoechste = max(fakten, int(alt.get("hoechste", 0) or 0))
    STAND.write_text(json.dumps({
        "schema": 1,
        "stand": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fakten": fakten,
        "hoechste": hoechste,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def volle_ursachen():
    """Nur im Fehlerfall: der volle Doctor liefert die Begruendung mit."""
    rc, out, _ = lauf(["doctor", "--json"], frist=180)
    if rc not in (0, 1):
        return []
    try:
        d = json.loads(out)
    except json.JSONDecodeError:
        return []
    zeilen = []
    for i in d.get("top_issues", []):
        if i.get("status") in ("fail", "error"):
            zeilen.append("  - %s: %s" % (i.get("name"), str(i.get("fix", ""))[:300]))
    return zeilen


def main():
    if "--stand-zeigen" in sys.argv:
        stand = stand_lesen()
        print("Merkdatei: %s" % STAND)
        print("  dort: %s Fakten (Stand %s)" % (stand.get("fakten", "?"),
                                                stand.get("stand", "?")))
        print("  jetzt gezaehlt: %s Fakten" % fakten_zaehlen())
        return

    if "--stand-setzen" in sys.argv:
        fakten = fakten_zaehlen()
        if fakten is None:
            print("GBrain-Maintenance: recall nicht lesbar - Merkdatei NICHT gesetzt.")
            return
        stand_schreiben(fakten)
        print("Merkdatei gesetzt: %d Fakten." % fakten)
        return

    meldungen = []

    # --- 1. Doctor, wie von der Installation verlangt ---------------------
    rc, out, err = doctor_fast()
    if rc == -1:
        meldungen.append("GBrain-Maintenance: Launcher nicht erreichbar - %s" % err)
    elif rc != 0:
        meldungen.append("GBrain-Maintenance: doctor --fast Exit %s\nstderr: %s\nstdout: %s"
                         % (rc, err.strip(), out.strip()[:2000]))
    else:
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            meldungen.append("GBrain-Maintenance: doctor --fast lieferte kein JSON\n%s"
                             % out.strip()[:2000])
            data = {}
        if data.get("status") in ("error", "fail"):
            bad = [c for c in data.get("checks", [])
                   if c.get("status") in ("error", "fail")]
            lines = ["GBrain-Maintenance: Doctor-Status %s" % data.get("status")]
            for c in bad:
                lines.append("- %s: %s" % (c.get("name"), str(c.get("message", ""))[:300]))
            if not bad:
                lines.append("- (kein Check als error/fail markiert; top_issues: %s)"
                             % json.dumps(data.get("top_issues", []),
                                          ensure_ascii=False)[:500])
            meldungen.append("\n".join(lines))

        # --- 3. Tripwire: loeschende Befehle in der Ausgabe ---------------
        klein = out.lower()
        treffer = [w for w in LOESCHENDE_WOERTER if w in klein]
        if treffer:
            meldungen.append(
                "GBrain-Maintenance: die Doctor-Ausgabe nennt einen LOESCHENDEN Befehl "
                "(%s).\nNICHT ausfuehren, solange Fakten im Gehirn liegen: "
                "`reinit-pglite` loescht den Bestand\n(\"Wiping dims is destructive: it "
                "drops every embedding in your brain\").\nErst `gbrain recall` zaehlen, "
                "dann `gbrain backup create --output <pfad>`." % ", ".join(treffer))

    # --- 2. Der eigentliche Waechter: die Faktenzahl ----------------------
    fakten = fakten_zaehlen()
    alt = stand_lesen()
    hoechste = int(alt.get("hoechste", 0) or 0) or None

    if fakten is None:
        meldungen.append("GBrain-Maintenance: `recall` nicht lesbar - Faktbestand "
                         "unkontrolliert. Launcher und Distro pruefen.")
    elif hoechste is None:
        stand_schreiben(fakten, fakten)   # erster Lauf: nur merken, nicht melden
    elif fakten < hoechste - RUECKGANG_SCHWELLE:
        lines = ["GBrain-Maintenance: FAKTBESTAND GEFALLEN - Hoechststand %d, jetzt %d "
                 "(-%d, Schwelle %d)." % (hoechste, fakten, hoechste - fakten,
                                          RUECKGANG_SCHWELLE),
                 "Gezaehlt ueber `recall`; `stats`/`list` zaehlen Seiten und zeigen "
                 "hier 0 - darauf ist kein Verlass."]
        ursachen = volle_ursachen()
        if ursachen:
            lines.append("Befunde des vollen Doctors:")
            lines.extend(ursachen)
        lines.append("Erst pruefen, was die Fakten verloren hat - vor jedem "
                     "`reinit-pglite`/`init`/`migrate` eine Sicherung fahren.")
        meldungen.append("\n".join(lines))
        stand_schreiben(fakten, fakten)   # nach der Meldung neu messen
    else:
        # Kleiner Rueckgang (gewollte `forget`s) oder Wachstum: nur nachfuehren.
        stand_schreiben(fakten, max(fakten, hoechste))

    if meldungen:
        print("\n\n".join(meldungen))


if __name__ == "__main__":
    main()
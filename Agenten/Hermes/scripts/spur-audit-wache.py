#!/usr/bin/env python
"""Cron-Wache fuer den Spur-Audit (T-322, Auftrag Max 03.10.2026).

Aufruf: spur_audit.py --nur-befund, Ausgabe auf stdout. Das Skript meldet
NUR, was sich gegen den letzten Lauf geaendert hat, und schweigt sonst -
eine Wache, die bei jedem Lauf dieselbe Zahl wiederholt, wird abgeschaltet
und damit blind (das ist im Haus mehrfach passiert).

Grund fuer den Aufrufer: bis zum 03.10.2026 gab es kein Werkzeug, das die
Fehlerklasse "schoene Zahlen aus einem Rechenfehler" von selbst findet. Der
Scanner galt mit +17,49 % und t = 15,42 als beste Spur des Hauses; das war
ein uebernommener Einstiegspreis auf einem 87/161-Einzelinstrument.

Was diese Wache NICHT tut: sie aendert nichts. Sie meldet. Eine Spur, deren
Statistik nicht echt ist, wird nicht stillgelegt - das ist eine Entscheidung
von Max, keine des Werkzeugs.
"""
import json
import os
import subprocess
import sys
from datetime import datetime

HIER = os.path.dirname(os.path.abspath(__file__))
WURZEL = os.path.abspath(os.path.join(HIER, "..", "..", ".."))
HANDEL = os.path.join(WURZEL, "Agenten", "Handel")
AUDIT = os.path.join(HANDEL, "spur_audit.py")
VENV = os.path.join(HANDEL, "scanner", ".venv", "Scripts", "python.exe")
# Die Merksdatei gehoert nach Agenten/Hermes/cache, nicht in einen 'cache'
# UNTER scripts. Dort liegen 59 Merksdateien der uebrigen Wachen; ein zweiter
# Cache-Ordner im Skriptordner verteilt den Stand des Hauses auf zwei Orte -
# und wird beim Aufraeumen mitgenommen, ohne dass jemand ihn erwartet.
MERK = os.path.join(os.path.dirname(HIER), "cache", "spur-audit-wache.json")
STUNDE_S = 6 * 3600


def lesen():
    try:
        with open(MERK, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def schreiben(daten):
    os.makedirs(os.path.dirname(MERK), exist_ok=True)
    with open(MERK, "w", encoding="utf-8") as fh:
        json.dump(daten, fh, ensure_ascii=False, indent=2)


def main():
    if not os.path.isfile(AUDIT) or not os.path.isfile(VENV):
        print("spur_audit.py oder der venv fehlt - Wache schweigt")
        return 0
    env = dict(os.environ)
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)
    try:
        p = subprocess.run([VENV, AUDIT, "--nur-befund"],
                           cwd=HANDEL, capture_output=True, text=True,
                           timeout=600, env=env)
    except subprocess.TimeoutExpired:
        print("Spur-Audit laeuft nach 600 s nicht durch - Wache schweigt")
        return 0
    if p.returncode != 0:
        # Ein Fehler des Werkzeugs ist selbst ein Befund - aber nur, wenn er
        # sich wiederholt, sonst schreit die Wache bei jedem Stoerungsfenster.
        alt = lesen()
        if alt.get("fehler") == (p.stderr or "")[-300:]:
            return 0
        schreiben({"fehler": (p.stderr or "")[-300:], "zeit": datetime.now().isoformat()})
        print("Spur-Audit abgebrochen: %s" % (p.stderr or "").strip()[-200:])
        return 0

    ausgabe = (p.stdout or "").strip()
    alt = lesen()
    if not ausgabe:
        return 0
    if ausgabe == alt.get("ausgabe"):
        return 0
    alt_seit = alt.get("zeit")
    schreiben({"ausgabe": ausgabe, "zeit": datetime.now().isoformat()})
    zeilen = ["*Spur-Audit: Befundlage geaendert*" + ("" if not alt_seit else
             " (zuletzt %s)" % alt_seit[:16])]
    zeilen.append("```")
    zeilen.append(ausgabe[:2500])
    zeilen.append("```")
    print("\n".join(zeilen))
    return 0


if __name__ == "__main__":
    sys.exit(main())

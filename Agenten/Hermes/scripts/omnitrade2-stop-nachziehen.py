# -*- coding: utf-8 -*-
"""Cron-Einstieg: Schutz-Stop des omnitrade2-XPERP-Laufs an der Boerse nachziehen.

Der Kern liegt in Agenten/Handel/omnitrade2/nachziehen.py (eine Quelle fuer
Position, Deckung, Stop-Regeln und das einmalige Hochziehen von 1 auf 19
Kontrakte). Dieses Skript ist nur der Cron-Mantel.

Muster: LEERE Ausgabe = nichts zu melden (dann sendet der Cron nichts).
Gemeldet wird nur, wenn etwas GETAN wurde oder ein Fehler vorliegt - sonst
waere die Wache ein Dauerregen und wuerde abgeschaltet.
Exitcode 2 bei Fehler: ein Pruef- oder Schreibfehler darf nie still bleiben.
"""

import importlib.util
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
KERN = os.path.normpath(
    os.path.join(HIER, "..", "..", "Handel", "omnitrade2", "nachziehen.py")
)


def kern_laden():
    spec = importlib.util.spec_from_file_location("omnitrade2_nachziehen_cron", KERN)
    modul = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modul
    spec.loader.exec_module(modul)
    return modul


def haupt():
    if not os.path.exists(KERN):
        print("omnitrade2-Nachzieher FEHLT: %s" % KERN)
        return 2
    modul = kern_laden()
    erg = modul.lauf(anwenden=True)

    if erg.get("fehler"):
        print("omnitrade2-Nachzieher FEHLER (%s): %s" % (erg.get("inst"), erg["fehler"]))
        for zeile in erg.get("handlung", []):
            print("  - " + zeile)
        return 2

    getan = [z for z in erg.get("handlung", [])
             if z.startswith(("Luecke", "Hochziehen", "Loop PID", "Start:", "NACHKONTROLLE"))]
    if not getan:
        return 0
    print("omnitrade2-Nachzieher (%s, phase %s):" % (erg.get("inst"), erg.get("phase")))
    for zeile in getan:
        print("  - " + zeile)
    return 0


if __name__ == "__main__":
    sys.exit(haupt())

"""Cron-Wache: offene Freigabe-Belege ausfuehren (die Hand im Betrieb).

Ruft `Agenten/Handel/beleg_hand.py --anwenden` mit dem Haus-venv auf. Nur wenn
wirklich etwas ausgefuehrt wurde, entsteht eine Zeile - leere Ausgabe heisst
"nichts zu senden" (Hausmuster fuer no_agent-Crons).

Warum als Wache und nicht im Dauerlauf: der Dauerlauf startet die Spuren, die
Hand ist aber kein Spur-Lauf. Sie muss auch dann nachsehen, wenn eine Spur
gerade keinen Zyklus faehrt (z. B. weil ihr Zeitfenster erst spaeter passt) -
der Beleg gilt 180 s, danach ist er verfallen.
"""
from __future__ import annotations

import os
import subprocess
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.abspath(os.path.join(HIER, os.pardir, os.pardir, "Handel"))
PY = os.path.join(HANDEL, "scanner", ".venv", "Scripts", "python.exe")


def main() -> int:
    umgebung = dict(os.environ)
    umgebung.pop("PYTHONHOME", None)     # Hausfalle: uv-venv vererbt PYTHONHOME
    umgebung.pop("PYTHONPATH", None)
    umgebung["MAXHIRN_ROUTINE"] = "1"    # kein Bildschirm, keine Rueckfrage
    try:
        p = subprocess.run([PY, os.path.join(HANDEL, "beleg_hand.py"), "--anwenden"],
                           cwd=HANDEL, capture_output=True, text=True, timeout=180,
                           env=umgebung)
    except Exception as e:                                            # noqa: BLE001
        print("beleg-hand: Start fehlgeschlagen: %s" % e)
        return 1
    ausgabe = (p.stdout or "").strip()
    if "keine offenen Belege" in ausgabe and "VERFALLEN" not in ausgabe:
        return 0                        # leise: nichts zu tun
    if "wuerde kaufen" in ausgabe:
        print("beleg-hand meldet im Vorschau-Modus (sollte nicht vorkommen):\n%s" % ausgabe)
        return 1
    if p.returncode != 0:
        print("beleg-hand endete mit Code %s:\n%s\n%s"
              % (p.returncode, ausgabe, (p.stderr or "").strip()[:800]))
        return 1
    if "VERFALLEN" in ausgabe and "ausgefuehrt" not in ausgabe:
        # Belege, die an der Frist gestorben sind (T-283) - kein Schaden, aber
        # eine beschlossene Order, die niemand ausgefuehrt hat. Genau einmal
        # gemeldet (`merke_verfallen`), deshalb hier keine Wiederholung noetig.
        print("beleg-hand: Beleg(e) verfallen:\n%s" % ausgabe)
        return 0
    print("beleg-hand hat ausgefuehrt:\n%s" % ausgabe)
    return 0


if __name__ == "__main__":
    sys.exit(main())
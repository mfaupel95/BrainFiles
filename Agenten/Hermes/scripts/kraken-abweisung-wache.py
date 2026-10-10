"""Cron-Wache: weist Kraken unsere signierten Aufrufe ab?

Ruft die Sonde `Agenten/Handel/kraken_abweisungs_sonde.py --wache` als eigenen
Prozess (Host-Python) und reicht deren Ausgabe unveraendert weiter.

Leere Ausgabe = nichts zu senden (Hausmuster fuer no_agent-Crons).

Warum eine Wache und nicht nur die Sonde (T-073, 25.09.2026): der Ausfall
zwischen ~00:29 und ~01:33 blieb unbemerkt, weil im Haus NIEMAND nachfragt -
die Spuren liefen im Papier weiter und meldeten "ok", waehrend jeder signierte
Aufruf abgewiesen wurde. Ein Nachweis ist keine Wache: er muss von selbst
laufen. Die Sonde haelt im Fehlerfall Status, Header und Rohantwort fest; diese
Wache entscheidet, ob das eine Nachricht wert ist.

Enthalten die Sonden selbst schon:
  * Kuehlzeit - nach einer Abweisung wird 60 min NICHT wieder geklopft
    (bei einem Konto-Lockout setzt jeder weitere Aufruf den Timer zurueck),
  * Erholungsmeldung - "wieder offen nach X min" ist der Beleg, den T-073
    verlangt hat.
"""

import os
import subprocess
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
WURZEL = os.path.dirname(os.path.dirname(os.path.dirname(HIER)))   # scripts -> Hermes -> Agenten -> Wurzel
SONDE = os.path.join(WURZEL, "Agenten", "Handel", "kraken_abweisungs_sonde.py")


def main():
    if not os.path.exists(SONDE):
        print("Kraken-Abweisungs-Wache: Sonde fehlt (%s)" % SONDE)
        return 1
    umgebung = dict(os.environ)
    # Ein uv-venv setzt PYTHONHOME in die eigene Umgebung; Kinder erben es und
    # sterben beim Start (Hausfalle). Vor dem Aufruf entfernen.
    for name in ("PYTHONHOME", "PYTHONPATH"):
        umgebung.pop(name, None)
    umgebung.setdefault("PYTHONIOENCODING", "utf-8")
    ergebnis = subprocess.run([sys.executable, SONDE, "--wache"],
                                  capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", timeout=180, env=umgebung,
                                  cwd=os.path.dirname(SONDE),
                                  creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    text = (ergebnis.stdout or "").strip()
    if text:
        print(text)
    if ergebnis.returncode not in (0, 1):
        print("Kraken-Abweisungs-Wache: Sonde brach ab (Code %s)\n%s"
              % (ergebnis.returncode, (ergebnis.stderr or "").strip()[:800]))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
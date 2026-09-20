"""Faehrt die Spiegel-Auswertung, sobald sie faellig ist.

Unterschied zu spiegel-arm-ausstiege.py: das Skript MELDET nicht nur,
dass die Auswertung faellig waere - es FUEHRT sie aus und gibt das
Ergebnis zurueck.

Faellig ist die Auswertung, wenn seit dem letzten Lauf mindestens
NEUE_AUSSTIEGE Ausstiege dazugekommen sind. Das ist die einzige
Bedingung, die zaehlt: eine Auswertung auf unveraenderter Datenlage
wiederholt nur ihr eigenes Ergebnis und kostet 90 Sekunden Rechenzeit.

Watchdog-Muster: leere Ausgabe = nichts senden. Das Skript schweigt,
solange nicht genug Neues vorliegt.

Der Stand des letzten Laufs steht in auswertung-stand.json neben diesem
Skript (Ausstiegszahl je Buch). Faellt die Datei weg, laeuft die
Auswertung einmal und legt sie neu an.
"""
import csv
import json
import os
import subprocess
import sys

# Ab wievielen NEUEN Ausstiegen die Auswertung sich lohnt. 25 ist rund
# ein Fuenftel des Hauptbuchs (1133 Ausstiege, Stand 20.09.2026) - darunter
# verschiebt sich keine der Kennzahlen sichtbar.
NEUE_AUSSTIEGE = 25

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.join(HIER, "..", "..", "Handel")
SPIEGEL = os.path.join(HANDEL, "spiegel")
PYTHON = os.path.join(HANDEL, "scanner", ".venv", "Scripts", "python.exe")
STAND = os.path.join(HIER, "auswertung-stand.json")

# Buch -> (Journaldatei, Argumente fuer auswertung.py). Das Hauptbuch
# laeuft ohne --pfad, die Schattenbuecher mit.
BUECHER = {
    "haupt": ("handelsjournal.csv", []),
    "knapp": ("handelsjournal.knapp.csv", ["--pfad", "handelsjournal.knapp.csv"]),
    "weit": ("handelsjournal.weit.csv", ["--pfad", "handelsjournal.weit.csv"]),
}


def ausstiege(datei):
    """Zahl der Ausstiege in einem Spiegel-Journal."""
    pfad = os.path.join(SPIEGEL, datei)
    try:
        with open(pfad, encoding="utf-8") as fh:
            return sum(1 for z in csv.DictReader(fh)
                       if z.get("aktion") == "schliessen")
    except FileNotFoundError:
        return 0


def lade_stand():
    try:
        with open(STAND, encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, ValueError):
        return {}


def schreibe_stand(stand):
    with open(STAND, "w", encoding="utf-8") as fh:
        json.dump(stand, fh, indent=2, ensure_ascii=False)


def fahre_auswertung(args):
    """Ruft auswertung.py und gibt (ok, ausgabe) zurueck."""
    if not os.path.exists(PYTHON):
        return False, "venv fehlt: %s" % PYTHON
    try:
        p = subprocess.run([PYTHON, "auswertung.py"] + args,
                           cwd=SPIEGEL, capture_output=True, text=True,
                           timeout=600)
    except subprocess.TimeoutExpired:
        return False, "Auswertung ueberschritt 600 s"
    if p.returncode != 0:
        return False, (p.stderr or p.stdout or "").strip()[-400:]
    return True, (p.stdout or "").strip()


def kernzeilen(ausgabe):
    """Die Zeilen, die das Ergebnis tragen - nicht der ganze Bericht.

    Eine Telegram-Meldung mit 40 Zeilen liest niemand. Bilanz und
    Trefferquote beantworten die Frage; wer mehr will, faehrt die
    Auswertung selbst.
    """
    behalten = []
    for z in ausgabe.splitlines():
        s = z.strip()
        if not s:
            continue
        if (s.startswith("Bilanz") or s.startswith("Ergebnis")
                or s.startswith("Treffer") or s.startswith("davon Kosten")
                or s.startswith("nach Kosten")):
            behalten.append(s)
        if len(behalten) >= 6:
            break
    return behalten


def main():
    stand = lade_stand()
    neu = {}
    faellig = []
    for name, (datei, _args) in BUECHER.items():
        jetzt = ausstiege(datei)
        neu[name] = jetzt
        vorher = stand.get(name, 0)
        if jetzt - vorher >= NEUE_AUSSTIEGE:
            faellig.append((name, vorher, jetzt))

    if not faellig:
        return  # nichts Neues - schweigen

    teile = []
    for name, vorher, jetzt in faellig:
        _datei, args = BUECHER[name]
        ok, ausgabe = fahre_auswertung(args)
        if not ok:
            teile.append("Spiegel/%s: Auswertung FEHLGESCHLAGEN - %s"
                         % (name, ausgabe))
            continue
        zeilen = kernzeilen(ausgabe)
        teile.append("Spiegel/%s (%d -> %d Ausstiege):\n%s"
                     % (name, vorher, jetzt, "\n".join("  " + z for z in zeilen)))
        stand[name] = jetzt

    # Nur die tatsaechlich ausgewerteten Buecher fortschreiben; ein
    # fehlgeschlagener Lauf darf den Stand nicht bewegen, sonst faellt
    # die Auswertung stillschweigend aus.
    for name in neu:
        stand.setdefault(name, 0)
    schreibe_stand(stand)

    print("Spiegel-Auswertung faellig und gefahren:\n\n" + "\n\n".join(teile))


if __name__ == "__main__":
    main()
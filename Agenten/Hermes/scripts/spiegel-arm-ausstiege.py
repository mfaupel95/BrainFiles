"""Zaehlt die Ausstiege der Spiegel-Schattenbuecher (knapp/weit).

Watchdog-Muster: leere Ausgabe = nichts senden. Sobald BEIDE Arme
>= MINDEST Ausstiege haben, wird eine Meldung ausgegeben (der Cron
liefert sie nach Telegram). Danach still, bis der naechste Schwellwert
erreicht ist (MINDEST + 10, + 20, ...), damit nicht jede halbe Stunde
dieselbe Meldung kommt.
"""
import csv
import os
import sys

MINDEST = 30
SCHRITT = 10
SPIEGEL = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "..", "Handel", "spiegel")
ARME = ("handelsjournal.knapp.csv", "handelsjournal.weit.csv")


def ausstiege(pfad):
    try:
        with open(pfad, encoding="utf-8") as fh:
            return sum(1 for z in csv.DictReader(fh)
                       if z.get("aktion") == "schliessen")
    except FileNotFoundError:
        return 0


def main():
    zaehler = {}
    for arm in ARME:
        zaehler[arm] = ausstiege(os.path.join(SPIEGEL, arm))
    knapp = zaehler[ARME[0]]
    weit = zaehler[ARME[1]]
    if knapp < MINDEST or weit < MINDEST:
        return  # noch nicht genug, nichts senden
    # Schwellwert: groesstes Vielfaches von SCHRITT unter dem Minimum
    schwelle = (min(knapp, weit) // SCHRITT) * SCHRITT
    if schwelle < MINDEST:
        return
    print("Spiegel-Schattenbuecher: %d Ausstiege je Arm erreicht "
          "(knapp=%d, weit=%d). Auswertung faellig: "
          "auswertung.py --pfad handelsjournal.knapp.csv und "
          "--pfad handelsjournal.weit.csv gegen das Hauptbuch."
          % (schwelle, knapp, weit))


if __name__ == "__main__":
    main()

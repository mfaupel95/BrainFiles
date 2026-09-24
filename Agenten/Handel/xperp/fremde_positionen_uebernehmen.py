"""Fremde Positionen ins xperp-Buch holen (Reparatur, 24.09.2026).

ANLASS: Max eroeffnet Positionen in der OKX-App. Die Spur kennt nur ihr
eigenes Journal und sieht sie nie - am 23.09.2026 lagen so BZ (1467 Kontrakte)
und CL (133) unbemerkt offen, mit belegter Margin und ohne Buchplatz, teils
ohne Stop. `handeln.py` prueft das jetzt in JEDEM Live-Zyklus
(bueche_fremde_positionen_uebernehmen); dieses Werkzeug ist der Handgriff fuer
den schon entstandenen Bestand.

Vorschau ist der Standard: sie zeigt, was uebernommen und welcher Stop gestellt
wuerde, ohne etwas zu schreiben. Erst `--anwenden` bucht ins Journal, setzt den
fehlenden Schutz-Stop, schreibt den Zustand und spiegelt nach Q:.

Aufruf aus dem xperp-Ordner:
    ../scanner/.venv/Scripts/python.exe fremde_positionen_uebernehmen.py
    ../scanner/.venv/Scripts/python.exe fremde_positionen_uebernehmen.py --anwenden
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime

# Eigene Spur ZULETZT einfuegen: sys.path.insert(0, ...) draengt sich nach
# vorn, und scanner/ hat ebenfalls ein handeln.py - sonst laedt dieses
# Werkzeug das fremde Modul (und findet die neue Funktion nicht).
HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HIER), "scanner"))
sys.path.insert(0, os.path.dirname(HIER))
sys.path.insert(0, HIER)

import handeln as h                                            # noqa: E402
import wachen_xperp as wx                                      # noqa: E402

assert os.path.dirname(os.path.abspath(h.__file__)) == HIER,     "falsches handeln.py geladen: %s" % h.__file__


def main():
    p = argparse.ArgumentParser(description="Fremde (Hand-)Positionen ins Buch holen")
    p.add_argument("--anwenden", action="store_true",
                   help="wirklich buchen (Journal, Schutz-Stop, Zustand, Spiegelung)")
    a = p.parse_args()

    with open(wx.WACHEN, encoding="utf-8") as fh:
        w = json.load(fh)
    z = h.lade_zustand()
    vorher = len(z.get("positionen") or [])
    print("Buch vorher: %d Position(en), modus=%s" % (vorher, z.get("modus")))
    print("Boersenfrage (positionen) und Buchabgleich:")
    n = h.bueche_fremde_positionen_uebernehmen(z, w, still=not a.anwenden)
    nachher = len(z.get("positionen") or [])
    if not n:
        print("\nNichts zu uebernehmen - das Buch kennt jede Position der Boerse.")
        return 0
    if not a.anwenden:
        print("\nVORSCHAU: %d Position(en) wuerden uebernommen (Buch %d -> %d). "
              "Kein Schreibzugriff, kein Stop, kein Journal." % (n, vorher, nachher))
        return 0

    # Sicherung VOR dem Schreiben (Stufe 1: erst .bak, dann aendern).
    bak = h.ZUSTAND + ".bak-%s" % datetime.now().strftime("%Y%m%d-%H%M%S")
    shutil.copy2(h.ZUSTAND, bak)
    h.schreibe_zustand(z)                       # setzt letzter_lauf selbst
    ziel = w.get("journal_zweitziel")
    ok, info = wx.spiegele_journal([h.JOURNAL, h.ZUSTAND], ziel)
    if wx.vermerke_spiegelung(z, ziel, ok, info, h.schreibe_zustand) and ok:
        wx.spiegele_journal([h.ZUSTAND], ziel)
    print("\n%d Position(en) uebernommen (Buch %d -> %d). Sicherung: %s"
          % (n, vorher, nachher, os.path.basename(bak)))
    print("Spiegelung nach %s: %s"
          % (ziel, "ok" if ok else "NICHT ok (%s)" % info))
    with open(h.ZUSTAND, encoding="utf-8") as fh:
        neu = json.load(fh)
    for q in neu.get("positionen", []):
        print("  %-26s %-5s %-10s Kontrakte %-10s Stop %-10s Herkunft %s"
              % (q.get("inst"), q.get("seite"), q.get("einstieg"), q.get("kontrakte"),
                 q.get("stop"), q.get("herkunft") or "eigener Einstieg"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""Einsatz nachziehen: Journal und Buch auf GELD statt Stueckpreis bringen.

Der Fehler (Befund 30.09.2026, T-208)
-------------------------------------
`beleg_hand.py` schrieb als Einsatz den **Stueckpreis** statt des Betrags
(`eintrag["preis_max"]`). Vier ueber die Hand ausgeführte Belege stehen
deshalb mit 0,21 / 0,95 / 1,15 / 1,61 EUR im Journal und mit 0,21 / 0,95 /
1,14 / 1,60 EUR im Buch - gemeint waren je ~50 EUR:

    XXLMZEUR  249,938765 @ 0,200049   Journal 0,21   richtig 50,30
    FILEUR     55,432373 @ 0,902      Journal 0,95   richtig 50,30
    DOTEUR     45,989698 @ 1,0882     Journal 1,15   richtig 50,35
    ATOMEUR    32,881757 @ 1,5206     Journal 1,61   richtig 50,30

Wirkung: `eingesetzt` war um Faktor ~30 zu klein, jede Runde dieser Paare
haette einen Scheingewinn von ~+49 EUR gezeigt, und der Gesamtdeckel
(max_gesamt_eur) konnte nie binden.

Was dieses Werkzeug tut
-----------------------
Es rechnet aus der ZEILE SELBST nach (Menge x Preis) und ersetzt den Einsatz
nur dort, wo er um mehr als die Haelfte daneben liegt. Es raet nichts: der
Stueckpreis steht in derselben Zeile, die Menge auch.

  * Journal:  Einsatz = menge x preis x (1 + gebuehr_taker)  - wie im Zyklus
  * Buch:     eur     = menge x einstieg                     - wie im Zyklus

Vorher werden die ALTEN Zeilen nach `handelsjournal.verworfen-JJJJMMTT.csv`
und die ganze Datei nach `handelsjournal.bak-JJJJMMTT.csv` gelegt (Beleg).

Aufruf (aus diesem Ordner):
    python einsatz_nachziehen.py              # Vorschau, schreibt nichts
    python einsatz_nachziehen.py --anwenden   # schreiben (mit Sicherungen)
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import shutil
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
ZUSTAND = os.path.join(HIER, "zustand.json")
JOURNAL = os.path.join(HIER, "handelsjournal.csv")
# Ab hier gilt ein Einsatz als Stueckpreis (er liegt um Faktor 2+ daneben).
QUOTE = 0.5


def _lade(name, pfad):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


kraken = _lade("kraken", os.path.join(HIER, "kraken.py"))
_stops = _lade("spot_stops", os.path.join(HIER, "spot_stops.py"))


def _zahl(x):
    try:
        return float(str(x).strip().replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def journal_fehler(zeilen, gebuehr_taker):
    """Kauf-Zeilen, deren Einsatz ein Stueckpreis ist -> [(index, alt, neu, text)].

    Geprueft wird nur, was sich aus der Zeile selbst nachrechnen laesst:
    Aktion `kauf`, Preis > 0, Menge > 0 und ein Einsatz, der um Faktor 2+
    unter Menge x Preis liegt. Ein bereits richtiger Einsatz wird nicht
    angefasst (Idempotenz - der zweite Lauf findet nichts mehr).
    """
    raus = []
    for i, z in enumerate(zeilen):
        if len(z) < 7 or z[2] != "kauf":
            continue
        preis, einsatz, menge = _zahl(z[4]), _zahl(z[5]), _zahl(z[6])
        erwartet = menge * preis
        if erwartet <= 0 or einsatz <= 0 or einsatz >= erwartet * QUOTE:
            continue
        neu = erwartet * (1 + gebuehr_taker)
        raus.append((i, einsatz, neu, "%s %s: %.2f -> %.2f EUR (Menge %.8g x %.8g)"
                     % (z[0][:10], z[3], einsatz, neu, menge, preis)))
    return raus


def buch_fehler(positionen):
    """Buchpositionen, deren `eur` ein Stueckpreis ist -> [(index, alt, neu, text)]."""
    raus = []
    for i, p in enumerate(positionen):
        preis, eur, menge = _zahl(p.get("einstieg")), _zahl(p.get("eur")), _zahl(p.get("menge"))
        erwartet = menge * preis
        if erwartet <= 0 or eur <= 0 or eur >= erwartet * QUOTE:
            continue
        raus.append((i, eur, erwartet,
                     "%s: %.2f -> %.2f EUR (Menge %.8g x %.8g)"
                     % (p.get("paar"), eur, erwartet, menge, preis)))
    return raus


def _stempel():
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def lauf(anwenden=False):
    w = json.load(open(os.path.join(HIER, "wachen.json"), encoding="utf-8"))
    gebuehr = float(w.get("gebuehr_taker") or 0.0)
    with open(JOURNAL, newline="", encoding="utf-8") as f:
        zeilen = [z for z in csv.reader(f)]
    kopf, daten = zeilen[:1], zeilen[1:]
    jf = journal_fehler(daten, gebuehr)
    with open(ZUSTAND, encoding="utf-8") as f:
        z = json.load(f)
    positionen = z.get("positionen") or []
    bf = buch_fehler(positionen)

    print("Journal: %d Zeile(n) mit Stueckpreis als Einsatz" % len(jf))
    for _, _, _, t in jf:
        print("  " + t)
    print("Buch: %d Position(en) mit Stueckpreis als Einsatz" % len(bf))
    for _, _, _, t in bf:
        print("  " + t)
    if not jf and not bf:
        print("Nichts zu tun (idempotent).")
        return 0
    if not anwenden:
        print("\nVORSCHAU - nichts geschrieben. Mit --anwenden ausfuehren.")
        return 0

    st = _stempel()
    # Die Sicherungen liegen NEBEN der Datei, die sie sichern - nicht im
    # Modulordner. Sonst schreibt ein Test (oder eine Stufe mit eigenem
    # Journal) seine Sicherungen in die echte Spur.
    jordner = os.path.dirname(os.path.abspath(JOURNAL))
    shutil.copy2(JOURNAL, os.path.join(jordner, "handelsjournal.bak-%s.csv" % st))
    with open(os.path.join(jordner, "handelsjournal.verworfen-%s.csv" % st), "w",
              newline="", encoding="utf-8") as f:
        s = csv.writer(f)
        s.writerow(kopf[0])
        for i, alt, _, _ in jf:
            s.writerow(daten[i])
    shutil.copy2(ZUSTAND, os.path.join(os.path.dirname(os.path.abspath(ZUSTAND)),
                                       "zustand.bak-%s.json" % st))

    for i, _, neu, _ in jf:
        daten[i][5] = "%.2f" % neu
    with open(JOURNAL, "w", newline="", encoding="utf-8") as f:
        s = csv.writer(f)
        s.writerow(kopf[0])
        s.writerows(daten)
    for i, _, neu, _ in bf:
        positionen[i]["eur"] = round(neu, 2)
    z["positionen"] = positionen
    z.setdefault("buch_korrekturen", []).append(
        {"zeit": datetime.now(timezone.utc).isoformat(timespec="seconds"),
         "grund": "einsatz_war_stueckpreis (beleg_hand, T-208)",
         "journal": len(jf), "buch": len(bf)})
    with open(ZUSTAND, "w", encoding="utf-8") as f:
        json.dump(z, f, ensure_ascii=False, indent=2)

    # Gegenprobe: nach dem Schreiben darf nichts mehr zu finden sein.
    with open(JOURNAL, newline="", encoding="utf-8") as f:
        nach = [x for x in csv.reader(f)][1:]
    rest = journal_fehler(nach, gebuehr)
    print("\nGeschrieben. Gegenprobe Journal: %d Fund(e) uebrig (muss 0 sein)." % len(rest))
    print("Sicherungen: handelsjournal.bak-%s.csv, handelsjournal.verworfen-%s.csv, "
          "zustand.bak-%s.json" % (st, st, st))
    return 0 if not rest else 1


def main():
    ap = argparse.ArgumentParser(description="Einsatz nachziehen (Vorschau Standard)")
    ap.add_argument("--anwenden", action="store_true", help="wirklich schreiben")
    args = ap.parse_args()
    return lauf(anwenden=args.anwenden)


if __name__ == "__main__":
    sys.exit(main())
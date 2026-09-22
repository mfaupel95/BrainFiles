"""Geister-Zeilen im Journal auf den echten Wert ziehen.

DAS PROBLEM (xperp, 21.09.2026)
-------------------------------
`bueche_geister_aus` schrieb die Verkaufszeile einer von Hand geschlossenen
Position mit `margin_usd = 0.00`. Die Wachen lesen die schliessen-Zeile als
ERLOES - die Runde zaehlte damit als Totalverlust in Hoehe des Einsatzes.
HBAR kostete das -16.84 USD in genau der Drawdown-Kurve, aus der der
Kill-Switch liest.

Der Code schreibt seit dem 22.09.2026 den echten Wert (Boersenergebnis, sonst
neutral). ALTE Zeilen tragen die 0.00 aber weiter - und eine Wache, die nur
den Code prueft, sieht sie nie.

WAS ES TUT
----------
Liest das Journal mit DERSELBEN FIFO-Regel wie `wachen_xperp.runden_aus_journal`
(eroeffnen-Zeile = Einsatz, schliessen-Zeile = Erloes, je Instrument in
Reihenfolge) und ersetzt bei einer kaputten Zeile
(`grund = buchbereinigung_geist` und Erloes genau 0.00) die 0.00 durch den
Einsatz, mit dem die Zeile verrechnet wird. Ergebnis: die Runde steht neutral
(Einsatz zurueck) statt als Vollverlust. Es wird NICHTS anderes angefasst -
keine Zeile geloescht, keine Zahl sonst veraendert.

WARUM NEUTRAL UND NICHT "DAS ECHTE ERGEBNIS": Bei diesen Zeilen stand die
Position in Wahrheit noch (HBAR wurde am selben Abend zurueckgebucht). Ein
Boersenergebnis gibt es dazu nicht - der ehrliche Wert ist der Einsatz.

VOR DEM SCHREIBEN: eine Kopie `handelsjournal.bak-JJJJMMTT.csv` daneben.

AUFRUF
    python geister_nachziehen.py --vorschau     (Standard, schreibt nichts)
    python geister_nachziehen.py --anwenden
    python geister_nachziehen.py --anwenden --spur xperp
"""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)

KAPUTT_GRUND = "buchbereinigung_geist"
SPALTEN_MIN = ("zeit", "modus", "aktion", "inst", "margin_usd", "grund")


def _journale(spur=None):
    """Alle Journale, die nach dem eroeffnen/schliessen-Schema laufen."""
    ordner = [os.path.join(HANDEL, spur)] if spur else \
        [os.path.join(HANDEL, d) for d in sorted(os.listdir(HANDEL))]
    treffer = []
    for o in ordner:
        if not os.path.isdir(o):
            continue
        for name in sorted(os.listdir(o)):
            if not (name.startswith("handelsjournal") and name.endswith(".csv")):
                continue
            if ".bak-" in name or "falsch-skaliert" in name:
                continue
            p = os.path.join(o, name)
            try:
                with open(p, "r", newline="", encoding="utf-8") as f:
                    f.readline()          # Kopfzeile: nur Lesbarkeit pruefen
            except OSError:
                continue
            treffer.append(p)
    return treffer


def _kaputte_zeilen(pfad):
    """[(zeilenindex, inst, alter_wert, richtiger_wert)] mit FIFO wie die Wachen.

    Gibt zusaetzlich die Kopfzeile und alle Zeilen zurueck, damit der Aufrufer
    nicht zweimal liest.
    """
    with open(pfad, "r", newline="", encoding="utf-8") as f:
        kopf = f.readline()
        zeilen = list(csv.reader(f))
    namen = next(csv.reader([kopf]))
    fehlend = [s for s in SPALTEN_MIN if s not in namen]
    if fehlend:
        return kopf, zeilen, namen, [], "Spalten fehlen: %s" % ", ".join(fehlend)
    i_akt, i_inst = namen.index("aktion"), namen.index("inst")
    i_margin, i_grund = namen.index("margin_usd"), namen.index("grund")
    offen = {}          # inst -> Liste der Einsaetze (FIFO)
    kaputt = []
    gesehen_eroeffnen = False
    for n, z in enumerate(zeilen):
        if len(z) <= max(i_akt, i_inst, i_margin, i_grund):
            continue
        akt, inst = z[i_akt], z[i_inst]
        try:
            betrag = float(z[i_margin])
        except (TypeError, ValueError):
            betrag = None
        if akt == "eroeffnen":
            gesehen_eroeffnen = True
            if betrag is not None:
                offen.setdefault(inst, []).append(betrag)
        elif akt == "schliessen":
            einsatz = offen[inst].pop(0) if offen.get(inst) else None
            if z[i_grund] == KAPUTT_GRUND and betrag == 0.0 and einsatz:
                kaputt.append((n, inst, z[i_margin], "%.2f" % einsatz))
    if not gesehen_eroeffnen:
        return kopf, zeilen, namen, [], "kein eroeffnen/schliessen-Schema"
    return kopf, zeilen, namen, kaputt, None


def korrigiere_datei(pfad, anwenden=True, still=False):
    """EINE Journaldatei. Rueckgabe: (kaputte_zeilen, geschrieben).

    Getrennt von `nachziehen`, damit ein Aufrufer mit einem bekannten Pfad
    (die Hermes-Wache) genau diese Datei behandeln kann - und damit ein Test
    auf einem Temp-Journal laufen kann, ohne die echten Buecher zu suchen.
    """
    kopf, zeilen, namen, kaputt, fehler = _kaputte_zeilen(pfad)
    if fehler or not kaputt:
        return [], False
    if not still:
        print("%s: %d kaputte Geister-Zeile(n)" % (pfad, len(kaputt)))
    for n, inst, alt, neu in kaputt:
        if not still:
            print("  Zeile %d  %-28s  Erloes %s -> %s" % (n + 1, inst, alt, neu))
        zeilen[n][namen.index("margin_usd")] = neu
    if not anwenden:
        return kaputt, False
    sicherung = pfad.replace(".csv", ".bak-%s.csv"
                             % datetime.now(timezone.utc).strftime("%Y%m%d"))
    if not os.path.exists(sicherung):
        shutil.copy2(pfad, sicherung)
        if not still:
            print("  Sicherung: %s" % os.path.basename(sicherung))
    with open(pfad, "w", newline="", encoding="utf-8") as f:
        f.write(kopf)
        csv.writer(f).writerows(zeilen)
    return kaputt, True


def nachziehen(spur=None, anwenden=False):
    gesamt = 0
    for p in _journale(spur):
        kaputt, geschrieben = korrigiere_datei(p, anwenden=anwenden)
        if kaputt:
            gesamt += len(kaputt)
    if not gesamt:
        print("Keine kaputten Geister-Zeilen gefunden.")
        return 0
    if not anwenden:
        print("\nVORSCHAU - nichts geschrieben. Mit --anwenden ausfuehren.")
        return 1
    print("\nFertig: %d Zeile(n) auf den echten Wert gezogen." % gesamt)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--spur", default=None)
    ap.add_argument("--anwenden", action="store_true")
    ap.add_argument("--vorschau", action="store_true",
                    help="nur zeigen (Standard, wenn --anwenden fehlt)")
    a = ap.parse_args(argv)
    return nachziehen(spur=a.spur, anwenden=a.anwenden)


if __name__ == "__main__":
    sys.exit(main())

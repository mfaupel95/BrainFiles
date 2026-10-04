"""Einen TASKS.md-Eintrag als erledigt nach unten ziehen (byte-genau, CRLF).

Warum es das gibt: Erledigtes wandert nach '## Erledigt' und behaelt den
Belegsatz. Von Hand ist das eine Fehlerquelle - Block falsch abgegrenzt,
Leerzeilen verschoben, ganze Datei neu geschrieben (LF statt CRLF). Hier steht
die Prozedur EINMAL, mit Gegenproben vor dem Schreiben:

    python scripts/erledigen.py T-129 "**Erledigt JJJJ-MM-TT.** was gemessen wurde"
    python scripts/erledigen.py T-129 "..." --pfad <andere TASKS.md> --trocken

Geprueft wird vor dem Schreiben: Nummer existiert genau EINMAL und steht in
'## Offen'; danach: Abschnitte unveraendert, Nummernmenge bis auf die eigene
unveraendert, Zeilenenden weiter CRLF. Sicherung TASKS.md.bak-JJJJMMTT.
Rueckgabe 0 = geschrieben (oder Trockenlauf ok), 1 = nichts gefunden/geaendert.
"""

import argparse
import datetime
import os
import re
import shutil
import sys

# GLEICHES Muster wie `doppelte_nummern.KOPF` - das war der Fehler (T-332,
# 04.10.2026): `[ x]` verlangt EXAKT ein Leerzeichen und kennt die
# Statuszeichen `[?]`, `[!]`, `[✓]` nicht. Gemessen an TASKS.md: 313 von 342
# Bloecken sichtbar, 29 unsichtbar. Die Folge war still - `erledigen`
# meldete "T-332 kommt 0x vor" fuer einen Eintrag, der in Zeile 378 steht.
#
# Zwei Werkzeuge, EIN Muster: sie auseinanderlaufen zu lassen hiesse, dass
# eins von beiden blind wird. Das hier ist die Kopie, nicht die Quelle - ein
# Test haelt beide gleich.
KOPF = re.compile(r"^- \[[ x?!✓]\]\s*\*\*(T-\d{3,})\b")


class Fehler(Exception):
    pass


class Datei:
    def __init__(self, pfad):
        self.pfad = pfad
        with open(pfad, "rb") as f:
            self.roh = f.read()
        if b"\r\n" not in self.roh:
            raise Fehler("Datei hat kein CRLF - falsche Datei?")
        self.zeilen = self.roh.decode("utf-8").split("\r\n")

    @property
    def text(self):
        return "\r\n".join(self.zeilen)

    def abschnitt(self, name):
        for i, z in enumerate(self.zeilen):
            if z.strip() == "## " + name:
                return i
        raise Fehler("Abschnitt '## %s' fehlt" % name)

    def block(self, nummer):
        """(start, ende) des Blocks - ende zeigt auf die erste Zeile danach."""
        treffer = [i for i, z in enumerate(self.zeilen) if KOPF.match(z)
                   and KOPF.match(z).group(1) == nummer]
        if len(treffer) != 1:
            raise Fehler("%s kommt %dx vor" % (nummer, len(treffer)))
        i = treffer[0]
        j = i + 1
        while j < len(self.zeilen) and not KOPF.match(self.zeilen[j]) \
                and not self.zeilen[j].startswith("## "):
            j += 1
        while j - 1 > i and not self.zeilen[j - 1].strip():
            j -= 1
        return i, j

    def erledigen(self, nummer, beleg):
        i_offen, i_erl = self.abschnitt("Offen"), self.abschnitt("Erledigt")
        i, j = self.block(nummer)
        if not (i_offen < i < i_erl):
            raise Fehler("%s steht nicht in '## Offen' (Zeile %d)" % (nummer, i + 1))
        if not self.zeilen[i].startswith("- [ ] "):
            raise Fehler("%s ist schon abgehakt: %r" % (nummer, self.zeilen[i][:40]))
        ids_vorher = re.findall(r"- \[[ x?!✓]\]\s*\*\*(T-\d{3,})", self.text)
        abschnitte_vorher = [z for z in self.zeilen if z.startswith("## ")]

        block = self.zeilen[i:j]
        block[0] = block[0].replace("- [ ] ", "- [x] ", 1)
        block.append("      " + beleg)
        del self.zeilen[i:j]
        i_erl = self.abschnitt("Erledigt")
        self.zeilen[i_erl + 1:i_erl + 1] = block
        # vor dem einruecken keine Zeile verlieren
        assert [z for z in self.zeilen if z.startswith("## ")] == abschnitte_vorher
        # Reihenfolge aendert sich durch das Verschieben - die MENGE muss gleich bleiben
        assert sorted(re.findall(r"- \[[ x?!✓]\]\s*\*\*(T-\d{3,})", self.text)) == sorted(ids_vorher)
        return i + 1

    def schreibe(self, mit_sicherung=True):
        stempel = datetime.date.today().strftime("%Y%m%d")
        bak = "%s.bak-%s" % (self.pfad, stempel)
        if mit_sicherung and not os.path.exists(bak):
            shutil.copy2(self.pfad, bak)
        neu = self.text.encode("utf-8")
        assert b"\r\r" not in neu, "Zeilenenden verdoppelt"
        with open(self.pfad, "wb") as f:
            f.write(neu)
        return bak


def main(argv=None):
    hier = os.path.dirname(os.path.abspath(__file__))
    wurzel = os.path.abspath(os.path.join(hier, "..", "..", "..", "..", ".."))
    p = argparse.ArgumentParser(description="TASKS.md-Eintrag erledigen")
    p.add_argument("nummer")
    p.add_argument("beleg", nargs="?", default="",
                   help="was GEMESSEN wurde (nicht der Auftrag)")
    p.add_argument("--pfad", default=os.path.join(wurzel, "MaxHirn", "Archiv", "TASKS.md"))
    p.add_argument("--trocken", action="store_true")
    a = p.parse_args(argv)
    try:
        d = Datei(a.pfad)
        zeile = d.erledigen(a.nummer, a.beleg)
    except Fehler as e:
        print("nichts geaendert: %s" % e)
        return 1
    if a.trocken:
        print("Trockenlauf ok: %s wuerde von Zeile %d nach '## Erledigt' ziehen" % (a.nummer, zeile))
        return 0
    bak = d.schreibe()
    print("%s erledigt (Sicherung %s)" % (a.nummer, os.path.basename(bak)))
    print("bitte nachsehen: %s" % d.pfad)
    return 0


if __name__ == "__main__":
    sys.exit(main())

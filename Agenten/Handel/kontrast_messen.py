"""Kontrast der Hausfarben messen - WCAG-Kontrastverhaeltnis, kein Blick.

`claude-design` nennt Typografie und Farbe als zwei der Ursachen fuer
schlechtes Design, und `design-md` fuehrt WCAG-Kontrast als Prufzeile.
Beides ist auf die tkinter-Fenster anwendbar, obwohl die Skills fuer Web
geschrieben sind: eine Farbe, deren Text nicht lesbar ist, ist auf beiden
Medien ein Fehler.

Gemessen wird jedes Paar aus `fenster_design.FARBEN`, das im Haus wirklich
vorkommt: Flaeche x Schrift, Blatt x Zellenhintergrund, Text auf Akzent.

WCAG 2.1 Kontrastverhaeltnis: (L1 + 0.05) / (L2 + 0.05) mit der
relativen Leuchtdichte L aus den sRGB-Werten.

Kein Fenster noetig - reines Rechnen, damit es ohne Bildschirm laeuft.

Aufruf:  python kontrast_messen.py
"""

from __future__ import annotations

import importlib.util
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
WERKZEUGE = os.path.join(HIER, "..", "Werkzeuge")

# (Name, Hintergrund, Vordergrund, wo im Haus)
PAARE = [
    ("Text auf Fensterflaeche", "bg", "text", "Tabellentext, Labels"),
    ("Text auf Datenflaeche", "blatt", "text", "Tabellenzellen"),
    ("MATT auf Fensterflaeche", "bg", "matt", "Nebeninfo, Fusszeile"),
    ("MATT auf Datenflaeche", "blatt", "matt", "Achsen, Nebenspalten"),
    ("AKZENT auf Fensterflaeche", "bg", "akzent", "Tabellenkopf, Titel"),
    ("GRUEN auf Fensterflaeche", "bg", "gruen", "Gewinn, long"),
    ("ROT auf Fensterflaeche", "bg", "rot", "Verlust, short"),
    ("GELB auf Fensterflaeche", "bg", "gelb", "Warnung"),
    ("Text auf Zellgruen", "zellgruen", "text", "Gewinnzelle"),
    ("Text auf Zellrot", "zellrot", "text", "Verlustzelle"),
    ("Text auf Auswahl", "auswahl", "text", "aktive Zeile"),
    ("Text auf Gitter", "gitter", "text", "Trennlinie, Kopfzeile"),
]

# WCAG: 4.5 fuer Fliesstext, 3.0 fuer GROSS (>=18.66px bold oder >=24px).
GRENZE_NORMAL = 4.5
GRENZE_GROSS = 3.0


def _design():
    pfad = os.path.join(WERKZEUGE, "fenster_design.py")
    spec = importlib.util.spec_from_file_location("fenster_design", pfad)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def leuchtdichte(hexfarbe: str) -> float:
    """Relative Leuchtdichte nach WCAG 2.1 (sRGB, lineare Kanaele)."""
    h = hexfarbe.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))

    def linear(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b)


def verhaeltnis(a: str, b: str) -> float:
    la, lb = leuchtdichte(a), leuchtdichte(b)
    hell, dunkel = max(la, lb), min(la, lb)
    return (hell + 0.05) / (dunkel + 0.05)


def main() -> int:
    d = _design()
    f = d.FARBEN
    print("Kontrast der Hausfarben (WCAG 2.1), Quelle fenster_design.py")
    print("Grenze: %.1f normal, %.1f gross" % (GRENZE_NORMAL, GRENZE_GROSS))
    print()
    print("%-28s %-9s %-9s %6s  %s" % ("Paar", "Hinten", "Vorn", "Verh.",
                                       "Urteil"))
    schlecht = []
    for name, hg, vf, wo in PAARE:
        v = verhaeltnis(f[hg], f[vf])
        if v >= 7.0:
            urteil = "AAA"
        elif v >= GRENZE_NORMAL:
            urteil = "AA"
        elif v >= GRENZE_GROSS:
            urteil = "AA nur GROSS"
        else:
            urteil = "ZU WENIG"
            schlecht.append((name, v, wo))
        print("%-28s %-9s %-9s %6.2f  %s"
              % (name, f[hg], f[vf], v, urteil))
    print()
    if schlecht:
        print("ZU WENIG KONTRAST: %d Paare" % len(schlecht))
        for name, v, wo in schlecht:
            print("   %-28s %6.2f  (%s)" % (name, v, wo))
        return 1
    print("Alle %d Paare mindestens AA fuer Fliesstext." % len(PAARE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
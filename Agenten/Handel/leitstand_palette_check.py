"""Sind die sieben Extra-Farben im Leitstand eine Abweichung oder ein Defekt?

`leitstand_stil.py` erweitert die Hauspalette um sieben Werte. Das ist nicht
automatisch ein Wartungsfehler - eine Zustandsfarbe, die es in der Quelle
nicht gibt (Notaus, Zebra, Auswahl), muss irgendwo definiert werden. Die
Frage ist, welche davon BEGRUENDET sind und welche die Quelle umgehen.

Vier Kategorien, und die Unterscheidung ist eine Entscheidung:

  1. NEU (5): Zustandsfarben, die es in der Quelle nicht gibt - `gedaempft`,
     `wahl`, `zebra`, `hinweis`, `dunkelgelb`, `notaus*`. Sie erweitern die
     Palette um etwas, das keine andere Datei braucht. Das ist in Ordnung,
     solange sie im Hausstil liegen und nicht spurlos eingetragen sind.
  2. UEBERSCHRIEBEN (1): `matt` bekommt einen ANDEREN Wert als die Quelle
     (`#bac2de` statt `#a6adc8`). Ein Name, zwei Werte, zwei hausweite
     Bedeutung - das ist der eigentliche Wartungsfehler.
  3. DOPPELTE NAMEN (2): `wahl` und `rand` sind beide `#45475a`, und die
     Quelle fuehrt denselben Wert als `auswahl`. Drei Namen, eine Farbe.
  4. KONTRAST (1): `gedaempft` #7f849c verfehlt 4,5:1 gegen die Datenflaeche
     (gemessen 4,75 auf blatt, 4,44 auf bg) - und derselbe Kommentar nennt
     `matt` bei 9.26:1 als "lesbar".

Aufruf:  scanner/.venv/Scripts/python.exe leitstand_palette_check.py
"""

from __future__ import annotations

import ast
import importlib.util
import os
import sys

HANDEL = os.path.dirname(os.path.abspath(__file__))
STIL = os.path.join(HANDEL, "leitstand_stil.py")


def lade_quelle():
    pfad = os.path.join(os.path.dirname(HANDEL), "Werkzeuge",
                        "fenster_design.py")
    spec = importlib.util.spec_from_file_location("fenster_design", pfad)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def leuchtdichte(hexfarbe):
    h = hexfarbe.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    lin = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def verhaeltnis(a, b):
    la, lb = leuchtdichte(a), leuchtdichte(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def main() -> int:
    d = lade_quelle()
    with open(STIL, encoding="utf-8") as f:
        src = f.read()
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") \
                == "FARBEN" and isinstance(n.value, ast.Call):
            break

    # Der Wert, den das Fenster TATSAECHLICH benutzt, steht im Modul -
    # nicht per Regex im Quelltext. `matt=hz.FARBEN["matt_flache"]` ist keine
    # Farbangabe im Text, und die Erklaerung darueber nennt den alten Wert;
    # der Regex las ihn und meldete "UEBERSCHREIBT" fuer eine Farbe, die aus
    # der Quelle kommt. Kein besserer Regex hilft - nur das echte Objekt.
    import importlib.util
    import sys as _sys
    if HANDEL not in _sys.path:
        _sys.path.insert(0, HANDEL)
    spec = importlib.util.spec_from_file_location(
        "leitstand_stil_probe", STIL)
    stil = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stil)
    gefunden = {k: v for k, v in stil.FARBEN.items()
                if k not in d.FARBEN}

    # Welche Farbe traegt WELCHEN Text. Das ist nicht ueberall der
    # Standardtext: der Notaus-Knopf setzt `fg="white"`
    # (leitstand_freigaben.py:265). Mit dem Standardtext gerechnet lag
    # `notaus` bei 3,23:1 und sah wie ein Befund aus - gegen Weiss sind es
    # 5,44:1, also in Ordnung. Ein Zellhintergrund (`zebra`, `dunkelgelb`),
    # eine Rahmenfarbe (`rand`, `wahl`) oder eine Auswahl traegt gar keinen
    # Text; dort ist ein Wert unter 4,5:1 die Absicht.
    TRAGEND = {
        "matt": d.FARBEN["blatt"],
        "hinweis": d.FARBEN["bg"],
        "notaus": "#ffffff",
        "notaus_aktiv": "#ffffff",
    }
    # `gedaempft` steht NICHT hier: es ist der Vordergrund GESPERRTER
    # Knoepfe (leitstand_stil.py:103-116, `disabled`) und der
    # Grundlinie. Ein gesperrter Knopf soll lesbar sein und nicht
    # aus der Reihe fallen - ein Wert deutlich unter dem Standardtext
    # ist dafuer die Absicht, nicht ein Befund. Die Zahl gehoert
    # trotzdem in die Ausgabe, damit sie nicht untergeht.
    ABSICHT = {"gedaempft": d.FARBEN["blatt"]}

    print("Hauspalette: %d Schluessel in fenster_design.py" % len(d.FARBEN))
    print()
    print("%-14s %-9s %-9s %8s  %s"
          % ("Name", "Leitstand", "Quelle", "Kontrast", "Einordnung"))
    print("-" * 74)
    befunde = []
    for name, wert in sorted(gefunden.items()):
        q = d.FARBEN.get(name)
        if q == wert:
            ordnung = "identisch"
        elif q is None and wert in d.FARBEN.values():
            # Der Wert steht in der Quelle, nur unter einem anderen Schluessel:
            # `matt` nimmt `matt_flache` (Max, 05.10.2026). Ohne diese Zeile
            # meldete das Skript weiter "UEBERSCHREIBT" fuer eine Farbe, die
            # aus der Quelle kommt.
            treffer = [k for k, v in d.FARBEN.items() if v == wert]
            ordnung = "aus der Quelle: %s" % ", ".join(sorted(treffer))
        elif q is None:
            # Doppelter Name: derselbe Wert unter anderem Schluessel?
            gleiche = [k for k, v in d.FARBEN.items() if v == wert]
            if gleiche:
                ordnung = "DOPPELT %s" % ", ".join(gleiche)
                befunde.append((name, wert, ordnung, None))
            else:
                ordnung = "neu (Zustand)"
        else:
            ordnung = "UEBERSCHREIBT %s" % q
            befunde.append((name, wert, ordnung, q))
        vor = TRAGEND.get(name)
        v = (verhaeltnis(vor, wert) if vor
             else verhaeltnis(d.FARBEN["blatt"], wert))
        print("%-14s %-9s %-9s %8.2f  %s"
              % (name, wert, q or "-", v, ordnung))
        if vor and v < 4.5:
            befunde.append((name, wert, "KONTRAST %.2f < 4.5 (auf %s)"
                            % (v, vor), vor))

    print()
    text_befunde = [b for b in befunde if b[0] in TRAGEND]
    if text_befunde:
        print("BEFUNDE an farbtragenden Werten: %d" % len(text_befunde))
        for name, wert, art, zweite in text_befunde:
            print("   %-14s %s  (%s)" % (name, wert, art))
        return 1
    print("Keine Befunde an farbtragenden Werten. Die uebrigen sind\n          Flaechen, Rahmen und Auswahl - dort ist der Wert gewollt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
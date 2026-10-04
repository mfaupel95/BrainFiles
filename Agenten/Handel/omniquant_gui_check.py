"""Wie weit ist omniquant/gui.py von der einen Designquelle entfernt?

Der Audit vom 04.10.2026 fand in diesem Fenster eine vollstaendige Kopie der
Palette aus `fenster_design.FARBEN` (12 Schluessel) plus 20 eigene
`font=("Consolas", N)`-Literale und zwei Farben als Literal. Die Kopie ist
HEUTE wertgleich - das ist kein Fehler, sondern der Keim zu einem: eine
Aenderung in der Quelle erreicht dieses Fenster nicht mehr.

Dieses Skript misst den Abstand, damit die Zahl nicht aus einer Behauptung
wird: Schluessel, Werte, eigene Farben, eigene Schriften.

Aufruf:  scanner/.venv/Scripts/python.exe omniquant_gui_check.py
"""

from __future__ import annotations

import ast
import importlib.util
import os
import re
import sys

# Das Skript liegt in `Agenten/Handel/`: `scratch` gibt es hier nicht,
# also ist der Handel-Ordner selbst der Ausgangspunkt.
HANDEL = os.path.dirname(os.path.abspath(__file__))
assert os.path.isdir(os.path.join(HANDEL, "omniquant")), HANDEL
ZIEL = os.path.join(HANDEL, "omniquant", "gui.py")
QUELLE = os.path.join(os.path.dirname(HANDEL), "Werkzeuge",
                       "fenster_design.py")


def lade_quelle():
    spec = importlib.util.spec_from_file_location("fenster_design", QUELLE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    d = lade_quelle()
    q = d.FARBEN
    with open(ZIEL, encoding="utf-8") as f:
        src = f.read()
    tree = ast.parse(src)

    # Eine Kopie ist ein DICT-Literal; `FARBEN = design.FARBEN` ist ein
    # Attribut und laesst sich nicht auswerten. Genau der Unterschied
    # ist der Befund - also wird er hier unterschieden, nicht geraten.
    kopie = None
    gebunden = False
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) \
                == "FARBEN":
            try:
                kopie = ast.literal_eval(n.value)
            except ValueError:
                gebunden = isinstance(n.value, ast.Attribute) \
                    and getattr(n.value.value, "id", "") == "design"
                if not gebunden:
                    raise

    print("Quelle  fenster_design.py: %d Farbschluessel" % len(q))
    print("Ziel    omniquant/gui.py:    %s"
          % ("%d (Kopie)" % len(kopie) if kopie else "importiert die Quelle"))

    if kopie is not None:
        fehlt = sorted(set(q) - set(kopie))
        extra = sorted(set(kopie) - set(q))
        abweich = [(k, v, q[k]) for k, v in sorted(kopie.items())
                   if k in q and v != q[k]]
        print()
        print("  fehlt in der Kopie : %s" % (", ".join(fehlt) or "-"))
        print("  extra in der Kopie : %s" % (", ".join(extra) or "-"))
        print("  Wertabweichungen   : %s"
              % (", ".join("%s %s statt %s" % a for a in abweich) or "-"))
        print("  BINDUNG            : %s"
              % ("keine - die Kopie laeuft auseinander"
                 if abweich or fehlt else
                 "noch wertgleich, aber ungebunden"))

    # Eigene Farbwerte: Hex-Literale, die NICHT aus FARBEN[] kommen.
    alle_hex = set(re.findall(r'"(#[0-9a-fA-F]{6})"', src))
    fremd = sorted(h for h in alle_hex if h not in set(q.values()))
    print()
    print("Hex-Literale gesamt : %d (%d verschieden)"
          % (len(re.findall(r'"(#[0-9a-fA-F]{6})"', src)), len(alle_hex)))
    print("davon nicht in der Quelle: %s" % (", ".join(fremd) or "-"))

    # Eigene Schriften: font=("...", N) statt design.schrift().
    fonts = re.findall(r'font=\("([^"]+)",\s*(\d+)\)', src)
    basis = q and d.SCHRIFT_GROESSE
    fremde_stufen = sorted({int(g) for _, g in fonts if int(g) != basis})
    print()
    print("font=(...) Literale : %d" % len(fonts))
    print("Familien            : %s" % ", ".join(sorted({f for f, _ in fonts})))
    print("Stufen              : %s (Haus-Basis %s)"
          % (", ".join(str(x) for x in sorted({int(g) for _, g in fonts})),
             basis))
    print("Stufen ausserhalb der Basis: %s"
          % (", ".join(str(x) for x in fremde_stufen) or "-"))

    sauber = (kopie is None and not fremd
              and not fremde_stufen)
    print()
    print("ERGEBNIS: %s"
          % ("gebunden an die eine Quelle" if sauber else
             "eigene Farben oder eigene Schriftstufen"))
    return 0 if sauber else 1


if __name__ == "__main__":
    sys.exit(main())
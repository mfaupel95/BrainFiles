"""Audit: baut eine Wache ihren Werkzeugpfad aus einem FALSCHEN Anker?

Zwei Fehler, beide gemessen am 05.10.2026 in `historie-auftrag.py`:

  A) `HIER = Path(__file__).resolve()` (die DATEI) und dann `HIER / "x.py"`.
     Der Pfad zeigt auf ein Verzeichnis mit py-Namen darin. `subprocess.run`
     und `spec.loader.exec_module` reagieren unterschiedlich, aber beide
     fuehren zu "nichts passiert" oder zu einer Ausnahme mit falschem Text.

  B) `HIER = ...resolve().parent` (der ORDNER) und dann `HIER / "x.py"`.
     Das ist RICHTIG und darf nicht als Fehler gemeldet werden.

Der Unterschied ist nur im Code zu sehen, nicht im Dateinamen. Also liest
dieses Skript den Anker und verlangt beides zusammen: `HIER` muss ein
ORDNER sein, wenn mit `/` ein Dateiname folgt.

KEIN Textmustern: `HIER = Path(__file__).resolve()` ist in 26 Dateien der
Normalbau und in keiner falsch. Gesucht ist nur die ZUSAMMENstellung aus
Zeile 1 und Zeile 2.

Aufruf:  python audit-werkzeugpfad.py [--ordner <scripts>] [--json]
"""
import argparse
import ast
import json
import sys
from pathlib import Path


def _anker_ist_ordner(knoten):
    """Aus einem AST-Ausdruck: baut er einen ORDNER?

    `Path(__file__).resolve().parent` -> True (parents[0] der Datei)
    `Path(__file__).resolve()`       -> False (die Datei selbst)
    `Path(__file__)`                 -> False
    """
    # Kette von Calls und Attributen abbauen.
    attribute = None
    while isinstance(knoten, ast.Call):
        knoten = knoten.func
    if isinstance(knoten, ast.Attribute):
        attribute = knoten.attr
        knoten = knoten.value
    else:
        return None                          # nicht entscheidbar
    if attribute == "parent":
        return True
    # `Path(__file__).resolve()` ohne `.parent`: Attribute ist "resolve"
    if attribute in ("resolve", "absolute", "expanduser", "realpath"):
        return False
    return None


def datei_baut_datei_als_ordner(pfad):
    """Der Befund fuer EINE Datei, oder None."""
    try:
        text = pfad.read_text(encoding="utf-8")
        baum = ast.parse(text, filename=str(pfad))
    except (OSError, SyntaxError, ValueError):
        return None
    zuweisungen = {}
    for knoten in ast.walk(baum):
        if not isinstance(knoten, ast.Assign):
            continue
        for ziel in knoten.targets:
            if isinstance(ziel, ast.Name) and ziel.id.isupper():
                zuweisungen[ziel.id] = knoten.value
    # Alle `HIER / "<name>.py"`-Verwendungen sammeln.
    verwendung = None
    for knoten in ast.walk(baum):
        if not isinstance(knoten, ast.BinOp):
            continue
        if not isinstance(knoten.op, ast.Div):
            continue
        links = knoten.left
        if not (isinstance(links, ast.Name) and links.id == "HIER"):
            continue
        rechts = knoten.right
        if isinstance(rechts, ast.Constant) and isinstance(rechts.value, str):
            if rechts.value.endswith((".py", ".ps1", ".cmd")):
                verwendung = rechts.value
                break
    if verwendung is None:
        return None
    wert = zuweisungen.get("HIER")
    if wert is None:
        return {"datei": pfad.name, "art": "HIER ohne Zuweisung",
                "nutzt": verwendung, "zeile": None}
    ist_ordner = _anker_ist_ordner(wert)
    if ist_ordner is None:
        return None                          # nicht entscheidbar -> kein Befund
    if not ist_ordner:
        zeile = getattr(knoten := wert, "lineno", None)
        return {"datei": pfad.name, "art": "HIER ist die DATEI",
                "nutzt": verwendung, "zeile": zeile}
    return None


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--ordner", default=str(Path(__file__).resolve().parent))
    p.add_argument("--json", action="store_true")
    p.add_argument("--mit-tests", action="store_true",
                   help="auch test_*.py pruefen (sie setzen HIER bewusst "
                        "auf den Ordner)")
    a = p.parse_args(argv)

    ordner = Path(a.ordner)
    befunde = []
    for pfad in sorted(ordner.glob("*.py")):
        if not a.mit_tests and pfad.name.startswith("test_"):
            continue
        b = datei_baut_datei_als_ordner(pfad)
        if b:
            befunde.append(b)
    if a.json:
        print(json.dumps(befunde, ensure_ascii=False, indent=1))
    elif befunde:
        print("FEHLER: HIER ist die Datei, wird aber wie ein Ordner benutzt")
        for b in befunde:
            print("  %-34s Zeile %s nutzt %r" % (b["datei"], b["zeile"],
                                                  b["nutzt"]))
    else:
        print("Kein Befund in %s" % ordner.name)
    return 1 if befunde else 0


if __name__ == "__main__":
    sys.exit(main())
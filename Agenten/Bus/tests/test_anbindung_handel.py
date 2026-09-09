"""Prueft, dass jede Handelsspur den Bus wirklich ruft. Startet keinen Bot -
nur die Anbindung wird geprueft. Direkt ausfuehrbar.
"""
import ast
import os

BUS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDEL = os.path.join(os.path.dirname(BUS), "Handel")

# orb und scanner in Schritt 1 nachgetragen: gefunden per
# `grep -rl "__main__" Agenten/Handel/orb Agenten/Handel/scanner`, unter
# Ausschluss von backtest.py/scan.py (Analysewerkzeuge, kein Live-/Papier-
# Einstieg) und scanner/.venv (Fremdcode). handeln.py ist in beiden Ordnern
# das Skript mit --vorschau/--papier/--live/--wachen, das dauerlauf.py fuer
# die Spur 'scanner' per subprocess aufruft und das orb/SPEC.md als die
# vierte Spur beschreibt.
SPUREN = {
    "dauerlauf.py": "handel/dauerlauf",
    "dca.py": "handel/dca",
    "grid.py": "handel/grid",
    os.path.join("xperp", "bot.py"): "handel/xperp",
    os.path.join("verbesserer", "auswerter.py"): "handel/verbesserer",
    os.path.join("orb", "handeln.py"): "handel/orb",
    os.path.join("scanner", "handeln.py"): "handel/scanner",
}


def test_jede_spur_ruft_den_bus():
    fehlt = []
    for datei, wer in SPUREN.items():
        with open(os.path.join(HANDEL, datei), encoding="utf-8") as f:
            inhalt = f.read()
        if "ereignis.lauf" not in inhalt or wer not in inhalt:
            fehlt.append(datei)
    assert not fehlt, "ohne Bus-Anbindung: %s" % fehlt


def test_orb_und_scanner_sind_nachgetragen():
    # Die Spec verlangt alle sieben Spuren. Dieser Test faellt absichtlich,
    # solange Schritt 1 nicht erledigt ist.
    assert len(SPUREN) == 7, "orb und scanner fehlen noch in SPUREN"


def _dauerlauf_quelle():
    pfad = os.path.join(HANDEL, "dauerlauf.py")
    with open(pfad, encoding="utf-8") as f:
        return f.read(), pfad


def _spuren_ordner(baum):
    """Liest die SPUREN-Zuordnung (Spurname -> Unterordner) aus dem
    Syntaxbaum von dauerlauf.py. ast statt Regex, weil SPUREN ein echtes
    Dict-Literal ist - eine Regex muesste dieselbe Grammatik nachbauen und
    waere die zerbrechlichere Variante."""
    ordner = {}
    for knoten in ast.walk(baum):
        ist_spuren = (isinstance(knoten, ast.Assign)
                      and any(isinstance(z, ast.Name) and z.id == "SPUREN"
                              for z in knoten.targets))
        if not ist_spuren:
            continue
        for schluessel, wert in zip(knoten.value.keys, knoten.value.values):
            for k2, v2 in zip(wert.keys, wert.values):
                if isinstance(k2, ast.Constant) and k2.value == "ordner":
                    ordner[schluessel.value] = v2.value
    return ordner


def _subprocess_skriptnamen(baum):
    """Liest die Dateinamen, die dauerlauf.py per subprocess.run startet.

    Erfasst wird jedes Listenelement einer subprocess.run-Aufrufliste, das
    auf .py endet (z. B. "handeln.py"), unabhaengig von den uebrigen
    Argumenten (modus, --vorschau, ...) - so bricht die Pruefung nicht,
    wenn die Aufrufliste sich sonst aendert."""
    namen = set()
    for knoten in ast.walk(baum):
        ist_subprocess_run = (isinstance(knoten, ast.Call)
                              and isinstance(knoten.func, ast.Attribute)
                              and knoten.func.attr == "run"
                              and isinstance(knoten.func.value, ast.Name)
                              and knoten.func.value.id == "subprocess")
        if not ist_subprocess_run or not knoten.args:
            continue
        if not isinstance(knoten.args[0], ast.List):
            continue
        for el in knoten.args[0].elts:
            if (isinstance(el, ast.Constant) and isinstance(el.value, str)
                    and el.value.endswith(".py")):
                namen.add(el.value)
    return namen


def test_dauerlauf_subprocess_skripte_haben_bus():
    """Genau der Weg, auf dem Befund 1 durchgerutscht ist: die alte Pruefung
    (test_jede_spur_ruft_den_bus oben) sieht nur, OB irgendeine Datei den Bus
    ruft - nicht, ob sie die Datei ist, die dauerlauf.py automatisch startet.
    xperp handelt automatisch ueber xperp/handeln.py (dauerlauf.py:
    zyklus_spur und nur_fenster_fehlt rufen "handeln.py" per subprocess im
    xperp-Ordner auf), nicht ueber xperp/bot.py - bot.py wird von
    dauerlauf.py nie per subprocess gestartet, nur als Modul importiert.

    Diese Pruefung liest die Wahrheit direkt aus dauerlauf.py: fuer jede
    Spur in SPUREN wird ihr Ordner genommen, und fuer jeden per subprocess
    gestarteten Dateinamen (z. B. handeln.py) wird geprueft, ob GENAU DIESE
    Datei ereignis.lauf("handel/<spur>") traegt. Kommentiert man die
    Anbindung in xperp/handeln.py wieder aus, wird dieser Test rot - im
    Unterschied zur alten Pruefung, die jede Datei mit dem passenden String
    irgendwo im Ordner akzeptiert haette."""
    quelle, pfad = _dauerlauf_quelle()
    baum = ast.parse(quelle, filename=pfad)
    spuren_ordner = _spuren_ordner(baum)
    assert spuren_ordner, "SPUREN-Dict in dauerlauf.py nicht gefunden/leer"
    skriptnamen = _subprocess_skriptnamen(baum)
    assert skriptnamen, "keine per subprocess gestarteten .py-Dateien gefunden"

    fehlt = []
    for spur, ordner in spuren_ordner.items():
        for skript in skriptnamen:
            datei = os.path.join(HANDEL, ordner, skript)
            if not os.path.exists(datei):
                continue          # dieser Ordner kennt das Skript nicht
            with open(datei, encoding="utf-8") as f:
                inhalt = f.read()
            wer = "handel/%s" % spur
            if "ereignis.lauf" not in inhalt or wer not in inhalt:
                fehlt.append(os.path.join(ordner, skript))
    assert not fehlt, "automatisch gestartet, aber ohne Bus-Anbindung: %s" % fehlt


def test_melder_bleibt_unveraendert():
    # Die Spec verlangt das ausdruecklich (melder.py wird nur aufgerufen,
    # nicht geaendert). git status waere hier zahnlos: nach dem Commit
    # dieser Aufgabe ist der Status ohnehin leer. Stattdessen wird gegen
    # den Stand VOR dieser Aufgabe verglichen (verbindliche Abweichung vom
    # Brief, siehe Auftrag).
    import subprocess
    wurzel = os.path.dirname(os.path.dirname(HANDEL))
    r = subprocess.run(["git", "diff", "--quiet", "3a9b6e5", "--",
                        "Agenten/Handel/melder.py"],
                       cwd=wurzel)
    assert r.returncode == 0, "melder.py weicht vom Stand vor Aufgabe 7 ab"


if __name__ == "__main__":
    for name, f in sorted(list(globals().items())):
        if name.startswith("test_"):
            f()
            print("ok", name)
    print("alle Anbindungs-Tests Handel bestanden")

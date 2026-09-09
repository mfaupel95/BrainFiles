"""Prueft, dass jede Handelsspur den Bus wirklich ruft. Startet keinen Bot -
nur die Anbindung wird geprueft. Direkt ausfuehrbar.
"""
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

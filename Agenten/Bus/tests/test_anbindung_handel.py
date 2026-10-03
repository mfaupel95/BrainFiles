"""Prueft, dass jede Handelsspur den Bus wirklich ruft. Startet keinen Bot -
nur die Anbindung wird geprueft. Direkt ausfuehrbar.
"""
import ast
import os

BUS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDEL = os.path.join(os.path.dirname(BUS), "Handel")

# orbk und scanner in Schritt 1 nachgetragen: gefunden per
# `grep -rl "__main__" Agenten/Handel/orbk Agenten/Handel/scanner`, unter
# Ausschluss von backtest.py/scan.py (Analysewerkzeuge, kein Live-/Papier-
# Einstieg) und scanner/.venv (Fremdcode). handeln.py ist in beiden Ordnern
# das Skript mit --vorschau/--papier/--live/--wachen, das dauerlauf.py fuer
# die Spur 'scanner' per subprocess aufruft und das orbk/SPEC.md als die
# vierte Spur beschreibt.
#
# Nachgezogen am 13.09.2026: hier stand `orb/handeln.py`. Die Datei gibt es
# nicht mehr - `orb/` traegt nur noch backtest.py, session.py, wachen*.py,
# tests/ und daten/, das handeln.py liegt in orb/.backup-okx-20260913/. Die
# Spur laeuft als `orbk` (Kraken), so steht sie auch in dauerlauf.SPUREN. Auf-
# gefallen ist es erst, als die Pruefung darunter wieder griff (sie war seit
# dem SWAP-Umbau am 12.09.2026 stumm) - dieser Test war danach der naechste,
# der zum ersten Mal wieder lief.
SPUREN = {
    "dauerlauf.py": "handel/dauerlauf",
    "dca.py": "handel/dca",
    "grid.py": "handel/grid",
    os.path.join("xperp", "bot.py"): "handel/xperp",
    os.path.join("verbesserer", "auswerter.py"): "handel/verbesserer",
    os.path.join("orbk", "handeln.py"): "handel/orbk",
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
    """Liest die Dateinamen, die dauerlauf.py je Spur per subprocess startet.

    Drei Quellen, weil der Aufruf sich am 12.09.2026 geaendert hat: in der
    subprocess.run-Aufrufliste steht seit dem SWAP-Umbau die Variable
    `skript` (`SPUREN[spur].get("skript", "handeln.py")`), kein Literal mehr.
    Die alten Literale gab es zuletzt nur noch als get-Default - eine
    Pruefung, die nur Listenelemente ansieht, fand damit NICHTS und brach mit
    "keine per subprocess gestarteten .py-Dateien gefunden" ab, statt zu
    pruefen (aufgefallen am 13.09.2026). Gelesen wird jetzt:

      1. der "skript"-Schluessel jeder Spur in SPUREN (die Wahrheit),
      2. der Default von `... .get("skript", "<name>.py")`,
      3. zusaetzlich Listenelemente, die auf .py enden (falls wieder welche
         dorthin zurueckkehren).
    """
    namen = set()
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Call):
            # (1) SPUREN["spur"]["skript"] im Dict selbst: erfasst der
            #     SPUREN-Walk unten, hier nur die beiden Aufrufformen.
            # (2) Default eines get("skript", ...)-Aufrufs
            if (isinstance(knoten.func, ast.Attribute)
                    and knoten.func.attr == "get"
                    and len(knoten.args) == 2
                    and isinstance(knoten.args[0], ast.Constant)
                    and knoten.args[0].value == "skript"
                    and isinstance(knoten.args[1], ast.Constant)
                    and isinstance(knoten.args[1].value, str)
                    and knoten.args[1].value.endswith(".py")):
                namen.add(knoten.args[1].value)
            # (3) subprocess.run([..., "<name>.py", ...])
            if (isinstance(knoten.func, ast.Attribute)
                    and knoten.func.attr == "run"
                    and isinstance(knoten.func.value, ast.Name)
                    and knoten.func.value.id == "subprocess"
                    and knoten.args
                    and isinstance(knoten.args[0], ast.List)):
                for el in knoten.args[0].elts:
                    if (isinstance(el, ast.Constant) and isinstance(el.value, str)
                            and el.value.endswith(".py")):
                        namen.add(el.value)
        # (1) der "skript"-Schluessel in SPUREN selbst
        if (isinstance(knoten, ast.Assign)
                and any(isinstance(z, ast.Name) and z.id == "SPUREN"
                        for z in knoten.targets)
                and isinstance(knoten.value, ast.Dict)):
            for wert in knoten.value.values:
                if not isinstance(wert, ast.Dict):
                    continue
                for k2, v2 in zip(wert.keys, wert.values):
                    if (isinstance(k2, ast.Constant) and k2.value == "skript"
                            and isinstance(v2, ast.Constant)
                            and isinstance(v2.value, str)):
                        namen.add(v2.value)
    return namen


def _spuren_skripte(baum):
    """Liest je Spur das Skript, das dauerlauf.py fuer SIE startet.

    Die Wahrheit ist das "skript"-Feld jeder Spur in SPUREN (Default
    "handeln.py"). Seit die Spiegel-Schattenbuecher (18.09.2026) denselben
    Ordner wie spiegel teilen (spiegel/spiegel_knapp/spiegel_weit -> alle
    Ordner "spiegel", aber drei verschiedene Skripte), ist die alte
    "alle Skriptnamen gegen alle Spuren"-Pruefung falsch-positiv: sie
    verlangte, dass spiegel.py auch "handel/spiegel_knapp" traegt. Geprueft
    wird jetzt nur das Skript, das dauerlauf.py fuer die jeweilige Spur
    wirklich startet.
    """
    skripte = {}
    for knoten in ast.walk(baum):
        if (isinstance(knoten, ast.Assign)
                and any(isinstance(z, ast.Name) and z.id == "SPUREN"
                        for z in knoten.targets)
                and isinstance(knoten.value, ast.Dict)):
            for schluessel, wert in zip(knoten.value.keys,
                                        knoten.value.values):
                if not isinstance(wert, ast.Dict):
                    continue
                skript = "handeln.py"
                for k2, v2 in zip(wert.keys, wert.values):
                    if (isinstance(k2, ast.Constant) and k2.value == "skript"
                            and isinstance(v2, ast.Constant)
                            and isinstance(v2.value, str)):
                        skript = v2.value
                skripte[schluessel.value] = skript
    return skripte


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
    Datei die Bus-Anbindung traegt. Kommentiert man die Anbindung in
    xperp/handeln.py wieder aus, wird dieser Test rot - im Unterschied zur
    alten Pruefung, die jede Datei mit dem passenden String irgendwo im Ordner
    akzeptiert haette.

    NACHTRAG 17.09.2026: acht Spuren (moondev_listingarb/-topmovers/-marktlage,
    iv_wand und die drei Sprachmodell-Spuren) fuehren ihr Buch ueber den
    gemeinsamen Kern `Handel/spur_buch.py` - die Meldung entsteht DORT
    (`ereignis.lauf(ereignis_name)` in `zyklus`), nicht in der Spurendatei.
    Deshalb standen sie hier als "ohne Bus-Anbindung", obwohl sie im
    Bus-Journal stehen. Eine Bindung ueber den Kern zaehlt aber nur, wenn die
    gestartete Datei IHREN EIGENEN Namen wortwoertlich uebergibt ("handel/<spur>")
    UND der Kern `ereignis.lauf` traegt - sonst waere "irgendwo im Ordner steht
    der Bus" wieder da, nur eine Ebene tiefer."""
    quelle, pfad = _dauerlauf_quelle()
    baum = ast.parse(quelle, filename=pfad)
    spuren_ordner = _spuren_ordner(baum)
    assert spuren_ordner, "SPUREN-Dict in dauerlauf.py nicht gefunden/leer"
    spuren_skripte = _spuren_skripte(baum)
    assert spuren_skripte, "keine Spur-Skript-Zuordnung in dauerlauf.py gefunden"

    kern = os.path.join(HANDEL, "spur_buch.py")
    kern_gebunden = os.path.exists(kern) and "ereignis.lauf" in open(
        kern, encoding="utf-8").read()

    # ZWEITER KERN (01.10.2026, T-255): die acht klassik_*-Spuren bestehen aus
    # einem kurzen `handeln.py`, das nur `klassik_regeln.spur_main(...)` ruft -
    # die Meldung entsteht wie bei spur_buch im gemeinsamen Buch-Kern, den
    # klassik_regeln.py aufruft (sp.zyklus -> ereignis.lauf). Dieselbe Regel wie
    # oben, nur eine Ebene tiefer: sie gilt NUR, wenn die gestartete Datei ihren
    # EIGENEN Bus-Namen woertlich uebergibt UND der Regelkern ihn wirklich an
    # `spur_buch.zyklus(ereignis_name=...)` weiterreicht. Sonst waere
    # "irgendwo im Ordner steht der Bus" nur eine Ebene tiefer wieder da.
    regelkern = os.path.join(HANDEL, "klassik_regeln.py")
    regelkern_quelle = (open(regelkern, encoding="utf-8").read()
                        if os.path.exists(regelkern) else "")
    regelkern_gebunden = ("ereignis_name" in regelkern_quelle
                          and "spur_buch" in regelkern_quelle)

    fehlt = []
    for spur, skript in spuren_skripte.items():
        ordner = spuren_ordner.get(spur)
        if ordner is None:
            continue          # Spur ohne Ordner-Zuordnung (sollte nicht sein)
        datei = os.path.join(HANDEL, ordner, skript)
        if not os.path.exists(datei):
            continue          # dieser Ordner kennt das Skript nicht
        with open(datei, encoding="utf-8") as f:
            inhalt = f.read()
        wer = "handel/%s" % spur
        direkt = "ereignis.lauf" in inhalt and wer in inhalt
        ueber_kern = (kern_gebunden and wer in inhalt
                      and "buch.zyklus" in inhalt)
        ueber_regelkern = (regelkern_gebunden and "spur_main" in inhalt
                           and ('bus_name="%s"' % wer) in inhalt)
        if not (direkt or ueber_kern or ueber_regelkern):
            fehlt.append(os.path.join(ordner, skript))
    assert not fehlt, "automatisch gestartet, aber ohne Bus-Anbindung: %s" % fehlt


def test_melder_bleibt_der_reine_sendeweg():
    # Die Spec verlangte: melder.py wird nur AUFGERUFEN, nicht zur Bus-Stelle
    # umgebaut. Der Test verglich dafuer bis zum 21.09.2026 byte-genau gegen
    # den Commit 3a9b6e5 ("Stand vor Aufgabe 7") - und wurde damit bei jeder
    # spaeteren Reparatur rot, ohne dass die Spec verletzt war: an dem Tag
    # zweimal (Telegram-400-Entschaerfung, dann die Stueckelung langer
    # Nachrichten). Ein Test, der jede Aenderung verbietet, prueft nicht die
    # Regel, sondern friert eine Datei ein.
    #
    # Geprueft wird deshalb die Regel selbst: melder.py kennt den Bus nicht.
    quelle = open(os.path.join(HANDEL, "melder.py"), encoding="utf-8").read()
    for verboten in ("import ereignis", "from ereignis", "ereignis.lauf",
                     "bus.py", "8787"):
        assert verboten not in quelle, (
            "melder.py ist zur Bus-Stelle geworden (%s) - er soll nur senden"
            % verboten)


if __name__ == "__main__":
    for name, f in sorted(list(globals().items())):
        if name.startswith("test_"):
            f()
            print("ok", name)
    print("alle Anbindungs-Tests Handel bestanden")

"""Die Summe ueber alle Buecher - getrennt nach Waehrung und nach Papier/Live.

Warum es diese Datei gibt: die Uebersicht in auswertung_alle.py kennt die
fuenf Spuren mit eigener auswertung.py nicht, und niemand rechnet den
Gesamtstand. Hier wird nichts NEU gerechnet - die Posten kommen fertig aus
den vorhandenen Auswertungen.

Zwei Regeln, die hier nicht verhandelbar sind:

  - Waehrungen werden nicht stumm gemischt. kraken rechnet EUR, der Rest USD.
    Eine Summe ueber beide waere eine Zahl ohne Einheit.
  - Papier und Live werden nicht verrechnet. Eine Zahl, die Papiergewinne mit
    echtem Geld zusammenwirft, ist schlimmer als keine Zahl.

Aufruf:
    python gesamtbilanz.py              # alles seit Anfang
    python gesamtbilanz.py --tage 30    # nur der letzte Monat
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))

import auswertung_alle                                         # noqa: E402
import zeitfenster                                             # noqa: E402

# Die fuenf Spuren mit eigener Auswertung. Sie liefern kennzahlen_kurz();
# die Rechnung bleibt ihre eigene.
EIGENE = ("spiegel", "omniquant", "kopier", "gitter")


def _lade_eigene(spur):
    """Laedt <spur>/auswertung.py ueber den Dateipfad, nicht den Punktnamen.

    Die Spurenordner sind keine Pakete (kein __init__.py) und jede legt
    beim Import ihren eigenen Ordner in sys.path - ein "import
    spiegel.auswertung" haengt damit davon ab, was vorher lief, und
    scheitert in der vollen unittest-discover-Suite. Der Dateipfad haengt
    von nichts ab.
    """
    name = "gesamtbilanz_spur_%s_auswertung" % spur
    if name in sys.modules:
        return sys.modules[name]
    pfad = HIER / spur / "auswertung.py"
    spec = importlib.util.spec_from_file_location(name, pfad)
    modul = importlib.util.module_from_spec(spec)
    sys.modules[name] = modul
    spec.loader.exec_module(modul)
    return modul


def _live(spur):
    """Handelt die Spur echt? Quelle ist handel_erlaubt in wachen.json.

    Wirft nie. Jeder Fehlschlag gilt als Papier - eine Spur faelschlich als
    Live zu zaehlen waere der teurere Irrtum. Deshalb auch `isinstance`:
    gueltiges JSON, das kein Objekt ist (`[]`, `42`, `null`), hat kein .get(),
    und der Aufruf steht in posten() ausserhalb jedes try - ein Wurf hier
    reisst die ganze Gesamtbilanz mit. Wortgleich mit den fuenf
    Eigen-Modulen (seit 7d80750).
    """
    p = HIER / spur / "wachen.json"
    if not p.exists():
        return False
    try:
        inhalt = json.loads(p.read_text("utf-8"))
    except (OSError, ValueError):
        return False
    if not isinstance(inhalt, dict):
        return False
    return bool(inhalt.get("handel_erlaubt"))


def posten(von=None, bis=None):
    """Alle Buecher als flache Liste gleichgeformter Posten.

    Jeder Posten traegt zusaetzlich "belastbar" - das Urteil aus
    auswertung_alle.belastbar(), an EINER Stelle gefaellt (dieselbe
    Schwelle wie ueberall sonst, MIN_RUNDEN). Ein Posten mit zu wenigen
    Runden bleibt in der Liste - er wird nur nicht mitsummiert (siehe
    summe()) und im Bericht gesondert ausgewiesen, statt zu verschwinden.
    """
    aus = []
    for spur in auswertung_alle.SPUREN:
        if spur in EIGENE:
            continue          # die bringen ihre eigene Rechnung mit
        k = auswertung_alle.kennzahlen_fuer(spur, von=von, bis=bis)
        if not k or not k.get("n"):
            continue
        aus.append({"spur": spur, "n": k["n"], "ergebnis": k["ergebnis"],
                    "treffer": k["treffer"],
                    "waehrung": "EUR" if spur == "kraken" else "USD",
                    "live": _live(spur),
                    "belastbar": auswertung_alle.belastbar(k)})
    for spur in EIGENE:
        try:
            m = _lade_eigene(spur)
            k = m.kennzahlen_kurz(von=von, bis=bis)
        except Exception as e:                           # noqa: BLE001
            # Eine Spur, die beim Auswerten ausfaellt, darf die Bilanz der
            # anderen nicht mitnehmen - dieselbe Regel wie im Tagesbericht.
            print("  %s: Auswertung ausgefallen (%s)" % (spur, e))
            continue
        if k:
            k = dict(k, spur=spur, belastbar=auswertung_alle.belastbar(k))
            aus.append(k)
    return aus


def summe(posten_):
    """Die Posten zu Summen je (Waehrung, Live) verdichten.

    Der Schluessel ist bewusst ein Paar. Es gibt keinen Schluessel, der
    alles zusammenwirft - eine solche Zahl waere ohne Einheit und ohne
    Bedeutung.

    Nur belastbare Posten zaehlen mit (Feld "belastbar" je Posten). Eine
    Spur mit zu wenigen Runden ist keine Aussage und wuerde sonst die
    stille Falschzahl erzeugen, gegen die belastbar() geschrieben ist.
    """
    s = {}
    for p in posten_:
        if not p.get("belastbar"):
            continue
        schluessel = (p["waehrung"], bool(p["live"]))
        t = s.setdefault(schluessel, {"n": 0, "ergebnis": 0.0, "treffer": 0})
        t["n"] += p["n"]
        t["ergebnis"] += p["ergebnis"]
        t["treffer"] += p["treffer"]
    return s


def zeilen_text(s):
    """Die Summen als Text - je Paar eine Zeile, nie eine Gesamtzahl."""
    if not s:
        return "  Keine Buecher mit geschlossenen Runden."
    zeilen = []
    for (waehrung, live) in sorted(s, key=lambda k: (not k[1], k[0])):
        t = s[(waehrung, live)]
        quote = (100.0 * t["treffer"] / t["n"]) if t["n"] else 0.0
        zeilen.append("  %-6s %-6s  %4d Runden  %+10.2f %s  Treffer %.0f %%"
                      % ("Live" if live else "Papier", waehrung,
                         t["n"], t["ergebnis"], waehrung, quote))
    return "\n".join(zeilen)


def bericht(von=None, bis=None):
    p = posten(von, bis)
    unbelastbar = [x for x in p if not x.get("belastbar")]
    t = ["=== Gesamtbilanz ==="]
    if von or bis:
        t.append("Fenster: %s bis %s"
                 % (von.date() if von else "Anfang",
                    bis.date() if bis else "heute"))
    t.append(zeilen_text(summe(p)))
    if unbelastbar:
        t.append("")
        t.append("  Nicht belastbar (zu wenige Runden, zaehlen nicht in "
                 "der Summe):")
        for x in unbelastbar:
            t.append("    %-16s %4d Runden" % (x["spur"], x["n"]))
    t.append("")
    t.append("  Papier und Live werden nicht verrechnet, Waehrungen nicht "
             "gemischt.")
    # Nicht len(p): summe() laesst jeden unbelastbaren Posten weg. Die
    # Zeile steht unter der Summe und muss deren Grundlage nennen, sonst
    # behauptet sie eine breitere Basis als die Rechnung hat.
    t.append("  %d Buecher in der Summe." % (len(p) - len(unbelastbar)))
    return "\n".join(t)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Summe ueber alle Buecher")
    p.add_argument("--tage", type=int, help="nur die letzten N Tage")
    p.add_argument("--seit", help="Fensteranfang, JJJJ-MM-TT")
    p.add_argument("--bis", help="Fensterende, JJJJ-MM-TT")
    a = p.parse_args()
    try:
        von, bis = zeitfenster.fenster(tage=a.tage, seit=a.seit, bis=a.bis)
    except ValueError as e:
        p.error(str(e))
    print(bericht(von, bis))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

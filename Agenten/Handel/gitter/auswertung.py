"""Auswertung des Gitter-Papierbuchs: traegt das Gitter nach Kosten?

Die Mechanik steht in `Handel/buchauswertung.py` - hier steht nur, was gitter
anders macht: seine Aktionsnamen, seine Zusatzspalten und die Gruppe, nach der
sich eine Frage lohnt.

Die Frage des Gitters ist nicht "welches Signal traegt", sondern "traegt der
Stufenabstand die Kosten beider Seiten". Jeder Zyklus hat per Bauart denselben
prozentualen Schritt; was schwankt, ist die Lage der Stufe (unten fuehrt zu
groesseren absoluten Schritten als oben). Deshalb wird nach STUFE gruppiert
und NICHT nach dem Schritt - ein Band ueber den Schritt waere ein Band ueber
eine einzige Zahl.

Aufruf:
    python auswertung.py              # Bilanz und Datenlage
    python auswertung.py --min 20     # strengere Schwelle fuer Hinweise
"""

import argparse
import json
import os
import sys
from pathlib import Path

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
for p in (HANDEL, HIER):
    if p not in sys.path:
        sys.path.insert(0, p)

import buchauswertung as b                                 # noqa: E402

# Risikostufe (HANDEL_RISIKO): liest die Dateien dieser Stufe
# (handelsjournal.mittel.csv). OHNE die Variable aendert sich nichts.
#
# Der Import ist AUSFALLSICHER: dieses Modul wird auch aus einem temp-Ordner
# geladen (Tagesbericht-Tests kopieren <spur>/auswertung.py dorthin), und dort
# liegt risikostufe.py eine Ebene hoeher nicht. Ein harter Import machte den
# Bericht dort unlesbar. Faellt er aus, bleibt es bei den Basisnamen - eine
# Auswertung darf nie daran scheitern, dass eine Stufe fehlt.
risikostufe = None
try:
    from importlib.util import (module_from_spec as _rs_mod,
                                spec_from_file_location as _rs_spec)
    _rs_datei = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "risikostufe.py")
    _rs_spec_obj = _rs_spec("risikostufe", _rs_datei)
    risikostufe = _rs_mod(_rs_spec_obj)
    _rs_spec_obj.loader.exec_module(risikostufe)
except Exception:                                            # noqa: BLE001
    risikostufe = None


def _stufe(pfad):
    """Dateiname dieser Risikostufe - ohne risikostufe.py der Basisname."""
    return risikostufe.datei(pfad) if risikostufe is not None else pfad


JOURNAL = _stufe(os.path.join(HIER, "handelsjournal.csv"))
WACHEN = os.path.join(HIER, "wachen.json")
ZUSTAND = _stufe(os.path.join(HIER, "zustand.json"))

MIN_AUSSTIEGE = b.MIN_AUSSTIEGE
MIN_JE_GRUPPE = b.MIN_JE_GRUPPE

ACTIONEN = ("AUSSTIEG",)
EXTRA = ("stufe", "gw_usd")

GRUPPEN = [("stufe", "Nach Stufe")]
BAENDER = []          # kein Band: der Stufenabstand ist bei allen Zyklen gleich

LEER = ("Noch kein geschlossener Zyklus im Journal - es gibt nichts zu messen.\n"
        "Die Bilanz entsteht, sobald eine Stufe gekauft und eine hoeher "
        "wieder verkauft ist.")


def _lies(pfad):
    try:
        with open(pfad, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _kosten(pfad=WACHEN):
    """Gebuehr + Slippage EINER Seite als Anteil (0.0015 = 0,15 %).

    gitter rechnet beide Saetze nacheinander je Seite - hier wird daraus ein
    Satz je Seite, wie es das Basismodul fuer die Rueckrechnung braucht.
    """
    w = _lies(pfad)
    return (w.get("slippage_pct", 0.05) + w.get("gebuehr_pct", 0.1)) / 100.0


def lade_ausstiege(pfad=JOURNAL, von=None, bis=None):
    return b.lade_zeilen(pfad, ACTIONEN, extra=EXTRA, name="inst",
                        von=von, bis=bis)


def kennzahlen(aus, k):
    return b.kennzahlen(aus, k)


def brutto_pct(netto_pct, kauf, verkauf=None):
    return b.brutto_pct(netto_pct, kauf, verkauf)


def hinweise(aus, k, min_ausstiege=MIN_AUSSTIEGE, min_je_gruppe=MIN_JE_GRUPPE):
    return b.hinweise(aus, k, baender=BAENDER, min_ausstiege=min_ausstiege,
                      min_je_gruppe=min_je_gruppe)


def zustandszeile(pfad=ZUSTAND):
    """Der Stand des Buches aus dem Zustand - Zahlen, die handeln.py schreibt
    (Buchwert, Stufen). Keine zweite Rechnung, nur eine Zeile."""
    z = _lies(pfad)
    leiter = z.get("leiter") or {}
    if not leiter:
        return "Gitter noch nicht angelegt."
    return ("Gitter %s: %d Stufen %.4f..%.4f (Schritt %.3f %%), %d belegt, "
            "%d armiert | Buchwert %.2f von %.2f (%.2f %%) | %d Zyklen"
            % (z.get("instrument", "?"), leiter.get("stufen", 0),
               leiter.get("unten", 0), leiter.get("oben", 0),
               leiter.get("schritt_prozent", 0),
               sum(1 for s in leiter.get("zustand", []) if s == "gekauft"),
               sum(1 for s in leiter.get("zustand", []) if s == "armiert"),
               z.get("buchwert_usd", 0.0), z.get("startwert_usd", 0.0),
               (z.get("buchwert_usd", 0.0) / z.get("startwert_usd", 1.0) - 1) * 100
               if z.get("startwert_usd") else 0.0,
               z.get("zyklen", 0)))


def bericht(aus, k, min_ausstiege=MIN_AUSSTIEGE):
    """Der ganze Ausdruck als Liste von Zeilen (testbar, ohne Druck)."""
    return (["=== GITTER Auswertung ===", zustandszeile()]
            + b.bericht(aus, k, gruppenliste=GRUPPEN, baender=BAENDER,
                        min_ausstiege=min_ausstiege, leer=LEER))


def kernzeile(pfad=JOURNAL, kosten=None, zustand=ZUSTAND):
    """Die Auswertung in EINER Zeile - fuer den Tagesbericht.

    Zwei Tatsachen in einer Zeile: der Stand des Buches (Buchwert gegen Start,
    Belegung der Leiter) und die Auswertung der geschlossenen Zyklen. Beides
    kommt aus EINER Quelle - der Stand aus zustand.json (geschrieben von
    handeln.py), die Zyklen aus dem gemeinsamen Basismodul.
    """
    k = _kosten() if kosten is None else kosten
    return "%s | %s" % (zustandszeile(zustand),
                        b.kernzeile(lade_ausstiege(pfad), k,
                                    min_ausstiege=MIN_AUSSTIEGE))


def kernzeilen(pfad=JOURNAL, kosten=None, max_hinweise=2):
    """Die Auswertung als wenige Zeilen - fuer die GUI (mehr Platz)."""
    k = _kosten() if kosten is None else kosten
    return b.kernzeilen(lade_ausstiege(pfad), k, min_ausstiege=MIN_AUSSTIEGE,
                        baender=BAENDER, max_hinweise=max_hinweise)


def _live():
    """Steht `handel_erlaubt` in der wachen.json auf true? Wirft nie.

    Eigene Funktion, damit der Merker pruefbar ist, ohne ein Journal
    aufzubauen: kennzahlen_kurz() kommt hier nur mit geschlossenen Runden
    ueberhaupt vorbei. Jeder Fehlschlag gilt als Papier - eine Spur
    faelschlich als Live zu zaehlen waere der teurere Irrtum. Deshalb auch
    `isinstance`: gueltiges JSON, das kein Objekt ist (`[]`, `42`, `null`),
    hat kein .get().
    """
    try:
        inhalt = json.loads(Path(WACHEN).read_text("utf-8"))
    except (OSError, ValueError):
        return False
    if not isinstance(inhalt, dict):
        return False
    return bool(inhalt.get("handel_erlaubt"))


def kennzahlen_kurz(von=None, bis=None):
    """Die Mindestform fuer die Gesamtbilanz - vier Zahlen und ein Merker.

    Angelegt, damit gesamtbilanz.py die fuenf Spuren mit eigener Auswertung
    addieren kann, ohne fuenf Sonderfaelle zu kennen. Die RECHNUNG ist
    unveraendert die dieses Moduls - hier steht nur die Uebergabe.
    `gv_usd` heisst hier `ergebnis`, weil auswertung_alle.kennzahlen() das
    Feld so nennt und die Bilanz nur EINEN Namen kennen soll.

    None heisst: diese Spur hat nichts auszusagen (kein Buch, keine
    geschlossenen Ausstiege).
    """
    k = kennzahlen(lade_ausstiege(von=von, bis=bis), _kosten())
    if not k.get("n"):
        return None
    live = _live()
    return {"n": k["n"],
            "ergebnis": k["gv_usd"],
            "treffer": k["treffer"],
            "waehrung": "USD",
            "live": live}


def main():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pfad", default=JOURNAL, help="Journal-CSV")
    p.add_argument("--min", type=int, default=MIN_AUSSTIEGE,
                   help="Ausstiege, ab denen ein Hinweis erlaubt ist")
    a = p.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for zeile in bericht(lade_ausstiege(a.pfad), _kosten(), min_ausstiege=a.min):
        print(zeile)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

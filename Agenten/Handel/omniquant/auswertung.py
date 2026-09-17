"""Auswertung des Omniquant-Papierbuchs: traegt die Prognose nach Kosten?

Die Mechanik steht in `Handel/buchauswertung.py` - hier steht nur, was
omniquant anders macht: seine Aktionsnamen, seine Zusatzspalten und die
Baender, in denen kalibriert wurde (Score und C/R). Eine eigene zweite
Formel fuer dieselbe Frage waere eine zweite Wahrheit.

Die Signalquelle ist der Prognose-Bericht; das Buch schreibt je Ausstieg
Score, C/R und die Buchgewinne/-verluste mit. Genau die braucht diese
Auswertung, um zu trennen, ob ein Stop zu eng war oder das Signal falsch.

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

MIN_AUSSTIEGE = b.MIN_AUSSTIEGE
MIN_JE_GRUPPE = b.MIN_JE_GRUPPE

ACTIONEN = ("AUSSTIEG",)
EXTRA = ("score", "cr", "mfe_pct", "mae_pct", "haltetage")

BAND_SCORE = (55.0, 60.0, 65.0, 70.0)
BAND_CR = (1.5, 2.0)

GRUPPEN = [("seite", "Nach Richtung"), ("grund", "Nach Ausstiegsgrund")]
BAENDER = [
    ("score", BAND_SCORE, "Nach Score",
     "Score %(band)s: %(n)d Ausstiege, nur %(plus)d im Plus, "
     "Ø %(netto)+.2f %% - Schwelle fuer dieses Band pruefen (Muster: "
     "_mindest_score_short in prognose.json)."),
    ("cr", BAND_CR, "Nach C/R",
     "C/R %(band)s: %(n)d Ausstiege, nur %(plus)d im Plus, "
     "Ø %(netto)+.2f %% - das Verhaeltnis traegt in diesem Band nicht."),
]

LEER = ("Noch kein Ausstieg im Journal - es gibt nichts zu messen.\n"
        "Die Bilanz entsteht, sobald die ersten Positionen geschlossen sind.")


# --- Zugang (Signatur wie bisher: Pfad bzw. Liste, Kosten) -------------------

def _zahl(x):
    return b.zahl(x)


def _kosten(pfad=WACHEN):
    """Slippage + Gebuehr EINER Seite als Anteil (0.0025 = 0,25 %).

    omniquant fasst beide Saetze zu einem zusammen (so rechnet handeln.py);
    das Basismodul kennt auch die getrennte Form des spiegel-Buchs.
    """
    try:
        import json
        with open(pfad, encoding="utf-8") as f:
            w = json.load(f)
    except (OSError, ValueError):
        return 0.0025
    return (w.get("slippage_pct", 0.15) + w.get("gebuehr_pct", 0.1)) / 100.0


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


def bericht(aus, k, min_ausstiege=MIN_AUSSTIEGE):
    """Der ganze Ausdruck als Liste von Zeilen (testbar, ohne Druck)."""
    return ["=== OMNIQUANT Auswertung ==="] + b.bericht(
        aus, k, gruppenliste=GRUPPEN, baender=BAENDER,
        min_ausstiege=min_ausstiege, leer=LEER)


def kernzeile(pfad=JOURNAL, kosten=None):
    """Die Auswertung in EINER Zeile - fuer den Tagesbericht."""
    k = _kosten() if kosten is None else kosten
    return b.kernzeile(lade_ausstiege(pfad), k, min_ausstiege=MIN_AUSSTIEGE)


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
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pfad", default=JOURNAL, help="Journal-CSV")
    p.add_argument("--min", type=int, default=MIN_AUSSTIEGE,
                   help="Ausstiege, ab denen ein Hinweis erlaubt ist")
    a = p.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    aus = lade_ausstiege(a.pfad)
    for zeile in bericht(aus, _kosten(), min_ausstiege=a.min):
        print(zeile)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

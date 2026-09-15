"""Auswertung des 1:1-Kopier-Buchs: traegt das Nachmachen auf TRADE-Ebene
nach Kosten?

Die Mechanik steht in `Handel/buchauswertung.py` - hier steht nur, was
kopier1zu1 anders macht als kopier/. Beide Buecher schliessen mit der Aktion
"schliessen" und schreiben die Kostensaetze je Zeile mit; der Unterschied
liegt im AUSSTIEGSGRUND: diese Spur kennt "verkauft" (das Vorbild hat auf
trades/batch verkauft - das primaere Signal dieser Spur), daneben die
Sicherheitsnetze stop/trail/frist und die beiden Sammelgruende kill und
herzschlag_alt. Die Gruppe "Nach Ausstiegsgrund" ist hier deshalb die
eigentliche Frage: traegt das Nachmachen, wenn man dem Vorbild WIRKLICH
folgt - oder kommt das Ergebnis aus den Netzen?

ABGRENZUNG zu handeln.py bilanz(): dort steht die TRADER-Sicht - welche
Wallets haben getragen, und deckt sich das mit der Rangliste. Hier steht die
BUCH-Sicht - traegt das 1:1-Nachmachen ueberhaupt, nach Kosten, und in
welcher Tiefe. Beides ist noetig und keine zweite Wahrheit.

ABGRENZUNG zu kopier/auswertung.py: dasselbe Muster, aber ein eigenes
Journal. Ein gemeinsamer Aufruf waere eine zweite Wahrheit ueber ZWEI
Buecher - die Spuren buchen verschieden (Portfolio-Diff gegen Trade-Ebene)
und muessen getrennt messbar bleiben.

Aufruf:
    python auswertung.py              # Bilanz des Buchs
    python auswertung.py --min 20     # strengere Schwelle fuer Hinweise
"""

import argparse
import json
import os
import sys

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

# Das Buch schreibt "schliessen" - dieselbe Aktionskonvention wie kopier und
# spiegel (handeln.py: pruefe_verkaeufe, pruefe_ausstiege, flach_stellen).
# Gross-/Kleinschreibung vergleicht buchauswertung selbst.
ACTIONEN = ("schliessen",)
EXTRA = ("kette", "symbol", "token", "marktkap_usd", "wallet")

GRUPPEN = [("kette", "Nach Kette"), ("grund", "Nach Ausstiegsgrund"),
           ("wallet", "Nach Vorbild-Wallet")]

# Das Tor des Feeds ist die Marktkapitalisierung (marketcap_band_usd in den
# Wachen - den Wert DORT lesen, nicht hier wiederholen). Diese Baender fragen,
# ob die Tiefe traegt: Pump.fun-Buecher sind duenn, und duenn heisst, dass ein
# Nachahmer den Preis macht. Auf Trade-Ebene wiegt das schwerer als bei
# kopier/, weil hier JEDER Kauf des Vorbilds gebucht wird - auch Nachkaeufe.
BAND_MK = (250_000, 1_000_000, 5_000_000)
BAENDER = [
    ("marktkap_usd", BAND_MK, "Nach Marktkapitalisierung",
     "Marktkapitalisierung %(band)s: %(n)d Kopien, nur %(plus)d im Plus, "
     "Ø %(netto)+.2f %% - in dieser Tiefe traegt das Nachmachen nicht "
     "(Slippage-Annahme in wachen.json pruefen, nicht das Band zuerst)."),
]

LEER = ("Noch keine geschlossene Runde im Journal - es gibt nichts zu messen.\n"
        "Die Bilanz entsteht, sobald die erste Kopie ausgestiegen ist "
        "(Vorbild verkauft, Stop, Trail oder Frist).")


def _wachen(pfad=WACHEN):
    try:
        with open(pfad, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _kosten(pfad=WACHEN):
    """Die zwei Ausfuehrungsfaktoren des Buchs aus seinen Wachen."""
    w = _wachen(pfad)
    return b.faktoren(w.get("slippage_pct", 5.0), w.get("gebuehr_pct", 1.0))


def _zahl(x):
    return b.zahl(x)


def _marktkap_je_token(pfad=JOURNAL):
    """Die Marktkapitalisierung beim KAUF, je Token aus den eroeffnen-Zeilen.

    Die schliessen-Zeile fuehrt keine Marktkap (handeln.py schreibt sie nur
    beim Eroeffnen) - ohne diese Karte stuende jedes Band auf "?".
    """
    import csv
    karte = {}
    if not os.path.exists(pfad):
        return karte
    with open(pfad, newline="", encoding="utf-8") as f:
        for zeile in csv.DictReader(f):
            if (zeile.get("aktion") or "").strip().lower() != "eroeffnen":
                continue
            token = zeile.get("token")
            mk = b.zahl(zeile.get("marktkap_usd"))
            if token and mk is not None:
                karte[token] = mk
    return karte


def lade_ausstiege(pfad=JOURNAL):
    """Geschlossene Kopien - mit Kostensaetzen und der Tiefe beim Kauf."""
    aus = b.lade_zeilen(pfad, ACTIONEN, extra=EXTRA, mit_kosten=True)
    karte = _marktkap_je_token(pfad)
    for a in aus:
        if a.get("marktkap_usd") is None and a.get("token"):
            a["marktkap_usd"] = karte.get(a["token"])
    return aus


def kennzahlen(aus, k):
    return b.kennzahlen(aus, k)


def brutto_pct(netto_pct, kauf, verkauf=None):
    return b.brutto_pct(netto_pct, kauf, verkauf)


def hinweise(aus, k, min_ausstiege=MIN_AUSSTIEGE, min_je_gruppe=MIN_JE_GRUPPE):
    return b.hinweise(aus, k, baender=BAENDER, min_ausstiege=min_ausstiege,
                      min_je_gruppe=min_je_gruppe, mit_stop_hinweis=False)


def bericht(aus, k, min_ausstiege=MIN_AUSSTIEGE):
    """Der ganze Ausdruck als Liste von Zeilen (testbar, ohne Druck)."""
    return ["=== KOPIER1ZU1 Auswertung ==="] + b.bericht(
        aus, k, gruppenliste=GRUPPEN, baender=BAENDER,
        min_ausstiege=min_ausstiege, mit_stop_hinweis=False, leer=LEER)


def kernzeile(pfad=JOURNAL, kosten=None):
    """Die Auswertung in EINER Zeile - fuer den Tagesbericht.

    Ohne geschlossene Runde steht die Datenlage da, nicht eine Null-Bilanz:
    heute ist genau das der Normalfall (3 offene Kopien, kein Ausstieg).
    """
    k = _kosten() if kosten is None else kosten
    return b.kernzeile(lade_ausstiege(pfad), k, min_ausstiege=MIN_AUSSTIEGE)


def kernzeilen(pfad=JOURNAL, kosten=None, max_hinweise=2):
    """Die Auswertung als wenige Zeilen - fuer die GUI (mehr Platz)."""
    k = _kosten() if kosten is None else kosten
    return b.kernzeilen(lade_ausstiege(pfad), k, min_ausstiege=MIN_AUSSTIEGE,
                        baender=BAENDER, max_hinweise=max_hinweise)


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

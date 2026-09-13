"""Auswertung des Omniquant-Papierbuchs: traegt die Prognose nach Kosten?

Das Stueck, das der Spur bis hier fehlte: handeln.py schreibt ein Journal,
aber niemand zerlegte es. Ohne diese Schleife kann das System nicht lernen -
die Tore in prognose.json bleiben auf dem Stand ihrer Kalibrierung, und
niemand sieht, ob sie noch stimmen.

WAS SIE TUT
-----------
Sie liest handelsjournal.csv (nur AUSSTIEG-Zeilen), rechnet die Bilanz nach
Kosten und zerlegt sie nach Richtung, Ausstiegsgrund, Score-Band und
C/R-Band. Sie nennt ausserdem die Rendite vor Kosten (aus der Netto-Rendite
zurueckgerechnet, der Kostenanteil ist ja bekannt) - erst dieser Vergleich
zeigt, wie viel die Prognose vor Kosten verdient und wie viel davon die
Ausfuehrung frisst.

WAS SIE NICHT TUT
-----------------
Sie schreibt nichts, sie handelt nicht, sie fasst die Tore nicht an. Und
sie behauptet nichts aus zu wenig Daten: unter MIN_AUSSTIEGE Ausstiegen gibt
es Rohzahlen und den Satz, dass es fuer eine Schwelle nicht reicht, unter
MIN_JE_GRUPPE je Gruppe keinen Hinweis. Ein Tor aus drei Beobachtungen zu
drehen ist Rauschen, kein Lernen.

Aufruf:
    python auswertung.py              # Bilanz und Datenlage
    python auswertung.py --min 20     # strengere Schwelle fuer Hinweise
"""

import argparse
import csv
import json
import os
import statistics
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
JOURNAL = os.path.join(HIER, "handelsjournal.csv")
WACHEN = os.path.join(HIER, "wachen.json")

# Ab wie vielen Ausstiegen eine Schwelle ueberhaupt etwas heissen darf, und
# ab wie vielen je Gruppe ein Hinweis erlaubt ist. Beides bewusst hoch: die
# Tore wurden an 41 Maerkten kalibriert, drei Trades sind kein Gegenbeweis.
MIN_AUSSTIEGE = 8
MIN_JE_GRUPPE = 5

BAND_SCORE = (55.0, 60.0, 65.0, 70.0)
BAND_CR = (1.5, 2.0)


def _zahl(x):
    """Ein Journal-Feld als Zahl lesen - leer/None/'None' -> None."""
    s = str(x if x is not None else "").strip()
    if not s or s == "None":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def lade_ausstiege(pfad=JOURNAL):
    """Alle AUSSTIEG-Zeilen des Journals, Zahlen geparst, alte Felder -> None.

    Eine Zeile ohne Einsatz oder Wert ist keine Messung und faellt raus -
    ein Platzhalter waere schlimmer als eine fehlende Zeile, weil er die
    Bilanz mit Nullen verzerrt.
    """
    if not os.path.exists(pfad):
        return []
    aus = []
    with open(pfad, newline="", encoding="utf-8") as f:
        for zeile in csv.DictReader(f):
            if (zeile.get("aktion") or "").strip().upper() != "AUSSTIEG":
                continue
            einsatz = _zahl(zeile.get("einsatz_usd"))
            wert = _zahl(zeile.get("wert_usd"))
            if not einsatz or wert is None:
                continue
            aus.append({
                "zeit": zeile.get("zeit") or "",
                "inst": zeile.get("inst") or "",
                "seite": (zeile.get("seite") or "").strip().lower(),
                "grund": (zeile.get("grund") or "").strip().lower(),
                "einsatz": einsatz,
                "wert": wert,
                "netto_pct": (wert / einsatz - 1.0) * 100.0,
                "score": _zahl(zeile.get("score")),
                "cr": _zahl(zeile.get("cr")),
                "mfe_pct": _zahl(zeile.get("mfe_pct")),
                "mae_pct": _zahl(zeile.get("mae_pct")),
                "haltetage": _zahl(zeile.get("haltetage")),
            })
    return aus


def _kosten(pfad=WACHEN):
    """Slippage + Gebuehr einer Seite als Anteil (0.0025 = 0,25 %)."""
    try:
        with open(pfad, encoding="utf-8") as f:
            w = json.load(f)
    except (OSError, ValueError):
        return 0.0025
    return (w.get("slippage_pct", 0.15) + w.get("gebuehr_pct", 0.1)) / 100.0


def brutto_pct(netto_pct, k):
    """Rendite vor Kosten aus der Rendite nach Kosten zurueckrechnen.

    Das Buch rechnet ergebnis = einsatz * (1 + bewegung) * (1-k)/(1+k).
    Nach bewegung umgestellt: ergebnis/einsatz * (1+k)/(1-k) - 1. Beide
    Seiten der Ausfuehrung sind damit herausgerechnet, nicht geschaetzt.
    """
    return ((1.0 + netto_pct / 100.0) * (1.0 + k) / (1.0 - k) - 1.0) * 100.0


def _median(werte):
    return statistics.median(werte) if werte else None


def kennzahlen(aus, k):
    """Die Bilanz ueber alle Ausstiege - Betraege und Prozente."""
    n = len(aus)
    if not n:
        return {"n": 0}
    einsatz = sum(a["einsatz"] for a in aus)
    wert = sum(a["wert"] for a in aus)
    netto = [a["netto_pct"] for a in aus]
    brutto = [brutto_pct(x, k) for x in netto]
    treffer = [a for a in aus if a["wert"] > a["einsatz"]]
    mfe = [a["mfe_pct"] for a in aus if a["mfe_pct"] is not None]
    mae = [a["mae_pct"] for a in aus if a["mae_pct"] is not None]
    tage = [a["haltetage"] for a in aus if a["haltetage"] is not None]
    return {
        "n": n, "einsatz": einsatz, "wert": wert,
        "gv_usd": wert - einsatz,
        "gv_pct": (wert / einsatz - 1.0) * 100.0 if einsatz else 0.0,
        "brutto_usd": einsatz * sum(brutto) / 100.0,
        "brutto_pct": sum(brutto) / n,
        "netto_pct": sum(netto) / n,
        "median_pct": _median(netto),
        "best": max(netto), "schlecht": min(netto),
        "treffer": len(treffer),
        "quote": len(treffer) / n * 100.0,
        "mfe": _median(mfe), "mae": _median(mae),
        "tage": _median(tage),
    }


def _gruppen(aus, schluessel):
    """Ausstiege nach einem Felde gruppieren, Reihenfolge stabil."""
    g = {}
    for a in aus:
        g.setdefault(a[schluessel] or "?", []).append(a)
    return g


def _band(x, kanten):
    """Ein Wert in ein Band einordnen ('65-70'). None -> '?'."""
    if x is None:
        return "?"
    for i, k in enumerate(kanten):
        if x < k:
            return "< %g" % kanten[0] if i == 0 else "%g-%g" % (
                kanten[i - 1], k)
    return ">= %g" % kanten[-1]


def _nach_band(aus, feld, kanten):
    g = {}
    for a in aus:
        g.setdefault(_band(a[feld], kanten), []).append(a)
    return g


def _zeile_gruppe(name, gruppe, k):
    netto = [a["netto_pct"] for a in gruppe]
    q = sum(1 for a in gruppe if a["wert"] > a["einsatz"]) / len(gruppe) * 100
    return "  %-14s %2d Ausstiege  %3.0f %% Treffer  Ø %+6.2f %%  (vor Kosten Ø %+6.2f %%)" % (
        name, len(gruppe), q, sum(netto) / len(netto),
        sum(brutto_pct(x, k) for x in netto) / len(netto))


def hinweise(aus, k, min_ausstiege=MIN_AUSSTIEGE, min_je_gruppe=MIN_JE_GRUPPE):
    """Was die Zahlen hergeben - und nur das.

    Ein Hinweis braucht genug Daten: unter min_ausstiege insgesamt gibt es
    keinen, und je Gruppe erst ab min_je_gruppe Beobachtungen. Die
    Formulierung ist bewusst eine Frage ('pruefen'), keine Anweisung - die
    Tore wurden an 41 Maerkten kalibriert, ein Band mit wenigen Trades ist
    kein Gegenbeweis.
    """
    if len(aus) < min_ausstiege:
        return ["Datenlage: %d Ausstiege, %d noetig fuer einen Schwellen-Hinweis. "
                "Die Tore bleiben, wie sie sind." % (len(aus), min_ausstiege)]
    raus = []
    for name, gruppe in _nach_band(aus, "score", BAND_SCORE).items():
        if name == "?" or len(gruppe) < min_je_gruppe:
            continue
        quote = sum(1 for a in gruppe if a["wert"] > a["einsatz"]) / len(gruppe)
        netto = sum(a["netto_pct"] for a in gruppe) / len(gruppe)
        if quote < 0.5 and netto < 0:
            raus.append("Score %s: %d Ausstiege, nur %d im Plus, Ø %+.2f %% - "
                        "Schwelle fuer dieses Band pruefen (Muster: "
                        "_mindest_score_short in prognose.json)."
                        % (name, len(gruppe), round(quote * len(gruppe)), netto))
    kopf = [a for a in aus if a["mfe_pct"] is not None]
    if len(kopf) >= min_ausstiege:
        mfe = sum(a["mfe_pct"] for a in kopf) / len(kopf)
        stop = [a for a in kopf if a["grund"] == "stop"]
        if stop and mfe > 0.5:
            raus.append("Stop: %d von %d gerissen, mittlerer Buchgewinn vorher "
                        "%+.2f %% - ein Teil lief erst ins Plus. Stop-Breite "
                        "gegen Streuung pruefen (ATR-Kandidat), aber erst nach "
                        "der Tor-Kalibrierung: sonst misst man zwei Variablen "
                        "gleichzeitig." % (len(stop), len(kopf), mfe))
    return raus or ["Keine Auffaelligkeit, die eine Schwelle rechtfertigt."]


def bericht(aus, k, min_ausstiege=MIN_AUSSTIEGE):
    """Der ganze Ausdruck als Liste von Zeilen (testbar, ohne Druck)."""
    z = ["=== OMNIQUANT Auswertung ==="]
    if not aus:
        z.append("Noch kein Ausstieg im Journal - es gibt nichts zu messen.")
        z.append("Die Bilanz entsteht, sobald die ersten Positionen "
                 "geschlossen sind.")
        return z
    kz = kennzahlen(aus, k)
    z.append("Bilanz (%d Ausstiege)" % kz["n"])
    z.append("  Einsatz gesamt            %10.2f USD" % kz["einsatz"])
    z.append("  Wert gesamt               %10.2f USD" % kz["wert"])
    z.append("  Ergebnis                  %+10.2f USD (%+.2f %%)"
             % (kz["gv_usd"], kz["gv_pct"]))
    z.append("  davon Kosten              %10.2f USD"
             % (kz["einsatz"] * kz["brutto_pct"] / 100.0 - kz["gv_usd"]))
    z.append("  vor Kosten (Ø je Position) %+9.2f %%" % kz["brutto_pct"])
    z.append("  nach Kosten (Ø je Position) %+8.2f %%  (Median %+.2f %%)"
             % (kz["netto_pct"], kz["median_pct"]))
    z.append("  bester / schlechtester     %+.2f %% / %+.2f %%"
             % (kz["best"], kz["schlecht"]))
    z.append("  Treffer (Wert > Einsatz)   %d von %d (%.0f %%)"
             % (kz["treffer"], kz["n"], kz["quote"]))
    if kz["mfe"] is not None:
        z.append("  Buchgewinn/-verlust (MFE/MAE, Median) %+.2f %% / %+.2f %%"
                 % (kz["mfe"], kz["mae"]))
    if kz["tage"] is not None:
        z.append("  mittlere Haltedauer       %.1f Tage" % kz["tage"])
    z.append("")
    z.append("Nach Richtung")
    for name, gruppe in _gruppen(aus, "seite").items():
        z.append(_zeile_gruppe(name, gruppe, k))
    z.append("Nach Ausstiegsgrund")
    for name, gruppe in _gruppen(aus, "grund").items():
        z.append(_zeile_gruppe(name, gruppe, k))
    z.append("Nach Score")
    for name, gruppe in _nach_band(aus, "score", BAND_SCORE).items():
        z.append(_zeile_gruppe(name, gruppe, k))
    z.append("Nach C/R")
    for name, gruppe in _nach_band(aus, "cr", BAND_CR).items():
        z.append(_zeile_gruppe(name, gruppe, k))
    z.append("")
    z.append("Hinweise")
    for h in hinweise(aus, k, min_ausstiege=min_ausstiege):
        z.append("  - " + h)
    return z


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

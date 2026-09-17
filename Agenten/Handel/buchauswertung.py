"""Die gemeinsame Auswertung der Papierbuecher im Handel-Baum.

Warum es dieses Modul gibt: Jede Spur fuehrt ein eigenes Journal, aber die
Frage ist ueberall dieselbe - traegt das Buch nach Kosten? Bis hierher hatte
nur omniquant eine Auswertung. Sie fuer spiegel abzuschreiben waere eine
zweite Formel fuer dieselbe Frage gewesen, und zwei Formeln laufen
auseinander. Also steht die Mechanik hier einmal, und jede Spur bringt nur
mit, was wirklich anders ist: ihre Aktionsnamen, ihre Spalten, ihre Baender.

WAS HIER GLEICH IST
  - Bilanz in USD, Rendite je Position, Median, Trefferquote
  - der Schnitt VOR und NACH Kosten (zurueckgerechnet, nicht geschaetzt)
  - Buchgewinn/-verlust (MFE/MAE), wenn das Buch sie mitschreibt
  - Gruppen und Baender, Hinweise - und die Regel, dass unter
    MIN_AUSSTIEGE Beobachtungen nichts behauptet wird

WAS JEDE SPUR MITBRINGT
  - `aktionen`: welche Journal-Aktionen zaehlen (omniquant "AUSSTIEG",
    spiegel "schliessen" - Gross-/Kleinschreibung ist egal, weil die
    Journale sie historisch verschieden schreiben)
  - `extra`: Zusatzspalten fuer Gruppen/Baender (score, cr, kette, ...)
  - die Baender und Gruppentitel fuer den Bericht

KOSTEN: ZWEI FAKTOREN, NICHT EINE ZAHL
  Ein Buch kann seine Kosten verschieden aufteilen - omniquant fasst
  slippage + gebuehr zu einem Satz je Seite zusammen, das spiegel-Buch
  rechnet beide Saetze nacheinander ((1+s)(1+g) beim Kauf, (1-s)(1-g) beim
  Verkauf). Beide Faelle sind hier abgebildet (`faktoren`, `brutto_pct`),
  damit "vor Kosten" in beiden Buechern dieselbe Bedeutung hat.
"""

import csv
import os
import statistics

import zeitfenster

MIN_AUSSTIEGE = 8
MIN_JE_GRUPPE = 5

# Felder, die jedes Journal der Spuren in dieser Form traegt.
PFLICHT = ("einsatz_usd", "wert_usd")


def zahl(x):
    """Ein Journal-Feld als Zahl lesen - leer/None/'None' -> None."""
    s = str(x if x is not None else "").strip()
    if not s or s == "None":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def median(werte):
    return statistics.median(werte) if werte else None


def faktoren(slippage_pct, gebuehr_pct):
    """(kauf, verkauf) - Kauf teurer, Verkauf billiger, beide Saetze je Seite.

    Das spiegel-Buch rechnet genau so: (1+s)(1+g) beim Kauf, (1-s)(1-g) beim
    Verkauf. omniquant fasst slippage+gebuehr zu EINEM Satz zusammen und
    uebergibt ihn als slippage mit gebuehr=0 - dieselbe Formel mit anderer
    Aufteilung, die Zahlen des Buchs bleiben unveraendert.
    """
    s = (slippage_pct or 0.0) / 100.0
    g = (gebuehr_pct or 0.0) / 100.0
    return (1.0 + s) * (1.0 + g), (1.0 - s) * (1.0 - g)


def brutto_pct(netto_pct, kauf, verkauf=None):
    """Rendite vor Kosten aus der Rendite nach Kosten zurueckrechnen.

    Ein Buch rechnet ergebnis = einsatz * (1+bewegung) * verkauf/kauf.
    Nach bewegung umgestellt: (1+netto) * kauf/verkauf - 1. Beide
    Ausfuehrungsseiten sind damit herausgerechnet, nicht geschaetzt.

    Ein SKALAR bei kauf bedeutet den symmetrischen Fall (kauf = 1+k,
    verkauf = 1-k) - so rechnet omniquant mit einem Satz je Seite. Zwei
    Faktoren sind der getrennte Fall des spiegel-Buchs.
    """
    if verkauf is None:
        k = kauf
        kauf, verkauf = 1.0 + k, 1.0 - k
    return ((1.0 + netto_pct / 100.0) * kauf / verkauf - 1.0) * 100.0


def lade_zeilen(pfad, aktionen, extra=(), mit_kosten=False, name=None,
                 von=None, bis=None):
    """Journal-Zeilen einer Aktion laden, Zahlen geparst.

    aktionen: Menge zulaessiger Aktionsnamen (Kleinschreibung wird
    verglichen). Zeilen ohne Einsatz oder Wert sind keine Messung und
    fallen raus - ein Platzhalter waere schlimmer als eine fehlende Zeile,
    weil er die Bilanz mit Nullen verzerrt.

    mit_kosten=True liest slippage_pct/gebuehr_pct der Zeile, wenn sie da
    stehen (spiegel schreibt sie mit; sonst gilt der Satz der Spur).

    name: Spalten, aus denen der Instrumentname kommt (erste gefundene).

    von/bis: Zeitfenster ueber die Spalte `zeit`. Vorgabe None/None heisst
    alles - ein Aufruf ohne Fenster liest dasselbe wie vorher.
    """
    if not os.path.exists(pfad):
        return []
    akt = {a.lower() for a in aktionen}
    aus = []
    with open(pfad, newline="", encoding="utf-8") as f:
        for zeile in csv.DictReader(f):
            if not zeitfenster.im_fenster(zeile, von, bis):
                continue
            if (zeile.get("aktion") or "").strip().lower() not in akt:
                continue
            einsatz = zahl(zeile.get("einsatz_usd"))
            wert = zahl(zeile.get("wert_usd"))
            if not einsatz or wert is None:
                continue
            e = {
                "zeit": zeile.get("zeit") or "",
                "name": "",
                "grund": (zeile.get("grund") or "").strip().lower(),
                "einsatz": einsatz,
                "wert": wert,
                "netto_pct": (wert / einsatz - 1.0) * 100.0,
            }
            # Der Instrumentname steht je Spur in einer anderen Spalte
            # (omniquant: inst, spiegel: symbol). Beide bleiben unter ihrem
            # Journal-Namen lesbar, "name" ist der gemeinsame Zugriff.
            for spalte in ("inst", "symbol", "token"):
                if zeile.get(spalte):
                    e[spalte] = zeile[spalte]
                    if not e["name"]:
                        e["name"] = zeile[spalte]
            for feld in extra:
                # Zusatzspalten sind nicht immer Zahlen: kette/symbol sind
                # Text, marktkap_usd/score sind Zahlen. Erst als Zahl
                # versuchen, sonst den Rohwert behalten - sonst liest sich
                # jede Kette als "?".
                roh = zeile.get(feld)
                als_zahl = zahl(roh)
                e[feld] = (als_zahl if als_zahl is not None
                           else ((roh or "").strip() or None))
            if mit_kosten:
                s = zahl(zeile.get("slippage_pct"))
                g = zahl(zeile.get("gebuehr_pct"))
                e["kosten"] = faktoren(s, g) if (s is not None or g is not None) else None
            aus.append(e)
    return aus


def _kz_faktoren(a, k):
    """Die zwei Ausfuehrungsfaktoren einer Zeile.

    k darf ein Skalar (symmetrischer Satz je Seite) oder ein (kauf, verkauf)
    sein; eine Zeile mit eigenen Kostenspalten hat Vorrang.
    """
    kk = a.get("kosten")
    if kk:
        return kk
    if isinstance(k, (tuple, list)):
        return k
    return 1.0 + k, 1.0 - k


def kennzahlen(aus, k):
    """Die Bilanz ueber alle Ausstiege - Betraege und Prozente."""
    n = len(aus)
    if not n:
        return {"n": 0}
    einsatz = sum(a["einsatz"] for a in aus)
    wert = sum(a["wert"] for a in aus)
    netto = [a["netto_pct"] for a in aus]
    brutto = [brutto_pct(a["netto_pct"], *_kz_faktoren(a, k)) for a in aus]
    treffer = [a for a in aus if a["wert"] > a["einsatz"]]
    mfe = [a["mfe_pct"] for a in aus if a.get("mfe_pct") is not None]
    mae = [a["mae_pct"] for a in aus if a.get("mae_pct") is not None]
    tage = [a["haltetage"] for a in aus if a.get("haltetage") is not None]
    return {
        "n": n, "einsatz": einsatz, "wert": wert,
        "gv_usd": wert - einsatz,
        "gv_pct": (wert / einsatz - 1.0) * 100.0 if einsatz else 0.0,
        "brutto_usd": einsatz * sum(brutto) / 100.0,
        "brutto_pct": sum(brutto) / n,
        "netto_pct": sum(netto) / n,
        "median_pct": median(netto),
        "best": max(netto), "schlecht": min(netto),
        "treffer": len(treffer),
        "quote": len(treffer) / n * 100.0,
        "mfe": median(mfe), "mae": median(mae),
        "tage": median(tage),
    }


def gruppen(aus, schluessel):
    """Ausstiege nach einem Felde gruppieren, Reihenfolge stabil."""
    g = {}
    for a in aus:
        schluesselwert = a.get(schluessel)
        if isinstance(schluesselwert, float):
            schluesselwert = "%g" % schluesselwert
        g.setdefault(str(schluesselwert or "?"), []).append(a)
    return g


def _kompakt(x):
    """Zahlen fuer Bandnamen lesbar machen: 250000 -> 250k, 1e6 -> 1M."""
    if abs(x) >= 1_000_000:
        return "%gM" % (x / 1_000_000.0)
    if abs(x) >= 1_000:
        return "%gk" % (x / 1_000.0)
    return "%g" % x


def band(x, kanten):
    """Ein Wert in ein Band einordnen ('65-70', '< 250k'). None -> '?'."""
    if x is None:
        return "?"
    for i, k in enumerate(kanten):
        if x < k:
            return ("< " + _kompakt(kanten[0])) if i == 0 else (
                "%s-%s" % (_kompakt(kanten[i - 1]), _kompakt(k)))
    return ">= " + _kompakt(kanten[-1])


def nach_band(aus, feld, kanten):
    g = {}
    for a in aus:
        g.setdefault(band(a.get(feld), kanten), []).append(a)
    return g


def zeile_gruppe(name, gruppe, k):
    netto = [a["netto_pct"] for a in gruppe]
    q = sum(1 for a in gruppe if a["wert"] > a["einsatz"]) / len(gruppe) * 100
    brutto = sum(brutto_pct(a["netto_pct"], *_kz_faktoren(a, k))
                 for a in gruppe) / len(gruppe)
    return ("  %-14s %2d Ausstiege  %3.0f %% Treffer  Ø %+6.2f %%  "
            "(vor Kosten Ø %+6.2f %%)"
            % (name, len(gruppe), q, sum(netto) / len(netto), brutto))


def hinweise(aus, k, baender=(), min_ausstiege=MIN_AUSSTIEGE,
             min_je_gruppe=MIN_JE_GRUPPE, mit_stop_hinweis=True):
    """Was die Zahlen hergeben - und nur das.

    Unter min_ausstiege insgesamt gibt es keinen Hinweis, je Band erst ab
    min_je_gruppe Beobachtungen. Die Formulierung ist eine Frage
    ('pruefen'), keine Anweisung: die Tore wurden an vielen Maerkten
    kalibriert, ein Band mit wenigen Trades ist kein Gegenbeweis.

    baender: Liste von (feld, kanten, titel, muster) - muster ist der Text
    des Hinweises, wenn ein Band schlecht traegt.
    """
    if len(aus) < min_ausstiege:
        return ["Datenlage: %d Ausstiege, %d noetig fuer einen Schwellen-Hinweis. "
                "Die Tore bleiben, wie sie sind."
                % (len(aus), min_ausstiege)]
    raus = []
    for feld, kanten, _titel, muster in baender:
        for name, gruppe in nach_band(aus, feld, kanten).items():
            if name == "?" or len(gruppe) < min_je_gruppe:
                continue
            quote = sum(1 for a in gruppe
                        if a["wert"] > a["einsatz"]) / len(gruppe)
            netto = sum(a["netto_pct"] for a in gruppe) / len(gruppe)
            if quote < 0.5 and netto < 0:
                raus.append(muster % {
                    "band": name, "n": len(gruppe),
                    "plus": round(quote * len(gruppe)), "netto": netto})
    kopf = [a for a in aus if a.get("mfe_pct") is not None]
    if mit_stop_hinweis and len(kopf) >= min_ausstiege:
        mfe = sum(a["mfe_pct"] for a in kopf) / len(kopf)
        stop = [a for a in kopf if a["grund"] == "stop"]
        if stop and mfe > 0.5:
            raus.append("Stop: %d von %d gerissen, mittlerer Buchgewinn vorher "
                        "%+.2f %% - ein Teil lief erst ins Plus. Stop-Breite "
                        "gegen Streuung pruefen (ATR-Kandidat), aber erst nach "
                        "der Tor-Kalibrierung: sonst misst man zwei Variablen "
                        "gleichzeitig." % (len(stop), len(kopf), mfe))
    return raus or ["Keine Auffaelligkeit, die eine Schwelle rechtfertigt."]


def bericht(aus, k, gruppenliste=(), baender=(), min_ausstiege=MIN_AUSSTIEGE,
            mit_stop_hinweis=True, leer="Noch kein Ausstieg im Journal - es "
            "gibt nichts zu messen."):
    """Der ganze Ausdruck als Liste von Zeilen (testbar, ohne Druck).

    gruppenliste: [(feld, titel)] - Gruppenabschnitte.
    baender:      [(feld, kanten, titel, muster)] - Bandabschnitte.
    """
    z = []
    if not aus:
        z.append(leer)
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
    for feld, titel in gruppenliste:
        g = gruppen(aus, feld)
        if not g:
            continue
        z.append("")
        z.append(titel)
        for name, gruppe in g.items():
            z.append(zeile_gruppe(name, gruppe, k))
    for feld, kanten, titel, _muster in baender:
        g = nach_band(aus, feld, kanten)
        if not g:
            continue
        z.append("")
        z.append(titel)
        for name, gruppe in g.items():
            z.append(zeile_gruppe(name, gruppe, k))
    z.append("")
    z.append("Hinweise")
    for h in hinweise(aus, k, baender=baender, min_ausstiege=min_ausstiege,
                      mit_stop_hinweis=mit_stop_hinweis):
        z.append("  - " + h)
    return z


def kernzeile(aus, k, min_ausstiege=MIN_AUSSTIEGE, leer=None, titel="Auswertung"):
    """Die Auswertung in EINER Zeile - fuer den Tagesbericht.

    Gleiche Quelle wie bericht(): eine zweite Formel fuer dieselbe Frage
    waere eine zweite Wahrheit. Ohne Ausstiege steht die Datenlage da, nicht
    eine Null-Bilanz - die liest sich sonst wie ein Ergebnis.
    """
    if not aus:
        return "%s: %s" % (titel, leer or
                           "noch kein Ausstieg (Schwellen ab %d Ausstiegen)"
                           % min_ausstiege)
    kz = kennzahlen(aus, k)
    return ("%s: %d Ausstiege, %+.2f USD (%+.2f %% je Position nach Kosten, "
            "%+.2f %% davor), Treffer %d/%d"
            % (titel, kz["n"], kz["gv_usd"], kz["netto_pct"],
               kz["brutto_pct"], kz["treffer"], kz["n"]))


def kernzeilen(aus, k, min_ausstiege=MIN_AUSSTIEGE, baender=(),
               max_hinweise=2, leer=None):
    """Die Auswertung als wenige Zeilen - fuer die GUI (mehr Platz)."""
    if not aus:
        return [leer or ("noch kein Ausstieg — Schwellen ab %d Ausstiegen"
                         % min_ausstiege)]
    kz = kennzahlen(aus, k)
    zeilen = [
        "%d Ausstiege · Bilanz %+.2f USD · %+.2f %% je Position "
        "(Median %+.2f %%)"
        % (kz["n"], kz["gv_usd"], kz["netto_pct"], kz["median_pct"]),
        "vor Kosten %+.2f %% · nach Kosten %+.2f %% · Treffer %d/%d (%.0f %%)"
        % (kz["brutto_pct"], kz["netto_pct"], kz["treffer"], kz["n"],
           kz["quote"]),
    ]
    if kz["mfe"] is not None:
        zeilen.append("Buchgewinn/-verlust (Median) %+.2f %% / %+.2f %%"
                      % (kz["mfe"], kz["mae"]))
    for h in hinweise(aus, k, baender=baender,
                      min_ausstiege=min_ausstiege)[:max_hinweise]:
        zeilen.append(h)
    return zeilen

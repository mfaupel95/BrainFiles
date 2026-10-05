"""T-122 (b): der Spannenweg der iv_waelle wurde nur an BTC gemessen (400 Tage,
ein Regime). Dieser Lauf misst ihn an EINEM ZWEITEN Instrument (ETH) und
vergleicht die beiden Kopfzahlen.

Aufruf (aus Agenten/Handel/iv_waelle):
    ../../scanner/.venv/Scripts/python.exe spannenweg_zweites_instrument.py

Kein Blick nach vorn: die Spanne fuer Tag D kommt aus dem DVOL-Schluss von
Tag D-1 und dem Tageseroeffnungskurs. Gebuehr 0,05 % je Seite, dieselbe
Annahme wie NOTIZ.md. Nur lesend (oeffentliche Deribit-Schnittstelle).

Ergebnis geht nach stdout; nichts wird gebucht, nichts geschrieben ausser dem
Cache der Datensammlung (Agenten/Handel/iv_waelle/cache/).
"""
import os
import statistics
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)

import backtest_iv_waelle as b      # noqa: E402
import daten                        # noqa: E402
import iv_waelle as k               # noqa: E402

GEBUEHR = 0.0005          # je Seite, wie NOTIZ.md
TAGE = 400


def messe(waehrung, instrument):
    """Dieselbe Rechnung wie NOTIZ.md, nur fuer eine andere Waehrung.

    Achtung: `pruefe_fade()` nimmt die Gebuehr aus dem Modulkonstanten
    GEBUEHR_JE_SEITE, nicht als Argument - dieselbe Zahl wie in NOTIZ.md.

    ZWEI Ziele werden getrennt gemessen, weil sie nicht dasselbe sind:
      * `mitte`  = der volle Rueckweg zur Tagesmitte (Backtest-Default)
      * `anteil` = der HALBE Rueckweg (`ziel_anteil=0.5`) - DAS ist die Zahl
        aus NOTIZ.md (+0,276 % je Runde). Die wird hier aus dem Einstieg
        und der Mitte selbst gerechnet, weil `pruefe_fade()` sie nicht
        kennt; sonst wuerde ein Vergleich gegen die Notiz an zwei
        verschiedenen Regeln haengen.
    """
    dvol_reihe = daten.dvol_tagesreihe(waehrung, tage=TAGE)
    kerzen = daten.minutenkerzen(instrument, "60", tage=TAGE)
    dvol = b.dvol_je_tag(dvol_reihe)
    tage = b.tage_aus_kerzen(kerzen)

    tagnamen = sorted(tage)
    iv_je_tag = {}
    for i in range(1, len(tagnamen)):
        vorher = dvol.get(tagnamen[i - 1])
        if vorher is not None:
            iv_je_tag[tagnamen[i]] = vorher

    # Die Zeile der NOTIZ: IV aus DVOL, k=1,0, Stop 0,5 Sigma
    voll = b.pruefe_fade(tage, iv_je_tag, k.K_68, stop_sigma=0.5)
    halb = _fade_anteil(tage, iv_je_tag, k.K_68, 0.5, 0.5, b.GEBUEHR_JE_SEITE)
    return {"waehrung": waehrung, "instrument": instrument,
            "handelstage": len(tage), "iv_tage": len(iv_je_tag),
            "kennzahlen": halb["kennzahlen"],
            "voll": voll["kennzahlen"],
            "roh": halb}


def _fade_anteil(tage, iv_je_tag, kk, stop_sigma, anteil, gebuehr):
    """Derselbe Fade, aber mit einem ANTEIL des Rueckwegs als Ziel.

    Bewusst als eigene Funktion und nicht als Parameter an `pruefe_fade()`:
    die beiden Aufrufer (das Backtest-Werkzeug und die Spur) sollen sich nicht
    stillschweigend unterscheiden - genau ein solcher Unterschied hat die
    NOTIZ-Zahl und den Backtest-Default auseinanderlaufen lassen.
    """
    rundungen = []
    for tag in sorted(tage):
        iv = iv_je_tag.get(tag)
        kerzen = tage[tag]
        if iv is None or len(kerzen) < 4:
            continue
        offen = kerzen[0]["open"]
        sigma = k.tages_sigma(offen, iv)
        mitte = offen
        for seite, grenze in (("short", offen + kk * sigma),
                              ("long", offen - kk * sigma)):
            ziel_kurs = grenze + anteil * (mitte - grenze)
            for i, balken in enumerate(kerzen):
                beruehrt = (balken["high"] >= grenze) if seite == "short" \
                    else (balken["low"] <= grenze)
                if not beruehrt:
                    continue
                einstieg = grenze
                stop = (einstieg + stop_sigma * sigma if seite == "short"
                        else einstieg - stop_sigma * sigma)
                ergebnis = None
                for j in range(i, len(kerzen)):
                    bk = kerzen[j]
                    if seite == "short":
                        if bk["high"] >= stop:
                            ergebnis = stop
                            break
                        if bk["low"] <= ziel_kurs:
                            ergebnis = ziel_kurs
                            break
                    else:
                        if bk["low"] <= stop:
                            ergebnis = stop
                            break
                        if bk["high"] >= ziel_kurs:
                            ergebnis = ziel_kurs
                            break
                if ergebnis is None:
                    ergebnis = kerzen[-1]["close"]
                brutto = ((einstieg - ergebnis) / einstieg if seite == "short"
                          else (ergebnis - einstieg) / einstieg)
                rundungen.append({
                    "tag": tag, "seite": seite,
                    "brutto_prozent": brutto * 100.0,
                    "netto_prozent": (brutto - 2 * gebuehr) * 100.0,
                })
                break
    return {"rundungen": rundungen, "kennzahlen": b.kennzahlen(rundungen)}


def kopfzeile(z):
    kz = z["kennzahlen"] or {}
    if not kz.get("n"):
        return "%-4s n=0  (kein Signal)" % z["waehrung"]
    v = z.get("voll") or {}
    return ("%-4s HALBER Rueckweg (NOTIZ-Regel) n=%-4d Treffer %5.1f %%  "
            "%+.3f %% je Runde  Summe %+.1f %%  |  voller Rueckweg n=%-4d "
            "%+.3f %% je Runde  |  %s"
            % (z["waehrung"], kz["n"], kz["trefferquote"],
               kz["mittel_netto_prozent"], kz["summe_netto_prozent"],
               v.get("n", 0), v.get("mittel_netto_prozent", 0.0),
               _haelften(z)))


def _haelften(z):
    r = z.get("roh") or {}
    rnd = r.get("rundungen") or []
    if len(rnd) < 20:
        return "zu wenige Runden fuer die Haelfte"
    mitte = len(rnd) // 2
    a = [x["netto_prozent"] for x in rnd[:mitte]]
    c = [x["netto_prozent"] for x in rnd[mitte:]]
    return ("erste %d %+.3f %% / zweite %d %+.3f %%"
            % (len(a), statistics.mean(a), len(c), statistics.mean(c)))


def main():
    print("T-122 (b): Spannenweg auf einem ZWEITEN Instrument (Deribit, %d Tage,"
          " Gebuehr %.3f %% je Seite, IV aus dem Vortages-DVOL)"
          % (TAGE, GEBUEHR * 100))
    print()
    z = []
    for waehrung, instrument in (("BTC", "BTC-PERPETUAL"),
                                 ("ETH", "ETH-PERPETUAL")):
        try:
            z.append(messe(waehrung, instrument))
        except Exception as fehler:                     # noqa: BLE001
            print("%-4s FEHLER: %s" % (waehrung, fehler))
    print()
    for e in z:
        print(kopfzeile(e))
        print("     Handelstage %d, IV-Tage %d"
              % (e["handelstage"], e["iv_tage"]))
    if len(z) == 2 and all((e["kennzahlen"] or {}).get("n") for e in z):
        a, c = z
        print()
        print("VERGLEICH: beide Instrumente positiv? "
              "%s" % ("ja" if all(e["kennzahlen"]["mittel_netto_prozent"] > 0
                                 for e in z) else "NEIN"))
        print("  Groessenvergleich: BTC %+.3f %% vs ETH %+.3f %% je Runde"
              % (a["kennzahlen"]["mittel_netto_prozent"],
                 c["kennzahlen"]["mittel_netto_prozent"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
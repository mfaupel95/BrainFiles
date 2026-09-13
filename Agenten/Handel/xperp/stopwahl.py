"""Welcher Stop und welches Ziel - gemessen statt geschaetzt.

Rechnet ein Raster aus Stop- und Ziel-Abstaenden (in ATR) auf der tiefsten
verfuegbaren Kursreihe durch und gibt fuer jede Kombination den Erwartungswert
je Runde aus. Das beantwortet die Frage "welcher Stop ist klug" mit einer Zahl
statt mit einer Faustregel.

Der Erwartungswert ist die einzige Groesse, die zaehlt:

    E = p * Gewinn - (1-p) * Verlust - Kosten

Eine hohe Trefferquote allein sagt nichts - das ist der Kern von
Wissen/Handelsbots.md: Dort lagen noetige und erreichte Quote ueber 12 Monate
immer ein bis zwei Prozentpunkte auseinander, und uebrig blieben die Gebuehren.
Ein enges Ziel mit weitem Stop erkauft eine schoene Quote mit einem Verlust,
der alle Treffer frisst.

Zwei Sicherungen gegen Selbstbetrug sind eingebaut:

  - **Mindestbesetzung beider Seiten.** Eine Kombination mit 237 Zielen und
    einem Stop wird nicht bewertet, sondern verworfen. Das Verlustereignis ist
    dort nicht gemessen, sondern nicht vorgekommen.
  - **Zweite Haelfte gegen erste Haelfte.** Wer nur den Gesamtzeitraum
    optimiert, findet die Einstellung, die zu genau diesem Fenster passt.
    Deshalb steht neben dem Gesamtwert immer der Wert der juengeren Haelfte.

Aufruf:
    python stopwahl.py --wert SOL --richtung long
    python stopwahl.py --wert SOL --historie selbst    # nur der XPERP
"""

import argparse
import sys

import bot
import historie
import indikatoren
import okxf

STOPS = (1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0)
ZIELE = (1.5, 2.0, 2.5, 3.0, 4.0, 5.0)
MIN_SEITE = 10          # so viele Ereignisse braucht die seltenere Seite
HALTEDAUER = 60         # Kerzen, bis ein Anlauf als offen gilt (4H -> 10 Tage)


def bewerte(k, stop_atr, ziel_atr, seite, kosten, haltedauer=HALTEDAUER):
    tq = bot.trefferquote(k, stop_atr, ziel_atr, seite, max_kerzen=haltedauer)
    if tq["quote"] is None:
        return None
    a = indikatoren.atr(k, 14)
    kurs = k[-1][4]
    atr_pct = a[-1] / kurs if a[-1] else 0.0
    gewinn = ziel_atr * atr_pct
    verlust = stop_atr * atr_pct
    p = tq["quote"]
    erwartung = p * gewinn - (1 - p) * verlust - kosten
    noetig = bot.noetige_quote(gewinn, verlust, kosten)
    return {
        "stop": stop_atr, "ziel": ziel_atr, "quote": p, "noetig": noetig,
        "kante": (p - noetig) * 100 if noetig is not None else None,
        "erwartung": erwartung, "gewinn": gewinn, "verlust": verlust,
        "n_ziel": tq["ziel"], "n_stop": tq["stop"], "offen": tq["offen"],
        "besetzt": min(tq["ziel"], tq["stop"]),
    }


def main():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--wert", required=True)
    p.add_argument("--richtung", choices=("long", "short"), default="long")
    p.add_argument("--historie", default="auto",
                   help="'auto' (=<Basis>-USDT-SWAP), 'selbst' oder ein instId")
    p.add_argument("--hebel", type=float, default=5.0)
    a = p.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    w = bot.wachen()
    instr = okxf.instrument(a.wert)
    quelle = None if a.historie == "selbst" else a.historie
    k, name, tief = historie.tiefe_reihe(instr["instId"], quelle)
    k_selbst = okxf.kerzen(instr["instId"], "4H", 300)

    f = okxf.funding(instr["instId"]) or 0.0
    # Haltedauer im Schnitt rund 2 Tage -> 6 Funding-Perioden
    funding = f * 6 * (1 if a.richtung == "long" else -1)
    kosten = 2 * w["gebuehr_taker"] + funding

    ind = indikatoren.lage(k_selbst, inst=instr["instId"])
    # hebel_deckel() zieht seine Tageskerzen selbst und will den instId, nicht
    # die Reihe: hier gehoert der Name der TIEFEN Reihe hin (name, ersatzweise
    # der Kontrakt), sonst wandert eine Kerzenliste in die URL (HTTP 414).
    # Seit der Umstellung auf Tageskerzen (fc5d2d0) stand hier k und der
    # Aufruf brach ab.
    dl, ds = bot.hebel_deckel(name or instr["instId"], wartung=w["wartungsmarge"])
    deckel = dl if a.richtung == "long" else ds

    print()
    print("=" * 78)
    print("STOPWAHL  %s  %s  %.0fx" % (a.wert.upper(), a.richtung.upper(), a.hebel))
    print("=" * 78)
    print("  Kontrakt      %s" % instr["instId"])
    print("  Reihe         %s, %d Kerzen = %.0f Tage%s" % (
        name, len(k), len(k) / 6, "  (tiefer als der Kontrakt)" if tief else ""))
    print("  ATR(14) jetzt %.2f%% vom Kurs (%.4f bei %.4f)" % (
        ind["atr_pct"] * 100, ind["atr"], ind["kurs"]))
    print("  Kosten/Runde  %.3f%%  (%.3f%% Gebuehr %+.3f%% Funding)" % (
        kosten * 100, 2 * w["gebuehr_taker"] * 100, funding * 100))
    print("  Hebel-Deckel  %.1fx aus der tiefen Reihe -> %s" % (
        deckel, "5x passt" if deckel >= a.hebel else "5x ZU HOCH"))
    print()
    print("  Haltedauer je Anlauf hoechstens %d Kerzen = %.0f Tage." % (
        HALTEDAUER, HALTEDAUER / 6))
    print("  Die seltenere Seite braucht %d Ereignisse, sonst wird verworfen." % MIN_SEITE)
    print()

    halb = len(k) // 2
    zeilen = []
    for s in STOPS:
        for z in ZIELE:
            r = bewerte(k, s, z, a.richtung, kosten)
            if r is None:
                continue
            r2 = bewerte(k[halb:], s, z, a.richtung, kosten)
            r["jung"] = r2["erwartung"] if r2 else None
            zeilen.append(r)

    gut = [r for r in zeilen if r["besetzt"] >= MIN_SEITE]
    verworfen = len(zeilen) - len(gut)

    print("  %-5s %-5s %7s %7s %7s %9s %9s  %s" % (
        "Stop", "Ziel", "Quote", "noetig", "Kante", "E/Runde", "E juengere", "Ziel/Stop"))
    print("  " + "-" * 74)
    for r in sorted(gut, key=lambda x: -x["erwartung"])[:14]:
        print("  %4.2f  %4.2f  %6.1f%% %6.1f%% %+6.1fpp %+8.3f%% %+8s%%  %d/%d" % (
            r["stop"], r["ziel"], r["quote"] * 100, r["noetig"] * 100,
            r["kante"], r["erwartung"] * 100,
            "%.3f" % (r["jung"] * 100) if r["jung"] is not None else "n/a",
            r["n_ziel"], r["n_stop"]))

    print()
    print("  %d Kombinationen verworfen (seltenere Seite unter %d Ereignissen)." % (
        verworfen, MIN_SEITE))

    if not gut:
        print("  Keine Kombination ist belastbar besetzt.")
        return 1

    best = max(gut, key=lambda x: x["erwartung"])
    # Stabil ist, was in beiden Haelften positiv ist.
    stabil = [r for r in gut
              if r["erwartung"] > 0 and r["jung"] is not None and r["jung"] > 0]
    empfehlung = max(stabil, key=lambda x: min(x["erwartung"], x["jung"])) \
        if stabil else best

    print()
    print("-" * 78)
    print("  Bester Erwartungswert insgesamt: Stop %.2f ATR / Ziel %.2f ATR = %+.3f%%" % (
        best["stop"], best["ziel"], best["erwartung"] * 100))
    if stabil:
        print("  In BEIDEN Haelften positiv: %d von %d Kombinationen." % (
            len(stabil), len(gut)))
        print("  Empfehlung (beste schlechtere Haelfte): Stop %.2f ATR / Ziel %.2f ATR" % (
            empfehlung["stop"], empfehlung["ziel"]))
        print("    gesamt %+.3f%% je Runde, juengere Haelfte %+.3f%%" % (
            empfehlung["erwartung"] * 100, empfehlung["jung"] * 100))
    else:
        print("  KEINE Kombination ist in beiden Haelften positiv. Das ist die")
        print("  Nulllinie aus Wissen/Handelsbots.md - der beste Wert oben ist")
        print("  dann eine Eigenschaft des Fensters, keine Strategie.")

    print()
    print("  Stop %.2f ATR sind bei %.2f%% ATR ein Abstand von %.2f%%," % (
        empfehlung["stop"], ind["atr_pct"] * 100,
        empfehlung["stop"] * ind["atr_pct"] * 100))
    print("  Ziel %.2f ATR entsprechend %.2f%%. Bei %.0fx Hebel liegt die" % (
        empfehlung["ziel"], empfehlung["ziel"] * ind["atr_pct"] * 100, a.hebel))
    liq = 1 / a.hebel - w["wartungsmarge"]
    print("  Liquidation %.1f%% entfernt - der Stop liegt %.1f%% davor." % (
        liq * 100, (liq - empfehlung["stop"] * ind["atr_pct"]) * 100))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Welcher XPERP-Kontrakt taugt wofuer - Long, Short oder Grid.

Sucht nicht den "besten" Wert, sondern beantwortet drei getrennte Fragen, weil
sie verschiedene Eigenschaften brauchen:

  Long   - Aufwaertstrend, der schon laeuft, bei tragbarer Schwankung.
  Short  - Abwaertstrend, und die Funding-Rate zahlt an den Short statt an ihn.
  Grid   - viel Weg, wenig Richtung. Das ist die Kennzahl, die zaehlt, nicht
           "sieht seitwaerts aus".

Die Grundlinie steht in Wissen/Handelsbots.md: ueber lange Zeitraeume lag jede
getestete mechanische Krypto-Strategie nahe null, leicht darunter. Dieser Scan
sucht deshalb Lagen mit gutem Verhaeltnis, nicht den grossen Wurf.

Aufruf:
    python auswahl.py                # alle drei Ranglisten
    python auswahl.py --zweck grid    # nur eine
    python auswahl.py --wert RE       # ein Wert im Detail
"""

import argparse
import math
import statistics as st
import sys
import time

import okxf

# --- Modellannahmen ---------------------------------------------------------
# Sie gehoeren angepasst, wenn sich Gebuehren oder Wartungsmarge aendern.

WARTUNGSMARGE = 0.005      # Anteil des Positionswerts, der stehen bleiben muss
GEBUEHR_TAKER = 0.0005     # je Ausfuehrung
GEBUEHR_MAKER = 0.0002
BAR = "4H"                 # 300 Kerzen = rund 50 Tage
PRO_TAG = 6                # 4H-Kerzen je Tag

# 21 Tage Mindesthistorie, 42 Tage bis die Warnung faellt. Der Grund steht in
# Wissen/Handelsbots.md: "Einen Bot nie ueber weniger als ein Jahr bewerten."
# Ein Jahr gibt es bei XPERP nicht - die aeltesten Kontrakte laufen seit Mai
# 2026. Also wenigstens genug Kerzen, dass die 14-Tage-Kennzahl ueberhaupt
# existiert. Am 01.09.2026 standen DASH und POL mit 8,3 Tagen Historie weit
# oben in der Grid-Liste, weil ihre fehlende 14-Tage-Rendite als "+0.0%"
# gedruckt wurde und wie perfekte Seitwaertsbewegung aussah.
MIN_KERZEN = 21 * PRO_TAG
JUNG_KERZEN = 42 * PRO_TAG

# Tor aus scanner/wachen.json - dort 1.20 fuer Spot ohne Hebel. Fuer gehebelte
# Kontrakte ist es keine Frage der Vorliebe: Die Vola bestimmt direkt, wieviel
# Hebel ueberhaupt ueberlebt (siehe hebel_deckel).
VOLA_TOR = 1.20


def kennzahlen(k):
    """Alle Kennzahlen eines Werts aus seinen Kerzen."""
    c = [r[4] for r in k]
    n = len(c)
    kurs = c[-1]

    ren = [c[i] / c[i - 1] - 1 for i in range(1, n)]
    vola = st.stdev(ren) * math.sqrt(PRO_TAG * 365) if len(ren) > 2 else 0.0

    # ATR(14) in Prozent - der Massstab fuer jeden Stop-Abstand
    tr = [max(k[i][2] - k[i][3],
              abs(k[i][2] - k[i - 1][4]),
              abs(k[i][3] - k[i - 1][4])) for i in range(1, n)]
    atr = st.mean(tr[-14:]) / kurs if len(tr) >= 14 else 0.0

    def rendite(tage):
        b = tage * PRO_TAG
        return (c[-1] / c[-1 - b] - 1) if n > b else None

    # Kaufman Efficiency Ratio ueber 7 Tage: Nettobewegung geteilt durch
    # zurueckgelegten Weg. Nahe 1 = sauberer Trend, nahe 0 = Gezappel.
    f = c[-min(42, n - 1):]
    weg = sum(abs(f[i] - f[i - 1]) for i in range(1, len(f)))
    netto = abs(f[-1] - f[0])
    er = netto / weg if weg > 0 else 0.0
    weg_pct = weg / kurs                     # Weg in Prozent des Kurses

    # SMA-Ausrichtung
    def sma(tage):
        b = tage * PRO_TAG
        return st.mean(c[-b:]) if n >= b else None
    ueber = sum(1 for t in (3, 7, 14, 30)
                if sma(t) is not None and kurs > sma(t))
    von = sum(1 for t in (3, 7, 14, 30) if sma(t) is not None)

    # Groesster Ruecklauf gegen eine Long- bzw. Short-Position ueber 7 Tage.
    # Daraus faellt der Hebel, der ueberhaupt ueberlebt haette.
    hd = min(42, n - 1)
    mae_long = mae_short = 0.0
    for i in range(n - hd):
        e = c[i]
        tief = min(r[3] for r in k[i + 1:i + 1 + hd])
        hoch = max(r[2] for r in k[i + 1:i + 1 + hd])
        mae_long = max(mae_long, 1 - tief / e)
        mae_short = max(mae_short, hoch / e - 1)

    spanne = (max(r[2] for r in k[-hd:]) / min(r[3] for r in k[-hd:]) - 1)

    return {
        "kurs": kurs, "kerzen": n, "vola": vola, "atr": atr,
        "r7": rendite(7), "r14": rendite(14), "r30": rendite(30),
        "er": er, "weg": weg_pct, "ueber_sma": ueber, "von_sma": von,
        "mae_long": mae_long, "mae_short": mae_short, "spanne": spanne,
    }


def mae_tage(kt, tage=7):
    """Groesster Ruecklauf gegen Long bzw. Short ueber N Tage, aus Tageskerzen.

    Getrennt von kennzahlen(), weil diese Groesse eine andere Reihe braucht:
    Sie darf nicht davon abhaengen, wie weit das 4H-Fenster zurueckreicht.
    """
    mae_l = mae_s = 0.0
    for i in range(len(kt) - tage):
        e = kt[i][4]
        if e <= 0:
            continue
        mae_l = max(mae_l, 1 - min(r[3] for r in kt[i + 1:i + 1 + tage]) / e)
        mae_s = max(mae_s, max(r[2] for r in kt[i + 1:i + 1 + tage]) / e - 1)
    return mae_l, mae_s


def hebel_deckel(mae):
    """Groesster Hebel, der den beobachteten Ruecklauf ueberlebt haette.

    Liquidation greift rund bei 1/hebel minus Wartungsmarge. Wer mehr Hebel
    nimmt, als hier steht, waere im Beobachtungsfenster mindestens einmal
    ausgestoppt worden - nicht als Prognose, sondern als Rueckblick.
    """
    if mae <= 0:
        return 20.0
    return max(1.0, min(20.0, 1.0 / (mae + WARTUNGSMARGE)))


def bewerte(z, umsatz):
    """Drei Eignungen, je 0..100. Getrennt, weil sie sich widersprechen."""
    # Bezugsgroesse 3 Mio USD am Tag: gemessen am 01.09.2026 erreicht das im
    # XPERP-Universum ausser BTC/ETH kaum ein Wert. Das Universum ist duenn -
    # das ist ein Befund, kein Massstabsfehler.
    liquide = min(1.0, umsatz / 3_000_000) if umsatz else 0.0
    ruhig = max(0.0, 1.0 - z["vola"] / 2.0)

    # Long: Trend nach oben, SMA-Ausrichtung, nicht zu wild
    auf = sum(x for x in (z["r7"], z["r14"]) if x is not None)
    lo = (max(0.0, min(1.0, auf * 3)) * 0.40
          + (z["ueber_sma"] / z["von_sma"] if z["von_sma"] else 0) * 0.25
          + ruhig * 0.20 + liquide * 0.15)

    # Short: Trend nach unten. Positives Funding ist ein Zuschuss, kein Grund.
    ab = -auf
    sh = (max(0.0, min(1.0, ab * 3)) * 0.40
          + (1 - (z["ueber_sma"] / z["von_sma"] if z["von_sma"] else 0)) * 0.25
          + ruhig * 0.20 + liquide * 0.15)

    # Grid: viel Weg bei wenig Richtung. Der Weg muss die Gebuehren tragen,
    # deshalb zaehlt er absolut mit und nicht nur das Verhaeltnis.
    gr = (min(1.0, z["weg"] / 0.60) * 0.35
          + (1 - z["er"]) * 0.35
          + liquide * 0.20 + ruhig * 0.10)

    return {"long": lo * 100, "short": sh * 100, "grid": gr * 100}


def sammle(werte=None, still=False):
    instr = {x["instId"].split("-")[0]: x
             for x in okxf.instrumente(okxf.KRYPTO)}
    if werte:
        instr = {k: v for k, v in instr.items() if k in werte}
    tick = okxf.tickers()

    ergebnis = []
    for i, (basis, x) in enumerate(sorted(instr.items()), 1):
        iid = x["instId"]
        if not still:
            print("  %3d/%d %-10s" % (i, len(instr), basis), end="\r",
                  file=sys.stderr)
        try:
            k = okxf.kerzen(iid, BAR, 300)
        except Exception:                       # noqa: BLE001
            continue
        if len(k) < MIN_KERZEN:
            continue
        z = kennzahlen(k)

        # Der Hebel-Deckel kommt aus TAGESKERZEN, nicht aus den 4H-Kerzen
        # oben. 300 4H-Kerzen sind nur 50 Tage; 300 Tageskerzen sind 300.
        # Gemessen am 01.09.2026 an SOL: ueber 50 Tage sieht der groesste
        # 7-Tage-Ruecklauf nach 9,5 % aus (Deckel 10x), ueber 200 Tage sind
        # es 27,9 % (Deckel 3,5x) - der Einbruch vom 31.05.2026 lag ausserhalb
        # des kurzen Fensters. Schutzregeln, Spur 2 machen diesen Wert zur
        # festen Grenze; er darf nicht vom Fensterrand abhaengen.
        try:
            kt = okxf.kerzen(iid, "1D", 300)
            if len(kt) >= 14:
                z["mae_long"], z["mae_short"] = mae_tage(kt, 7)
                z["tage_gemessen"] = len(kt)
            time.sleep(0.06)
        except Exception:                       # noqa: BLE001
            z["tage_gemessen"] = len(k) / PRO_TAG

        t = tick.get(iid, {})
        # volCcy24h ist bereits Basiswaehrung (Kontrakte x ctVal). Wer hier
        # nochmal mit ctVal multipliziert, meldet BONK mit 167 Billionen
        # Umsatz - passiert am 01.09.2026 im ersten Wurf.
        umsatz = float(t.get("volCcy24h") or 0) * z["kurs"]
        z.update(basis=basis, instId=iid, umsatz=umsatz,
                 max_lever=float(x["lever"]),
                 punkte=bewerte(z, umsatz))
        ergebnis.append(z)
        time.sleep(0.06)                        # OKX: 40 Anfragen je 2 s
    if not still:
        print(" " * 30, end="\r", file=sys.stderr)
    return ergebnis


def tabelle(daten, zweck, n=12):
    ueber = {"long": "LONG - Aufwaertstrend",
             "short": "SHORT - Abwaertstrend",
             "grid": "GRID - viel Weg, wenig Richtung"}[zweck]
    print()
    print("=" * 100)
    print(ueber)
    print("=" * 100)
    print("%-9s %8s %7s %7s %6s %5s %5s %5s %6s %7s  %s" % (
        "Wert", "Kurs", "7T", "14T", "Vola", "ATR%", "Weg%", "ER", "Hebel",
        "Umsatz", "Punkte"))

    mae = "mae_short" if zweck == "short" else "mae_long"
    for z in sorted(daten, key=lambda d: -d["punkte"][zweck])[:n]:
        deckel = hebel_deckel(z[mae])
        warn = ""
        if z["vola"] > VOLA_TOR:
            warn += " !vola"
        if deckel < 5:
            warn += " !hebel<5"
        if z["kerzen"] < JUNG_KERZEN:
            warn += " !jung(%dT)" % (z["kerzen"] // PRO_TAG)
        # Fehlende Kennzahlen als n/a, nicht als 0 - eine fehlende
        # 14-Tage-Rendite sieht als "+0.0%" wie Seitwaertsbewegung aus.
        def pz(v):
            return "%+6.1f%%" % (v * 100) if v is not None else "   n/a"
        print("%-9s %8.4f %s %s %5.0f%% %5.2f %5.0f %5.2f %5.1fx %6.1fM  %5.1f%s" % (
            z["basis"], z["kurs"], pz(z["r7"]), pz(z["r14"]),
            z["vola"] * 100, z["atr"] * 100, z["weg"] * 100, z["er"],
            deckel, z["umsatz"] / 1e6, z["punkte"][zweck], warn))


def detail(z):
    print()
    print("=" * 70)
    print("%s   (%s)" % (z["basis"], z["instId"]))
    print("=" * 70)
    print("  Kurs            %.6f      Kerzen %d x %s" % (z["kurs"], z["kerzen"], BAR))
    print("  Rendite          7T %+.1f%%   14T %+.1f%%   30T %s" % (
        (z["r7"] or 0) * 100, (z["r14"] or 0) * 100,
        "%+.1f%%" % (z["r30"] * 100) if z["r30"] is not None else "n/a"))
    print("  ueber SMA        %d von %d (3/7/14/30 Tage)" % (z["ueber_sma"], z["von_sma"]))
    print("  Vola p.a.       %5.0f%%   %s" % (
        z["vola"] * 100, "UEBER dem Tor von %.0f%%" % (VOLA_TOR * 100)
        if z["vola"] > VOLA_TOR else "unter dem Tor"))
    print("  ATR(14)         %5.2f%% vom Kurs" % (z["atr"] * 100))
    print("  7T-Spanne       %5.1f%%" % (z["spanne"] * 100))
    print("  Weg / ER        %5.1f%% Weg bei ER %.2f  (%s)" % (
        z["weg"] * 100, z["er"],
        "eher Gezappel" if z["er"] < 0.3 else
        "gemischt" if z["er"] < 0.6 else "eher Trend"))
    print("  Umsatz 24h      %5.1f Mio USD" % (z["umsatz"] / 1e6))
    print()
    print("  Groesster Ruecklauf ueber 7 Tage und der Hebel, der ihn ueberlebt:")
    print("    gegen Long   %5.1f%%  ->  hoechstens %4.1fx" % (
        z["mae_long"] * 100, hebel_deckel(z["mae_long"])))
    print("    gegen Short  %5.1f%%  ->  hoechstens %4.1fx" % (
        z["mae_short"] * 100, hebel_deckel(z["mae_short"])))
    print()
    print("  Punkte: Long %.0f   Short %.0f   Grid %.0f" % (
        z["punkte"]["long"], z["punkte"]["short"], z["punkte"]["grid"]))

    # Was ein Grid hier kosten wuerde
    stufe = z["atr"]
    zyklus = 2 * GEBUEHR_MAKER
    print()
    print("  Grid-Probe: eine Stufe von 1 ATR = %.2f%%, ein Zyklus kostet %.2f%%" % (
        stufe * 100, zyklus * 100))
    if stufe > zyklus * 3:
        print("    -> Stufengewinn traegt die Gebuehr (%.1fx)" % (stufe / zyklus))
    else:
        print("    -> ZU ENG: Gebuehr frisst den Stufengewinn")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--zweck", choices=("long", "short", "grid", "alle"),
                   default="alle")
    p.add_argument("--wert", help="ein Basiswert im Detail, z.B. RE")
    p.add_argument("--anzahl", type=int, default=12)
    a = p.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if a.wert:
        d = sammle([a.wert.upper()])
        if not d:
            print("kein XPERP-Kontrakt zu %r (oder zu wenig Historie)" % a.wert)
            return 1
        detail(d[0])
        return 0

    print("Scanne alle Krypto-XPERP ueber %s-Kerzen ..." % BAR, file=sys.stderr)
    d = sammle()
    print("%d Werte bewertet, %s" % (len(d), time.strftime("%Y-%m-%d %H:%M")))
    for zweck in (("long", "short", "grid") if a.zweck == "alle" else (a.zweck,)):
        tabelle(d, zweck, a.anzahl)
    print()
    print("!vola    = ueber dem Tor von %.0f%% aus scanner/wachen.json" % (VOLA_TOR * 100))
    print("!hebel<5 = 5x haette den groessten Ruecklauf der letzten 7 Tage nicht ueberlebt")
    print("!jung    = unter %d Tagen Historie; die Kennzahlen tragen noch nicht." % (
        JUNG_KERZEN // PRO_TAG))
    print("ER       = Nettobewegung / zurueckgelegter Weg. Niedrig = Gezappel = Grid-Futter.")
    print("Hebel    = Deckel aus dem groessten Ruecklauf der letzten 7 Tage,")
    print("           Rueckblick und keine Zusage fuer die naechsten 7.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

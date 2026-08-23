"""
Reinvestitionsrechner: Welche Mechanik erzeugt wie oft reinvestierbaren Ertrag,
und ab wann lohnt das Reinvestieren ueberhaupt?

Die Ausgangsfrage war, womit sich "in kurzer Zeit wiederkehrende Gewinne
reinvestieren" lassen. Dafuer sind drei Groessen entscheidend, und nur zwei
davon stehen in den APY-Angaben:

  1. Wie oft entsteht ueberhaupt etwas Realisiertes?
  2. Wie viel ist es je Ereignis?
  3. Was kostet es, diesen Betrag wieder anzulegen?

Punkt 3 entscheidet bei kleinen Betraegen alles. Eine Reinvestition auf
Ethereum kostet rund 28 USD an Gas - unterhalb eines Ertrags von einigen
hundert USD ist Reinvestieren dort schlicht ein Verlustgeschaeft.

Aufruf:
    python reinvest.py
    python reinvest.py --kapital 500,5000,50000 --kette solana
    python reinvest.py --kette ethereum
"""

import argparse
import sys

import dca

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Am 10.08.2026 ueber `onchainos defi search` abgefragt, Kette Solana.
# Die APY-Werte sind Momentaufnahmen und schwanken.
QUELLEN = [
    # (Name, APY, TVL in USD, Art, was die APY NICHT enthaelt)
    ("Kamino Main Pool", 0.0683, 94_265_773, "Lending",
     "Protokollrisiko; Zinssatz schwankt mit der Auslastung"),
    ("Jupiter", 0.0508, 430_632_025, "Single Earn",
     "Protokollrisiko"),
    ("Kamino", 0.0464, 19_853_490, "Single Earn",
     "Protokollrisiko"),
    ("Orca V3 (bester Pool)", 0.3592, 2_718_604, "DEX-Pool",
     "IMPERMANENT LOSS - nicht in der APY enthalten; kleinster TVL der Liste"),
    ("Orca V3 (grosser Pool)", 0.2759, 26_323_067, "DEX-Pool",
     "IMPERMANENT LOSS - nicht in der APY enthalten"),
    ("Raydium V3", 0.2300, 6_149_676, "DEX-Pool",
     "IMPERMANENT LOSS - nicht in der APY enthalten"),
]


def schwelle(rendite, kette, restlaufzeit_jahre=1.0):
    """Ab welchem Ertragsbetrag lohnt eine Reinvestition?

    Reinvestieren bringt `ertrag * rendite * restlaufzeit` zusaetzlich und
    kostet `anteil * ertrag + fix`. Lohnend ist es, sobald

        ertrag * (rendite * laufzeit - anteil) > fix

    Bei einer fixen Gebuehr nahe null (Solana) ist die Schwelle praktisch
    immer erfuellt; bei hoher Fixgebuehr (Ethereum) verschiebt sie sich in
    dreistellige Betraege."""
    anteil, fix = dca.KOSTEN.get(kette, dca.KOSTEN["keine"])
    nutzen_je_usd = rendite * restlaufzeit_jahre - anteil
    if nutzen_je_usd <= 0:
        return float("inf")
    if fix == 0:
        return 0.0
    return fix / nutzen_je_usd


def endwert(kapital, rendite, jahre, reinvest_pro_jahr, kette):
    """Endwert mit periodischer Reinvestition, Kosten je Reinvestition
    abgezogen. reinvest_pro_jahr = 0 bedeutet: Ertraege bleiben liegen."""
    if reinvest_pro_jahr <= 0:
        return kapital * (1 + rendite * jahre)
    anteil, fix = dca.KOSTEN.get(kette, dca.KOSTEN["keine"])
    stand = kapital
    schritte = int(round(jahre * reinvest_pro_jahr))
    r = rendite / reinvest_pro_jahr
    for _ in range(schritte):
        ertrag = stand * r
        kosten = ertrag * anteil + fix
        stand += max(0.0, ertrag - kosten)
    return stand


def main():
    p = argparse.ArgumentParser(description="Reinvestitionsrechner")
    p.add_argument("--kapital", default="500,5000,50000",
                   help="Stützwerte, kommagetrennt")
    p.add_argument("--kette", default="solana", choices=list(dca.KOSTEN))
    p.add_argument("--jahre", type=float, default=3.0)
    args = p.parse_args()

    kapitalien = [float(x) for x in args.kapital.split(",")]
    anteil, fix = dca.KOSTEN[args.kette]

    print(f"\nReinvestition auf {args.kette}  |  Kosten je Vorgang: "
          f"{fix:,.2f} USD fix + {anteil:.2%} vom Betrag")
    print(f"Ertragsquellen gemessen am 10.08.2026 über `onchainos defi search`\n")

    # --- 1. Ab welchem Ertrag lohnt Reinvestieren? ---------------------
    print("  Mindestertrag, ab dem eine Reinvestition sich rechnet")
    print(f"  {'Quelle':<26}{'APY':>8}{'Schwelle':>14}")
    print("  " + "-" * 48)
    for name, apy, _, _, _ in QUELLEN:
        s = schwelle(apy, args.kette)
        text = "jeder Betrag" if s < 0.01 else f"{s:,.2f} USD"
        print(f"  {name:<26}{apy:>7.1%}{text:>14}")

    # --- 2. Wie oft im Jahr faellt dieser Betrag an? --------------------
    print(f"\n  Wie oft im Jahr erreicht der Ertrag diese Schwelle?")
    print(f"  {'Kapital':>10}", end="")
    for name, _, _, _, _ in QUELLEN[:3]:
        print(f"{name[:14]:>16}", end="")
    print()
    print("  " + "-" * 58)
    for kap in kapitalien:
        print(f"  {kap:>10,.0f}", end="")
        for _, apy, _, _, _ in QUELLEN[:3]:
            s = schwelle(apy, args.kette)
            jahresertrag = kap * apy
            if s < 0.01:
                text = "beliebig oft"
            elif jahresertrag < s:
                text = "nie"
            else:
                text = f"{jahresertrag / s:,.0f}x"
            print(f"{text:>16}", end="")
        print()

    # --- 3. Was bringt Reinvestieren tatsaechlich? ----------------------
    beste = max(QUELLEN[:3], key=lambda q: q[1])
    print(f"\n  Endwert nach {args.jahre:g} Jahren bei {beste[0]} ({beste[1]:.2%})")
    print(f"  {'Kapital':>10}{'gar nicht':>14}{'jährlich':>12}"
          f"{'monatlich':>12}{'täglich':>12}{'bestes Plus':>14}")
    print("  " + "-" * 74)
    for kap in kapitalien:
        werte = {n: endwert(kap, beste[1], args.jahre, f, args.kette)
                 for n, f in (("gar nicht", 0), ("jährlich", 1),
                              ("monatlich", 12), ("täglich", 365))}
        bestes = max(werte.values())
        plus = bestes - werte["gar nicht"]
        print(f"  {kap:>10,.0f}", end="")
        for n in ("gar nicht", "jährlich", "monatlich", "täglich"):
            print(f"{werte[n]:>12,.0f}  ", end="")
        print(f"{plus:>+12,.0f}")

    # --- 4. Was in den APY-Zahlen fehlt --------------------------------
    print("\n  Was die APY-Angabe nicht enthält")
    for name, apy, tvl, art, warnung in QUELLEN:
        print(f"    {name} ({art}, TVL {tvl:,.0f}): {warnung}")

    print("\n  Grid-Zyklen als vierte Quelle sind NICHT vergleichbar aufgeführt:")
    print("  ihr Ertrag hängt an der Volatilität, nicht an einer Rate. Gemessen")
    print("  wurden 69 Zyklen/Jahr bei 20 Stufen (BTC 08/25–08/26) — in einem")
    print("  Zeitraum, in dem das Grid insgesamt 161 USD VERLOR. Häufige Zyklen")
    print("  bedeuten nicht Gewinn, sondern nur häufige Umsätze.\n")


if __name__ == "__main__":
    sys.exit(main())

"""
Dieselbe DCA-Mechanik ueber mehrere Titel - der Ehrlichkeitstest.

Ein Backtest auf einem einzelnen Titel misst vor allem diesen Titel. Erst der
Vergleich zeigt, wie viel am Ergebnis Methode war und wie viel Kursverlauf.

Die Titelauswahl ist bewusst KEINE Empfehlungsliste, sondern eine Sammlung von
Testfaellen. Entscheidend sind die Titel der Gruppe "gescheitert": Highflyer,
die eingebrochen und nicht zurueckgekommen sind. Wer nur AAPL, NVDA und TSLA
testet, testet ausschliesslich Ueberlebende und bekommt garantiert ein zu
gutes Ergebnis heraus (Survivorship Bias).

Aufruf:
    python vergleich.py                        # Hebel 1 und 3, 18 Monate Haltedauer
    python vergleich.py --hebel 3 --dauer 36
    python vergleich.py --ab-pltr              # nur gemeinsamer Zeitraum ab PLTR-IPO
"""

import argparse
import sys

import dca
import kursdaten

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Gruppe: warum der Titel im Test ist - nicht, was von ihm zu halten ist.
TITEL = [
    ("PLTR", "Ausgangsfall"),
    ("NVDA", "überlebt"),
    ("TSLA", "überlebt"),
    ("AAPL", "überlebt"),
    ("SPY",  "breiter Markt"),
    ("PTON", "gescheitert"),
    ("ZM",   "gescheitert"),
    ("INTC", "abgestiegen"),
]

PLTR_IPO = "2020-09-30"


def auswerten(ticker, betrag, intervall, hebel, dauer, modus, zins, ab=None):
    df, _ = kursdaten.laden(ticker, still=True)
    if ab:
        df = df.loc[ab:]
    if len(df) < 300:
        return None
    erg = dca.rollierend(df, betrag, intervall, hebel, dauer, modus, zins)
    if not erg:
        return None
    renditen = sorted(r for _, r, _, _ in erg)
    n = len(renditen)
    return {
        "ticker": ticker,
        "fenster": n,
        "median": renditen[n // 2],
        "schlecht": renditen[0],
        "gut": renditen[-1],
        "minus": sum(1 for r in renditen if r < 0) / n,
        "ruin": sum(1 for r in renditen if r <= -0.90) / n,
        "liq": sum(1 for _, _, l, _ in erg if l > 0) / n,
    }


def tabelle(zeilen, hebel, dauer, hinweis):
    print(f"\n  Hebel {hebel:g}  |  {dauer} Monate Haltedauer  |  {hinweis}")
    print(f"  {'Titel':<7}{'Rolle':<15}{'Fenster':>8}{'Median':>9}{'Schlecht.':>11}"
          f"{'im Minus':>10}{'unter -90%':>12}{'m. Liquid.':>12}")
    print("  " + "-" * 84)
    for z, rolle in zeilen:
        if z is None:
            continue
        print(f"  {z['ticker']:<7}{rolle:<15}{z['fenster']:>8}{z['median']:>+8.0%}"
              f"{z['schlecht']:>+11.0%}{z['minus']:>10.0%}{z['ruin']:>12.0%}"
              f"{z['liq']:>12.0%}" if hebel > 1 else
              f"  {z['ticker']:<7}{rolle:<15}{z['fenster']:>8}{z['median']:>+8.0%}"
              f"{z['schlecht']:>+11.0%}{z['minus']:>10.0%}{'-':>12}{'-':>12}")


def main():
    p = argparse.ArgumentParser(description="DCA über mehrere Titel vergleichen")
    p.add_argument("--betrag", type=float, default=200)
    p.add_argument("--intervall", default="monat", choices=["woche", "monat", "quartal"])
    p.add_argument("--hebel", type=float, default=None, help="einzelner Hebel statt 1 und 3")
    p.add_argument("--dauer", type=int, default=18, help="Haltedauer in Monaten")
    p.add_argument("--modus", default="isoliert", choices=["isoliert", "cross"])
    p.add_argument("--zins", type=float, default=dca.FINANZIERUNG_PA)
    p.add_argument("--ab-pltr", action="store_true",
                   help="nur der Zeitraum ab PLTR-IPO, damit alle dasselbe Fenster sehen")
    p.add_argument("--titel", default=None,
                   help="eigene Liste statt der Standard-Testfälle, z.B. NVDA,MSFT,BTC-USD,IREN")
    p.add_argument("--ab", default=None, help="gemeinsamer Start JJJJ-MM-TT")
    args = p.parse_args()

    global TITEL
    if args.titel:
        eigene = [t.strip().upper() for t in args.titel.split(",") if t.strip()]
        # SPY als Referenz anhaengen, falls nicht schon drin: ohne Vergleichsmassstab
        # sagt eine Rendite wenig.
        TITEL = [(t, "gewählt") for t in eigene]
        if "SPY" not in eigene:
            TITEL.append(("SPY", "Referenz"))

    ab = args.ab or (PLTR_IPO if args.ab_pltr else None)
    hinweis = (f"gemeinsamer Zeitraum ab {ab}" if ab
               else "volle verfügbare Historie je Titel")

    print(f"\nDCA-Vergleich  |  {dca.euro(args.betrag)} je {args.intervall.capitalize()}"
          f"  |  Modus {args.modus}")
    print("Die Titelauswahl ist eine Sammlung von Testfällen, keine Empfehlungsliste.")

    hebel_liste = [args.hebel] if args.hebel else [1, 3]
    for h in hebel_liste:
        zeilen = []
        for ticker, rolle in TITEL:
            try:
                z = auswerten(ticker, args.betrag, args.intervall, h,
                              args.dauer, args.modus, args.zins, ab)
            except Exception as e:
                print(f"  {ticker}: übersprungen ({type(e).__name__})")
                continue
            zeilen.append((z, rolle))
        tabelle(zeilen, h, args.dauer, hinweis)

    print("\n  \"unter -90%\" = Fenster, die praktisch totalverlust waren.")
    print("  Nicht enthalten: Spread, Gebühren, Steuern, Slippage, Wechselkurs.\n")


if __name__ == "__main__":
    sys.exit(main())

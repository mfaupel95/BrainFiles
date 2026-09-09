"""
DCA-Simulator - instrumentenneutral.

Rechnet einen Sparplan (feste Summe, festes Intervall) auf historischen Kursen
durch, wahlweise ohne Hebel oder gehebelt. Der interessante Teil ist der
gehebelte Fall: Dort entscheidet nicht der Einstiegspreis ueber das Ergebnis,
sondern der Abstand zur Liquidation.

Aufruf:
    python dca.py                          # Standard: PLTR, 200 EUR/Monat, ohne Hebel
    python dca.py --hebel 3                # dieselbe Reihe mit Hebel 3, isolierte Margin
    python dca.py --hebel 3 --modus cross  # gemeinsame Margin statt je Tranche
    python dca.py --vergleich              # Hebel 1/2/3/5 nebeneinander
    python dca.py --hebel 3 --details      # zusaetzlich jede Tranche einzeln

Das Skript handelt nicht und verbindet sich mit keinem Broker. Es rechnet.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                os.pardir, "Bus"))
import ereignis                                            # noqa: E402

import kursdaten

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Anteil des Positionswerts, der als Sicherheit stehenbleiben muss. Faellt das
# Eigenkapital darunter, wird zwangsgeschlossen. 0,5 % ist ein gaengiger Wert
# bei CFD-Brokern; bei Optionen und Futures gilt eine andere Mechanik.
WARTUNGSMARGE = 0.005
# Jahreszins auf das geliehene Kapital. Bei CFDs ueblicherweise Referenzzins
# plus Aufschlag - der genaue Wert gehoert vom Broker eingesetzt.
FINANZIERUNG_PA = 0.06


# Am 10.08.2026 mit `onchainos swap quote` gemessen (USDC -> WBTC), nicht
# geschaetzt. Die Zahlen gehoeren nachgemessen, wenn sich Route oder Gaspreis
# aendern - siehe README, Abschnitt "Swap-Kosten".
KOSTEN = {
    # Kette: (Anteil vom Betrag, feste Kosten je Swap in USD)
    "solana": (0.0006, 0.02),      # 0,05-0,06 % Impact, keine Router-Fee, Gas ~2 Cent
    "ethereum": (0.0090, 28.00),   # 0,89 % Fee bei 200 USD + ~1,5 Mio Gas
    "keine": (0.0, 0.0),
}


def swap_kosten(betrag, kette):
    anteil, fix = KOSTEN.get(kette, KOSTEN["keine"])
    return betrag * anteil + fix


def kauftage(df, start, ende, intervall):
    """Die Handelstage, an denen gekauft wird. Faellt der Stichtag auf ein
    Wochenende oder einen Feiertag, wird der naechste Handelstag genommen -
    genau wie ein echter Sparplan es tut."""
    zeitraum = df.loc[start:ende]
    if zeitraum.empty:
        return []
    if intervall == "woche":
        gruppen = zeitraum.groupby([zeitraum.index.isocalendar().year,
                                    zeitraum.index.isocalendar().week])
    elif intervall == "monat":
        gruppen = zeitraum.groupby([zeitraum.index.year, zeitraum.index.month])
    elif intervall == "quartal":
        gruppen = zeitraum.groupby([zeitraum.index.year, zeitraum.index.quarter])
    else:
        raise ValueError(f"unbekanntes Intervall: {intervall}")
    return [g.index[0] for _, g in gruppen]


class Tranche:
    def __init__(self, datum, einstieg, margin, hebel):
        self.datum = datum
        self.einstieg = einstieg
        self.margin = margin
        self.hebel = hebel
        self.position = margin * hebel
        self.stueck = self.position / einstieg
        self.geliehen = self.position - margin
        self.finanzierung = 0.0
        self.liquidiert_am = None

    def eigenkapital(self, kurs):
        return self.margin - self.finanzierung + self.stueck * (kurs - self.einstieg)

    def wert(self, kurs):
        """Was die Tranche gerade wert ist - null, wenn sie liquidiert wurde."""
        if self.liquidiert_am:
            return 0.0
        return max(0.0, self.eigenkapital(kurs))


def simuliere(df, betrag, intervall, hebel, start, ende, modus="isoliert",
              zins=FINANZIERUNG_PA, wartungsmarge=WARTUNGSMARGE, kette="keine"):
    tage = kauftage(df, start, ende, intervall)
    if not tage:
        raise ValueError("keine Kauftage im gewaehlten Zeitraum")

    offen = []
    erledigt = []
    naechste = {d: True for d in tage}
    eingezahlt = 0.0
    kosten_summe = 0.0
    verlorene_margin = 0.0
    liquidationen = 0
    eigenkapital_verlauf = []

    zeitraum = df.loc[tage[0]:ende]
    tageszins = zins / 365.0

    for datum, zeile in zeitraum.iterrows():
        # 1. Finanzierungskosten fuer den abgelaufenen Tag
        for t in offen:
            t.finanzierung += t.geliehen * tageszins

        # 2. Liquidation pruefen - am Tagestief, nicht am Schlusskurs.
        #    Ein Broker schliesst zwangsweise, sobald der Kurs die Schwelle
        #    beruehrt; ob er sich bis zum Abend erholt, ist dann egal.
        tief = zeile["Low"]
        if hebel > 1 and offen:
            if modus == "cross":
                ek = sum(t.eigenkapital(tief) for t in offen)
                pos_wert = sum(t.stueck for t in offen) * tief
                if ek <= wartungsmarge * pos_wert:
                    # Gemeinsame Margin: es trifft alle Positionen gleichzeitig.
                    for t in offen:
                        t.liquidiert_am = datum
                        verlorene_margin += t.margin
                        erledigt.append(t)
                    liquidationen += len(offen)
                    offen = []
            else:
                weiter = []
                for t in offen:
                    if t.eigenkapital(tief) <= wartungsmarge * t.stueck * tief:
                        t.liquidiert_am = datum
                        verlorene_margin += t.margin
                        liquidationen += 1
                        erledigt.append(t)
                    else:
                        weiter.append(t)
                offen = weiter

        # 3. Kaufen, falls heute ein Sparplantag ist. Die Swap-Kosten gehen vom
        #    Betrag ab: eingezahlt wird die volle Rate, investiert nur der Rest.
        if naechste.pop(datum, False):
            kosten = swap_kosten(betrag, kette)
            netto = max(0.0, betrag - kosten)
            if netto > 0:
                offen.append(Tranche(datum, zeile["Close"], netto, hebel))
            eingezahlt += betrag
            kosten_summe += kosten

        schluss = zeile["Close"]
        eigenkapital_verlauf.append((datum, sum(t.wert(schluss) for t in offen)))

    letzter_kurs = zeitraum["Close"].iloc[-1]
    wert = sum(t.wert(letzter_kurs) for t in offen)

    # Groesster Ruecksetzer des Depotwerts gegenueber dem bis dahin
    # Eingezahlten - das ist die Zahl, die man aushalten muss.
    spitze = 0.0
    max_dd = 0.0
    for _, w in eigenkapital_verlauf:
        spitze = max(spitze, w)
        if spitze > 0:
            max_dd = max(max_dd, (spitze - w) / spitze)

    return {
        "hebel": hebel,
        "modus": modus if hebel > 1 else "-",
        "tranchen": len(erledigt) + len(offen),
        "eingezahlt": eingezahlt,
        "wert": wert,
        "gewinn": wert - eingezahlt,
        "rendite": (wert / eingezahlt - 1) if eingezahlt else 0.0,
        "liquidationen": liquidationen,
        "verlorene_margin": verlorene_margin,
        "swap_kosten": kosten_summe,
        "finanzierung": sum(t.finanzierung for t in offen + erledigt),
        "max_drawdown": max_dd,
        "offene": offen,
        "erledigte": erledigt,
        "erster_kauf": tage[0],
        "letzter_kurs": letzter_kurs,
    }


def rollierend(df, betrag, intervall, hebel, dauer_monate, modus, zins, kette="keine"):
    """Startet denselben Plan zu jedem moeglichen Monatsanfang und sammelt die
    Ergebnisse ein.

    Der Grund: Ein einzelner Backtest sagt vor allem etwas ueber das gewaehlte
    Zeitfenster aus. Bei PLTR liegen zwischen dem besten und dem schlechtesten
    Startzeitpunkt derselben Strategie mehr als 1500 Prozentpunkte. Erst die
    Verteilung ueber alle Startzeitpunkte zeigt, wie viel davon Methode war und
    wie viel Zufall."""
    import pandas as pd

    monatsanfaenge = sorted({d.replace(day=1) for d in df.index})
    ergebnisse = []
    for start in monatsanfaenge:
        ende = start + pd.DateOffset(months=dauer_monate)
        if ende > df.index[-1]:
            break
        try:
            e = simuliere(df, betrag, intervall, hebel, start, ende, modus, zins,
                          kette=kette)
        except ValueError:
            continue
        if e["eingezahlt"] > 0:
            ergebnisse.append((start, e["rendite"], e["liquidationen"], e["tranchen"]))
    return ergebnisse


def zeige_rollierend(ergebnisse, dauer_monate, hebel):
    if not ergebnisse:
        print("  Zeitraum zu kurz für diese Haltedauer.")
        return
    renditen = sorted(r for _, r, _, _ in ergebnisse)
    n = len(renditen)
    median = renditen[n // 2]
    verlust = sum(1 for r in renditen if r < 0)
    total = sum(1 for r in renditen if r <= -0.95)
    liq_fenster = sum(1 for _, _, l, _ in ergebnisse if l > 0)

    print(f"  Startzeitpunkte  {n}  (je {dauer_monate} Monate Haltedauer)")
    print(f"  Median           {median:+.0%}")
    print(f"  Schlechtestes    {renditen[0]:+.0%}")
    print(f"  Bestes           {renditen[-1]:+.0%}")
    print(f"  Im Minus         {verlust} von {n}  ({verlust / n:.0%})")
    if hebel > 1:
        print(f"  Fast totalverlust {total} von {n}  ({total / n:.0%})")
        print(f"  mit Liquidation  {liq_fenster} von {n}  ({liq_fenster / n:.0%})")


def euro(x):
    return f"{x:,.0f}".replace(",", ".")


def zeige(e, details=False):
    print(f"  Tranchen        {e['tranchen']}  ab {e['erster_kauf'].date()}")
    print(f"  Eingezahlt      {euro(e['eingezahlt'])}")
    print(f"  Wert heute      {euro(e['wert'])}   ({e['rendite']:+.1%})")
    if e["hebel"] > 1:
        print(f"  Finanzierung    {euro(e['finanzierung'])}  (Kosten, bereits abgezogen)")
        if e["liquidationen"]:
            print(f"  Liquidiert      {e['liquidationen']} Tranchen, "
                  f"{euro(e['verlorene_margin'])} verloren")
        else:
            print("  Liquidiert      keine")
    print(f"  Max. Rücksetzer {e['max_drawdown']:.0%} vom Höchststand")

    if details:
        print("\n  Tranche      Einstieg   Status")
        for t in sorted(e["erledigte"] + e["offene"], key=lambda t: t.datum):
            if t.liquidiert_am:
                status = f"liquidiert {t.liquidiert_am.date()}  -{euro(t.margin)}"
            else:
                status = f"offen, Wert {euro(t.wert(e['letzter_kurs']))}"
            print(f"  {t.datum.date()}   {t.einstieg:8.2f}   {status}")


def main():
    with ereignis.lauf("handel/dca"):
        return _main()


def _main():
    p = argparse.ArgumentParser(description="DCA-Simulator (rechnet nur, handelt nicht)")
    p.add_argument("--ticker", default="PLTR")
    p.add_argument("--betrag", type=float, default=200, help="je Tranche (Standard 200)")
    p.add_argument("--intervall", default="monat", choices=["woche", "monat", "quartal"])
    p.add_argument("--hebel", type=float, default=1)
    p.add_argument("--modus", default="isoliert", choices=["isoliert", "cross"],
                   help="Margin je Tranche oder gemeinsam")
    p.add_argument("--start", default=None, help="JJJJ-MM-TT (Standard: erster Kurs)")
    p.add_argument("--ende", default=None)
    p.add_argument("--zins", type=float, default=FINANZIERUNG_PA,
                   help="Finanzierung p.a. auf geliehenes Kapital (Standard 0.06)")
    p.add_argument("--kette", default="keine", choices=list(KOSTEN),
                   help="Swap-Kosten der Kette einrechnen (gemessen 10.08.2026)")
    p.add_argument("--vergleich", action="store_true", help="Hebel 1/2/3/5 nebeneinander")
    p.add_argument("--rollierend", type=int, metavar="MONATE", default=None,
                   help="Plan zu jedem Startmonat durchrechnen, Verteilung zeigen")
    p.add_argument("--details", action="store_true", help="jede Tranche einzeln")
    p.add_argument("--neu", action="store_true", help="Kurse neu abrufen")
    args = p.parse_args()

    df, quelle = kursdaten.laden(args.ticker, erzwinge_aktualisierung=args.neu)
    start = args.start or df.index[0]
    ende = args.ende or df.index[-1]

    print(f"\n{args.ticker}  |  {euro(args.betrag)} je {args.intervall.capitalize()}  "
          f"|  Kurs {df['Close'].iloc[-1]:.2f}  |  {quelle}")

    if args.rollierend:
        for h in ([args.hebel] if args.hebel != 1 else (1, 2, 3)):
            erg = rollierend(df, args.betrag, args.intervall, h,
                             args.rollierend, args.modus, args.zins)
            print(f"\nHebel {h:g}")
            zeige_rollierend(erg, args.rollierend, h)
        print(f"\n  Modus {args.modus}, Finanzierung {args.zins:.1%} p.a.")
    elif args.vergleich:
        print(f"\n{'Hebel':>6} {'Eingezahlt':>11} {'Wert':>10} {'Rendite':>9} "
              f"{'Liquid.':>8} {'Rücksetzer':>11}")
        print("  " + "-" * 62)
        for h in (1, 2, 3, 5):
            e = simuliere(df, args.betrag, args.intervall, h, start, ende,
                          args.modus, args.zins, kette=args.kette)
            liq = f"{e['liquidationen']}/{e['tranchen']}" if h > 1 else "-"
            print(f"{h:>6} {euro(e['eingezahlt']):>11} {euro(e['wert']):>10} "
                  f"{e['rendite']:>+8.0%} {liq:>8} {e['max_drawdown']:>10.0%}")
        print(f"\n  Modus {args.modus}, Finanzierung {args.zins:.1%} p.a., "
              f"Wartungsmarge {WARTUNGSMARGE:.1%}")
    else:
        e = simuliere(df, args.betrag, args.intervall, args.hebel, start, ende,
                      args.modus, args.zins, kette=args.kette)
        kopf = f"Hebel {args.hebel:g}" + (f", Margin {args.modus}" if args.hebel > 1 else "")
        if args.kette != "keine":
            kopf += f", Swap-Kosten {args.kette}"
        print(f"\n{kopf}")
        zeige(e, args.details)
        if e["swap_kosten"]:
            anteil = e["swap_kosten"] / e["eingezahlt"]
            print(f"  Swap-Kosten     {euro(e['swap_kosten'])}  "
                  f"({anteil:.1%} des Eingezahlten)")

    print()


if __name__ == "__main__":
    sys.exit(main())

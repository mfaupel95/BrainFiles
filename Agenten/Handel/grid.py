"""
Grid-Simulator: kauft auf fallenden Gitterstufen, verkauft auf steigenden.

Ein Grid legt zwischen einer unteren und oberen Grenze N Preisstufen. Faellt der
Kurs auf eine Stufe, wird gekauft; steigt er auf die naechsthoehere, wird genau
diese Position wieder verkauft. Der Gewinn eines Zyklus ist der Stufenabstand
minus Kosten.

Warum der Simulator VOR der Konfiguration kommt:

  1. Ein Grid macht viele Trades. Jeder kostet. Bei engen Stufen kann die
     Gebuehr groesser sein als der Stufengewinn - dann verliert das Grid
     zuverlaessig, egal wie der Kurs laeuft.
  2. Grids gewinnen in Seitwaertsmaerkten und verlieren gegen Buy-and-Hold in
     Trends: nach oben, weil zu frueh verkauft wird; nach unten, weil immer
     weiter zugekauft wird.
  3. Verlaesst der Kurs die Spanne nach unten, sitzt das gesamte Kapital in
     Positionen fest und es passiert nichts mehr.

Deshalb steht in jeder Ausgabe der Vergleich zu Buy-and-Hold. Ein Grid, das
schlechter ist als schlicht halten, hat seinen Zweck verfehlt.

Aufruf:
    python grid.py --ticker BTC-USD --unten 50000 --oben 80000 --stufen 10
    python grid.py --ticker SOL-USD --spanne-auto --start 2024-01-01
    python grid.py --ticker BTC-USD --spanne-auto --raster       # Parametervergleich
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                os.pardir, "Bus"))
import ereignis                                            # noqa: E402

import dca
import kursdaten

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def stufen_bauen(unten, oben, anzahl, geometrisch=True):
    """Gitterpreise. Geometrisch heisst gleicher prozentualer Abstand - das ist
    bei Kryptokursen sinnvoller als gleicher absoluter Abstand, weil eine
    Bewegung von 100 auf 110 dieselbe Bedeutung hat wie 1000 auf 1100."""
    if anzahl < 2:
        raise ValueError("mindestens 2 Stufen")
    if geometrisch:
        faktor = (oben / unten) ** (1 / (anzahl - 1))
        return [unten * faktor ** i for i in range(anzahl)]
    schritt = (oben - unten) / (anzahl - 1)
    return [unten + schritt * i for i in range(anzahl)]


def stufen_bis_liquidation(hebel, stufenfaktor, wartungsmarge=None):
    """Wie viele Gitterstufen darf der Kurs unter einen Einstieg fallen, bevor
    diese Position liquidiert wird?

    Das ist die entscheidende Zahl eines gehebelten Grids. Ein Grid kauft nach
    unten immer weiter zu - der Hebel setzt dem eine harte Grenze, die der
    ungehebelte Fall nicht kennt."""
    import math

    if hebel <= 1:
        return float("inf")
    mm = dca.WARTUNGSMARGE if wartungsmarge is None else wartungsmarge
    rest = 1 - 1 / hebel + mm
    if rest <= 0:
        return 0.0
    return -math.log(rest) / math.log(stufenfaktor)


def kurs_stress(zeitraum, prozent, tage=60):
    """Haengt einen Rueckgang um `prozent` ueber `tage` an den Zeitraum an.
    Kein historisches Vorbild - der Zweck ist zu sehen, was passiert, wenn der
    Kurs die Gitterspanne nach unten verlaesst."""
    import pandas as pd

    if not prozent:
        return zeitraum
    letzter = zeitraum.index[-1]
    schluss = zeitraum["Close"].iloc[-1]
    ziel = schluss * (1 - prozent / 100)
    daten = []
    for t in range(1, tage + 1):
        kurs = schluss + (ziel - schluss) * t / tage
        daten.append({"Open": kurs, "High": kurs * 1.01,
                      "Low": kurs * 0.99, "Close": kurs})
    idx = pd.date_range(letzter + pd.Timedelta(days=1), periods=tage, freq="D")
    return pd.concat([zeitraum, pd.DataFrame(daten, index=idx)])


def simuliere(df, unten, oben, stufen, kapital, start, ende, kette="keine",
              geometrisch=True, hebel=1.0, modus="isoliert", stress=0):
    preise = stufen_bauen(unten, oben, stufen, geometrisch)
    # Auf jeder Stufe ausser der obersten kann gekauft werden; die oberste
    # dient nur als Verkaufsziel.
    kauf_stufen = preise[:-1]
    je_stufe = kapital / len(kauf_stufen)

    # position[i] = dca.Tranche auf Stufe i, oder None (Stufe frei). Die
    # Tranche traegt Einstand, Hebel, Stueckzahl und aufgelaufene Finanzierung
    # und weiss, wann sie liquidiert ist - dieselbe Mechanik wie beim DCA.
    position = [None] * len(kauf_stufen)

    zeitraum = df.loc[start:ende]
    if zeitraum.empty:
        raise ValueError("kein Kurs im Zeitraum")
    if stress:
        zeitraum = kurs_stress(zeitraum, stress)

    tageszins = dca.FINANZIERUNG_PA / 365.0
    kaeufe = verkaeufe = liquidationen = 0
    realisiert = 0.0
    kosten_summe = 0.0
    verlorene_margin = 0.0
    investiert = 0.0
    ausserhalb_unten = ausserhalb_oben = 0
    # Freies Kapital. Ohne dieses Konto koennte das Modell nach jeder
    # Liquidation unbegrenzt neue Margin nachschiessen - im ersten Testlauf
    # ergab das 283 Liquidationen auf 8 Stufen und einen Verlust vom
    # 40-fachen des Einsatzes. Real ist bei aufgebrauchtem Kapital Schluss.
    frei = kapital
    kapital_erschoepft_am = None

    for datum, zeile in zeitraum.iterrows():
        tief, hoch = zeile["Low"], zeile["High"]

        if hoch < unten:
            ausserhalb_unten += 1
        if tief > oben:
            ausserhalb_oben += 1

        # 1. Finanzierungskosten auf das geliehene Kapital
        if hebel > 1:
            for t in position:
                if t is not None:
                    t.finanzierung += t.geliehen * tageszins

            # 2. Liquidation am TAGESTIEF pruefen, nicht am Schlusskurs -
            #    dieselbe Regel wie in dca.simuliere. Am Schluss zu pruefen
            #    wuerde die Strategie systematisch schoenrechnen.
            offen = [(i, t) for i, t in enumerate(position) if t is not None]
            if offen and modus == "cross":
                ek = sum(t.eigenkapital(tief) for _, t in offen)
                pos_wert = sum(t.stueck for _, t in offen) * tief
                if ek <= dca.WARTUNGSMARGE * pos_wert:
                    for i, t in offen:
                        verlorene_margin += t.margin
                        liquidationen += 1
                        position[i] = None
            elif offen:
                for i, t in offen:
                    if t.eigenkapital(tief) <= dca.WARTUNGSMARGE * t.stueck * tief:
                        verlorene_margin += t.margin
                        liquidationen += 1
                        position[i] = None

        # 3. Kaufen: jede freie Stufe, die vom Tageskurs unterschritten wurde -
        #    soweit noch freies Kapital da ist.
        for i, p in enumerate(kauf_stufen):
            if position[i] is None and tief <= p:
                if frei < je_stufe:
                    if kapital_erschoepft_am is None and any(
                            position[j] is None and tief <= q
                            for j, q in enumerate(kauf_stufen)):
                        kapital_erschoepft_am = datum
                    break
                # Gebuehr faellt auf die POSITIONSGROESSE an, nicht auf die
                # Margin - gehebelt handeln kostet entsprechend mehr.
                kosten = dca.swap_kosten(je_stufe * hebel, kette)
                netto = je_stufe - kosten
                if netto <= 0:
                    continue
                position[i] = dca.Tranche(datum, p, netto, hebel)
                frei -= je_stufe
                investiert += je_stufe
                kosten_summe += kosten
                kaeufe += 1

        # 4. Verkaufen: eine belegte Stufe wird glattgestellt, sobald die
        #    naechsthoehere Stufe erreicht ist.
        for i, p in enumerate(kauf_stufen):
            t = position[i]
            if t is None:
                continue
            ziel = preise[i + 1]
            if hoch >= ziel:
                kosten = dca.swap_kosten(t.stueck * ziel, kette)
                erloes = t.eigenkapital(ziel) - kosten
                realisiert += erloes - t.margin
                # Margin plus Gewinn stehen wieder zur Verfuegung - genau das
                # macht ein Grid zur wiederkehrenden Ertragsquelle.
                frei += max(0.0, erloes)
                kosten_summe += kosten
                position[i] = None
                verkaeufe += 1

    schluss = zeitraum["Close"].iloc[-1]
    offene = [t for t in position if t is not None]
    offen_menge = sum(t.stueck for t in offene)
    offen_wert = sum(max(0.0, t.eigenkapital(schluss)) for t in offene)
    offen_einstand = sum(t.margin for t in offene)

    # Buy-and-Hold als Massstab: dasselbe Kapital am ersten Tag komplett
    # investiert, einmal Kosten.
    bh_start = zeitraum["Close"].iloc[0]
    bh_kosten = dca.swap_kosten(kapital, kette)
    bh_menge = (kapital - bh_kosten) / bh_start
    bh_wert = bh_menge * schluss

    stufenfaktor = preise[1] / preise[0]
    return {
        "stufen_preise": preise,
        "kaeufe": kaeufe,
        "verkaeufe": verkaeufe,
        "zyklen": verkaeufe,
        "realisiert": realisiert,
        "offen_menge": offen_menge,
        "offen_wert": offen_wert,
        "offen_einstand": offen_einstand,
        "investiert": investiert,
        "kosten": kosten_summe,
        "kapital": kapital,
        "hebel": hebel,
        "modus": modus if hebel > 1 else "-",
        "liquidationen": liquidationen,
        "verlorene_margin": verlorene_margin,
        "stufen_bis_liq": stufen_bis_liquidation(hebel, stufenfaktor),
        "stufenfaktor": stufenfaktor,
        "stress": stress,
        "frei": frei,
        "kapital_erschoepft_am": kapital_erschoepft_am,
        # Endvermoegen minus Einsatz. Das freie Kapital enthaelt bereits
        # zurueckgeflossene Margin und realisierte Gewinne; dazu kommt der Wert
        # der offenen Positionen. Liquidierte Margin fehlt in beidem - genau so
        # soll es sein, sie ist verloren.
        "ergebnis": (frei + offen_wert) - kapital,
        "bh_ergebnis": bh_wert - kapital,
        "kurs_start": bh_start,
        "kurs_ende": schluss,
        "tage": len(zeitraum),
        "tage_unter_spanne": ausserhalb_unten,
        "tage_ueber_spanne": ausserhalb_oben,
    }


def plausibel(e):
    """Meldet Konstellationen, in denen die Zahlen zwar stimmen, das Ergebnis
    aber nichts ueber die Strategie aussagt."""
    hinweise = []
    preise = e["stufen_preise"]
    abstand = preise[1] / preise[0] - 1
    if abstand > 0.25:
        hinweise.append(
            f"Stufenabstand {abstand:.0%} — viel zu grob für ein Grid. Spanne "
            f"enger fassen (--unten/--oben) oder Zeitraum eingrenzen (--start).")
    jahre = e["tage"] / 365
    if jahre > 1 and e["zyklen"] / jahre < 4:
        hinweise.append(
            f"Nur {e['zyklen']} Zyklen in {jahre:.1f} Jahren — ein Grid lebt von "
            f"häufigen Durchläufen. So ist es eher Zufall als Strategie.")
    faktor = e["kurs_ende"] / e["kurs_start"]
    if faktor > 3 or faktor < 0.33:
        richtung = "gestiegen" if faktor > 1 else "gefallen"
        hinweise.append(
            f"Der Kurs ist im Zeitraum um Faktor {faktor:.1f} {richtung}. In so "
            f"starken Trends verliert jedes Grid gegen Halten — das ist keine "
            f"Aussage über die Parameter.")
    if e.get("liquidationen"):
        hinweise.append(
            f"{e['liquidationen']} Stufen wurden LIQUIDIERT ({e['verlorene_margin']:,.0f} "
            f"USD Margin verloren). Die Konstruktion ist in diesem Zeitraum "
            f"gebrochen — ein Grid sichert nicht ab, es kauft nach unten zu, "
            f"während der Hebel die Liquidationsschwelle heranzieht.")
    if e.get("hebel", 1) > 1 and e.get("stufen_bis_liq", float("inf")) < len(e["stufen_preise"]):
        hinweise.append(
            f"Liquidation greift schon {e['stufen_bis_liq']:.1f} Gitterstufen unter "
            f"jedem Einstieg — das Gitter ist {len(e['stufen_preise'])} Stufen tief. "
            f"Die unteren Stufen können also nicht mehr erreicht werden, ohne dass "
            f"die oberen vorher sterben.")
    return hinweise


def zeige(e, kette):
    kap = e["kapital"]
    print(f"  Zeitraum        {e['tage']} Tage, Kurs {e['kurs_start']:,.2f} → {e['kurs_ende']:,.2f}")
    print(f"  Gitter          {e['stufen_preise'][0]:,.2f} bis {e['stufen_preise'][-1]:,.2f}, "
          f"{len(e['stufen_preise'])} Stufen")
    if e["hebel"] > 1:
        print(f"  Hebel           {e['hebel']:g}, Margin {e['modus']}, "
              f"Liquidation {e['stufen_bis_liq']:.1f} Stufen unter Einstieg")
    if e["stress"]:
        print(f"  Stresstest      zusätzlicher Rückgang um {e['stress']:g} % "
              f"über 60 Tage angehängt")
    print(f"  Trades          {e['kaeufe']} Käufe, {e['verkaeufe']} Verkäufe "
          f"({e['zyklen']} abgeschlossene Zyklen)")
    if e["liquidationen"]:
        print(f"  LIQUIDIERT      {e['liquidationen']} Stufen, "
              f"{e['verlorene_margin']:,.2f} USD Margin verloren")
    print(f"  Realisiert      {e['realisiert']:+,.2f} USD")
    if e["offen_menge"] > 0:
        unrealisiert = e["offen_wert"] - e["offen_einstand"]
        print(f"  Offen           {e['offen_einstand']:,.2f} USD investiert, "
              f"Wert {e['offen_wert']:,.2f}  ({unrealisiert:+,.2f})")
    print(f"  Kosten          {e['kosten']:,.2f} USD  (Kette {kette})")
    print(f"  ERGEBNIS        {e['ergebnis']:+,.2f} USD  ({e['ergebnis'] / kap:+.1%} auf {kap:,.0f})")
    print(f"  Buy-and-Hold    {e['bh_ergebnis']:+,.2f} USD  ({e['bh_ergebnis'] / kap:+.1%})")
    diff = e["ergebnis"] - e["bh_ergebnis"]
    urteil = "Grid besser" if diff > 0 else "Halten wäre besser gewesen"
    print(f"  Differenz       {diff:+,.2f} USD   → {urteil}")
    if e["tage_unter_spanne"]:
        print(f"  ACHTUNG         {e['tage_unter_spanne']} Tage komplett unter der Spanne "
              f"(Kapital lag fest)")
    if e["tage_ueber_spanne"]:
        print(f"  ACHTUNG         {e['tage_ueber_spanne']} Tage komplett über der Spanne "
              f"(Grid leer, kein Zukauf)")
    hinweise = plausibel(e)
    if hinweise:
        print()
        for h in hinweise:
            print(f"  ! {h}")


def main():
    with ereignis.lauf("handel/grid"):
        return _main()


def _main():
    p = argparse.ArgumentParser(description="Grid-Simulator (rechnet nur, handelt nicht)")
    p.add_argument("--ticker", default="BTC-USD")
    p.add_argument("--unten", type=float, default=None)
    p.add_argument("--oben", type=float, default=None)
    p.add_argument("--spanne-auto", action="store_true",
                   help="Spanne aus Tief/Hoch des Zeitraums ableiten")
    p.add_argument("--stufen", type=int, default=10)
    p.add_argument("--kapital", type=float, default=2000)
    p.add_argument("--start", default=None)
    p.add_argument("--ende", default=None)
    p.add_argument("--kette", default="solana", choices=list(dca.KOSTEN))
    p.add_argument("--linear", action="store_true", help="gleiche absolute statt prozentuale Abstände")
    p.add_argument("--raster", action="store_true", help="mehrere Stufenzahlen vergleichen")
    p.add_argument("--hebel", type=float, default=1.0)
    p.add_argument("--modus", default="isoliert", choices=["isoliert", "cross"],
                   help="Margin je Stufe oder gemeinsam")
    p.add_argument("--stress", type=float, default=0,
                   help="zusätzlichen Rückgang in %% über 60 Tage anhängen")
    args = p.parse_args()

    df, quelle = kursdaten.laden(args.ticker, still=True)
    start = args.start or df.index[0]
    ende = args.ende or df.index[-1]
    zeitraum = df.loc[start:ende]
    if zeitraum.empty:
        print("Kein Kurs im gewählten Zeitraum.")
        return

    if args.spanne_auto or args.unten is None or args.oben is None:
        unten = float(zeitraum["Low"].min())
        oben = float(zeitraum["High"].max())
        herkunft = "aus Tief/Hoch des Zeitraums"
    else:
        unten, oben = args.unten, args.oben
        herkunft = "vorgegeben"

    print(f"\n{args.ticker}  |  Kapital {args.kapital:,.0f} USD  |  {quelle}")
    print(f"Spanne {herkunft}: {unten:,.2f} – {oben:,.2f}\n")

    if args.raster:
        print(f"  {'Stufen':>7}{'Zyklen':>8}{'Kosten':>10}{'Ergebnis':>12}"
              f"{'in %':>8}{'vs. Halten':>13}")
        print("  " + "-" * 58)
        for n in (5, 10, 20, 40, 80):
            try:
                e = simuliere(df, unten, oben, n, args.kapital, start, ende,
                              args.kette, not args.linear)
            except ValueError:
                continue
            diff = e["ergebnis"] - e["bh_ergebnis"]
            print(f"  {n:>7}{e['zyklen']:>8}{e['kosten']:>10,.0f}"
                  f"{e['ergebnis']:>+12,.0f}{e['ergebnis'] / args.kapital:>+8.0%}"
                  f"{diff:>+13,.0f}")
        e = simuliere(df, unten, oben, 10, args.kapital, start, ende, args.kette)
        print(f"\n  Buy-and-Hold über denselben Zeitraum: {e['bh_ergebnis']:+,.0f} USD")
    else:
        e = simuliere(df, unten, oben, args.stufen, args.kapital, start, ende,
                      args.kette, not args.linear, args.hebel, args.modus,
                      args.stress)
        zeige(e, args.kette)
    print()


if __name__ == "__main__":
    sys.exit(main())

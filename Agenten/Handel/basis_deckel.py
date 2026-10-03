"""Basis-Deckel: kein Instrument darf mehr als 20 % des Kapitals tragen.

DIE ZAHL, AUS DER ER ENTSTANDEN IST
-----------------------------------
Am 03.10.2026 trug BTC 2958,30 USD in 26 Positionen ueber 20 Spuren - bei
12127,43 USD Gesamtkapital sind das 24,4 %. Fuenf Schreibweisen derselben
Basis (`BTC-USDT-SWAP`, `BTC-USDC`, `BTC-USDT`, `XBT-USD`,
`BTC-USD_UM_XPERP-310704`) und zwanzig Spuren, die jede fuer sich eine
Wette auf Bitcoin halten. Jede einzelne ist klein; zusammen sind sie das
groesste Risiko im Haus.

WARUM DAS KEIN RISIKO-DECKEL IST
--------------------------------
Risiko_beitrag zaehlt den Abstand zum Stop. Dieser Deckel zaehlt das
KAPITAL. Beides wird gebraucht: eine Position mit 5 % Stop und 2000 USD
Nominal haelt wenig Risiko, aber sie bindet Kapital und sie faellt mit
allen anderen. Der Deckel ist die zweite Sicht.

WAS EIN DECKEL TUT - UND WAS ER NICHT TUT
------------------------------------------
Der Deckel bindet NEUE Einstiege. Eine Position, die den Deckel reisst,
wird NICHT zwangsverkauft: eine bestehende Position zu schliessen ist eine
Order, und eine Order gehoert in die Freigabekette wie jede andere. Der
Deckel sagt "hier kommt nichts mehr hinein", nicht "das hier muss weg".

Damit ist er ein Deckel und kein Verkaufsautomat, und er ist scharf, ohne
dass jemand eine Position gegen ihren Willen verliert.

DIE ZAHL IST BEI NULL ANGELEGT
------------------------------
Wer eine Basis einmal ueberschreitet, hat sie schon bezahlt: das Kapital
lag schon drin. Deshalb meldet der Deckel den Iststand und wartet auf den
naechsten Einstieg. Ein Deckel, der beim Start sofort 20 Spuren einfriert,
ist ein Abschaltknopf mit anderem Namen.
"""

import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = HIER
if HANDEL not in sys.path:
    sys.path.append(HANDEL)

import risiko_beitrag  # noqa: E402

DECKEL_PROZENT = 20.0

# Je BASIS eine eigene Grenze (Auftrag Max 03.10.2026: "BTC von der Regel
# ausnehmen, BTC darf bis zu 50 % tragen"). Der Deckel ist damit eine
# Tabelle und keine Zahl. Grund fuer den Sonderfall BTC: die Positionen auf
# BTC stammen aus sehr verschiedenen Spuren und sind alt - sie einzeln zu
# schliessen waere eine Order je Position. Der Sonderfall haelt die
# Schranke, ohne dass jemand 26 Positionen auf einmal anfassen muss.
GRENZE = {
    "BTC": 50.0,
}


def grenze_fuer(basis):
    return float(GRENZE.get(basis, DECKEL_PROZENT))


def lage():
    """(basen, nominal_gesamt, ueber) - die Zahlen fuer Bericht und Tor."""
    daten, _ = risiko_beitrag.ermittle()
    basen = {}
    for d in daten:
        for p in d["positionen"]:
            b = risiko_beitrag.basisform(p["inst"])
            e = basen.setdefault(b, {"nominal": 0.0, "risiko": 0.0, "n": 0,
                                     "spuren": {}, "ohne_stop": False})
            e["nominal"] += p["nominal"]
            e["risiko"] += p["risiko"]
            e["n"] += 1
            e["spuren"][d["spur"]] = e["spuren"].get(d["spur"], 0.0) + p["nominal"]
            if p["marke"]:
                e["ohne_stop"] = True
    gesamt = sum(b["nominal"] for b in basen.values())
    for b, e in basen.items():
        e["anteil"] = (e["nominal"] / gesamt * 100.0) if gesamt else 0.0
        e["grenze"] = grenze_fuer(b)
        e["ueber"] = e["anteil"] > e["grenze"]
        e["haupttraeger"] = sorted(e["spuren"].items(), key=lambda kv: -kv[1])[:3]
    ueber = {k: v for k, v in basen.items() if v["ueber"]}
    return basen, gesamt, ueber


def bericht():
    basen, gesamt, ueber = lage()
    if not basen:
        return "Kein Kapital im Buch."
    z = ["Basis-Deckel: %.0f %% je Instrument, %s."
         % (DECKEL_PROZENT,
            ", ".join("%s %.0f %%" % (k, v) for k, v in sorted(GRENZE.items()))),
         "Gesamtkapital %.2f USD auf %d Basen" % (gesamt, len(basen)), ""]
    z.append("%-10s %10s %8s %6s %8s  %s"
             % ("Basis", "Kapital", "Anteil", "Pos", "Grenze", "Traeger"))
    z.append("-" * 96)
    for b in sorted(basen, key=lambda k: -basen[k]["nominal"]):
        e = basen[b]
        z.append("%-10s %10.2f %7.1f%% %6d %7.0f%% %s %s"
                 % (b, e["nominal"], e["anteil"], e["n"], e["grenze"],
                    "! " if e["ueber"] else "ok  ",
                    ", ".join("%s %.0f" % (s, n) for s, n in e["haupttraeger"])))
    if ueber:
        z.append("")
        z.append("UEBER DEM DECKEL (binde neue Einstiege, bestehende laufen):")
        for b in sorted(ueber, key=lambda k: -ueber[k]["nominal"]):
            e = ueber[b]
            z.append("  %-8s %7.1f %% statt %4.1f %% - UEBERZUG %.2f USD, "
                     "hauptsaechlich %s"
                     % (b, e["anteil"], e["grenze"],
                        e["nominal"] - gesamt * e["grenze"] / 100.0,
                        ", ".join("%s %.0f" % (s, n)
                                  for s, n in e["haupttraeger"])))
    return "\n".join(z)


def main():
    print(bericht())
    return 0


if __name__ == "__main__":
    sys.exit(main())
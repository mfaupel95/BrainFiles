"""Parameter-Suche auf einem Fenster, Gegenprobe auf einem anderen.

Warum das noetig ist: suche_gitter.py findet auf den letzten acht Wochen
Spanne 10 % / 8 Stufen mit +2.23 % als Bestwert - aber das ist der Bestwert
von 42 Kombinationen auf EINEM Marktzustand. Ohne Gegenprobe ist nicht zu
unterscheiden, ob das eine Verbesserung ist oder der beste Zufallstreffer.

Verfahren: dieselbe Kombination auf beiden Fenstern rechnen. Was auf dem
Suchfenster gewinnt UND auf dem Prueffenster haelt, ist eine Verbesserung.
Was nur auf dem Suchfenster gewinnt, ist Auswendiglernen.

Fenster (keine Ueberlappung):
  Suche:  mitgelieferte Reihe, acht Wochen VOR dem Prueffenster
  Pruef:  die letzten acht Wochen, live von OKX

Aufruf: python optimieren_gitter.py --wochen 8
"""

import argparse
import datetime as dt
import importlib.util
import os

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)


def lade(name, pfad):
    s = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


b = lade("backtest_gitter", os.path.join(HIER, "backtest_gitter.py"))

SPANNEN = (8.0, 10.0, 15.0, 20.0, 25.0, 30.0)
STUFEN = (6, 8, 12, 16, 24)


def tag(ms):
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).strftime("%Y-%m-%d")


def fenster(wochen):
    n = int(wochen * 7 * 24)
    alle = b.kerzen_lokal(
        os.path.join(HANDEL, "kerzen_BTC-USDT_1H_8760.json"), 8800)
    pruef = b.kerzen_holen(b.INST["instId"], "1H", n)
    alt = [k for k in alle if k[0] < pruef[0][0]]
    return alt[-n:], pruef


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--wochen", type=float, default=8.0)
    a = p.parse_args()

    such, pruef = fenster(a.wochen)
    basis = b.wachen()
    e_s = b.lauf(such, basis)
    e_p = b.lauf(pruef, basis)
    print("Suche  %s..%s  Markt %+.2f %%   Gitter %+.2f %%"
          % (tag(such[0][0]), tag(such[-1][0]), e_s["halten_pct"], e_s["rendite_pct"]))
    print("Pruef  %s..%s  Markt %+.2f %%   Gitter %+.2f %%"
          % (tag(pruef[0][0]), tag(pruef[-1][0]), e_p["halten_pct"], e_p["rendite_pct"]))
    print()

    zeilen = []
    for spanne in SPANNEN:
        for stufen in STUFEN:
            w = dict(basis)
            w["spanne_prozent"] = spanne
            w["stufen"] = stufen
            try:
                a1 = b.lauf(such, w)
                a2 = b.lauf(pruef, w)
            except Exception:          # noqa: BLE001 - zu enge Spanne
                continue
            zeilen.append((spanne, stufen, a1, a2))

    print("%-7s %-6s | %9s %9s %7s | %9s" %
          ("Spanne", "Stufen", "Suche", "Pruef", "haelt", "Halten(P)"))
    print("-" * 62)
    for spanne, stufen, a1, a2 in zeilen:
        h = "ja" if a2["rendite_pct"] > e_p["rendite_pct"] else "nein"
        print("%-7.1f %-6d | %+8.2f%% %+8.2f%% %7s | %+8.2f%%"
              % (spanne, stufen, a1["rendite_pct"], a2["rendite_pct"], h,
                 a2["halten_pct"]))

    if not zeilen:
        print("keine gueltige Kombination")
        return
    bester_s = max(zeilen, key=lambda z: z[2]["rendite_pct"])
    print()
    print("Bestes auf der SUCHE: Spanne %.1f %%, %d Stufen  ->  suche %+.2f %%"
          % (bester_s[0], bester_s[1], bester_s[2]["rendite_pct"]))
    print("  dasselbe ungesehen:  %+.2f %%   (ohne Aenderung: %+.2f %%)"
          % (bester_s[3]["rendite_pct"], e_p["rendite_pct"]))
    print("  -> %s" % ("HAELT."
                       if bester_s[3]["rendite_pct"] > e_p["rendite_pct"]
                       else "HAELT NICHT - der Suchgewinn ist ungesehen weg."))
    hielte = [z for z in zeilen if z[3]["rendite_pct"] > e_p["rendite_pct"]]
    print()
    print("  Kombinationen, die ungesehen besser sind als die heutige: %d von %d"
          % (len(hielte), len(zeilen)))


if __name__ == "__main__":
    main()
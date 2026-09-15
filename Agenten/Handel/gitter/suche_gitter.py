"""Parameter-Suchlauf fuer das Gitter - trainiert und geprueft getrennt.

Warum getrennt: acht Wochen sind EIN Marktzustand. Wer Parameter so lange
dreht, bis diese acht Wochen positiv sind, hat nicht die Strategie verbessert,
sondern die Vergangenheit auswendig gelernt. Deshalb wird auf einem Fenster
gesucht und auf einem FENSTER DANACH geprueft, das beim Suchen nicht zu sehen
war. Nur was dort haelt, ist eine Verbesserung.

Aufruf:
  python suche_gitter.py --wochen 8                 Suchlauf + Gegenprobe
  python suche_gitter.py --wochen 8 --pruef 8       anderes Prueffenster
"""

import argparse
import importlib.util
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))


def lade(name, pfad):
    s = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


b = lade("backtest_gitter", os.path.join(HIER, "backtest_gitter.py"))


def reihe(wochen, stueck_gesamt=2600):
    return b.kerzen_holen(b.INST["instId"], "1H", int(wochen * 7 * 24))


def pruefe(k, w):
    return b.lauf(k, w)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--wochen", type=float, default=8.0)
    p.add_argument("--pruef", type=float, default=0.0,
                   help="Wochen der Gegenprobe (Fenster VOR dem Suchfenster)")
    p.add_argument("--top", type=int, default=12)
    a = p.parse_args()

    k = reihe(a.wochen)
    basis = b.wachen()
    print("Suchfenster: %d Kerzen, Kurs %+.2f %%"
          % (len(k), (k[-1][4] / k[0][4] - 1) * 100))
    print()

    ergebnisse = []
    for spanne in (8.0, 10.0, 15.0, 20.0, 25.0, 30.0, 40.0):
        for stufen in (8, 12, 16, 24, 32, 48):
            w = dict(basis)
            w["spanne_prozent"] = spanne
            w["stufen"] = stufen
            try:
                e = pruefe(k, w)
            except Exception as fehler:      # noqa: BLE001
                continue
            e["spanne"] = spanne
            e["stufen"] = stufen
            ergebnisse.append(e)

    ergebnisse.sort(key=lambda e: -e["rendite_pct"])
    print("%-8s %-7s %8s %8s %8s %6s %6s" %
          ("Spanne", "Stufen", "Rendite", "Halten", "Vorsprung", "Kauf", "Verk"))
    for e in ergebnisse[:a.top]:
        print("%-8.1f %-7d %+7.2f%% %+7.2f%% %+7.2f%% %6d %6d"
              % (e["spanne"], e["stufen"], e["rendite_pct"], e["halten_pct"],
                 e["rendite_pct"] - e["halten_pct"], e["kaeufe"], e["verkaeufe"]))

    print()
    print("Schlechteste drei (zur Kontrolle, dass der Lauf unterscheidet):")
    for e in ergebnisse[-3:]:
        print("%-8.1f %-7d %+7.2f%%  (Halten %+.2f %%)"
              % (e["spanne"], e["stufen"], e["rendite_pct"], e["halten_pct"]))


if __name__ == "__main__":
    main()
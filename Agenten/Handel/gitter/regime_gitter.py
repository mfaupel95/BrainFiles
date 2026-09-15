"""Wann gewinnt das Gitter, wann verliert es? - der Marktzustand, nicht der Parameter.

Befund aus suche_gitter.py: ueber 42 Parameterkombinationen spannt das Ergebnis
nur rund zwei Prozentpunkte (Spanne 8-40 %, Stufen 8-48). Die Parameter sind
also NICHT der Hebel. Diese Datei prueft die naheliegende Erklaerung: das
Ergebnis haengt am Kursverlauf des Fensters, nicht an der Einstellung.

Verfahren: ein Fenster fester Laenge ueber die ganze verfuegbare Reihe schieben
und je Fenster Gitter-Ergebnis gegen Kursbewegung stellen. Wenn die Erklaerung
stimmt, muss die Punktwolke steigen: je staerker der Kurs laeuft, desto
schlechter das Gitter - und umgekehrt.

Aufruf: python regime_gitter.py --fenster 8 --schritt 1
"""

import argparse
import importlib.util
import json
import os

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)


def lade(name, pfad):
    s = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


b = lade("backtest_gitter", os.path.join(HIER, "backtest_gitter.py"))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fenster", type=float, default=8.0)
    p.add_argument("--schritt", type=float, default=1.0)
    p.add_argument("--spanne", type=float, default=None)
    p.add_argument("--stufen", type=int, default=None)
    a = p.parse_args()

    alle = b.kerzen_lokal(
        os.path.join(HANDEL, "kerzen_BTC-USDT_1H_8760.json"), 8800)
    w = b.wachen()
    if a.spanne:
        w["spanne_prozent"] = a.spanne
    if a.stufen:
        w["stufen"] = a.stufen

    n = int(a.fenster * 7 * 24)
    schritt = int(a.schritt * 7 * 24)
    zeilen = []
    i = 0
    while i + n <= len(alle):
        k = alle[i:i + n]
        try:
            e = b.lauf(k, w)
        except Exception as fehler:      # noqa: BLE001
            print("  Fenster %d uebersprungen: %s" % (i, fehler))
            i += schritt
            continue
        e["von"] = k[0][0]
        zeilen.append(e)
        i += schritt

    if not zeilen:
        print("keine Fenster")
        return

    print("Gitter %.1f %%, %d Stufen - %d Fenster a %.0f Wochen, Schritt %.0f Woche(n)"
          % (w.get("spanne_prozent"), w.get("stufen"), len(zeilen),
             a.fenster, a.schritt))
    print()
    print("%-12s %9s %9s %9s" % ("Fenster ab", "Markt", "Gitter", "Vorsprung"))
    for e in zeilen:
        import datetime as dt
        tag = dt.datetime.fromtimestamp(e["von"] / 1000, dt.timezone.utc)
        print("%-12s %+8.1f%% %+8.2f%% %+8.2f%%"
              % (tag.strftime("%Y-%m-%d"), e["halten_pct"], e["rendite_pct"],
                 e["rendite_pct"] - e["halten_pct"]))

    # Die Frage: haengt das Gitter am Markt?
    markt = [e["halten_pct"] for e in zeilen]
    gitter = [e["rendite_pct"] for e in zeilen]
    mittel_m = sum(markt) / len(markt)
    mittel_g = sum(gitter) / len(gitter)
    oben = sum((m - mittel_m) * (g - mittel_g) for m, g in zip(markt, gitter))
    unten_m = sum((m - mittel_m) ** 2 for m in markt) ** 0.5
    unten_g = sum((g - mittel_g) ** 2 for g in gitter) ** 0.5
    r = oben / (unten_m * unten_g) if unten_m and unten_g else 0.0

    print()
    print("  Mittel Markt  %+.2f %%" % mittel_m)
    print("  Mittel Gitter %+.2f %%" % mittel_g)
    print("  Korrelation Markt/Gitter  %+.2f" % r)
    print()
    print("  Lesart: r nahe -1 heisst, das Gitter verdient genau dann, wenn der")
    print("  Markt sich NICHT bewegt - dann ist der Parameter nicht der Hebel,")
    print("  sondern die Auswahl des Marktzustands.")
    positive = sum(1 for e in gitter if e > 0)
    print()
    print("  Fenster mit positivem Gitter: %d von %d" % (positive, len(gitter)))
    ruhig = [e for e in zeilen if abs(e["halten_pct"]) < 5.0]
    if ruhig:
        m = sum(e["rendite_pct"] for e in ruhig) / len(ruhig)
        print("  Seitwaerts (|Markt| < 5 %%): %d Fenster, Gitter im Mittel %+.2f %%"
              % (len(ruhig), m))
    stark = [e for e in zeilen if abs(e["halten_pct"]) >= 15.0]
    if stark:
        m = sum(e["rendite_pct"] for e in stark) / len(stark)
        print("  Stark (|Markt| >= 15 %%):  %d Fenster, Gitter im Mittel %+.2f %%"
              % (len(stark), m))


if __name__ == "__main__":
    main()
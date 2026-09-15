"""Seitwaerts-Filter fuer das Gitter - gesucht und geprueft auf ZWEI Fenstern.

Befund regime_gitter.py: das Gitter gewinnt in fallenden Fenstern (+7 bis +13
Prozentpunkte Vorsprung) und verliert in steigenden; die Korrelation zum Markt
ist +0.78. Der Parameter ist also nicht der Hebel, sondern die Frage, OB das
Gitter laufen soll.

Geprueft wird ein Filter, der genau das messbar macht: neue Kaufstufen werden
nur belegt, wenn der Kurs nicht weit von seinem eigenen Mittel entfernt steht
- also weder steil auf noch steil ab. Gemessen wird nur aus Kerzen DAVOR
(sma_reihe in backtest_gitter.py).

TRENNUNG: gesucht wird auf dem Fenster VOR dem Prueffenster. Acht Wochen sind
ein Marktzustand; wer so lange dreht, bis das Prueffenster positiv ist, hat
nicht verbessert, sondern auswendig gelernt. Was auf dem Suchfenster gewinnt
und auf dem Prueffenster haelt, ist eine Verbesserung - alles andere nicht.

Aufruf: python filter_gitter.py --wochen 8
"""

import argparse
import datetime as dt
import importlib.util
import os

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)


def _tag(ms):
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).strftime("%Y-%m-%d")


def lade(name, pfad):
    s = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


b = lade("backtest_gitter", os.path.join(HIER, "backtest_gitter.py"))

FENSTER = ((50, 100, 200), (2.0, 4.0, 7.0, 12.0))


def bewerte(k, w, f):
    try:
        return b.lauf(k, w, f)
    except Exception as fehler:          # noqa: BLE001
        return {"rendite_pct": float("nan"), "fehler": str(fehler),
                "halten_pct": 0.0, "kaeufe": 0, "verkaufe": 0}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--wochen", type=float, default=8.0)
    a = p.parse_args()

    n = int(a.wochen * 7 * 24)
    # Suchfenster: die mitgelieferte Reihe, die AELTEREN acht Wochen.
    # Prueffenster: die letzten acht Wochen, live geholt.
    # Beide duerfen sich NICHT ueberlappen, sonst prueft man auf Daten, aus
    # denen man gesucht hat. Der oeffentliche OKX-Abruf reicht dafuer nicht:
    # er gibt nur 1440 Stundenkerzen heraus (60 Tage), also gerade mal die
    # letzten acht Wochen - das Suchfenster davor muss aus der lokalen Reihe
    # kommen.
    alle = b.kerzen_lokal(
        os.path.join(HANDEL, "kerzen_BTC-USDT_1H_8760.json"), 8800)
    pruef = b.kerzen_holen(b.INST["instId"], "1H", n)
    grenze = pruef[0][0]
    alt = [k for k in alle if k[0] < grenze]
    if len(alt) < n:
        raise SystemExit("zu wenig lokale Historie vor dem Prueffenster "
                         "(%d von %d Kerzen)" % (len(alt), n))
    such = alt[-n:]
    w = b.wachen()
    print("Prueffenster beginnt %s" % _tag(grenze))
    print()

    ohne_s = b.lauf(such, w)
    ohne_p = b.lauf(pruef, w)
    print("Suchfenster   Markt %+.2f %%   Gitter ohne Filter %+.2f %%"
          % (ohne_s["halten_pct"], ohne_s["rendite_pct"]))
    print("Prueffenster  Markt %+.2f %%   Gitter ohne Filter %+.2f %%"
          % (ohne_p["halten_pct"], ohne_p["rendite_pct"]))
    print()

    zeilen = []
    for nn in FENSTER[0]:
        for ab in FENSTER[1]:
            f = {"n": nn, "abstand_pct": ab}
            e_s = bewerte(such, w, f)
            e_p = bewerte(pruef, w, f)
            zeilen.append((nn, ab, e_s, e_p))

    print("%-6s %-8s | %10s %8s | %10s %8s" %
          ("SMA", "Abstand", "Such", "Kaeufe", "Pruef", "Kaeufe"))
    print("-" * 62)
    for nn, ab, e_s, e_p in zeilen:
        print("%-6d %-8.1f | %+9.2f%% %8d | %+9.2f%% %8d"
              % (nn, ab, e_s["rendite_pct"], e_s["kaeufe"],
                 e_p["rendite_pct"], e_p["kaeufe"]))

    gueltig = [z for z in zeilen if z[2]["rendite_pct"] == z[2]["rendite_pct"]]
    if not gueltig:
        print("kein Filter gelaufen")
        return
    bester = max(gueltig, key=lambda z: z[2]["rendite_pct"])
    print()
    print("Bestes auf dem SUCHFENSTER: SMA %d, Abstand %.1f %%  ->  such %+.2f %%"
          % (bester[0], bester[1], bester[2]["rendite_pct"]))
    print("  dasselbe auf dem PRUEFFENSTER (ungesehen):        %+.2f %%"
          % bester[3]["rendite_pct"])
    print("  ohne Filter auf dem Prueffenster:                 %+.2f %%"
          % ohne_p["rendite_pct"])
    hielte = bester[3]["rendite_pct"] > ohne_p["rendite_pct"]
    print("  -> %s" % ("HAELT: Filter schlaegt ohne Filter auch ungesehen."
                       if hielte else
                       "HAELT NICHT: der Suchgewinn ist auf dem Prueffenster weg - "
                       "das war Auswendiglernen, keine Verbesserung."))


if __name__ == "__main__":
    main()
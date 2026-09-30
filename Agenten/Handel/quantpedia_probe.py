"""Quantpedia-Befunde auf den eigenen Kerzen nachrechnen.

Warum: die Paper-Zahlen einer fremden Strategie sind keine Handelszahlen. Erst
die eigene Historie mit den eigenen Gebuehren entscheidet. Aufruf aus
Agenten/Handel (Daten aus daten/historie):

    .venv/Scripts/python.exe quantpedia_probe.py stunde            # Stundenprofil BTC
    .venv/Scripts/python.exe quantpedia_probe.py fenster 21 23     # Kauf/Verkauf je UTC-Stunde
    .venv/Scripts/python.exe quantpedia_probe.py donchian          # MAX-Regel und Donchian
    .venv/Scripts/python.exe quantpedia_probe.py vergleich         # gegen Buy & Hold

Ergebnis vom 30.09.2026 (BTC 2021-01..2026-09) steht in
MaxHirn/Wiki/Handel/Lektionen.md, Abschnitt 'Quantpedia'.
"""
import datetime as dt
import json
import statistics as st
import sys

EINSATZ_DATEI_1H = "daten/historie/BTCUSDT_1H.json"
EINSATZ_DATEI_1D = "daten/historie/BTCUSDT_1D.json"
GEBUEHREN = (0.0005, 0.001, 0.006)   # je Seite: OKX-artig, Haus-Standard, Kraken taker


def _laden(pfad):
    k = json.load(open(pfad))
    zeit = [dt.datetime.fromtimestamp(x[0] / 1000, dt.UTC) for x in k]
    return zeit, [x[4] for x in k]


def stunde(pfad=EINSATZ_DATEI_1H):
    """Mittlere Rendite je UTC-Stunde (die Quantpedia-Saisonalitaet)."""
    zeit, c = _laden(pfad)
    print(f"Kerzen {len(c)} von {zeit[0]} bis {zeit[-1]}")
    je = {}
    for i in range(1, len(c)):
        je.setdefault(zeit[i].hour, []).append(c[i] / c[i - 1] - 1)
    print("\nUTC-Stunde  n     Mittel%   t-Wert   Jahr%")
    for h in range(24):
        v = je[h]
        m = st.mean(v)
        print(f"{h:>4}       {len(v):>5}  {m * 100:+.4f}  "
              f"{m / (st.stdev(v) / len(v) ** 0.5):+6.2f}  {((1 + m) ** 365 - 1) * 100:+8.1f}")


def fenster(von, bis, pfad=EINSATZ_DATEI_1H):
    """Kauf beim Schluss der Stunde `von`, Verkauf beim Schluss von `bis`."""
    zeit, c = _laden(pfad)
    idx = {(t.date(), t.hour): i for i, t in enumerate(zeit)}
    r, d = [], []
    for i, t in enumerate(zeit):
        j = idx.get((t.date(), bis))
        if t.hour == von and j is not None:
            r.append(c[j] / c[i] - 1)
            d.append(t.date())
    n = len(r)
    if n < 20:
        print(f"Kauf {von:02d}:00 -> Verkauf {bis:02d}:00: nur {n} Tage, zu wenig")
        return
    m, s = st.mean(r), st.stdev(r)
    jahre = (d[-1] - d[0]).days / 365.25
    kum = 1
    for x in r:
        kum *= 1 + x
    print(f"Kauf {von:02d}:00 -> Verkauf {bis:02d}:00 UTC: n={n}  "
          f"Mittel {m * 100:+.3f}%/Tag  Treffer {sum(1 for x in r if x > 0) / n * 100:.0f}%  "
          f"t={m / (s / n ** 0.5):+.2f}")
    print(f"   brutto {((kum ** (1 / jahre)) - 1) * 100:+.1f}% p.a.")
    for g in GEBUEHREN:
        kn = 1
        for x in r:
            kn *= (1 + x) * (1 - g) ** 2
        print(f"   mit {g * 100:.2f}%/Seite: {((kn ** (1 / jahre)) - 1) * 100:+.1f}% p.a.")
    h = n // 2
    for lab, teil in (("1. Haelfte", r[:h]), ("2. Haelfte", r[h:])):
        mt = st.mean(teil)
        print(f"   {lab}: {mt * 100:+.3f}%/Tag  t={mt / (st.stdev(teil) / len(teil) ** 0.5):+.2f}")


def _kennzahlen(r, d, lab, gebuehr=0.001):
    if not r:
        print(f"{lab}: keine Signale")
        return
    n = len(r)
    jahre = (d[-1] - d[0]).days / 365.25
    m = st.mean(r)
    kum = kn = 1
    for x in r:
        kum *= 1 + x
        kn *= (1 + x) * (1 - gebuehr) ** 2
    print(f"{lab}: Signale {n} ({n / jahre:.1f}/Jahr)  Mittel {m * 100:+.2f}%  "
          f"Treffer {sum(1 for x in r if x > 0) / n * 100:.0f}%  "
          f"t={m / (st.stdev(r) / n ** 0.5):+.2f}")
    print(f"    brutto {((kum ** (1 / jahre)) - 1) * 100:+.1f}% p.a. | "
          f"mit {gebuehr * 100:.1f}%/Seite {((kn ** (1 / jahre)) - 1) * 100:+.1f}% p.a.")


def donchian(pfad=EINSATZ_DATEI_1D):
    """Quantpedia MAX-Regel (Halten 1 Tag) und Donchian-Ausbruch."""
    zeit, c = _laden(pfad)
    print(f"BTC 1D: {len(c)} Kerzen {zeit[0].date()} -> {zeit[-1].date()}")
    print("\nA) MAX-Regel: Kauf bei X-Tage-Hoch, Halten 1 Tag")
    for w in (5, 10, 20, 30, 50):
        r, d = [], []
        for i in range(w, len(c) - 1):
            if c[i] >= max(c[i - w:i]):
                r.append(c[i + 1] / c[i] - 1)
                d.append(zeit[i].date())
        _kennzahlen(r, d, f"  MAX({w}) 1 Tag")
    print("\nB) Donchian: Kauf ueber X-Tage-Hoch, Verkauf unter X-Tage-Tief")
    for w in (10, 20, 30, 50):
        r, d, pos = [], [], None
        for i in range(w, len(c)):
            if pos is None and c[i] > max(c[i - w:i]):
                pos = c[i]
            elif pos is not None and c[i] < min(c[i - w:i]):
                r.append(c[i] / pos - 1)
                d.append(zeit[i].date())
                pos = None
        _kennzahlen(r, d, f"  Donchian({w})")


def vergleich(pfad=EINSATZ_DATEI_1D):
    """Donchian netto gegen Buy & Hold, mit Rueckgang und Zeit im Markt."""
    zeit, c = _laden(pfad)
    d0, d1 = zeit[0].date(), zeit[-1].date()
    jahre = (d1 - d0).days / 365.25

    def rueckgang(kurve):
        hoch, tief = -1e9, 0.0
        for v in kurve:
            hoch = max(hoch, v)
            tief = min(tief, v / hoch - 1)
        return tief * 100

    print(f"Zeitraum {d0} .. {d1} ({jahre:.1f} Jahre)")
    print(f"BTC Buy&Hold: {((c[-1] / c[0]) ** (1 / jahre) - 1) * 100:+.1f}% p.a., "
          f"max. Rueckgang {rueckgang(c):.0f}%")
    for w in (20, 30):
        eq, kurve, pos, tage = [1.0], [1.0], None, 0
        for i in range(w, len(c)):
            if pos is None and c[i] > max(c[i - w:i]):
                pos = c[i] * (1 + 0.001)
            elif pos is not None and c[i] < min(c[i - w:i]):
                eq.append(eq[-1] * (c[i] * (1 - 0.001)) / pos)
                pos = None
            if pos is not None:
                tage += 1
            kurve.append(eq[-1] if pos is None else eq[-1] * c[i] / pos)
        print(f"Donchian({w}) netto 0,1%/Seite: {((eq[-1]) ** (1 / jahre) - 1) * 100:+.1f}% p.a., "
              f"max. Rueckgang {rueckgang(kurve):.0f}%, "
              f"Tage im Markt {tage}/{len(c) - w} = {tage / (len(c) - w) * 100:.0f}%")


def main(argv):
    if not argv or argv[0] == "stunde":
        stunde()
    elif argv[0] == "fenster":
        fenster(int(argv[1]), int(argv[2]))
    elif argv[0] == "donchian":
        donchian()
    elif argv[0] == "vergleich":
        vergleich()
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
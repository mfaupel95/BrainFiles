"""Time-Series-Momentum (TSMOM, Quantpedia #0118) und die QQQ/BTC-Rotation messen.

Ergaenzt die Quantpedia-Nachrechnung (quantpedia_probe.py, T-209 Donchian) um
die beiden Kandidaten aus T-210. Gleiche Konvention wie die Probe: nur die
EIGENE Historie mit den EIGENEN Gebuehren entscheidet; geschrieben wird hier
gar nichts (reiner Messlauf, kein Schreib- und kein Spuren-Pfad).

Aufruf aus Agenten/Handel (Daten aus daten/historie):

    .venv/Scripts/python.exe tsmom_probe.py tsmom            # TSMOM BTC/ETH/SOL 1D
    .venv/Scripts/python.exe tsmom_probe.py qqq             # QQQ/BTC-Rotation (Datenlage)
    .venv/Scripts/python.exe tsmom_probe.py vergleich       # gegen Buy & Hold

TSMOM-Regel (T-210, QuantConnect-Gegenprobe Sharpe ~0,3 / CAGR 7,29 %, #0118):
  12-Monats-Rendite je Instrument am Monatsende; Positionsgroesse invers zur
  realisierten 20-Tage-Volatilitaet (Ziel: Monats-Volatilitaet 4 %); monatliche
  Neuverteilung; Gebuehr je Seite bei jeder Umschichtung (2x je Umschichtmonat).

Kennzahlen wie T-209: Monate, t-Stat, Sharpe p.a., brutto/netto p.a.
"""
import datetime as dt
import json
import os
import statistics as st
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HIER, "daten", "historie")
FEED = os.path.join(ROOT, "feed")
GEBUEHREN = (0.0005, 0.001, 0.006)          # je Seite: OKX-artig, Haus, Kraken taker
EPHEMEREN = ("BTCUSDT_1D", "ETHUSDT_1D", "SOLUSDT_1D")
SIGNAL_TAGE = 365          # 12-Monats-Fenster in Tagen
VOL_TAGE = 20              # realisierte Volatilitaet


def _laden(pfad):
    """Eigene Kerzen: [ts_ms, open, high, low, close, vol], close = Feld 4."""
    k = json.load(open(pfad, encoding="utf-8"))
    zeit = [dt.datetime.fromtimestamp(x[0] / 1000, dt.UTC) for x in k]
    return zeit, [x[4] for x in k]


def _rueckgang(kurve):
    hoch, tief = -1e18, 0.0
    for v in kurve:
        hoch = max(hoch, v)
        tief = min(tief, v / hoch - 1)
    return tief * 100


def _monatswechsel(zeit):
    """Indizes des MonatsENDEs (letzte Kerze des Monats)."""
    aus = []
    letzter = None
    for i, t in enumerate(zeit):
        schluessel = (t.year, t.month)
        if schluessel != letzter:
            if letzter is not None:
                aus.append(i - 1)      # letzte Kerze des Vormonats
            letzter = schluessel
    aus.append(len(zeit) - 1)
    return aus


def _realvol_20(c, i):
    """Realisierte 20-Tage-Volatilitaet (Monatsbasis) bis Kerze i."""
    if i < VOL_TAGE:
        return None
    r = [c[j] / c[j - 1] - 1 for j in range(i - VOL_TAGE + 1, i + 1)]
    m = st.mean(r)
    var = sum((x - m) ** 2 for x in r) / (len(r) - 1)
    return var ** 0.5 * (21 ** 0.5)    # Monats-Volatilitaet


def _kennzahlen(r, d, lab, gebuehr_je_umschicht=1):
    """t-Stat, Sharpe p.a., Rueckgang, brutto/netto p.a. — das T-209-Raster.

    Sharpe p.a. wird aus dem t-Wert zurueckgerechnet (t = Sharpe_je_Periode
    * sqrt(n) => Sharpe_pa = t * sqrt(12) / sqrt(n)).
    """
    if not r:
        print(f"{lab}: keine Monate (Historie zu kurz fuer 12-Monats-Signal)")
        return
    n = len(r)
    jahre = (d[-1] - d[0]).days / 365.25
    if jahre <= 0 or n < 2:
        print(f"{lab}: n={n}, jahre={jahre:.2f} - zu wenig fuer Kennzahlen")
        return
    m = st.mean(r)
    s = st.stdev(r)
    if s == 0:
        print(f"{lab}: n={n} ohne Streuung - keine Kennzahlen")
        return
    t = m / (s / n ** 0.5)
    sharpe = t * (12 ** 0.5) / (n ** 0.5)
    kum = 1.0
    kurve = [1.0]
    for x in r:
        kum *= 1 + x
        kurve.append(kum)
    print(f"{lab}: Monate {n} ({n / jahre:.0f}/Jahr)  Mittel {m * 100:+.2f}%/Monat  "
          f"Treffer {sum(1 for x in r if x > 0) / n * 100:.0f}%  t={t:+.2f}  "
          f"Sharpe p.a. {sharpe:+.2f}")
    print(f"    brutto {((kum ** (1 / jahre)) - 1) * 100:+.1f}% p.a., "
          f"max. Rueckgang {_rueckgang(kurve):.0f}%")
    for g in GEBUEHREN:
        kn = 1.0
        for x in r:
            kn *= (1 + x) * (1 - g) ** (2 * gebuehr_je_umschicht)
        print(f"    mit {g * 100:.2f}%/Seite: {((kn ** (1 / jahre)) - 1) * 100:+.1f}% p.a.")


def tsmom():
    """TSMOM: 12M-Signal, inverse Vol, monatliche Neuverteilung."""
    print("TSMOM (#0118): 12-Monats-Signal, inverse Vol, monatliche Neuverteilung\n")
    for name in EPHEMEREN:
        pfad = os.path.join(ROOT, name + ".json")
        if not os.path.isfile(pfad):
            print(f"{name}: keine eigene 1D-Historie ({pfad})")
            continue
        zeit, c = _laden(pfad)
        wechsel = _monatswechsel(zeit)
        r, d, groesse = [], [], 0.0
        for k in range(len(wechsel) - 1):
            i = wechsel[k]                     # Monatsende: Signal berechnen
            if i < SIGNAL_TAGE:
                groesse = 0.0
                continue
            rendite12 = c[i] / c[i - SIGNAL_TAGE] - 1
            real = _realvol_20(c, i)
            if real is None or real <= 0:
                continue
            groesse = (0.04 / real) if rendite12 > 0 else 0.0
            # Monat der Position: vom Monatsende i bis zum naechsten Monatsende
            j = wechsel[k + 1]
            mon_r = (c[j] / c[i] - 1) * groesse
            r.append(mon_r)
            d.append(zeit[j].date())
        _kennzahlen(r, d, f"  {name} TSMOM(12M)")
    print(f"\nReferenz T-209 (Donchian(30) BTC 1D): netto +17,8 % p.a., max. -43 %, t=+1,25")


def qqq():
    """QQQ/BTC-Rotation (Blog): Donchian 5..50, Rotation QQQ/BTC/Cash."""
    print("QQQ/BTC-Rotation (Donchian 5..50 Tage, QQQ/BTC/Cash)\n")
    pfad = os.path.join(FEED, "QQQBUSDT_1D.json")
    if not os.path.isfile(pfad):
        print(f"QQQ 1D fehlt im feed: {pfad}")
        print("-> Rotation auf EIGENEN Daten nicht messbar (Datenluecke).")
        return
    zeit, c = _laden(pfad)
    if len(c) < 150:
        print(f"QQQ 1D nur {len(c)} Kerzen ({zeit[0].date()}..{zeit[-1].date()}) - "
              f"fuer eine Donchian(50)-Messung ueber 2019..2026 zu kurz.")
        print("-> Datenluecke: QQQ-Tageskerzen nachladen (T-210).")
        return
    print(f"QQQ 1D: {len(c)} Kerzen {zeit[0].date()}..{zeit[-1].date()}")
    for w in (5, 20, 30, 50):
        r, d, pos = [], [], None
        for i in range(w, len(c) - 1):
            if pos is None and c[i] > max(c[i - w:i]):
                pos = c[i]
            elif pos is not None and c[i] < min(c[i - w:i]):
                r.append(c[i] / pos - 1)
                d.append(zeit[i].date())
                pos = None
        _kennzahlen(r, d, f"  QQQ Donchian({w})")


def vergleich():
    """Buy & Hold als Referenzrahmen (wie quantpedia_probe.vergleich)."""
    print("Buy & Hold (Referenzrahmen zu T-209)\n")
    for name in EPHEMEREN:
        pfad = os.path.join(ROOT, name + ".json")
        if not os.path.isfile(pfad):
            continue
        zeit, c = _laden(pfad)
        jahre = (zeit[-1] - zeit[0]).days / 365.25
        bnh = ((c[-1] / c[0]) ** (1 / jahre) - 1) * 100
        print(f"{name}: Buy & Hold {bnh:+.1f}% p.a., max Rueckgang {_rueckgang(c):.0f}%")


def main(argv):
    if not argv or argv[0] == "tsmom":
        tsmom()
    elif argv[0] == "qqq":
        qqq()
    elif argv[0] == "vergleich":
        vergleich()
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
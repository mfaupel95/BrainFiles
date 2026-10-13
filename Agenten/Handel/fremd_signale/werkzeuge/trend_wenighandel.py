"""Handelsarme Trend-Varianten (Long/Flat, Spot) auf OKX BTC-USDT, vorab FESTGELEGT (kein Optimieren):
 A: SMA 50/200 (Golden Cross), 1D          B: Donchian 55 rein / 20 raus, 1D
 C: Donchian 20 rein / 10 raus, 1D         D: EMA 20/50, 4H
 E: Donchian 55 rein / 20 raus auf 4H-Kerzen (Fenster in 4H-Kerzen: 330/120)
Kosten 0,07 %/Seite, Signal auf Schluss, Ausfuehrung 1 Kerze spaeter. Zeitraum: alles verfuegbare (>= 4 Jahre).
Erfolg (vorab): netto > 0 in BEIDEN Haelften UND maxDD kleiner als Buy&Hold UND <= 30 Wechsel/Jahr.
Aufruf: python trend_wenighandel.py"""
import csv, json, os, time, urllib.request
import numpy as np

HIER = os.path.dirname(os.path.abspath(__file__))
KOST = 0.0007
INST = "BTC-USDT"


def lade(bar, tage):
    cache = os.path.join(HIER, "trend_%s_%s_%dd.csv" % (INST, bar, tage))
    if os.path.exists(cache):
        return [tuple(map(float, r)) for r in csv.reader(open(cache))]
    bis, z, ziel = "", {}, time.time() * 1000 - tage * 86400000
    while True:
        u = "https://www.okx.com/api/v5/market/history-candles?instId=%s&bar=%s&limit=100%s" % (INST, bar, ("&after=" + bis) if bis else "")
        d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "brainfiles/1.0"}), timeout=20))["data"]
        if not d:
            break
        for x in d:
            if x[8] == "1":
                z[int(x[0])] = (int(x[0]), float(x[4]))
        bis = d[-1][0]
        if int(bis) < ziel:
            break
        time.sleep(0.12)
    out = sorted(z.values())
    csv.writer(open(cache, "w", newline="")).writerows(out)
    return out


def sma(x, n):
    c = np.cumsum(np.insert(x, 0, 0.0)); o = np.full(len(x), np.nan)
    o[n - 1:] = (c[n:] - c[:-n]) / n
    return o


def ema(x, n):
    a = 2.0 / (n + 1); o = np.empty_like(x); o[0] = x[0]
    for i in range(1, len(x)):
        o[i] = a * x[i] + (1 - a) * o[i - 1]
    return o


def donchian(c, rein, raus):
    pos = np.zeros(len(c)); an = False
    for i in range(len(c)):
        if i >= rein and not an and c[i] > np.max(c[i - rein:i]):
            an = True
        elif an and i >= raus and c[i] < np.min(c[i - raus:i]):
            an = False
        pos[i] = 1.0 if an else 0.0
    return pos


def bewerte(c, sig, name, pro_jahr):
    pos = np.roll(sig, 1); pos[0] = 0.0
    r = np.zeros(len(c)); r[1:] = c[1:] / c[:-1] - 1
    wechsel = np.abs(np.diff(pos, prepend=0.0))
    netto = pos * r - wechsel * KOST
    eq = np.cumprod(1 + netto); bh = np.cumprod(1 + r)
    dd = lambda e: float(np.max(1 - e / np.maximum.accumulate(e)))
    h = len(c) // 2
    n1, n2 = float(np.prod(1 + netto[:h]) - 1), float(np.prod(1 + netto[h:]) - 1)
    b1, b2 = float(np.prod(1 + r[:h]) - 1), float(np.prod(1 + r[h:]) - 1)
    jahre = len(c) / pro_jahr
    wj = wechsel.sum() / jahre
    ok = n1 > 0 and n2 > 0 and dd(eq) < dd(bh) and wj <= 30
    print("%-22s Gesamt %+7.1f%% (B&H %+7.1f%%) | 1.Haelfte %+6.1f%% (B&H %+6.1f%%) 2.Haelfte %+6.1f%% (B&H %+6.1f%%) | maxDD %4.1f%% (B&H %4.1f%%) | Wechsel/Jahr %4.1f | %s"
          % (name, (eq[-1] - 1) * 100, (bh[-1] - 1) * 100, n1 * 100, b1 * 100, n2 * 100, b2 * 100, dd(eq) * 100, dd(bh) * 100, wj, "ERFUELLT" if ok else "nicht erfuellt"))


d1 = np.array([x[1] for x in lade("1D", 2000)])
d4 = np.array([x[1] for x in lade("4H", 1500)])
print("1D: %d Kerzen (%.1f Jahre) | 4H: %d Kerzen (%.1f Jahre) | Kosten %.2f%%/Seite" % (len(d1), len(d1) / 365, len(d4), len(d4) / 2190, KOST * 100))
bewerte(d1, (sma(d1, 50) > sma(d1, 200)).astype(float), "A SMA 50/200 1D", 365)
bewerte(d1, donchian(d1, 55, 20), "B Donchian 55/20 1D", 365)
bewerte(d1, donchian(d1, 20, 10), "C Donchian 20/10 1D", 365)
bewerte(d4, (ema(d4, 20) > ema(d4, 50)).astype(float), "D EMA 20/50 4H", 2190)
bewerte(d4, donchian(d4, 330, 120), "E Donchian 55d/20d 4H", 2190)

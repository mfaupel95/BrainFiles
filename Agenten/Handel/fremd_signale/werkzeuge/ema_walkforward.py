"""Walk-forward der EMA-Kreuzung (Long/Flat, Spot) auf OKX-Kerzen. Vorab festgelegt (siehe Kopf der Auswertung):
Gebuehr 0,05 %/Seite + Slippage 0,02 %/Seite; Signal auf Schlusskurs der Kerze, Ausfuehrung zum Schluss der naechsten Kerze
(1 Kerze Verzug). Raster fast {5,8,10,13,20}, slow {20,30,50,80,120}; IS 30 Tage waehlt, OOS naechste 7 Tage, Schritt 7 Tage.
Erfolg: OOS-Summe netto > 0 UND OOS besser als Buy&Hold-Differenz? -> hier: OOS netto > 0 in >= 60 % der Fenster UND Summe > 0.
Aufruf: python ema_walkforward.py <bar: 5m|1H> [tage]"""
import csv, json, os, sys, time, urllib.request
import numpy as np

BAR = sys.argv[1] if len(sys.argv) > 1 else "5m"
TAGE = int(sys.argv[2]) if len(sys.argv) > 2 else 120
INST = "BTC-USDC"
BAR_S = {"5m": 300, "1H": 3600}[BAR]
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ema_wf_%s_%s_%dd.csv" % (INST, BAR, TAGE))
KOST = 0.0005 + 0.0002   # je Seite


def lade():
    if os.path.exists(CACHE):
        return [tuple(map(float, r)) for r in csv.reader(open(CACHE))]
    bis, zeilen, ziel = "", {}, time.time() * 1000 - TAGE * 86400 * 1000
    while True:
        url = "https://www.okx.com/api/v5/market/history-candles?instId=%s&bar=%s&limit=100%s" % (INST, BAR, ("&after=" + bis) if bis else "")
        d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "brainfiles/1.0"}), timeout=20))["data"]
        if not d:
            break
        for x in d:
            if x[8] == "1":
                zeilen[int(x[0])] = (int(x[0]), float(x[4]))
        bis = d[-1][0]
        if int(bis) < ziel:
            break
        time.sleep(0.12)
    out = sorted(zeilen.values())
    csv.writer(open(CACHE, "w", newline="")).writerows(out)
    return out


def ema(x, n):
    a = 2.0 / (n + 1)
    o = np.empty_like(x); o[0] = x[0]
    for i in range(1, len(x)):
        o[i] = a * x[i] + (1 - a) * o[i - 1]
    return o


def sim(c, f, s):
    """Netto-Rendite der Long/Flat-Strategie ueber c (Schlusskurse). Position wirkt ab naechster Kerze."""
    sig = (ema(c, f) > ema(c, s)).astype(float)
    sig[: s] = 0.0
    pos = np.roll(sig, 1); pos[0] = 0.0
    r = np.diff(c, prepend=c[0]) / np.maximum(np.roll(c, 1), 1e-9); r[0] = 0.0
    wechsel = np.abs(np.diff(pos, prepend=0.0))
    netto = pos * r - wechsel * KOST
    return float(np.sum(netto)), int(wechsel.sum())


def main():
    d = lade()
    c = np.array([x[1] for x in d])
    n_pro_tag = 86400 // BAR_S
    IS, OOS = 30 * n_pro_tag, 7 * n_pro_tag
    raster = [(f, s) for f in (5, 8, 10, 13, 20) for s in (20, 30, 50, 80, 120) if f < s]
    print("Kerzen %d (%s, %.0f Tage) | Fenster IS %dd / OOS 7d | Kosten %.2f%%/Seite" % (len(c), BAR, len(c) / n_pro_tag, 30, KOST * 100))
    fenster, i = [], 0
    while i + IS + OOS <= len(c):
        ist, oos = c[i:i + IS], c[i + IS - 120:i + IS + OOS]   # 120 Vorlauf fuer EMA
        beste = max(raster, key=lambda p: sim(ist, *p)[0])
        # OOS: nur den OOS-Teil werten (Vorlauf zaehlt nicht)
        r_all, _ = sim(oos, *beste)
        r_vor, _ = sim(oos[:120], *beste)
        r_fix, _ = sim(oos, 10, 20)
        r_fix0, _ = sim(oos[:120], 10, 20)
        bh = (c[i + IS + OOS - 1] / c[i + IS - 1] - 1)
        fenster.append((beste, r_all - r_vor, r_fix - r_fix0, bh))
        i += OOS
    w = len(fenster)
    gew = [f[1] for f in fenster]; fix = [f[2] for f in fenster]; bh = [f[3] for f in fenster]
    print("Fenster:", w)
    print("OOS gewaehlt : Summe %+.2f%% | Fenster positiv %d/%d | Mittel %+.3f%%" % (sum(gew) * 100, sum(g > 0 for g in gew), w, np.mean(gew) * 100))
    print("OOS fix 10/20: Summe %+.2f%% | Fenster positiv %d/%d | Mittel %+.3f%%" % (sum(fix) * 100, sum(g > 0 for g in fix), w, np.mean(fix) * 100))
    print("Buy&Hold     : Summe %+.2f%% (Fenster positiv %d/%d)" % (sum(bh) * 100, sum(g > 0 for g in bh), w))
    ok = sum(gew) > 0 and sum(g > 0 for g in gew) >= 0.6 * w
    print("Kriterium (OOS Summe>0 UND >=60%% Fenster positiv): %s" % ("ERFUELLT" if ok else "NICHT erfuellt"))
    print("gewaehlte Parameter:", [f[0] for f in fenster][:8], "...")


main()

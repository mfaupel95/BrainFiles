"""Ensemble-Donchian (nach Zarattini/Pagani/Barbon, 'Catching Crypto Trends', SFI 25-80) - VORAB festgelegt, nicht optimiert.
Lookbacks n in {5,10,20,30,60,90,150,250,360} (Tage). Je Modell: rein ueber Max(n), raus unter Min(n/2). Position = Anteil der Modelle im Markt.
 F: Ensemble 1D, gleichgewichtet, Position 0..1
 G: wie F + Volatilitaets-Skalierung (Ziel 40 % p. a., 30-Tage-Vola, Deckel 1,0 = kein Hebel)
 H: Ensemble auf 4H (Lookbacks in 4H-Kerzen = n*6)
Kosten 0,07 %/Seite auf Positionsaenderung, 1 Kerze Verzug. BTC-USDT OKX.
Erfolg vorab: netto > 0 in BEIDEN Haelften UND maxDD < Buy&Hold UND Sharpe >= Buy&Hold-Sharpe.
Referenz: A (SMA50/200) und B (Donchian 55/20) aus trend_wenighandel.py."""
import numpy as np
src = open(r"O:\Werkstatt\trend_wenighandel.py").read().split("d1 = np.array")[0]
ns = {"__file__": r"O:\Werkstatt\trend_wenighandel.py"}; exec(src, ns)
KOST = 0.0007
NS = (5, 10, 20, 30, 60, 90, 150, 250, 360)


def donch(c, rein, raus):
    return ns["donchian"](c, rein, raus)


def ensemble(c, faktor=1):
    pos = np.zeros(len(c))
    for n in NS:
        pos += donch(c, n * faktor, max(2, n * faktor // 2))
    return pos / len(NS)


def volskal(c, pos, pro_jahr, ziel=0.40):
    r = np.zeros(len(c)); r[1:] = c[1:] / c[:-1] - 1
    v = np.full(len(c), np.nan)
    f = 30 * (pro_jahr // 365)
    for i in range(f, len(c)):
        v[i] = np.std(r[i - f + 1:i + 1]) * np.sqrt(pro_jahr)
    k = np.where(np.isnan(v) | (v <= 0), 0.0, np.minimum(1.0, ziel / np.where(v > 0, v, 1)))
    return pos * k


def bewerte(c, sig, name, pro_jahr):
    pos = np.roll(sig, 1); pos[0] = 0.0
    r = np.zeros(len(c)); r[1:] = c[1:] / c[:-1] - 1
    w = np.abs(np.diff(pos, prepend=0.0))
    net = pos * r - w * KOST
    eq, bh = np.cumprod(1 + net), np.cumprod(1 + r)
    dd = lambda e: float(np.max(1 - e / np.maximum.accumulate(e)))
    sh = lambda x: float(np.mean(x) / np.std(x) * np.sqrt(pro_jahr)) if np.std(x) > 0 else 0.0
    h = len(c) // 2
    n1, n2 = float(np.prod(1 + net[:h]) - 1), float(np.prod(1 + net[h:]) - 1)
    ok = n1 > 0 and n2 > 0 and dd(eq) < dd(bh) and sh(net) >= sh(r)
    print("%-26s Gesamt %+7.1f%% (B&H %+7.1f%%) | H1 %+6.1f%% H2 %+6.1f%% | maxDD %4.1f%% (%4.1f%%) | Sharpe %4.2f (B&H %4.2f) | Umschicht./Jahr %5.1f | %s"
          % (name, (eq[-1] - 1) * 100, (bh[-1] - 1) * 100, n1 * 100, n2 * 100, dd(eq) * 100, dd(bh) * 100, sh(net), sh(r),
             w.sum() / (len(c) / pro_jahr), "ERFUELLT" if ok else "nicht erfuellt"))


d1 = np.array([x[1] for x in ns["lade"]("1D", 2000)])
d4 = np.array([x[1] for x in ns["lade"]("4H", 1500)])
print("1D %.1f J | 4H %.1f J | Kosten %.2f%%/Seite" % (len(d1) / 365, len(d4) / 2190, KOST * 100))
bewerte(d1, ns["donchian"](d1, 55, 20), "B Donchian 55/20 (Ref)", 365)
bewerte(d1, (ns["sma"](d1, 50) > ns["sma"](d1, 200)).astype(float), "A SMA50/200 (Ref)", 365)
f = ensemble(d1)
bewerte(d1, f, "F Ensemble 1D", 365)
bewerte(d1, volskal(d1, f, 365), "G Ensemble 1D + Vola 40%", 365)
bewerte(d4, ensemble(d4, 6), "H Ensemble 4H", 2190)
bewerte(d4, volskal(d4, ensemble(d4, 6), 2190), "H2 Ensemble 4H + Vola 40%", 2190)

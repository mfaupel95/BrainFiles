#!/usr/bin/env python3
"""Schattenbuch des Ensemble-Donchian (Variante H2): bewertet die Strategie in PROZENT, unabhaengig vom
Papierbuch und vom Bus (kein Stop, kein Nur-long/flat-Zwang, Gewichte stetig 0..1, Umschichtung kostet 0,07 %).

Lauf: python schattenbuch.py [--start-jetzt]     (reines numpy/stdlib, kein Nautilus)
 - Kerzen: OKX BTC-USDC 4H, Cache adapter_stand/schatten_kerzen.csv (einmal 2400, danach nur die neuesten).
 - Start: adapter_stand/schatten.json {"start_ms": ...}; --start-jetzt setzt den Start auf die letzte Kerze.
 - Ausgabe: Agenten/Routinen/logs/schattenbuch.txt (Strategie vs. Buy&Hold seit Start, Gewicht jetzt).
Handelt nie. Gleiche Regeln wie Bus/nautilus_signalgeber.EnsembleSignalgeber.
"""
import csv
import json
import os
import sys
import time
import urllib.request

HIER = os.path.dirname(os.path.abspath(__file__))
STAND = os.path.join(HIER, "adapter_stand")
KERZEN = os.path.join(STAND, "schatten_kerzen.csv")
ZUSTAND = os.path.join(STAND, "schatten.json")
BERICHT = os.path.join(os.path.dirname(HIER), "Routinen", "logs", "schattenbuch.txt")
INST, BAR, BAR_S, F = "BTC-USDC", "4H", 14400, 6
LOOKBACKS = (5, 10, 20, 30, 60, 90, 150, 250, 360)
KOST, VOLA_ZIEL, N_ZIEL = 0.0007, 0.40, 2400


def gewichte(c):
    """Stetiges Zielgewicht je Kerze (0..1) aus den Schlusskursen c (Liste)."""
    an = {n: False for n in LOOKBACKS}
    w = []
    for i in range(len(c)):
        for n in LOOKBACKS:
            rein, raus = n * F, max(2, n * F // 2)
            if i < rein:
                continue
            if not an[n] and c[i] > max(c[i - rein:i]):
                an[n] = True
            elif an[n] and i >= raus and c[i] < min(c[i - raus:i]):
                an[n] = False
        anteil = sum(an.values()) / len(LOOKBACKS)
        fenster = 30 * F
        if i < fenster:
            w.append(0.0)
            continue
        r = [c[j] / c[j - 1] - 1 for j in range(i - fenster + 1, i + 1)]
        m = sum(r) / len(r)
        vola = (sum((x - m) ** 2 for x in r) / len(r)) ** 0.5 * (365 * F) ** 0.5
        w.append(anteil * (min(1.0, VOLA_ZIEL / vola) if vola > 0 else 0.0))
    return w


def verlauf(c, w, ab):
    """(eq_strategie, eq_buyhold) ab Schluss der Kerze `ab` (Start = 1.0). Das Gewicht, das am Schluss einer
    Kerze gilt, wirkt auf die naechste; der Einstieg ins Startgewicht kostet wie eine Umschichtung."""
    pos = w[ab]
    eq, bh = 1.0 - pos * KOST, 1.0
    for i in range(ab + 1, len(c)):
        r = c[i] / c[i - 1] - 1
        eq *= 1 + pos * r
        bh *= 1 + r
        neu = w[i]
        eq *= 1 - abs(neu - pos) * KOST
        pos = neu
    return eq, bh


def lade_kerzen():
    os.makedirs(STAND, exist_ok=True)
    z = {}
    if os.path.exists(KERZEN):
        for r in csv.reader(open(KERZEN)):
            z[int(r[0])] = float(r[1])
    bis, hist = "", len(z) < N_ZIEL
    while True:
        pfad = "history-candles" if (bis or hist) else "candles"
        url = "https://www.okx.com/api/v5/market/%s?instId=%s&bar=%s&limit=%d" % (pfad, INST, BAR, 100 if pfad == "history-candles" else 300)
        if bis:
            url += "&after=" + bis
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "brainfiles/1.0"}), timeout=15) as r:
            d = json.load(r)["data"]
        if not d:
            break
        for x in d:
            if x[8] == "1":
                z[int(x[0])] = float(x[4])
        bis = d[-1][0]
        if not hist or len(z) >= N_ZIEL:
            break
        time.sleep(0.12)
    ks = sorted(z)[-N_ZIEL:]
    with open(KERZEN, "w", newline="") as f:
        csv.writer(f).writerows((k, z[k]) for k in ks)
    return ks, [z[k] for k in ks]


def main(argv):
    ks, c = lade_kerzen()
    if len(c) < 400:
        print("zu wenige Kerzen:", len(c))
        return 1
    w = gewichte(c)
    start = None
    if os.path.exists(ZUSTAND):
        start = json.load(open(ZUSTAND)).get("start_ms")
    if start is None or "--start-jetzt" in argv:
        start = ks[-1]
        json.dump({"start_ms": start}, open(ZUSTAND, "w"))
    ab = max(0, next((i for i, k in enumerate(ks) if k >= start), len(ks) - 1))
    eq, bh = verlauf(c, w, ab)
    zeit = lambda ms: time.strftime("%Y-%m-%d %H:%M", time.localtime(ms / 1000))
    os.makedirs(os.path.dirname(BERICHT), exist_ok=True)
    text = ("Schattenbuch Ensemble-Donchian H2 (BTC-USDC 4H, Kosten 0,07 %% je Seite)\n"
            "Start: %s | letzte Kerze: %s | Kerzen seit Start: %d\n"
            "Strategie: %+.2f %% | Buy&Hold: %+.2f %% | Differenz: %+.2f %%-Pkt\n"
            "Gewicht jetzt: %.3f (0 = flat, 1 = voll)\n"
            % (zeit(ks[ab]), zeit(ks[-1]), len(ks) - 1 - ab, (eq - 1) * 100, (bh - 1) * 100, (eq - bh) * 100, w[-1]))
    open(BERICHT, "w", encoding="utf-8").write(text)
    print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

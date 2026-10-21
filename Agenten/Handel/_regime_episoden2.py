"""Reale unabhaengige Regime-Episoden: Einstiege gruppiert nach Regime-Lauf.

Ein Wechsel zwischen zwei Einstiegen ist nur dann eine Beobachtung, wenn
zwischen ihnen ZEIT vergeht - sonst sind zwei Einstiege im selben Regime-Lauf
eine Episode, nicht zwei.

Aufruf: python _regime_episoden2.py
"""
from __future__ import annotations

import csv
import json
import os
import statistics

HIER = os.path.dirname(os.path.abspath(__file__))
DATEN = os.environ.get("REGIME_DATEN") or os.path.join(HIER, "daten")
HISTORIE = os.path.join(DATEN, "historie")
LAUF = "regime_studie"
GEBUEHR_PCT = 0.1
ABDECKUNG = 0.80
SUCH_ANTEIL = 0.60
SPUREN = ["squeeze", "wavetrend", "macd_mtf", "supertrend"]
BLOCK_MS = 12 * 3600 * 1000        # 12 Stunden = Mindestabstand je Episode


def ts(iso):
    from datetime import datetime
    try:
        return int(datetime.fromisoformat(iso).timestamp() * 1000)
    except (TypeError, ValueError):
        return 0


def symbol(inst):
    for alt in ("-USDC", "-USDT"):
        if inst.endswith(alt):
            return inst[: -len(alt)] + "USDT"
    return inst + "USDT"


def runden(zeilen):
    offen, raus = {}, []
    for r in zeilen:
        a = (r.get("aktion") or "").strip().lower()
        if a not in ("kauf", "verkauf"):
            continue
        pid = (r.get("pos_id") or "").strip()
        preis = float(r.get("preis") or 0.0)
        if a == "kauf":
            if pid and preis:
                offen[pid] = (r.get("inst"), r.get("seite"), ts(r.get("zeit")), preis)
        elif pid in offen:
            inst, seite, t, ein = offen.pop(pid)
            if ein and preis:
                vz = -1.0 if (seite or "").lower() == "short" else 1.0
                raus.append((inst, seite, t,
                             (preis / ein - 1.0) * 100.0 * vz - 2 * GEBUEHR_PCT))
    return raus


def lade_historie(name):
    p = os.path.join(HISTORIE, "%s_1H.json" % name)
    if not os.path.isfile(p):
        return []
    with open(p, encoding="utf-8") as f:
        return sorted(json.load(f), key=lambda k: k[0])


def idx_bis(reihe, t):
    lo, hi, letzter = 0, len(reihe) - 1, -1
    while lo <= hi:
        m = (lo + hi) // 2
        if reihe[m][0] <= t:
            letzter, lo = m, m + 1
        else:
            hi = m - 1
    return letzter


def sma200(reihe, t):
    i = idx_bis(reihe, t)
    return sum(k[4] for k in reihe[i - 199:i + 1]) / 200.0 if i >= 199 else None


def atr14(reihe, t):
    i = idx_bis(reihe, t)
    if i < 14:
        return None
    f = reihe[i - 13:i + 1]
    vorher, trs = f[0][4], []
    for k in f[1:]:
        h, l, c = k[2], k[3], k[4]
        trs.append(max(h - l, abs(h - vorher), abs(l - vorher)))
        vorher = c
    return (sum(trs) / len(trs)) / f[-1][4] if f[-1][4] else None


def main():
    reihen = {}
    for name in os.listdir(HISTORIE):
        if name.endswith("_1H.json"):
            reihen[name[:-len("_1H.json")]] = lade_historie(name[:-len("_1H.json")])

    print("Regime-Episoden, gezaehlt als ZEITLICHE Laufe (Block >= %.0f h)\n"
          % (BLOCK_MS / 3600000))
    print("%-10s %-12s %8s %8s %8s %9s %9s" %
          ("spur", "merkmal", "laeufe", "wechsel", "runden", "r/lauf", "r/block"))
    for spur in SPUREN:
        p = os.path.join(DATEN, "backtest", spur, LAUF, "handelsjournal.csv")
        rr = runden(list(csv.DictReader(open(p, encoding="utf-8", newline=""))))
        ts_sort = sorted(x[2] for x in rr)
        min_ts, max_ts = ts_sort[0], ts_sort[-1]
        grenze = int(min_ts + (max_ts - min_ts) * SUCH_ANTEIL)
        spanne = max_ts - min_ts
        uni = {n: r for n, r in reihen.items()
               if r and spanne and (r[-1][0] - r[0][0]) / spanne >= ABDECKUNG}

        merk = {}
        for inst, _s, t, _n in rr:
            if (inst, t) in merk:
                continue
            eigene = uni.get(symbol(inst), [])
            s = sma200(eigene, t) if eigene else None
            i = idx_bis(eigene, t)
            c = eigene[i][4] if i >= 0 and eigene else None
            ueber = gesamt = 0
            for sym, reihe in uni.items():
                ss = sma200(reihe, t)
                j = idx_bis(reihe, t)
                kk = reihe[j][4] if j >= 0 and reihe else None
                if ss is None or kk is None or not kk:
                    continue
                gesamt += 1
                if kk > ss:
                    ueber += 1
            merk[(inst, t)] = {"trend": bool(c and s and c > s),
                               "vol": atr14(eigene, t) if eigene else None,
                               "breite": (ueber / gesamt) if gesamt else None}
        such_r = [m for (i, t), m in merk.items() if min_ts <= t <= grenze]
        vol_m = statistics.median([m["vol"] for m in such_r if m["vol"]]) if such_r else 0.0
        br_m = statistics.median([m["breite"] for m in such_r
                                  if m["breite"] is not None]) if such_r else 1.0

        sortiert = sorted(merk.items(), key=lambda kv: kv[0][1])
        for name, z in (("trend_200", "trend"), ("vol_hoch", "vol"), ("breite_hoch", "breite")):
            if z == "vol":
                vals = [1 if (m["vol"] is not None and m["vol"] >= vol_m) else 0 for _, m in sortiert]
            elif z == "breite":
                vals = [1 if (m["breite"] is not None and m["breite"] >= br_m) else 0
                        for _, m in sortiert]
            else:
                vals = [1 if m["trend"] else 0 for _, m in sortiert]
            zeiten = [t for (_, t), _ in sortiert]
            # Laeufe: Wechsel, der zusaetzlich BLOCK_MS Zeit zum vorherigen
            # Einstieg hat (kein Schwund durch zwei Einstiege in derselben Phase)
            laeufe, wechsel, letzter_lauf = 1, 0, zeiten[0]
            for v, t in zip(vals[1:], zeiten[1:]):
                if v != vals[0] if False else False:
                    pass
            vorher = vals[0]
            for v, t in zip(vals[1:], zeiten[1:]):
                if v != vorher and (t - letzter_lauf) >= BLOCK_MS:
                    wechsel += 1
                    letzter_lauf = t
                vorher = v
            laeufe = wechsel + 1
            netto = [n for _i, _s, _t, n in rr]
            print("%-10s %-12s %8d %8d %8d %9.2f %9.2f" %
                  (spur, name, laeufe, wechsel, len(rr),
                   sum(netto) / laeufe,
                   sum(netto) / (len(rr) and (max_ts - min_ts) / BLOCK_MS)))


if __name__ == "__main__":
    main()

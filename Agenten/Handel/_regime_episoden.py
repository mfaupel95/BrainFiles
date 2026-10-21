"""Zaehlt Regime-Episoden und Regime-Wechsel in den vier Spuren (T-101 Satz 5).

Liegt nur - kein Parameter wird angepasst. Frage: wie viele UNABHAENGIGE
Beobachtungen hat jeder Regimefilter wirklich? Die Antwort ist die Zahl der
Wechsel, nicht die Zahl der Runden.

Aufruf: python _regime_episoden.py
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


def lade_journal(spur):
    p = os.path.join(DATEN, "backtest", spur, LAUF, "handelsjournal.csv")
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


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
                roh = (preis / ein - 1.0) * 100.0 * vz
                raus.append((inst, seite, t, roh - 2 * GEBUEHR_PCT))
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
    if i < 199:
        return None
    return sum(k[4] for k in reihe[i - 199:i + 1]) / 200.0


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
    if os.path.isdir(HISTORIE):
        for name in os.listdir(HISTORIE):
            if name.endswith("_1H.json"):
                reihen[name[:-len("_1H.json")]] = lade_historie(name[:-len("_1H.json")])
    print("Historien geladen: %d Reihen\n" % len(reihen))

    for spur in SPUREN:
        p = os.path.join(DATEN, "backtest", spur, LAUF, "handelsjournal.csv")
        if not os.path.isfile(p):
            print("== %s: Journal fehlt" % spur)
            continue
        rr = runden(lade_journal(spur))
        if not rr:
            print("== %s: keine Runden" % spur)
            continue
        ts_sort = sorted(x[2] for x in rr)
        min_ts, max_ts = ts_sort[0], ts_sort[-1]
        grenze = int(min_ts + (max_ts - min_ts) * SUCH_ANTEIL)
        spanne = max_ts - min_ts
        uni = {n: r for n, r in reihen.items()
               if r and spanne and (r[-1][0] - r[0][0]) / spanne >= ABDECKUNG}

        # Merkmale je Einstieg
        merk = {}
        for inst, _seite, t, _net in rr:
            key = (inst, t)
            if key in merk:
                continue
            eigene = uni.get(symbol(inst), [])
            s = sma200(eigene, t) if eigene else None
            c = eigene[idx_bis(eigene, t)][4] if eigene and idx_bis(eigene, t) >= 0 else None
            ueber = gesamt = 0
            for sym, reihe in uni.items():
                ss = sma200(reihe, t)
                i = idx_bis(reihe, t)
                kk = reihe[i][4] if i >= 0 and reihe else None
                if ss is None or kk is None or not kk:
                    continue
                gesamt += 1
                if kk > ss:
                    ueber += 1
            merk[key] = {"trend": bool(c and s and c > s),
                         "vol": atr14(eigene, t) if eigene else None,
                         "breite": (ueber / gesamt) if gesamt else None}
        such_r = [m for (i, t), m in merk.items() if min_ts <= t <= grenze]
        vol_m = statistics.median([m["vol"] for m in such_r if m["vol"]]) if such_r else 0.0
        br_m = statistics.median([m["breite"] for m in such_r
                                  if m["breite"] is not None]) if such_r else 1.0

        print("== %s: %d Runden, %d Historien-Reihen, Grenze %s"
              % (spur, len(rr), len(uni),
                 __import__("datetime").datetime.fromtimestamp(grenze / 1000,
                                                               __import__("datetime").timezone.utc).date()))
        for name, z in (("trend_200", "trend"), ("vol_hoch", "vol"), ("breite_hoch", "breite")):
            if z == "vol":
                vals = [1 if (m["vol"] is not None and m["vol"] >= vol_m) else 0 for m in merk.values()]
            elif z == "breite":
                vals = [1 if (m["breite"] is not None and m["breite"] >= br_m) else 0
                        for m in merk.values()]
            else:
                vals = [1 if m["trend"] else 0 for m in merk.values()]
            n = len(vals)
            wechsel = sum(1 for a, b in zip(vals, vals[1:]) if a != b)
            # Episoden = Wechsel + 1
            episoden = wechsel + 1
            # Wechsel nur INNERHALB der Prueffensster-Zeit (wo der Filter frei ist)
            pr = [1 for (i, t) in merk if t > grenze]
            print("   %-12s: n=%d Einstiege, Wechsel gesamt=%d (Episoden %d), "
                  "Wechsel je 1000 Einstiege=%.1f, Anteil gut=%.1f%%"
                  % (name, n, wechsel, episoden, 1000.0 * wechsel / n,
                     100.0 * sum(vals) / n))
        print()


if __name__ == "__main__":
    main()

"""Studie: Gewinnsicherung (Trailing erst im Plus) und Short-Verluste.

AUFTRAG (Max, 09.10.2026):
 1. Der Trailing-Stop soll NUR greifen, wenn die Position ins Plus laeuft, und
    dann verhindern, dass trotz positiver Strecke bei Breakeven oder im Verlust
    ausgestoppt wird. Der Abstand soll sich je Coin nach Volatilitaet und
    Marktrauschen richten.
 2. Die Short-Verluste (PR #15: Kontrolle Long +196 R, Short -141 R) untersuchen.

Aufbau wie fib_backtest/trailing_backtest: gleiche Einstiege der Klassik-
Trendspuren, fester %-Stop der Spur, KEIN festes Ziel (PR #16), Regelausstieg
bleibt, Ergebnis netto in R des urspruenglichen Stops, Gebuehr je Seite, Stop
vor Ziel/Regel im selben Balken, Stop gilt ab der naechsten Kerze.

GEWINNSICHERUNG (Arme):
  atr:      scharf, sobald der SCHLUSS `trigger_r` Vielfache des Start-Stops im
            Plus liegt. Danach Stop = Hochstand -/+ k x ATR(14), nie schlechter
            als Einstand + Gebuehren (= netto mindestens +-0), nie zurueck.
  giveback: scharf wie oben. Danach Stop = Einstand + f x (bisheriger
            Hoechstgewinn), mindestens Einstand + Gebuehren. Der Stop haelt
            also immer den Bruchteil f des erreichten Gewinns fest.
  Kontrolle: kein Trailing.   Breakeven: nur der Boden (Einstand + Gebuehren)
            nach `trigger_r`, ohne Nachfuehrung.

REGIME (Short-Analyse): Bullenmarkt, wenn der Schluss ueber dem Durchschnitt der
letzten 1200 Kerzen liegt (4H: rund 200 Tage), sonst Baerenmarkt. Gemessen am
Einstiegsbalken, ohne Blick nach vorn.

Aufruf (je Spur ein Prozess; danach auswerten):
    python ausstieg_studie.py --spuren klassik_ema --aus daten/studie/ema.json
    python ausstieg_studie.py --auswerten daten/studie/*.json
"""

from __future__ import annotations

import argparse
import datetime
import glob
import importlib.util
import itertools
import json
import sys
from collections import defaultdict
from pathlib import Path

HANDEL = Path(__file__).resolve().parent


def _lade(pfad, name):
    spec = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


fb = _lade(HANDEL / "fib_backtest.py", "studie_fb")
kr = fb.kr
REGIME_N = 1200          # 4H-Kerzen, rund 200 Tage


# --- Hilfsreihen -------------------------------------------------------------

def atr_reihe(k, n=14):
    """Wilder-ATR je Kerze (None, solange n Kerzen fehlen). Nur Vergangenheit."""
    out = [None] * len(k)
    tr_summe, atr = 0.0, None
    for j in range(len(k)):
        h, l = float(k[j][2]), float(k[j][3])
        pc = float(k[j - 1][4]) if j else float(k[j][4])
        tr = max(h - l, abs(h - pc), abs(l - pc))
        if j < n:
            tr_summe += tr
            if j == n - 1:
                atr = tr_summe / n
                out[j] = atr
        else:
            atr = (atr * (n - 1) + tr) / n
            out[j] = atr
    return out


def regime_reihe(k, n=REGIME_N):
    """True = Bullenmarkt (Schluss ueber dem n-Kerzen-Schnitt), None = noch unbekannt."""
    out = [None] * len(k)
    s = 0.0
    for j in range(len(k)):
        s += float(k[j][4])
        if j >= n:
            s -= float(k[j - n][4])
        if j >= n - 1:
            out[j] = float(k[j][4]) > s / n
    return out


def halbjahr(ts_ms):
    d = datetime.datetime.fromtimestamp(ts_ms / 1000, datetime.timezone.utc)
    return "%d-H%d" % (d.year, 1 if d.month <= 6 else 2)


# --- Simulation --------------------------------------------------------------

def laufe(k, i, seite, einstieg, stop, regel_aus, gebuehr, stop_frac, atr,
          modus=None, trigger_r=1.0, param=None):
    """Eine Position ab Kerze i+1; fester Start-Stop, kein Ziel.

    modus None: Kontrolle. "boden": nach trigger_r Stop auf Einstand+Gebuehren.
    "atr": param = k (ATR-Vielfache). "giveback": param = f (Bruchteil).
    """
    n = len(k)
    vz = 1.0 if seite == "long" else -1.0
    abstand0 = abs(einstieg - stop)
    boden = einstieg * (1.0 + vz * 2.0 * gebuehr)       # netto +-0 nach beiden Gebuehren
    hoch = einstieg
    scharf = False
    start = stop
    mfe = [0.0]                                  # hoechster Schluss-Gewinn in R (nur Messung)

    def _e(*a):
        t = fb._ergebnis(*a)
        t["mfe_r"] = mfe[0]
        return t

    for j in range(i + 1, n):
        o, h, l, c = k[j][1], k[j][2], k[j][3], k[j][4]
        if seite == "long":
            if l <= stop:
                return _e(seite, einstieg, min(o, stop), gebuehr, stop_frac,
                          "sicherung" if stop != start else "stop", j - i)
        else:
            if h >= stop:
                return _e(seite, einstieg, max(o, stop), gebuehr, stop_frac,
                          "sicherung" if stop != start else "stop", j - i)
        g = regel_aus(j, seite)
        mfe[0] = max(mfe[0], (c - einstieg) * vz / abstand0)
        if g:
            return _e(seite, einstieg, c, gebuehr, stop_frac, g, j - i)
        if modus is None:
            continue
        hoch = max(hoch, h) if vz > 0 else min(hoch, l)
        if not scharf and (c - einstieg) * vz / abstand0 >= trigger_r:
            scharf = True
        if not scharf:
            continue
        if modus == "boden":
            neu = boden
        elif modus == "atr":
            a = atr[j]
            neu = boden if a is None else hoch - vz * param * a
        else:                                           # giveback
            neu = einstieg + vz * param * abs(hoch - einstieg)
        neu = max(neu, boden) if vz > 0 else min(neu, boden)       # nie schlechter als der Boden
        neu = min(neu, c * (1 - 1e-6)) if vz > 0 else max(neu, c * (1 + 1e-6))
        if (neu > stop) if vz > 0 else (neu < stop):
            stop = neu
    return _e(seite, einstieg, k[-1][4], gebuehr, stop_frac, "ende", n - 1 - i)


def _e(seite, einstieg, ausstieg, gebuehr, stop_frac, grund, bars):
    return fb._ergebnis(seite, einstieg, ausstieg, gebuehr, stop_frac, grund, bars)


def simuliere(k, sigs, sp, regel_aus, gebuehr, atr, **kw):
    trades, frei_ab = [], 0
    for i, seite in sigs:
        if i < frei_ab:
            continue
        kurs = k[i][4]
        d = kurs * sp
        stop = kurs - d if seite == "long" else kurs + d
        t = laufe(k, i, seite, kurs, stop, regel_aus, gebuehr, sp, atr, **kw)
        t.update(i=i, seite=seite)
        trades.append(t)
        frei_ab = i + t["bars"] + 1
    return trades


ARME = [("Kontrolle (kein Trailing)", dict(modus=None))]
for tr in (1.0, 1.5, 2.0):
    ARME.append(("Boden nach %.1fR" % tr, dict(modus="boden", trigger_r=tr)))
    for kk in (2.0, 3.0, 4.0, 6.0):
        ARME.append(("ATR-Trail trig %.1fR k=%.0f" % (tr, kk), dict(modus="atr", trigger_r=tr, param=kk)))
    for f in (0.25, 0.5):
        ARME.append(("Giveback trig %.1fR halte %.0f%%" % (tr, f * 100), dict(modus="giveback", trigger_r=tr, param=f)))


# --- Lauf je Spur -------------------------------------------------------------

def lauf(a):
    out = {"zellen": {}}
    insts = [x for x in a.instrumente.split(",") if x]
    for spur in [s for s in a.spuren.split(",") if s]:
        ef, af = kr.REGELN[spur]
        w = json.loads((HANDEL / spur / "wachen.json").read_text(encoding="utf-8"))
        bar = w.get("kerzen_zeitrahmen", "4H")
        sp = float(w["stop_prozent"]) / 100.0
        gb = float(w.get("gebuehr_taker", 0.0005))
        kn = int(w.get("kerzen_anzahl", 400))
        for inst in insts:
            k = fb.lade_kerzen(inst, bar, a.anzahl, a.cache)
            if len(k) < 1500:
                print("%s %s: nur %d Kerzen - uebersprungen" % (spur, inst, len(k)), flush=True)
                continue
            atr = atr_reihe(k)
            reg = regime_reihe(k)
            memo = {}

            def regel_aus(j, seite, k=k, w=w, kn=kn, fn=af, memo=memo):
                key = (j, seite)
                if key not in memo:
                    memo[key] = fn(k[max(0, j - kn + 1): j + 1], seite, w)
                return memo[key]

            sigs = fb.signale(k, ef, w)
            if a.nur_long:                       # wie nur_long in klassik_regeln.bauen()
                sigs = [x for x in sigs if x[1] == "long"]
            for name, kw in ARME:
                for t in simuliere(k, sigs, sp, regel_aus, gb, atr, **kw):
                    r_ = reg[t["i"]]
                    key = "|".join((name, spur, inst, t["seite"],
                                    "bull" if r_ else ("bear" if r_ is False else "?"),
                                    halbjahr(k[t["i"]][0])))
                    z = out["zellen"].setdefault(key, [0, 0.0])
                    z[0] += 1
                    z[1] += t["r"]
            # Marktdrift je Halbjahr fuer die Short-Analyse (einmal je Instrument)
            drift = {}
            for j in range(len(k)):
                drift.setdefault(halbjahr(k[j][0]), [k[j][4], k[j][4]])[1] = k[j][4]
            out.setdefault("drift", {})[inst] = {p: (v[1] / v[0] - 1.0) * 100.0 for p, v in drift.items()}
            print("%s %s fertig (%d Signale, %d Kerzen)" % (spur, inst, len(sigs), len(k)), flush=True)
    Path(a.aus).parent.mkdir(parents=True, exist_ok=True)
    Path(a.aus).write_text(json.dumps(out))


# --- Zaehlung: "erst im Plus, dann bei +-0 oder im Verlust" -------------------

def zaehlen(a):
    arme = [x for x in ARME if x[0] in ("Kontrolle (kein Trailing)", "Boden nach 1.0R",
                                        "Boden nach 1.5R", "Boden nach 2.0R")]
    ges = defaultdict(lambda: defaultdict(float))
    for spur in [s_ for s_ in a.spuren.split(",") if s_]:
        ef, af = kr.REGELN[spur]
        w = json.loads((HANDEL / spur / "wachen.json").read_text(encoding="utf-8"))
        sp = float(w["stop_prozent"]) / 100.0
        gb = float(w.get("gebuehr_taker", 0.0005))
        kn = int(w.get("kerzen_anzahl", 400))
        for inst in [x for x in a.instrumente.split(",") if x]:
            k = fb.lade_kerzen(inst, w.get("kerzen_zeitrahmen", "4H"), a.anzahl, a.cache)
            if len(k) < 1500:
                continue
            atr = atr_reihe(k)
            memo = {}

            def regel_aus(j, seite, k=k, w=w, kn=kn, fn=af, memo=memo):
                key = (j, seite)
                if key not in memo:
                    memo[key] = fn(k[max(0, j - kn + 1): j + 1], seite, w)
                return memo[key]

            sigs = fb.signale(k, ef, w)
            for name, kw in arme:
                for t in simuliere(k, sigs, sp, regel_aus, gb, atr, **kw):
                    z = ges[(name, t["seite"])]
                    z["n"] += 1
                    z["summe"] += t["r"]
                    if t["mfe_r"] >= 1.0:
                        z["plus"] += 1
                        if t["r"] <= 0.0:
                            z["plus_dann_minus"] += 1
                            z["verlust_r"] += t["r"]
                        elif t["r"] < 0.5:
                            z["plus_dann_fast_null"] += 1
            print("%s %s gezaehlt" % (spur, inst), flush=True)
    Path(a.aus).parent.mkdir(parents=True, exist_ok=True)
    Path(a.aus).write_text(json.dumps({"%s|%s" % k_: dict(v) for k_, v in ges.items()}))


def zaehlen_auswerten(dateien):
    ges = defaultdict(lambda: defaultdict(float))
    for f in dateien:
        for key, v in json.loads(Path(f).read_text()).items():
            for kk, vv in v.items():
                ges[key][kk] += vv
    print("%-22s %-6s %6s %8s %12s %18s %10s" % ("Arm", "Seite", "n", "im Plus", "dann <=0 R", "dann 0..0,5 R", "Summe R"))
    for name in ("Kontrolle (kein Trailing)", "Boden nach 1.0R", "Boden nach 1.5R", "Boden nach 2.0R"):
        for seite in ("long", "short"):
            z = ges.get("%s|%s" % (name, seite))
            if not z:
                continue
            print("%-22s %-6s %6d %8d %5d (%4.1f%%) %9d (%4.1f%%) %+10.1f" % (
                name, seite, z["n"], z["plus"], z["plus_dann_minus"],
                100.0 * z["plus_dann_minus"] / max(z["plus"], 1),
                z["plus_dann_fast_null"], 100.0 * z["plus_dann_fast_null"] / max(z["plus"], 1), z["summe"]))


# --- Auswertung ---------------------------------------------------------------

def auswerten(dateien):
    zellen = defaultdict(lambda: [0, 0.0])
    drift = {}
    for f in dateien:
        d = json.loads(Path(f).read_text())
        for key, (n, s) in d["zellen"].items():
            z = zellen[key]
            z[0] += n
            z[1] += s
        for inst, v in d.get("drift", {}).items():
            drift[inst] = v
    zeilen = [(key.split("|"), n, s) for key, (n, s) in zellen.items()]

    def summe(filt):
        n = sum(n for k_, n, s in zeilen if filt(k_))
        s = sum(s for k_, n, s in zeilen if filt(k_))
        return n, s

    namen = [n for n, _ in ARME]
    print("== A) Gewinnsicherung: alle Spuren/Instrumente, gesamte Historie (netto R)")
    print("%-34s %6s %8s %8s %8s %8s %8s" % ("Arm", "n", "Summe R", "E/Trade", "Long", "Short", "2022 bis"))
    ergeb = []
    for name in namen:
        n, s = summe(lambda k_: k_[0] == name)
        _, lg = summe(lambda k_: k_[0] == name and k_[3] == "long")
        _, sh = summe(lambda k_: k_[0] == name and k_[3] == "short")
        _, frueh = summe(lambda k_: k_[0] == name and k_[5] <= "2022-H2")
        ergeb.append((name, n, s, lg, sh, frueh))
    for name, n, s, lg, sh, frueh in sorted(ergeb, key=lambda x: -x[2]):
        print("%-34s %6d %+8.1f %+8.3f %+8.1f %+8.1f %+8.1f" % (name, n, s, s / max(n, 1), lg, sh, frueh))

    print("\n== A2) Stabilitaet: Halbjahre mit positiver Summe (von allen mit Trades)")
    perioden = sorted({k_[5] for k_, n, s in zeilen})
    for name in namen:
        pos = sum(1 for p in perioden if summe(lambda k_: k_[0] == name and k_[5] == p)[1] > 0)
        print("  %-34s %d von %d" % (name, pos, len(perioden)))

    ko = namen[0]
    print("\n== B) Short-Analyse, Kontrolle (fester Stop, kein Ziel, Regelausstieg)")
    print("%-22s %6s %8s %8s" % ("Regime x Seite", "n", "Summe R", "E/Trade"))
    for reg in ("bull", "bear"):
        for seite in ("long", "short"):
            n, s = summe(lambda k_: k_[0] == ko and k_[4] == reg and k_[3] == seite)
            print("%-22s %6d %+8.1f %+8.3f" % (reg + " / " + seite, n, s, s / max(n, 1)))
    print("\n   je Spur (Short, Bullen- / Baerenmarkt):")
    spuren = sorted({k_[1] for k_, n, s in zeilen})
    for sp_ in spuren:
        nb, sb = summe(lambda k_: k_[0] == ko and k_[1] == sp_ and k_[3] == "short" and k_[4] == "bull")
        nr, sr = summe(lambda k_: k_[0] == ko and k_[1] == sp_ and k_[3] == "short" and k_[4] == "bear")
        print("   %-26s bull n=%4d %+7.1f R | bear n=%4d %+7.1f R" % (sp_, nb, sb, nr, sr))
    print("\n   je Instrument (Short, Bullen- / Baerenmarkt):")
    for inst in sorted({k_[2] for k_, n, s in zeilen}):
        nb, sb = summe(lambda k_: k_[0] == ko and k_[2] == inst and k_[3] == "short" and k_[4] == "bull")
        nr, sr = summe(lambda k_: k_[0] == ko and k_[2] == inst and k_[3] == "short" and k_[4] == "bear")
        print("   %-18s bull n=%4d %+7.1f R | bear n=%4d %+7.1f R" % (inst, nb, sb, nr, sr))
    print("\n   Halbjahre: Long / Short (Summe R) und BTC-Kursaenderung:")
    btc = drift.get("BTC-USDT-SWAP", {})
    for p in perioden:
        _, l_ = summe(lambda k_: k_[0] == ko and k_[5] == p and k_[3] == "long")
        _, s_ = summe(lambda k_: k_[0] == ko and k_[5] == p and k_[3] == "short")
        print("   %s  Long %+7.1f | Short %+7.1f | BTC %+6.1f %%" % (p, l_, s_, btc.get(p, float("nan"))))

    print("\n== C) Beste Arme nach Seite und Regime (Summe R)")
    for name, *_ in sorted(ergeb, key=lambda x: -x[2])[:6] + [e for e in ergeb if e[0] == ko]:
        zl = []
        for reg in ("bull", "bear"):
            for seite in ("long", "short"):
                zl.append("%s/%s %+6.1f" % (reg, seite, summe(lambda k_: k_[0] == name and k_[4] == reg and k_[3] == seite)[1]))
        print("  %-34s %s" % (name, " | ".join(zl)))
    return ergeb


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--spuren", default="klassik_ema,klassik_sma,klassik_macd,klassik_donchian_trend,klassik_supertrend")
    ap.add_argument("--instrumente", default="BTC-USDT-SWAP,ETH-USDT-SWAP,SOL-USDT-SWAP,XAU-USDT-SWAP")
    ap.add_argument("--anzahl", type=int, default=22000)
    ap.add_argument("--cache", default=str(HANDEL / "daten" / "fib_bt"))
    ap.add_argument("--aus", default=str(HANDEL / "daten" / "studie" / "ergebnis.json"))
    ap.add_argument("--auswerten", nargs="+")
    ap.add_argument("--nur-long", action="store_true", help="Short-Signale verwerfen (wie nur_long in den Wachen)")
    ap.add_argument("--zaehlen", action="store_true", help="Plus-dann-Verlust-Zaehlung statt voller Studie")
    ap.add_argument("--zaehl-auswerten", nargs="+")
    a = ap.parse_args(argv)
    if a.zaehl_auswerten:
        return zaehlen_auswerten([f for p in a.zaehl_auswerten for f in glob.glob(p)])
    if a.zaehlen:
        return zaehlen(a)
    if a.auswerten:
        dateien = [f for p in a.auswerten for f in glob.glob(p)]
        return auswerten(dateien)
    return lauf(a)


if __name__ == "__main__":
    main()

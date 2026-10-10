"""Studie: Funding, Slippage und Korrelation der Trend-Klassikspuren (Long-only).

AUFTRAG (Max, 09.10.2026): nach der Long-only-Umstellung (PR #18) pruefen, was
die bisherigen Backtests NICHT enthielten - Funding und Slippage - und wie
stark die Spuren untereinander korrelieren.

Grundlage: die Handelsliste der fuenf Spuren (ema, sma, macd, donchian_trend,
supertrend), Long-only, fester %-Stop, kein Ziel, Regelausstieg (so konfiguriert
nach PR #16/#18), BTC/ETH/SOL (+XAU) auf 4H, Dez. 2019 bis Okt. 2026, netto in R
des Start-Stops, Gebuehr 0,05 % je Seite wie bisher.

FUNDING
  Long zahlt den positiven Satz je Abrechnungszeitpunkt. R-Kosten eines Trades:
  (Summe der Saetze im Halteintervall) / Stop-Anteil. Eine lange Funding-
  Historie gibt es von hier NICHT (OKX/Bitget ~3 Monate, Binance 451, Bybit 403).
  Gemessen wird deshalb mit Hyperliquid (stuendlich, ab 2023-05) als Proxy,
  validiert gegen die echten OKX-Saetze der letzten Monate; vor 2023 gilt nur die
  Break-even-Rechnung: welches Funding p.a. verkraftet die Strategie?

SLIPPAGE
  Aus dem echten OKX-Orderbuch (Spread + Marktauswirkung fuer die Ordergroesse),
  Momentaufnahme. Szenarien in Basispunkten je Seite; Stop-Ausstiege (Marktorder
  im schnellen Markt) mit Aufschlag.

KORRELATION
  Kursrenditen (4H, auch im Stress), und - wichtiger - die Korrelation der
  HANDELSERGEBNISSE (Wochen-R) zwischen Instrumenten und Spuren, effektive Zahl
  unabhaengiger Wetten, gleichzeitig offene Positionen, schlechteste Cluster.

Aufruf:
    python kosten_korrelation.py handel --spur klassik_ema --aus <datei>   (je Spur)
    python kosten_korrelation.py analyse --handel "<dir>/*.json"
"""

from __future__ import annotations

import argparse
import datetime
import glob
import importlib.util
import json
import math
import ssl
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

HANDEL = Path(__file__).resolve().parent
SPUREN = ["klassik_ema", "klassik_sma", "klassik_macd", "klassik_donchian_trend", "klassik_supertrend"]
INSTS = ["BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP", "XAU-USDT-SWAP"]
BAR_MS = 4 * 3600 * 1000
JAHR_STUNDEN = 8760.0


def _lade(pfad, name):
    spec = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


st = _lade(HANDEL / "ausstieg_studie.py", "kk_studie")
fb = st.fb
kr = st.kr


# --- Netz -------------------------------------------------------------------

def _http(url, daten=None):
    ctx = ssl.create_default_context(cafile="/root/.ccr/ca-bundle.crt") \
        if Path("/root/.ccr/ca-bundle.crt").exists() else ssl.create_default_context()
    for versuch in range(4):
        try:
            rq = urllib.request.Request(url, data=daten, headers={
                "User-Agent": "kosten_korrelation/1.0", "Content-Type": "application/json"})
            with urllib.request.urlopen(rq, timeout=25, context=ctx) as r:
                return json.loads(r.read())
        except Exception:                                          # noqa: BLE001
            time.sleep(2 ** versuch)
    raise RuntimeError("Abruf scheitert: " + url)


# --- 1) Handelsliste --------------------------------------------------------

def handel(a):
    out = []
    ef, af = kr.REGELN[a.spur]
    w = json.loads((HANDEL / a.spur / "wachen.json").read_text(encoding="utf-8"))
    sp = float(w["stop_prozent"]) / 100.0
    gb = float(w.get("gebuehr_taker", 0.0005))
    kn = int(w.get("kerzen_anzahl", 400))
    for inst in INSTS:
        k = fb.lade_kerzen(inst, w.get("kerzen_zeitrahmen", "4H"), a.anzahl, a.cache)
        if len(k) < 1500:
            continue
        memo = {}

        def regel_aus(j, seite, k=k, w=w, kn=kn, fn=af, memo=memo):
            key = (j, seite)
            if key not in memo:
                memo[key] = fn(k[max(0, j - kn + 1): j + 1], seite, w)
            return memo[key]

        sigs = [x for x in fb.signale(k, ef, w) if x[1] == "long"]          # nur_long
        for t in st.simuliere(k, sigs, sp, regel_aus, gb, st.atr_reihe(k), modus=None):
            ein = k[t["i"]][0] + BAR_MS
            # Stop-Ausstieg liegt irgendwo im Balken (Mitte), Regel/Ende am Schluss
            aus = k[t["i"] + t["bars"]][0] + (BAR_MS // 2 if t["grund"] == "stop" else BAR_MS)
            out.append({"spur": a.spur, "inst": inst, "ts_in": ein, "ts_out": aus,
                        "r": t["r"], "grund": t["grund"], "sp": sp, "gb": gb})
        print("%s %s: %d Trades" % (a.spur, inst, sum(1 for o in out if o["inst"] == inst)), flush=True)
    Path(a.aus).parent.mkdir(parents=True, exist_ok=True)
    Path(a.aus).write_text(json.dumps(out))


# --- 2) Funding -------------------------------------------------------------

def hl_funding(coin, start_ms, cache):
    """Stuendliche Hyperliquid-Saetze (Rate je Stunde), aufsteigend, mit Cache."""
    pfad = Path(cache) / ("hl_%s.json" % coin)
    if pfad.exists():
        return [tuple(x) for x in json.loads(pfad.read_text())]
    reihe, t = [], start_ms
    while True:
        d = _http("https://api.hyperliquid.xyz/info",
                  json.dumps({"type": "fundingHistory", "coin": coin, "startTime": t}).encode())
        if not d:
            break
        reihe += [(int(x["time"]), float(x["fundingRate"])) for x in d]
        if len(d) < 500:
            break
        t = int(d[-1]["time"]) + 1
        time.sleep(0.15)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps(reihe))
    return reihe


def okx_funding(inst, cache):
    """Echte OKX-Saetze (8h), soweit die Boerse sie hergibt (~3 Monate)."""
    pfad = Path(cache) / ("okxf_%s.json" % inst)
    if pfad.exists():
        return [tuple(x) for x in json.loads(pfad.read_text())]
    reihe, after = [], None
    while True:
        u = "https://www.okx.com/api/v5/public/funding-rate-history?instId=%s&limit=100" % inst
        if after:
            u += "&after=%s" % after
        d = _http(u).get("data") or []
        if not d:
            break
        reihe += [(int(x["fundingTime"]), float(x.get("realizedRate") or x["fundingRate"])) for x in d]
        after = d[-1]["fundingTime"]
        time.sleep(0.15)
    reihe.sort()
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps(reihe))
    return reihe


def summe_saetze(reihe, von, bis):
    """Summe der Saetze mit von < Zeit <= bis (Reihe aufsteigend)."""
    import bisect
    zeiten = [z for z, _ in reihe]
    i, j = bisect.bisect_right(zeiten, von), bisect.bisect_right(zeiten, bis)
    return sum(r for _, r in reihe[i:j])


# --- 3) Orderbuch ------------------------------------------------------------

def orderbuch(inst, groessen_usd, proben=5):
    """Mittlere Kosten (bps gegen Mitte) eines Marktkaufs/-verkaufs je Ordergroesse."""
    ins = _http("https://www.okx.com/api/v5/public/instruments?instType=SWAP&instId=%s" % inst)["data"][0]
    ct = float(ins["ctVal"])
    kosten = defaultdict(list)
    halb = []
    for _ in range(proben):
        b = _http("https://www.okx.com/api/v5/market/books?instId=%s&sz=200" % inst)["data"][0]
        asks = [(float(p), float(s)) for p, s, *_ in b["asks"]]
        bids = [(float(p), float(s)) for p, s, *_ in b["bids"]]
        mitte = (asks[0][0] + bids[0][0]) / 2.0
        halb.append((asks[0][0] - bids[0][0]) / 2.0 / mitte * 1e4)
        for seite, buch in (("kauf", asks), ("verkauf", bids)):
            for usd in groessen_usd:
                rest, kost = usd / mitte / ct, 0.0                    # Kontrakte
                n = rest
                for p, s in buch:
                    nimm = min(rest, s)
                    kost += nimm * p
                    rest -= nimm
                    if rest <= 1e-12:
                        break
                if rest > 1e-9:
                    continue                                           # Buch zu flach
                vwap = kost / n
                kosten[(seite, usd)].append(abs(vwap - mitte) / mitte * 1e4)
        time.sleep(1.5)
    return {"halber_spread_bps": sum(halb) / len(halb),
            "kosten_bps": {"%s|%d" % k: sum(v) / len(v) for k, v in kosten.items()}}


# --- 4) Analyse ---------------------------------------------------------------

def jahr(ms):
    return datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc).year


def korr(x, y):
    n = len(x)
    if n < 3:
        return float("nan")
    mx, my = sum(x) / n, sum(y) / n
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return float("nan") if sx == 0 or sy == 0 else sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)


def wochen(ms):
    return int(ms // (7 * 86400 * 1000))


def analyse(a):
    trades = []
    for f in glob.glob(a.handel):
        trades += json.loads(Path(f).read_text())
    cache = a.cache
    print("Trades gesamt: %d  (Summe R %+.1f, E %+.3f)\n" % (
        len(trades), sum(t["r"] for t in trades), sum(t["r"] for t in trades) / len(trades)))
    print("== 0) VORTEIL JE JAHR (vor Funding, alle Spuren/Instrumente, nach Einstiegsjahr)")
    je_j = defaultdict(lambda: [0, 0.0])
    for t in trades:
        z = je_j[jahr(t["ts_in"])]
        z[0] += 1
        z[1] += t["r"]
    for j in sorted(je_j):
        print("   %d  n=%4d  Summe %+7.1f R  E %+.3f R/Trade" % (j, je_j[j][0], je_j[j][1], je_j[j][1] / je_j[j][0]))
    print()

    # ---- Funding ----
    print("== 1) FUNDING (Long zahlt positiven Satz)")
    hl = {i: hl_funding(c, 1672531200000, cache) for i, c in
          (("BTC-USDT-SWAP", "BTC"), ("ETH-USDT-SWAP", "ETH"), ("SOL-USDT-SWAP", "SOL"))}
    ok = {i: okx_funding(i, cache) for i in INSTS}
    # Proxy-Validierung: Tagessummen HL gegen OKX im gemeinsamen Zeitraum
    print("   Proxy-Pruefung Hyperliquid gegen echte OKX-Saetze (Tagessummen):")
    for inst in ("BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP"):
        o = ok[inst]
        if not o:
            continue
        tage = sorted({int(z // 86400000) for z, _ in o})
        x = [summe_saetze(o, t * 86400000 - 1, (t + 1) * 86400000 - 1) for t in tage]
        y = [summe_saetze(hl[inst], t * 86400000 - 1, (t + 1) * 86400000 - 1) for t in tage]
        print("   %-14s Tage %3d | OKX mittel %+.5f %%/Tag | HL mittel %+.5f %%/Tag | Korrelation %.2f" % (
            inst, len(tage), 100 * sum(x) / len(x), 100 * sum(y) / len(y), korr(x, y)))
    start_hl = 1683849600000                                   # 2023-05-12
    gedeckt = [t for t in trades if t["ts_in"] >= start_hl and t["inst"] in hl]
    if gedeckt:
        r0 = sum(t["r"] for t in gedeckt)
        kosten_r, anteile = 0.0, []
        je_jahr = defaultdict(lambda: [0, 0.0, 0.0])
        for t in gedeckt:
            f = summe_saetze(hl[t["inst"]], t["ts_in"], t["ts_out"])
            kr_ = f / t["sp"]
            kosten_r += kr_
            dauer_h = max((t["ts_out"] - t["ts_in"]) / 3600000.0, 1.0)
            anteile.append((f, dauer_h))
            z = je_jahr[jahr(t["ts_in"])]
            z[0] += 1
            z[1] += t["r"]
            z[2] += kr_
        ann = sum(f for f, _ in anteile) / sum(h for _, h in anteile) * JAHR_STUNDEN * 100
        print("\n   Gedeckte Trades (ab 2023-05): %d | Summe R vor Funding %+.1f | Funding-Kosten %+.1f R | danach %+.1f R" % (
            len(gedeckt), r0, kosten_r, r0 - kosten_r))
        print("   mittleres Funding waehrend der Haltezeit: %+.1f %% p.a. | pro Trade %+.4f R" % (ann, kosten_r / len(gedeckt)))
        print("   je Jahr:   Trades | R vor Funding | Funding-R | R nach Funding")
        for j in sorted(je_jahr):
            n_, r_, f_ = je_jahr[j]
            print("   %d      %6d | %+13.1f | %+9.1f | %+14.1f" % (j, n_, r_, f_, r_ - f_))
    # Break-even auf der GESAMTEN Historie (auch vor 2023)
    haltejahre_pro_stop = sum(((t["ts_out"] - t["ts_in"]) / 3600000.0 / JAHR_STUNDEN) / t["sp"] for t in trades)
    gesamt_r = sum(t["r"] for t in trades)
    be = gesamt_r / haltejahre_pro_stop * 100
    print("\n   Break-even ueber die GESAMTE Historie (2019-2026): die Strategie verkraftet im Mittel %.0f %% p.a. Funding" % be)
    print("   (Summe R %+.0f; bei jaehrlich f %% Funding sinkt sie um f/100 x %.0f R je 100 %%)" % (gesamt_r, haltejahre_pro_stop))
    for f in (5, 10, 20, 40, 80):
        print("      bei %2d %% p.a.: Summe R %+8.1f (E %+.3f je Trade)" % (
            f, gesamt_r - f / 100.0 * haltejahre_pro_stop, (gesamt_r - f / 100.0 * haltejahre_pro_stop) / len(trades)))
    mh = sum((t["ts_out"] - t["ts_in"]) / 3600000.0 for t in trades) / len(trades)
    print("   mittlere Haltedauer: %.0f Stunden (%.1f Tage)" % (mh, mh / 24))

    # ---- Slippage ----
    print("\n== 2) SLIPPAGE")
    groessen = (170, 350, 1000, 5000)
    for inst in INSTS:
        try:
            o = orderbuch(inst, groessen)
        except Exception as e:                                       # noqa: BLE001
            print("   %s: Orderbuch nicht lesbar (%s)" % (inst, e))
            continue
        print("   %-14s halber Spread %.2f bps | Kosten Marktkauf/-verkauf (bps gegen Mitte): %s" % (
            inst, o["halber_spread_bps"],
            "  ".join("%d USD: %.2f/%.2f" % (g, o["kosten_bps"].get("kauf|%d" % g, float("nan")),
                                                o["kosten_bps"].get("verkauf|%d" % g, float("nan")))
                      for g in groessen)))
    print("\n   Szenarien (bps je Seite; Stop-Ausstiege = 3-facher Wert), Summe R / E je Trade:")
    for s in (0, 1, 2, 5, 10, 20, 50):
        f = s / 1e4
        # je Trade: Einstieg f, Ausstieg f (Stop: 3f), jeweils geteilt durch den Stop-Anteil
        extra = sum((f + (3 * f if t["grund"] == "stop" else f)) / t["sp"] for t in trades)
        print("      %2d bps: Summe R %+8.1f | E %+.3f" % (s, gesamt_r - extra, (gesamt_r - extra) / len(trades)))
    s_be = gesamt_r / sum((1 + (3 if t["grund"] == "stop" else 1)) / t["sp"] for t in trades) * 1e4
    print("   Break-even-Slippage (Stop-Aufschlag 3x): %.0f bps je Seite" % s_be)

    # ---- Korrelation ----
    print("\n== 3) KORRELATION")
    k_ = {i: fb.lade_kerzen(i, "4H", 14000, a.kerzen) for i in INSTS}
    gem = {}
    for i, kk in k_.items():
        gem[i] = {x[0]: math.log(kk[j][4] / kk[j - 1][4]) for j, x in enumerate(kk) if j}
    print("   a) Kursrenditen 4H: Korrelation und Schwanz-Abhaengigkeit")
    print("      (Schwanz = P(B im schlechtesten 5 % | A im schlechtesten 5 %); bei Unabhaengigkeit 5 %.")
    print("       Eine Korrelation, die nur auf extreme Balken bedingt wird, ist verzerrt - sie schneidet die Streuung ab.)")
    namen = ["BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP", "XAU-USDT-SWAP"]
    for x_, y_ in ((0, 1), (0, 2), (1, 2), (0, 3), (2, 3)):
        a_, b_ = namen[x_], namen[y_]
        gz = sorted(z for z in gem[a_] if z in gem[b_])
        ra, rb = [gem[a_][z] for z in gz], [gem[b_][z] for z in gz]
        alle = korr(ra, rb)
        sa, sb = sorted(ra)[int(0.05 * len(ra))], sorted(rb)[int(0.05 * len(rb))]
        nenner = sum(1 for v in ra if v <= sa)
        schwanz = sum(1 for u, v in zip(ra, rb) if u <= sa and v <= sb) / max(nenner, 1)
        print("      %-4s ~ %-4s Korrelation %.2f | Schwanz-Abhaengigkeit %3.0f %% (n=%d)" % (
            a_[:3], b_[:3], alle, 100 * schwanz, len(gz)))

    print("   b) Handelsergebnisse: Wochen-R (Austritt), gemeinsame Spanne BTC/ETH/SOL ab SOL-Start:")
    start = k_["SOL-USDT-SWAP"][0][0]
    ende = max(t["ts_out"] for t in trades)
    w0, w1 = wochen(start), wochen(ende)
    reihe = defaultdict(lambda: [0.0] * (w1 - w0 + 1))
    for t in trades:
        if t["inst"] == "XAU-USDT-SWAP" or t["ts_out"] < start:
            continue
        reihe[(t["spur"], t["inst"])][wochen(t["ts_out"]) - w0] += t["r"]
    sp_ = sorted({s for s, _ in reihe})
    in_ = ["BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP"]
    n_w = w1 - w0 + 1
    summe_i = {i: [sum(reihe[(s, i)][w] for s in sp_ if (s, i) in reihe) for w in range(n_w)] for i in in_}
    summe_s = {s: [sum(reihe[(s, i)][w] for i in in_ if (s, i) in reihe) for w in range(n_w)] for s in sp_}
    print("      Instrumente (Summe ueber Spuren):")
    for x_, y_ in ((0, 1), (0, 2), (1, 2)):
        print("         %s ~ %s: %.2f" % (in_[x_][:3], in_[y_][:3], korr(summe_i[in_[x_]], summe_i[in_[y_]])))
    print("      Spuren (Summe ueber Instrumente):")
    zeilen = []
    for x_ in range(len(sp_)):
        for y_ in range(x_ + 1, len(sp_)):
            c = korr(summe_s[sp_[x_]], summe_s[sp_[y_]])
            zeilen.append(c)
            print("         %-22s ~ %-22s %.2f" % (sp_[x_], sp_[y_], c))
    schl = list(reihe)
    paare = [korr(reihe[schl[x_]], reihe[schl[y_]]) for x_ in range(len(schl)) for y_ in range(x_ + 1, len(schl))]
    paare = [p for p in paare if not math.isnan(p)]
    rho = sum(paare) / len(paare)
    n_k = len(schl)
    print("      Mittlere paarweise Korrelation aller %d Kombinationen (Spur x Instrument): %.2f" % (n_k, rho))
    print("      Effektive Zahl unabhaengiger Wetten: N_eff = N / (1 + (N-1) x rho) = %.1f von %d" % (
        n_k / (1 + (n_k - 1) * rho), n_k))

    print("   c) Gleichzeitigkeit und Cluster:")
    # offene Positionen je 4H-Balken ueber alle Kombinationen
    ereig = defaultdict(int)
    for t in trades:
        if t["inst"] == "XAU-USDT-SWAP":
            continue
        ereig[t["ts_in"]] += 1
        ereig[t["ts_out"]] -= 1
    lauf, hist, maxo = 0, defaultdict(float), 0
    zs = sorted(ereig)
    for z0, z1 in zip(zs, zs[1:]):
        lauf += ereig[z0]
        hist[lauf] += (z1 - z0) / 3600000.0
        maxo = max(maxo, lauf)
    tot = sum(hist.values())
    print("      Max. gleichzeitig offene Positionen (alle Spuren, BTC/ETH/SOL): %d" % maxo)
    for n_ in sorted(hist):
        if hist[n_] / tot > 0.01:
            print("         %2d offen: %4.1f %% der Zeit" % (n_, 100 * hist[n_] / tot))
    # Cluster: bester/schlechtester 3-Tage-Block (Austritt) ueber alle
    tage = defaultdict(float)
    for t in trades:
        if t["inst"] == "XAU-USDT-SWAP":
            continue
        tage[int(t["ts_out"] // 86400000)] += t["r"]
    td = sorted(tage)
    bl = []
    for i in range(len(td)):
        bl.append(sum(tage[d] for d in td if td[i] <= d < td[i] + 3))
    print("      Schlechtester 3-Tage-Block (alle Austritte): %+.1f R | bester %+.1f R | schlechtester Einzeltag %+.1f R" % (
        min(bl), max(bl), min(tage.values())))
    print("      Zum Vergleich Kill-Switch je Spur: 45 USD / 5 USD Risiko = 9 R")
    # Drawdown je Spur und gesamt (Wochen-R, BTC/ETH/SOL)
    def maxdd(serie):
        s, spitze, dd = 0.0, 0.0, 0.0
        for v in serie:
            s += v
            spitze = max(spitze, s)
            dd = max(dd, spitze - s)
        return dd
    print("      Max. Drawdown je Spur (Wochen-R): " + "  ".join("%s %.1f R" % (s.replace("klassik_", ""), maxdd(summe_s[s])) for s in sp_))
    gesamt = [sum(summe_s[s][w] for s in sp_) for w in range(n_w)]
    print("      Max. Drawdown ALLE Spuren zusammen: %.1f R | schlechteste Woche %+.1f R | Summe %+.1f R" % (
        maxdd(gesamt), min(gesamt), sum(gesamt)))


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("handel")
    p1.add_argument("--spur", required=True)
    p1.add_argument("--anzahl", type=int, default=14000)
    p1.add_argument("--cache", default=str(HANDEL / "daten" / "fib_bt"))
    p1.add_argument("--aus", required=True)
    p2 = sub.add_parser("analyse")
    p2.add_argument("--handel", required=True)
    p2.add_argument("--cache", default=str(HANDEL / "daten" / "kosten"))
    p2.add_argument("--kerzen", default=str(HANDEL / "daten" / "fib_bt"))
    a = ap.parse_args(argv)
    return handel(a) if a.cmd == "handel" else analyse(a)


if __name__ == "__main__":
    main()

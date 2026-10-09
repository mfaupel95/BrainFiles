"""Backtest: Fibonacci-Stop/Ziel gegen den Ist-Stand der Klassik-Trendspuren.

AUFTRAG (Max, 08.10.2026), Stufe A: die Einstiege der Spuren bleiben, nur Stop
und Ziel kommen aus fib.py. Dieses Skript misst, ob das besser ist. Es schreibt
nichts in Spuren, wachen.json oder Buecher.

FAIRNESS-REGELN (Hausregeln aus strategie-aus-fremdquelle.md):
  * Kein Blick nach vorn: Signal auf dem Schluss der Kerze i, Einstieg zu
    diesem Schluss, Stop/Ziel pruefen ab Kerze i+1.
  * Stop VOR Ziel im selben Balken; Gap ueber den Stop fuellt zum Eroeffnungskurs.
  * Gebuehr je Seite (`gebuehr_taker` der Spur).
  * Ergebnis in R (netto): Gewinn/Verlust geteilt durch den Stop-Abstand. So sind
    Stops unterschiedlicher Weite vergleichbar - 1 R ist immer das Risiko des
    Trades. (Die Spuren dimensionieren nach festem Risiko, das passt dazu.)
  * Die Regel-Ausstiege der Spur (Gegensignal / Kanal) gelten in BEIDEN
    Varianten weiter; Fib ersetzt nur Stop und Ziel.
  * Fib lehnt Trades ab (Pflichtrahmen, Mindest-R, kein Bein). Deshalb wird die
    Grundlinie zusaetzlich NUR auf den von Fib angenommenen Trades gerechnet
    (`Basis*`): so bleibt der Filtereffekt vom Stop/Ziel-Effekt getrennt.
  * Zwei Haelften der Reihe und beide Seiten getrennt; ein Gewinner muss in
    beiden Haelften vor der Grundlinie liegen.

Datenquelle: OKX /api/v5/market/history-candles (oeffentlich, 100 je Abruf),
Zwischenspeicher unter daten/fib_bt/ (durch die Whitelist ignoriert).

Aufruf:
    python fib_backtest.py --spuren klassik_ema,klassik_sma --anzahl 6000
"""

from __future__ import annotations

import argparse
import importlib.util
import itertools
import json
import os
import ssl
import sys
import time
import urllib.request
from pathlib import Path

HANDEL = Path(__file__).resolve().parent


def _lade(pfad, name):
    spec = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


fib = _lade(HANDEL / "fib.py", "fib_bt_fib")
kr = _lade(HANDEL / "klassik_regeln.py", "fib_bt_kr")

OKX = "https://www.okx.com/api/v5/market/history-candles"
BAR_MS = {"1H": 3600_000, "4H": 4 * 3600_000, "1D": 86400_000}


# --- Daten -------------------------------------------------------------------

def _ssl():
    ca = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE") \
        or ("/root/.ccr/ca-bundle.crt" if os.path.exists("/root/.ccr/ca-bundle.crt") else None)
    return ssl.create_default_context(cafile=ca) if ca else ssl.create_default_context()


def lade_kerzen(inst, bar, anzahl, cache_dir):
    """Aufsteigende, abgeschlossene Kerzen [ts, o, h, l, c, v]; Cache pro (inst, bar)."""
    pfad = Path(cache_dir) / ("%s_%s.json" % (inst, bar))
    if pfad.exists():
        try:
            k = json.loads(pfad.read_text())
            if len(k) >= anzahl:
                return k[-anzahl:]
        except Exception:
            pass
    ctx = _ssl()
    roh, after = {}, None
    while len(roh) < anzahl:
        url = "%s?instId=%s&bar=%s&limit=100" % (OKX, inst, bar)
        if after:
            url += "&after=%s" % after
        for versuch in range(4):
            try:
                rq = urllib.request.Request(url, headers={"User-Agent": "fib_backtest/1.0"})
                with urllib.request.urlopen(rq, timeout=20, context=ctx) as r:
                    d = json.loads(r.read())
                break
            except Exception:
                time.sleep(2 ** versuch)
        else:
            raise RuntimeError("OKX-Abruf scheitert: " + url)
        zeilen = d.get("data") or []
        if not zeilen:
            break
        for z in zeilen:
            if z[8] == "1":                      # nur abgeschlossene Kerzen
                roh[int(z[0])] = [int(z[0])] + [float(x) for x in z[1:6]]
        after = zeilen[-1][0]
        time.sleep(0.12)
    k = [roh[t] for t in sorted(roh)]
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps(k))
    return k[-anzahl:]


# --- Simulation --------------------------------------------------------------

def laufe(k, i, seite, einstieg, stop, ziel, regel_aus, gebuehr, stop_frac):
    """Eine Position ab Kerze i+1. Rueckgabe: dict mit r (netto), grund, bars."""
    n = len(k)
    for j in range(i + 1, n):
        o, h, l, c = k[j][1], k[j][2], k[j][3], k[j][4]
        if seite == "long":
            if l <= stop:
                return _ergebnis(seite, einstieg, min(o, stop), gebuehr, stop_frac, "stop", j - i)
            if ziel is not None and h >= ziel:
                return _ergebnis(seite, einstieg, ziel, gebuehr, stop_frac, "ziel", j - i)
        else:
            if h >= stop:
                return _ergebnis(seite, einstieg, max(o, stop), gebuehr, stop_frac, "stop", j - i)
            if ziel is not None and l <= ziel:
                return _ergebnis(seite, einstieg, ziel, gebuehr, stop_frac, "ziel", j - i)
        g = regel_aus(j, seite)
        if g:
            return _ergebnis(seite, einstieg, c, gebuehr, stop_frac, g, j - i)
    return _ergebnis(seite, einstieg, k[-1][4], gebuehr, stop_frac, "ende", n - 1 - i)


def _ergebnis(seite, einstieg, ausstieg, gebuehr, stop_frac, grund, bars):
    bewegung = (ausstieg - einstieg) / einstieg * (1 if seite == "long" else -1)
    return {"r": (bewegung - 2 * gebuehr) / stop_frac, "grund": grund, "bars": bars}


def signale(k, einstieg_fn, w):
    """[(i, seite)] auf jeder abgeschlossenen Kerze - das Signal ist zustandslos."""
    kn = int(w.get("kerzen_anzahl", 400))
    mindest = int(w.get("mindest_kerzen", 60))
    out = []
    for i in range(max(mindest, 1), len(k)):
        s = einstieg_fn(k[max(0, i - kn + 1): i + 1], w)
        if s:
            out.append((i, s))
    return out


def simuliere(k, sigs, varianten_fn, regel_aus):
    """Sequenziell: eine Position je Reihe; Signale in einer laufenden Position entfallen.

    varianten_fn(i, seite, kurs) -> (stop, ziel, stop_frac) | None (abgelehnt).
    Rueckgabe: Liste Trades mit i, seite, r, grund.
    """
    trades, frei_ab = [], 0
    for i, seite in sigs:
        if i < frei_ab:
            continue
        kurs = k[i][4]
        v = varianten_fn(i, seite, kurs)
        if v is None:
            continue
        stop, ziel, stop_frac, gebuehr = v
        t = laufe(k, i, seite, kurs, stop, ziel, regel_aus, gebuehr, stop_frac)
        t.update(i=i, seite=seite)
        trades.append(t)
        frei_ab = i + t["bars"] + 1
    return trades


def basis_variante(w):
    sp = float(w["stop_prozent"]) / 100.0
    r = float(w.get("ziel_r_vielfaches", 2.0))
    gb = float(w.get("gebuehr_taker", 0.0005))

    def f(i, seite, kurs):
        d = kurs * sp
        return ((kurs - d, kurs + r * d, sp, gb) if seite == "long"
                else (kurs + d, kurs - r * d, sp, gb))
    return f


def fib_variante(k, w, links, rechts, min_hub, stop_art, ziel_e, min_r=1.0):
    smin = float(w.get("pflicht_stop_prozent_min", 0.0))
    smax = float(w.get("pflicht_stop_prozent_max", 100.0))
    gb = float(w.get("gebuehr_taker", 0.0005))
    kn = int(w.get("kerzen_anzahl", 400))

    def f(i, seite, kurs):
        fenster = k[max(0, i - kn + 1): i + 1]
        p = fib.plan(fenster, seite, kurs, links=links, rechts=rechts,
                     min_hub_pct=min_hub, stop_art=stop_art,
                     stop_min_pct=smin, stop_max_pct=smax, min_r=0.0)
        if not p["ok"]:
            return None
        ziel = None
        if ziel_e is not None:
            z = [x for x in p["ziele"] if x["erweiterung"] == ziel_e]
            if not z or z[0]["r"] < min_r:
                return None
            ziel = z[0]["preis"]
        return (p["stop"], ziel, p["stop_pct"] / 100.0, gb)
    return f


# --- Auswertung --------------------------------------------------------------

def kennzahlen(trades, n_kerzen):
    if not trades:
        return {"n": 0, "winrate": 0.0, "e_r": 0.0, "summe_r": 0.0,
                "h1": 0.0, "h2": 0.0, "long": 0.0, "short": 0.0, "dd": 0.0}
    rs = [t["r"] for t in trades]
    mitte = n_kerzen // 2
    spitze, dd, lauf = 0.0, 0.0, 0.0
    for r in rs:
        lauf += r
        spitze = max(spitze, lauf)
        dd = max(dd, spitze - lauf)
    return {
        "n": len(rs),
        "winrate": sum(1 for r in rs if r > 0) / len(rs),
        "e_r": sum(rs) / len(rs),
        "summe_r": sum(rs),
        "h1": sum(t["r"] for t in trades if t["i"] < mitte),
        "h2": sum(t["r"] for t in trades if t["i"] >= mitte),
        "long": sum(t["r"] for t in trades if t["seite"] == "long"),
        "short": sum(t["r"] for t in trades if t["seite"] == "short"),
        "dd": dd,
    }


GITTER = {
    "swing": [(3, 3), (5, 5), (8, 8)],
    "min_hub": [1.0, 3.0],
    "stop_art": ["ursprung", "786"],
    "ziel_e": [1.0, 1.272, 1.618, None],     # None = nur Stop, Ausstieg per Regel
}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--spuren", default="klassik_ema,klassik_sma,klassik_macd,"
                    "klassik_donchian_trend,klassik_supertrend")
    ap.add_argument("--instrumente", default="BTC-USDT-SWAP,ETH-USDT-SWAP,SOL-USDT-SWAP,XAU-USDT-SWAP")
    ap.add_argument("--anzahl", type=int, default=6000)
    ap.add_argument("--cache", default=str(HANDEL / "daten" / "fib_bt"))
    ap.add_argument("--aus", default=str(HANDEL / "daten" / "fib_bt" / "ergebnis.json"))
    a = ap.parse_args(argv)

    insts = [x for x in a.instrumente.split(",") if x]
    ergebnis = {}
    for spur in [s for s in a.spuren.split(",") if s]:
        einstieg_fn, ausstieg_fn = kr.REGELN[spur]
        w = json.loads((HANDEL / spur / "wachen.json").read_text(encoding="utf-8"))
        bar = w.get("kerzen_zeitrahmen", "4H")
        for inst in insts:
            k = lade_kerzen(inst, bar, a.anzahl, a.cache)
            if len(k) < 500:
                print("%s %s: nur %d Kerzen - uebersprungen" % (spur, inst, len(k)))
                continue
            kn = int(w.get("kerzen_anzahl", 400))
            memo = {}

            def regel_aus(j, seite, k=k, w=w, kn=kn, fn=ausstieg_fn, memo=memo):
                key = (j, seite)
                if key not in memo:
                    memo[key] = fn(k[max(0, j - kn + 1): j + 1], seite, w)
                return memo[key]

            sigs = signale(k, einstieg_fn, w)
            basis = simuliere(k, sigs, basis_variante(w), regel_aus)
            zeilen = {"basis": kennzahlen(basis, len(k)), "varianten": []}
            for (l, r), hub, sa, ze in itertools.product(
                    GITTER["swing"], GITTER["min_hub"], GITTER["stop_art"], GITTER["ziel_e"]):
                fv = fib_variante(k, w, l, r, hub, sa, ze)
                trades = simuliere(k, sigs, fv, regel_aus)
                angenommen = {t["i"] for t in trades}
                # Grundlinie auf denselben Einstiegen (gleiche Signale, Basis-Exit)
                sub = [t for t in basis if t["i"] in angenommen]
                zeilen["varianten"].append({
                    "swing": [l, r], "min_hub": hub, "stop_art": sa, "ziel_e": ze,
                    "fib": kennzahlen(trades, len(k)),
                    "basis_gleiche_trades": kennzahlen(sub, len(k)),
                    "signale": len(sigs)})
            ergebnis["%s|%s" % (spur, inst)] = zeilen
            print("%s %s: %d Signale, Basis n=%d sumR=%.1f" % (
                spur, inst, len(sigs), zeilen["basis"]["n"], zeilen["basis"]["summe_r"]))

    Path(a.aus).parent.mkdir(parents=True, exist_ok=True)
    Path(a.aus).write_text(json.dumps(ergebnis, indent=1))
    print("Ergebnis:", a.aus)
    return ergebnis


if __name__ == "__main__":
    main()

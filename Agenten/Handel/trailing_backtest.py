"""Backtest: Trailing-Stop gegen festes Ziel auf den Klassik-Trendspuren.

ANLASS (08.10.2026): fib_backtest.py zeigte, dass auf den Trendspuren schon das
WEGLASSEN des festen 2R-Ziels die Summe von -43 R auf +56 R dreht. Dieses
Skript fragt: Bringt ein Trailing-Stop (trailing.py) darueber hinaus etwas -
und welche Einstellung?

Gleiche Einstiege wie die Spur (klassik_regeln.REGELN), gleicher Regelausstieg
(Gegensignal/Kanal), gleicher Start-Stop (`stop_prozent`). Nur die
Stop-Nachfuehrung und das Ziel unterscheiden die Arme. Ergebnis in R des
URSPRUENGLICHEN Stops (netto, Gebuehr je Seite), damit alles vergleichbar ist.

BEFUND beim Bau (08.10.2026): trailing.kandidat() kappt den Abstand mit
min() statt max() (Long) - bei halten 0,4 % und max_halten 5 % liegt der Stop
tatsaechlich 5 % hinter dem Hoch (Beispiel: Hoch 112 -> Stop 106,4 statt
111,55). Dieser Backtest rechnet die DOKUMENTIERTE Semantik; der Arm
"halten 5 %" ist das heutige Live-Verhalten.

Die Trailing-Rechnung bildet trailing.kandidat() nach (Trigger in R, Abstand
hinter dem Hochstand in %, Mindestabstand zum Kurs, nie zurueck, Mindest-Hub);
sie arbeitet auf abgeschlossenen Kerzen: der Stop wird am Kerzenschluss neu
gesetzt und gilt ab der NAECHSTEN Kerze (kein Blick nach vorn). Der Hochstand
folgt dem Kerzenhoch (Long) bzw. -tief (Short).

Aufruf:
    python trailing_backtest.py --cache <ordner> --aus <datei.json>
"""

from __future__ import annotations

import argparse
import importlib.util
import itertools
import json
import sys
from pathlib import Path

HANDEL = Path(__file__).resolve().parent


def _lade(pfad, name):
    spec = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


fb = _lade(HANDEL / "fib_backtest.py", "trail_bt_fb")
kr = fb.kr


def laufe_trailing(k, i, seite, einstieg, stop, ziel, regel_aus, gebuehr, stop_frac,
                   trigger_r=None, halten_pct=0.4, floor_pct=0.25,
                   min_hub_r=0.25, max_halten_pct=5.0, breakeven_r=None):
    """Eine Position ab Kerze i+1 mit nachgefuehrtem Stop.

    trigger_r None -> kein Trailing (reiner fester Stop). Der Stop gilt in
    Kerze j so, wie er am Schluss von j-1 stand. Stop vor Ziel im selben Balken.
    """
    n = len(k)
    vz = 1.0 if seite == "long" else -1.0
    abstand0 = abs(einstieg - stop)
    start_stop = stop
    hoch = einstieg
    for j in range(i + 1, n):
        o, h, l, c = k[j][1], k[j][2], k[j][3], k[j][4]
        if seite == "long":
            if l <= stop:
                return _erg(seite, einstieg, min(o, stop), gebuehr, stop_frac,
                            "trail" if stop != start_stop else "stop", j - i)
            if ziel is not None and h >= ziel:
                return _erg(seite, einstieg, ziel, gebuehr, stop_frac, "ziel", j - i)
        else:
            if h >= stop:
                return _erg(seite, einstieg, max(o, stop), gebuehr, stop_frac,
                            "trail" if stop != start_stop else "stop", j - i)
            if ziel is not None and l <= ziel:
                return _erg(seite, einstieg, ziel, gebuehr, stop_frac, "ziel", j - i)
        g = regel_aus(j, seite)
        if g:
            return _erg(seite, einstieg, c, gebuehr, stop_frac, g, j - i)
        hoch = max(hoch, h) if vz > 0 else min(hoch, l)
        plus_r = (c - einstieg) * vz / abstand0
        if breakeven_r is not None and plus_r >= breakeven_r:
            if (einstieg > stop) if vz > 0 else (einstieg < stop):
                stop = einstieg                    # Stop auf den Einstand, nie zurueck
        if trigger_r is None:
            continue
        if plus_r < trigger_r:
            continue
        neu = hoch - vz * abs(hoch) * halten_pct / 100.0
        grenze = hoch - vz * abs(hoch) * max_halten_pct / 100.0
        # Dokumentierte Semantik: der Abstand hinter dem Hoch ist `halten_pct`,
        # hoechstens `max_halten_pct` (Stop liegt also nie WEITER weg).
        # ACHTUNG trailing.py rechnet hier min()/max() vertauscht (siehe Kopf):
        # dort gilt effektiv der GROESSERE Abstand aus halten und 5 %. Der Arm
        # halten=5 % dieses Backtests entspricht dem heutigen Live-Verhalten.
        neu = max(neu, grenze) if vz > 0 else min(neu, grenze)
        floor = abs(c) * floor_pct / 100.0
        neu = min(neu, c - floor) if vz > 0 else max(neu, c + floor)
        besser = (neu > stop + 1e-12) if vz > 0 else (neu < stop - 1e-12)
        if besser and abs(neu - stop) / abstand0 >= min_hub_r:
            stop = neu
    return _erg(seite, einstieg, k[-1][4], gebuehr, stop_frac, "ende", n - 1 - i)


def _erg(seite, einstieg, ausstieg, gebuehr, stop_frac, grund, bars):
    return fb._ergebnis(seite, einstieg, ausstieg, gebuehr, stop_frac, grund, bars)


def simuliere(k, sigs, sp, ziel_r, regel_aus, gebuehr, **trail):
    """Sequenziell, eine Position je Reihe (wie fib_backtest.simuliere)."""
    trades, frei_ab = [], 0
    for i, seite in sigs:
        if i < frei_ab:
            continue
        kurs = k[i][4]
        d = kurs * sp
        stop = kurs - d if seite == "long" else kurs + d
        ziel = None
        if ziel_r is not None:
            ziel = kurs + ziel_r * d if seite == "long" else kurs - ziel_r * d
        t = laufe_trailing(k, i, seite, kurs, stop, ziel, regel_aus, gebuehr, sp, **trail)
        t.update(i=i, seite=seite)
        trades.append(t)
        frei_ab = i + t["bars"] + 1
    return trades


ARME = [("Ist: fest 2R-Ziel", dict(ziel_r="w", trigger_r=None))]
for tr, hp in itertools.product((1.0, 2.0, 3.0), (0.4, 1.0, 2.0, 3.0, 5.0)):
    ARME.append(("Trailing trig %.0fR halten %.1f%%" % (tr, hp), dict(ziel_r=None, trigger_r=tr, halten_pct=hp)))
ARME.insert(1, ("Kontrolle: kein Ziel, fester Stop", dict(ziel_r=None, trigger_r=None)))
ARME.insert(2, ("Breakeven nach 1R, kein Ziel", dict(ziel_r=None, trigger_r=None, breakeven_r=1.0)))
ARME.append(("Hausstandard + 2R-Ziel", dict(ziel_r="w", trigger_r=1.0, halten_pct=0.4)))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--spuren", default="klassik_ema,klassik_sma,klassik_macd,"
                    "klassik_donchian_trend,klassik_supertrend")
    ap.add_argument("--instrumente", default="BTC-USDT-SWAP,ETH-USDT-SWAP,SOL-USDT-SWAP,XAU-USDT-SWAP")
    ap.add_argument("--anzahl", type=int, default=6000)
    ap.add_argument("--cache", default=str(HANDEL / "daten" / "fib_bt"))
    ap.add_argument("--aus", default=str(HANDEL / "daten" / "fib_bt" / "trailing.json"))
    a = ap.parse_args(argv)

    summe = {name: [] for name, _ in ARME}
    je_spur = {}
    for spur in [s for s in a.spuren.split(",") if s]:
        einstieg_fn, ausstieg_fn = kr.REGELN[spur]
        w = json.loads((HANDEL / spur / "wachen.json").read_text(encoding="utf-8"))
        bar = w.get("kerzen_zeitrahmen", "4H")
        sp = float(w["stop_prozent"]) / 100.0
        gb = float(w.get("gebuehr_taker", 0.0005))
        for inst in [x for x in a.instrumente.split(",") if x]:
            k = fb.lade_kerzen(inst, bar, a.anzahl, a.cache)
            if len(k) < 500:
                continue
            kn = int(w.get("kerzen_anzahl", 400))
            memo = {}

            def regel_aus(j, seite, k=k, w=w, kn=kn, fn=ausstieg_fn, memo=memo):
                key = (j, seite)
                if key not in memo:
                    memo[key] = fn(k[max(0, j - kn + 1): j + 1], seite, w)
                return memo[key]

            sigs = fb.signale(k, einstieg_fn, w)
            for name, kw in ARME:
                kw = dict(kw)
                zr = float(w.get("ziel_r_vielfaches", 2.0)) if kw.get("ziel_r") == "w" else kw.get("ziel_r")
                kw.pop("ziel_r", None)
                tr = simuliere(k, sigs, sp, zr, regel_aus, gb, **kw)
                z = fb.kennzahlen(tr, len(k))
                summe[name].append(z)
                je_spur.setdefault(spur, {}).setdefault(name, []).append(z["summe_r"])
            print("%s %s fertig (%d Signale)" % (spur, inst, len(sigs)), flush=True)

    out = {}
    for name, zs in summe.items():
        out[name] = {
            "n": sum(z["n"] for z in zs), "summe_r": sum(z["summe_r"] for z in zs),
            "h1": sum(z["h1"] for z in zs), "h2": sum(z["h2"] for z in zs),
            "long": sum(z["long"] for z in zs), "short": sum(z["short"] for z in zs),
            "dd_max": max((z["dd"] for z in zs), default=0.0),
            "je_spur": {s: sum(v[name]) for s, v in je_spur.items()},
        }
    Path(a.aus).parent.mkdir(parents=True, exist_ok=True)
    Path(a.aus).write_text(json.dumps(out, indent=1))
    for name, o in sorted(out.items(), key=lambda x: -x[1]["summe_r"]):
        print("%-38s n=%5d sumR=%+7.1f h1=%+6.1f h2=%+6.1f L=%+6.1f S=%+6.1f" % (
            name, o["n"], o["summe_r"], o["h1"], o["h2"], o["long"], o["short"]))
    return out


if __name__ == "__main__":
    main()

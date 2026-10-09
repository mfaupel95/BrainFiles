"""Backtest mit den echten Begrenzungen der Trend-Klassikspuren.

AUFTRAG (Max, 09.10.2026): "Positionslimits im Backtest erzwingen". Die
bisherigen Studien (PR #12 bis #19) liessen jede Kombination aus Spur und
Instrument unabhaengig laufen. Die Spuren haben aber eine Kette von Bremsen
(spur_buch.zyklus, risikovorfilter.py, ratschen.py, wachen_pruefung.py):

  1. Plaetze         max_offene_positionen (3), max 1 Position je Instrument
  2. Groesse         Nominal = Risiko / Stop, hoechstens max_pro_trade_usd
  3. Vorfilter       risikovorfilter: in den letzten 12 h gebuchte Runden;
                     Ergebnis <= -25 USD oder >= +25 USD, oder
                     Ergebnis/Einsatz <= -5 % bzw. >= +5 %  -> KEIN neuer Einstieg
  4. Halbierung      Ruecklauf der gebuchten Kurve >= drawdown_halbierung_usd
                     (15 USD) -> halbe Groesse
  5. Kill            Ruecklauf >= kill_switch_gesamt_usd (45 USD) -> alles flach,
                     7 Tage Sperre

Reihenfolge je Zyklus wie im Code: Kill/Ratsche zuerst, dann Ausstiege, dann
Einstiege. Eine Spur = ein Buch (eigenes Journal/Zustand), also wird je Spur
simuliert. Universum = `instrumente` der Wache (BTC/ETH/SOL); XAU ist dort nicht
enthalten und fehlt deshalb hier (frueher Studien nahmen XAU als Zugabe mit).

KILL, ZWEI LESARTEN (siehe `kill`-Parameter):
  "implementiert": so, wie spur_buch.zyklus heute handelt (am 09.10.2026 mit dem
        echten Code und einem kuenstlichen Journal nachgestellt): Positionen werden
        OHNE Journalzeile geloescht, der gebuchte Rueckgang bleibt stehen. Nach
        Ablauf der Frist laeuft ein Zyklus frei, im naechsten greift der Kill sofort
        wieder - solange der Ruecklauf >= 45 USD bleibt, also dauerhaft.
  "gemeint": ANNAHME, wie es gedacht war: Positionen werden zum Marktkurs
        geschlossen UND gebucht, nach der Frist beginnt der Ruecklauf neu zu laufen.

Ergebnis in USD bei 5 USD Risiko je Position (netto, Gebuehr 0,05 % je Seite).

Aufruf:
    python limits_backtest.py lauf --spur klassik_ema --aus <datei.json>
    python limits_backtest.py auswerten "<dir>/*.json"
"""

from __future__ import annotations

import argparse
import glob
import importlib.util
import json
import sys
from collections import defaultdict
from pathlib import Path

HANDEL = Path(__file__).resolve().parent
BAR_MS = 4 * 3600 * 1000
SPUREN = ["klassik_ema", "klassik_sma", "klassik_macd", "klassik_donchian_trend", "klassik_supertrend"]


def _lade(pfad, name):
    spec = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


st = _lade(HANDEL / "ausstieg_studie.py", "lim_studie")
fb = st.fb
kr = st.kr

# Stufen der Begrenzung (jede schliesst die vorigen ein)
VARIANTEN = [
    ("A ohne Limits",            dict(plaetze=False, vf_usd=False, vf_pct=False, halbierung=False, kill=None)),
    ("B Plaetze und Groesse",    dict(plaetze=True,  vf_usd=False, vf_pct=False, halbierung=False, kill=None)),
    ("C + Vorfilter nur USD",    dict(plaetze=True,  vf_usd=True,  vf_pct=False, halbierung=False, kill=None)),
    ("D + Vorfilter komplett",   dict(plaetze=True,  vf_usd=True,  vf_pct=True,  halbierung=False, kill=None)),
    ("E + Halbierung 15 USD",    dict(plaetze=True,  vf_usd=True,  vf_pct=True,  halbierung=True,  kill=None)),
    ("F + Kill implementiert",   dict(plaetze=True,  vf_usd=True,  vf_pct=True,  halbierung=True,  kill="implementiert")),
    ("G + Kill gemeint",         dict(plaetze=True,  vf_usd=True,  vf_pct=True,  halbierung=True,  kill="gemeint")),
]


def konfig(w):
    pct = float(w["stop_prozent"])
    pct = min(max(pct, float(w.get("pflicht_stop_prozent_min", 0))), float(w.get("pflicht_stop_prozent_max", 100)))
    return {
        "risiko": float(w["risiko_je_position_usd"]),
        "pct": pct,
        "max_pos": int(w.get("max_offene_positionen", 3)),
        "max_trade": float(w["max_pro_trade_usd"]),
        "fenster_ms": float(w.get("risiko_fenster_stunden", 12.0)) * 3600 * 1000,
        "v_usd": float(w.get("risiko_verlust_max_usd", 25.0)),
        "g_usd": float(w.get("risiko_gewinn_ziel_usd", 25.0)),
        "v_pct": float(w.get("risiko_verlust_max_pct", 5.0)),
        "g_pct": float(w.get("risiko_gewinn_ziel_pct", 5.0)),
        "halb": float(w["drawdown_halbierung_usd"]),
        "kill": float(w["kill_switch_gesamt_usd"]),
        "frist_ms": float(w.get("kill_frist_stunden", 168)) * 3600 * 1000,
        "gebuehr": float(w.get("gebuehr_taker", 0.0005)),
        "vorfilter_an": bool(w.get("risikovorfilter")),
    }


def portfolio(cfg, daten, regeln, start_ms=0):
    """Eine Spur als Buch. daten[inst] = {"k": Kerzen, "sigs": set(i), "ausgang": f(i) -> (j, r)}.

    start_ms: ein frisches Buch ab diesem Zeitpunkt (Rolling-Start); davor wird nichts gehandelt.
    Rueckgabe: dict mit Kennzahlen. `r` ist netto-R der Position (voller Groesse)."""
    k_ = {inst: d["k"] for inst, d in daten.items()}
    idx = {inst: {x[0]: n for n, x in enumerate(k)} for inst, k in k_.items()}
    zeiten = sorted({x[0] for k in k_.values() for x in k})
    pos = {}                                    # inst -> {"j","r","nominal","i","entry"}
    runden = []                                 # (zeit_ms, gv_usd, nominal)
    cum = peak = 0.0
    kill_seit = None
    blockiert = defaultdict(int)
    stats = {"einstiege": 0, "kills": 0, "erster_kill": None, "tot_ab": None,
             "ungebucht_verworfen": 0}
    verlauf = []

    def ruecklauf():
        return peak - cum

    for ts in zeiten:
        if ts < start_ms:
            continue
        jetzt = ts + BAR_MS                      # Zyklus am Schluss des Balkens
        # ---- 1) Kill / Ratsche ----
        rl = ruecklauf()
        if regeln["kill"] and rl >= cfg["kill"]:
            if kill_seit is None:
                stats["kills"] += 1
                stats["erster_kill"] = stats["erster_kill"] or jetzt
                if regeln["kill"] == "implementiert":
                    stats["ungebucht_verworfen"] += len(pos)
                    pos = {}
                else:                            # gemeint: zum Marktkurs schliessen und buchen
                    for inst, p in list(pos.items()):
                        n = idx[inst].get(ts)
                        if n is None:
                            continue
                        cur = k_[inst][n][4]
                        r = ((cur / p["entry"] - 1.0) - 2 * cfg["gebuehr"]) / (cfg["pct"] / 100.0)
                        gv = r * (cfg["pct"] / 100.0) * p["nominal"]
                        runden.append((jetzt, gv, p["nominal"]))
                        cum += gv
                        peak = max(peak, cum)
                    pos = {}
                kill_seit = jetzt
                continue
            if jetzt - kill_seit < cfg["frist_ms"]:
                if regeln["kill"] == "implementiert":
                    stats["ungebucht_verworfen"] += len(pos)
                pos = {}
                continue
            kill_seit = None                     # Frist um: dieser Zyklus laeuft frei
            if regeln["kill"] == "gemeint":
                peak = cum                       # Annahme: Ruecklauf beginnt neu
            elif stats["tot_ab"] is None:
                stats["tot_ab"] = jetzt          # ab hier greift der Kill im Folgezyklus wieder
        faktor = 0.5 if (regeln["halbierung"] and ruecklauf() >= cfg["halb"]) else 1.0

        # ---- 2) Ausstiege ----
        for inst, p in list(pos.items()):
            n = idx[inst].get(ts)
            if n is not None and n == p["j"]:
                gv = p["r"] * (cfg["pct"] / 100.0) * p["nominal"]
                runden.append((jetzt, gv, p["nominal"]))
                cum += gv
                peak = max(peak, cum)
                del pos[inst]

        # ---- 3) Einstiege ----
        for inst in sorted(daten):
            n = idx[inst].get(ts)
            if n is None or n not in daten[inst]["sigs"]:
                continue
            if inst in pos:
                continue
            if regeln["plaetze"] and len(pos) >= cfg["max_pos"]:
                blockiert["Plaetze"] += 1
                continue
            if cfg["vorfilter_an"] and (regeln["vf_usd"] or regeln["vf_pct"]):
                fenster = [x for x in runden if jetzt - cfg["fenster_ms"] < x[0] <= jetzt]
                erg = sum(x[1] for x in fenster)
                einsatz = sum(x[2] for x in fenster)
                grund = None
                if regeln["vf_usd"] and erg <= -abs(cfg["v_usd"]):
                    grund = "Vorfilter Verlust USD"
                elif regeln["vf_usd"] and erg >= abs(cfg["g_usd"]):
                    grund = "Vorfilter Gewinn USD"
                elif regeln["vf_pct"] and einsatz > 0 and erg / einsatz * 100.0 <= -abs(cfg["v_pct"]):
                    grund = "Vorfilter Verlust %"
                elif regeln["vf_pct"] and einsatz > 0 and erg / einsatz * 100.0 >= abs(cfg["g_pct"]):
                    grund = "Vorfilter Gewinn %"
                if grund:
                    blockiert[grund] += 1
                    continue
            nominal = cfg["risiko"] / (cfg["pct"] / 100.0)
            if regeln["plaetze"]:
                nominal = min(nominal, cfg["max_trade"])
            nominal *= faktor
            j, r = daten[inst]["ausgang"](n)
            pos[inst] = {"j": j, "r": r, "nominal": nominal, "i": n, "entry": k_[inst][n][4]}
            stats["einstiege"] += 1
        verlauf.append(cum)

    gv_sum = sum(x[1] for x in runden)
    dd = peak_ = 0.0
    c = tief = 0.0
    for _, gv, _n in runden:
        c += gv
        peak_ = max(peak_, c)
        dd = max(dd, peak_ - c)
        tief = min(tief, c)
    return {"tief_usd": tief, "usd": gv_sum, "runden": len(runden), "einstiege": stats["einstiege"],
            "kills": stats["kills"], "erster_kill": stats["erster_kill"], "tot_ab": stats["tot_ab"],
            "ungebucht": stats["ungebucht_verworfen"], "max_dd_usd": dd,
            "blockiert": dict(blockiert), "letzte_runde": runden[-1][0] if runden else None}


def baue_daten(spur, anzahl, cache):
    """(cfg, daten) einer Spur: Long-Signale und Ausgaenge je Instrument der Wache."""
    w = json.loads((HANDEL / spur / "wachen.json").read_text(encoding="utf-8"))
    cfg = konfig(w)
    ef, af = kr.REGELN[spur]
    kn = int(w.get("kerzen_anzahl", 400))
    sp = cfg["pct"] / 100.0
    daten = {}
    for inst in w["instrumente"]:
        k = fb.lade_kerzen(inst, w.get("kerzen_zeitrahmen", "4H"), anzahl, cache)
        memo = {}

        def regel_aus(j, seite, k=k, w=w, kn=kn, fn=af, memo=memo):
            key = (j, seite)
            if key not in memo:
                memo[key] = fn(k[max(0, j - kn + 1): j + 1], seite, w)
            return memo[key]

        sigs = {i for i, s in fb.signale(k, ef, w) if s == "long"}                # nur_long
        ausg_memo = {}

        def ausgang(i, k=k, regel_aus=regel_aus, memo=ausg_memo):
            if i not in memo:
                kurs = k[i][4]
                d = kurs * sp
                t = st.laufe(k, i, "long", kurs, kurs - d, regel_aus, cfg["gebuehr"], sp, None, modus=None)
                memo[i] = (i + t["bars"], t["r"])
            return memo[i]

        daten[inst] = {"k": k, "sigs": sigs, "ausgang": ausgang}
        print("%s %s: %d Long-Signale" % (spur, inst, len(sigs)), flush=True)
    return cfg, daten


def lauf(a):
    cfg, daten = baue_daten(a.spur, a.anzahl, a.cache)
    aus = {"spur": a.spur, "cfg": {k_: v for k_, v in cfg.items()}, "ergebnis": {}}
    for name, regeln in VARIANTEN:
        aus["ergebnis"][name] = portfolio(cfg, daten, regeln)
        e = aus["ergebnis"][name]
        print("  %-28s %7.1f USD | Einstiege %4d | Kills %d" % (name, e["usd"], e["einstiege"], e["kills"]), flush=True)
    # Rolling-Start: frisches Buch an vielen Starttagen - wie schnell trifft der Kill (Stufe F)?
    erste = max(d["k"][0][0] for d in daten.values())
    letzte = max(d["k"][-1][0] for d in daten.values())
    f_regeln = dict(VARIANTEN)["F + Kill implementiert"]
    aus["rolling"] = []
    t0 = erste + 150 * 86400 * 1000                       # Einlaufzeit der Indikatoren
    while t0 < letzte - 30 * 86400 * 1000:
        e = portfolio(cfg, daten, f_regeln, start_ms=t0)
        aus["rolling"].append({"start": t0, "tage_bis_kill": None if not e["erster_kill"]
                               else (e["erster_kill"] - t0) / 86400000.0,
                               "restlaufzeit_tage": (letzte - t0) / 86400000.0, "usd": e["usd"]})
        t0 += 14 * 86400 * 1000
    Path(a.aus).parent.mkdir(parents=True, exist_ok=True)
    Path(a.aus).write_text(json.dumps(aus))


KILL_R = (9, 15, 20, 30, 40, 60)          # Schwelle als Vielfaches des Risikos je Position (9 = die alten 45 USD)


def killraster(a):
    """Kill-Schwelle in R-Vielfachen: Kill wie gemeint (Marktkurs, Reset), Rolling-Start."""
    cfg, daten = baue_daten(a.spur, a.anzahl, a.cache)
    regeln = dict(VARIANTEN)["G + Kill gemeint"]
    erste = max(d["k"][0][0] for d in daten.values())
    letzte = max(d["k"][-1][0] for d in daten.values())
    aus = {"spur": a.spur, "risiko": cfg["risiko"], "raster": {}}
    for r in KILL_R:
        c = dict(cfg, kill=r * cfg["risiko"])
        voll = portfolio(c, daten, regeln)
        starts = []
        t0 = erste + 150 * 86400 * 1000
        while t0 < letzte - 30 * 86400 * 1000:
            e = portfolio(c, daten, regeln, start_ms=t0)
            starts.append({"tage_bis_kill": None if not e["erster_kill"] else (e["erster_kill"] - t0) / 86400000.0,
                           "tief": e["tief_usd"], "usd": e["usd"], "kills": e["kills"],
                           "rest": (letzte - t0) / 86400000.0})
            t0 += 14 * 86400 * 1000
        aus["raster"][str(r)] = {"voll": voll, "starts": starts}
        print("  Schwelle %2d R: %+8.1f USD, Kills %d, max DD %.0f" % (r, voll["usd"], voll["kills"], voll["max_dd_usd"]), flush=True)
    Path(a.aus).parent.mkdir(parents=True, exist_ok=True)
    Path(a.aus).write_text(json.dumps(aus))


def killraster_auswerten(muster):
    erg = [json.loads(Path(f).read_text()) for f in sorted(glob.glob(muster))]
    print("== Kill-Schwelle in Vielfachen des Risikos je Position (5 USD); Kill gemeint (Marktkurs, Reset), Halbierung 15 USD, Vorfilter an")
    print("%-8s %9s %8s | Spur: %s" % ("Schwelle", "Summe USD", "Kills", " ".join("%-12s" % e["spur"].replace("klassik_", "")[:12] for e in erg)))
    for r in KILL_R:
        zeilen = []
        for e in erg:
            ra = e["raster"][str(r)]
            zeilen.append("%+7.0f/%2dK" % (ra["voll"]["usd"], ra["voll"]["kills"]))
        usd = sum(e["raster"][str(r)]["voll"]["usd"] for e in erg)
        kills = sum(e["raster"][str(r)]["voll"]["kills"] for e in erg)
        print("%2d R %4d USD %+8.0f %8d | %s" % (r, r * 5, usd, kills, "  ".join(zeilen)))
    print("\n== Rolling-Start (frisches Buch): Anteil der Starts mit Kill binnen 365 Tagen / tiefster Stand (USD) im Median und im schlechtesten Fall")
    print("%-8s | %s" % ("Schwelle", " ".join("%-26s" % e["spur"].replace("klassik_", "")[:12] for e in erg)))
    for r in KILL_R:
        spalten = []
        for e in erg:
            st_ = e["raster"][str(r)]["starts"]
            n = len(st_)
            kill365 = 100.0 * sum(1 for x in st_ if x["tage_bis_kill"] is not None and x["tage_bis_kill"] <= 365) / n
            tiefs = sorted(x["tief"] for x in st_)
            spalten.append("%3.0f%% | med %5.0f | min %5.0f" % (kill365, tiefs[n // 2], tiefs[0]))
        print("%2d R     | %s" % (r, "  ".join(spalten)))


def datum(ms):
    import datetime
    return "-" if not ms else datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc).strftime("%Y-%m-%d")


def auswerten(muster):
    dateien = sorted(glob.glob(muster))
    erg = [json.loads(Path(f).read_text()) for f in dateien]
    print("== Ergebnis je Stufe, Summe ueber %d Spuren (USD bei 5 USD Risiko je Position)" % len(erg))
    print("%-28s %9s %9s %7s %6s %10s" % ("Stufe", "USD", "Einstiege", "Runden", "Kills", "max DD/Spur"))
    for name, _ in VARIANTEN:
        s = [e["ergebnis"][name] for e in erg]
        print("%-28s %+9.1f %9d %7d %6d %10.1f" % (
            name, sum(x["usd"] for x in s), sum(x["einstiege"] for x in s), sum(x["runden"] for x in s),
            sum(x["kills"] for x in s), max(x["max_dd_usd"] for x in s)))
    print("\n== Je Spur: Stufe A (ohne Limits) -> D (Vorfilter) -> F (Kill wie implementiert) -> G (Kill gemeint)")
    for e in erg:
        r = e["ergebnis"]
        print("%-24s A %+8.1f | D %+8.1f (%d Einstiege von %d) | F %+8.1f, erster Kill %s, Einstiege %d | G %+8.1f, Kills %d" % (
            e["spur"].replace("klassik_", ""), r["A ohne Limits"]["usd"], r["D + Vorfilter komplett"]["usd"],
            r["D + Vorfilter komplett"]["einstiege"], r["A ohne Limits"]["einstiege"],
            r["F + Kill implementiert"]["usd"], datum(r["F + Kill implementiert"]["erster_kill"]),
            r["F + Kill implementiert"]["einstiege"], r["G + Kill gemeint"]["usd"], r["G + Kill gemeint"]["kills"]))
    print("\n== Warum Einstiege entfallen (Stufe F, Zaehlung der Blocker, Summe ueber Spuren)")
    summe = defaultdict(int)
    for e in erg:
        for k_, v in e["ergebnis"]["F + Kill implementiert"]["blockiert"].items():
            summe[k_] += v
    for k_, v in sorted(summe.items(), key=lambda x: -x[1]):
        print("   %-26s %6d" % (k_, v))
    print("\n== Rolling-Start: frisches Buch (5 USD Risiko, alle Bremsen, Kill wie implementiert) an vielen Starttagen")
    print("   %-22s %7s | getroffen nach 90 / 180 / 365 Tagen | irgendwann | Median bis Kill" % ("Spur", "Starts"))
    for e in erg:
        rl = e.get("rolling") or []
        if not rl:
            continue
        n = len(rl)
        def anteil(tage):
            return 100.0 * sum(1 for x in rl if x["tage_bis_kill"] is not None and x["tage_bis_kill"] <= tage) / n
        getroffen = sorted(x["tage_bis_kill"] for x in rl if x["tage_bis_kill"] is not None)
        med = getroffen[len(getroffen) // 2] if getroffen else float("nan")
        print("   %-22s %7d | %4.0f %% / %4.0f %% / %4.0f %%        | %5.0f %%     | %6.0f Tage" % (
            e["spur"].replace("klassik_", ""), n, anteil(90), anteil(180), anteil(365), anteil(1e9), med))
    print("\n== Je Spur, Blocker einzeln (Stufe D, ohne Kill)")
    for e in erg:
        b = e["ergebnis"]["D + Vorfilter komplett"]["blockiert"]
        print("   %-22s %s" % (e["spur"].replace("klassik_", ""), ", ".join("%s %d" % (k_, v) for k_, v in sorted(b.items(), key=lambda x: -x[1])) or "-"))


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("lauf")
    p1.add_argument("--spur", required=True)
    p1.add_argument("--anzahl", type=int, default=14000)
    p1.add_argument("--cache", default=str(HANDEL / "daten" / "fib_bt"))
    p1.add_argument("--aus", required=True)
    p2 = sub.add_parser("auswerten")
    p2.add_argument("muster")
    p3 = sub.add_parser("killraster")
    p3.add_argument("--spur", required=True)
    p3.add_argument("--anzahl", type=int, default=14000)
    p3.add_argument("--cache", default=str(HANDEL / "daten" / "fib_bt"))
    p3.add_argument("--aus", required=True)
    p4 = sub.add_parser("killraster-auswerten")
    p4.add_argument("muster")
    a = ap.parse_args(argv)
    if a.cmd == "lauf":
        return lauf(a)
    if a.cmd == "killraster":
        return killraster(a)
    if a.cmd == "killraster-auswerten":
        return killraster_auswerten(a.muster)
    return auswerten(a.muster)


if __name__ == "__main__":
    main()

"""Backtest der vierten Spur: Opening Range Breakout ueber DE30/US30/NAS100.

Diese Datei prueft die "81 %"-Behauptung (SPEC.md, Anlass). Sie handelt nichts.
Regeln exakt nach SPEC.md, Abschnitt "Die Strategie, exakt".

Mehrdeutigkeit: M15 loest nicht auf, ob Hoch oder Tief zuerst kam. Beruehrt
eine Kerze Stop UND Ziel, zaehlt sie als Stop (konservativ, "am Tief pruefen,
nicht am Schluss").
"""

import session as sess


def sessions_gruppieren(kerzen, inst_konf):
    aus = {}
    for k in kerzen:
        tag = sess.handelstag(k["zeit"], inst_konf["zone"])
        eroeff, _ = sess.opening_range_fenster(inst_konf, tag)
        schluss = sess.zwangsschluss(inst_konf, tag)
        if eroeff <= k["zeit"] < schluss:
            aus.setdefault(tag, []).append(k)
    return [(t, sorted(aus[t], key=lambda x: x["zeit"])) for t in sorted(aus)]


def opening_range(session_kerzen, inst_konf, tag):
    start, ende = sess.opening_range_fenster(inst_konf, tag)
    im_fenster = [k for k in session_kerzen if start <= k["zeit"] < ende]
    if len(im_fenster) < 2:
        return None
    zwei = im_fenster[:2]
    return max(k["h"] for k in zwei), min(k["l"] for k in zwei)


def _inst_schluessel(inst_konf, w):
    for name, konf in w["instrumente"].items():
        if konf is inst_konf or konf == inst_konf:
            return name
    return next(iter(w["instrumente"]))


def simuliere_session(session_kerzen, inst_konf, tag, w, einstiegsmodell):
    key = _inst_schluessel(inst_konf, w)
    hr = opening_range(session_kerzen, inst_konf, tag)
    if hr is None:
        return None
    hoch, tief = hr
    range_hoehe = hoch - tief
    if range_hoehe < w["mindest_range_punkte"][key] or range_hoehe > w["max_range_punkte"][key]:
        return None

    _, range_ende = sess.opening_range_fenster(inst_konf, tag)
    letzt = sess.letzter_einstieg(inst_konf, tag, w["letzter_einstieg_min_vor_schluss"])
    nach_range = [k for k in session_kerzen if k["zeit"] >= range_ende]

    einstieg_kerze = None
    richtung = None
    for i, k in enumerate(nach_range):
        if k["zeit"] > letzt:
            break
        if k["c"] > hoch:
            einstieg_kerze, richtung, rest = k, "long", nach_range[i + 1:]
            break
        if k["c"] < tief:
            einstieg_kerze, richtung, rest = k, "short", nach_range[i + 1:]
            break
    if einstieg_kerze is None:
        return None

    # Nur Kerzen pruefen, durch die die Position tatsaechlich gehalten wurde:
    #   schluss            -> Einstieg = Schluss der Ausbruchskerze, gehalten ab
    #                         der NAECHSTEN Kerze (H/L der Ausbruchskerze lagen
    #                         vor dem Einstieg) -> pruef_kerzen = rest
    #   naechste_eroeffnung -> Einstieg = Open der Fuellkerze (rest[0]), diese
    #                         Kerze wird voll gehalten -> pruef_kerzen ab rest[0]
    if einstiegsmodell == "schluss":
        einstieg = einstieg_kerze["c"]
        pruef_kerzen = list(rest)
    else:  # naechste_eroeffnung
        if not rest:
            return None
        einstieg = rest[0]["o"]
        pruef_kerzen = list(rest)

    if richtung == "long":
        stop = tief
        ziel = einstieg + (w["ziel_k"] * range_hoehe if w["ziel_modus"] == "r_vielfaches"
                           else w["ziel_punkte"][key])
    else:
        stop = hoch
        ziel = einstieg - (w["ziel_k"] * range_hoehe if w["ziel_modus"] == "r_vielfaches"
                           else w["ziel_punkte"][key])

    ausgang, ausstieg, mehrdeutig = "zwangsschluss", None, False
    for k in pruef_kerzen:
        if richtung == "long":
            stop_beruehrt = k["l"] <= stop
            ziel_beruehrt = k["h"] >= ziel
        else:
            stop_beruehrt = k["h"] >= stop
            ziel_beruehrt = k["l"] <= ziel
        if stop_beruehrt and ziel_beruehrt:
            ausgang, ausstieg, mehrdeutig = "stop", stop, True
            break
        if stop_beruehrt:
            ausgang, ausstieg = "stop", stop
            break
        if ziel_beruehrt:
            ausgang, ausstieg = "ziel", ziel
            break
    if ausstieg is None:
        ausstieg = pruef_kerzen[-1]["c"] if pruef_kerzen else einstieg

    gv = (ausstieg - einstieg) if richtung == "long" else (einstieg - ausstieg)
    return {"tag": tag, "inst": key, "richtung": richtung, "einstieg": einstieg,
            "stop": stop, "ziel": ziel, "ausgang": ausgang, "ausstieg": ausstieg,
            "range_punkte": range_hoehe, "mehrdeutig": mehrdeutig,
            "gv_punkte": gv}


# --- Kosten + Bericht -----------------------------------------------------

from collections import defaultdict


def mit_kosten(ergebnis, spread_punkte, slippage_punkte=0.5):
    """gv_punkte nach Spread. Modell SPEC.md: ein voller Spread + Slippage je
    Runde (OANDA-Index-CFD = Spread, keine Kommission auf Standard)."""
    return ergebnis["gv_punkte"] - spread_punkte - slippage_punkte


def _quartal(d):
    return "%d-Q%d" % (d.year, (d.month - 1) // 3 + 1)


def _noetige_trefferquote(oe_gewinn, oe_verlust):
    spanne = oe_gewinn + abs(oe_verlust)
    return abs(oe_verlust) / spanne if spanne > 0 else 1.0


def bericht(ergebnisse, inst_konf, spread_punkte, kursreihe, slippage_punkte=0.5):
    netto = [mit_kosten(e, spread_punkte, slippage_punkte) for e in ergebnisse]
    n = len(netto) or 1
    gewinner = [x for x in netto if x > 0]
    verlierer = [x for x in netto if x <= 0]
    oe_gewinn = sum(gewinner) / len(gewinner) if gewinner else 0.0
    oe_verlust = sum(verlierer) / len(verlierer) if verlierer else 0.0
    ev = sum(netto) / n

    q = defaultdict(list)
    for e, x in zip(ergebnisse, netto):
        q[_quartal(e["tag"])].append(x)
    quartale = [{"quartal": k, "ev": sum(v) / len(v), "n": len(v)}
                for k, v in sorted(q.items())]
    schlechtestes_q_ev = min((qq["ev"] for qq in quartale), default=0.0)

    kum = hoch = 0.0
    max_rueck = 0.0
    for x in netto:
        kum += x
        hoch = max(hoch, kum)
        max_rueck = max(max_rueck, hoch - kum)

    sens = {}
    for faktor in (1.0, 1.5, 2.0):
        sn = [e["gv_punkte"] - spread_punkte * faktor - slippage_punkte for e in ergebnisse]
        sens["%.1f" % faktor] = sum(sn) / (len(sn) or 1)

    trefferquote = len(gewinner) / n
    noetig = _noetige_trefferquote(oe_gewinn, oe_verlust)
    genug_verlierer = len(verlierer) >= 10
    haelt_81 = (ev > 0 and schlechtestes_q_ev > 0 and genug_verlierer
                and trefferquote >= 0.75)
    if haelt_81:
        urteil = ("Ja - die 81-%%-Behauptung haelt: Trefferquote %.0f%%, EV %+.2f "
                  "Pkt/Runde, schlechtestes Quartal %+.2f, %d Verlierer."
                  % (trefferquote * 100, ev, schlechtestes_q_ev, len(verlierer)))
    else:
        grund = ("EV im Fenster <= 0" if ev <= 0 else
                 "schlechtestes Quartal <= 0" if schlechtestes_q_ev <= 0 else
                 "unter 10 Verlierer" if not genug_verlierer else
                 "Trefferquote unter 75%")
        urteil = ("Nein - die 81-%%-Behauptung faellt (%s): Trefferquote %.0f%%, "
                  "EV %+.2f, schlechtestes Quartal %+.2f, %d Verlierer."
                  % (grund, trefferquote * 100, ev, schlechtestes_q_ev, len(verlierer)))
    return {
        "trefferquote": trefferquote, "oe_gewinn": oe_gewinn, "oe_verlust": oe_verlust,
        "noetige_trefferquote": noetig, "ev_je_runde": ev,
        "verlierer": len(verlierer), "verlierer_warnung": not genug_verlierer,
        "quartale": quartale, "spread_sensitivitaet": sens,
        "max_rueckschlag": max_rueck,
        "mehrdeutige": sum(1 for e in ergebnisse if e["mehrdeutig"]),
        "kursreihe_start_ende": (kursreihe[0], kursreihe[-1]) if kursreihe else (None, None),
        "haelt_81": haelt_81, "urteil": urteil,
    }


def _okx_kerzen(inst, tage, cache_dir=None):
    """M15-Kerzen von OKX als [{zeit,o,h,l,c}], aufsteigend. Paginiert ueber
    history-candles (100 je Seite) und cached das Ergebnis als JSON, damit ein
    zweiter Lauf nicht wieder hunderte Seiten zieht. Die freie API reicht
    ~14 Monate zurueck (gemessen 2026-09-13, 400 Seiten = 40000 Kerzen)."""
    import json as _json
    import time as _time
    import sys as _sys
    from datetime import datetime, timezone
    from pathlib import Path as _P
    _sys.path.insert(0, str(_P(__file__).resolve().parent.parent / "xperp"))
    import okxf

    if cache_dir is not None:
        cache_pfad = _P(cache_dir) / (inst + "_M15.json")
        if cache_pfad.exists():
            roh = _json.loads(cache_pfad.read_text("utf-8"))
            return [{"zeit": datetime.fromtimestamp(r[0] / 1000, timezone.utc),
                     "o": r[1], "h": r[2], "l": r[3], "c": r[4]}
                    for r in roh]

    alle, nach = [], ""
    from urllib.parse import urlencode
    while True:
        p = "/api/v5/market/history-candles?" + urlencode(
            {"instId": inst, "bar": "15m", "limit": 100})
        if nach:
            p += "&after=" + nach
        d = okxf._mit_wiederholung(p)
        if not d:
            break
        r = [[int(x[0])] + [float(v) for v in x[1:6]] for x in d]
        alle += r
        nach = str(min(x[0] for x in r))
        if (alle[0][0] - alle[-1][0]) / 86400000.0 >= tage:
            break
        _time.sleep(0.1)

    if cache_dir is not None:
        _P(cache_dir).mkdir(parents=True, exist_ok=True)
        cache_pfad = _P(cache_dir) / (inst + "_M15.json")
        cache_pfad.write_text(_json.dumps(alle), "utf-8")

    return [{"zeit": datetime.fromtimestamp(r[0] / 1000, timezone.utc),
             "o": r[1], "h": r[2], "l": r[3], "c": r[4]}
            for r in alle]


def _lauf_instrument(w, key, jahre, modell, cache_dir, live=False):
    from datetime import datetime, timezone
    konf = w["instrumente"][key]
    bis = datetime.now(timezone.utc)
    tage = min(365 * jahre, 420)   # freie OKX-Historie ~14 Monate
    kerzen = _okx_kerzen(konf["okx"], tage, cache_dir)
    ergebnisse = []
    for tag, sk in sessions_gruppieren(kerzen, konf):
        r = simuliere_session(sk, konf, tag, w, modell)
        if r:
            ergebnisse.append(r)
    kursreihe = [k["c"] for k in kerzen]
    return bericht(ergebnisse, konf, konf["spread_punkte"], kursreihe), len(ergebnisse)


def _drucke_bericht(key, modell, b, n):
    print("=== %s | Einstiegsmodell: %s | %d Sessions ===" % (key, modell, n))
    print("  Trefferquote beobachtet %.1f%%   noetig (Break-even) %.1f%%"
          % (b["trefferquote"] * 100, b["noetige_trefferquote"] * 100))
    print("  Ø Gewinn %+.2f Pkt   Ø Verlust %+.2f Pkt   EV %+.3f Pkt/Runde"
          % (b["oe_gewinn"], b["oe_verlust"], b["ev_je_runde"]))
    print("  Verlierer %d%s   mehrdeutige Kerzen %d   max. Rueckschlag %.1f Pkt"
          % (b["verlierer"], "  << WARNUNG < 10" if b["verlierer_warnung"] else "",
             b["mehrdeutige"], b["max_rueckschlag"]))
    print("  Quartale:")
    for q in b["quartale"]:
        print("    %-8s EV %+.3f  (n=%d)" % (q["quartal"], q["ev"], q["n"]))
    print("  Spread-Sensitivitaet  1.0x %+.3f  1.5x %+.3f  2.0x %+.3f"
          % (b["spread_sensitivitaet"]["1.0"], b["spread_sensitivitaet"]["1.5"],
             b["spread_sensitivitaet"]["2.0"]))
    print("  URTEIL: %s" % b["urteil"])
    print()


def main(argv=None):
    import argparse
    import json as _json
    from pathlib import Path as _P
    import sys as _sys
    if hasattr(_sys.stdout, "reconfigure"):
        _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser()
    p.add_argument("--instrument", default="alle")
    p.add_argument("--jahre", type=int, default=2)
    p.add_argument("--modell", default="beide",
                   choices=("schluss", "naechste_eroeffnung", "beide"))
    p.add_argument("--raster", action="store_true")
    p.add_argument("--cache", default=str(_P(__file__).resolve().parent / "daten"))
    a = p.parse_args(argv)

    w = _json.loads((_P(__file__).resolve().parent / "wachen.json").read_text("utf-8"))
    cache_dir = _P(a.cache)
    keys = list(w["instrumente"]) if a.instrument == "alle" else [a.instrument]
    modelle = (["schluss", "naechste_eroeffnung"] if a.modell == "beide" else [a.modell])

    raster_ziel_k = [1.0, 1.5, 2.0, 2.5, 3.0]
    for key in keys:
        for modell in modelle:
            if a.raster:
                for k in raster_ziel_k:
                    w2 = dict(w, ziel_modus="r_vielfaches", ziel_k=k)
                    b, n = _lauf_instrument(w2, key, a.jahre, modell, cache_dir)
                    print("[Raster k=%.1f] " % k, end="")
                    _drucke_bericht(key, modell, b, n)
            else:
                b, n = _lauf_instrument(w, key, a.jahre, modell, cache_dir)
                _drucke_bericht(key, modell, b, n)


if __name__ == "__main__":
    main()

"""Gegenprobe der beiden Empfehlungen aus backtest-optimierung-2026-09-21.md
auf einem ZWEITEN, unabhaengigen Fenster: 4H-Kerzen.

Fenster: daten/backtest_kerzen/{BTC,ETH,SOL}-USDC_4H.json (je 2379 Kerzen ab
21.08.2025). Varianten: macd_mtf BASE gegen hist1+4, squeeze BASE gegen
laenge30. Nur long, netto 0,10 %/Seite.

Vorgehen wie bt_varianten_fast.py: Indikator-Arrays einmal je Instrument
vorrechnen (dieselben ti_indikatoren-Funktionen), Einstiegs-/Ausstiegslogik aus
<spur>/handeln.py ueber den PFAD (pruefe_ausstiege + _einstieg). Der Unterschied
zum Treiber: die Kerzen kommen NICHT aus kerzen_holen (Live-Abruf), sondern
direkt aus den 4H-JSONs.

Zusaetzlich: Verifikation, dass die vorberechneten Indikator-Arrays gegen die
schrittweise Rechnung der Spur stimmen (>= 20 Stichproben-Indizes je Spur).

Rein lesend: SCHREIBEN=False, journal abgefangen, keine wachen.json, kein
Scharfschalten, kein git commit.
"""
import importlib.util, json, os, statistics, sys

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
sys.path.insert(0, HANDEL)

import backtest_prognose as m
import bt_varianten_fast as btv

CACHE = os.path.join(HANDEL, "daten", "backtest_kerzen")
GEBUEHR = 0.1  # netto 0,10 %/Seite


def lade_4h(instrumente):
    """4H-JSONs direkt als kerzen je Instrument laden (aufsteigend)."""
    kerzen = {}
    for inst in instrumente:
        datei = os.path.join(CACHE, "%s_4H.json" % inst)
        if not os.path.exists(datei):
            raise SystemExit("FEHLER: %s fehlt" % datei)
        with open(datei, encoding="utf-8") as f:
            k = json.load(f)
        kerzen[inst] = [r if len(r) == 6 else r + [0.0] for r in k]
    return kerzen


def vorwaerts_runden_4h(spur, signal_fn, kerzen):
    """Gleiche Schleife wie btv.vorwaerts_runden, aber mit vorgegebenen
    Kerzen (4H-JSONs) statt kerzen_holen-Abruf."""
    h = btv.spur_modul(spur)
    w = h.lade_wachen()
    h.SCHREIBEN = False
    h.journal = lambda **f: None
    z = {"positionen": [], "modus": "papier", "letzter_lauf": None,
         "verluste_usd": 0.0}
    offen = {}
    runden = []
    mindest = w.get("mindest_kerzen", 300)
    laenge = min(len(k) for k in kerzen.values())

    for i in range(mindest, laenge):
        for inst, alle in kerzen.items():
            k = alle[:i + 1]
            vorher = {id(p): p for p in z["positionen"]}
            h.pruefe_ausstiege(z, k, w, nur=inst)
            nachher = {id(p) for p in z["positionen"]}
            for pid, p in vorher.items():
                if pid not in nachher and pid in offen:
                    e = offen.pop(pid)
                    kurs = k[-1][4]
                    vz = 1 if e["seite"] == "long" else -1
                    roh = (kurs - e["einstieg"]) / e["einstieg"] * 100.0 * vz
                    runden.append({
                        "inst": inst, "seite": e["seite"],
                        "einstieg": e["einstieg"], "ausstieg": kurs,
                        "nominal": e["nominal"], "stop_pct": e["stop_pct"],
                        "brutto_pct": roh, "netto_pct": roh - 2 * GEBUEHR,
                        "gv_netto": e["nominal"] * (roh - 2 * GEBUEHR) / 100.0,
                        "ein_ts": e["ts"], "aus_ts": k[-1][0],
                        "stunden": (k[-1][0] - e["ts"]) / 3600000.0,
                    })
            vorher_ids = {id(p) for p in z["positionen"]}
            if signal_fn(inst, k, len(k) - 1) == "long":
                btv._einstieg(inst, k, z, w, 1.0, h)
            for p in z["positionen"]:
                if id(p) not in vorher_ids:
                    offen[id(p)] = {"seite": p["seite"], "einstieg": p["einstieg"],
                                    "nominal": p["nominal"],
                                    "stop_pct": p["stop_pct"], "ts": k[-1][0]}
    return runden, len(z["positionen"])


def kennzahlen(runden, offen=0):
    return btv.kennzahlen(runden, offen)


# --- Verifikation: Vorberechnung gegen schrittweise Rechnung der Spur ------

def verifiziere(spur, kerzen, prep_fn, sig_fn, stichproben=25):
    """Vergleiche vorberechnetes Signal mit der schrittweisen signal() der
    Spur an stichproben Indizes. Nenne Trefferzahl."""
    h = btv.spur_modul(spur)
    prep = prep_fn(kerzen)
    insts = list(kerzen.keys())
    mindest = h.lade_wachen().get("mindest_kerzen", 300)
    laenge = min(len(k) for k in kerzen.values())
    # gleichmaessig verteilte Stichproben-Indizes ueber den Laufbereich
    indizes = [round(mindest + (laenge - mindest - 1) * t / (stichproben - 1))
               for t in range(stichproben)]
    treffer = 0
    abw = []
    for idx in indizes:
        inst = insts[idx % len(insts)]
        k = kerzen[inst][:idx + 1]
        vor = sig_fn(inst, k, idx)  # vorberechnet
        # schrittweise: echte signal() der Spur auf dem Ausschnitt
        echt = h.signal(k, idx)
        # normalisiere: wir pruefen nur die long-Seite
        vor_long = 1 if vor == "long" else 0
        echt_long = 1 if echt == "long" else 0
        if vor_long == echt_long:
            treffer += 1
        else:
            abw.append((idx, inst, vor, echt))
    return treffer, len(indizes), abw


def main():
    print("=== Gegenprobe 4H (long, netto 0,10%%/Seite) ===")
    print("Fenster: daten/backtest_kerzen/*_4H.json, je 2379 Kerzen ab 21.08.2025\n")

    ergebnis = {}

    # --- macd_mtf ---
    print("--- macd_mtf ---")
    h = btv.spur_modul("macd_mtf")
    w = h.lade_wachen()
    kerzen = lade_4h(w["instrumente"])
    print("  Instrumente:", ", ".join(kerzen.keys()), "| Kerzen je Inst:", len(list(kerzen.values())[0]))

    # Verifikation BASE (die Spur implementiert BASE schrittweise)
    tr, n, abw = verifiziere("macd_mtf", kerzen,
                             lambda k: btv.macd_prep(k),
                             lambda inst, k, idx: btv.macd_signal(btv.macd_prep(kerzen))(inst, k, idx))
    print("  Verifikation BASE (vorberechnet vs. schrittweise): %d/%d Treffer" % (tr, n))
    if abw:
        print("    Abweichungen:", abw[:5])

    varianten_macd = [
        ("BASE", btv.macd_prep(kerzen), dict()),
        ("hist1+4", btv.macd_prep(kerzen), dict(hist_mehrere=True)),
    ]
    for name, prep, kw in varianten_macd:
        fn = btv.macd_signal(prep, **kw)
        r, offen = vorwaerts_runden_4h("macd_mtf", fn, kerzen)
        k = kennzahlen(r, offen)
        ergebnis["macd_mtf/" + name] = k
        print("  %-9s n=%-4d quote %5.1f%% netto %+7.3f%%/R summe %+8.2f%% dd %8.2f"
              % (name, k["n"], k["quote"], k["netto_pct_mittel"],
                 k["netto_pct_summe"], k["max_ruecklauf_usd"]))

    # --- squeeze ---
    print("\n--- squeeze ---")
    h = btv.spur_modul("squeeze")
    w = h.lade_wachen()
    kerzen = lade_4h(w["instrumente"])
    print("  Instrumente:", ", ".join(kerzen.keys()), "| Kerzen je Inst:", len(list(kerzen.values())[0]))

    tr, n, abw = verifiziere("squeeze", kerzen,
                             lambda k: btv.squeeze_prep(k),
                             lambda inst, k, idx: btv.squeeze_signal(btv.squeeze_prep(kerzen))(inst, k, idx))
    print("  Verifikation BASE (vorberechnet vs. schrittweise): %d/%d Treffer" % (tr, n))
    if abw:
        print("    Abweichungen:", abw[:5])

    varianten_sq = [
        ("BASE", btv.squeeze_prep(kerzen), dict()),
        ("laenge30", btv.squeeze_prep(kerzen, laenge=30), dict()),
    ]
    for name, prep, kw in varianten_sq:
        fn = btv.squeeze_signal(prep, **kw)
        r, offen = vorwaerts_runden_4h("squeeze", fn, kerzen)
        k = kennzahlen(r, offen)
        ergebnis["squeeze/" + name] = k
        print("  %-9s n=%-4d quote %5.1f%% netto %+7.3f%%/R summe %+8.2f%% dd %8.2f"
              % (name, k["n"], k["quote"], k["netto_pct_mittel"],
                 k["netto_pct_summe"], k["max_ruecklauf_usd"]))

    out = os.path.join(HIER, "4h_gegenprobe.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(ergebnis, f, indent=1, ensure_ascii=False)
    print("\ngeschrieben:", out)


if __name__ == "__main__":
    main()
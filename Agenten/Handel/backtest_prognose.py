"""Backtest der vier Prognose-Spuren auf echten Kerzen - zur Optimierung.

FAEHRT DIE SPUREN SELBST: signal(), pruefe_einstieg() und pruefe_ausstiege()
werden aus <spur>/handeln.py ueber den PFAD geladen und auf historische Kerzen
gestellt. Keine Nachbildung - eine zweite Umsetzung waere eine zweite Wahrheit,
und optimiert waere dann die Nachbildung, nicht die Spur.

Spuren: squeeze, wavetrend, macd_mtf, supertrend.
(mosaic hat eine eigene Mehrzeitrahmen-Mechanik und bleibt aussen vor.)

KERZEN: /api/v5/market/history-candles blaettert mit 'after' rueckwaerts -
damit reichen die Daten weiter zurueck als die 1440 Stunden (60 Tage) des
oeffentlichen /market/candles. Gemessen 21.09.2026: 3000 Stundenkerzen
(ab 19.05.2026). Bei 4H entsprechend weiter.

KOSTEN: die vier wachen.json tragen KEINE Gebuehr. Der Backtest nimmt sie
deshalb als Parameter (--gebuehr, Standard 0.10 % je Seite = OKX Spot Taker)
und weist immer brutto UND netto aus.

AUSSTIEGSPRUEFUNG: wie in der Spur gegen den SCHLUSSKURS, nicht gegen
Hoch/Tief der Kerze. Ein intrabar getroffener Stop wird also erst am
Kerzenschluss gebucht - dieselbe Naeherung, die die Spur im Betrieb macht.

SCHREIBT NICHTS in die Spurenordner: SCHREIBEN=False, journal() abgefangen,
Zustand nur im Speicher.

Aufruf:
    python backtest_prognose.py                       alle vier, 1H/4H Standard
    python backtest_prognose.py --spur squeeze
    python backtest_prognose.py --kerzen 3000 --gebuehr 0.1
    python backtest_prognose.py --raster                Parametersuche
    python backtest_prognose.py --json bericht.json
"""

import argparse
import datetime as dt
import importlib.util
import json
import os
import statistics
import sys
import time
import urllib.parse

HIER = os.path.dirname(os.path.abspath(__file__))
SPUREN = ("squeeze", "wavetrend", "macd_mtf", "supertrend")


def lade(name, pfad):
    """Ein Modul ueber den PFAD laden, nicht ueber sys.path."""
    s = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def _okx():
    p = os.path.join(HIER, "scanner")
    if p not in sys.path:
        sys.path.insert(0, p)
    import okx
    return okx


CACHE = os.path.join(HIER, "daten", "backtest_kerzen")


def kerzen_holen(inst, bar, stueck):
    """Historische Kerzen, [ts, o, h, l, c, v], aufsteigend.

    history-candles gibt 100 je Abruf und blaettert mit 'after' rueckwaerts.
    Die Grenze ist eng (HTTP 429 'Too Many Requests'), deshalb 0,25 s Pause je
    Seite und ein Cache auf der Platte: derselbe Lauf zweimal fragt nicht
    zweimal. Der Cache haelt die HISTORIE, nicht die letzte Kerze - fuer den
    Backtest ist das richtig, fuer den Betrieb waere es falsch.
    """
    os.makedirs(CACHE, exist_ok=True)
    datei = os.path.join(CACHE, "%s_%s.json" % (inst, bar))
    roh = {}
    if os.path.exists(datei):
        try:
            with open(datei, encoding="utf-8") as f:
                for r in json.load(f):
                    roh[int(r[0])] = r
        except (OSError, ValueError):
            roh = {}
    if len(roh) >= stueck:
        return [roh[t] for t in sorted(roh)][-stueck:]

    okx = _okx()
    grenze = min(roh) if roh else None
    while len(roh) < stueck:
        time.sleep(0.25)
        w = {"instId": inst, "bar": bar, "limit": "100"}
        if grenze:
            w["after"] = str(grenze)
        pfad = "/api/v5/market/history-candles?" + urllib.parse.urlencode(w)
        seite = okx._mit_wiederholung(pfad)
        if not seite:
            break
        neu = min(int(r[0]) for r in seite)
        for r in seite:
            roh[int(r[0])] = [int(r[0])] + [float(x) for x in r[1:6]]
        if grenze is not None and neu >= grenze:
            break
        grenze = neu
    reihen = [roh[t] for t in sorted(roh)]
    try:
        with open(datei, "w", encoding="utf-8") as f:
            json.dump(reihen, f)
    except OSError:
        pass
    return reihen[-stueck:]


def spur_modul(spur):
    return lade("bt_%s" % spur, os.path.join(HIER, spur, "handeln.py"))


def lauf(spur, kerzen_je_inst, w, gebuehr_pct, modul=None):
    """Einen Walk ueber die Historie fahren, Runden zurueckgeben.

    kerzen_je_inst: {inst: [kerzen...]} - die Spur bekommt je Schritt nur die
    Kerzen bis zum aktuellen Index, sieht also nie die Zukunft.
    """
    h = modul or spur_modul(spur)
    h.SCHREIBEN = False
    runden = []
    offen = {}  # id(position) -> Einstiegsdaten

    gesammelt = []
    # Dieselbe Rechnung wie im Kern: der Ausstieg geschieht auf dem
    # BERUEHRTEN Kurs (replay.Beruehrungsjournal). Eine berichtigte
    # Journalzeile allein reicht hier NICHT - die Runde unten liest
    # `k[-1][4]`, den Kerzenschluss. Die Huelle fuehrt deshalb den Kurs
    # der Marke mit (`marke_je_inst`), damit Journal UND Runde
    # dieselbe Zahl tragen.
    import replay
    kerzen_schritt = {}
    journal_huelle = replay.Beruehrungsjournal(
        kerzen_schritt, lambda **f: gesammelt.append(f))
    h.journal = journal_huelle

    z = {"positionen": [], "modus": "papier", "letzter_lauf": None,
         "verluste_usd": 0.0}
    mindest = w.get("mindest_kerzen", 300)
    laenge = min(len(k) for k in kerzen_je_inst.values())

    for i in range(mindest, laenge):
        # Die Markenzeilen des VOR-Schritts verwerfen (je Schritt frisch),
        # damit keine Zeile einer Runde zugeschlagen wird, die nicht in
        # diesem Schritt geschlossen wurde. Geleert wird am SCHRITTANFANG,
        # nicht je Instrument: schliesst die Spur beim Durchgang von A eine
        # Position von B, muss die Zeile fuer B noch da sein.
        journal_huelle.schritt_anfang()
        for inst, alle in kerzen_je_inst.items():
            k = alle[:i + 1]
            # Die Kerze DIESES Schritts fuer die Journal-Huelle.
            kerzen_schritt[inst] = k[-1]
            vorher = {id(p): p for p in z["positionen"]}
            h.pruefe_ausstiege(z, k, w, nur=inst)
            # T-202/T-177 (04.10.2026): der Ausloeser der Spuren ist der
            # KERZENschluss. Eine Kerze, die Stop oder Ziel nur mit dem Docht
            # streift und darueber schliesst, loest dort nichts aus - der
            # Replay bildet diesen Ausstieg aber ab, sonst entstuende im
            # Backtest eine Position, die es im Betrieb nie gaebe.
            #
            # DIESER Aufruf fehlte hier und ist die ganze Ursache der
            # Gegenprobe-Abweichung: replay.lauf_a rief die Regel seit dem
            # 01.10.2026, dieser Weg nie. Ab Runde 2 schieden die Wege: der
            # alte schloss eine Docht-Position, der neue behielt sie, danach
            # unterschieden sich auch die naechsten Einstiege (gemessen an
            # squeeze, Fenster 700 Kerzen).
            #
            # Die Reihenfolge ist dieselbe wie in lauf_a: erst pruefen, dann
            # die Docht-Positionen schliessen, dann die Ausstiege buchen.
            replay.docht_ausstiege_anwenden(
                z, k[-1], inst, journal_huelle,
                dt.datetime.fromtimestamp(k[-1][0] / 1000.0,
                                         dt.timezone.utc)
                .isoformat(timespec="seconds"))
            nachher = {id(p) for p in z["positionen"]}
            for pid, p in vorher.items():
                if pid not in nachher and pid in offen:
                    e = offen.pop(pid)
                    # Der Ausstiegskurs der Spur steht im Journal: sitzt
                    # er auf einer Marke, gilt DIESER Kurs (nicht der
                    # Schluss der Kerze). Je geschlossener Position EINE
                    # Markenzeile - geholt ueber die `pos_id`, nicht blind
                    # in Zeilenreihenfolge: die Spuren schreiben erst die
                    # schlussgetriggerten und dann die Docht-Ausstiege, die
                    # Runde entsteht aber in der BUCHreihenfolge (04.10.2026).
                    marke = journal_huelle.nimm_marke(inst, p.get("pos_id"))
                    kurs = k[-1][4] if marke is None else marke
                    vz = 1 if e["seite"] == "long" else -1
                    roh_pct = (kurs - e["einstieg"]) / e["einstieg"] * 100.0 * vz
                    runden.append({
                        "inst": inst, "seite": e["seite"],
                        "einstieg": e["einstieg"], "ausstieg": kurs,
                        "nominal": e["nominal"], "stop_pct": e["stop_pct"],
                        "brutto_pct": roh_pct,
                        "netto_pct": roh_pct - 2 * gebuehr_pct,
                        "gv_brutto": e["nominal"] * roh_pct / 100.0,
                        "gv_netto": e["nominal"] * (roh_pct - 2 * gebuehr_pct) / 100.0,
                        "ein_ts": e["ts"], "aus_ts": k[-1][0],
                        "stunden": (k[-1][0] - e["ts"]) / 3600000.0,
                    })
            vorher_ids = {id(p) for p in z["positionen"]}
            h.pruefe_einstieg(inst, k, z, w, 1.0)
            for p in z["positionen"]:
                if id(p) not in vorher_ids:
                    offen[id(p)] = {"seite": p["seite"], "einstieg": p["einstieg"],
                                    "nominal": p["nominal"],
                                    "stop_pct": p["stop_pct"], "ts": k[-1][0]}
    return runden, len(z["positionen"])


def kennzahlen(runden, offen=0):
    if not runden:
        return {"n": 0, "offen": offen}
    netto = [r["netto_pct"] for r in runden]
    brutto = [r["brutto_pct"] for r in runden]
    gv = [r["gv_netto"] for r in runden]
    treffer = sum(1 for x in netto if x > 0)
    # Kapitalkurve in USD fuer den Ruecklauf
    kum, hoch, dd = 0.0, 0.0, 0.0
    for x in gv:
        kum += x
        hoch = max(hoch, kum)
        dd = min(dd, kum - hoch)
    return {
        "n": len(runden), "offen": offen,
        "quote": round(100.0 * treffer / len(runden), 1),
        "brutto_pct_mittel": round(statistics.fmean(brutto), 3),
        "netto_pct_mittel": round(statistics.fmean(netto), 3),
        "netto_pct_summe": round(sum(netto), 2),
        "gv_netto_usd": round(sum(gv), 2),
        "max_ruecklauf_usd": round(dd, 2),
        "stunden_median": round(statistics.median(r["stunden"] for r in runden), 1),
        "streuung_pct": round(statistics.pstdev(netto), 3) if len(netto) > 1 else 0.0,
    }


def takt_fuer(spur, w, override=None):
    return override or w.get("kerzen_takt", "1H")


def fahre(spur, anzahl, gebuehr, takt=None, wachen_patch=None, instrumente=None,
          nur_seite=None):
    h = spur_modul(spur)
    w = h.lade_wachen()
    if wachen_patch:
        w = dict(w)
        w.update(wachen_patch)
    bar = takt_fuer(spur, w, takt)
    insts = instrumente or w["instrumente"]
    kerzen = {}
    for inst in insts:
        k = kerzen_holen(inst, bar, anzahl)
        if len(k) > w.get("mindest_kerzen", 300) + 20:
            kerzen[inst] = k
    if not kerzen:
        return None, None
    if nur_seite:
        # Richtungsfilter als SEAM ueber signal(): die Spur bleibt unveraendert,
        # der Backtest sieht nur Signale der gewaehlten Seite. supertrend gibt
        # (seite, linie) zurueck, die anderen einen String.
        echt = h.signal

        def gefiltert(k, idx, _e=echt, _s=nur_seite):
            sig = _e(k, idx)
            if sig is None:
                return None
            seite = sig[0] if isinstance(sig, tuple) else sig
            return sig if seite == _s else None
        h.signal = gefiltert
    try:
        runden, offen = lauf(spur, kerzen, w, gebuehr, modul=h)
    finally:
        if nur_seite:
            h.signal = echt
    return runden, kennzahlen(runden, offen)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spur", choices=SPUREN)
    ap.add_argument("--kerzen", type=int, default=3000)
    ap.add_argument("--gebuehr", type=float, default=0.1,
                    help="Prozent je Seite (Standard 0.10 = OKX Spot Taker)")
    ap.add_argument("--takt", help="Kerzentakt erzwingen (1H, 4H, 1D)")
    ap.add_argument("--json", help="Ergebnis als JSON schreiben")
    a = ap.parse_args()

    spuren = [a.spur] if a.spur else list(SPUREN)
    aus = {}
    for s in spuren:
        try:
            runden, k = fahre(s, a.kerzen, a.gebuehr, a.takt)
        except Exception as e:
            print("%-12s FEHLER %s" % (s, e))
            continue
        if k is None:
            print("%-12s keine Kerzen" % s)
            continue
        aus[s] = {"kennzahlen": k, "runden": runden}
        if k["n"] == 0:
            print("%-12s 0 Runden (%d offen)" % (s, k["offen"]))
            continue
        print("%-12s n=%-3d Quote %5.1f%%  netto %+6.3f%%/Runde  "
              "Summe %+7.2f%%  G/V %+8.2f USD  Ruecklauf %8.2f  "
              "Median %5.1f h  offen %d"
              % (s, k["n"], k["quote"], k["netto_pct_mittel"],
                 k["netto_pct_summe"], k["gv_netto_usd"],
                 k["max_ruecklauf_usd"], k["stunden_median"], k["offen"]))

    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump({"erzeugt": dt.datetime.now(dt.UTC).isoformat(),
                       "kerzen": a.kerzen, "gebuehr_pct": a.gebuehr,
                       "ergebnis": aus}, f, indent=2, ensure_ascii=False)
        print("geschrieben:", a.json)


if __name__ == "__main__":
    main()

"""Ruecktest-Engine fuer Spur 2 (XPERP), Trend-Modus. Ruft die bestehenden
PUREN Rechenfunktionen aus xperp/ direkt auf (siehe Spec, Architektur-
entscheidung) statt Signal-/Groessen-/Trailing-Logik zweimal zu schreiben.

Nur Standardbibliothek.
"""

import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent
_XPERP = WURZEL.parent / "xperp"
_HANDEL = WURZEL.parent
for _p in (_HANDEL, _XPERP, WURZEL):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import auswahl  # noqa: E402
import bot  # noqa: E402
import cvd  # noqa: E402
import indikatoren  # noqa: E402
import okxf  # noqa: E402
import trailing as trailing_modul  # noqa: E402
import wachen_xperp as wx  # noqa: E402
from signal_wechsel import ERLAEUT, zugelassen  # noqa: E402

MIN_KERZEN_4H = auswahl.MIN_KERZEN


def schnitt_bis(kerzen, zeit_ms):
    """Alle Kerzen mit ts <= zeit_ms - kein Vorgriff auf die Zukunft."""
    return [k for k in kerzen if k[0] <= zeit_ms]


def _abgeschlossene_tageskerzen(kerzen, zeit_ms):
    """Nur 1D-Kerzen, die bei zeit_ms bereits geschlossen waren.

    OKX-1D-Kerzen enthalten Hoch/Tief des ganzen laufenden Tages; nur auf
    ihren Zeitstempel zu schauen wäre ein Vorgriff auf den späteren Tagespfad.
    """
    return [k for k in kerzen if k[0] + 86_400_000 <= zeit_ms]


def _umsatz_24h(k4, ctval):
    """Punkt-in-Zeit-Umsatz aus den sechs jüngsten abgeschlossenen 4H-Kerzen."""
    return sum(k[5] * ctval * k[4] for k in k4[-6:])


def rangliste_schritt(universum, kerzen_4h_je_inst, kerzen_1d_je_inst,
                      umsatz_je_inst, zeit_ms, ctval_je_inst=None):
    """Kennzahlen+Punkte aller Instrumente mit genuegend Historie BIS zeit_ms.

    Wie auswahl.sammle(): dieselben Kennzahlen auf höchstens 300
    abgeschlossenen 4H-Kerzen. Umsatz kommt ebenfalls aus dieser historischen
    Reihe; umsatz_je_inst bleibt nur der Kompatibilitätsweg für Aufrufer ohne
    Kontraktwert (Tests/Bestandsaufrufe).
    """
    aus = []
    for x in universum:
        iid = x["instId"]
        k4 = schnitt_bis(kerzen_4h_je_inst.get(iid, []), zeit_ms)[-300:]
        if len(k4) < MIN_KERZEN_4H:
            continue
        z = auswahl.kennzahlen(k4)
        kt = _abgeschlossene_tageskerzen(kerzen_1d_je_inst.get(iid, []),
                                         zeit_ms)
        if len(kt) >= 14:
            z["mae_long"], z["mae_short"] = auswahl.mae_tage(kt, 7)
        kat = auswahl.KATEGORIEN[x["kategorie"]]
        if ctval_je_inst is None:
            umsatz = umsatz_je_inst.get(iid, 0.0)
        else:
            umsatz = _umsatz_24h(k4, ctval_je_inst.get(iid, 0.0))
        z.update(basis=x["basis"], instId=iid, umsatz=umsatz,
                 kategorie=x["kategorie"], vola_tor=kat["vola_tor"],
                 punkte=auswahl.bewerte(z, umsatz, kat["umsatz_bezug"]))
        aus.append(z)
    return aus


def kandidaten_schritt(werte, w, anzahl=6):
    """Die besten Werte je Richtung, die ihre Tore bestehen.

    1:1 die Filterkette aus handeln.kandidaten() - Vola-Tor, Familie aktiv,
    Umsatz-Bezug der Familie, Hebel-Deckel >= wx.hebel_mindest().
    """
    aus = []
    for seite in ("long", "short"):
        beste = sorted(werte, key=lambda x: -x["punkte"][seite])
        for x in beste:
            if len(aus) >= anzahl * 2:
                break
            if x["vola"] > x["vola_tor"]:
                continue
            fam = (w.get("familien") or {}).get(x["kategorie"], {})
            if not fam.get("aktiv", True):
                continue
            if x["umsatz"] < fam.get("umsatz_bezug_usd",
                                     w["min_umsatz_24h_usd"]):
                continue
            mae = x["mae_short"] if seite == "short" else x["mae_long"]
            deckel = auswahl.hebel_deckel(mae)
            if deckel < wx.hebel_mindest(w, x["kategorie"]):
                continue
            aus.append({"basis": x["basis"], "instId": x["instId"],
                        "seite": seite, "kategorie": x["kategorie"],
                        "punkte": x["punkte"][seite], "deckel": deckel})
    return aus


def _cvd_neutral():
    return cvd.leer("Ruecktest: CVD-4h nicht historisch verfuegbar (Spec-"
                    "Abgrenzung, OKX-Endpunkt deckt nur ~16 Tage ab)")


def pruefe_einstieg(kandidat, w, instr_je_basis, k4_je_inst, k1d_je_inst,
                    offene_positionen, zustand, zeit_ms, jetzt_dt,
                    satz_bis=None):
    """Die Einstiegskette aus handeln.pruefe_einstiege(), Schritt fuer Schritt
    auf einen Kandidaten zu einem historischen Zeitpunkt angewendet. Gibt eine
    neue Position oder None zurueck. satz_bis(inst, zeit_ms) liefert den
    historischen Funding-Satz fuer die Pflichtzahlen; None = okxf.funding.
    """
    if len(offene_positionen) >= w["max_offene_anlaeufe"]:
        return None
    if zugelassen(zustand, w, kandidat["basis"], kandidat["seite"]) is not ERLAEUT:
        return None
    if kandidat["basis"] in {p.get("basis") for p in offene_positionen}:
        return None
    letzter_stop = (zustand.get("letzte_stops") or {}).get(kandidat["basis"])
    if letzter_stop is not None and (jetzt_dt - letzter_stop).days < w.get(
            "abklingzeit_tage", 3):
        return None
    if wx.wochenende_sperrt(w, jetzt_dt) and kandidat["kategorie"] in (
            "aktie", "rohstoff"):
        return None
    fam = wx.familien_belegung(offene_positionen, w).get(kandidat["kategorie"])
    if fam and fam["voll"]:
        return None

    instr = instr_je_basis.get(kandidat["basis"])
    k4 = schnitt_bis(k4_je_inst.get(kandidat["instId"], []), zeit_ms)[-300:]
    if instr is None or len(k4) < 60:
        return None
    lage = indikatoren.lage(k4, inst=kandidat["instId"], cvd_lage=_cvd_neutral())
    if lage["signal"] != kandidat["seite"]:
        return None
    atr = lage["atr"]
    if not atr:
        return None

    seite = kandidat["seite"]
    vz = 1 if seite == "long" else -1
    einstieg = okxf.auf_tick(instr, lage["kurs"]
                             - vz * w["einstieg_atr_abschlag"] * atr)
    stop = okxf.auf_tick(instr, einstieg - vz * w["stop_atr_faktor"] * atr)
    ziel = okxf.auf_tick(instr, einstieg + vz * w["ziel_atr_faktor"] * atr)

    smax = wx.stop_max_pct(w, kandidat["kategorie"])
    if smax is not None and abs(einstieg - stop) / einstieg * 100.0 > smax:
        return None
    wf = wx.fuer_familie(w, kandidat["kategorie"])

    g = bot.groesse(wf, instr, einstieg, stop, seite, kandidat["deckel"])
    if not g:
        return None
    if (sum(float(p.get("margin") or 0.0) for p in offene_positionen)
            + g["margin"] > w["max_margin_gesamt_usd"]):
        return None

    # pruefpflicht() greift live auf OKX zu: funding() fuer den Funding-Satz
    # und - ueber hebel_deckel() - auf die Tageskerzen (Seam
    # bot.tages_kerzen_quelle). Beides wird fuer die Dauer dieses einen
    # Aufrufs auf den historischen Stand zu zeit_ms umgeleitet; die
    # Pflichtzahlen selbst bleiben die EINE Rechnung aus bot.py.
    echt_funding = okxf.funding
    echt_seam = bot.tages_kerzen_quelle
    try:
        if satz_bis is not None:
            okxf.funding = lambda inst: satz_bis(inst, zeit_ms)
        bot.tages_kerzen_quelle = (
            lambda inst_id, n=300: _abgeschlossene_tageskerzen(
                k1d_je_inst.get(inst_id, []), zeit_ms))
        pflicht = bot.pruefpflicht(
            wf, instr, k4, seite, einstieg, stop, ziel, g["hebel"],
            stop_atr_f=w["stop_atr_faktor"], ziel_atr_f=w["ziel_atr_faktor"],
            still=True)
    finally:
        okxf.funding = echt_funding
        bot.tages_kerzen_quelle = echt_seam

    if not pflicht.get("traegt") or not pflicht.get("hebel_traegt"):
        return None

    return {"inst": kandidat["instId"], "basis": kandidat["basis"],
            "seite": seite, "kategorie": kandidat["kategorie"],
            "familie": kandidat["kategorie"],
            "einstieg": einstieg, "stop": stop, "ziel": ziel,
            "liq": g["liq"], "hebel": g["hebel"], "kontrakte": g["kontrakte"],
            "nominal": g["nominal"], "margin": g["margin"],
            "hoechstkurs": einstieg, "stop_id": "ruecktest",
            "eroeffnet_ts": zeit_ms, "letzte_funding_ts": zeit_ms,
            "funding_summe": 0.0}


def pruefe_ausstieg_1h(p, kerze_1h, w):
    """Ausstieg auf einer 1H-Kerze, danach Trailing-Nachfuehrung, wenn keiner
    greift. Gibt (grund, ausstiegspreis) oder (None, None).

    Die Boerse loest einen Stop beim Durchlaufen aus - ein Docht durch die
    Liquidationsmarke ist deshalb nur dann eine Liquidation, wenn die Kerze
    schon HINTER der Marke eroeffnet (Gap). Ebenso fuellt ein Stop bei einer
    Eroeffnung hinter dem Stop zum Eroeffnungskurs, nicht zum Stop-Preis.
    Ein vom Trailing verschobener Stop heisst 'trailing_stop'.
    """
    _, offen, hoch, tief, schluss, _ = kerze_1h
    lang = p["seite"] == "long"
    if lang:
        if offen <= p["liq"]:
            return "LIQUIDATION", offen
        if tief <= p["stop"]:
            return _stop_grund(p), min(offen, p["stop"])
        if hoch >= p["ziel"]:
            return "ziel", p["ziel"]
    else:
        if offen >= p["liq"]:
            return "LIQUIDATION", offen
        if hoch >= p["stop"]:
            return _stop_grund(p), max(offen, p["stop"])
        if tief <= p["ziel"]:
            return "ziel", p["ziel"]

    if not w.get("trailing_aktiv", True):
        return None, None
    trailing_modul.erst_hoch(p, schluss)
    kand, _grund = trailing_modul.kandidat(p, schluss, w, liq=p.get("liq"))
    if kand is not None:
        p["stop"] = kand["stop"]
        p["hoechstkurs"] = kand["hoechstkurs"]
        p["stop_nachgezogen"] = True
    return None, None


def _stop_grund(p):
    return "trailing_stop" if p.get("stop_nachgezogen") else "stop"


MAX_LUECKE_MS = 2 * 8 * 3_600_000      # laenger ohne neuen Satz = Cache veraltet


class FundingLuecke(Exception):
    """Keine (ausreichende) historische Funding-Reihe - nicht mit 0.0
    auffuellen. Dieselbe Haltung wie kraken_modell.FXLuecke."""


def satz_zu_zeitpunkt(saetze_je_inst, inst, zeit_ms):
    """Der zuletzt VOR (oder genau zu) zeit_ms veroeffentlichte Funding-Satz."""
    frueher = [s for s in saetze_je_inst.get(inst, []) if s[0] <= zeit_ms]
    if not frueher:
        raise FundingLuecke(
            "kein Funding-Satz vor Zeitpunkt %d fuer %s" % (zeit_ms, inst))
    return frueher[-1][1]


def funding_faellig(p, zeit_ms, saetze_je_inst):
    """Funding aller Abrechnungen in (letzte Buchung, zeit_ms]: Summe aus
    nominal * Satz je veroeffentlichter Abrechnung. Der Takt (1h/4h/8h) steht
    in den Daten - er wird nicht angenommen. Positiv = gezahlt (Long bei
    positivem Satz). p aendert sich erst, wenn gerechnet ist; eine
    FundingLuecke (Reihe beginnt nach der Eroeffnung oder endet lange vor
    zeit_ms) laesst p unberuehrt.
    """
    saetze = saetze_je_inst.get(p["inst"], [])
    if not saetze or saetze[0][0] > p["letzte_funding_ts"]:
        raise FundingLuecke(
            "Funding-Historie fuer %s beginnt nicht vor %d"
            % (p["inst"], p["letzte_funding_ts"]))
    if zeit_ms - saetze[-1][0] > MAX_LUECKE_MS:
        raise FundingLuecke(
            "Funding-Historie fuer %s endet bei %d, benoetigt bis %d"
            % (p["inst"], saetze[-1][0], zeit_ms))
    vz = 1 if p["seite"] == "long" else -1
    gesamt = sum(p["nominal"] * satz * vz for ts, satz in saetze
                 if p["letzte_funding_ts"] < ts <= zeit_ms)
    p["letzte_funding_ts"] = zeit_ms
    p["funding_summe"] = p.get("funding_summe", 0.0) + gesamt
    return gesamt


SCHRITT_MS = 4 * 3_600_000


def _ergebnis(p, kurs, w):
    """Bewegung des Nominals abzueglich Einstiegs- UND Ausstiegsgebuehr
    (2 x gebuehr_taker, wie bot.pruefpflicht() sie als Kosten ansetzt)."""
    vz = 1 if p["seite"] == "long" else -1
    bewegung = vz * (kurs - p["einstieg"]) / p["einstieg"]
    return p["nominal"] * bewegung - 2 * p["nominal"] * w["gebuehr_taker"]


def simuliere(universum, k4_je_inst, k1h_je_inst, k1d_je_inst,
              saetze_je_inst, umsatz_je_inst, instr_je_basis, w,
              start_ms, end_ms, werte_cache=None):
    """4H-Aussentakt (Rangliste/Einstieg), 1H-Innenaufloesung (Ausstieg,
    Trailing, Funding). Gibt die abgeschlossenen Runden zurueck.

    Entscheidungen zum Zeitpunkt t sehen nur ABGESCHLOSSENE 4H-Kerzen
    (ts <= t - 4H): die Kerze mit ts == t laeuft erst und ihr Schlusskurs ist
    noch nicht bekannt. Zum Ende offene Positionen werden nicht bewertet.
    ``werte_cache`` ({stand_ms: Rangliste}) ersetzt die Rangliste je Schritt
    durch vorgerechnete Werte; ein fehlender Stand ist ein KeyError (laut).
    """
    from datetime import datetime, timezone

    zustand, offene, runden = {}, [], []
    ctval_je_inst = {x["instId"]: float(instr_je_basis[x["basis"]]["ctVal"])
                     for x in universum if x["basis"] in instr_je_basis}

    def satz_bis(inst, zeit_ms):
        return satz_zu_zeitpunkt(saetze_je_inst, inst, zeit_ms)

    t = start_ms
    while t <= end_ms:
        stand = t - SCHRITT_MS
        jetzt_dt = datetime.fromtimestamp(t / 1000, tz=timezone.utc)

        if werte_cache is not None:
            werte = werte_cache[stand]
        else:
            werte = rangliste_schritt(universum, k4_je_inst, k1d_je_inst,
                                      umsatz_je_inst, stand,
                                      ctval_je_inst=ctval_je_inst)
        for kand in kandidaten_schritt(werte, w):
            if len(offene) >= w["max_offene_anlaeufe"]:
                break
            p = pruefe_einstieg(kand, w, instr_je_basis, k4_je_inst,
                                k1d_je_inst, offene, zustand, stand, jetzt_dt,
                                satz_bis=satz_bis)
            if p is not None:
                p["eroeffnet_ts"] = t
                p["letzte_funding_ts"] = t
                offene.append(p)

        for p in list(offene):
            for kerze in k1h_je_inst.get(p["inst"], []):
                if not (max(t, p["eroeffnet_ts"]) <= kerze[0]
                        < t + SCHRITT_MS):
                    continue
                funding_faellig(p, kerze[0], saetze_je_inst)
                grund, preis = pruefe_ausstieg_1h(p, kerze, w)
                if grund is None:
                    continue
                runden.append({
                    "inst": p["inst"], "basis": p["basis"],
                    "seite": p["seite"], "kategorie": p["kategorie"],
                    "einstieg": p["einstieg"], "ausstieg": preis,
                    "nominal": p["nominal"], "grund": grund,
                    "gv": _ergebnis(p, preis, w) - p["funding_summe"],
                    "funding_summe": p["funding_summe"],
                    "eroeffnet_ts": p["eroeffnet_ts"],
                    "geschlossen_ts": kerze[0]})
                offene.remove(p)
                if grund in ("stop", "LIQUIDATION"):
                    zustand.setdefault("letzte_stops", {})[p["basis"]] = (
                        datetime.fromtimestamp(kerze[0] / 1000,
                                               tz=timezone.utc))
                break
        t += SCHRITT_MS
    return runden


def bericht(runden):
    """Leistungsbericht fuer die AKTUELLE wachen.json - kein Vorschlag."""
    if not runden:
        return {"anzahl_runden": 0, "gv_gesamt": 0.0, "runden_je_grund": {},
                "trefferquote": None, "gewinnquote": None,
                "liquidationsanteil": 0.0,
                "groesster_ruecklauf_usd": 0.0, "je_familie": {},
                "funding_gesamt": 0.0}

    runden = sorted(runden, key=lambda r: r["geschlossen_ts"])
    je_grund, je_familie = {}, {}
    for r in runden:
        je_grund[r["grund"]] = je_grund.get(r["grund"], 0) + 1
        f = je_familie.setdefault(r["kategorie"], {"gv": 0.0, "n": 0})
        f["gv"] += r["gv"]
        f["n"] += 1

    kapital = hoch = ruecklauf = 0.0
    for r in runden:
        kapital += r["gv"]
        hoch = max(hoch, kapital)
        ruecklauf = max(ruecklauf, hoch - kapital)

    n = len(runden)
    return {
        "anzahl_runden": n,
        "gv_gesamt": sum(r["gv"] for r in runden),
        "runden_je_grund": je_grund,
        "trefferquote": je_grund.get("ziel", 0) / n,
        "gewinnquote": sum(1 for r in runden if r["gv"] > 0) / n,
        "liquidationsanteil": je_grund.get("LIQUIDATION", 0) / n,
        "groesster_ruecklauf_usd": ruecklauf,
        "je_familie": je_familie,
        "funding_gesamt": sum(r["funding_summe"] for r in runden),
    }


def zeitfenster(k4_je_inst, tage):
    """(start_ms, end_ms): die letzten 'tage' Tage bis zum juengsten 4H-Datum.
    Ohne Daten (0, -1) - die Schleife laeuft dann nicht."""
    enden = [k[-1][0] for k in k4_je_inst.values() if k]
    if not enden:
        return 0, -1
    ende = max(enden)
    return ende - tage * 86_400_000, ende


WARMUP_TAGE = 60       # Rangliste braucht 21 Tage 4H, Hebel-Deckel 14+ Tage 1D


def _main():
    import argparse
    import json
    import xperp_kerzen as xk

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tage", type=int, default=180,
                   help="Rueckblick (ohne Warmup)")
    p.add_argument("--kerzen-holen", action="store_true",
                   help="Cache vorher auffrischen - langsam (siehe Spec, "
                        "'Takt und Laufzeit')")
    a = p.parse_args()

    universum = xk.hole_universum() if a.kerzen_holen else xk.laden_universum()
    if not universum:
        print("Kein Universum-Cache - einmal mit --kerzen-holen starten.")
        return 1

    gesamt_tage = a.tage + WARMUP_TAGE
    seiten_1h = -(-gesamt_tage * 24 // 100)
    seiten_4h = -(-gesamt_tage * 6 // 100)
    seiten_fund = -(-gesamt_tage * 24 // 100) + 1   # deckt auch 1h-Takt

    k4, k1h, k1d, saetze = {}, {}, {}, {}
    for x in universum:
        iid = x["instId"]
        if a.kerzen_holen:
            xk.hole(iid, "1H", seiten=seiten_1h)
            xk.hole(iid, "4H", seiten=seiten_4h)
            xk.hole(iid, "1D")
            xk.hole_funding(iid, seiten=seiten_fund)
        k4[iid], _ = xk.laden(iid, "4H")
        k1h[iid], _ = xk.laden(iid, "1H")
        k1d[iid], _ = xk.laden(iid, "1D")
        saetze[iid], _ = xk.laden_funding(iid)

    # Einmal abrufen statt je Instrument. Der Umsatz wird punktgenau aus den
    # 4H-Kerzen und dem Kontraktwert gerechnet (rangliste_schritt).
    instr_je_basis = {i["instId"].split("-")[0]: i
                      for i in okxf.instrumente(kategorie=None)}

    start_ms, end_ms = zeitfenster(k4, a.tage)
    runden = simuliere(universum, k4, k1h, k1d, saetze, {},
                       instr_je_basis, bot.wachen(), start_ms, end_ms)
    print(json.dumps(bericht(runden), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(_main())

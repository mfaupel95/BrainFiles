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


def rangliste_schritt(universum, kerzen_4h_je_inst, kerzen_1d_je_inst,
                      umsatz_je_inst, zeit_ms):
    """Kennzahlen+Punkte aller Instrumente mit genuegend Historie BIS zeit_ms.

    Punkt-in-Zeit-Aequivalent zu auswahl.sammle(): derselbe kennzahlen()/
    bewerte()-Aufruf, aber auf einem auf zeit_ms geschnittenen Fenster.
    """
    aus = []
    for x in universum:
        iid = x["instId"]
        k4 = schnitt_bis(kerzen_4h_je_inst.get(iid, []), zeit_ms)
        if len(k4) < MIN_KERZEN_4H:
            continue
        z = auswahl.kennzahlen(k4)
        kt = schnitt_bis(kerzen_1d_je_inst.get(iid, []), zeit_ms)
        if len(kt) >= 14:
            z["mae_long"], z["mae_short"] = auswahl.mae_tage(kt, 7)
        kat = auswahl.KATEGORIEN[x["kategorie"]]
        umsatz = umsatz_je_inst.get(iid, 0.0)
        z.update(basis=x["basis"], instId=iid, umsatz=umsatz,
                 kategorie=x["kategorie"], vola_tor=kat["vola_tor"],
                 punkte=auswahl.bewerte(z, umsatz, kat["umsatz_bezug"]))
        aus.append(z)
    return aus


def kandidaten_schritt(werte, w, anzahl=6):
    """Die besten Werte je Richtung, die ihre Tore bestehen.

    1:1 die Filterkette aus handeln.kandidaten() - Vola-Tor, Familie aktiv,
    Umsatz-Bezug der Familie, Hebel-Deckel >= max_hebel.
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
            if deckel < w["max_hebel"]:
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
    k4 = schnitt_bis(k4_je_inst.get(kandidat["instId"], []), zeit_ms)
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

    g = bot.groesse(w, instr, einstieg, stop, seite, kandidat["deckel"])
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
            lambda inst_id, n=300: schnitt_bis(k1d_je_inst.get(inst_id, []),
                                               zeit_ms))
        pflicht = bot.pruefpflicht(
            w, instr, k4, seite, einstieg, stop, ziel, g["hebel"],
            stop_atr_f=w["stop_atr_faktor"], ziel_atr_f=w["ziel_atr_faktor"],
            still=True)
    finally:
        okxf.funding = echt_funding
        bot.tages_kerzen_quelle = echt_seam

    if not pflicht.get("traegt") or not pflicht.get("hebel_traegt"):
        return None

    return {"inst": kandidat["instId"], "basis": kandidat["basis"],
            "seite": seite, "kategorie": kandidat["kategorie"],
            "einstieg": einstieg, "stop": stop, "ziel": ziel,
            "liq": g["liq"], "hebel": g["hebel"], "kontrakte": g["kontrakte"],
            "nominal": g["nominal"], "margin": g["margin"],
            "hoechstkurs": einstieg, "stop_id": "ruecktest",
            "eroeffnet_ts": zeit_ms, "letzte_funding_ts": zeit_ms,
            "funding_summe": 0.0}


def pruefe_ausstieg_1h(p, kerze_1h, w):
    """Ausstiegsvorrang LIQUIDATION > stop > ziel auf einer 1H-Kerze, danach
    Trailing-Nachfuehrung, wenn kein Ausstieg greift. Reihenfolge 1:1 aus
    handeln.pruefe_ausstiege(), aber auf Kerzen-Extremen (hoch/tief) statt auf
    einem einzelnen Live-Preis. Gibt (grund, ausstiegspreis) oder (None, None).
    """
    _, _, hoch, tief, schluss, _ = kerze_1h
    if p["seite"] == "long":
        if tief <= p["liq"]:
            return "LIQUIDATION", p["liq"]
        if tief <= p["stop"]:
            return "stop", p["stop"]
        if hoch >= p["ziel"]:
            return "ziel", p["ziel"]
    else:
        if hoch >= p["liq"]:
            return "LIQUIDATION", p["liq"]
        if hoch >= p["stop"]:
            return "stop", p["stop"]
        if tief <= p["ziel"]:
            return "ziel", p["ziel"]

    trailing_modul.erst_hoch(p, schluss)
    kand, _grund = trailing_modul.kandidat(p, schluss, w, liq=p.get("liq"))
    if kand is not None:
        p["stop"] = kand["stop"]
        p["hoechstkurs"] = kand["hoechstkurs"]
    return None, None


ACHT_STUNDEN_MS = 8 * 3_600_000


class FundingLuecke(Exception):
    """Kein historischer Funding-Satz vor diesem Zeitpunkt - nicht mit 0.0
    auffuellen. Dieselbe Haltung wie kraken_modell.FXLuecke."""


def satz_zu_zeitpunkt(saetze_je_inst, inst, zeit_ms):
    """Der zuletzt VOR (oder genau zu) zeit_ms veroeffentlichte Funding-Satz."""
    frueher = [s for s in saetze_je_inst.get(inst, []) if s[0] <= zeit_ms]
    if not frueher:
        raise FundingLuecke(
            "kein Funding-Satz vor Zeitpunkt %d fuer %s" % (zeit_ms, inst))
    return frueher[-1][1]


def funding_faellig(p, zeit_ms, saetze_je_inst):
    """Faelliges Funding seit der letzten Buchung: nominal * Satz je Periode,
    mit dem historischen Satz der jeweiligen Periode (genauer als
    handeln.buche_funding(), das den aktuellen Satz auf alle Perioden legt).
    Positiv = gezahlt (Long bei positivem Satz). Veraendert p erst, wenn alle
    Perioden gerechnet sind - eine FundingLuecke laesst p unberuehrt.
    """
    perioden = (zeit_ms - p["letzte_funding_ts"]) // ACHT_STUNDEN_MS
    if perioden <= 0:
        return 0.0
    vz = 1 if p["seite"] == "long" else -1
    gesamt = 0.0
    for i in range(perioden):
        t = p["letzte_funding_ts"] + (i + 1) * ACHT_STUNDEN_MS
        gesamt += p["nominal"] * satz_zu_zeitpunkt(
            saetze_je_inst, p["inst"], t) * vz
    p["letzte_funding_ts"] += perioden * ACHT_STUNDEN_MS
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
              start_ms, end_ms):
    """4H-Aussentakt (Rangliste/Einstieg), 1H-Innenaufloesung (Ausstieg,
    Trailing, Funding). Gibt die abgeschlossenen Runden zurueck.

    Entscheidungen zum Zeitpunkt t sehen nur ABGESCHLOSSENE 4H-Kerzen
    (ts <= t - 4H): die Kerze mit ts == t laeuft erst und ihr Schlusskurs ist
    noch nicht bekannt. Zum Ende offene Positionen werden nicht bewertet.
    """
    from datetime import datetime, timezone

    zustand, offene, runden = {}, [], []

    def satz_bis(inst, zeit_ms):
        return satz_zu_zeitpunkt(saetze_je_inst, inst, zeit_ms)

    t = start_ms
    while t <= end_ms:
        stand = t - SCHRITT_MS
        jetzt_dt = datetime.fromtimestamp(t / 1000, tz=timezone.utc)

        werte = rangliste_schritt(universum, k4_je_inst, k1d_je_inst,
                                  umsatz_je_inst, stand)
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

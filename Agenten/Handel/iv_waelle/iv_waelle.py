"""IV-Wand-Spur - Kernrechnung.

Aus dem Video (atraintrades, "Can't beat the IV Walls"): aus historischer
Volatilitaet PLUS Options-Bepreisung eine erwartete Tagesspanne ableiten, dann
an den Waenden (Strikes mit hohem offenem Interesse) gegen die Bewegung
handeln, Stop knapp HINTER die Wand, Ziel zurueck zur Mitte.

Zwei Rechnungen, sauber getrennt:
  1. erwartete Spanne  -  aus IV (DVOL) und realisierter Volatilitaet (HV).
  2. Waende            -  aus der Optionskette (offenes Interesse je Strike).

Die Spur handelt NICHT. handel_erlaubt steht in wachen.json auf false.
"""
from __future__ import annotations

import math
import statistics
from datetime import datetime, timezone

TAGE_JE_JAHR = 365.0
WURZEL_TAG = math.sqrt(TAGE_JE_JAHR)

# Standardabweichungen fuer die ueblichen zwei-seitigen Wahrscheinlichkeiten.
K_68 = 1.0
K_90 = 1.6449  # z fuer 90 %
K_95 = 1.9600
K_99 = 2.5758


# ---------------------------------------------------------------- Volatilitaet

def hist_vol_prozent(schlusskurse: list, fenster: int = 20) -> float | None:
    """Realisierte Volatilitaet in Prozent pro Jahr aus Schlusskursen.

    Close-to-close, logarithmische Renditen, Annualisierung mit sqrt(365) -
    Krypto handelt durch, deshalb 365 und nicht 252.
    """
    if len(schlusskurse) < fenster + 1:
        return None
    reihe = schlusskurse[-(fenster + 1):]
    renditen = [math.log(reihe[i + 1] / reihe[i]) for i in range(fenster)
                if reihe[i] > 0 and reihe[i + 1] > 0]
    if len(renditen) < 2:
        return None
    return statistics.stdev(renditen) * WURZEL_TAG * 100.0


def tages_sigma(basispreis: float, jahres_iv_prozent: float) -> float:
    """Erwartete Tagesschwankung in Kursen (1 Sigma)."""
    return basispreis * (jahres_iv_prozent / 100.0) / WURZEL_TAG


def mische_iv_hv(iv_prozent: float | None, hv_prozent: float | None,
                 gewicht_iv: float = 0.5) -> float | None:
    """Beide Quellen des Videos zusammenfuehren: IV aus der Bepreisung, HV aus
    der Vergangenheit. Fehlt eine, wird die andere genommen."""
    if iv_prozent is None:
        return hv_prozent
    if hv_prozent is None:
        return iv_prozent
    return gewicht_iv * iv_prozent + (1.0 - gewicht_iv) * hv_prozent


def spanne(basispreis: float, jahres_iv_prozent: float, k: float = K_90) -> dict:
    """Erwartete Spanne um den Basispreis herum."""
    sigma = tages_sigma(basispreis, jahres_iv_prozent)
    return {
        "basispreis": basispreis,
        "sigma": sigma,
        "k": k,
        "oben": basispreis + k * sigma,
        "unten": basispreis - k * sigma,
        "mitte": basispreis,
        "breite_prozent": (2.0 * k * sigma / basispreis) * 100.0 if basispreis else 0.0,
        "iv_prozent": jahres_iv_prozent,
    }


# ---------------------------------------------------------------------- Waende

def strike_aus_name(instrument: str) -> tuple:
    """'BTC-25DEC26-220000-C' -> (220000.0, 'C')."""
    teile = instrument.split("-")
    if len(teile) < 4:
        return (None, None)
    try:
        return (float(teile[2]), teile[3].upper())
    except ValueError:
        return (None, None)


def offenes_interesse_je_strike(kette: list) -> dict:
    """Summiert das offene Interesse je (Strike, C/P). Alle Faelligkeiten zusammen -
    ein Verfallstag allein waere zu duenn besetzt."""
    summen: dict = {}
    for eintrag in kette:
        strike, seite = strike_aus_name(eintrag.get("instrument_name", ""))
        if strike is None:
            continue
        oi = float(eintrag.get("open_interest") or 0.0)
        mark_iv = float(eintrag.get("mark_iv") or 0.0)
        schluessel = (strike, seite)
        if schluessel not in summen:
            summen[schluessel] = {"oi": 0.0, "iv_gewichtet": 0.0, "iv_summe": 0.0, "n": 0}
        summen[schluessel]["oi"] += oi
        summen[schluessel]["iv_gewichtet"] += oi * mark_iv
        summen[schluessel]["iv_summe"] += mark_iv
        summen[schluessel]["n"] += 1
    for werte in summen.values():
        werte["iv"] = (werte["iv_gewichtet"] / werte["oi"]) if werte["oi"] > 0 \
            else (werte["iv_summe"] / werte["n"] if werte["n"] else 0.0)
    return summen


def waende(kette: list, spot: float, abstand_min_prozent: float = 0.3) -> dict:
    """Call-Wand (ueber dem Kurs) und Put-Wand (unter dem Kurs) bestimmen.

    Gesucht ist der Strike mit dem groessten offenen Interesse je Seite, der
    mindestens `abstand_min_prozent` vom Kurs entfernt liegt - Strikes direkt am
    Kurs sind meist Hedge-Bestand und keine Wand.
    """
    summen = offenes_interesse_je_strike(kette)
    grenze = spot * abstand_min_prozent / 100.0

    calls = {s: w for (s, seite), w in summen.items() if seite == "C" and s >= spot + grenze}
    puts = {s: w for (s, seite), w in summen.items() if seite == "P" and s <= spot - grenze}

    def _groesster(menge: dict):
        if not menge:
            return None
        strike = max(menge, key=lambda s: menge[s]["oi"])
        werte = dict(menge[strike])
        werte["strike"] = strike
        werte["abstand_prozent"] = (strike - spot) / spot * 100.0
        return werte

    call_wand = _groesster(calls)
    put_wand = _groesster(puts)

    def _top(menge: dict) -> list:
        strikes = sorted(menge, key=lambda s: menge[s]["oi"], reverse=True)[:3]
        return [{**menge[s], "strike": s,
                 "abstand_prozent": (s - spot) / spot * 100.0} for s in strikes]

    return {
        "spot": spot,
        "call_wand": call_wand,
        "put_wand": put_wand,
        "call_top3": _top(calls),
        "put_top3": _top(puts),
        "strikes_gesamt": len(summen),
        "oi_gesamt": sum(w["oi"] for w in summen.values()),
    }


# ---------------------------------------------------------------------- Signal

def wandelage(waende_: dict, spannweite: dict) -> dict:
    """Ordnet beide Waende in die erwartete Spanne ein.

    Der Befund aus den Gueteproben: eine Wand INNERHALB der Tagesspanne ist
    Rauschen, eine weit dahinter wird nie erreicht. Handelbar ist der Bereich
    zwischen der Grenze und dem Dreifachen von Sigma - dort liegt die Wand
    ausserhalb der normalen Bewegung, aber noch in Reichweite.
    """
    sigma = spannweite["sigma"] or 0.0
    spot = spannweite["basispreis"]
    aus = {}
    for name in ("call_wand", "put_wand"):
        wand = waende_.get(name)
        if not wand or sigma <= 0:
            aus[name] = {"lage": "keine", "text": "keine Wand gefunden"}
            continue
        abstand = abs(wand["strike"] - spot) / sigma
        if abstand <= spannweite["k"]:
            lage, text = "im_bereich", "liegt innerhalb der Tagesspanne (Rauschen)"
        elif abstand <= 3.0:
            lage, text = "handelbar", "liegt hinter der Grenze, aber in Reichweite"
        else:
            lage, text = "zu_weit", "weiter als 3 Sigma entfernt (heute unerreichbar)"
        aus[name] = {"lage": lage, "abstand_sigma": abstand, "text": text,
                     "strike": wand["strike"], "oi": wand["oi"]}
    return aus


def signal(spot: float, waende_: dict, spannweite: dict,
           naehe_prozent: float = 0.5, stop_puffer_prozent: float = 0.25,
           ziel: str = "mitte", ziel_anteil: float = 0.5,
           nur_handelbare_wand: bool = True) -> dict:
    """Fade-Signal an der Wand.

    Regel aus dem Video: an der Wand gegen die Bewegung, Stop HINTER die Wand
    (dort liegt die Absicherung der Gegenseite), Ziel zurueck zur Mitte.

    `ziel_anteil` ist der gemessene Teil: die Gueteprobe zeigt, dass der Rueckweg
    nur ZUR HAELFTE genommen wird (+0.32 / +0.24 % je Runde in beiden Haelften
    der 400 Tage), der volle Rueckweg zur Tagesmitte zahlt NICHT.
    """
    call_wand = waende_.get("call_wand")
    put_wand = waende_.get("put_wand")
    naehe = spot * naehe_prozent / 100.0
    lagen = wandelage(waende_, spannweite)

    ergebnis = {"richtung": "kein_signal", "grund": "keine Wand in Reichweite",
                "spot": spot, "lagen": lagen}

    def _gesperrt(name: str) -> bool:
        return nur_handelbare_wand and lagen.get(name, {}).get("lage") != "handelbar"

    if call_wand and not _gesperrt("call_wand") \
            and abs(spot - call_wand["strike"]) <= naehe and spot <= call_wand["strike"]:
        einstieg = spot
        stop = call_wand["strike"] * (1.0 + stop_puffer_prozent / 100.0)
        voll = spannweite["mitte"] if ziel == "mitte" else spannweite["unten"]
        ziel_kurs = einstieg - ziel_anteil * (einstieg - voll)
        ergebnis.update({
            "richtung": "short",
            "grund": f"Kurs an der Call-Wand {call_wand['strike']:.0f} "
                     f"(OI {call_wand['oi']:.0f}, {call_wand['abstand_prozent']:+.2f} %)",
            "einstieg": einstieg, "stop": stop, "ziel": ziel_kurs,
            "ziel_anteil": ziel_anteil,
            "wand": call_wand["strike"],
            "risiko_prozent": (stop - einstieg) / einstieg * 100.0,
            "chance_prozent": (einstieg - ziel_kurs) / einstieg * 100.0,
        })
    elif put_wand and not _gesperrt("put_wand") \
            and abs(spot - put_wand["strike"]) <= naehe and spot >= put_wand["strike"]:
        einstieg = spot
        stop = put_wand["strike"] * (1.0 - stop_puffer_prozent / 100.0)
        voll = spannweite["mitte"] if ziel == "mitte" else spannweite["oben"]
        ziel_kurs = einstieg + ziel_anteil * (voll - einstieg)
        ergebnis.update({
            "richtung": "long",
            "grund": f"Kurs an der Put-Wand {put_wand['strike']:.0f} "
                     f"(OI {put_wand['oi']:.0f}, {put_wand['abstand_prozent']:+.2f} %)",
            "einstieg": einstieg, "stop": stop, "ziel": ziel_kurs,
            "ziel_anteil": ziel_anteil,
            "wand": put_wand["strike"],
            "risiko_prozent": (einstieg - stop) / einstieg * 100.0,
            "chance_prozent": (ziel_kurs - einstieg) / einstieg * 100.0,
        })

    if ergebnis["richtung"] != "kein_signal":
        risiko = ergebnis["risiko_prozent"] or 0.0
        chance = ergebnis["chance_prozent"] or 0.0
        ergebnis["chance_risiko"] = (chance / risiko) if risiko > 0 else None
        ergebnis["ausserhalb_spanne"] = (
            spot > spannweite["oben"] or spot < spannweite["unten"])
    return ergebnis


def tag_in_utc(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def signal_an_der_spanne(spot: float, spannweite: dict,
                         stop_sigma: float = 0.5,
                         ziel_anteil: float = 0.5) -> dict:
    """Fade an der erwarteten Spannengrenze - das GEMESSENE Feld.

    WARUM ES DIESE FUNKTION GIBT (29.09.2026)
    -----------------------------------------
    `signal()` verlangt zweierlei: eine Wand innerhalb von 0,5 % des Kurses UND
    die Wand im Band zwischen der Grenze und 3 Sigma. An den echten Deribit-
    Ketten liegt keine Wand je dort. Gemessen mit der eigenen Sonde
    (29.09.2026): BTC 83.107, Tagesbasis 84.470, Sigma 1.765 -> Call-Wand
    90.000 = 3,13 Sigma, Put-Wand 60.000 = 13,9 Sigma. Beide "zu weit". Weil
    OI-Waende an runden Zahlen sitzen (80.000/90.000/100.000) und die
    Tagesspanne nur wenige Prozent breit ist, ist der geforderte Abstand ein
    Vielfaches des Moeglichen. Folge: die Spur hat seit dem 19.09.2026 KEIN
    Geschaeft gemacht und deshalb kein Journal - nicht weil sie versagt,
    sondern weil ihr Tor nie aufgeht.

    Die Wandregel ist nie gemessen worden (0 Zeilen), die Spannengrenze ist
    ueber 400 Tage gemessen: k=1,0 / Stop 0,5 Sigma / halber Rueckweg zur Mitte
    = +0,276 % je Runde bei 204 von 400 Tagen mit Signal, beide Haelften und
    beide Seiten positiv (backtest_iv_waelle.py, iv_waelle/NOTIZ.md).
    Deshalb handelt die Spur ab jetzt an der Spannengrenze; die Wand bleibt
    als Zusatzweg erhalten (signal()) und ist weiterhin in den Wachen
    abschaltbar.

    Regel: Kurs >= obere Grenze -> short, Kurs <= untere Grenze -> long.
    Stop `stop_sigma` Sigma HINTER die Grenze, Ziel der `ziel_anteil`-te
    Rueckweg zur Tagesmitte. Ein Kurs, der so weit ueber die Grenze gelaufen
    ist, dass der Stop VOR dem Einstieg laege, ist kein Geschaeft.
    """
    oben = spannweite["oben"]
    unten = spannweite["unten"]
    mitte = spannweite["mitte"]
    sigma = spannweite["sigma"] or 0.0
    aus = {"richtung": "kein_signal", "ausloeser": "spanne", "spot": spot,
           "grund": "Kurs innerhalb der Tagesspanne (%.2f - %.2f)" % (unten, oben)}
    if sigma <= 0:
        aus["grund"] = "kein Sigma (IV und HV fehlen)"
        return aus

    if spot >= oben:
        einstieg = spot
        stop = oben + stop_sigma * sigma
        ziel = einstieg - ziel_anteil * (einstieg - mitte)
        if stop <= einstieg:
            aus["grund"] = ("Kurs %.2f zu weit ueber der Grenze %.2f - der Stop "
                            "laege vor dem Einstieg" % (spot, oben))
            return aus
        aus.update({
            "richtung": "short",
            "grund": "Kurs %.2f ueber der oberen Grenze %.2f (%.2f Sigma)"
                     % (spot, oben, (spot - mitte) / sigma),
            "einstieg": einstieg, "stop": stop, "ziel": ziel,
            "grenze": oben, "ziel_anteil": ziel_anteil,
            "risiko_prozent": (stop - einstieg) / einstieg * 100.0,
            "chance_prozent": (einstieg - ziel) / einstieg * 100.0,
        })
        return aus

    if spot <= unten:
        einstieg = spot
        stop = unten - stop_sigma * sigma
        ziel = einstieg + ziel_anteil * (mitte - einstieg)
        if stop >= einstieg:
            aus["grund"] = ("Kurs %.2f zu weit unter der Grenze %.2f - der Stop "
                            "laege vor dem Einstieg" % (spot, unten))
            return aus
        aus.update({
            "richtung": "long",
            "grund": "Kurs %.2f unter der unteren Grenze %.2f (%.2f Sigma)"
                     % (spot, unten, (mitte - spot) / sigma),
            "einstieg": einstieg, "stop": stop, "ziel": ziel,
            "grenze": unten, "ziel_anteil": ziel_anteil,
            "risiko_prozent": (einstieg - stop) / einstieg * 100.0,
            "chance_prozent": (ziel - einstieg) / einstieg * 100.0,
        })
        return aus

    aus["ausserhalb_spanne"] = False
    return aus

"""Bewertet eine Kursreihe auf Chance und Risiko.

Kein Orakel. Das Modell ist bewusst durchschaubar: jede Kennzahl steht einzeln
im Ergebnis, damit im Bericht nachvollziehbar bleibt, warum eine Muenze oben
steht. Grundlinie aus Wissen/Handelsbots.md: ueber lange Zeitraeume liegt fast
jede mechanische Krypto-Strategie nahe null, leicht darunter. Dieser Scanner
sucht daher nicht den grossen Wurf, sondern Lagen mit gutem Verhaeltnis von
Aufwaertspotenzial zu Schwankung - und siebt alles Zappelige hart aus.

Eingabe: Tageskerzen [ts, o, h, l, c, vol], aufsteigend, mind. ~120 Stueck.
Ausgabe: dict mit chance (0-100), risiko (0-100), score (0-100), verhaeltnis
und den Rohkennzahlen.
"""

import math


def _sma(werte, n):
    if len(werte) < n:
        return None
    return sum(werte[-n:]) / n


def _rsi(schluss, n=14):
    if len(schluss) < n + 1:
        return 50.0
    gewinne, verluste = [], []
    for i in range(-n, 0):
        d = schluss[i] - schluss[i - 1]
        gewinne.append(max(d, 0.0))
        verluste.append(max(-d, 0.0))
    mg = sum(gewinne) / n
    mv = sum(verluste) / n
    if mv == 0:
        return 100.0
    rs = mg / mv
    return 100.0 - 100.0 / (1.0 + rs)


def _log_renditen(schluss):
    r = []
    for i in range(1, len(schluss)):
        if schluss[i - 1] > 0 and schluss[i] > 0:
            r.append(math.log(schluss[i] / schluss[i - 1]))
    return r


def _stdabw(werte):
    if len(werte) < 2:
        return 0.0
    m = sum(werte) / len(werte)
    return math.sqrt(sum((x - m) ** 2 for x in werte) / (len(werte) - 1))


def _max_drawdown(schluss):
    spitze = schluss[0]
    schlimmster = 0.0
    for p in schluss:
        spitze = max(spitze, p)
        schlimmster = min(schlimmster, p / spitze - 1.0)
    return abs(schlimmster)


def _skalieren(x, lo, hi):
    """x aus [lo, hi] linear nach [0, 1], ausserhalb gekappt."""
    if hi == lo:
        return 0.0
    return max(0.0, min(1.0, (x - lo) / (hi - lo)))


def bewerten(kerzen):
    schluss = [k[4] for k in kerzen]
    hoch = [k[2] for k in kerzen]
    tief = [k[3] for k in kerzen]
    vol = [k[5] for k in kerzen]
    preis = schluss[-1]

    sma20, sma50, sma100 = _sma(schluss, 20), _sma(schluss, 50), _sma(schluss, 100)
    trend_stufen = [preis > s for s in (sma20, sma50, sma100) if s is not None]
    trend = sum(trend_stufen) / len(trend_stufen) if trend_stufen else 0.5

    rendite_30 = preis / schluss[-31] - 1.0 if len(schluss) > 31 else 0.0
    rsi = _rsi(schluss)

    fenster = schluss[-60:] if len(schluss) >= 60 else schluss
    hoch_60 = max(hoch[-60:]) if len(hoch) >= 60 else max(hoch)
    abstand_hoch = preis / hoch_60 - 1.0            # <= 0, je naeher 0 desto teurer

    renditen = _log_renditen(schluss[-90:])
    vola_pa = _stdabw(renditen) * math.sqrt(365.0)
    drawdown_90 = _max_drawdown(fenster[-90:] if len(fenster) >= 90 else fenster)

    # Volumenbestaetigung: liegt das juengste Volumen ueber dem 30-Tage-Schnitt?
    vol_schnitt = _sma(vol, 30)
    vol_bestaetigung = 0.5
    if vol_schnitt:
        vol_bestaetigung = _skalieren(sum(vol[-5:]) / 5.0 / vol_schnitt, 0.7, 1.6)

    # --- Chance (0..100) --------------------------------------------------
    c_trend = trend                                        # 0..1
    c_momentum = _skalieren(rendite_30, -0.10, 0.40)       # bis +40 % in 30 T
    c_ruecksetzer = _skalieren(abstand_hoch, -0.20, -0.02) # Pullback, nicht am Hoch
    c_nicht_ueberkauft = 1.0 - _skalieren(rsi, 62, 82)     # RSI > 82 killt die Chance
    c_volumen = vol_bestaetigung
    chance = 100.0 * (
        0.30 * c_trend
        + 0.28 * c_momentum
        + 0.16 * c_ruecksetzer
        + 0.14 * c_nicht_ueberkauft
        + 0.12 * c_volumen
    )

    # --- Risiko (0..100) ------------------------------------------------
    r_vola = _skalieren(vola_pa, 0.30, 1.50)               # 30 % p.a. ruhig, 150 % wild
    r_drawdown = _skalieren(drawdown_90, 0.10, 0.55)
    r_extrem_rsi = max(_skalieren(rsi, 80, 92), _skalieren(38 - rsi, 0, 20))
    r_absturz_momentum = _skalieren(-rendite_30, 0.10, 0.45)
    risiko = 100.0 * (
        0.42 * r_vola
        + 0.28 * r_drawdown
        + 0.16 * r_extrem_rsi
        + 0.14 * r_absturz_momentum
    )

    score = max(0.0, min(100.0, chance * (1.0 - 0.7 * risiko / 100.0)))
    verhaeltnis = chance / max(risiko, 1.0)

    return {
        "preis": round(preis, 6),
        "chance": round(chance, 1),
        "risiko": round(risiko, 1),
        "score": round(score, 1),
        "verhaeltnis": round(verhaeltnis, 2),
        "kennzahlen": {
            "trend_ueber_sma": round(trend, 2),
            "rendite_30t_pct": round(rendite_30 * 100, 1),
            "rsi14": round(rsi, 1),
            "abstand_60t_hoch_pct": round(abstand_hoch * 100, 1),
            "volatilitaet_pa": round(vola_pa, 2),
            "max_drawdown_90t_pct": round(drawdown_90 * 100, 1),
            "volumen_bestaetigung": round(vol_bestaetigung, 2),
        },
    }

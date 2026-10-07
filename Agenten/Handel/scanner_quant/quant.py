"""Quant-Urteil fuer eine Tageskerzenreihe - reine Rechnung, kein Netz, kein Schreiben.

Ergaenzt die Bewertung des Scanners um vier Messgroessen, die dort fehlen:

1. **Trendordnung** - stehen Kurs und SMA20/50/200 in der Reihenfolge eines
   gesunden Trends (vier Paarvergleiche, 0 bis 4)?
2. **Trendguete** - Kaufmans Effizienzverhaeltnis ueber 30 Tage. Nah an 1 ist
   eine Gerade, nah an 0 Zappeln. Das trennt Trend von Rauschen, wo die
   Rendite allein beides gleich aussieht.
3. **Dehnung** - Abstand des Kurses zur SMA50 in ATR-Einheiten. Ueber ~6 heisst:
   der Weg hierher war schon der Gewinn, der Einstieg kauft die Spitze. ATR
   statt Standardabweichung, weil der z-Wert der letzten 50 Schluesse bei einer
   steilen Rampe nach oben gedeckelt ist (gemessen: eine Verdopplung in 20 Tagen
   ergibt nur z = 2,5) und genau die Spitzen nicht von normalen Trends trennt.
   Der z-Wert steht weiter im Ergebnis, zaehlt aber nicht.
4. **Schwung je Risikoeinheit** - 20-Tage-Rendite geteilt durch ATR14. Gleiche
   Rendite bei kleinerer Spanne ist die bessere Lage.

Dazu zur Information (nicht im Score): Korrelation und relative Staerke gegen
eine Referenzreihe (BTC), damit sichtbar bleibt, ob ein "Kandidat" nur BTC mit
Hebel ist.

Eingabe wie im Scanner: [ts, open, high, low, close, vol], aufsteigend.
Ohne ausreichende Historie (lang + LUFT Kerzen) gibt urteil() None zurueck - lieber
kein Urteil als ein geraetes.
"""

import math

LANG = 200                # lange Durchschnittslaenge (Spot); xperp nimmt 100
LUFT = 10                 # Kerzen ueber LANG hinaus fuer die Folgegroessen

GEWICHTE = {"ordnung": 0.35, "guete": 0.25, "schwung": 0.20, "dehnung": 0.20}


def _sma(werte, n):
    return sum(werte[-n:]) / n


def _skal(x, lo, hi):
    """Linear auf 0..1, ausserhalb abgeschnitten."""
    if hi == lo:
        return 0.0
    return max(0.0, min(1.0, (x - lo) / (hi - lo)))


def _stdabw(werte):
    m = sum(werte) / len(werte)
    return math.sqrt(sum((w - m) ** 2 for w in werte) / len(werte))


def atr(kerzen, n=14):
    """Durchschnittliche wahre Spanne der letzten n Kerzen."""
    spannen = []
    for i in range(len(kerzen) - n, len(kerzen)):
        _, _, h, l, _, _ = kerzen[i]
        c_vor = kerzen[i - 1][4]
        spannen.append(max(h - l, abs(h - c_vor), abs(l - c_vor)))
    return sum(spannen) / n


def effizienz(schluss, n=30):
    """Kaufman: Nettoweg / Summe der Einzelwege. 0 = Zappeln, 1 = Gerade."""
    fenster = schluss[-(n + 1):]
    weg = sum(abs(b - a) for a, b in zip(fenster, fenster[1:]))
    if weg == 0:
        return 0.0
    return abs(fenster[-1] - fenster[0]) / weg


def dehnung_z(schluss, n=50):
    """Abstand zur SMA50 in Standardabweichungen der letzten n Schluesse."""
    fenster = schluss[-n:]
    s = _stdabw(fenster)
    if s == 0:
        return 0.0
    return (schluss[-1] - sum(fenster) / n) / s


def _renditen(schluss):
    return [b / a - 1.0 for a, b in zip(schluss, schluss[1:]) if a > 0]


def korrelation(a, b, n=60):
    """Pearson der Tagesrenditen, ueber die letzten n gemeinsamen Tage."""
    ra, rb = _renditen(a[-(n + 1):]), _renditen(b[-(n + 1):])
    m = min(len(ra), len(rb))
    if m < 20:
        return None
    ra, rb = ra[-m:], rb[-m:]
    ma, mb = sum(ra) / m, sum(rb) / m
    za = sum((x - ma) ** 2 for x in ra)
    zb = sum((x - mb) ** 2 for x in rb)
    if za == 0 or zb == 0:
        return None
    return sum((x - ma) * (y - mb) for x, y in zip(ra, rb)) / math.sqrt(za * zb)


def urteil(kerzen, ref=None, dehnung_max=6.0, deckel_gedehnt=50.0,
           richtung="long", lang=LANG):
    """Quant-Urteil als dict, oder None bei zu kurzer Reihe.

    lang: Laenge der langen Durchschnittslinie (Standard 200). Die Ordnung
    heisst dann Kurs / SMA20 / SMA50 / SMA<lang>; unter lang + LUFT Kerzen
    gibt es kein Urteil. xperp nutzt 100, weil dort KEIN Kontrakt 210 Tage
    Historie hat (gemessen 07.10.2026: 0 von 181).
    richtung "long" (Standard, Spot-Scanner) oder "short" (Futures, xperp).
    Short ist die Spiegelung, kein zweiter Rechenweg: Ordnung zaehlt die
    umgekehrten Vergleiche, Schwung und Dehnung laufen nach unten (Dehnung =
    wie weit der Kurs UNTER der SMA50 liegt - dort lauert die Erholung bzw.
    der Short-Squeeze). Trendguete ist richtungslos. Die Referenzfelder bleiben
    wie bei long (Korrelation ist symmetrisch; die relative Staerke zeigt
    weiter "Wert minus BTC", beim Short ist ein negativer Wert der gute).

    Ist die Dehnung ueber dehnung_max (ATR-Einheiten), wird der Score auf
    deckel_gedehnt gekappt: eine Spitze darf an keinem Score-Tor vorbeikommen,
    egal wie sauber der Trend davor war. Die Schwelle fuer den Score setzt der
    Aufrufer (quant.json).
    """
    if richtung not in ("long", "short"):
        raise ValueError("richtung muss 'long' oder 'short' sein, nicht %r"
                         % (richtung,))
    if len(kerzen) < lang + LUFT:
        return None
    vz = 1.0 if richtung == "long" else -1.0       # Vorzeichen der Spiegelung
    schluss = [k[4] for k in kerzen]
    c = schluss[-1]
    s20, s50, s200 = _sma(schluss, 20), _sma(schluss, 50), _sma(schluss, lang)

    if richtung == "long":
        ordnung_n = sum([c > s20, s20 > s50, s50 > s200, c > s200])
    else:
        ordnung_n = sum([c < s20, s20 < s50, s50 < s200, c < s200])
    guete = effizienz(schluss, 30)
    z = dehnung_z(schluss, 50)
    a = atr(kerzen, 14)
    dehnung_atr = vz * (c - s50) / a if a > 0 else 0.0
    rendite_20 = c / schluss[-21] - 1.0
    schwung = vz * (c - schluss[-21]) / a if a > 0 else 0.0

    # Guete und "nicht gedehnt" sind fuer sich richtungslos: eine saubere Gerade
    # GEGEN die Richtung (oder ein Kurs weit auf der falschen Seite der SMA50,
    # also "nicht gedehnt") darf keine Punkte bringen. Gemessen: ohne diese
    # Bedingung bekam ein sauberer Abwaertstrend als Long 45 von 100.
    richtig = dehnung_atr > 0
    teile = {
        "ordnung": ordnung_n / 4.0,
        "guete": _skal(guete, 0.10, 0.50) if richtig else 0.0,
        "schwung": _skal(schwung, 0.0, 6.0),
        # Dehnung wirkt als Abzug: bis 3 ATR frei, ab 7 ATR voll bestraft.
        "dehnung": (1.0 - _skal(dehnung_atr, 3.0, 7.0)) if richtig else 0.0,
    }
    score = 100.0 * sum(GEWICHTE[k] * teile[k] for k in GEWICHTE)
    gedehnt = dehnung_atr > dehnung_max
    if gedehnt:
        score = min(score, deckel_gedehnt)

    out = {
        "richtung": richtung,
        "lang": lang,
        "quant_score": round(score, 1),
        "ordnung": ordnung_n,
        "effizienz30": round(guete, 3),
        "dehnung_atr": round(dehnung_atr, 2),
        "dehnung_z": round(z, 2),
        "schwung_je_atr": round(schwung, 2),
        "atr_pct": round(100.0 * a / c, 2) if c > 0 else None,
        "rendite_20t_pct": round(100.0 * rendite_20, 1),
        "zu_gedehnt": gedehnt,
    }
    if ref is not None and len(ref) >= 61:
        rs = [k[4] for k in ref]
        out["korr_ref_60t"] = (None if korrelation(schluss, rs) is None
                               else round(korrelation(schluss, rs), 2))
        if len(schluss) > 30 and len(rs) > 30:
            out["rel_staerke_30t_pct"] = round(
                100.0 * ((c / schluss[-31]) - (rs[-1] / rs[-31])), 1)
    return out

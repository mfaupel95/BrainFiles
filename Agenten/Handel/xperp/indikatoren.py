"""Indikatoren auf Kerzenreihen - reine Rechnung, keine Netzzugriffe.

Eingabe ist immer eine Liste [ts, offen, hoch, tief, schluss, volumen],
aufsteigend sortiert, wie sie okxf.kerzen() liefert. Jede Funktion gibt eine
Liste gleicher Laenge zurueck; die ersten Werte sind None, solange das Fenster
nicht voll ist. Das ist Absicht - ein mit dem ersten Kurs aufgefuellter
Indikator sieht am Anfang nach einem Signal aus, wo keines ist.

ATR ist hier die tragende Groesse, nicht nur ein Indikator unter vielen: Aus
ihm faellt der Stop-Abstand, und aus dem Stop-Abstand faellt die
Positionsgroesse. Der Hebel ist dann Ergebnis und nicht Eingabe.
"""


def wahre_spanne(k):
    """True Range je Kerze. Erste Kerze hat keine Vorgaengerin -> None."""
    tr = [None]
    for i in range(1, len(k)):
        tr.append(max(k[i][2] - k[i][3],
                      abs(k[i][2] - k[i - 1][4]),
                      abs(k[i][3] - k[i - 1][4])))
    return tr


def atr(k, n=14):
    """Average True Range, Wilder-Glaettung (wie in den meisten Charts)."""
    tr = wahre_spanne(k)
    out = [None] * len(k)
    if len(k) <= n:
        return out
    schnitt = sum(tr[1:n + 1]) / n
    out[n] = schnitt
    for i in range(n + 1, len(k)):
        schnitt = (schnitt * (n - 1) + tr[i]) / n
        out[i] = schnitt
    return out


def ema(werte, n):
    out = [None] * len(werte)
    if len(werte) < n:
        return out
    start = sum(werte[:n]) / n
    out[n - 1] = start
    f = 2.0 / (n + 1)
    for i in range(n, len(werte)):
        start = werte[i] * f + start * (1 - f)
        out[i] = start
    return out


def rsi(werte, n=14):
    out = [None] * len(werte)
    if len(werte) <= n:
        return out
    gew = [max(0.0, werte[i] - werte[i - 1]) for i in range(1, len(werte))]
    ver = [max(0.0, werte[i - 1] - werte[i]) for i in range(1, len(werte))]
    ag = sum(gew[:n]) / n
    av = sum(ver[:n]) / n
    out[n] = 100.0 if av == 0 else 100 - 100 / (1 + ag / av)
    for i in range(n, len(gew)):
        ag = (ag * (n - 1) + gew[i]) / n
        av = (av * (n - 1) + ver[i]) / n
        out[i + 1] = 100.0 if av == 0 else 100 - 100 / (1 + ag / av)
    return out


def supertrend(k, n=10, faktor=3.0):
    """SuperTrend. Gibt (linie, richtung) zurueck, richtung ist +1 oder -1.

    Die Baender liegen faktor x ATR um den Kerzenmittelpunkt. Entscheidend ist
    die Nachzieh-Logik: Ein Band darf sich nur in Richtung des Trends bewegen,
    nie zurueck. Ohne diese Sperre zappelt der Indikator mit jedem Ausreisser
    und liefert doppelt so viele Signale wie er soll.
    """
    a = atr(k, n)
    ob = [None] * len(k)
    ub = [None] * len(k)
    richtung = [None] * len(k)
    linie = [None] * len(k)

    for i in range(len(k)):
        if a[i] is None:
            continue
        mitte = (k[i][2] + k[i][3]) / 2
        o = mitte + faktor * a[i]
        u = mitte - faktor * a[i]

        if ob[i - 1] is None:
            ob[i], ub[i], richtung[i] = o, u, 1
        else:
            # Nachziehen nur in Trendrichtung
            ob[i] = o if (o < ob[i - 1] or k[i - 1][4] > ob[i - 1]) else ob[i - 1]
            ub[i] = u if (u > ub[i - 1] or k[i - 1][4] < ub[i - 1]) else ub[i - 1]
            if richtung[i - 1] == 1 and k[i][4] < ub[i - 1]:
                richtung[i] = -1
            elif richtung[i - 1] == -1 and k[i][4] > ob[i - 1]:
                richtung[i] = 1
            else:
                richtung[i] = richtung[i - 1]
        linie[i] = ub[i] if richtung[i] == 1 else ob[i]
    return linie, richtung


def effizienz(werte, n=42):
    """Kaufman Efficiency Ratio: Nettobewegung / zurueckgelegter Weg.

    Nahe 1 = sauberer Trend (Trendstrategie sinnvoll).
    Nahe 0 = Gezappel (Grid sinnvoll, Trendstrategie wird zerrieben).
    """
    f = werte[-min(n, len(werte)):]
    if len(f) < 2:
        return None
    weg = sum(abs(f[i] - f[i - 1]) for i in range(1, len(f)))
    return abs(f[-1] - f[0]) / weg if weg > 0 else 0.0


def lage(k, st_n=10, st_faktor=3.0):
    """Alle Signalgroessen der letzten Kerze in einem Wortschatz.

    Die drei Bausteine sind bewusst getrennt und werden nicht zu einer Zahl
    verrechnet: SuperTrend sagt die Richtung, EMA bestaetigt sie, RSI warnt vor
    dem Nachlaufen. Eine Summe wuerde verdecken, welcher davon widerspricht.
    """
    c = [r[4] for r in k]
    a = atr(k, 14)
    linie, richtung = supertrend(k, st_n, st_faktor)
    e20, e50 = ema(c, 20), ema(c, 50)
    r = rsi(c, 14)
    er = effizienz(c, 42)

    kurs = c[-1]
    st_richtung = richtung[-1]
    e_auf = (e20[-1] is not None and e50[-1] is not None and e20[-1] > e50[-1])
    e_ab = (e20[-1] is not None and e50[-1] is not None and e20[-1] < e50[-1])
    rsi_jetzt = r[-1]

    # Wieviele Kerzen laeuft die aktuelle Richtung schon?
    dauer = 0
    for i in range(len(richtung) - 1, 0, -1):
        if richtung[i] is None or richtung[i] != st_richtung:
            break
        dauer += 1

    if st_richtung == 1 and e_auf:
        signal, grund = "long", "SuperTrend auf, EMA20 ueber EMA50"
    elif st_richtung == -1 and e_ab:
        signal, grund = "short", "SuperTrend ab, EMA20 unter EMA50"
    else:
        signal, grund = "kein", "SuperTrend und EMA widersprechen sich"

    # RSI blockt nur das Nachlaufen, er dreht kein Signal um.
    if signal == "long" and rsi_jetzt is not None and rsi_jetzt > 78:
        signal, grund = "kein", "Long-Signal, aber RSI %.0f - ueberkauft" % rsi_jetzt
    if signal == "short" and rsi_jetzt is not None and rsi_jetzt < 22:
        signal, grund = "kein", "Short-Signal, aber RSI %.0f - ueberverkauft" % rsi_jetzt

    return {
        "kurs": kurs,
        "atr": a[-1],
        "atr_pct": (a[-1] / kurs) if a[-1] else None,
        "st_linie": linie[-1],
        "st_richtung": st_richtung,
        "st_dauer": dauer,
        "ema20": e20[-1], "ema50": e50[-1],
        "rsi": rsi_jetzt,
        "er": er,
        "signal": signal,
        "grund": grund,
    }

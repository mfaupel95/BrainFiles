"""TradingView-Familien-Indikatoren auf Kerzenreihen, reine Rechnung.

Eingabe ist immer eine Liste [ts, offen, hoch, tief, schluss, volumen],
aufsteigend sortiert, wie sie xperp.indikatoren bereitstellt. Jede Funktion
gibt eine Liste oder ein Tupel gleicher Laenge zurueck; die ersten Werte sind
None, solange das Fenster nicht voll ist. Das ist Absicht: ein mit dem ersten
Kurs aufgefuellter Indikator sieht Anfang nach einem Signal aus, keines ist.

Enthalten:
  squeeze_momentum  - LazyBear Squeeze Momentum (BB vs KC)
  macd              - MACD, Signal, Histogramm
  zu_hoeherem_zeitrahmen - OHLCV-Aggregation auf haeheren TF
  macd_mtf          - MACD Multiple Time Frame
  wavetrend         - LazyBear WaveTrend Oscillator

Nur Standardbibliothek (math). Kein Netzzugriff.
"""

import math


# --------------------------------------------------------------------------- #
# Hilfsfunktionen
# --------------------------------------------------------------------------- #

def _sma(werte, n):
    """Einfacher gleitender Mittelwert, None bis Fenster voll.

    None-Werte werden als 0 behandelt ( fuer wellenf?
    wo Zwischenwerte None sein koennen).
    """

    ausgabe = [None] * len(werte)
    if len(werte) < n:
        return ausgabe
    schritt = sum((v if v is not None else 0.0) for v in werte[:n]) / n
    ausgabe[n - 1] = schritt
    for i in range(n, len(werte)):
        neu = werte[i] if werte[i] is not None else 0.0
        alt = werte[i - n] if werte[i - n] is not None else 0.0
        schritt = schritt + (neu - alt) / n
        ausgabe[i] = schritt
    return ausgabe


def _ema(werte, n):
    """Exponentieller gleitender Mittelwert (Wilder-typisch).

    Startwert ist der SMA der ersten Werte, dann Glaettungsfaktor
    f = 2 / (n + 1). None am Anfang, solange Fenster unvollstaendig.
    None-Werte werden als 0 behandelt.
    """

    ausgabe = [None] * len(werte)
    if len(werte) < n:
        return ausgabe
    schritt = sum((v if v is not None else 0.0) for v in werte[:n]) / n
    ausgabe[n - 1] = schritt
    f = 2.0 / (n + 1)
    for i in range(n, len(werte)):
        aktuell = werte[i] if werte[i] is not None else 0.0
        schritt = aktuell * f + schritt * (1 - f)
        ausgabe[i] = schritt
    return ausgabe


def _atr(k, n=20):
    """Average True Range, Wilder-Glaettung. Erste Kerze hat None."""

    tr = [None] * len(k)
    for i in range(1, len(k)):
        tr[i] = max(
            k[i][2] - k[i][3],
            abs(k[i][2] - k[i - 1][4]),
            abs(k[i][3] - k[i - 1][4]),
        )
    ausgabe = [None] * len(k)
    if len(k) <= n:
        return ausgabe
    schneid = sum(tr[1 : n + 1]) / n
    ausgabe[n] = schneid
    for i in range(n + 1, len(k)):
        schneid = (schneid * (n - 1) + tr[i]) / n
        ausgabe[i] = schneid
    return ausgabe


def _lin_reg_wert(y_werte, fenster):
    """Endpunkt der linearen Regressionsgeraden ueber y_werte (len=fenster).

    Least Squares: slope = sum((xi - x_m) * (yi - y_m)) / sum((xi - x_m)^2)
    Rueckgabe: y_m + slope * (fenster - 1), also der Wert am rechten Rand.
    """

    n = fenster
    x_m = (n - 1) / 2.0
    y_m = sum(y_werte) / n
    zaehler = 0.0
    nenner = 0.0
    for i in range(n):
        dx = i - x_m
        zaehler += dx * (y_werte[i] - y_m)
        nenner += dx * dx
    if nenner == 0.0:
        return y_m
    slope = zaehler / nenner
    return y_m + slope * (n - 1)


# --------------------------------------------------------------------------- #
# squeeze_momentum
# --------------------------------------------------------------------------- #

def squeeze_momentum(k, laenge=20, bb_mult=2.0, kc_mult=1.5):
    """LazyBear Squeeze Momentum Indicator.

    Bollinger Band (SMA +/- mult * StdAbw) vs. Keltner Channel
    (EMA +/- mult * ATR).  Liegt BB innerhalb KC, ist Volatilitaets-
    kompression (squeeze_an = True).

    Gibt ein 3-Tupel zurueck:
      momentum  - lineare Regression von (schluss - basis) ueber das Fenster
      squeeze_an - True/False, None solange Fenster leer
      richtung  - +1 (steigend), -1 (fallend), 0 (gleich), None am Anfang
    """

    n = len(k)
    momentum = [None] * n
    squeeze_an = [None] * n
    richtung = [None] * n

    schliesse = [kerze[4] for kerze in k]
    sma = _sma(schliesse, laenge)

    # Bollinger: SMA und Standardabweichung
    bb_oben = [None] * n
    bb_unten = [None] * n
    for i in range(laenge - 1, n):
        fenster = schliesse[i - laenge + 1 : i + 1]
        mittel = sma[i]
        varianz = sum((x - mittel) ** 2 for x in fenster) / laenge
        std = math.sqrt(varianz)
        bb_oben[i] = mittel + bb_mult * std
        bb_unten[i] = mittel - bb_mult * std

    # Keltner: EMA und ATR
    ema_vals = _ema(schliesse, laenge)
    atr_vals = _atr(k, laenge)
    kc_oben = [None] * n
    kc_unten = [None] * n
    for i in range(laenge, n):
        if ema_vals[i] is not None and atr_vals[i] is not None:
            kc_oben[i] = ema_vals[i] + kc_mult * atr_vals[i]
            kc_unten[i] = ema_vals[i] - kc_mult * atr_vals[i]

    # Donchian-Mitte fuer die Regression
    for i in range(laenge - 1, n):
        fenster = k[i - laenge + 1 : i + 1]
        hoechstes = max(f[2] for f in fenster)
        tiefstes = min(f[3] for f in fenster)
        donchian_mitte = (hoechstes + tiefstes) / 2.0
        basis = (donchian_mitte + sma[i]) / 2.0

        y_werte = []
        for j in range(i - laenge + 1, i + 1):
            y_werte.append(schliesse[j] - basis)

        momentum[i] = _lin_reg_wert(y_werte, laenge)

    # squeeze_an: BB innerhalb KC
    for i in range(laenge, n):
        if bb_oben[i] is not None and kc_oben[i] is not None:
            squeeze_an[i] = (bb_oben[i] <= kc_oben[i]) and (bb_unten[i] >= kc_unten[i])

    # richtung
    for i in range(laenge, n):
        if momentum[i] is not None and momentum[i - 1] is not None:
            if momentum[i] > momentum[i - 1]:
                richtung[i] = 1
            elif momentum[i] < momentum[i - 1]:
                richtung[i] = -1
            else:
                richtung[i] = 0

    return momentum, squeeze_an, richtung


# --------------------------------------------------------------------------- #
# macd
# --------------------------------------------------------------------------- #

def macd(werte, schnell=12, langsam=26, signal=9):
    """MACD (Moving Average Convergence Divergence).

    macd_linie = EMA(schnell) - EMA(langsam)
    signal_linie = EMA(macd_linie, signal)
    histogramm = macd_linie - signal_linie

    Gibt ein 3-Tupel zurueck (macd_linie, signal_linie, histogramm).
    None am Anfang, solange nicht genug Werte vorhanden.
    werte muss eine Liste von Zahlen sein (nicht Kerzenlisten).
    """

    ema_schnell = _ema(werte, schnell)
    ema_langsam = _ema(werte, langsam)

    n = len(werte)
    macd_linie = [None] * n
    for i in range(n):
        if ema_schnell[i] is not None and ema_langsam[i] is not None:
            macd_linie[i] = ema_schnell[i] - ema_langsam[i]

    # Signal-Linie: EMA der MACD-Werte, aber nur ab dem Index, wo macd_linie
    # erstmals nicht None ist (index langsam - 1).
    start_idx = langsam - 1
    macd_fuer_signal = [
        macd_linie[i] if macd_linie[i] is not None else 0.0
        for i in range(start_idx, n)
    ]
    sig_raw = _ema(macd_fuer_signal, signal)

    signal_linie = [None] * n
    histogramm = [None] * n
    for i in range(len(sig_raw)):
        if sig_raw[i] is not None:
            idx = start_idx + i
            signal_linie[idx] = sig_raw[i]
            if macd_linie[idx] is not None:
                histogramm[idx] = macd_linie[idx] - sig_raw[i]

    return macd_linie, signal_linie, histogramm


# --------------------------------------------------------------------------- #
# zu_hoeherem_zeitrahmen
# --------------------------------------------------------------------------- #

def zu_hoeherem_zeitrahmen(k, faktor):
    """Kerzen zu einem hoeheren Zeitrahmen zusammenfassen.

    Je 'faktor' aufeinanderfolgende Kerzen werden zu einer zusammen:
      offen  = offen der ersten Kerze
      hoch   = Maximum aller Highs
      tief   = Minimum aller Lows
      schluss = Schluss der letzten Kerze
      volumen = Summe der Volumen
      ts     = Timestamp der ersten Kerze

    Rest am Ende wird verworfen, wenn er nicht vollstaendig ist.
    """

    ergebnis = []
    for start in range(0, len(k) - faktor + 1, faktor):
        gruppe = k[start : start + faktor]
        offen = gruppe[0][1]
        hoch = max(g[2] for g in gruppe)
        tief = min(g[3] for g in gruppe)
        schluss = gruppe[-1][4]
        volumen = sum(g[5] for g in gruppe)
        ts = gruppe[0][0]
        ergebnis.append([ts, offen, hoch, tief, schluss, volumen])
    return ergebnis


# --------------------------------------------------------------------------- #
# macd_mtf
# --------------------------------------------------------------------------- #

def macd_mtf(k, faktoren=(1, 4, 16), schnell=12, langsam=26, signal=9):
    """MACD Multiple Time Frame.

    Fuer jeden Faktor wird der Zeitrahmen mit zu_hoeherem_zeitrahmen()
    gebaut und macd() darauf gerechnet.

    Gibt ein dict zurueck:
      {faktor: {"macd": [...], "signal": [...], "hist": [...],
                "ausrichtung": +1/-1/0/None}}

    Zusaetzlich ein Schluessel "einig": True, wenn alle Zeitraeume
    dieselbe Ausrichtung haben (alle ungleich None).
    """

    ergebnis = {}
    ausrichtungen = []

    for faktor in faktoren:
        if faktor <= 1:
            tf_kerzen = k
        else:
            tf_kerzen = zu_hoeherem_zeitrahmen(k, faktor)

        # macd erwartet eine Liste von Zahlen, nicht Kerzenlisten
        schliesse = [kerze[4] for kerze in tf_kerzen]
        m, s, h = macd(schliesse, schnell, langsam, signal)

        # Ausrichtung = Vorzeichen des letzten Histogramm-Werts
        ausrichtung = None
        for i in range(len(h) - 1, -1, -1):
            if h[i] is not None:
                if h[i] > 0:
                    ausrichtung = 1
                elif h[i] < 0:
                    ausrichtung = -1
                else:
                    ausrichtung = 0
                break

        ausrichtungen.append(ausrichtung)
        ergebnis[faktor] = {
            "macd": m,
            "signal": s,
            "hist": h,
            "ausrichtung": ausrichtung,
        }

    alle_einig = (
        len(ausrichtungen) > 0
        and all(a is not None for a in ausrichtungen)
        and len(set(ausrichtungen)) == 1
    )
    ergebnis["einig"] = alle_einig

    return ergebnis


# --------------------------------------------------------------------------- #
# wavetrend
# --------------------------------------------------------------------------- #

def wavetrend(k, n1=10, n2=21):
    """LazyBear WaveTrend Oscillator.

    hlc3 = (hoch + tief + schluss) / 3
    esa  = EMA(hlc3, n1)
    d    = EMA(|hlc3 - esa|, n1)
    ci   = (hlc3 - esa) / (0.015 * d)    -- Division durch 0 abgefangen
    wt1  = EMA(ci, n2)
    wt2  = SMA(wt1, 4)

    Gibt ein 2-Tupel (wt1, wt2) zurueck.
    Wo Zwischenwerte None sind, bleibt die Ausgabe None.
    """

    n = len(k)
    hlc3 = [(kerze[2] + kerze[3] + kerze[4]) / 3.0 for kerze in k]

    esa = _ema(hlc3, n1)
    d_roh = [None] * n
    for i in range(n):
        if esa[i] is not None:
            d_roh[i] = abs(hlc3[i] - esa[i])

    # _ema kann None-Werte nicht handeln -> None durch 0.0 ersetzen
    d_roh_gesaeubert = [v if v is not None else 0.0 for v in d_roh]
    d = _ema(d_roh_gesaeubert, n1)

    ci = [None] * n
    for i in range(n):
        if esa[i] is not None and d[i] is not None and d[i] != 0.0:
            ci[i] = (hlc3[i] - esa[i]) / (0.015 * d[i])
        # Bei d == 0 oder fehlenden Werten bleibt ci[i] = None

    wt1 = _ema(ci, n2)
    # wt2 = SMA(wt1, 4) -- aber nur, wo alle vier wt1-Werte des Fensters
    # wirklich da sind. Wo Zwischenwerte None sind, bleibt wt2 None.
    wt2 = [None] * n
    for i in range(n):
        if i >= 3 and all(w is not None for w in wt1[i - 3 : i + 1]):
            wt2[i] = sum(wt1[i - 3 : i + 1]) / 4.0

    return wt1, wt2

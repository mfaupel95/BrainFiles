"""Ansatz B: Haus-Spuren vektorisiert - fuer schnellen Backtest und Hyperopt.

WARUM DIESE DATEI EXISTIERT
---------------------------
Spec Werkstatt/spec-freqtrade-hausspuren-2026-10-10.md, Phase 2. Der Adapter
(hausspur_regeln.signale) rechnet je Kerze die Haus-Regel auf ihrem Fenster
nach - richtig, aber O(Kerzen x Fenster) in reinem Python. Hier dieselbe
Entscheidung als numpy-Rechnung ueber die ganze Reihe.

Der Adapter bleibt die REFERENZ: jede Spur hier hat einen Gleichheitstest
(tests/test_hausspur_vektor.py, freqtrade/gleichheit.py), der Kerze fuer Kerze
Einstieg, Ausstiege, Stop und Ziel vergleicht. Erst bei gruenem Test darf ein
Bot mit `hausspur.rechnung: "vektor"` laufen.

Fenstertreue: Das Haus rechnet auf den letzten `fenster(w)` Kerzen, die EMA
startet dort mit dem SMA der ersten n Werte des FENSTERS. Ein EMA ueber die
ganze Reihe weicht davon ab ((1-2/201)^200 = 13,5 % Startgewicht bei n=200).
Darum laeuft die EMA hier je Kerze ab ihrem eigenen Fensterstart - alle
Kerzen gleichzeitig, Schritt fuer Schritt in derselben Rechenreihenfolge wie
klassik_regeln.ema. Das ist bitgleich, nicht nur "fast gleich".

Parameter kommen aus derselben wachen.json, Stop und Ziel aus derselben
Spur-Funktion wie im Adapter: nichts doppelt gepflegt.
"""

from __future__ import annotations

import numpy as np

import hausspur_regeln as hr


def _fensterstart(n_kerzen: int, w: dict):
    """Je Kerze i: Fensterstart s_i und Fensterlaenge L_i wie in hr.signale."""
    i = np.arange(n_kerzen)
    s = np.maximum(0, i + 1 - hr.fenster(w))
    return s, i + 1 - s


def _ema_im_fenster(c, s, n, versatz):
    """EMA(n) je Kerze i auf ihrem Fenster [s_i, i], gelesen an i - versatz.

    Wie klassik_regeln.ema: Start = sum(erste n)/n (sequentiell summiert),
    dann v = x*f + v*(1-f). NaN, wo der Wert im Fenster nicht existiert.
    """
    m = len(c)
    i = np.arange(m)
    ziel = i - versatz - (s + n - 1)          # Rekursionsschritte bis i - versatz
    ok = (ziel >= 0) & (s + n - 1 <= m - 1)
    v = np.zeros(m)
    for j in range(n):                        # sum() wie Python: 0 + x0 + x1 ...
        v = v + c[np.minimum(s + j, m - 1)]
    v = v / n
    f = 2.0 / (n + 1)
    schritte = int(ziel[ok].max()) if ok.any() else 0
    for t in range(1, schritte + 1):
        lauf = ok & (t <= ziel)
        x = c[np.minimum(s + n - 1 + t, m - 1)]
        v = np.where(lauf, x * f + v * (1 - f), v)
    return np.where(ok, v, np.nan)


def _kanal(werte, n, art):
    """Hoechstes Hoch/tiefstes Tief der n Kerzen VOR i (kanal_hoch/kanal_tief)."""
    aus = np.full(len(werte), np.nan)
    if len(werte) > n:
        fenster = np.lib.stride_tricks.sliding_window_view(werte, n)[:-1]
        aus[n:] = fenster.max(axis=1) if art == "hoch" else fenster.min(axis=1)
    return aus


def _donchian_trend(hoch, tief, c, w):
    s, laenge = _fensterstart(len(c), w)
    n_ein = int(w.get("kanal_ein_n", 20))
    n_aus = int(w.get("kanal_aus_n", 10))
    n_trend = int(w.get("trend_n", 200))
    steig = int(w.get("steigung_n", 20))

    # einstieg_donchian: Kanal braucht `bis >= n`, bis = L-1 im Fenster
    k_hoch, k_tief = _kanal(hoch, n_ein, "hoch"), _kanal(tief, n_ein, "tief")
    kanal_da = laenge - 1 >= n_ein
    roh_long = kanal_da & (c > k_hoch)
    roh_short = kanal_da & ~roh_long & (c < k_tief)

    # einstieg_donchian_trend: e[-1] und e[-1-s] im selben Fenster
    e = _ema_im_fenster(c, s, n_trend, 0)
    e_vor = _ema_im_fenster(c, s, n_trend, steig)
    trend_da = (laenge > steig) & ~np.isnan(e) & ~np.isnan(e_vor)
    long = roh_long & trend_da & (c > e) & (e > e_vor)
    short = roh_short & trend_da & (c < e) & (e < e_vor)

    # ausstieg_donchian (kanal_aus_n)
    a_tief, a_hoch = _kanal(tief, n_aus, "tief"), _kanal(hoch, n_aus, "hoch")
    aus_da = (laenge - 1 >= n_aus) & bool(w.get("ausstieg_bei_regel", True))
    aus_long = aus_da & (c < a_tief)
    aus_short = aus_da & (c > a_hoch)
    return long, short, aus_long, aus_short


VEKTOR = {"klassik_donchian_trend": _donchian_trend}


def hat(name: str) -> bool:
    return name in VEKTOR


def signale_arrays(hoch, tief, schluss, name: str, w: dict | None = None) -> dict:
    """Spalten wie hr.signale, aber als Arrays: einstieg (object), aus_long,
    aus_short (bool), stop, ziel (float, NaN wo das Haus nichts rechnet)."""
    if name not in VEKTOR:
        raise KeyError("keine Vektor-Fassung fuer %r (vorhanden: %s)"
                       % (name, ", ".join(VEKTOR)))
    w = dict(w if w is not None else hr.wachen(name))
    hoch = np.asarray(hoch, dtype=float)
    tief = np.asarray(tief, dtype=float)
    c = np.asarray(schluss, dtype=float)
    _, laenge = _fensterstart(len(c), w)
    gilt = laenge >= int(w.get("mindest_kerzen", 210))

    long, short, aus_long, aus_short = VEKTOR[name](hoch, tief, c, w)
    if w.get("nur_long"):
        short = np.zeros_like(short)
    einstieg = np.full(len(c), None, dtype=object)
    einstieg[gilt & long] = "long"
    einstieg[gilt & short] = "short"

    # Stop/Ziel aus der Spur-Funktion selbst (feste Prozente: kerzenunabhaengig)
    sp = hr.spur(name)
    stop = sp.stop_prozent([], w) or hr.STOP_VORGABE
    ziel = hr.ziel_wert(sp, [], w, "long", stop)
    return {"einstieg": einstieg,
            "aus_long": gilt & aus_long,
            "aus_short": gilt & aus_short,
            "stop": np.where(gilt, float(stop), np.nan),
            "ziel": np.where(gilt, float(ziel), np.nan)}


def signale(kerzen: list, name: str, w: dict | None = None) -> dict:
    """Wie signale_arrays, aus Kerzenlisten [ts, o, h, l, c, v]."""
    if not kerzen:
        return signale_arrays([], [], [], name, w)
    a = np.asarray([z[2:5] for z in kerzen], dtype=float)
    return signale_arrays(a[:, 0], a[:, 1], a[:, 2], name, w)

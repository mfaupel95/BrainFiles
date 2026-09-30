"""Klassische Kursregeln als Papierspuren - eine Rechnung fuer alle acht.

Herkunft: die sechs Pine-Vorlagen unter MaxHirn/Wiki/Handel/*.pine (Donchian,
EMA-Kreuz, MACD, RSI-Rueckkehr, SMA-Kreuz, Bollinger) plus zwei neue Regeln
(rsi2_trend, donchian_trend). Jede Spur ist ein Ordner mit einem Zweizeiler
`handeln.py`, der hier `spur_main(NAME)` ruft; Buch, Ratsche, Spiegelung und
Vorfilter liefert `spur_buch.py`.

Zwei Abweichungen von den Pine-Dateien, beide mit Absicht:

1. **Donchian:** Pine rechnet `ta.highest(high, 20)` INKLUSIVE der laufenden
   Kerze. Der Schluss kann aber nie ueber dem Hoch der eigenen Kerze liegen -
   `crossover(close, high20)` ist dort nie wahr, die Vorlage handelt nie. Hier
   zaehlt der Kanal der 20 Kerzen DAVOR.
2. **Nur abgeschlossene Kerzen.** OKX liefert die laufende Kerze mit; sie wird
   verworfen, sonst flackert ein Kreuz innerhalb der Stunde.

Regel je Spur: `einstieg(k, w)` -> "long" | "short" | None und
`ausstieg(k, seite, w)` -> Grund | None (Gegensignal bzw. Kanal/Mittellinie).
Alles reine Funktionen ueber Kerzenlisten [ts, o, h, l, c, v] - offline
testbar. Kein Sprachmodell, kein Live-Zweig.
"""

from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path

HANDEL = Path(__file__).resolve().parent


# --- Indikatoren (Listen gleicher Laenge, None wo noch nicht definiert) ------

def sma(w, n):
    out = [None] * len(w)
    if n <= 0 or len(w) < n:
        return out
    s = sum(w[:n])
    out[n - 1] = s / n
    for i in range(n, len(w)):
        s += w[i] - w[i - n]
        out[i] = s / n
    return out


def ema(w, n):
    """Start mit dem SMA der ersten n Werte (wie TradingView)."""
    out = [None] * len(w)
    if len(w) < n:
        return out
    v = sum(w[:n]) / n
    out[n - 1] = v
    f = 2.0 / (n + 1)
    for i in range(n, len(w)):
        v = w[i] * f + v * (1 - f)
        out[i] = v
    return out


def rsi(w, n=14):
    """Wilder-RSI wie ta.rsi."""
    out = [None] * len(w)
    if len(w) <= n:
        return out
    g = [max(0.0, w[i] - w[i - 1]) for i in range(1, len(w))]
    v = [max(0.0, w[i - 1] - w[i]) for i in range(1, len(w))]
    ag, av = sum(g[:n]) / n, sum(v[:n]) / n
    out[n] = 100.0 if av == 0 else 100 - 100 / (1 + ag / av)
    for i in range(n, len(g)):
        ag = (ag * (n - 1) + g[i]) / n
        av = (av * (n - 1) + v[i]) / n
        out[i + 1] = 100.0 if av == 0 else 100 - 100 / (1 + ag / av)
    return out


def bollinger(w, n=20, faktor=2.0):
    """(mitte, oben, unten); Standardabweichung der Grundgesamtheit wie Pine."""
    mitte = sma(w, n)
    oben, unten = [None] * len(w), [None] * len(w)
    for i in range(n - 1, len(w)):
        fenster = w[i - n + 1:i + 1]
        m = mitte[i]
        sd = (sum((x - m) ** 2 for x in fenster) / n) ** 0.5
        oben[i], unten[i] = m + faktor * sd, m - faktor * sd
    return mitte, oben, unten


def macd(w, schnell=12, langsam=26, signal=9):
    """(macd, signal) - Signal ist der EMA des MACD ab seinem ersten Wert."""
    es, el = ema(w, schnell), ema(w, langsam)
    linie = [None if a is None or b is None else a - b for a, b in zip(es, el)]
    start = next((i for i, x in enumerate(linie) if x is not None), None)
    sig = [None] * len(w)
    if start is not None:
        teil = ema(linie[start:], signal)
        for j, x in enumerate(teil):
            sig[start + j] = x
    return linie, sig


def kanal_hoch(k, n, bis):
    """Hoechstes Hoch der n Kerzen VOR Index `bis` (ohne `bis`)."""
    if bis < n:
        return None
    return max(float(z[2]) for z in k[bis - n:bis])


def kanal_tief(k, n, bis):
    if bis < n:
        return None
    return min(float(z[3]) for z in k[bis - n:bis])


def kreuzt_auf(a, b, i=-1):
    """`a` kreuzt `b` von unten nach oben auf Kerze i (a, b: Listen oder Zahl)."""
    return _kreuz(a, b, i, +1)


def kreuzt_ab(a, b, i=-1):
    return _kreuz(a, b, i, -1)


def _kreuz(a, b, i, richtung):
    def wert(x, j):
        return x if isinstance(x, (int, float)) else x[j]
    try:
        a1, b1 = wert(a, i), wert(b, i)
        a0, b0 = wert(a, i - 1), wert(b, i - 1)
    except IndexError:
        return False
    if None in (a1, b1, a0, b0):
        return False
    if richtung > 0:
        return a0 <= b0 and a1 > b1
    return a0 >= b0 and a1 < b1


# --- Die acht Regeln --------------------------------------------------------

def _schluesse(k):
    return [float(z[4]) for z in k]


def _lang_kurz(a, b, i=-1):
    """Kreuz zweier Linien -> long / short / None."""
    if kreuzt_auf(a, b, i):
        return "long"
    if kreuzt_ab(a, b, i):
        return "short"
    return None


def einstieg_sma(k, w):
    c = _schluesse(k)
    return _lang_kurz(sma(c, int(w.get("schnell_n", 20))),
                      sma(c, int(w.get("langsam_n", 50))))


def einstieg_ema(k, w):
    c = _schluesse(k)
    return _lang_kurz(ema(c, int(w.get("schnell_n", 12))),
                      ema(c, int(w.get("langsam_n", 26))))


def einstieg_macd(k, w):
    m, s = macd(_schluesse(k), int(w.get("schnell_n", 12)),
                int(w.get("langsam_n", 26)), int(w.get("signal_n", 9)))
    return _lang_kurz(m, s)


def einstieg_bollinger(k, w):
    c = _schluesse(k)
    _m, ob, un = bollinger(c, int(w.get("bb_n", 20)),
                           float(w.get("bb_faktor", 2.0)))
    if kreuzt_auf(c, ob):
        return "long"
    if kreuzt_ab(c, un):
        return "short"
    return None


def einstieg_donchian(k, w):
    n = int(w.get("kanal_ein_n", 20))
    i = len(k) - 1
    c = float(k[i][4])
    hoch, tief = kanal_hoch(k, n, i), kanal_tief(k, n, i)
    if hoch is None:
        return None
    if c > hoch:
        return "long"
    if c < tief:
        return "short"
    return None


def einstieg_rsi(k, w):
    r = rsi(_schluesse(k), int(w.get("rsi_n", 14)))
    if kreuzt_auf(r, float(w.get("rsi_unten", 30.0))):
        return "long"
    if kreuzt_ab(r, float(w.get("rsi_oben", 70.0))):
        return "short"
    return None


def einstieg_rsi2_trend(k, w):
    """Connors-Rueckkehr: RSI(2) extrem, aber NUR mit dem grossen Trend.

    Long: RSI(2) < 10 und Schluss ueber SMA200 - ein Ruecksetzer im
    Aufwaertstrend. Short spiegelbildlich (RSI(2) > 90, Schluss unter SMA200).
    Die Regel kauft keine fallenden Messer im Abwaertstrend.
    """
    c = _schluesse(k)
    r = rsi(c, int(w.get("rsi_n", 2)))
    trend = sma(c, int(w.get("trend_n", 200)))
    if r[-1] is None or trend[-1] is None:
        return None
    if r[-1] < float(w.get("rsi_unten", 10.0)) and c[-1] > trend[-1]:
        return "long"
    if r[-1] > float(w.get("rsi_oben", 90.0)) and c[-1] < trend[-1]:
        return "short"
    return None


def einstieg_donchian_trend(k, w):
    """Donchian-Ausbruch nur in Richtung der EMA200-Steigung.

    Der reine Ausbruch handelt in der Seitwaertsphase jeden Fehlausbruch. Der
    Filter verlangt: Long nur bei steigender EMA200 (Schluss darueber), Short
    nur bei fallender (Schluss darunter). Steigung ueber `steigung_n` Kerzen.
    """
    roh = einstieg_donchian(k, w)
    if roh is None:
        return None
    c = _schluesse(k)
    e = ema(c, int(w.get("trend_n", 200)))
    s = int(w.get("steigung_n", 20))
    if len(e) <= s or e[-1] is None or e[-1 - s] is None:
        return None
    if roh == "long" and c[-1] > e[-1] and e[-1] > e[-1 - s]:
        return "long"
    if roh == "short" and c[-1] < e[-1] and e[-1] < e[-1 - s]:
        return "short"
    return None


def _gegen_kreuz(einstieg_fn):
    """Ausstieg = das Gegensignal des Einstiegs (Pine: strategy.close bei Kreuz)."""
    def f(k, seite, w):
        s = einstieg_fn(k, w)
        if s and s != seite:
            return "gegensignal"
        return None
    return f


def ausstieg_donchian(k, seite, w):
    n = int(w.get("kanal_aus_n", 10))
    i = len(k) - 1
    c = float(k[i][4])
    if seite == "long":
        t = kanal_tief(k, n, i)
        return "kanal" if t is not None and c < t else None
    h = kanal_hoch(k, n, i)
    return "kanal" if h is not None and c > h else None


def ausstieg_rsi(k, seite, w):
    r = rsi(_schluesse(k), int(w.get("rsi_n", 14)))
    if seite == "long" and kreuzt_auf(r, float(w.get("rsi_aus_long", 55.0))):
        return "mitte"
    if seite == "short" and kreuzt_ab(r, float(w.get("rsi_aus_short", 45.0))):
        return "mitte"
    return None


def ausstieg_rsi2(k, seite, w):
    """Connors-Ausstieg: Schluss ueber (long) / unter (short) die SMA5."""
    c = _schluesse(k)
    s = sma(c, int(w.get("aus_sma_n", 5)))
    if s[-1] is None:
        return None
    if seite == "long" and c[-1] > s[-1]:
        return "sma5"
    if seite == "short" and c[-1] < s[-1]:
        return "sma5"
    return None


REGELN = {
    "klassik_sma":       (einstieg_sma, _gegen_kreuz(einstieg_sma)),
    "klassik_ema":       (einstieg_ema, _gegen_kreuz(einstieg_ema)),
    "klassik_macd":      (einstieg_macd, _gegen_kreuz(einstieg_macd)),
    "klassik_bollinger": (einstieg_bollinger, _gegen_kreuz(einstieg_bollinger)),
    "klassik_donchian":  (einstieg_donchian, ausstieg_donchian),
    "klassik_rsi":       (einstieg_rsi, ausstieg_rsi),
    "klassik_rsi2":      (einstieg_rsi2_trend, ausstieg_rsi2),
    "klassik_donchian_trend": (einstieg_donchian_trend, ausstieg_donchian),
}


# --- Anschluss an spur_buch --------------------------------------------------

def _lade(pfad, name):
    spec = importlib.util.spec_from_file_location(name, pfad)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


_okx = None
_cache = {}


def _kerzen(inst, bar, anzahl):
    """OKX-Kerzen, nur abgeschlossene; 60 s Zwischenspeicher je (inst, bar).

    Der Zwischenspeicher haelt Einstieg und Ausstieg im selben Zyklus auf
    DERSELBEN Kerzenreihe - zwei Abrufe koennten eine Kerze auseinanderliegen.
    """
    global _okx
    schluessel = (inst, bar, anzahl)
    jetzt = time.time()
    alt = _cache.get(schluessel)
    if alt and jetzt - alt[0] < 60:
        return alt[1]
    if _okx is None:
        sc = str(HANDEL / "scanner")
        if sc not in sys.path:
            sys.path.insert(0, sc)
        _okx = _lade(HANDEL / "scanner" / "okx.py", "okx_klassik")
    roh = _okx.kerzen(inst, bar=bar, anzahl=anzahl)
    k = roh[:-1] if roh else []          # laufende Kerze verwerfen
    _cache[schluessel] = (jetzt, k)
    return k


def bauen(name):
    """(quelle, signal, ausstieg) fuer die Spur `name` - Naht fuer Tests/Replay."""
    ein, aus = REGELN[name]

    def quelle(w):
        bar = w.get("kerzen_zeitrahmen", "4H")
        anzahl = int(w.get("kerzen_anzahl", 400))
        daten, kurse, fehler = {}, {}, []
        for inst in w.get("instrumente", ["BTC-USDT-SWAP"]):
            try:
                k = _kerzen(inst, bar, anzahl)
            except Exception as e:                             # noqa: BLE001
                fehler.append("%s: Kerzen nicht abrufbar (%s)" % (inst, str(e)[:100]))
                continue
            if not k:
                fehler.append("%s: keine Kerzen" % inst)
                continue
            daten[inst] = {"kerzen": k, "bar": bar}
            kurse[inst] = float(k[-1][4])
        return daten, kurse, fehler

    def signal(d, w):
        k = d.get("kerzen") or []
        if len(k) < int(w.get("mindest_kerzen", 210)):
            return None                  # lieber kein Signal als eines aus dem Nichts
        try:
            return ein(k, w)
        except Exception as e:                                 # noqa: BLE001
            print("  %s: Regel nicht rechenbar (%s)" % (name, e), file=sys.stderr)
            return None

    def ausstieg(p, w):
        if not w.get("ausstieg_bei_regel", True):
            return None
        inst = p.get("inst") or p.get("instrument")
        bar = w.get("kerzen_zeitrahmen", "4H")
        try:
            k = _kerzen(inst, bar, int(w.get("kerzen_anzahl", 400)))
        except Exception:                                      # noqa: BLE001
            return None
        if len(k) < int(w.get("mindest_kerzen", 210)):
            return None
        seite = (p.get("seite") or "").lower()
        if seite not in ("long", "short"):
            return None
        return aus(k, seite, w)

    return quelle, signal, ausstieg


def spur_main(name, ordner):
    """Gemeinsamer Startpunkt: `handeln.py` ruft nur noch dies."""
    import argparse
    quelle, signal, ausstieg = bauen(name)
    sp = _lade(HANDEL / "spur_buch.py", "spur_buch_" + name)
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = p.add_mutually_exclusive_group()
    for opt, c, h in (("--vorschau", "vorschau", "nur rechnen, nichts schreiben"),
                      ("--papier", "papier", "Papierbuch (Standard)"),
                      ("--live", "live", "verweigert: kein Live-Zweig"),
                      ("--wachen", "wachen", "nur den Wachenstand zeigen")):
        g.add_argument(opt, action="store_const", dest="modus", const=c, help=h)
    modus = p.parse_args().modus or "papier"
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if modus == "live":
        print("Live waere gesperrt durch: kein Live-Zweig in dieser Spur "
              "(Papier, Kursregel ohne Orderweg).")
        return 0
    return sp.zyklus(str(ordner), quelle, signal, modus,
                     ereignis_name="handel/" + name, zusatz_ausstieg=ausstieg)

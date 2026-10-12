"""Haus-Spuren als EINE Signal-Schnittstelle - fuer den Freqtrade-Adapter.

WARUM DIESE DATEI EXISTIERT
---------------------------
Auftrag Max 10.10.2026: moeglichst viele Spuren als Freqtrade-Dry-Run-Bots
(Spec: Werkstatt/spec-freqtrade-hausspuren-2026-10-10.md). Die Regeln leben im
Haus - in klassik_regeln.REGELN und in den handeln.py der Indikatorspuren.
Diese Datei macht daraus eine gemeinsame Form, damit die Freqtrade-Strategie
`HausSpur` nichts nachbauen muss: importiert, nicht nachgebaut.

Je Kerze wird die Regel auf DEMSELBEN Fenster gerechnet wie im Haus
(`kerzen_anzahl`, mindestens `mindest_kerzen`) - ein laengeres Fenster
veraendert EMA-Startwerte und damit Signale.

Kein Freqtrade, kein pandas: auf dem Host mit unittest pruefbar.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

HANDEL = Path(__file__).resolve().parent

KLASSIK = ("klassik_sma", "klassik_ema", "klassik_macd", "klassik_bollinger",
           "klassik_donchian", "klassik_rsi", "klassik_rsi2",
           "klassik_donchian_trend", "klassik_sr_breaks", "klassik_pmax",
           "klassik_supertrend")
INDIKATOR = ("macd_mtf", "squeeze", "wavetrend", "supertrend")
ALLE = KLASSIK + INDIKATOR + ("trendwende_btc", "orb")

STOP_VORGABE = 6.0          # wie die Moon-Dev-Bots, wenn die Spur keinen nennt
KEIN_HANDEL = -1.0          # Stop-Antwort "Haus handelt hier nicht" (Review M4)


@dataclass(frozen=True)
class Spur:
    name: str
    einstieg: Callable      # (k, w) -> "long" | "short" | None
    ausstieg: Callable      # (k, seite, w) -> Grund | None
    stop_prozent: Callable  # (k, w) -> float
    ziel_prozent: Callable  # (k, w, seite, stop) -> float


# --- Laden -------------------------------------------------------------------

_MODULE: dict = {}


def _lade(pfad: Path, modulname: str):
    if modulname in _MODULE:
        return _MODULE[modulname]
    spec = importlib.util.spec_from_file_location(modulname, pfad)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    _MODULE[modulname] = modul
    return modul


def _modul(name: str):
    """handeln.py der Spur `name` (Indikatorspuren, trendwende_btc, orb)."""
    return _lade(HANDEL / name / "handeln.py", "hausspur_%s" % name)


def wachen(name: str) -> dict:
    with (HANDEL / name / "wachen.json").open(encoding="utf-8") as f:
        return json.load(f)


def fenster(w: dict) -> int:
    return max(int(w.get("kerzen_anzahl") or 400), int(w.get("mindest_kerzen") or 0))


def zeitrahmen(name: str) -> str:
    if name == "orb":
        return "15m"                       # orb/handeln.py holt M15-Kerzen
    w = wachen(name)
    roh = w.get("kerzen_zeitrahmen") or w.get("kerzen_takt") or "1H"
    return roh.lower()


def _paar(inst: str) -> str:
    basis = inst.replace("_", "-").split("-")[0]
    return "%s/USDT:USDT" % basis


def paare(name: str) -> list[str]:
    w = wachen(name)
    roh = w.get("instrumente") or [w.get("instrument", "BTC-USDT-SWAP")]
    if isinstance(roh, dict):
        roh = list(roh)
    aus: list[str] = []
    for inst in roh:
        p = _paar(inst)
        if p not in aus:
            aus.append(p)
    return aus


# --- Bausteine ---------------------------------------------------------------

def _kein_ausstieg(_k, _seite, _w):
    return None


def _fester_stop(_k, w):
    return float(w.get("stop_prozent") or STOP_VORGABE)


def _ziel_r(_k, w, _seite, stop):
    return float(w.get("ziel_r_vielfaches") or 2.0) * stop


def _atr_stop(modul):
    """Stop wie in pruefe_einstieg der Indikatorspuren: ATR, in [min, max]."""
    def stop(k, w):
        idx = len(k) - 1
        atr = modul.atr_abs(k, idx, int(w.get("atr_n", 14)))
        unten = float(w.get("pflicht_stop_prozent_min", 5.0))
        if not atr or atr <= 0:
            return KEIN_HANDEL              # pruefe_einstieg bricht hier ab (M4)
        pct = max(atr / float(k[idx][4]) * 100.0, unten)
        return min(pct, float(w.get("pflicht_stop_prozent_max", 12.0)))
    return stop


def _klassik(name: str) -> Spur:
    kr = _lade(HANDEL / "klassik_regeln.py", "hausspur_klassik_regeln")
    ein, aus = kr.REGELN[name]

    def ausstieg(k, seite, w):
        if not w.get("ausstieg_bei_regel", True):
            return None
        return aus(k, seite, w)
    return Spur(name, ein, ausstieg, _fester_stop, _ziel_r)


def _indikator(name: str) -> Spur:
    modul = _modul(name)

    def einstieg(k, w):
        s = modul.signal(k, len(k) - 1, w)
        return s[0] if isinstance(s, tuple) else s

    ausstieg = _kein_ausstieg
    if name == "supertrend":
        def ausstieg(k, seite, w):
            linie, richtung = modul.supertrend_indikator(k, w)
            return modul.trailing_ausstieg({"seite": seite}, k, linie, richtung)
    return Spur(name, einstieg, ausstieg, _atr_stop(modul), _ziel_r)


def _trendwende() -> Spur:
    modul = _modul("trendwende_btc")

    def einstieg(k, w):
        return modul.signal({"kerzen": k}, w)

    def ausstieg(k, seite, w):
        # Dieselbe Rechnung wie trend_richtung() - nur ohne Netzabruf, auf
        # den Kerzen, die Freqtrade schon hat (alle abgeschlossen).
        if seite != "short" or not w.get("ausstieg_bei_rueckdreh", True):
            return None
        _, richtung = modul.xi.supertrend(
            k, n=int(w.get("supertrend_n", 10)),
            faktor=float(w.get("supertrend_faktor", 3.0)))
        return "rueckdreh" if richtung and richtung[-1] == 1 else None
    return Spur("trendwende_btc", einstieg, ausstieg, _fester_stop, _ziel_r)


def _orb() -> Spur:
    """ORB wie orb/handeln.py, auf Kerzen statt Netzabruf.

    Range = die ersten ZWEI M15-Kerzen ab 00:00 UTC (opening_range in
    handeln.py nimmt `im_fenster[:2]`). Ein Trade je Tag: nur die ERSTE
    Kerze, die ausserhalb schliesst. range_ok kommt aus wachen_orb.py -
    dieselbe Pruefung wie im Haus.
    """
    orb = str(HANDEL / "orb")
    scanner = str(HANDEL / "scanner")          # wachen_orb importiert wachen_pruefung
    for p in (scanner, orb):
        if p not in sys.path:
            sys.path.append(p)
    wo = _lade(HANDEL / "orb" / "wachen_orb.py", "hausspur_wachen_orb")

    def _tag(ts):
        return datetime.fromtimestamp(ts / 1000, timezone.utc)

    def _heute(k):
        tag = _tag(k[-1][0]).date()
        i = len(k) - 1
        while i > 0 and _tag(k[i - 1][0]).date() == tag:
            i -= 1
        heute = k[i:]
        if _tag(heute[0][0]).hour != 0 or _tag(heute[0][0]).minute != 0:
            return None                    # Tagesanfang fehlt im Fenster
        return heute

    def _range(k, w):
        heute = _heute(k)
        if not heute or len(heute) < 3:
            return None
        hoch = max(heute[0][2], heute[1][2])
        tief = min(heute[0][3], heute[1][3])
        if not wo.range_ok(hoch - tief, w.get("_paar") or w.get("instrument_aktiv"), w):
            return None
        return heute, hoch, tief

    def einstieg(k, w):
        r = _range(k, w)
        if not r:
            return None
        heute, hoch, tief = r
        # Gezaehlt wird das Kerzenende (Review M3): das Haus handelt erst nach
        # Schluss der Kerze, eine 22:45-Kerze also um 23:00.
        dauer_ms = heute[-1][0] - heute[-2][0]
        ende_min = (heute[-1][0] + dauer_ms - heute[0][0]) // 60_000
        schluss_min = 24 * 60 - int(w.get("letzter_einstieg_min_vor_schluss", 60))
        if ende_min >= schluss_min:
            return None
        for z in heute[2:-1]:
            if z[4] > hoch or z[4] < tief:
                return None                # heute schon ausgebrochen
        c = heute[-1][4]
        if c > hoch:
            return "long"
        if c < tief:
            return "short"
        return None

    def stop(k, w):
        r = _range(k, w)
        c = float(k[-1][4])
        if not r:
            return STOP_VORGABE
        _, hoch, tief = r
        abstand = (c - tief) if c >= hoch else (hoch - c)
        return max(abstand, 1e-9) / c * 100.0

    def ziel(k, w, _seite, stop_pct):
        r = _range(k, w)
        if not r:
            return 2.0 * stop_pct
        _, hoch, tief = r
        return float(w.get("ziel_k", 1.5)) * (hoch - tief) / float(k[-1][4]) * 100.0

    def ausstieg(k, _seite, _w):
        t = _tag(k[-1][0])
        return "session_ende" if (t.hour, t.minute) == (23, 45) else None

    return Spur("orb", einstieg, ausstieg, stop, ziel)


def _baue(name: str) -> Spur:
    if name in KLASSIK:
        return _klassik(name)
    if name in INDIKATOR:
        return _indikator(name)
    if name == "trendwende_btc":
        return _trendwende()
    return _orb()


_SPUREN: dict = {}


def spur(name: str) -> Spur:
    if name not in ALLE:
        raise KeyError("unbekannte Haus-Spur: %r (bekannt: %s)" % (name, ", ".join(ALLE)))
    if name not in _SPUREN:
        _SPUREN[name] = _baue(name)
    return _SPUREN[name]


# --- Rechnung je Kerze ---------------------------------------------------------

_GEMELDET: set = set()


def _sicher(fn, *args):
    """Eine Regel, die wirft, gibt kein Signal - wie klassik_regeln.bauen.

    Jeder Fehlertext wird nur einmal gemeldet (Review M9): im Backtest wirft
    sonst jede Kerze eine Zeile, ueber zwei Jahre M15 bis zu ~70k.
    """
    try:
        return fn(*args)
    except Exception as e:                                     # noqa: BLE001
        text = "%s: %s" % (type(e).__name__, e)
        if text not in _GEMELDET:
            _GEMELDET.add(text)
            print("  hausspur: Regel nicht rechenbar (%s)" % text, file=sys.stderr)
        return None


def signale(kerzen: list, name: str, w: dict | None = None,
            paar: str | None = None, ab: int = 0) -> list:
    s = spur(name)
    w = dict(w if w is not None else wachen(name))
    if paar:
        w["_paar"] = paar.split(":")[0].replace("/", "_")   # "BTC_USDT"
    fe = fenster(w)
    mindest = int(w.get("mindest_kerzen", 210))
    aus: list = [None] * len(kerzen)
    for i in range(max(0, ab), len(kerzen)):
        k = kerzen[max(0, i + 1 - fe):i + 1]
        if len(k) < mindest:
            continue
        seite = _sicher(s.einstieg, k, w)
        if seite not in ("long", "short"):
            seite = None
        if seite == "short" and w.get("nur_long"):
            seite = None
        stop = _sicher(s.stop_prozent, k, w) or STOP_VORGABE
        if stop == KEIN_HANDEL:
            seite, stop = None, STOP_VORGABE
        ziel = _sicher(s.ziel_prozent, k, w, seite or "long", stop) or 2.0 * stop
        aus[i] = {"einstieg": seite,
                  "aus_long": _sicher(s.ausstieg, k, "long", w),
                  "aus_short": _sicher(s.ausstieg, k, "short", w),
                  "stop": float(stop), "ziel": float(ziel)}
    return aus

"""Drei Indikator-Kandidaten auf 1H. Die Rechnung liegt in klassik_regeln, hier nichts doppelt."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import klassik_regeln as kr  # noqa: E402


def _schluss(kerzen):
    return [float(z[4]) for z in kerzen]


def _st_werte(w):
    # einstieg_supertrend liest atr_perioden/atr_multiplier; llm_stunde nennt sie st_*.
    return {"atr_perioden": w["st_atr_n"], "atr_multiplier": w["st_atr_multiplier"]}


def _ema_kreuz(c, w):
    """(vorher, jetzt) fuer EMA-schnell gegen EMA-langsam, None wenn zu wenig Kerzen."""
    f = kr.ema(c, w["ema_schnell_n"])
    s = kr.ema(c, w["ema_langsam_n"])
    if len(c) < 2 or None in (f[-1], s[-1], f[-2], s[-2]):
        return None
    return (f[-2] - s[-2], f[-1] - s[-1])


def kandidat(variante, kerzen, w):
    """'long' wenn der Kandidat auf der letzten (abgeschlossenen) Kerze steht, sonst None."""
    c = _schluss(kerzen)
    if variante == "ema1h":
        kreuz = _ema_kreuz(c, w)
        return "long" if kreuz and kreuz[0] <= 0 < kreuz[1] else None
    if variante == "rsi1h":
        r = kr.rsi(c, w["rsi_n"])
        t = kr.ema(c, w["trend_ema_n"])
        if len(c) < 2 or None in (r[-1], r[-2], t[-1]):
            return None
        kreuz = r[-2] <= w["rsi_unten"] < r[-1]
        return "long" if kreuz and c[-1] > t[-1] else None
    if variante == "st1h":
        return "long" if kr.einstieg_supertrend(kerzen, _st_werte(w)) == "long" else None
    raise ValueError(f"unbekannte Variante: {variante}")


def ausstieg(variante, kerzen, w):
    c = _schluss(kerzen)
    if variante == "ema1h":
        kreuz = _ema_kreuz(c, w)
        return bool(kreuz) and kreuz[0] >= 0 > kreuz[1]
    if variante == "rsi1h":
        r = kr.rsi(c, w["rsi_n"])
        return r[-1] is not None and r[-1] > w["rsi_aus_long"]
    if variante == "st1h":
        return kr.einstieg_supertrend(kerzen, _st_werte(w)) == "short"
    raise ValueError(f"unbekannte Variante: {variante}")


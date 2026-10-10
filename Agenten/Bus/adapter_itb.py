"""Adapter: signals.csv von intelligent-trading-bot -> Fremd-Signal im Bus.

Liest die LETZTE Zeile, uebersetzt buy_signal_column -> long, sell_signal_column
-> flat (ITB: Kauf eroeffnet, Verkauf schliesst), und schickt sie durch
fremd_signal.melden_signal (Schema + Tor). Das Signal traegt den Zeitpunkt des
Kerzenschlusses als ts_utc; ein spaet laufender Adapter wird deshalb vom
Stale-Verwurf gestoppt. Je Kerze wird hoechstens einmal gemeldet (Stand-Datei).
Es handelt nicht, wirft nie und kennt keinen Orderweg.
"""
import csv
import json
import os
import time
from datetime import datetime, timezone

import fremd_signal

QUELLE = "intelligent-trading-bot"


def _wahr(x):
    return str(x).strip().lower() in ("true", "1", "1.0")


def _ts(text):
    return int(datetime.fromisoformat(str(text).strip()).astimezone(timezone.utc).timestamp())


def signal_aus_zeile(zeile, instrument, bar_s=3600, size_pct=0.2, expiry_s=180,
                     mode="paper", venue="okx"):
    """Eine CSV-Zeile -> Signal-Dict oder None (kein/widerspruechliches Signal)."""
    buy = _wahr(zeile.get("buy_signal_column"))
    sell = _wahr(zeile.get("sell_signal_column"))
    if buy == sell:
        return None
    s = {"instrument": instrument, "venue": venue,
         "direction": "long" if buy else "flat", "source": QUELLE,
         "ts_utc": _ts(zeile["timestamp"]) + bar_s, "expiry_s": expiry_s, "mode": mode}
    if buy:
        s["size_pct"] = size_pct
    return s


def _letzte_zeile(pfad):
    letzte = None
    with open(pfad, encoding="utf-8", newline="") as f:
        for letzte in csv.DictReader(f):
            pass
    if letzte is None or "timestamp" not in letzte:
        raise ValueError("signals.csv leer oder ohne timestamp")
    return letzte


def _stand_lesen(pfad):
    try:
        with open(pfad, encoding="utf-8") as f:
            return json.load(f).get("letzte_kerze")
    except (OSError, ValueError):
        return None


def lauf(csv_pfad, stand_pfad, instrument, bar_s=3600, size_pct=0.2, expiry_s=180,
         jetzt=None, port=None, wurzel=None, wache=None):
    """(status, ok, grund). status: gemeldet | schon_gemeldet | kein_signal | fehler."""
    try:
        zeile = _letzte_zeile(csv_pfad)
        kerze = zeile["timestamp"]
        if _stand_lesen(stand_pfad) == kerze:
            return "schon_gemeldet", None, kerze
        sig = signal_aus_zeile(zeile, instrument, bar_s, size_pct, expiry_s)
        if sig is None:
            return "kein_signal", None, kerze
        ok, grund = fremd_signal.melden_signal(
            "fremd/" + QUELLE, sig, jetzt=jetzt if jetzt is not None else time.time(),
            port=port, wurzel=wurzel, wache=wache)
        with open(stand_pfad, "w", encoding="utf-8") as f:
            json.dump({"letzte_kerze": kerze}, f)
        return "gemeldet", ok, grund
    except Exception as f:                                  # noqa: BLE001
        return "fehler", None, "%s: %s" % (type(f).__name__, f)

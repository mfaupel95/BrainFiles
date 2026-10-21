"""Adapter: Empfehlungs-CSV von moon-dev-ai-agents -> Fremd-Signal im Bus.

Liest src/data/ai_analysis_buys.csv (oder ai_analysis.csv) des Repos: je Zeile ein
Token mit den Empfehlungen zweier Agenten (BUY / SELL / DO NOTHING). Regel:
  beide BUY            -> long (size_pct)
  beide SELL           -> flat (Spot kann nicht short)
  alles andere         -> kein Signal (Uneinigkeit ist keine Empfehlung)
Instrument = SYMBOL-USDC (OKX-Spot); was nicht in instrumente_erlaubt der Wache steht
(die meisten Memecoins), wird VOR dem Bus verworfen und macht kein Journal-Rauschen.
Nur neue Zeilen (Stand = Zeilenzahl). ts_utc = Zeilen-timestamp (naive Zeit gilt als
lokal); ein spaet laufender Adapter wird vom Stale-Verwurf gestoppt. Handelt nie, wirft nie.
"""
import csv
import json
import time
from datetime import datetime

import fremd_signal

QUELLE = "moon-dev-ai-agents"


def _ts(text):
    return int(datetime.fromisoformat(str(text).strip()).astimezone().timestamp())


def signal_aus_zeile(z, erlaubt=None, size_pct=0.2, expiry_s=180, mode="paper"):
    """Eine CSV-Zeile -> Signal-Dict oder None."""
    a = str(z.get("agent_one_recommendation", "")).strip().upper()
    b = str(z.get("agent_two_recommendation", "")).strip().upper()
    sym = str(z.get("symbol", "")).strip().upper()
    if a != b or a not in ("BUY", "SELL") or not sym.isalnum() or not z.get("timestamp"):
        return None
    inst = sym + "-USDC"
    if erlaubt is not None and inst not in erlaubt:
        return None
    s = {"instrument": inst, "venue": "okx", "direction": "long" if a == "BUY" else "flat",
         "source": QUELLE, "ts_utc": _ts(z["timestamp"]), "expiry_s": expiry_s, "mode": mode}
    if a == "BUY":
        s["size_pct"] = size_pct
    return s


def _stand_lesen(pfad):
    try:
        with open(pfad, encoding="utf-8") as f:
            return int(json.load(f).get("zeilen", 0))
    except (OSError, ValueError, TypeError):
        return 0


def lauf(csv_pfad, stand_pfad, size_pct=0.2, expiry_s=180, mode="paper",
         jetzt=None, port=None, wurzel=None, wache=None):
    """(status, gemeldet, uebersprungen). status: ok | fehler."""
    try:
        with open(csv_pfad, encoding="utf-8", newline="") as f:
            zeilen = list(csv.DictReader(f))
        start = _stand_lesen(stand_pfad)
        if start > len(zeilen):
            start = 0
        w = wache if wache is not None else fremd_signal._tor().lade()
        erlaubt = set((w or {}).get("instrumente_erlaubt") or [])
        gemeldet = uebersprungen = 0
        for z in zeilen[start:]:
            sig = signal_aus_zeile(z, erlaubt, size_pct, expiry_s, mode)
            if sig is None:
                uebersprungen += 1
                continue
            ok, _ = fremd_signal.melden_signal(
                "fremd/" + QUELLE, sig, jetzt=jetzt if jetzt is not None else time.time(),
                port=port, wurzel=wurzel, wache=wache)
            gemeldet += 1
            uebersprungen += 0 if ok else 1
        with open(stand_pfad, "w", encoding="utf-8") as f:
            json.dump({"zeilen": len(zeilen)}, f)
        return "ok", gemeldet, uebersprungen
    except Exception as f:                                  # noqa: BLE001
        return "fehler", 0, "%s: %s" % (type(f).__name__, f)

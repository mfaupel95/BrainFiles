"""Adapter: Absichtszeilen einer nautilus_trader-Strategie -> Fremd-Signal im Bus.

Nautilus selbst bleibt unangetastet und braucht keine Anbindung an Boersen: eine
Strategie schreibt statt zu ordern je Entscheidung EINE JSON-Zeile in eine Datei
(Beispiel unten). Dieser Adapter liest nur neue Zeilen (Stand = Zeilenzahl),
uebersetzt sie und schickt sie durch fremd_signal.melden_signal (Schema + Tor).

Zeile: {"ts_event": <ns oder s>, "instrument_id": "BTC-USDC.OKX", "side": "BUY"|"SELL"}
  BUY  -> long (size_pct), SELL -> flat (Spot kann nicht short)
  instrument_id "SYMBOL.VENUE": OKX -> "SYMBOL" (z. B. BTC-USDC), KRAKEN -> "BASE/USD".
Das Signal traegt ts_event als ts_utc; ein spaet laufender Adapter wird vom
Stale-Verwurf gestoppt. Handelt nie, wirft nie, kennt keinen Orderweg.

Strategie-Seite (Nautilus, in on_bar statt submit_order):
    with open("nautilus_intents.jsonl", "a") as f:
        f.write(json.dumps({"ts_event": self.clock.timestamp_ns(),
                            "instrument_id": str(bar.bar_type.instrument_id),
                            "side": "BUY"}) + "\n")
"""
import json
import os
import time

import fremd_signal

QUELLE = "nautilus_trader"


def _sekunden(ts):
    ts = float(ts)
    return int(ts / 1e9) if ts > 1e12 else int(ts)


def instrument_aus_id(instrument_id):
    """('BTC-USDC.OKX') -> ('BTC-USDC', 'okx'); unbekannt -> None."""
    sym, _, ven = str(instrument_id).rpartition(".")
    ven = ven.strip().lower()
    if not sym or ven not in ("okx", "kraken"):
        return None
    if ven == "kraken":
        sym = sym.replace("XBT", "BTC")
        if "/" not in sym:
            return None
    return sym, ven


def signal_aus_zeile(z, size_pct=0.2, expiry_s=180, mode="paper"):
    """Eine Absichtszeile -> Signal-Dict oder None."""
    ziel = instrument_aus_id(z.get("instrument_id"))
    side = str(z.get("side", "")).strip().upper()
    if ziel is None or side not in ("BUY", "SELL") or "ts_event" not in z:
        return None
    s = {"instrument": ziel[0], "venue": ziel[1],
         "direction": "long" if side == "BUY" else "flat", "source": QUELLE,
         "ts_utc": _sekunden(z["ts_event"]), "expiry_s": expiry_s, "mode": mode}
    if side == "BUY":
        s["size_pct"] = size_pct
    return s


def _stand_lesen(pfad):
    try:
        with open(pfad, encoding="utf-8") as f:
            return int(json.load(f).get("zeilen", 0))
    except (OSError, ValueError, TypeError):
        return 0


def lauf(jsonl_pfad, stand_pfad, size_pct=0.2, expiry_s=180, mode="paper",
         jetzt=None, port=None, wurzel=None, wache=None):
    """(status, gemeldet, verworfen). status: ok | fehler. Ungueltige Zeilen zaehlen als verworfen."""
    try:
        with open(jsonl_pfad, encoding="utf-8") as f:
            zeilen = f.read().splitlines()
        start = _stand_lesen(stand_pfad)
        if start > len(zeilen):
            start = 0  # Datei wurde neu angelegt
        gemeldet = verworfen = 0
        for roh in zeilen[start:]:
            try:
                z = json.loads(roh)
                sig = signal_aus_zeile(z, size_pct, expiry_s, mode) if isinstance(z, dict) else None
            except ValueError:
                sig = None
            if sig is None:
                verworfen += 1
                continue
            ok, _ = fremd_signal.melden_signal(
                "fremd/" + QUELLE, sig, jetzt=jetzt if jetzt is not None else time.time(),
                port=port, wurzel=wurzel, wache=wache)
            gemeldet += 1 if ok else 0
            verworfen += 0 if ok else 1
        with open(stand_pfad, "w", encoding="utf-8") as f:
            json.dump({"zeilen": len(zeilen)}, f)
        return "ok", gemeldet, verworfen
    except Exception as f:                                  # noqa: BLE001
        return "fehler", 0, "%s: %s" % (type(f).__name__, f)

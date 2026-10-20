"""Uebersetzer: ITB-Signalexport -> Signal-Dicts fuer das fremd_signale-Tor.

ITB schreibt je Lauf eine CSV mit den boolschen Spalten buy/sell (Export in
ITB-Fork, outputs/notifier_trades.py). Dieses Modul macht daraus Signal-Dicts
in der Form von signal_schema.pruefe. Es handelt nicht und prueft nicht; die
Pruefung bleibt bei signal_schema und fremd_tor.

Regeln
------
* buy -> long. size_pct ist 0.5 (= size_pct_max in wachen.json): fremd_papier
  rechnet min(Risiko / Stop, 0.5 x max_pro_trade) = min(125, 125) = 125 USD,
  also 5 USD Risiko bei 4 % Stop.
* sell ohne buy -> flat (Ausstieg, braucht keine Groesse).
* buy und sell zugleich, oder keins von beiden -> kein Signal.
* venue okx, mode paper, source intelligent-trading-bot, expiry_s 1800 (halbe
  Stundenkerze, freq 1h laut config-okx-in-sample.json).
"""
import csv

QUELLE = "intelligent-trading-bot"
VENUE = "okx"
MODUS = "paper"
EXPIRY_S = 1800
GROESSE = 0.5
SPALTEN = ("instrument", "ts_utc", "buy", "sell")


def _wahr(wert):
    return str(wert).strip().lower() in ("true", "1")


def uebersetze_zeile(zeile):
    """Eine CSV-Zeile -> Signal-Dict, oder None wenn kein Signal entsteht."""
    buy, sell = _wahr(zeile["buy"]), _wahr(zeile["sell"])
    if buy == sell:
        return None
    signal = {
        "instrument": zeile["instrument"],
        "venue": VENUE,
        "direction": "long" if buy else "flat",
        "source": QUELLE,
        "ts_utc": int(float(zeile["ts_utc"])),
        "expiry_s": EXPIRY_S,
        "mode": MODUS,
    }
    if buy:
        signal["size_pct"] = GROESSE
    return signal


def uebersetze(zeilen):
    """Alle Zeilen uebersetzen, die ein Signal ergeben. Stale-Pruefung macht das Tor."""
    return [s for s in (uebersetze_zeile(z) for z in zeilen) if s is not None]


def lese_export(pfad):
    """ITB-CSV lesen. Fehlt eine Pflichtspalte, bricht das mit ValueError ab."""
    with open(pfad, encoding="utf-8", newline="") as f:
        leser = csv.DictReader(f)
        fehlt = [s for s in SPALTEN if s not in (leser.fieldnames or [])]
        if fehlt:
            raise ValueError("ITB-Export ohne Spalten: %s" % ", ".join(fehlt))
        return list(leser)

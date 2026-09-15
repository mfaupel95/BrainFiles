"""Datenbeschaffung fuer die IV-Wand-Spur (Deribit, oeffentlich, kein Schluessel).

Quellen (alles oeffentlich, ohne Anmeldung):
  - Indexpreis:      /public/get_index_price
  - DVOL (30-Tage-IV-Index): /public/get_volatility_index_data
  - Kurse:           /public/get_tradingview_chart_data
  - Optionskette:    /public/get_book_summary_by_currency

Antworten werden unter daten/ zwischengespeichert, damit ein Backtestlauf nicht
bei jedem Aufruf neu laedt (Deribit begrenzt Anfragen).
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASIS = "https://www.deribit.com/api/v2"
HIER = Path(__file__).resolve().parent
CACHE = HIER / "daten"

# Deribit liefert hoechstens 5000 Kerzen je Anfrage.
KERZEN_MAX = 5000


def _holen(pfad: str, versuche: int = 3, **parameter) -> dict:
    frage = urllib.parse.urlencode(parameter)
    url = f"{BASIS}/{pfad}" + (f"?{frage}" if frage else "")
    letzter = None
    for versuch in range(versuche):
        try:
            with urllib.request.urlopen(url, timeout=30) as antwort:
                daten = json.load(antwort)
            if "result" in daten:
                return daten["result"]
            raise RuntimeError(f"Deribit-Antwort ohne result: {str(daten)[:200]}")
        except (urllib.error.URLError, OSError, ValueError, RuntimeError) as fehler:
            letzter = fehler
            time.sleep(1.5 * (versuch + 1))
    raise RuntimeError(f"Deribit nicht erreichbar ({pfad}): {letzter}")


def _aus_cache(name: str, frische_sekunden: int):
    pfad = CACHE / name
    if not pfad.exists():
        return None
    if time.time() - pfad.stat().st_mtime > frische_sekunden:
        return None
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _in_cache(name: str, inhalt) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / name).write_text(json.dumps(inhalt), encoding="utf-8")


def indexpreis(index: str = "btc_usd") -> float:
    return float(_holen("public/get_index_price", index_name=index)["index_price"])


def dvol_tagesreihe(waehrung: str = "BTC", tage: int = 400, frisch: bool = False) -> list:
    """Tages-DVOL. Rueckgabe: [[ts_ms, open, high, low, close], ...] aufsteigend."""
    name = f"dvol_{waehrung.lower()}_{tage}.json"
    if not frisch:
        gespeichert = _aus_cache(name, 60 * 60 * 6)
        if gespeichert:
            return gespeichert
    ende = int(time.time() * 1000)
    beginn = ende - int(tage * 86400 * 1000)
    reihe = _holen(
        "public/get_volatility_index_data",
        currency=waehrung,
        start_timestamp=beginn,
        end_timestamp=ende,
        resolution="1D",
    )["data"]
    _in_cache(name, reihe)
    return reihe


def minutenkerzen(instrument: str = "BTC-PERPETUAL", aufloesung: str = "60",
                  tage: int = 400, frisch: bool = False) -> dict:
    """Minuten-/Stundenkerzen, in Bloecken von hoechstens 5000 Stueck geblaettert.

    Rueckgabe: {"ticks": [...ms...], "open" / "high" / "low" / "close" / "volume": [...]}
    """
    name = f"kerzen_{instrument}_{aufloesung}_{tage}.json"
    if not frisch:
        gespeichert = _aus_cache(name, 60 * 60 * 6)
        if gespeichert:
            return gespeichert
    einheit = 60 if aufloesung == "60" else (3600 if aufloesung == "1D" else 60)
    schritt = KERZEN_MAX * einheit * 1000
    ende = int(time.time() * 1000)
    beginn_gesamt = ende - int(tage * 86400 * 1000)
    saetze = {}
    beginn = beginn_gesamt
    while beginn < ende:
        block_ende = min(beginn + schritt, ende)
        antwort = _holen(
            "public/get_tradingview_chart_data",
            instrument_name=instrument,
            start_timestamp=beginn,
            end_timestamp=block_ende,
            resolution=aufloesung,
        )
        if antwort.get("status") != "ok":
            raise RuntimeError(f"Kerzenabruf fehlgeschlagen: {antwort.get('status')}")
        for i, tick in enumerate(antwort["ticks"]):
            saetze[tick] = tuple(antwort[f][i] for f in ("open", "high", "low", "close", "volume"))
        beginn = block_ende
    ticks = sorted(saetze)
    gebuendelt = {
        "ticks": ticks,
        "open": [saetze[t][0] for t in ticks],
        "high": [saetze[t][1] for t in ticks],
        "low": [saetze[t][2] for t in ticks],
        "close": [saetze[t][3] for t in ticks],
        "volume": [saetze[t][4] for t in ticks],
    }
    _in_cache(name, gebuendelt)
    return gebuendelt


def optionskette(waehrung: str = "BTC", frisch: bool = False) -> list:
    """Alle Optionsinstrumente mit offenem Interesse und Markt-IV (Momentaufnahme)."""
    name = f"optionen_{waehrung.lower()}.json"
    if not frisch:
        gespeichert = _aus_cache(name, 60 * 15)
        if gespeichert:
            return gespeichert
    kette = _holen("public/get_book_summary_by_currency", currency=waehrung, kind="option")
    _in_cache(name, kette)
    return kette

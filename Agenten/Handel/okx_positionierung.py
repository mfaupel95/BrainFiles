"""Positionierungs-Signale von OKX - oeffentlich, ohne Schluessel.

HERKUNFT (20.10.2026): Ersatz fuer das smartmoney-Modul aus
Werkstatt/agent-trade-kit. Dessen Endpunkte (/api/v5/journal/smartmoney/*)
liegen NUR auf dem globalen Host www.okx.com und verlangen einen privaten
Schluessel; der Haus-Schluessel ist ein EEA-Account-Key und antwortet dort mit
50119 "API key doesn't exist" (geprueft 20.10.2026). Dieselbe Frage - "kippt
die Positionierung?" - beantworten die oeffentlichen Rubik-Endpunkte, die auf
BEIDEN Hosts ohne Schluessel mit 200 antworten.

DREI SIGNALE (alle 1H, passend zum Takt der Spur):
  1. long_short_ratio  - Verhaeltnis Long-/Short-Konten (Masse-Positionierung).
     Faellt es schnell, loesen Longs auf: Abwaertswende wahrscheinlicher.
  2. open_interest      - offene Kontrakte in USD. Abbau bei fallendem Preis =
     Positionsauflösung, kein neues Geld gegen den Trend.
  3. taker_flow          - Kauf- gegen Verkaufsvolumen der Taker (aktiver Druck).
     Dreht das Verhaeltnis auf die Verkaufsseite, traegt der Fluss die Wende.

Rein lesend. Jede Funktion faellt bei Netz-/Formatfehlern auf None zurueck -
ein fehlendes Signal darf die Spur nie blockieren (fail-soft wie bei allen
Fremdquellen im Haus).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

KOPF = {"User-Agent": "Mozilla/5.0 (Handel/positionierung)"}
ZEIT_AUS = 15


def _basis() -> str:
    """Host wie scanner/okx.py: OKX_BASE, sonst der globale Host."""
    return (os.environ.get("OKX_BASE") or "https://www.okx.com").rstrip("/")


def _hol(pfad: str):
    """GET auf einen oeffentlichen Endpunkt. None bei jedem Fehler."""
    try:
        req = urllib.request.Request(_basis() + pfad, headers=KOPF)
        with urllib.request.urlopen(req, timeout=ZEIT_AUS) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, OSError, ValueError):
        return None
    if str(d.get("code")) != "0":
        return None
    reihen = d.get("data") or []
    return reihen or None


def long_short_ratio(ccy: str = "BTC", takt: str = "1H", anzahl: int = 24):
    """Long/Short-Konten-Verhaeltnis, neueste Reihe zuerst.

    Rueckgabe: Liste [(ts_ms, wert), ...] oder None.
    """
    reihen = _hol("/api/v5/rubik/stat/contracts/long-short-account-ratio"
                  "?ccy=%s&period=%s&limit=%d" % (ccy, takt, int(anzahl)))
    if not reihen:
        return None
    aus = []
    for r in reihen:
        try:
            aus.append((int(r[0]), float(r[1])))
        except (IndexError, TypeError, ValueError):
            continue
    return aus or None


def open_interest(ccy: str = "BTC", takt: str = "1H", anzahl: int = 24):
    """Offene Kontrakte (USD) und Volumen, neueste Reihe zuerst.

    Rueckgabe: Liste [(ts_ms, oi_usd, volumen_usd), ...] oder None.
    """
    reihen = _hol("/api/v5/rubik/stat/contracts/open-interest-volume"
                  "?ccy=%s&period=%s&limit=%d" % (ccy, takt, int(anzahl)))
    if not reihen:
        return None
    aus = []
    for r in reihen:
        try:
            aus.append((int(r[0]), float(r[1]), float(r[2])))
        except (IndexError, TypeError, ValueError):
            continue
    return aus or None


def taker_flow(ccy: str = "BTC", takt: str = "1H", anzahl: int = 24):
    """Taker-Volumen Verkauf/Kauf, neueste Reihe zuerst.

    OKX liefert [ts, sellVol, buyVol]. Rueckgabe:
    Liste [(ts_ms, verkauf, kauf), ...] oder None.
    """
    reihen = _hol("/api/v5/rubik/stat/taker-volume"
                  "?ccy=%s&instType=CONTRACTS&period=%s&limit=%d"
                  % (ccy, takt, int(anzahl)))
    if not reihen:
        return None
    aus = []
    for r in reihen:
        try:
            aus.append((int(r[0]), float(r[1]), float(r[2])))
        except (IndexError, TypeError, ValueError):
            continue
    return aus or None


def kipp_abwaerts(ccy: str = "BTC", takt: str = "1H",
                  ls_abfall_min: float = 0.02,
                  oi_abbau_min: float = 0.0,
                  takervolumen_min: float = 1.0):
    """Stuetzt die Positionierung eine ABWAERTS-Wende?

    Drei Teilurteile, jedes einzeln None-tolerant:
      - ls_faellt:   Long/Short-Verhaeltnis ist gegenueber dem Mittel der
                     Vorperioden um mindestens `ls_abfall_min` gefallen
                     (Longs loesen auf).
      - oi_faellt:   Open Interest ist gegenueber der Vorperiode gefallen
                     (mindestens `oi_abbau_min` relativ) - kein neues Geld.
      - verkaufsdruck: Taker-Verkauf/Kauf liegt ueber `takervolumen_min`.

    Rueckgabe: Dict mit den Teilurteilen und `stuetzt` (alle verfuegbaren
    Teilurteile positiv UND mindestens eines verfuegbar). Fehlt eine Quelle,
    steht ihr Feld auf None und zaehlt nicht gegen das Urteil.
    """
    urteil = {"ls_faellt": None, "oi_faellt": None,
              "verkaufsdruck": None, "stuetzt": False, "quellen": 0}

    ls = long_short_ratio(ccy, takt, 6)
    if ls and len(ls) >= 3:
        jetzt = ls[0][1]
        mittel = sum(w for _, w in ls[1:]) / float(len(ls) - 1)
        urteil["ls_faellt"] = bool(mittel - jetzt >= float(ls_abfall_min))
        urteil["ls_jetzt"] = jetzt
        urteil["ls_mittel"] = round(mittel, 4)

    oi = open_interest(ccy, takt, 3)
    if oi and len(oi) >= 2:
        jetzt, vor = oi[0][1], oi[1][1]
        rel = (vor - jetzt) / vor if vor else 0.0
        urteil["oi_faellt"] = bool(rel >= float(oi_abbau_min))
        urteil["oi_rel"] = round(rel, 6)

    tf = taker_flow(ccy, takt, 2)
    if tf:
        verkauf, kauf = tf[0][1], tf[0][2]
        quote = (verkauf / kauf) if kauf else None
        if quote is not None:
            urteil["verkaufsdruck"] = bool(quote >= float(takervolumen_min))
            urteil["taker_quote"] = round(quote, 4)

    teil = [urteil[k] for k in ("ls_faellt", "oi_faellt", "verkaufsdruck")
            if urteil[k] is not None]
    urteil["quellen"] = len(teil)
    urteil["stuetzt"] = bool(teil) and all(teil)
    return urteil


if __name__ == "__main__":
    import pprint
    pprint.pprint(kipp_abwaerts())

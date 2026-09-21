#!/usr/bin/env python3
"""Trendwende-BTC: SHORT, sobald der Trend auf 1H nach unten dreht.

AUFTRAG Max 21.09.2026: "Baue einen Agenten, der BTCUSD xperp short setzt,
sobald der Trend wendet."

WAS HIER LAEUFT (eine Regel, nachrechenbar, kein Sprachmodell):
  1. Daten: BTC-Kerzen 1H (OKX, oeffentlich, ueber scanner/okx.kerzen).
  2. Trend: SuperTrend(10, 3.0) aus xperp/indikatoren.py - dieselbe Quelle wie
     die Spur `supertrend`, damit es nicht zwei Wahrheiten gibt.
  3. Wendepunkt: die Richtung der letzten ABGESCHLOSSENEN Kerze wechselt von
     +1 (aufwaerts) auf -1 (abwaerts). Nur der WECHSEL zaehlt, nicht der
     Zustand: sonst stuende die Spur jede Kerze wieder short.
  4. Filter: der Schlusskurs liegt unter der EMA200 - ein Wendepunkt gegen
     einen intakten Aufwaertstrend ist meist nur ein Ruecksetzer.
  Erst wenn (3) UND (4) stimmen, geht die Spur short.

BUCH: Papier. Kein Live-Zweig, --live verweigert (Auftrag Max: Live nur ueber
die Freigabekette; hier erst einmal beobachten). Buch, Ratsche, Spiegelung und
Vorfilter kommen aus Handel/spur_buch.py - eine Buchhaltung fuer alle Buch-Spuren.

Instrument: BTC-USDT-SWAP (der liquide Perpetual auf OKX). Wird die Spur je
live genommen, uebersetzt spur_buch.venue_inst() sie auf das Boersenpaar; fuer
OKX-XPERP waere das ein datierter Kontrakt (BTC-USD_UM_XPERP-<Verfall>).
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
HANDEL = HIER.parent


def _lade(pfad: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, pfad)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


# Die Nachbarmodule laden sich gegenseitig per Kurzname (xperp/indikatoren.py
# holt `cvd`, scanner/okx.py seine Geschwister). Deshalb muessen ihre ORDNER auf
# dem Suchpfad stehen - und der eigene Ordner bleibt vorne (sonst zieht ein
# gleichnamiges Modul aus einem Nachbarordner).
for _ordner in (HIER, HANDEL / "xperp", HANDEL / "scanner"):
    if str(_ordner) not in sys.path:
        sys.path.insert(0, str(_ordner))

okx = _lade(HANDEL / "scanner" / "okx.py", "okx_trendwende")
xi = _lade(HANDEL / "xperp" / "indikatoren.py", "indikatoren_trendwende")
spur_buch = _lade(HANDEL / "spur_buch.py", "spur_buch_trendwende")


def quelle(w):
    """Kerzen holen. Rueckgabe wie bei allen Buch-Spuren: (daten, kurse, fehler)."""
    inst = w.get("instrument", "BTC-USDT-SWAP")
    bar = w.get("kerzen_zeitrahmen", "1H")
    anzahl = int(w.get("kerzen_anzahl", 400))
    daten, kurse, fehler = {}, {}, []
    try:
        kerzen = okx.kerzen(inst, bar=bar, anzahl=anzahl)
    except Exception as e:                                     # noqa: BLE001
        return {}, {}, ["%s: Kerzen nicht abrufbar (%s)" % (inst, e)]
    if not kerzen:
        return {}, {}, ["%s: keine Kerzen zurueckgekommen" % inst]
    daten[inst] = {"kerzen": kerzen, "bar": bar}
    kurse[inst] = float(kerzen[-1][4])
    return daten, kurse, fehler


def signal(d, w):
    """'short' beim WECHSEL des SuperTrend nach unten, unter der EMA200."""
    k = d.get("kerzen") or []
    n_st = int(w.get("supertrend_n", 10))
    faktor = float(w.get("supertrend_faktor", 3.0))
    n_ema = int(w.get("ema_filter_n", 200))
    if len(k) < max(n_ema + 2, n_st * 3 + 2):
        # Zu wenig Kerzen: lieber kein Signal als eines aus dem Nichts.
        return None
    try:
        _, richtung = xi.supertrend(k, n=n_st, faktor=faktor)
        schluesse = [float(z[4]) for z in k]
        ema = xi.ema(schluesse, n_ema)
    except Exception as e:                                     # noqa: BLE001
        print("  Trendwende: Indikator nicht rechenbar (%s)" % e, file=sys.stderr)
        return None
    if not richtung or len(richtung) < 2 or ema is None or not len(ema):
        return None
    # Der Wendepunkt: vorher aufwaerts, jetzt abwaerts.
    if not (richtung[-2] == 1 and richtung[-1] == -1):
        return None
    # Der Filter: nur gegen einen NICHT mehr steigenden grossen Trend.
    if schluesse[-1] >= float(ema[-1]):
        return None
    return "short"


def trend_richtung(w):
    """Aktuelle SuperTrend-Richtung auf der letzten abgeschlossenen Kerze.

    Eigene kleine Funktion, damit signal() und rueckdreh() nachweislich
    DIESELBE Rechnung benutzen - zwei Kopien derselben Formel waeren die
    Stelle, an der Einstieg und Ausstieg auseinanderlaufen.
    """
    daten, _kurse, fehler = quelle(w)
    if fehler:
        return None
    inst = w.get("instrument", "BTC-USDT-SWAP")
    k = (daten.get(inst) or {}).get("kerzen") or []
    n_st = int(w.get("supertrend_n", 10))
    if len(k) < n_st * 3 + 2:
        return None
    k = k[:-1]
    try:
        _, richtung = xi.supertrend(k, n=n_st,
                                    faktor=float(w.get("supertrend_faktor", 3.0)))
    except Exception:  # noqa: BLE001
        return None
    return richtung[-1] if richtung else None


def rueckdreh(p, w):
    """'rueckdreh', sobald der Trend wieder nach oben zeigt - sonst None.

    AUFTRAG Max 21.09.2026. Die Spur steigt beim Wechsel +1 -> -1 short ein;
    der ehrliche Gegenpart ist der Ausstieg, sobald der SuperTrend wieder auf
    +1 steht. Ohne ihn endet ein Short nur an Stop, Ziel oder Frist - also
    moeglicherweise erst weit, nachdem die eigene Begruendung entfallen ist.

    Stop und Ziel behalten Vorrang (spur_buch fragt diesen Zusatz erst danach).
    Nur fuer Short-Positionen: die Spur eroeffnet keine Longs, eine Long-
    Position waere ein Fremdkoerper und wird nicht angefasst.
    """
    if (p.get("seite") or "").lower() != "short":
        return None
    if not w.get("ausstieg_bei_rueckdreh", True):
        return None
    return "rueckdreh" if trend_richtung(w) == 1 else None



def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = p.add_mutually_exclusive_group()
    g.add_argument("--vorschau", action="store_const", dest="modus",
                   const="vorschau", help="nur rechnen, nichts schreiben")
    g.add_argument("--papier", action="store_const", dest="modus", const="papier",
                   help="Papierbuch (Standard)")
    g.add_argument("--live", action="store_const", dest="modus", const="live",
                   help="verweigert: diese Spur hat keinen Live-Zweig")
    g.add_argument("--wachen", action="store_const", dest="modus", const="wachen",
                   help="nur den Wachenstand zeigen")
    a = p.parse_args()
    modus = a.modus or "papier"
    if modus == "live" and not _live_erlaubt():
        print("--live verweigert: handel_erlaubt ist false und freigabe.erfuellt "
              "ist nicht gesetzt - Handelsregeln Punkt 3 (scharf schalten von "
              "Hand). Diese Spur hat zusaetzlich keinen Orderaufruf.")
        modus = "papier"
    return spur_buch.zyklus(HIER, quelle, signal, modus,
                            ereignis_name="handel/trendwende_btc",
                            zusatz_ausstieg=rueckdreh)


def _live_erlaubt() -> bool:
    import json
    try:
        w = json.loads((HIER / "wachen.json").read_text(encoding="utf-8"))
    except Exception:                                          # noqa: BLE001
        return False
    return bool(w.get("handel_erlaubt")) and bool(
        (w.get("freigabe") or {}).get("erfuellt"))


if __name__ == "__main__":
    sys.exit(main())

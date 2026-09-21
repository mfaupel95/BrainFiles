#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wache auf die Spur trendwende_btc (SHORT bei Trendwende auf 1H).

WARUM: Die Spur ist am 21.09.2026 angelegt und hat noch keine einzige Buchung.
Ihr Signal ist selten (in den letzten 200 Kerzen drehte der SuperTrend 3x nach
unten) - nachsehen waere also Warten auf ein Ereignis, das tagelang ausbleibt.
Diese Wache meldet es stattdessen.

Gemeldet wird NUR, was neu ist:
  1. jeder neue EINSTIEG (der erste ist die Antwort auf 'greift die Regel?'),
  2. jede geschlossene RUNDE mit G/V und Grund (Stop, Ziel oder Frist),
  3. eine WENDE, die der EMA200-Filter zurueckgehalten hat - das ist kein
     Fehler, sondern die Regel bei der Arbeit; einmal je Kerze, nicht oefter,
  4. ein STILLSTAND: der Zyklus schreibt alle ~6,5 min, meldet wird erst ab
     45 min ohne Lauf (dann laeuft der Dauerlauf nicht oder die Spur bricht ab).

LEERE AUSGABE = nichts senden (Watchdog-Muster). Zustand in
Agenten/Hermes/cache/trendwende-btc-wache.json.

Aufruf (Hermes-Cron, no_agent, alle 30 Minuten):
    python trendwende-btc-wache.py
    python trendwende-btc-wache.py --jetzt    # zeigen, nichts schreiben
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import sys
from pathlib import Path

HERMES = Path(__file__).resolve().parents[1]
HANDEL = HERMES.parents[0] / "Handel"
SPUR = HANDEL / "trendwende_btc"
STAND = HERMES / "cache" / "trendwende-btc-wache.json"

JOURNAL = SPUR / "handelsjournal.csv"
ZUSTAND = SPUR / "zustand.json"
WACHEN = SPUR / "wachen.json"

EINSTIEG = ("kauf", "eroeffnen", "EINSTIEG")
AUSSTIEG = ("verkauf", "schliessen", "AUSSTIEG")
STILL_MIN = 45          # ab wann ein fehlender Zyklus gemeldet wird
# Ein Zyklus schreibt alle ~6,5 min; 45 min sind rund sieben verpasste Laeufe.


def _lies(pfad: Path):
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _zeilen(pfad: Path):
    if not pfad.exists():
        return []
    try:
        with pfad.open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def _zeit(wert):
    try:
        return dt.datetime.fromisoformat(str(wert).replace("Z", "+00:00"))
    except Exception:
        return None


def _zahl(wert):
    try:
        return float(wert)
    except (TypeError, ValueError):
        return None


def _wende_zurueckgehalten(w):
    """(True, text) wenn der SuperTrend gedreht hat, die EMA200 aber blockt.

    Rechnet mit denselben Funktionen wie die Spur - eine nachgebaute Formel
    wuerde die Formel pruefen, nicht die Spur.
    """
    # REIHENFOLGE ZAEHLT: jedes insert(0, ...) draengt sich vor. Stuende die
    # eigene Spur zuerst in der Schleife, laege am Ende scanner/ vorn und
    # 'import handeln' holte scanner/handeln.py - gemessen genau so passiert.
    # Deshalb die eigene Spur ZULETZT und danach gegen __file__ pruefen.
    for p in (HANDEL / "scanner", HANDEL / "xperp", SPUR):
        if str(p) in sys.path:
            sys.path.remove(str(p))
        sys.path.insert(0, str(p))
    try:
        import handeln as spur                                # trendwende_btc/
        import indikatoren as xi                              # xperp/
    except Exception as e:                                    # Netz/Import
        return None, "Indikatoren nicht ladbar: %s" % e
    if not str(Path(spur.__file__).resolve()).startswith(str(SPUR)):
        return None, ("falsches Modul geladen (%s) - Suchpfad pruefen."
                      % spur.__file__)

    # Die Kerzen holt die SPUR selbst (quelle()) - damit rechnet die Wache auf
    # denselben Daten wie der Zyklus, samt Instrument, Zeitrahmen und Anzahl
    # aus der wachen.json. Ein eigener Abruf koennte still abweichen.
    # quelle() gibt (daten, kurse, fehler) zurueck - daten[inst]["kerzen"].
    try:
        daten, _kurse, fehler = spur.quelle(w)
    except Exception as e:
        return None, "Kerzen nicht abrufbar: %s" % e
    if fehler:
        return None, "Kerzen nicht abrufbar: %s" % "; ".join(fehler)
    inst = w.get("instrument", "BTC-USDT-SWAP")
    k = (daten.get(inst) or {}).get("kerzen") or []
    if not k or len(k) < int(w.get("ema_filter_n", 200)) + 5:
        return None, None

    # Die Spur rechnet auf ABGESCHLOSSENEN Kerzen - hier genauso, sonst meldet
    # die Wache eine Wende, die sich bis zum Kerzenschluss noch aufloest.
    k = k[:-1]
    _, richtung = xi.supertrend(k, n=int(w.get("supertrend_n", 10)),
                                faktor=float(w.get("supertrend_faktor", 3.0)))
    if not (len(richtung) >= 2 and richtung[-2] == 1 and richtung[-1] == -1):
        return None, None

    schluss = [float(z[4]) for z in k]
    ema = xi.ema(schluss, int(w.get("ema_filter_n", 200)))
    if ema[-1] is None or schluss[-1] < float(ema[-1]):
        return None, None                         # Signal - die Spur handelt
    return (str(k[-1][0]),
            "Trend gedreht (+1 -> -1), aber Schluss %.0f liegt UEBER der "
            "EMA200 %.0f - der Filter haelt zurueck (Ruecksetzer im "
            "Aufwaertstrend, kein Short)." % (schluss[-1], float(ema[-1])))


def lauf(schreiben: bool = True):
    meldungen = []
    stand = _lies(STAND)
    neu = dict(stand)
    w = _lies(WACHEN)
    rows = _zeilen(JOURNAL)

    ein = [r for r in rows if (r.get("aktion") or "").strip() in EINSTIEG]
    aus = [r for r in rows if (r.get("aktion") or "").strip() in AUSSTIEG]

    n_ein, n_aus = int(stand.get("einstiege", 0)), int(stand.get("ausstiege", 0))
    neu["einstiege"], neu["ausstiege"] = len(ein), len(aus)

    for r in ein[n_ein:]:
        preis = _zahl(r.get("preis"))
        meldungen.append(
            "trendwende_btc: ERSTER SHORT %s zu %s (Einsatz %s USD, Stop %s, "
            "Ziel %s) - %s" % (
                r.get("inst") or "?",
                ("%.1f" % preis) if preis is not None else "?",
                r.get("einsatz_usd") or "?", r.get("stop") or "?",
                r.get("ziel") or "?", (r.get("zeit") or "")[:16])
            if n_ein == 0 else
            "trendwende_btc: SHORT %s zu %s (%s)" % (
                r.get("inst") or "?",
                ("%.1f" % preis) if preis is not None else "?",
                (r.get("zeit") or "")[:16]))

    for r in aus[n_aus:]:
        ein_usd, wert = _zahl(r.get("einsatz_usd")), _zahl(r.get("wert_usd"))
        gv = "%+.2f USD" % (wert - ein_usd) if (
            ein_usd is not None and wert is not None) else "?"
        meldungen.append(
            "trendwende_btc: RUNDE ZU %s, G/V %s (Grund %s, %s)" % (
                r.get("inst") or "?", gv, r.get("grund") or "?",
                (r.get("zeit") or "")[:16]))

    # Stillstand: der Zyklus schreibt alle ~6,5 min.
    z = _lies(ZUSTAND)
    letzter = _zeit(z.get("letzter_lauf"))
    if letzter is not None:
        alt = (dt.datetime.now(letzter.tzinfo) - letzter).total_seconds() / 60
        gemeldet = bool(stand.get("stillstand_gemeldet"))
        if alt > STILL_MIN and not gemeldet:
            meldungen.append(
                "trendwende_btc: seit %d min kein Zyklus (letzter %s) - "
                "Dauerlauf pruefen." % (alt, str(z.get("letzter_lauf"))[:16]))
            neu["stillstand_gemeldet"] = True
        elif alt <= STILL_MIN and gemeldet:
            meldungen.append("trendwende_btc: laeuft wieder (Zyklus frisch).")
            neu["stillstand_gemeldet"] = False

    # Zurueckgehaltene Wende - einmal je Kerze.
    if not z.get("positionen"):
        kerze, text = _wende_zurueckgehalten(w)
        if kerze and text and kerze != stand.get("letzte_blockierte_wende"):
            meldungen.append("trendwende_btc: " + text)
            neu["letzte_blockierte_wende"] = kerze

    if schreiben:
        STAND.parent.mkdir(parents=True, exist_ok=True)
        STAND.write_text(json.dumps(neu, ensure_ascii=False, indent=1),
                         encoding="utf-8")
    return meldungen


if __name__ == "__main__":
    for zeile in lauf(schreiben="--jetzt" not in sys.argv):
        print(zeile)

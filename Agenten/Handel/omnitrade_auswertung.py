"""Auswertung aller omnitrade-Laeufe - rein lesend.

Mehrere `omnitrade live`-Laeufe schreiben je eine Statusdatei
`Werkstatt/omnitrade/status/live*.json`. Diese Datei liest sie alle und
rechnet je Lauf: Orders, Kaeufe/Verkaeufe, Gewinn (realisiert + offene Position
zum letzten Kurs) und den Vergleich mit Buy-and-Hold ab Laufbeginn.

GRENZEN: Gebuehren und Slippage stehen nicht in der Statusdatei und fehlen in
der Rechnung; es zaehlen nur die letzten 20 Orders der Datei (`recent_orders`).
Bei 1h-Kerzen reicht das fuer Tage. Nur lesen, wirft nie.

Aufruf:  python omnitrade_auswertung.py          -> Tabelle (Text)
         python omnitrade_auswertung.py --json   -> Liste als JSON
         python omnitrade_auswertung.py --schreibe -> zusaetzlich Bericht nach
                                                    Werkstatt/omnitrade/status/auswertung.md
"""

import glob
import json
import os
import sys
import time

HIER = os.path.dirname(os.path.abspath(__file__))
if HIER not in sys.path:
    sys.path.insert(0, HIER)

import omnitrade_bridge as bruecke  # noqa: E402

STATUS_ORDNER = os.path.dirname(os.path.normpath(bruecke.STANDARD))


def _f(x, vorgabe=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return vorgabe


def dateien(ordner=None):
    """Alle Statusdateien der Laeufe (live.json und live_*.json)."""
    ordner = ordner or STATUS_ORDNER
    return sorted(glob.glob(os.path.join(ordner, "live*.json")))


def _start_kurs(lage):
    """Schlusskurs der letzten Kerze bis Laufbeginn (Buy-and-Hold-Bezug)."""
    start = _f(lage.get("started_ms"))
    kerzen = [k for k in (lage.get("recent_candles") or []) if isinstance(k, dict)]
    davor = [k for k in kerzen if _f(k.get("time_ms")) <= start]
    if not davor:
        return None
    return _f(max(davor, key=lambda k: _f(k.get("time_ms"))).get("close")) or None


def bilanz(lage, jetzt_ms=None):
    """Kennzahlen eines Laufs aus `omnitrade_bridge.lage()`."""
    jetzt_ms = time.time() * 1000 if jetzt_ms is None else jetzt_ms
    orders = [o for o in (lage.get("recent_orders") or []) if isinstance(o, dict)]
    gefuellt = [o for o in orders if o.get("outcome") == "filled"]
    kauf = sum(_f(o.get("quantity")) * _f(o.get("price")) for o in gefuellt if o.get("side") == "buy")
    verkauf = sum(_f(o.get("quantity")) * _f(o.get("price")) for o in gefuellt if o.get("side") == "sell")
    kurs = _f(lage.get("last_close"))
    netto = _f(lage.get("net_quantity"))
    gewinn = verkauf - kauf + netto * kurs
    kapital = _f(lage.get("initial_capital"))
    start_kurs = _start_kurs(lage)
    bh = None
    if start_kurs and kurs and kapital:
        bh = kapital * (kurs / start_kurs - 1.0)
    laufzeit_h = max(0.0, (jetzt_ms - _f(lage.get("started_ms"))) / 3.6e6)
    return {
        "datei": os.path.basename(lage.get("datei", "")),
        "ok": bool(lage.get("ok")),
        "fehler": lage.get("fehler", ""),
        "state": lage.get("state"),
        "symbol": lage.get("symbol"),
        "strategie": os.path.splitext(os.path.basename(str(lage.get("script") or "?")))[0],
        "laufzeit_h": round(laufzeit_h, 1),
        "kerzen": int(_f(lage.get("candles_seen"))),
        "signal": lage.get("last_signal"),
        "orders": int(_f(lage.get("orders_placed"))),
        "abgelehnt": int(_f(lage.get("orders_rejected"))),
        "kaeufe": sum(1 for o in gefuellt if o.get("side") == "buy"),
        "verkaeufe": sum(1 for o in gefuellt if o.get("side") == "sell"),
        "netto": netto,
        "kurs": kurs,
        "gewinn": round(gewinn, 2),
        "gewinn_pct": round(100 * gewinn / kapital, 2) if kapital else None,
        "buyhold": None if bh is None else round(bh, 2),
        "buyhold_pct": None if bh is None or not kapital else round(100 * bh / kapital, 2),
        "letzter_fehler": lage.get("last_error", ""),
    }


def alle(ordner=None, jetzt_ms=None):
    """Bilanzen aller Laeufe; eine kaputte Datei stoert die anderen nicht."""
    ergebnis = []
    for d in dateien(ordner):
        try:
            ergebnis.append(bilanz(bruecke.lage(d), jetzt_ms))
        except Exception as e:  # noqa: BLE001
            ergebnis.append({"datei": os.path.basename(d), "ok": False,
                             "fehler": "nicht auswertbar: %s" % e})
    return ergebnis


def _pct(x):
    return "  -  " if x is None else "%+.2f%%" % x


def zeile(b):
    """Eine Tabellenzeile als Text."""
    if "strategie" not in b:
        return "%-34s  %s" % (b.get("datei"), b.get("fehler"))
    marke = "" if b["ok"] else "  [%s]" % (b["fehler"] or "?")
    if b.get("state") not in (None, "running"):
        marke += "  [LAEUFT NICHT: %s]" % b["state"]
    return ("%-14s %-8s %5.1fh K%-4d O%d/%d (K%d V%d) netto %+.5g  Gewinn %+8.2f (%s)  B&H %s%s"
            % (b["strategie"], b["symbol"], b["laufzeit_h"], b["kerzen"], b["orders"],
               b["abgelehnt"], b["kaeufe"], b["verkaeufe"], b["netto"], b["gewinn"],
               _pct(b["gewinn_pct"]), _pct(b["buyhold_pct"]), marke))


def bericht(liste):
    kopf = "# omnitrade-Laeufe (%s)\n\n" % time.strftime("%d.%m.%Y %H:%M")
    zeilen = "\n".join("- " + zeile(b) for b in liste) or "- keine Statusdateien"
    fuss = ("\n\nGewinn = Verkaeufe - Kaeufe + offene Position zum letzten Kurs, ohne "
            "Gebuehren; B&H = Kapital mal Kursaenderung seit Laufbeginn. Testnet.\n")
    return kopf + zeilen + fuss


def main(argv):
    liste = alle()
    if "--json" in argv:
        json.dump(liste, sys.stdout, indent=2, ensure_ascii=False)
        print()
    else:
        print("\n".join(zeile(b) for b in liste) or "keine Statusdateien")
    if "--schreibe" in argv:
        with open(os.path.join(STATUS_ORDNER, "auswertung.md"), "w", encoding="utf-8") as f:
            f.write(bericht(liste))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

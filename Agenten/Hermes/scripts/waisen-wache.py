"""Wache ueber Kraken-Schutz-Orders, die keine Position mehr haben (Waisen).

Warum es die Wache gibt (Befund 24.09.2026, Auftrag "Waisen-Waechter bauen"):
  * Beim Schliessen einer Margin-Position LOESCHT Kraken den Stop-Loss NICHT. Er
    bleibt "open", sieht in der Oberflaeche aus wie eine offene Position, und ein
    Schliessversuch scheitert (kein Bestand, keine Position).
  * Gefaehrlich ist der Waise selbst: ein Margin-SELL-Stop ohne Long-Position
    verkauft, was nicht da ist - beim Ausloesen entsteht ein SHORT. Am 24.09.2026
    lagen 7 solcher Waisen mit rund 940 EUR Nominal im Markt.

Die Wache MELDET NUR. Sie storniert nichts - ein Waechter, der Orders an einem
echten Konto loescht, ist selbst ein Risiko. Sie ruft die Rechnung aus
`Agenten/Handel/kraken/waisen_stops.py` auf (dieselbe Quelle wie das Werkzeug,
nichts nachgebaut).

Meldet: neue Waisen sofort, dieselben Waisen hoechstens alle 6 Stunden, das
Verschwinden einmal ("erledigt"), und einen Messfehler - auch der darf nicht
stumm bleiben. Leere Ausgabe = nichts zu senden (Hausmuster fuer no_agent-Crons).

Aufruf:  python waisen-wache.py [--alles]
"""
import argparse
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
WURZEL = os.path.dirname(os.path.dirname(os.path.dirname(HIER)))
HANDEL = os.path.join(WURZEL, "Agenten", "Handel")
KRAKEN = os.path.join(HANDEL, "kraken")
MERKDATEI = os.path.abspath(os.path.join(HIER, "..", "cache", "waisen-wache.json"))

WIEDERHOLUNG_H = 6.0
MAX_ZEILEN = 5


def laden(name, pfad):
    """Ein Modul ueber den PFAD laden - nie ueber sys.path[0] raten."""
    spec = importlib.util.spec_from_file_location(name, pfad)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def messen():
    """(waisen, fehler) - waisen sind die Zeilen aus waisen_stops.lage()."""
    try:
        kraken = laden("kraken_wache", os.path.join(KRAKEN, "kraken.py"))
        stops = laden("spot_stops_wache", os.path.join(KRAKEN, "spot_stops.py"))
        zeilen = stops_waisen(kraken, stops)
        return [z for z in zeilen if z.get("waise")], None
    except Exception as e:                      # noqa: BLE001 - melden, nicht sterben
        return [], "%s: %s" % (type(e).__name__, e)


def stops_waisen(kraken, stops):
    """Die Rechnung liegt in EINEM Werkzeug - hier nur geladen, nicht kopiert."""
    modul = laden("waisen_stops_wache", os.path.join(KRAKEN, "waisen_stops.py"))
    return modul.lage(kraken, stops)


def _stunden(zeit, jetzt):
    try:
        d = datetime.fromisoformat(zeit)
    except Exception:
        return 1e9
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return (jetzt - d).total_seconds() / 3600.0


def _kurz(z):
    return "%s %s %.8g @ %.6g" % (z.get("txid"), z.get("paar"),
                                  float(z.get("menge") or 0),
                                  float(z.get("preis") or 0))


def meldung(waisen, alt, jetzt, wiederholung_h=WIEDERHOLUNG_H):
    """Reine Entscheidung: (Text, neuer Zustand). Leerer Text = nichts senden."""
    alt = alt or {}
    gemeldet = dict(alt.get("gemeldet") or {})
    txids = sorted(z.get("txid") or "" for z in waisen)
    frisch = [t for t in txids if t not in gemeldet]
    faellig = [t for t in txids if t in gemeldet
               and _stunden(gemeldet[t], jetzt) >= wiederholung_h]
    neu = dict(alt)

    if not txids:
        neu["gemeldet"] = {}
        neu["hatte_waisen"] = False
        if alt.get("hatte_waisen"):
            return ("Kraken: keine Waisen-Stops mehr - die zuletzt gemeldeten "
                    "Schutz-Orders ohne Position sind weg.", neu)
        return ("", neu)

    if not frisch and not faellig:
        return ("", neu)

    kopf = ("Kraken: %d Schutz-Order(s) OHNE Position (Waise).\n"
            "Ein Margin-Sell-Stop ohne Long-Position eroeffnet beim Ausloesen "
            "einen SHORT - bitte stornieren:\n"
            "  python Agenten/Handel/kraken/waisen_stops.py --stornieren\n"
            % len(txids))
    zeilen = ["  " + _kurz(z) for z in waisen[:MAX_ZEILEN]]
    if len(waisen) > MAX_ZEILEN:
        zeilen.append("  ... und %d weitere" % (len(waisen) - MAX_ZEILEN))
    if not frisch:
        zeilen.insert(0, "  (Erinnerung, dieselben Waisen wie zuvor)")
    neu["gemeldet"] = {t: jetzt.isoformat() for t in txids}
    neu["hatte_waisen"] = True
    neu["letzte_meldung"] = jetzt.isoformat()
    return ("\n".join([kopf] + zeilen), neu)


def _lies():
    if not os.path.exists(MERKDATEI):
        return {}
    try:
        with open(MERKDATEI, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _schreib(daten):
    os.makedirs(os.path.dirname(MERKDATEI), exist_ok=True)
    with open(MERKDATEI, "w", encoding="utf-8") as fh:
        json.dump(daten, fh, ensure_ascii=False, indent=1)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Waisen-Stops melden (nie stornieren)")
    ap.add_argument("--alles", action="store_true",
                    help="auch unveraenderte Waisen erneut melden")
    args = ap.parse_args(argv if argv is not None else sys.argv[1:])

    jetzt = datetime.now(timezone.utc)
    alt = _lies()
    waisen, fehler = messen()
    if fehler:
        if not args.alles and _stunden(alt.get("letzter_fehler") or
                                       "1970-01-01T00:00:00+00:00",
                                       jetzt) < WIEDERHOLUNG_H:
            return 0
        alt["letzter_fehler"] = jetzt.isoformat()
        _schreib(alt)
        print("Kraken-Waisen-Wache konnte nicht messen: %s\n"
              "Das ist keine Entwarnung - es ist unbekannt, ob Waisen liegen."
              % fehler)
        return 0

    text, neu = meldung(waisen, alt, jetzt,
                        wiederholung_h=0.0 if args.alles else WIEDERHOLUNG_H)
    neu.pop("letzter_fehler", None)
    _schreib(neu)
    if text:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
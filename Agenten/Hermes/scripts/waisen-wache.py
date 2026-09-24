"""Wache ueber Schutz-Orders, die keine Position und keinen Bestand mehr haben.

Warum es die Wache gibt (Befund 24.09.2026, Auftrag "Waisen-Waechter bauen"):
  * Beim Schliessen einer Margin-Position LOESCHT Kraken den Stop-Loss NICHT. Er
    bleibt "open", sieht in der Oberflaeche aus wie eine offene Position, und ein
    Schliessversuch scheitert (kein Bestand, keine Position).
  * Gefaehrlich ist der Waise selbst: ein Margin-SELL-Stop ohne Long-Position
    verkauft, was nicht da ist - beim Ausloesen entsteht ein SHORT. Am 24.09.2026
    lagen 7 solcher Waisen mit rund 940 EUR Nominal im Markt.

Seit demselben Tag wird OKX mitgeprueft (`Agenten/Handel/okx_waisen.py`). Dort ist
die Klasse milder - bei Spot laesst sich nur verkaufen, was da ist, und Perp-Stops
tragen reduceOnly - aber ein verwaister Zuschlag sperrt den Bestand.

Die Wache MELDET NUR. Sie storniert nichts - ein Waechter, der Orders an einem
echten Konto loescht, ist selbst ein Risiko. Sie ruft die Rechnung der beiden
Werkzeuge auf (dieselbe Quelle, nichts nachgebaut).

Meldet: neue Waisen sofort, dieselben hoechstens alle 6 Stunden, das Verschwinden
einmal ("erledigt"), und einen Messfehler je Boerse - auch der darf nicht stumm
bleiben. Leere Ausgabe = nichts zu senden (Hausmuster fuer no_agent-Crons).

Aufruf:  python waisen-wache.py [--alles] [--selbsttest]
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

HINWEIS = {
    "kraken": "python Agenten/Handel/kraken/waisen_stops.py --stornieren",
    "okx": "python Agenten/Handel/okx_waisen.py --stornieren",
}


def laden(name, pfad):
    """Ein Modul ueber den PFAD laden - nie ueber sys.path[0] raten."""
    spec = importlib.util.spec_from_file_location(name, pfad)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _kraken_waisen():
    kraken = laden("kraken_wache", os.path.join(KRAKEN, "kraken.py"))
    stops = laden("spot_stops_wache", os.path.join(KRAKEN, "spot_stops.py"))
    modul = laden("waisen_stops_wache", os.path.join(KRAKEN, "waisen_stops.py"))
    return modul.lage(kraken, stops)


def _okx_waisen():
    modul = laden("okx_waisen_wache", os.path.join(HANDEL, "okx_waisen.py"))
    okx = laden("okx_wache", os.path.join(HANDEL, "scanner", "okx.py"))
    return modul.lage(okx)


QUELLEN = (("kraken", _kraken_waisen), ("okx", _okx_waisen))


def messen():
    """(waisen, fehler) - eine Boerse darf die andere nicht verdecken."""
    waisen, fehler = [], []
    for name, quelle in QUELLEN:
        try:
            for z in quelle():
                if not z.get("waise"):
                    continue
                z = dict(z)
                z["boerse"] = name
                z["kennung"] = "%s:%s" % (name, z.get("txid") or z.get("kennung") or "")
                waisen.append(z)
        except Exception as e:                  # noqa: BLE001 - melden, nicht sterben
            fehler.append("%s: %s: %s" % (name, type(e).__name__, e))
    return waisen, fehler


def _stunden(zeit, jetzt):
    try:
        d = datetime.fromisoformat(zeit)
    except Exception:
        return 1e9
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return (jetzt - d).total_seconds() / 3600.0


def _kurz(z):
    """Eine Zeile je Waise - die Kraken- und die OKX-Form passen beide hierhin."""
    name = (z.get("boerse") or "").strip()
    kennung = z.get("kennung") or z.get("txid") or "?"
    if name and str(kennung).startswith(name + ":"):
        name = ""                    # die Kennung traegt die Boerse schon
    wo = z.get("paar") or z.get("inst") or "?"
    return "%s%s %s %.8g @ %.6g" % (name + " " if name else "", kennung, wo,
                                    float(z.get("menge") or 0),
                                    float(z.get("preis") or 0))


def meldung(waisen, alt, jetzt, wiederholung_h=WIEDERHOLUNG_H):
    """Reine Entscheidung: (Text, neuer Zustand). Leerer Text = nichts senden."""
    alt = alt or {}
    gemeldet = dict(alt.get("gemeldet") or {})
    kennungen = sorted((z.get("kennung") or z.get("txid") or "") for z in waisen)
    frisch = [k for k in kennungen if k not in gemeldet]
    faellig = [k for k in kennungen if k in gemeldet
               and _stunden(gemeldet[k], jetzt) >= wiederholung_h]
    neu = dict(alt)

    if not kennungen:
        neu["gemeldet"] = {}
        neu["hatte_waisen"] = False
        if alt.get("hatte_waisen"):
            return ("Es liegen keine Waisen-Stops mehr vor - die zuletzt "
                    "gemeldeten Orders ohne Position sind weg.", neu)
        return ("", neu)

    if not frisch and not faellig:
        return ("", neu)

    boersen = sorted({(z.get("boerse") or "kraken") for z in waisen})
    kopf = ["%d Schutz-Order(s) OHNE Position oder Bestand (Waise)."
            % len(kennungen),
            "Kraken-Margin: ein Sell-Stop ohne Long-Position eroeffnet beim "
            "Ausloesen einen SHORT.",
            "Stornieren:"]
    kopf += ["  " + HINWEIS[b] for b in boersen if b in HINWEIS]
    zeilen = ["  " + _kurz(z) for z in waisen[:MAX_ZEILEN]]
    if len(waisen) > MAX_ZEILEN:
        zeilen.append("  ... und %d weitere" % (len(waisen) - MAX_ZEILEN))
    if not frisch:
        zeilen.insert(0, "  (Erinnerung, dieselben Waisen wie zuvor)")
    neu["gemeldet"] = {k: jetzt.isoformat() for k in kennungen}
    neu["hatte_waisen"] = True
    neu["letzte_meldung"] = jetzt.isoformat()
    return ("\n".join(kopf + zeilen), neu)


def _liegt():
    return [{"boerse": "kraken", "txid": "OTEST-1", "paar": "SUIEUR",
             "menge": 615.0, "preis": 0.777, "waise": True, "kennung": "kraken:OTEST-1"}]


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
    ap.add_argument("--selbsttest", action="store_true",
                    help="die fertige Meldung einmal zeigen - ohne Zustand, "
                         "ohne Netz (beweist die Form, nicht die Lage)")
    args = ap.parse_args(argv if argv is not None else sys.argv[1:])

    jetzt = datetime.now(timezone.utc)

    if args.selbsttest:
        text, _ = meldung(_liegt(), {}, jetzt)
        print(text)
        return 0

    alt = _lies()
    waisen, fehler = messen()
    if fehler:
        if not args.alles and _stunden(alt.get("letzter_fehler") or
                                       "1970-01-01T00:00:00+00:00",
                                       jetzt) < WIEDERHOLUNG_H:
            return 0
        alt["letzter_fehler"] = jetzt.isoformat()
        _schreib(alt)
        print("Waisen-Wache konnte nicht messen:\n  " + "\n  ".join(fehler) +
              "\nDas ist keine Entwarnung - es ist unbekannt, ob Waisen liegen.")
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
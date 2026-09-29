"""Einen CoinGecko-Abzug aufzeichnen - die Gegenprobe zur eigenen Tafel.

Wozu: `moondev_historie` baut den Marktquerschnitt aus Binance-Kerzen. Wer nur
die eigene Rechnung sieht, kann nicht wissen, ob sie die Wirklichkeit trifft.
Dieses Werkzeug holt EINMAL die echten Marktdaten von CoinGecko (Preis,
24h-Aenderung, Volumen) und legt sie ab; `tests/test_replay_feed.GegenprobeTest`
haelt die Tafel danach gegen die Groessenordnung.

Verglichen wird bewusst NICHT auf Gleichheit: Binance und CoinGecko sind zwei
Boersen, und CoinGecko mittelt ueber viele. Ein Vergleich, der Gleichheit
verlangt, waere selbst falsch.

Aufruf (aus Agenten/Handel):

    python historie_probe.py            # schreibt daten/historie/coingecko_probe.json
    python -m unittest tests.test_replay_feed.GegenprobeTest -v

Ohne Netz oder ohne Zugang scheitert der Aufruf LAUT und schreibt nichts - eine
fehlende Probe ist keine bestandene Probe, und eine erfundene waere schlimmer
als keine.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

HIER = os.path.dirname(os.path.abspath(__file__))
ZIEL = os.path.join(HIER, "daten", "historie", "coingecko_probe.json")
ZIEL_OKX = os.path.join(HIER, "daten", "historie", "okx_probe.json")

# CoinGecko blockt schluesselfreie Aufrufe inzwischen (HTTP 403, gemessen am
# 29.09.2026). OKX antwortet oeffentlich und ist eine ZWEITE Boerse - fuer eine
# Groessenordnungs-Probe genauso gut, und der Weg ist im Haus erprobt.
#
# WARUM KERZEN UND NICHT TICKER: der erste Versuch verglich Binances letzte
# Tageskerze mit OKX' Ticker "jetzt". Vier Symbole lagen dadurch 10-11 %
# auseinander (CELO/BERA/ONE/HBAR) - kein Boersenunterschied, sondern die
# Tagesbewegung ZWISCHEN dem Abruf der Kerze und dem Abruf des Tickers. Ein
# solcher Vergleich prueft die Uhr, nicht die Daten. Deshalb werden auf beiden
# Seiten DIESELBEN Tagesschlusskurse verglichen.
# ... und WARUM STUNDENKERZEN: OKX' Tageskerze beginnt um 00:00 UTC+8, Binances
# um 00:00 UTC - dieselbe Zahl "1D" bedeutet dort eine andere Tagesgrenze
# (gemessen am 29.09.2026: 0 von 50 Paaren trafen sich). Der Vergleich holt
# deshalb die Stunde, die GENAU auf der Tagesgrenze endet: 23:00 UTC.
OKX_KERZEN = ("https://eea.okx.com/api/v5/market/history-candles"
              "?instId=%s&bar=1H&limit=100")
OKX_SYMBOLE = 60

URL = ("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd"
       "&order=market_cap_desc&per_page=250&page=1"
       "&price_change_percentage=1h,24h")


def hole(url=URL, frist=40):
    """Die Marktliste holen. Kein Schluessel - die freie Schnittstelle."""
    anfrage = urllib.request.Request(url, headers={"User-Agent": "BrainFiles/1.0"})
    with urllib.request.urlopen(anfrage, timeout=frist) as antwort:
        return json.loads(antwort.read().decode("utf-8"))


def hole_okx(inst, frist=40):
    """Drei Tageskerzen eines Paares von OKX (oeffentlich, kein Schluessel).

    Rueckgabe: {ts_ms: schlusskurs}. Der Zeitstempel ist der Anfang der Kerze -
    auf beiden Boersen 00:00 UTC, damit sind die Kerzen vergleichbar.
    """
    d = hole(OKX_KERZEN % inst, frist)
    if not isinstance(d, dict) or d.get("code") != "0":
        raise RuntimeError("OKX antwortet %r" % (d if not isinstance(d, dict)
                                                 else d.get("msg")))
    aus = {}
    for r in (d.get("data") or []):
        try:
            aus[int(r[0])] = float(r[4])
        except (IndexError, TypeError, ValueError):
            continue
    return aus


def grosse_symbole(n=OKX_SYMBOLE):
    """Die groessten USDT-Basiswerte des eigenen Bestandes, in OKX-Schreibweise."""
    sys.path.insert(0, HIER)
    import moondev_historie as mh
    b = mh.Bestand()
    b.laden("1D")
    schritte = b.schritte(30)
    if not schritte:
        return []
    tafel = b.tafel(schritte[-1], top=n)
    aus = []
    for z in tafel.values():
        basis = z.get("basis")
        if basis:
            aus.append("%s-USDT" % basis)
    return aus


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    if "--okx" in argv:
        insts = grosse_symbole()
        if not insts:
            print("Kein Bestand geladen - nichts geschrieben.")
            return 1
        maerkte, fehler = [], []
        for inst in insts:
            try:
                kerzen = hole_okx(inst)
            except Exception as e:                          # noqa: BLE001
                fehler.append("%s: %s" % (inst, e))
                continue
            if not kerzen:
                fehler.append("%s: keine Kerzen" % inst)
                continue
            maerkte.append({"symbol": inst.split("-")[0],
                            "schluss": {str(k): v for k, v in kerzen.items()}})
        if len(maerkte) < 20:
            print("Zu wenige Paare (%d) - nichts geschrieben. %s"
                  % (len(maerkte), "; ".join(fehler[:3])))
            return 1
        print("%d Paare ohne Kerzen uebersprungen" % len(fehler))
        os.makedirs(os.path.dirname(ZIEL_OKX), exist_ok=True)
        with open(ZIEL_OKX, "w", encoding="utf-8") as f:
            json.dump({"stand_ms": int(time.time() * 1000),
                       "quelle": OKX_KERZEN % "<instId>", "maerkte": maerkte},
                      f, indent=1, ensure_ascii=False)
        print("%d Paare mit Tagesschluss -> %s" % (len(maerkte), ZIEL_OKX))
        return 0
    try:
        maerkte = hole()
    except urllib.error.HTTPError as e:
        print("CoinGecko antwortet HTTP %s: %s" % (e.code, e.reason))
        print("Kein Abzug geschrieben - der Test bleibt dann SKIP, nicht gruen.")
        return 1
    except Exception as e:                                  # noqa: BLE001
        print("Abruf gescheitert: %s: %s" % (type(e).__name__, e))
        print("Kein Abzug geschrieben - der Test bleibt dann SKIP, nicht gruen.")
        return 1
    if not isinstance(maerkte, list) or len(maerkte) < 20:
        print("Unerwartete Antwort (%r) - nichts geschrieben." % type(maerkte))
        return 1
    os.makedirs(os.path.dirname(ZIEL), exist_ok=True)
    with open(ZIEL, "w", encoding="utf-8") as f:
        json.dump({"stand_ms": int(time.time() * 1000), "quelle": URL,
                   "maerkte": maerkte}, f, indent=1, ensure_ascii=False)
    print("%d Maerkte -> %s" % (len(maerkte), ZIEL))
    return 0


if __name__ == "__main__":
    sys.exit(main())
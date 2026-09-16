"""Moon-Dev-Bot-Spur: Listing-Arbitrage (Coin gross, bei Binance noch nicht handelbar)

WOHER DIE IDEE KOMMT
--------------------
Der Agent `listingarb_agent` aus `Werkstatt/Repos/moon-dev-ai-agents` macht genau das:
er sucht Coins, die gross sind, aber an einer grossen Boerse noch fehlen, und kauft sie vor dem Listing. Sein Urteil faellt aber in einem Sprachmodell, und seine
Daten kommen ueber die CoinGecko-Pro-API (Schluessel noetig). Beides laesst sich
hier nicht sauber nachbilden, deshalb:

  * **Daten** ueber die oeffentliche CoinGecko-/Binance-API (`Handel/moondev_daten.py`)
    - dieselben Endpunkte, ohne Schluessel,
  * **Regel** deterministisch im Haus (siehe `signal()`), nachrechenbar,
  * **Buch** ein Haus-Buch (`Handel/spur_buch.py`): Zustand, Journal, Kopie
    nach `Q:\\Handel_Journal\\moondev_listingarb` (Bedingung 4), Ratsche, Stop/Ziel.

Kein Live-Zweig: die Fremd-Agenten handeln mit echten Schluesseln, diese Spur
bucht Papier. Ein `--live` verweigert.

Aufruf:
  python handeln.py --vorschau | --papier | --wachen
"""

import argparse
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
for p in (HANDEL, os.path.join(HANDEL, "scanner"), HIER):
    if p not in sys.path:
        sys.path.insert(0, p)

import spur_buch as buch  # noqa: E402
import moondev_daten as daten  # noqa: E402

# Test-Seam: None -> echter Abruf. Tests setzen ein Lambda.
quelle_override = None


def signal(d, w):
    """Long, wenn ein grosser Coin bei Binance (noch) nicht handelbar ist.

    Die Wette des Bots: Was gross ist und an einer grossen Boerse fehlt, kommt
    dorthin - und steigt dann. `d` traegt das Feld `auf_binance` (aus dem
    Abruf), `marktkap` und `volumen` filtern die Kleinigkeit aus.
    """
    if d.get("auf_binance"):
        return None
    if (d.get("marktkap") or 0) < w.get("mindest_marktkap_usd", 1e9):
        return None
    if (d.get("volumen_24h") or 0) < w.get("mindest_volumen_usd", 3e7):
        return None
    return "long"


def quelle(w):
    """Die grossen Coins + Binance-Paare. Der Abruf darf Fehler melden."""
    fehler = []
    aus = {}
    try:
        maerkte = daten.maerkte(anzahl=int(w.get("anzahl_coins", 100)))
    except Exception as e:                                     # noqa: BLE001
        return {}, {}, ["CoinGecko: %s" % str(e)[:120]]
    try:
        paare = daten.binance_paare()
    except Exception as e:                                     # noqa: BLE001
        fehler.append("Binance: %s" % str(e)[:120])
        paare = set()
    for m in maerkte:
        symbol = (m.get("symbol") or "").upper()
        if not symbol:
            continue
        aus[symbol] = {
            "name": m.get("name"),
            "marktkap": daten.zahl(m.get("market_cap")),
            "volumen_24h": daten.zahl(m.get("total_volume")),
            "rang": m.get("market_cap_rank"),
            "kurs": daten.zahl(m.get("current_price")),
            "auf_binance": symbol in paare,
        }
    kurse = {s: v["kurs"] for s, v in aus.items() if v["kurs"]}
    return aus, kurse, fehler


def daten_holen(w):
    """quelle() mit Test-Seam: Tests setzen `quelle_override`."""
    if quelle_override:
        return quelle_override(w)
    return quelle(w)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vorschau", action="store_const", const="vorschau", dest="modus")
    ap.add_argument("--papier", action="store_const", const="papier", dest="modus")
    ap.add_argument("--live", action="store_const", const="live", dest="modus")
    ap.add_argument("--wachen", action="store_const", const="wachen", dest="modus")
    ap.set_defaults(modus="papier")
    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if a.modus == "live":
        print("Live waere gesperrt durch: kein Live-Zweig in dieser Spur "
              "(Papier). Der Fremd-Agent handelt mit echten Schluesseln - "
              "dieser Haus-Lauf bucht nur Papier.")
        return 0
    # Der Name im Bus-Journal steht WOERTLICH hier: die Anbindung oeffnet der
    # gemeinsame Kern (spur_buch.zyklus -> ereignis.lauf), aber welcher Spur die
    # Meldung gehoert, entscheidet diese Datei - abgeleitet aus dem Ordnernamen
    # ist es nur so lange richtig, wie Ordner und Spurname gleich heissen.
    return buch.zyklus(HIER, daten_holen, signal, a.modus,
                       "handel/moondev_listingarb")


if __name__ == "__main__":
    raise SystemExit(main())

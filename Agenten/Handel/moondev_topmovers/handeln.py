"""Moon-Dev-Bot-Spur: Top-Mover der letzten 24 Stunden (Momentum ohne Ueberhitzung)

WOHER DIE IDEE KOMMT
--------------------
Der Agent `new_or_top_agent` aus `Werkstatt/Repos/moon-dev-ai-agents` macht genau das:
er sieht sich die neuen und die staerksten Coins der letzten 24 Stunden an. Sein Urteil faellt aber in einem Sprachmodell, und seine
Daten kommen ueber die CoinGecko-Pro-API (Schluessel noetig). Beides laesst sich
hier nicht sauber nachbilden, deshalb:

  * **Daten** ueber die oeffentliche CoinGecko-/Binance-API (`Handel/moondev_daten.py`)
    - dieselben Endpunkte, ohne Schluessel,
  * **Regel** deterministisch im Haus (siehe `signal()`), nachrechenbar,
  * **Buch** ein Haus-Buch (`Handel/spur_buch.py`): Zustand, Journal, Kopie
    nach `Q:\\Handel_Journal\\moondev_topmovers` (Bedingung 4), Ratsche, Stop/Ziel.

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
    """Long bei Momentum - aber nur unterhalb der Ueberhitzungsgrenze.

    Ein Coin, der in 24 h 80 % gemacht hat, ist keine Gelegenheit mehr,
    sondern eine Wette auf die naechste Stunde. Die Grenzen stehen in
    `wachen.json` (mindest_plus_pct, hoechst_plus_pct).
    """
    pct = d.get("aenderung_24h")
    if pct is None:
        return None
    if (d.get("volumen_24h") or 0) < w.get("mindest_volumen_usd", 2e7):
        return None
    if pct < w.get("mindest_plus_pct", 8.0):
        return None
    if pct > w.get("hoechst_plus_pct", 40.0):
        return None
    return "long"


def quelle(w):
    fehler = []
    aus = {}
    try:
        maerkte = daten.maerkte(anzahl=int(w.get("anzahl_coins", 250)),
                                sortierung="market_cap_desc")
    except Exception as e:                                     # noqa: BLE001
        return {}, {}, ["CoinGecko: %s" % str(e)[:120]]
    for m in maerkte:
        symbol = (m.get("symbol") or "").upper()
        if not symbol:
            continue
        aus[symbol] = {
            "name": m.get("name"),
            "aenderung_24h": daten.zahl(m.get("price_change_percentage_24h")),
            "volumen_24h": daten.zahl(m.get("total_volume")),
            "kurs": daten.zahl(m.get("current_price")),
        }
    kurse = {s: v["kurs"] for s, v in aus.items() if v["kurs"]}
    return aus, kurse, fehler


def daten_holen(w):
    """quelle() mit Test-Seam: Tests setzen `quelle_override`."""
    if quelle_override:
        return quelle_override(w)
    return quelle(w)


def preis_fuer(inst):
    """Der Kurs EINES Symbols - fuer Positionen, die aus dem Feed gefallen sind.

    T-160: die Top-Movers wechseln taeglich; faellt ein gehaltenes Symbol aus
    der Liste, verliert die Position sonst ihren Kurs und friert im Buch ein.
    Ueber `daten.symbol_kurs` (Binance zuerst, dann CoinGecko mit ID-Cache)
    bleibt der Kurs erhalten - `spur_buch.zyklus` ruft das nur fuer verwaiste
    Positionen auf.
    """
    return daten.symbol_kurs(inst)


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
    # --live laeuft seit dem 21.09.2026 ueber den GEMEINSAMEN Orderweg in
    # spur_buch (boerse aus der wachen.json). Jede Sperre, die noch steht,
    # laesst den Zyklus Papier handeln und nennt den Grund - der Schalter
    # allein schaltet nichts scharf.
    # Der Name im Bus-Journal steht WOERTLICH hier: die Anbindung oeffnet der
    # gemeinsame Kern (spur_buch.zyklus -> ereignis.lauf), aber welcher Spur die
    # Meldung gehoert, entscheidet diese Datei - abgeleitet aus dem Ordnernamen
    # ist es nur so lange richtig, wie Ordner und Spurname gleich heissen.
    return buch.zyklus(HIER, daten_holen, signal, a.modus,
                       "handel/moondev_topmovers", preis_fuer=preis_fuer)


if __name__ == "__main__":
    raise SystemExit(main())

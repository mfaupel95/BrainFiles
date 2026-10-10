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

LIVE: `--live` laeuft seit dem 21.09.2026 ueber den GEMEINSAMEN Orderweg in
`spur_buch` (Boerse und Grenzen aus der `wachen.json`, hier OKX-Spot gegen USDC).
Jede Sperre, die noch steht, laesst den Zyklus Papier handeln und nennt den Grund.

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
# Test-Seam fuer die handelbaren OKX-Paare (siehe okx_instrumente()).
instrumente_override = None


def okx_instrumente():
    """Die handelbaren OKX-Spot-Paare - oeffentlich, ohne Schluessel.

    WARUM DAS HIER STEHT (25.09.2026): diese Spur handelte auf KRAKEN (EUR).
    Auf OKX (USDC) heisst das Paar `<SYM>-USDC`, und NICHT jede grosse Muenze
    gibt es dort: von den drei Signalen des Tages (VVV, WBT, XMR) hatte nur VVV
    ueberhaupt ein OKX-Paar, und das nur als -USDT. Ohne diese Pruefung schickte
    der Orderweg ein Paar, das die Boerse nicht kennt.
    """
    if instrumente_override:
        return instrumente_override()
    import okx                                       # liegt in scanner/ am Pfad
    liste = okx._roh("/api/v5/public/instruments?instType=SPOT",
                     signiert=False) or []
    return {i.get("instId") for i in liste if i.get("instId")}


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
    if str(w.get("boerse") or "okx").strip().lower() == "okx" and not d.get("okx_usdc"):
        # Das OKX-Paar fehlt (oder der Abruf der Paarliste ging schief): kein
        # Handel. Der Orderweg wuerde sonst ein Paar schicken, das es nicht gibt.
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
    if str(w.get("boerse") or "okx").strip().lower() == "okx":
        try:
            paare = okx_instrumente()
        except Exception as e:                                 # noqa: BLE001
            fehler.append("OKX-Instrumente: %s" % str(e)[:120])
            paare = set()
        for symbol, eintrag in aus.items():
            eintrag["okx_usdc"] = ("%s-USDC" % symbol) in paare
    kurse = {s: v["kurs"] for s, v in aus.items() if v["kurs"]}
    return aus, kurse, fehler


def daten_holen(w):
    """quelle() mit Test-Seam: Tests setzen `quelle_override`."""
    if quelle_override:
        return quelle_override(w)
    return quelle(w)


def preis_fuer(inst):
    """Der Kurs EINES Symbols - fuer Positionen, die aus dem Feed gefallen sind.

    T-160: CoinGecko sortiert nach Marktkapitalisierung; ein grosser Coin,
    der aus den Top-100 faellt, verliert sonst seinen Kurs und die Position
    friert ein. Ueber `daten.symbol_kurs` (Binance, dann CoinGecko mit
    ID-Cache) bleibt der Kurs erhalten - `spur_buch.zyklus` ruft das nur
    fuer verwaiste Positionen auf. Wichtig gerade hier: Listingarb kauft
    bewusst Coins, die es NICHT auf Binance gibt - dafuer ist der
    CoinGecko-Weg mit ID-Cache da.
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
                       "handel/moondev_listingarb", preis_fuer=preis_fuer)


if __name__ == "__main__":
    raise SystemExit(main())

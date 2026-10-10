"""Moon-Dev-Bot-Spur: Marktlage BTC (Regime aus Kurs und Marktbreite)

WOHER DIE IDEE KOMMT
--------------------
Der Agent `coingecko_agent` aus `Werkstatt/Repos/moon-dev-ai-agents` macht genau das:
er beschreibt die Lage des Gesamtmarkts und leitet daraus eine Richtung ab. Sein Urteil faellt aber in einem Sprachmodell, und seine
Daten kommen ueber die CoinGecko-Pro-API (Schluessel noetig). Beides laesst sich
hier nicht sauber nachbilden, deshalb:

  * **Daten** ueber die oeffentliche CoinGecko-/Binance-API (`Handel/moondev_daten.py`)
    - dieselben Endpunkte, ohne Schluessel,
  * **Regel** deterministisch im Haus (siehe `signal()`), nachrechenbar,
  * **Buch** ein Haus-Buch (`Handel/spur_buch.py`): Zustand, Journal, Kopie
    nach `Q:\\Handel_Journal\\moondev_marktlage` (Bedingung 4), Ratsche, Stop/Ziel.

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
    """BTC long oder short - je nach Lage des GESAMTmarkts.

    Ein Regime-Signal: BTC allein sagt wenig, wenn 90 % aller Coins fallen.
    `breite` ist der Anteil der Top-Coins mit positivem 24h-Vorzeichen.
    """
    pct = d.get("btc_aenderung_24h")
    breite = d.get("breite")
    if pct is None or breite is None:
        return None
    schwelle = float(w.get("btc_schwelle_pct", 2.0))
    oben = float(w.get("breite_oben", 0.60))
    unten = float(w.get("breite_unten", 0.40))
    if pct >= schwelle and breite >= oben:
        return "long"
    if pct <= -schwelle and breite <= unten:
        return "short"
    return None


def quelle(w):
    """BTC/ETH plus Marktbreite aus den Top 100 (CoinGecko)."""
    fehler = []
    try:
        maerkte = daten.maerkte(anzahl=100)
    except Exception as e:                                     # noqa: BLE001
        return {}, {}, ["CoinGecko: %s" % str(e)[:120]]
    if not maerkte:
        return {}, {}, ["CoinGecko: leere Antwort"]
    aus, kurse = {}, {}
    plus = sum(1 for m in maerkte
               if (daten.zahl(m.get("price_change_percentage_24h")) or 0) > 0)
    breite = plus / float(len(maerkte))
    for m in maerkte:
        symbol = (m.get("symbol") or "").upper()
        if symbol == "BTC":
            aus[symbol] = {
                "name": m.get("name"),
                "btc_aenderung_24h": daten.zahl(m.get("price_change_percentage_24h")),
                "breite": breite,
                "kurs": daten.zahl(m.get("current_price")),
            }
            kurse[symbol] = daten.zahl(m.get("current_price"))
    return aus, kurse, fehler


def daten_holen(w):
    """quelle() mit Test-Seam: Tests setzen `quelle_override`."""
    if quelle_override:
        return quelle_override(w)
    return quelle(w)


def preis_fuer(inst):
    """Der Kurs EINES Symbols - fuer Positionen, die aus dem Feed gefallen sind.

    T-160: die Markt-Breite wird aus den Top-100 gerechnet; ein Coin, der
    daraus faellt, verliert sonst seinen Kurs und die offene Position friert
    ein. Ueber `daten.symbol_kurs` (Binance, dann CoinGecko mit ID-Cache)
    bleibt der Kurs ueber den Symbolwechsel hinweg erhalten - `spur_buch.zyklus`
    ruft das nur fuer verwaiste Positionen auf.
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
    if a.modus == "live":
        # Erster echter Geldpfad: eigener Live-Stamm in live_kraken.py
        # (Kraken-Spot, Long, kleine Einsatzhöhe, 9-Sperrenkette). Papier
        # ueber spur_buch bleibt unangetastet. handel_erlaubt=false zentral.
        import live_kraken  # noqa: E402
        return live_kraken.lauf("live")
    # Der Name im Bus-Journal steht WOERTLICH hier: die Anbindung oeffnet der
    # gemeinsame Kern (spur_buch.zyklus -> ereignis.lauf), aber welcher Spur die
    # Meldung gehoert, entscheidet diese Datei - abgeleitet aus dem Ordnernamen
    # ist es nur so lange richtig, wie Ordner und Spurname gleich heissen.
    r = buch.zyklus(HIER, daten_holen, signal, a.modus,
                    "handel/moondev_marktlage", preis_fuer=preis_fuer)
    if a.modus == "vorschau":
        # Der gemeinsame Papier-Kern kann die LIVE-Sperren nicht beurteilen -
        # sie liegen im eigenen Live-Zweig. Der Dauerlauf liest aber genau
        # diese eine Zeile, um zu entscheiden, ob sich eine Freigabe-Anfrage
        # lohnt (dauerlauf.nur_fenster_fehlt); ohne sie oeffnet AUTO_FREIGABE
        # nie ein Fenster und die Spur kann nie live gehen (Befund 22.09.2026).
        try:
            import live_kraken  # noqa: E402
            live_kraken.sperren_zeile()
        except Exception as e:                                   # noqa: BLE001
            print("Live waere gesperrt durch: nicht bestimmbar (%s)" % e)
    return r


if __name__ == "__main__":
    raise SystemExit(main())

"""Moon-Dev-Bot-Spur: Signalwelle - 1h-Momentum mit Volumen-Spike.

WOHER DIE IDEE KOMMT
--------------------
Anlass war ein VIP-Signal-Kanal (Screenshot, 20.09.2026): eine Gewinnkarte
(NVDAUSDT Perpetual 10x, +27 % ROI) ohne Verlusthistorie - Survivorship
Bias, hoher Hebel ohne sichtbare Stop-Regel, ein synthetisches Produkt, das
auf keiner Haus-Boerse handelbar ist. Diese Spur ist das ehrliche
Gegenstueck: dieselbe Grundidee (kurzfristige starke Bewegung als Signal),
aber

  * **Daten** ueber die oeffentliche Binance /ticker/24hr-API (`Handel/moondev_daten.py`,
    ``) - keine Blackbox, keine Kanalgebuehr,
  * **Regel** deterministisch im Haus (siehe `signal()`), nachrechenbar,
  * **Buch** ein Haus-Buch (`Handel/spur_buch.py`): Zustand, Journal, Kopie
    nach `Q:\\Handel_Journal\\moondev_signalwelle` (Bedingung 4), Ratsche,
    Stop/Ziel,
  * **Kein Hebel**: Spot-Papier mit Hausrisiko, kein Perpetual, kein
    Future - der Hebel im Screenshot ist genau der Teil, der hier bewusst
    NICHT nachgebaut wird.

Unterschied zu `moondev_topmovers`: topmovers fragt die 24h-Aenderung (eine
Tagesbewegung ist schon gelaufen), diese Spur fragt die 1h-Aenderung (eine
Welle, die GERADE anrollt) - engere Schwellen, engerer Stop.

Kein Live-Zweig: ein `--live` verweigert.

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
    """Long bei einer 1h-Welle - zwischen Anrollen und Ueberhitzung.

    Eine 1h-Aenderung ueber der Hoechstgrenze ist schon eine Spike-Kerze,
    keine Welle mehr; darunter ist kein Momentum da. Die Grenzen stehen in
    `wachen.json` (mindest_plus_1h_pct, hoechst_plus_1h_pct).
    """
    pct = d.get("aenderung_1h")
    if pct is None:
        return None
    if (d.get("volumen_24h") or 0) < w.get("mindest_volumen_usd", 2e7):
        return None
    if pct < w.get("mindest_plus_1h_pct", 3.0):
        return None
    if pct > w.get("hoechst_plus_1h_pct", 15.0):
        return None
    return "long"


def quelle(w):
    fehler = []
    aus = {}
    try:
        maerkte = daten.ticker_24hr()
    except Exception as e:                                     # noqa: BLE001
        return {}, {}, ["Binance: %s" % str(e)[:120]]
    for m in maerkte:
        symbol = m.get("symbol") or ""
        if not symbol:
            continue
        aus[symbol] = {
            "aenderung_1h": daten.zahl(m.get("pct_change")),
            "volumen_24h": daten.zahl(m.get("volume")),
            "kurs": daten.zahl(m.get("price")),
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
              "(Papier, kein Hebel). Der VIP-Kanal handelt mit Hebel und "
              "eigenen Schluesseln - dieser Haus-Lauf bucht nur Papier.")
        return 0
    # Der Name im Bus-Journal steht WOERTLICH hier: die Anbindung oeffnet der
    # gemeinsame Kern (spur_buch.zyklus -> ereignis.lauf), aber welcher Spur
    # die Meldung gehoert, entscheidet diese Datei.
    return buch.zyklus(HIER, daten_holen, signal, a.modus,
                       "handel/moondev_signalwelle")


if __name__ == "__main__":
    raise SystemExit(main())

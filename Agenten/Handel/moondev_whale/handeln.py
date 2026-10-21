"""Bot-Spur: Moon-Dev Whale - Open-Interest-Anomalie mit lokalem Urteil.

WOHER DIE IDEE KOMMT
--------------------
Der Agent `whale_agent` aus `Werkstatt/moon-dev-ai-agents` beobachtet das
offene Interesse (Open Interest) ueber ein Zeitfenster, erkennt eine ANOMALIE
gegen den Durchschnitt (`WHALE_THRESHOLD_MULTIPLIER = 1.31`) und laesst dann
ein Sprachmodell ueber die Richtung urteilen - genau drei Zeilen: BUY, SELL oder
NOTHING, ein Grund, eine Confidence.

DIE ARBEITSTEILUNG IST ABSICHT
------------------------------
  * **Daten**  OKX oeffentlich, ohne Schluessel (`Handel/moondev_daten.py`):
    `/public/open-interest` und `/rubik/stat/contracts/open-interest-volume`,
    Kurs aus `/market/candles`.
  * **Gate**   deterministisch und nachrechenbar: liegt die Aenderung ueber
    `_schwelle_mal_mittel` x Durchschnitt (und ueber `mindest_aenderung_pct`)?
    Ohne Anomalie wird das Modell GAR NICHT gefragt - das spart den Abruf und
    macht nachvollziehbar, wann ueberhaupt geurteilt wurde.
  * **Urteil**  das LOKALE Modell (`Handel/llm_lokal.py`, Vertrag des Bots
    wortgleich, Confidence-Schwelle aus der `wachen.json`).
  * **Buch**   `Handel/spur_buch.py` - Zustand, Journal, Ratsche, Stop/Ziel,
    Kopie nach `Q:\\Handel_Journal\\moondev_whale` (Bedingung 4).

Kein Live-Zweig: der Fremd-Agent handelt mit echten Schluesseln auf
Hyperliquid, diese Spur bucht Papier. Ein `--live` verweigert.

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
import llm_lokal as llm  # noqa: E402

# Test-Seams: None -> echter Abruf bzw. echtes Modell.
quelle_override = None
urteil_override = None


def mitte(werte):
    """Durchschnitt ohne Statistikpaket; leere Liste -> None."""
    werte = [w for w in werte if w is not None]
    if not werte:
        return None
    return sum(werte) / float(len(werte))


def fenster(w):
    """Fenster in Minuten und die dafuer noetige Zahl OI-Punkte."""
    minuten = float(w.get("fenster_minuten", 15))
    periode = float(w.get("periode_minuten", 5))
    return minuten, max(1, int(round(minuten / periode)))


def quelle(w):
    """OI-Verlauf, Kurs und daraus die Anomalie - alles aus OKX.

    Die Historie liefert 5-Minuten-Punkte, neuester zuerst. Der Vergleich ist
    `neuester Punkt` gegen den Punkt GENAU ein Fenster davor (Vorgabe des Bots:
    Letzter Wert gegen einen Wert fuenf Minuten vor dem Fenster).
    """
    inst = w.get("inst", "BTC-USDT-SWAP")
    fehler = []
    try:
        hist = daten.okx_oi_historie(w.get("ccy", "BTC"),
                                     w.get("periode", "5m"))
    except Exception as e:                                     # noqa: BLE001
        return {}, {}, ["OKX OI-Historie: %s" % str(e)[:120]]
    try:
        kerzen = daten.okx_kerzen(inst, bar=w.get("bar", "1H"), anzahl=3)
    except Exception as e:                                     # noqa: BLE001
        fehler.append("OKX Kerzen: %s" % str(e)[:120])
        kerzen = []
    if len(hist) < 3:
        return {}, {}, ["OKX OI-Historie: nur %d Punkte" % len(hist)]

    minuten, noetig = fenster(w)
    if len(hist) <= noetig:
        return {}, {}, ["OI-Historie zu kurz fuer ein Fenster von %.0f min"
                        % minuten]
    jetzt, vorher = hist[0][1], hist[noetig][1]
    if not jetzt or not vorher:
        return {}, {}, ["OI-Werte unlesbar"]

    aenderung = (jetzt - vorher) / vorher * 100.0
    # Das "Mittel" des Bots: die mittlere ABSOLUTE Aenderung ueber die letzten
    # Fenster - ohne sie waere jede kleine Bewegung eine "Anomalie".
    schritte = []
    for i in range(0, min(noetig * 8, len(hist) - 1)):
        a, b = hist[i][1], hist[i + 1][1]
        if a and b:
            schritte.append(abs(a - b) / b * 100.0)
    mittel = mitte(schritte)

    kurs = kerzen[-1][4] if kerzen else None
    kurs_vorher = kerzen[0][4] if kerzen else None
    kurs_pct = ((kurs - kurs_vorher) / kurs_vorher * 100.0
                if kurs and kurs_vorher else None)
    volumen = hist[0][2]

    schwelle = float(w.get("schwelle_mal_mittel", 1.31))
    mindest = float(w.get("mindest_aenderung_pct", 0.5))
    anomalie = False
    if mittel is not None:
        anomalie = (abs(aenderung) >= mindest
                    and abs(aenderung) >= schwelle * mittel)
    elif abs(aenderung) >= mindest:
        # Ohne Vergleichsmittel bleibt nur die harte Mindestschwelle - sie ist
        # die schwaechere Bedingung, deshalb steht sie im Journal als Hinweis.
        anomalie = True
        fehler.append("kein Vergleichsmittel - nur Mindestschwelle %.2f%%"
                      % mindest)

    d = {
        "inst": inst,
        "fenster_minuten": minuten,
        "oi_jetzt_usd": jetzt,
        "oi_vorher_usd": vorher,
        "oi_aenderung_pct": aenderung,
        "oi_mittel_pct": mittel,
        "schwelle_mal_mittel": schwelle,
        "anomalie": anomalie,
        "volumen_usd": volumen,
        "kurs": kurs,
        "kurs_aenderung_pct": kurs_pct,
    }
    if kurs:
        return {inst: d}, {inst: kurs}, fehler
    return {inst: d}, {}, fehler + ["kein Kurs - Buchung ohne Kurs unterbleibt"]


def marktbild(d, w):
    """Das Marktbild, das dem Modell vorgelegt wird - Zahlen, kein Urteil."""
    return llm.VERTRAG + """
Analyze BTC with {pct:+.2f}% OI change in {fenster:.0f}m:
Current OI: ${jetzt:,.0f}
Previous OI: ${vorher:,.0f}
Average absolute OI change in this window: {mittel}
Price 1h: {kurs_pct}
Open interest up with price up may indicate strong momentum.
Open interest down with price down may indicate capitulation, which can be a
good buy or a confirmation of the trend - you need to look at the data.
""".format(
        pct=d.get("oi_aenderung_pct") or 0.0,
        fenster=d.get("fenster_minuten") or 0.0,
        jetzt=d.get("oi_jetzt_usd") or 0.0,
        vorher=d.get("oi_vorher_usd") or 0.0,
        mittel=("%.2f%%" % d["oi_mittel_pct"] if d.get("oi_mittel_pct")
                is not None else "unknown"),
        kurs_pct=("%+.2f%%" % d["kurs_aenderung_pct"]
                  if d.get("kurs_aenderung_pct") is not None else "unknown"))


def richte(d, w):
    """Urteil des Modells zu einem Marktbild - Seam fuer die Tests."""
    if urteil_override:
        return urteil_override(d, w)
    return llm.entscheide(marktbild(d, w), w)


def signal(d, w):
    """Erst das Gate, dann das Modell. Kein Gate heisst: keine Frage."""
    if not d.get("anomalie"):
        print("  keine OI-Anomalie (%.2f%% gegen Mittel %s) - kein Urteil"
              % (d.get("oi_aenderung_pct") or 0.0,
                 ("%.2f%%" % d["oi_mittel_pct"]) if d.get("oi_mittel_pct")
                 is not None else "?"))
        return None
    seite, info = richte(d, w)
    d["llm"] = info
    print("  OI-Anomalie %+.2f%% in %.0f min -> Urteil: %s"
          % (d.get("oi_aenderung_pct") or 0.0, d.get("fenster_minuten") or 0.0,
             llm.zeile(info)))
    if seite:
        w["_grund"] = ("%s llm %s %.0f%%"
                       % (w.get("grund", "moondev_whale"), info.get("aktion"),
                          info.get("confidence", 0)))
    return seite


def daten_holen(w):
    """quelle() mit Test-Seam."""
    if quelle_override:
        return quelle_override(w)
    return quelle(w)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vorschau", action="store_const", const="vorschau",
                    dest="modus")
    ap.add_argument("--papier", action="store_const", const="papier",
                    dest="modus")
    ap.add_argument("--live", action="store_const", const="live", dest="modus")
    ap.add_argument("--wachen", action="store_const", const="wachen",
                    dest="modus")
    ap.set_defaults(modus="papier")
    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if a.modus == "live":
        # Live-Pfad ueber spur_buch (sperren_live + orderweg). Ist die
        # Sperrenkette zu, faellt der Lauf auf Papier zurueck und nennt den
        # Grund - derselbe Fallsafe wie die anderen Buch-Spuren.
        return buch.zyklus(HIER, daten_holen, signal, "live", "handel/moondev_whale")
    # Der Name im Bus-Journal steht WOERTLICH hier: die Anbindung oeffnet der
    # gemeinsame Kern (spur_buch.zyklus -> ereignis.lauf), aber welcher Spur die
    # Meldung gehoert, entscheidet diese Datei - abgeleitet aus dem Ordnernamen
    # ist es nur so lange richtig, wie Ordner und Spurname gleich heissen.
    return buch.zyklus(HIER, daten_holen, signal, a.modus,
                       "handel/moondev_whale")


if __name__ == "__main__":
    raise SystemExit(main())

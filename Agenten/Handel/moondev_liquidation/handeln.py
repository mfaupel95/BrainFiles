"""Bot-Spur: Moon-Dev Liquidationen - Zwangsschluesse mit lokalem Urteil.

WOHER DIE IDEE KOMMT
--------------------
Der Agent `liquidation_agent` aus `Werkstatt/moon-dev-ai-agents` summiert
die Zwangsschluesse der letzten Minuten getrennt nach Seite (long/short),
vergleicht sie mit dem vorigen Stand und laesst ein Sprachmodell urteilen -
genau drei Zeilen: BUY, SELL oder NOTHING, ein Grund, eine Confidence. Sein
Prompt steht in `LIQUIDATION_ANALYSIS_PROMPT`; seine Daten kommen ueber die
Moon-Dev-API (`MOONDEV_API_KEY`), sein Urteil von Claude oder DeepSeek.

Hier laeuft dieselbe Arbeitsteilung ohne Schluessel:

  * **Daten**  OKX oeffentlich (`/public/liquidation-orders`, `state=filled`).
    Die Saetze tragen `posSide` (long = ein Long wurde zwangsgeschlossen,
    short = ein Short) und `sz` in KONTRAKTEN - der USD-Wert entsteht erst
    ueber `ctVal` (BTC-USDT-SWAP: 0.01 BTC je Kontrakt). Ohne diese Zahl waeren
    alle Summen um Faktor 100 falsch.
  * **Gate**   deterministisch: der Abruf deckt nur die NEUESTEN 100 Saetze ab.
    Daraus wird die Spanne gebildet (`abdeckung_minuten`), die Summe darauf
    bezogen (USD je Stunde) und der Long-Anteil gerechnet. Geurteilt wird nur,
    wenn die Spanne frisch genug, die Rate hoch genug und das Ungleichgewicht
    deutlich ist - sonst faellt kein Aufruf.
  * **Urteil**  das LOKALE Modell (`Handel/llm_lokal.py`, Vertrag wie beim Bot,
    Confidence-Schwelle aus der `wachen.json`).
  * **Buch**   `Handel/spur_buch.py`, Kopie nach
    `Q:\\Handel_Journal\\moondev_liquidation` (Bedingung 4).

Kein Live-Zweig: der Fremd-Agent handelt mit echten Schluesseln, diese Spur
bucht Papier. Ein `--live` verweigert.

Aufruf:
  python handeln.py --vorschau | --papier | --wachen
"""

import argparse
import os
import sys
from datetime import datetime, timezone

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


def summen(liq, w):
    """Summen, Long-Anteil und Rate aus den zurueckgegebenen Saetzen.

    Einheit ist der GANZE Abruf, nicht ein festes Zeitfenster: OKX gibt nur die
    neuesten 100 Saetze heraus, und in einem Kaskadenmarkt spannen die wenigen
    Minuten. Ein festes Fenster waere dann entweder leer oder unvollstaendig -
    die Spanne wird deshalb gemessen und die Rate darauf bezogen.
    """
    gefuellt = [z for z in liq if z.get("usd")]
    if not gefuellt:
        return None
    jetzt = max(z["ts"] for z in gefuellt)
    alt = min(z["ts"] for z in gefuellt)
    abdeckung = (jetzt - alt) / 60000.0
    if abdeckung <= 0:
        return None
    lang = sum(z["usd"] for z in gefuellt if z.get("seite") == "long")
    kurz = sum(z["usd"] for z in gefuellt if z.get("seite") == "short")
    gesamt = lang + kurz
    if gesamt <= 0:
        return None
    rate = gesamt / abdeckung * 60.0
    return {"abdeckung_minuten": abdeckung, "anzahl": len(gefuellt),
            "lang_usd": lang, "kurz_usd": kurz, "gesamt_usd": gesamt,
            "anteil_long": lang / gesamt, "rate_usd_pro_stunde": rate}


def quelle(w):
    """Liquidationsbild plus Kurs - alles aus OKX, ohne Schluessel."""
    inst = w.get("inst", "BTC-USDT-SWAP")
    fehler = []
    try:
        liq = daten.okx_liquidationen(w.get("uly", "BTC-USDT"),
                                     w.get("abruf_grenze", 100))
    except Exception as e:                                     # noqa: BLE001
        return {}, {}, ["OKX Liquidationen: %s" % str(e)[:120]]
    if not liq:
        return {}, {}, ["OKX Liquidationen: keine Saetze"]
    s = summen(liq, w)
    if s is None:
        return {}, {}, ["Liquidationssaetze unlesbar (leere Summe)"]

    try:
        kerzen = daten.okx_kerzen(inst, bar=w.get("bar", "15m"), anzahl=5)
    except Exception as e:                                     # noqa: BLE001
        fehler.append("OKX Kerzen: %s" % str(e)[:120])
        kerzen = []

    mindest_abdeckung = float(w.get("mindest_abdeckung_minuten", 10))
    hoechst_abdeckung = float(w.get("hoechst_abdeckung_minuten", 240))
    mindest_rate = float(w.get("mindest_rate_usd_pro_stunde", 100000.0))
    kaskade = float(w.get("kaskade_rate_usd_pro_stunde", 750000.0))
    oben = float(w.get("schief_anteil_oben", 0.75))
    unten = float(w.get("schief_anteil_unten", 0.25))

    frisch = mindest_abdeckung <= s["abdeckung_minuten"] <= hoechst_abdeckung
    laut = s["rate_usd_pro_stunde"] >= mindest_rate
    schief = s["anteil_long"] >= oben or s["anteil_long"] <= unten
    kaskade_da = s["rate_usd_pro_stunde"] >= kaskade

    kurs = kerzen[-1][4] if kerzen else None
    kurs_vorher = kerzen[0][4] if kerzen else None

    d = dict(s)
    d.update({
        "inst": inst,
        "frisch": frisch,
        "laut": laut,
        "schief": schief,
        "kaskade": kaskade_da,
        "signal_gate": bool(frisch and laut and (schief or kaskade_da)),
        "kurs": kurs,
        "kurs_aenderung_pct": ((kurs - kurs_vorher) / kurs_vorher * 100.0
                               if kurs and kurs_vorher else None),
        "kerzen_text": kerzen_text(kerzen),
    })
    if not frisch:
        fehler.append("Ausschnitt nicht frisch (%.0f min, erlaubt %.0f-%.0f)"
                      % (s["abdeckung_minuten"], mindest_abdeckung,
                         hoechst_abdeckung))
    return {inst: d}, ({inst: kurs} if kurs else {}), fehler


def kerzen_text(kerzen):
    """Die letzten Kerzen als Zeilen - wie der Bot sie dem Modell zeigt."""
    zeilen = []
    for k in kerzen or []:
        tag = datetime.fromtimestamp(k[0] / 1000.0, timezone.utc)
        zeilen.append("  %s UTC  o=%.1f h=%.1f l=%.1f c=%.1f vol=%.0f"
                      % (tag.strftime("%d.%m. %H:%M"), k[1], k[2], k[3], k[4],
                         k[5] or 0.0))
    return "\n".join(zeilen) or "  no market data available"


def marktbild(d, w):
    """Der Prompt - die drei Schlusszeilen sind die des Bots."""
    return llm.VERTRAG + """
Analyze BTC liquidations:
Total liquidated: ${gesamt:,.0f} over the last {abdeckung:.0f} minutes
({rate:,.0f} USD per hour, {anzahl} events)

Current Long Liquidations: ${lang:,.0f}
Current Short Liquidations: ${kurz:,.0f}
Long share: {anteil:.2f} of the total

Market Data (last 5 {bar} candles):
{kerzen}

Large long liquidations often indicate potential bottoms (shorts taking profit)
Large short liquidations often indicate potential tops (longs taking profit)
Consider the ratio of long vs short liquidations and their relative changes
""".format(
        gesamt=d.get("gesamt_usd") or 0.0,
        abdeckung=d.get("abdeckung_minuten") or 0.0,
        rate=d.get("rate_usd_pro_stunde") or 0.0,
        anzahl=d.get("anzahl") or 0,
        lang=d.get("lang_usd") or 0.0,
        kurz=d.get("kurz_usd") or 0.0,
        anteil=d.get("anteil_long") or 0.0,
        bar=w.get("bar", "15m"),
        kerzen=d.get("kerzen_text") or "  no market data available")


def richte(d, w):
    """Urteil des Modells zu einem Marktbild - Seam fuer die Tests."""
    if urteil_override:
        return urteil_override(d, w)
    return llm.entscheide(marktbild(d, w), w)


def signal(d, w):
    """Erst das Gate, dann das Modell. Kein Gate heisst: keine Frage."""
    if not d.get("signal_gate"):
        print("  kein Liquidationssignal (%.0f min, %.0f USD/h, "
              "Long-Anteil %.2f)"
              % (d.get("abdeckung_minuten") or 0.0,
                 d.get("rate_usd_pro_stunde") or 0.0,
                 d.get("anteil_long") or 0.0))
        return None
    seite, info = richte(d, w)
    d["llm"] = info
    print("  Liquidationsdruck %.0f USD/h, Long-Anteil %.2f -> Urteil: %s"
          % (d.get("rate_usd_pro_stunde") or 0.0, d.get("anteil_long") or 0.0,
             llm.zeile(info)))
    if seite:
        w["_grund"] = ("%s llm %s %.0f%%"
                       % (w.get("grund", "moondev_liquidation"),
                          info.get("aktion"), info.get("confidence", 0)))
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
        return buch.zyklus(HIER, daten_holen, signal, "live", "handel/moondev_liquidation")
    # Der Name im Bus-Journal steht WOERTLICH hier: die Anbindung oeffnet der
    # gemeinsame Kern (spur_buch.zyklus -> ereignis.lauf), aber welcher Spur die
    # Meldung gehoert, entscheidet diese Datei - abgeleitet aus dem Ordnernamen
    # ist es nur so lange richtig, wie Ordner und Spurname gleich heissen.
    return buch.zyklus(HIER, daten_holen, signal, a.modus,
                       "handel/moondev_liquidation")


if __name__ == "__main__":
    raise SystemExit(main())

"""Bot-Spur: Moon-Dev Sentiment - Schlagzeilen mit lokalem Urteil.

WOHER DIE IDEE KOMMT
--------------------
Der Agent `sentiment_agent` aus `Werkstatt/moon-dev-ai-agents` sammelt
Texte zu seinen Tokens, bewertet sie (Stimmung zwischen -1 und +1) und meldet,
wenn der Betrag ueber `SENTIMENT_ANNOUNCE_THRESHOLD` (0.4) liegt. Seine Texte
kommen von Twitter ueber `twikit` (Cookies, Konto noetig), seine Bewertung aus
einem HuggingFace-Modell.

Hier laeuft dieselbe Idee mit dem, was ohne Konto oeffentlich ist:

  * **Daten**  die Titel der neuesten Meldungen aus den oeffentlichen RSS-Feeds
    von CoinDesk, Cointelegraph und CryptoSlate (`Handel/moondev_daten.py`),
    dazu der BTC-Kurs aus OKX-Kerzen.
  * **Gate**   ohne frische Schlagzeilen kein Urteil: erst ab
    `mindest_schlagzeilen` Ueberschriften wird ueberhaupt gefragt. Das ist die
    Uebertragung der Bot-Schwelle 0.4 - nur steht sie hier nicht als Zahl
    zwischen -1 und 1, sondern als Mindestmenge an Text.
  * **Urteil**  das LOKALE Modell (`Handel/llm_lokal.py`): es liest die
    Schlagzeilen und antwortet im Vertrag des Bots (BUY/SELL/NOTHING,
    Confidence). Unter `llm_mindest_confidence` faellt das Urteil aus.
  * **Buch**   `Handel/spur_buch.py`, Kopie nach
    `Q:\\Handel_Journal\\moondev_sentiment` (Bedingung 4).

Kein Live-Zweig: der Fremd-Agent handelt mit echten Schluesseln, diese Spur
bucht Papier. Ein `--live` verweigert.

WAS DIESE SPUR NICHT IST
------------------------
Kein Nachrichtenleser: bewertet werden die UEBERSCHRIFTEN der Redaktionen, nicht
deren Inhalt, und nur die drei Feeds, die oeffentlich sind. Die Ueberschrift ist
das, was der Markt zuerst sieht - mehr behauptet diese Spur nicht.

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


def quelle(w):
    """Schlagzeilen und Kurs - beides oeffentlich, ohne Schluessel."""
    inst = w.get("inst", "BTC-USDT-SWAP")
    fehler = []
    try:
        titel, fehler_feed = daten.schlagzeilen(
            je_quelle=w.get("je_quelle", 8))
    except Exception as e:                                     # noqa: BLE001
        return {}, {}, ["RSS: %s" % str(e)[:120]]
    fehler.extend(fehler_feed)
    hoechstens = int(w.get("hoechst_schlagzeilen", 12))
    grenze = int(w.get("zeichen_je_schlagzeile", 140))
    gewaehlt = [t[:grenze] for t in titel[:hoechstens] if t.strip()]

    try:
        kerzen = daten.okx_kerzen(inst, bar=w.get("bar", "1H"),
                                  anzahl=w.get("kerzen", 25))
    except Exception as e:                                     # noqa: BLE001
        fehler.append("OKX Kerzen: %s" % str(e)[:120])
        kerzen = []
    kurs = kerzen[-1][4] if kerzen else None
    kurs_24h = kerzen[0][4] if kerzen else None
    kurs_1h = kerzen[-2][4] if len(kerzen) > 1 else None
    if not kurs or not kurs_24h:
        fehler.append("kein Kurs - Buchung ohne Kurs unterbleibt")

    mindest = int(w.get("mindest_schlagzeilen", 6))
    d = {
        "inst": inst,
        "schlagzeilen": gewaehlt,
        "anzahl_schlagzeilen": len(gewaehlt),
        "nachrichten_gate": len(gewaehlt) >= mindest,
        "mindest_schlagzeilen": mindest,
        "kurs": kurs,
        "kurs_aenderung_24h": ((kurs - kurs_24h) / kurs_24h * 100.0
                               if kurs and kurs_24h else None),
        "kurs_aenderung_1h": ((kurs - kurs_1h) / kurs_1h * 100.0
                              if kurs and kurs_1h else None),
    }
    if not d["nachrichten_gate"]:
        fehler.append("nur %d Schlagzeilen (mindestens %d noetig)"
                      % (len(gewaehlt), mindest))
    if kurs:
        return {inst: d}, {inst: kurs}, fehler
    return {inst: d}, {}, fehler


def marktbild(d, w):
    """Der Prompt: Vertrag des Bots, darunter die Schlagzeilen."""
    zeilen = "\n".join("%d. \"%s\"" % (i + 1, t)
                       for i, t in enumerate(d.get("schlagzeilen") or []))
    return llm.VERTRAG + """
Analyze the sentiment of the latest crypto headlines for BTC:

{zeilen}

Market: BTC 24h {pct24}, 1h {pct1}

Judge the TONE of the headlines, not the price alone.
If the headlines point in no clear direction, answer NOTHING.
""".format(
        zeilen=zeilen or "  no headlines available",
        pct24=("%+.2f%%" % d["kurs_aenderung_24h"]
               if d.get("kurs_aenderung_24h") is not None else "unknown"),
        pct1=("%+.2f%%" % d["kurs_aenderung_1h"]
              if d.get("kurs_aenderung_1h") is not None else "unknown"))


def richte(d, w):
    """Urteil des Modells zu einem Marktbild - Seam fuer die Tests."""
    if urteil_override:
        return urteil_override(d, w)
    return llm.entscheide(marktbild(d, w), w)


def signal(d, w):
    """Erst das Gate, dann das Modell. Kein Gate heisst: keine Frage."""
    if not d.get("nachrichten_gate"):
        print("  nur %d Schlagzeilen (mindestens %d noetig) - kein Urteil"
              % (d.get("anzahl_schlagzeilen") or 0,
                 d.get("mindest_schlagzeilen") or 0))
        return None
    seite, info = richte(d, w)
    d["llm"] = info
    print("  %d Schlagzeilen -> Urteil: %s"
          % (d.get("anzahl_schlagzeilen") or 0, llm.zeile(info)))
    if seite:
        w["_grund"] = ("%s llm %s %.0f%%"
                       % (w.get("grund", "moondev_sentiment"),
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
        return buch.zyklus(HIER, daten_holen, signal, "live", "handel/moondev_sentiment")
    # Der Name im Bus-Journal steht WOERTLICH hier: die Anbindung oeffnet der
    # gemeinsame Kern (spur_buch.zyklus -> ereignis.lauf), aber welcher Spur die
    # Meldung gehoert, entscheidet diese Datei - abgeleitet aus dem Ordnernamen
    # ist es nur so lange richtig, wie Ordner und Spurname gleich heissen.
    return buch.zyklus(HIER, daten_holen, signal, a.modus,
                       "handel/moondev_sentiment")


if __name__ == "__main__":
    raise SystemExit(main())

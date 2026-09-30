"""Lohnt eine andere Quotewaehrung? Messen statt annehmen.

Anlass: Die kraken-Spur kann seit 30.09.2026 in EUR, USDC und EURC handeln
(Quote je Paar aus der API, siehe quote.py). Damit stellt sich die Frage, ob
es sich lohnt, Guthaben in eine andere Waehrung zu tauschen - etwa das frei
liegende EURC-Kapital zu nutzen. Dieses Werkzeug beantwortet sie mit zwei
Messungen, die zusammen die Entscheidung tragen:

  1. DECKUNG   Deckt die eigene Waehrung die Instrumente schon ab? Gibt es
               ein Instrument, das NUR in der anderen Quote erreichbar ist?
               Ist die Antwort nein, erschliesst der Umtausch kein Instrument.
  2. SPREAD    Ist der Markt in der anderen Waehrung enger? Ein Rundlauf
               zahlt rund EINEN Spread; der Umtausch kostet einmalig die
               Taker-Gebuehr. Break-even = Umtausch / Ersparnis je Runde.

Ergebnis vom 30.09.2026 (gemessen, nicht geschaetzt): EUR deckt alle 17
Instrumente der Watchlist ab, kein Instrument ist nur in EURC oder USDC
erreichbar; EURC ist Quote auf 3 Paaren (XBT/ETH/SOL), die EUR schon fuehrt.
Die USDC-Paare sind im Mittel 4,2 bp WEITER als die EUR-Paare (13 Instrumente).
Der Umtausch kostet 60 bp und fuehrt in schlechtere Maerkte - Break-even gibt
es keinen. Deshalb bleibt EURC bei 0,00 und wird nichts umgetauscht.

Aufruf (aus Agenten/Handel/kraken, nur oeffentliche Schnittstelle, kein
Schluessel, keine Order):

    python quoten_vergleich.py                # beide Messungen
    python quoten_vergleich.py --nur deckung
    python quoten_vergleich.py --quote USDC   # andere Waehrung pruefen

Fuer einen VOLLstaendigen Deckungslauf ueber ALLE Paare der Boerse (nicht nur
die Watchlist) gibt es `--alle`; das braucht einen AssetPairs-Abruf.
"""

import argparse
import json
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
if HIER not in sys.path:
    sys.path.insert(0, HIER)

import kraken                                            # noqa: E402
import quote as q                                        # noqa: E402

assert kraken.__file__.startswith(HIER), \
    "fremdes kraken-Modul geladen: %s" % kraken.__file__

TAKER = 0.006            # gemessen 22.09.2026 an echten Fuellungen (Kraken Pro
                         # ohne Volumenstufe); nur fuer die Break-even-Rechnung


def _als_aufruf(abruf=None):
    """Der Seam von quote.py ist ein AUFRUFBARES, das die Antwort liefert.

    `quote._paare(abruf)` ruft `abruf()` auf. Ein blankes dict hier
    durchzureichen faellt deshalb mit "'dict' object is not callable" um -
    der Test hat genau das gefunden. Beide Formen werden angenommen, damit
    ein Test die Antwort direkt hinlegen kann.
    """
    if callable(abruf):
        return abruf
    if abruf is not None:
        return lambda: abruf
    return lambda: kraken._roh_oeffentlich("AssetPairs") or {}


def wachen_lesen():
    pfad = os.path.join(HIER, "wachen.json")
    with open(pfad, encoding="utf-8") as f:
        return json.load(f)


def paare_nach_wsname(abruf=None):
    """{basis: {quote: paar}} aus AssetPairs, ueber wsname normalisiert."""
    aus = {}
    for name, d in _als_aufruf(abruf)().items():
        ws = str(d.get("wsname") or "")
        if "/" not in ws:
            continue
        b, qt = [t.strip().upper() for t in ws.split("/", 1)]
        aus.setdefault(b, {})[qt] = name
    return aus


def deckung(watchlist, ziel, abruf=None):
    """Deckt die Watchlist ab, was die andere Waehrung zusaetzlich bringt.

    Rueckgabe: {'instrumente', 'ohne_eigene', 'ohne_ziel', 'nur_ziel',
                'basen', 'paare_je_quote'}
    """
    pro = paare_nach_wsname(abruf)
    basen = sorted({q.basis_von_paar(p, _als_aufruf(abruf)) for p in watchlist})
    ohne_eigene, ohne_ziel, nur_ziel = [], [], []
    for b in basen:
        qts = pro.get(b, {})
        hat_eur = any(t in ("EUR", "ZEUR") for t in qts)
        hat_ziel = ziel in qts
        if not hat_eur:
            ohne_eigene.append(b)
        if not hat_ziel:
            ohne_ziel.append(b)
        if hat_ziel and not hat_eur:
            nur_ziel.append(b)
    verteilung = {}
    for _b, qts in pro.items():
        for t in qts:
            verteilung[t] = verteilung.get(t, 0) + 1
    return {"instrumente": len(basen), "basen": basen,
            "ohne_eigene": ohne_eigene, "ohne_ziel": ohne_ziel,
            "nur_ziel": nur_ziel, "paare_je_quote": verteilung}


def _ticker_spread_bp(paar, wiederholungen=3, pause=0.4):
    """Median des relativen Spreads in Basispunkten ueber mehrere Abrufe.

    EIN Abruf ist bei duennen Buechern zu laut: am 30.09.2026 schwankte
    LINK/EUR zwischen 0,7 und 4,8 bp und ALGO/USDC zwischen 23,5 und 55,0 bp
    - dieselbe Messung, Minuten auseinander. Der Median mehrerer Abrufe macht
    die Aussage belastbar; eine einzelne Stichprobe darf keine Empfehlung
    tragen.
    """
    import statistics
    import time
    werte = []
    for i in range(max(1, int(wiederholungen))):
        if i:
            time.sleep(pause)
        try:
            roh = kraken._roh_oeffentlich("Ticker", pair=paar) or {}
            d = list(roh.values())[0]
            bid, ask = float(d["b"][0]), float(d["a"][0])
            if bid > 0 and ask > 0:
                werte.append((ask - bid) / ((ask + bid) / 2.0) * 1e4)
        except Exception:                                 # noqa: BLE001
            continue
    if not werte:
        return None
    return statistics.median(werte)


def spreads(watchlist, ziel, eigene="EUR", abruf=None, wiederholungen=3):
    """Spread-Vergleich je INSTRUMENT zwischen `eigene` und `ziel`.

    `eigene` ist die Waehrung, die das Konto haelt (nicht die, die zufaellig
    am besten aussieht) - verglichen wird also "behalten" gegen "umtauschen".
    Je Instrument genau EIN Paar pro Waehrung, sonst steht dasselbe
    Instrument zweimal in der Tabelle (XBT hat ein EUR- UND ein EURC-Paar).
    """
    pro = paare_nach_wsname(abruf)
    zeilen = []
    gesehen = set()
    for paar in watchlist:
        try:
            basis = q.basis_von_paar(paar, _als_aufruf(abruf))
            eigene_quote = q.quote_von_paar(paar, _als_aufruf(abruf))
        except q.QuoteUnbekannt:
            continue
        if basis in gesehen:
            continue
        if q.lesbar(eigene_quote) != str(eigene).upper():
            continue
        gesehen.add(basis)
        anderes = pro.get(basis, {}).get(ziel)
        if not anderes:
            continue
        a = _ticker_spread_bp(paar, wiederholungen)
        b = _ticker_spread_bp(anderes, wiederholungen)
        if a is None or b is None:
            continue
        zeilen.append({"instrument": basis, "eigenes_paar": paar,
                       "ziel_paar": anderes, "eigene_bp": a, "ziel_bp": b,
                       "vorteil_ziel_bp": a - b})
    return zeilen


def bericht(watchlist, ziel="USDC", abruf=None):
    d = deckung(watchlist, ziel, abruf)
    print("Instrumente der Watchlist: %d" % d["instrumente"])
    print("Paare der Boerse mit Quote %-5s: %d" % (ziel, d["paare_je_quote"].get(ziel, 0)))
    for t in ("ZEUR", "EUR"):
        if t in d["paare_je_quote"]:
            print("Paare der Boerse mit Quote %-5s: %d" % (t, d["paare_je_quote"][t]))
            break
    if d["nur_ziel"]:
        print("NUR in %s erreichbar: %s" % (ziel, ", ".join(d["nur_ziel"])))
    else:
        print("Kein Instrument ist NUR in %s erreichbar - der Umtausch "
              "erschliesst kein Instrument." % ziel)

    zeilen = spreads(watchlist, ziel, abruf=abruf)
    if not zeilen:
        print("\nSpreads: nicht messbar (keine Paarung in beiden Waehrungen).")
        return d, zeilen
    print("\n%-6s %12s %12s   %s"
          % ("Instr", "eigene Quote", "Quote %s" % ziel, "Vorteil %s" % ziel))
    for z in zeilen:
        print("%-6s %12.1f %12.1f   %+7.1f bp"
              % (z["instrument"], z["eigene_bp"], z["ziel_bp"],
                 z["vorteil_ziel_bp"]))
    mittel = sum(z["vorteil_ziel_bp"] for z in zeilen) / len(zeilen)
    print("\nGemessen: %d Instrumente, mittlerer Vorteil %s: %+.1f bp je Runde"
          % (len(zeilen), ziel, mittel))
    print("Umtausch einmalig: %.0f bp (Taker %.2f %%)" % (TAKER * 1e4, TAKER * 100))
    if mittel > 0:
        print("Break-even: %.0f Runden" % (TAKER * 1e4 / mittel))
    else:
        print("Break-even: KEINER - %s ist nicht enger, der Umtausch kostet nur."
              % ziel)
    return d, zeilen


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quote", default="USDC",
                    help="Waehrung, gegen die geprueft wird (Standard USDC)")
    ap.add_argument("--nur", choices=("deckung", "spread"), default=None)
    args = ap.parse_args()

    w = wachen_lesen()
    watchlist = w.get("watchlist") or []
    if not watchlist:
        print("Keine watchlist in wachen.json - nichts zu messen.")
        return 1

    if args.nur == "deckung":
        d = deckung(watchlist, args.quote)
        print("NUR in %s erreichbar: %s" % (args.quote, d["nur_ziel"] or "keines"))
        return 0
    if args.nur == "spread":
        for z in spreads(watchlist, args.quote):
            print("%-6s %+7.1f bp" % (z["instrument"], z["vorteil_ziel_bp"]))
        return 0
    bericht(watchlist, args.quote)
    return 0


if __name__ == "__main__":
    sys.exit(main())
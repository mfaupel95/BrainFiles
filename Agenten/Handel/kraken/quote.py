"""Welche Waehrung steht hinter einem Kraken-Paar - aus der API, nicht geraten.

Die Spur 3 (kraken) war bis 30.09.2026 auf EUR festgelegt: Watchlist in EUR,
Guthaben-Tor gegen "ZEUR", Journalspalte "eur". Damit lag Kapital brach, das
in einer anderen Quotewaehrung auf demselben Konto liegt - Kraken fuehrt Paare
in EUR, EURC und USDC.

Dieses Modul beantwortet die zwei Fragen, die dafuer noetig sind:

  1. Welche Quotewaehrung hat dieses Paar?      -> quote_von_paar()
  2. Wie heisst diese Waehrung im KONTOSTAND?   -> guthaben_asset()

Zu (2): Kraken nennt die Quote eines Paares nicht immer so wie den Posten im
Kontostand. Gemessen am 30.09.2026 an 1455 Paaren:

  - Fiat bekommt ein "Z":   AssetPairs sagt "ZEUR",  Balance sagt "ZEUR"
  - Stablecoins nicht:      AssetPairs sagt "EURC",  Balance sagt "EURC"
                            AssetPairs sagt "USDC",  Balance sagt "USDC"
  - Ausreisser:             EURCHF traegt die Quote "CHF" (ohne Z), waehrend
                            der Kontostand "ZCHF" heisst.

Deshalb wird die Quote NICHT in einen Namen uebersetzt, sondern gegen den
tatsaechlich abgerufenen Kontostand aufgeloest: erst der Code selbst, dann
"Z"+Code, dann ohne fuehrendes Z. Findet sich keiner, ist das Guthaben 0 und
die Waehrung gilt als nicht vorhanden - nie als "irgendwas wird schon passen".

Ein unbekanntes Paar ist ein FEHLER, kein Rueckfall auf EUR: wer die Quote
raet, handelt im falschen Markt. QuoteUnbekannt ist die Folge, und die
Aufrufer behandeln sie als Sperre.
"""

import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
if HIER not in sys.path:
    sys.path.insert(0, HIER)

import kraken                                            # noqa: E402

assert kraken.__file__.startswith(HIER), \
    "fremdes kraken-Modul geladen: %s" % kraken.__file__


class QuoteUnbekannt(Exception):
    """Die Quotewaehrung liess sich nicht bestimmen - dann wird nicht gehandelt."""


_CACHE = {}


def vergiss_cache():
    """AssetPairs erneut holen (Tests und lange Laeufe)."""
    _CACHE.clear()


def _paare(abruf=None):
    """Alle Paare aus AssetPairs. `abruf` ist die Naht fuer Tests: eine
    Funktion ohne Argumente, die das Dict liefert. Ohne sie wird EINMAL
    abgerufen und behalten - die Antwort aendert sich nicht innerhalb eines
    Zyklus."""
    if abruf is not None:
        return abruf() or {}
    if "paare" not in _CACHE:
        _CACHE["paare"] = kraken._roh_oeffentlich("AssetPairs") or {}
    return _CACHE["paare"]


def _eintrag(paar, abruf=None):
    return _paare(abruf).get(str(paar or "").strip().upper()) or {}


def quote_von_paar(paar, abruf=None):
    """Der Kraken-Code der Quotewaehrung: 'ZEUR', 'EURC', 'USDC'.

    Erst das Feld `quote`, dann der Teil nach dem Schraegstrich in `wsname`
    (dort steht er normalisiert: 'XBT/EURC'). Fehlt beides, ist das Paar
    entweder unbekannt oder unvollstaendig - beides ist ein Fehler."""
    w = _eintrag(paar, abruf)
    if not w:
        raise QuoteUnbekannt("Paar %r steht nicht in AssetPairs" % (paar,))
    q = str(w.get("quote") or "").strip().upper()
    if q:
        return q
    ws = str(w.get("wsname") or "")
    if "/" in ws:
        rest = ws.split("/", 1)[1].strip().upper()
        if rest:
            return rest
    raise QuoteUnbekannt("Paar %r traegt keine Quote" % (paar,))


def basis_von_paar(paar, abruf=None):
    """Die BASIS-Kennung des Paares - aus `wsname`, weil dort normalisiert.

    XXBTZEUR (base 'XXBT') und XBTEURC (base 'XBT') sind DASSELBE Instrument
    in zwei Waehrungen. Nur der wsname macht daraus zweimal 'XBT', und nur so
    kann das Buch erkennen, dass es schon eine Position in diesem Instrument
    hat."""
    w = _eintrag(paar, abruf)
    if not w:
        raise QuoteUnbekannt("Paar %r steht nicht in AssetPairs" % (paar,))
    ws = str(w.get("wsname") or "")
    if "/" in ws:
        basis = ws.split("/", 1)[0].strip().upper()
        if basis:
            return basis
    basis = str(w.get("base") or "").strip().upper()
    if basis:
        return basis
    raise QuoteUnbekannt("Paar %r traegt keine Basis" % (paar,))


def lesbar(code):
    """'ZEUR' -> 'EUR'. Nur fuer die ANZEIGE - zum Rechnen und Vergleichen
    bleibt der API-Code stehen.

    Die Regel ist bewusst eng: vier Zeichen und ein fuehrendes Z. Das trifft
    die Fiat-Codes (ZEUR, ZUSD, ZGBP, ZCAD, ZCHF, ZJPY, ZAUD) und laesst
    Stablecoins in Ruhe (EURC, USDC, USDT)."""
    c = str(code or "").strip().upper()
    if len(c) == 4 and c.startswith("Z"):
        return c[1:]
    return c


def guthaben_asset(quote, kontostaende_):
    """Der Schluessel im Kontostand, der diese Quote traegt - oder None."""
    q = str(quote or "").strip().upper()
    if not q:
        return None
    st = kontostaende_ or {}
    for kandidat in (q, "Z" + q, q[1:] if q.startswith("Z") else q, "X" + q):
        if kandidat in st:
            return kandidat
    return None


def frei(kontostaende_, quote):
    """Freies Guthaben in dieser Quotewaehrung. Unbekannt = 0.0."""
    a = guthaben_asset(quote, kontostaende_)
    if a is None:
        return 0.0
    try:
        return float(kontostaende_.get(a) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def quoten_der_watchlist(watchlist, abruf=None):
    """Die Quote-Codes, die in einer Watchlist wirklich vorkommen - in der
    Reihenfolge des ersten Auftretens. Unbekannte Paare werden uebergangen
    (der Scan hat sie ohnehin verworfen)."""
    aus = []
    for paar in watchlist or []:
        try:
            q = quote_von_paar(paar, abruf)
        except QuoteUnbekannt:
            continue
        if q not in aus:
            aus.append(q)
    return aus


def basen_der_watchlist(watchlist, abruf=None):
    """{paar: basis} - die normalisierte Instrument-Kennung je Paar."""
    aus = {}
    for paar in watchlist or []:
        try:
            aus[paar] = basis_von_paar(paar, abruf)
        except QuoteUnbekannt:
            continue
    return aus
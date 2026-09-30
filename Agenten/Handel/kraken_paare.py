"""Wie heisst ein Instrument bei Kraken - EINE Tabelle, je Quote.

Warum ein eigenes Modul
-----------------------
Am 28.09.2026 stellten vier Spuren dieselbe Frage ("wie heisst BTC bei
Kraken?") und jede hatte ihre eigene Antwort: ``mosaic/kraken_spot.PAARE``,
``moondev_marktlage/live_kraken.PAAR``, die Watchlist der kraken-Spur und
``nautilus_kraken/wachen.json``. Wer ein Paar ergaenzt, ergaenzt es viermal -
oder vergisst drei. Hier steht es einmal.

Die Quote ist eine Konfigurationsfrage, keine Codefrage
-------------------------------------------------------
Das Kraken-Konto rechnet in EUR, deshalb ist **EUR die Vorgabe**; USDC waehlt
man ueber ``quote``. Am 28.09.2026 gemessen: Kraken listet 45 USDC-Paare, darunter
XBTUSDC, ETHUSDC, SOLUSDC, XRPUSDC, ADAUSDC, LINKUSDC, AVAXUSDC, DOTUSDC,
LTCUSDC, BNBUSDC, XMRUSDC, XDGUSDC (Quelle: GET /0/public/AssetPairs, Feld
``quote`` = USDC, ``status`` = online). EURC fuehrt Kraken gegen **nur drei**
Maerkte - XBTEURC, ETHEURC, SOLEURC (30.09.2026 gemessen).

Was ein Paar NICHT ist: eine Waehrungsempfehlung. Ein USDC-Paar auf einem
EUR-Konto traegt zusaetzlich das EUR/USD-Risiko - wer in EUR rechnet, will
EUR-Paare. USDC lohnt, wenn das Guthaben in USDC liegt oder die Boerse den
Markt nur gegen USDC fuehrt.

Ein unbekanntes Paar ist ein FEHLER, keine stille Ersatzwahl: sonst landet
eine Order im falschen Markt.
"""

# Geprueft am 28.09.2026 gegen GET /0/public/AssetPairs (Feld wsname/quote).
PAARE = {
    "EUR": {
        # Kern-Instrumente (mosaic, kraken-Spur). mosaic rechnet in OKX-Namen
        # (BTC-USDC) - die Kraken-Quote ist eine eigene Wahl, deshalb stehen
        # die USDC-Instrumentnamen auch hier und zeigen auf EUR-Paare.
        "BTC-EUR": "XXBTZEUR",
        "BTC-USDC": "XXBTZEUR",
        "BTC-USDT": "XXBTZEUR",
        "XBT-EUR": "XXBTZEUR",
        "ETH-EUR": "XETHZEUR",
        "ETH-USDC": "XETHZEUR",
        "ETH-USDT": "XETHZEUR",
        "SOL-EUR": "SOLEUR",
        "SOL-USDC": "SOLEUR",
        "SOL-USDT": "SOLEUR",
        "XRP-EUR": "XXRPZEUR",
        "ADA-EUR": "ADAEUR",
        "DOT-EUR": "DOTEUR",
        "LINK-EUR": "LINKEUR",
        "LTC-EUR": "XLTCZEUR",
        # Listing-Arb-Paare (moondev_listingarb, 22.09.2026)
        "AKE-EUR": "AKEEUR",
        "DAI-EUR": "DAIEUR",
        "HYPE-EUR": "HYPEEUR",
        "KAS-EUR": "KASEUR",
        "LIT-EUR": "LITEUR",
        "MNT-EUR": "MNTEUR",
        "VVV-EUR": "VVVEUR",
        "WBT-EUR": "WBTEUR",
        "XMR-EUR": "XXMRZEUR",   # Kraken-Sonderform: X-Prefix + Z-Quote
    },
    "USDC": {
        # Aliase unserer Instrumentnamen auf Kraken-Namen (mosaic rechnet in
        # OKX-Namen: BTC-USDC, nicht XBT-USDC).
        "BTC-USDC": "XBTUSDC",
        "DOGE-USDC": "XDGUSDC",
        "ADA-USDC": "ADAUSDC",
        "ALGO-USDC": "ALGOUSDC",
        "APE-USDC": "APEUSDC",
        "ATOM-USDC": "ATOMUSDC",
        "AVAX-USDC": "AVAXUSDC",
        "BCH-USDC": "BCHUSDC",
        "BERA-USDC": "BERAUSDC",
        "BNB-USDC": "BNBUSDC",
        "CRO-USDC": "CROUSDC",
        "DOT-USDC": "DOTUSDC",
        "ETH-USDC": "ETHUSDC",
        "FARTCOIN-USDC": "FARTCOINUSDC",
        "LINK-USDC": "LINKUSDC",
        "LTC-USDC": "LTCUSDC",
        "MANA-USDC": "MANAUSDC",
        "PENGU-USDC": "PENGUUSDC",
        "SHIB-USDC": "SHIBUSDC",
        "SOL-USDC": "SOLUSDC",
        "TON-USDC": "TONUSDC",
        "TRUMP-USDC": "TRUMPUSDC",
        "VET-USDC": "VETUSDC",
        "VIRTUAL-USDC": "VIRTUALUSDC",
        "XBT-USDC": "XBTUSDC",
        "XDC-USDC": "XDCUSDC",
        "XDG-USDC": "XDGUSDC",
        "XMR-USDC": "XMRUSDC",
        "XRP-USDC": "XRPUSDC",
        "XTZ-USDC": "XTZUSDC",
    },
    # EURC (30.09.2026 gemessen gegen GET /0/public/AssetPairs, Feld quote):
    # Kraken fuehrt gegen EURC NUR drei Maerkte - XBT, ETH, SOL. Alle drei sind
    # online, pair_decimals 1/2/2, ordermin 0.00005/0.001/0.06. Eine kurze
    # Tabelle ist hier die Wahrheit, nicht eine Luecke: wer mehr hineinschreibt,
    # erfindet einen Markt. Und weil es nur drei sind, darf es KEINEN Rueckfall
    # auf andere Quoten geben - ein "DOGE-EURC" muss ein Fehler sein und nicht
    # still in einem EUR-Markt landen.
    "EURC": {
        "BTC-EURC": "XBTEURC",
        "BTC-USDC": "XBTEURC",
        "BTC-EUR": "XBTEURC",
        "XBT-EURC": "XBTEURC",
        "ETH-EURC": "ETHEURC",
        "ETH-USDC": "ETHEURC",
        "ETH-EUR": "ETHEURC",
        "SOL-EURC": "SOLEURC",
        "SOL-USDC": "SOLEURC",
        "SOL-EUR": "SOLEURC",
    },
}

# Paare ohne Markt (beide Seiten Stablecoin) sind bewusst NICHT enthalten -
# sie sehen wie ein Handel aus, sind aber ein Tausch.
QUOTEN = tuple(PAARE)


def quote_aus_wachen(w, vorgabe="EUR"):
    """Quote einer Spur: ``kraken_quote`` in der wachen.json, sonst die Vorgabe.

    Ein unbekannter Wert ist ein Fehler - ein Tippfehler darf nicht still auf
    EUR zurueckfallen und dort echtes Geld bewegen.
    """
    q = str((w or {}).get("kraken_quote") or vorgabe).strip().upper()
    if q not in PAARE:
        raise ValueError("kraken_quote %r unbekannt - erlaubt: %s"
                         % (q, ", ".join(QUOTEN)))
    return q


def paar_fuer(inst, quote="EUR"):
    """Kraken-Paar zu einem Instrument. Unbekannt = klarer Fehler.

    Sucht zuerst in der gewaehlten Quote; findet sich dort nichts, wird in den
    anderen Quoten nachgesehen, damit ein bereits in Kraken-Namen geschriebenes
    Instrument (z. B. ``XXBTZEUR`` aus einer Watchlist) unveraendert
    durchgeht.
    """
    q = str(quote or "EUR").strip().upper()
    if q not in PAARE:
        raise ValueError("Quote %r unbekannt - erlaubt: %s"
                         % (q, ", ".join(QUOTEN)))
    schluessel = str(inst).strip().upper()
    if schluessel in PAARE[q]:
        return PAARE[q][schluessel]
    # Ein fertiger Kraken-Name (Watchlist-Fall: "SOLEUR", "XBTUSDC") geht durch,
    # unabhaengig von der gewaehlten Quote - er enthaelt seine Quote selbst.
    for tabelle in PAARE.values():
        if schluessel in tabelle.values():
            return schluessel
    # KEIN Rueckfall auf Schluessel anderer Quoten: 'BTC-USDC' mit Quote EUR
    # muss XXBTZEUR ergeben (mosaic rechnet in OKX-Namen), 'BTC-EUR' mit Quote
    # USDC dagegen ein Fehler sein. Ein stiller Wechsel der Waehrung waere eine
    # Order im falschen Markt.
    raise ValueError("kein Kraken-Paar fuer %s in Quote %s (kraken_paare.PAARE)"
                     % (inst, q))


def quote_von_paar(name):
    """Quote eines fertigen Kraken-Namens ('SOLEUR' -> 'EUR', 'XBTUSDC' -> 'USDC').

    Fuer Anzeigen und Pruefungen: wer den Namen schon hat, will nicht raten,
    in welcher Waehrung er notiert.
    """
    n = str(name or "").strip().upper()
    for q, tabelle in PAARE.items():
        if n in tabelle.values():
            return q
    if n.endswith("USDC"):
        return "USDC"
    if n.endswith("EUR") or n.endswith("ZEUR"):
        return "EUR"
    return None
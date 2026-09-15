"""Datenzugang der Moon-Dev-Bot-Spuren - eine Quelle fuer alle.

WARUM DIESE DATEI EXISTIERT
---------------------------
Die drei CoinGecko-Agenten des Bot-Repos (`new_or_top_agent`, `coingecko_agent`,
`listingarb_agent`) sind Monolithen mit `main()`: sie holen Marktdaten, lassen
ein Sprachmodell urteilen und handeln. Eine einzelne, wiederverwendbare
Datenfunktion wie bei `moondev_funding` (dort `nice_funcs_hl.get_funding_rates`)
gibt es bei ihnen NICHT - und ihr CoinGecko-Zugang laeuft ueber die
Pro-API (`pro-api.coingecko.com`, API-Key noetig).

Diese Datei liefert deshalb denselben Datenweg ueber die **oeffentliche**
CoinGecko-API und die **oeffentliche** Binance-API - beide ohne Schluessel,
beide mit den Endpunkten, die der Bot ebenfalls benutzt. Was hier NICHT
passiert: das Urteil des Bots. Seine Empfehlung kommt von einem Sprachmodell;
die Regel jeder Spur steht im Haus und ist nachrechenbar.

Nur Standardbibliothek (urllib): die Spuren laufen im gemeinsamen venv, und
`requests` gehoert dort nicht zu ihren Abhaengigkeiten.
"""

import json
import urllib.error
import urllib.parse
import urllib.request

COINGECKO = "https://api.coingecko.com/api/v3"
BINANCE = "https://api.binance.com/api/v3"
ZEITGRENZE = 30

# Ein eigener Kopf, weil CoinGecko nackte urllib-Aufrufe ohne User-Agent
# ablehnt (403). Der Name nennt den Absender - wer die API betreibt, soll
# sehen, woher die Aufrufe kommen.
KOPF = {"User-Agent": "brainfiles-handelsspur/1.0 (privater Papierlauf)"}


def hole_json(url, zeitgrenze=ZEITGRENZE):
    """JSON von einer oeffentlichen API. Fehler werden geworfen, nicht geraten."""
    anfrage = urllib.request.Request(url, headers=KOPF)
    with urllib.request.urlopen(anfrage, timeout=zeitgrenze) as antwort:
        return json.loads(antwort.read().decode("utf-8", "replace"))


def maerkte(vs="usd", anzahl=100, seiten=1, sortierung="market_cap_desc"):
    """CoinGecko `/coins/markets` - Preis, Volumen, 24h-Aenderung.

    `seiten` > 1 blaettert weiter (je Seite 250). Der Endpunkt ist derselbe,
    den der Bot nutzt; ohne Schluessel begrenzt CoinGecko nur die Rate, nicht
    die Felder.
    """
    felder = {
        "vs_currency": vs,
        "order": sortierung,
        "per_page": str(max(1, min(250, int(anzahl)))),
        "page": str(max(1, int(seiten))),
        "sparkline": "false",
        "price_change_percentage": "24h,7d",
    }
    return hole_json("%s/coins/markets?%s" % (COINGECKO, urllib.parse.urlencode(felder)))


def binance_paare():
    """Alle handelbaren Spot-Paare von Binance als Menge von Basiswerten.

    Rueckgabe: set von Basis-Symbolen in Grossschreibung ('BTC', 'ETH', ...).
    Paare sind '<BASIS><QUOTE>' (z.B. BTCUSDT) - die Aufteilung auf Quote-
    Endungen ist noetig, weil Binance keine Basis-Spalte liefert.
    """
    daten = hole_json("%s/exchangeInfo?permissions=SPOT" % BINANCE)
    quotes = ("USDT", "USDC", "FDUSD", "TUSD", "BTC", "ETH", "BNB", "EUR", "TRY",
              "BRL", "DAI", "XRP", "SOL")
    aus = set()
    for s in daten.get("symbols", []):
        if s.get("status") != "TRADING":
            continue
        symbol = s.get("symbol") or ""
        for q in sorted(quotes, key=len, reverse=True):
            if symbol.endswith(q) and len(symbol) > len(q):
                aus.add(symbol[: -len(q)])
                break
    return aus


def zahl(wert):
    """Ein Zahlenwert oder None - nie ein geratener Ersatz."""
    try:
        if wert is None:
            return None
        return float(wert)
    except (TypeError, ValueError):
        return None

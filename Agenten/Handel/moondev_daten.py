"""Datenzugang der Moon-Dev-Bot-Spuren - eine Quelle fuer alle.

WARUM DIESE DATEI EXISTIERT
---------------------------
Die drei CoinGecko-Agenten des Bot-Repos (`new_or_top_agent`, `coingecko_agent`,
`listingarb_agent`) sind Monolithen mit `main()`: sie holen Marktdaten, lassen
ein Sprachmodell urteilen und handeln. Eine einzelne, wiederverwendbare
Datenfunktion wie bei `moondev_funding` (dort `nice_funcs_hl.get_funding_rates`)
gibt es bei ihnen NICHT - und ihr CoinGecko-Zugang laeuft ueber die
Pro-API (`pro-api.coingecko.com`, API-Key noetig).

Diese Datei liefert deshalb denselben Datenweg ueber **oeffentliche** Quellen -
CoinGecko, Binance, OKX und die RSS-Feeds der Redaktionen -, alle ohne
Schluessel und mit den Endpunkten, die der Bot ebenfalls benutzt.

Seit 17.09.2026 kommt auch das URTEIL des Bots zurueck, aber lokal: die Spuren
`moondev_whale`, `moondev_liquidation` und `moondev_sentiment` lassen ein Modell
auf dieser Maschine urteilen (`Handel/llm_lokal.py`, Ollama) - Vertrag und
Confidence-Schwelle wie beim Bot, nur ohne Schluessel und ohne Kosten. Dieses
Modul bleibt die Datenschicht darunter.

Nur Standardbibliothek (urllib): die Spuren laufen im gemeinsamen venv, und
`requests` gehoert dort nicht zu ihren Abhaengigkeiten.
"""

import json
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

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


# --- OKX: offenes Interesse, Liquidationen, Kerzen -------------------------
# Dieselben oeffentlichen Endpunkte, die der Haus-Handel schon kennt
# (scanner/okx.py) - hier ohne Schluessel, ohne Order, nur lesend. Die drei
# LLM-Spuren brauchen genau diese Zahlen: den OI-Verlauf (Wale), die
# Zwangsschluesse (Liquidationen) und einen Kurs (alle).
OKX = "https://www.okx.com/api/v5"

# ctVal je Instrument - einmal geholt, dann gemerkt. Ohne diese Zahl waeren die
# Liquidationssummen um Faktor 100 falsch: OKX liefert `sz` in KONTRAKTEN
# (BTC-USDT-SWAP: 0.01 BTC je Kontrakt), nicht in Coins.
_CTV = {}


def okx_json(pfad, felder=None, zeitgrenze=ZEITGRENZE):
    """Ein oeffentlicher OKX-Endpunkt. `felder` sind die Query-Parameter."""
    url = "%s/%s" % (OKX, pfad.lstrip("/"))
    if felder:
        url = "%s?%s" % (url, urllib.parse.urlencode(felder))
    return hole_json(url, zeitgrenze)


def okx_offenes_interesse(inst="BTC-USDT-SWAP"):
    """{inst, oi, oi_usd, ts} - offenes Interesse in Kontrakten und in USD."""
    daten = okx_json("public/open-interest",
                     {"instType": "SWAP", "instId": inst})
    if not daten.get("data"):
        raise ValueError("OKX open-interest: leere Antwort")
    s = daten["data"][0]
    return {"inst": s.get("instId"), "oi": zahl(s.get("oi")),
            "oi_usd": zahl(s.get("oiUsd")), "ts": int(s.get("ts") or 0)}


def okx_oi_historie(ccy="BTC", periode="5m"):
    """[[ts, oi_usd, volumen_usd], ...] - aeltester Eintrag zuletzt.

    576 Punkte zu 5 Minuten = 48 Stunden. Der Endpunkt liefert oeffentlich,
    ohne Schluessel.
    """
    daten = okx_json("rubik/stat/contracts/open-interest-volume",
                     {"ccy": ccy, "period": periode})
    aus = []
    for zeile in daten.get("data") or []:
        if len(zeile) >= 3:
            aus.append([int(zeile[0]), zahl(zeile[1]), zahl(zeile[2])])
    return aus


def okx_kerzen(inst="BTC-USDT", bar="1H", anzahl=3):
    """[[ts, o, h, l, c, vol], ...] AUFSTEIGEND (OKX liefert rueckwaerts)."""
    daten = okx_json("market/candles",
                     {"instId": inst, "bar": bar, "limit": str(int(anzahl))})
    aus = []
    for zeile in daten.get("data") or []:
        if len(zeile) >= 6:
            aus.append([int(zeile[0])] + [zahl(x) for x in zeile[1:6]])
    return list(reversed(aus))


def okx_vertragsgroesse(inst="BTC-USDT-SWAP"):
    """ctVal des Kontrakts (0.01 BTC bei BTC-USDT-SWAP)."""
    if inst in _CTV:
        return _CTV[inst]
    daten = okx_json("public/instruments", {"instType": "SWAP", "instId": inst})
    if not daten.get("data"):
        raise ValueError("OKX instruments: leere Antwort")
    _CTV[inst] = zahl(daten["data"][0].get("ctVal"))
    return _CTV[inst]


def okx_liquidationen(uly="BTC-USDT", grenze=100):
    """Zwangsschluesse: [{"seite", "preis", "kontrakte", "usd", "ts"}, ...].

    `posSide` ist die Seite des KONTOS, das liquidiert wurde: "long" heisst, ein
    Long wurde zwangsgeschlossen (Verkauf am Markt), "short" ein Short. Der
    Endpunkt ist auf 100 Saetze begrenzt - mehr gibt OKX oeffentlich nicht
    heraus, deshalb steht die Abdeckung des Fensters im Ergebnis (siehe
    `abdeckung_sekunden` in der Spur).
    """
    daten = okx_json("public/liquidation-orders",
                     {"instType": "SWAP", "uly": uly, "state": "filled",
                      "limit": str(max(1, min(100, int(grenze))))})
    inst, aus = None, []
    for satz in daten.get("data") or []:
        inst = satz.get("instId") or inst
        for d in satz.get("details") or []:
            preis, groesse = zahl(d.get("bkPx")), zahl(d.get("sz"))
            if preis is None or groesse is None:
                continue
            aus.append({"seite": (d.get("posSide") or "").lower(),
                        "preis": preis, "kontrakte": groesse,
                        "ts": int(d.get("ts") or 0), "inst": inst})
    if inst and aus:
        ctval = okx_vertragsgroesse(inst)
        if ctval:
            for z in aus:
                z["usd"] = z["kontrakte"] * ctval * z["preis"]
    return aus


def zahl(wert):
    """Ein Zahlenwert oder None - nie ein geratener Ersatz."""
    try:
        if wert is None:
            return None
        return float(wert)
    except (TypeError, ValueError):
        return None


# --- Schlagzeilen aus oeffentlichen RSS-Feeds ------------------------------
# Die Vorlage ist der Bot-Agent `sentiment_agent`: er liest Texte und laesst sie
# bewerten. Seine Texte kommen von Twitter (twikit-Cookies, Zugang noetig) -
# oeffentlich und ohne Konto geht nur, was die Redaktionen selbst veroeffentlichen.
# Genau das steht hier: die Titel der neuesten Meldungen, mehr nicht.
RSS_QUELLEN = ("https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml",
               "https://cointelegraph.com/rss",
               "https://cryptoslate.com/feed/")


def hole_text(url, zeitgrenze=ZEITGRENZE):
    """Rohtext einer Seite (RSS ist XML, kein JSON)."""
    anfrage = urllib.request.Request(url, headers=KOPF)
    with urllib.request.urlopen(anfrage, timeout=zeitgrenze) as antwort:
        return antwort.read().decode("utf-8", "replace")


def schlagzeilen(quellen=RSS_QUELLEN, je_quelle=8, zeitgrenze=ZEITGRENZE):
    """(Titel, Fehler) - die neuesten Meldungen, ohne Doppelte.

    Gelesen wird ueber `item`: der Titel des Kanals selbst ist der Name der
    Quelle, keine Meldung - wer `//title` nimmt, schickt dem Modell den
    Feed-Namen als erste Schlagzeile.
    """
    titel, fehler = [], []
    for url in quellen:
        try:
            baum = ET.fromstring(hole_text(url, zeitgrenze))
        except Exception as e:                                 # noqa: BLE001
            fehler.append("%s: %s" % (url.split("/")[2], str(e)[:80]))
            continue
        for punkt in list(baum.iter("item"))[:max(1, int(je_quelle))]:
            t = (punkt.findtext("title") or "").strip()
            if t:
                titel.append(t)
    aus, gesehen = [], set()
    for t in titel:
        k = t.lower()
        if k not in gesehen:
            gesehen.add(k)
            aus.append(t)
    return aus, fehler

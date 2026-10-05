#!/usr/bin/env python3
"""Marktdaten ohne Schluessel und ohne Kosten: Krypto, Aktien, Indizes, ETFs.

Drei Fragen, drei Wege - alle oeffentlich, alle bezahlbar null:

* ``kurs``   Krypto ueber OKX (Hausboerse, ``/api/v5/market/ticker``), alles
             andere (Aktie, Index, ETF, Rohstoff) ueber die Yahoo-Chart-Schnitt-
             stelle, die Waehrung und Vortagesschluss mitliefert.
* ``kerzen`` Zeitreihe ueber dieselbe Yahoo-Schnittstelle; funktioniert fuer
             beide Welten (Krypto als ``BTC-USD``), ``range``/``interval``
             werden durchgereicht.
* ``news``   die Titel der Redaktionen aus oeffentlichen RSS-Feeds: ohne Symbol
             die Krypto- und Markt-Feeds, mit Symbol den Ticker-Feed von Yahoo
             (``?s=AAPL``) beziehungsweise die Krypto-Feeds.

Jede Zeile nennt Quelle und Zeitpunkt - eine Zahl ohne Quelle ist hier ein
Fehler, keine Antwort. Nur die Standardbibliothek, keine Abhaengigkeiten.

Beispiele::

    python marktdaten.py kurs BTC-USDT AAPL "^GDAXI" VUSA.DE
    python marktdaten.py kerzen BTC-USD --zeitraum 1mo --intervall 1d
    python marktdaten.py news AAPL --anzahl 5
    python marktdaten.py selbsttest        # Parser, ohne Netz
"""

from __future__ import annotations

import argparse
import json
import sys
# Die Haus-Bremse gegen OKX-Drosselung: sie begrenzt ALLE OKX-Abrufe des
# Hauses prozessuebergreifend (Fensterspiegel in Agenten/Handel/cache/okx-takt),
# damit Wache, Handelszentrale und die drei Dauerlauf-Stufen sich nicht
# gegenseitig in die Drosselung laufen. Gemessen 05.10.2026: 6 parallene
# Threads -> 93x 'OKX 50011', nacheinander 120 Abrufe -> 0 Fehler.
#
# Sie wird ueber den PFAD geladen (importlib), nicht ueber sys.path: diese
# Datei laeuft aus Agenten/Werkzeuge/, wo der Handel-Ordner nicht im Pfad
# steht. Genau darum nehmen es die Spuren (sys.path.append) und die Werkzeuge
# hier (importlib) auf zwei Wegen - einer waere an einer Stelle falsch.
import os as _os
import sys as _sys
import importlib.util as _ilu
_s = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(
    __file__))), "Handel", "okx_takt.py")
if not _os.path.exists(_s):
    raise RuntimeError("Haus-Bremse fehlt: %s" % _s)
_spec = _ilu.spec_from_file_location("okx_takt", _s)
okx_takt = _ilu.module_from_spec(_spec)
_sys.modules["okx_takt"] = okx_takt
_spec.loader.exec_module(okx_takt)

import urllib.error
import urllib.parse
import urllib.request
from email.utils import parsedate_to_datetime

KOPF = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Hermes-Marktdaten"}
ZEITGRENZE = 15
OKX_TICKER = "https://www.okx.com/api/v5/market/ticker?instId=%s"
YAHOO_CHART = ("https://query1.finance.yahoo.com/v8/finance/chart/%s"
               "?range=%s&interval=%s")
YAHOO_NEWS = ("https://feeds.finance.yahoo.com/rss/2.0/headline?s=%s"
              "&region=US&lang=en-US")
KRYPTO_FEEDS = (("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml"),
                ("Cointelegraph", "https://cointelegraph.com/rss"),
                ("CryptoSlate", "https://cryptoslate.com/feed/"))
MARKT_FEEDS = (("MarketWatch", "https://feeds.content.dowjones.io/public/rss/mw_topstories"),)

#: Endungen, die ein Krypto-Paar bezeichnen (dann fragt der Kurs OKX).
KRYPTO_ENDUNGEN = ("-USDT", "-USDC", "-USD")


# --- Netz ------------------------------------------------------------------

def hole(url, zeitgrenze=ZEITGRENZE):
    """Rohtext einer URL (RSS ist XML, kein JSON)."""
    anfrage = urllib.request.Request(url, headers=KOPF)
    okx_takt.reserviere()
    with urllib.request.urlopen(anfrage, timeout=zeitgrenze) as antwort:
        return antwort.read().decode("utf-8", "replace")


def ist_krypto(symbol):
    """Krypto-Paar (OKX) oder alles andere (Yahoo)? Nicht raten, sondern am
    Symbol entscheiden: ein Paar traegt eine Krypto-Endung."""
    return symbol.upper().endswith(KRYPTO_ENDUNGEN)


# --- Parser (ohne Netz pruefbar) ------------------------------------------

def okx_kurs(symbol, rohtext):
    """Zeile aus der OKX-Ticker-Antwort: Kurs, 24-h-Aenderung, Hoch/Tief."""
    daten = json.loads(rohtext)
    if daten.get("code") != "0" or not daten.get("data"):
        raise ValueError("OKX: %s" % (daten.get("msg") or "leere Antwort"))
    d = daten["data"][0]
    letzter, offen = float(d["last"]), float(d["open24h"])
    return {"symbol": d["instId"], "quelle": "OKX", "waehrung": d["instId"].split("-")[-1],
            "kurs": letzter, "aenderung_pct": (letzter / offen - 1) * 100 if offen else None,
            "hoch": float(d["high24h"]), "tief": float(d["low24h"]),
            "zeit": int(d["ts"]) // 1000}


def yahoo_kurs(symbol, rohtext):
    """Zeile aus der Yahoo-Chart-Antwort: Kurs, Aenderung gegen den Vortag."""
    daten = json.loads(rohtext)
    if daten.get("chart", {}).get("error"):
        raise ValueError("Yahoo: %s" % daten["chart"]["error"].get("description"))
    ergebnis = (daten.get("chart") or {}).get("result")
    if not ergebnis:
        raise ValueError("Yahoo: leere Antwort")
    meta = ergebnis[0]["meta"]
    kurs = meta.get("regularMarketPrice")
    if kurs is None:
        raise ValueError("Yahoo: kein Kurs in der Antwort")
    vortag = meta.get("chartPreviousClose") or meta.get("previousClose")
    return {"symbol": meta.get("symbol", symbol), "quelle": "Yahoo",
            "waehrung": meta.get("currency"), "kurs": float(kurs),
            "aenderung_pct": (kurs / vortag - 1) * 100 if vortag else None,
            "hoch": meta.get("regularMarketDayHigh"), "tief": meta.get("regularMarketDayLow"),
            "boerse": meta.get("fullExchangeName"),
            "zeit": meta.get("regularMarketTime")}


def yahoo_kerzen(symbol, rohtext):
    """Kerzen aus der Yahoo-Antwort: Liste (zeit, open, high, low, close, volume)."""
    daten = json.loads(rohtext)
    ergebnis = (daten.get("chart") or {}).get("result")
    if not ergebnis:
        raise ValueError("Yahoo: leere Antwort")
    r = ergebnis[0]
    zeiten = r.get("timestamp") or []
    quote = ((r.get("indicators") or {}).get("quote") or [{}])[0]
    reihen = []
    for i, ts in enumerate(zeiten):
        def feld(name):
            werte = quote.get(name) or []
            return werte[i] if i < len(werte) else None
        if feld("close") is None:
            continue
        reihen.append({"zeit": ts, "open": feld("open"), "hoch": feld("high"),
                       "tief": feld("low"), "kurs": feld("close"),
                       "volumen": feld("volume")})
    meta = r.get("meta") or {}
    return {"symbol": meta.get("symbol", symbol), "waehrung": meta.get("currency"),
            "kerzen": reihen}


def rss_titel(rohtext, quelle, grenze=8):
    """(Titel, Zeit) aus einem RSS-Feed.

    Gelesen wird ueber ``item``: der Kanal-Titel selbst ist der Name der Quelle
    und keine Meldung - wer ``//title`` nimmt, liefert den Feed-Namen als erste
    Schlagzeile aus.
    """
    import xml.etree.ElementTree as ET
    try:
        wurzel = ET.fromstring(rohtext)
    except ET.ParseError as fehler:
        raise ValueError("RSS nicht lesbar: %s" % fehler)
    treffer = []
    for item in wurzel.iter("item"):
        knoten = item.find("title")
        if knoten is None or not (knoten.text or "").strip():
            continue
        zeit = item.find("pubDate")
        treffer.append({"quelle": quelle,
                        "titel": " ".join(knoten.text.split()),
                        "zeit": zeit.text.strip() if zeit is not None and zeit.text else None})
        if len(treffer) >= grenze:
            break
    return treffer


def zeit_text(stempel):
    """Unix-Sekunden oder RSS-Datum als UTC-Zeitstempel (ISO, Minuten)."""
    if stempel is None:
        return None
    if isinstance(stempel, (int, float)):
        import datetime
        return datetime.datetime.fromtimestamp(stempel, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
    try:
        return parsedate_to_datetime(stempel).astimezone().strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return str(stempel)


# --- Befehle ---------------------------------------------------------------

def kurs_holen(symbol, zeitgrenze=ZEITGRENZE):
    """Eine Kurszeile - OKX fuer Krypto, Yahoo fuer alles andere."""
    if ist_krypto(symbol):
        return okx_kurs(symbol, hole(OKX_TICKER % symbol, zeitgrenze))
    return yahoo_kurs(symbol, hole(YAHOO_CHART % (urllib.parse.quote(symbol), "5d", "1d"), zeitgrenze))


def kerzen_holen(symbol, zeitraum="1mo", intervall="1d", zeitgrenze=ZEITGRENZE):
    return yahoo_kerzen(symbol, hole(YAHOO_CHART % (urllib.parse.quote(symbol), zeitraum, intervall), zeitgrenze))


def news_holen(symbole=(), anzahl=8, zeitgrenze=ZEITGRENZE):
    """(Zeilen, Fehler) - Feeds je Symbol, ohne Symbol die Markt- und Krypto-Feeds."""
    quellen = []
    for symbol in symbole:
        if ist_krypto(symbol):
            quellen += KRYPTO_FEEDS
        else:
            quellen.append(("%s (Yahoo)" % symbol, YAHOO_NEWS % urllib.parse.quote(symbol)))
    if not symbole:
        quellen = list(KRYPTO_FEEDS) + list(MARKT_FEEDS)
    zeilen, fehler, gesehen = [], [], set()
    for name, url in quellen:
        try:
            for eintrag in rss_titel(hole(url, zeitgrenze), name, anzahl):
                schluessel = eintrag["titel"].lower()
                if schluessel in gesehen:
                    continue
                gesehen.add(schluessel)
                zeilen.append(eintrag)
        except (urllib.error.URLError, ValueError, OSError) as problem:
            fehler.append("%s: %s" % (name, problem))
    zeilen.sort(key=lambda z: z["zeit"] or "", reverse=True)
    return zeilen[:anzahl], fehler


def kurs_text(zeile):
    aenderung = zeile.get("aenderung_pct")
    pfeil = "" if aenderung is None else ("+" if aenderung >= 0 else "")
    prozent = "-" if aenderung is None else "%.2f%%" % aenderung
    return ("%-10s %10.4f %-4s %s%s   Hoch/Tief %s/%s   %s   %s" % (
        zeile["symbol"], zeile["kurs"], zeile.get("waehrung") or "?",
        pfeil, prozent, _kurz(zeile.get("hoch")), _kurz(zeile.get("tief")),
        zeile["quelle"], zeit_text(zeile.get("zeit"))))


def _kurz(wert):
    return "-" if wert is None else ("%.4f" % wert)


def main(argv=None):
    zerleger = argparse.ArgumentParser(description="Marktdaten ohne Schluessel (Krypto, Aktien, Indizes, ETFs)")
    unter = zerleger.add_subparsers(dest="befehl", required=True)

    p_kurs = unter.add_parser("kurs", help="aktueller Kurs je Symbol")
    p_kurs.add_argument("symbole", nargs="+", help="z. B. BTC-USDT AAPL ^GDAXI VUSA.DE")
    p_kurs.add_argument("--json", action="store_true")

    p_kerzen = unter.add_parser("kerzen", help="Zeitreihe eines Symbols")
    p_kerzen.add_argument("symbol")
    p_kerzen.add_argument("--zeitraum", default="1mo", help="1d, 5d, 1mo, 6mo, 1y, max")
    p_kerzen.add_argument("--intervall", default="1d", help="1m, 5m, 1h, 1d, 1wk")
    p_kerzen.add_argument("--json", action="store_true")

    p_news = unter.add_parser("news", help="Schlagzeilen der Redaktionen (RSS)")
    p_news.add_argument("symbole", nargs="*", help="leer = Markt- und Krypto-Feeds")
    p_news.add_argument("--anzahl", type=int, default=8)
    p_news.add_argument("--json", action="store_true")

    unter.add_parser("selbsttest", help="Parser ohne Netz pruefen")

    args = zerleger.parse_args(argv)

    if args.befehl == "selbsttest":
        return selbsttest()

    if args.befehl == "kurs":
        ergebnis, fehler = [], []
        for symbol in args.symbole:
            try:
                ergebnis.append(kurs_holen(symbol))
            except (urllib.error.URLError, ValueError, OSError) as problem:
                fehler.append("%s: %s" % (symbol, problem))
        print(json.dumps(ergebnis, ensure_ascii=False, indent=2) if args.json
              else "\n".join(kurs_text(z) for z in ergebnis))
        for zeile in fehler:
            print("FEHLER %s" % zeile, file=sys.stderr)
        return 1 if fehler and not ergebnis else 0

    if args.befehl == "kerzen":
        try:
            daten = kerzen_holen(args.symbol, args.zeitraum, args.intervall)
        except (urllib.error.URLError, ValueError, OSError) as problem:
            print("FEHLER %s: %s" % (args.symbol, problem), file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(daten, ensure_ascii=False, indent=2))
        else:
            print("%s (%s), %d Kerzen %s/%s" % (daten["symbol"], daten.get("waehrung") or "?",
                                                len(daten["kerzen"]), args.zeitraum, args.intervall))
            for kerze in daten["kerzen"]:
                print("%s  %10s  H %10s  T %10s  C %10s" % (
                    zeit_text(kerze["zeit"]), _kurz(kerze["open"]), _kurz(kerze["hoch"]),
                    _kurz(kerze["tief"]), _kurz(kerze["kurs"])))
        return 0

    zeilen, fehler = news_holen(args.symbole, args.anzahl)
    if args.json:
        print(json.dumps(zeilen, ensure_ascii=False, indent=2))
    else:
        for eintrag in zeilen:
            print("%s  %-16s %s" % (zeit_text(eintrag["zeit"]), eintrag["quelle"], eintrag["titel"]))
    for zeile in fehler:
        print("FEHLER %s" % zeile, file=sys.stderr)
    return 0 if zeilen else 1


# --- Selbsttest (ohne Netz) ------------------------------------------------

OKX_BEISPIEL = ('{"code":"0","msg":"","data":[{"instType":"SPOT","instId":"BTC-USDT",'
                '"last":"86258.6","askPx":"86258.7","bidPx":"86258.6","open24h":"86586.2",'
                '"high24h":"86763.8","low24h":"85111.1","ts":"1790107201000"}]}')
YAHOO_BEISPIEL = ('{"chart":{"result":[{"meta":{"symbol":"AAPL","currency":"USD",'
                  '"regularMarketPrice":339.75,"chartPreviousClose":331.34,'
                  '"regularMarketTime":1790107201,"fullExchangeName":"NasdaqGS"},'
                  '"timestamp":[1790000000,1790107200],"indicators":{"quote":[{'
                  '"open":[330.0,332.0],"high":[335.0,340.0],"low":[329.0,331.0],'
                  '"close":[332.0,339.75],"volume":[1000,2000]}]}}],"error":null}}')
RSS_BEISPIEL = ('<?xml version="1.0"?><rss version="2.0"><channel><title>Feedname</title>'
                '<item><title>Erste Meldung</title><pubDate>Mon, 22 Sep 2026 10:00:00 GMT</pubDate></item>'
                '<item><title>Zweite Meldung</title><pubDate>Mon, 22 Sep 2026 09:00:00 GMT</pubDate></item>'
                '</channel></rss>')


def selbsttest():
    fehler = []
    krypto = okx_kurs("BTC-USDT", OKX_BEISPIEL)
    if abs(krypto["aenderung_pct"] + 0.3784) > 0.01 or krypto["quelle"] != "OKX":
        fehler.append("okx_kurs: %r" % krypto)
    if ist_krypto("BTC-USDT") is not True or ist_krypto("AAPL") or ist_krypto("VUSA.DE"):
        fehler.append("ist_krypto erkennt die Paare nicht")

    aktie = yahoo_kurs("AAPL", YAHOO_BEISPIEL)
    if abs(aktie["kurs"] - 339.75) > 1e-6 or abs(aktie["aenderung_pct"] - 2.538) > 0.01:
        fehler.append("yahoo_kurs: %r" % aktie)

    reihe = yahoo_kerzen("AAPL", YAHOO_BEISPIEL)
    if len(reihe["kerzen"]) != 2 or reihe["kerzen"][1]["kurs"] != 339.75:
        fehler.append("yahoo_kerzen: %r" % reihe)

    titel = rss_titel(RSS_BEISPIEL, "Test", 8)
    if [t["titel"] for t in titel] != ["Erste Meldung", "Zweite Meldung"]:
        fehler.append("rss_titel: %r" % titel)
    if titel[0]["quelle"] != "Test":
        fehler.append("rss_titel: Quelle fehlt")

    for zeile, marke in ((kurs_text(krypto), "BTC-USDT"), (kurs_text(aktie), "AAPL")):
        if marke not in zeile or "OKX" not in kurs_text(krypto):
            fehler.append("kurs_text: %r" % zeile)

    if fehler:
        for f in fehler:
            print("FEHLER %s" % f)
        return 1
    print("Selbsttest bestanden: okx_kurs, yahoo_kurs, yahoo_kerzen, rss_titel, ist_krypto, kurs_text")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Lesezugriff auf die oeffentlichen Pump.fun-APIs - die Signalquelle der
Kopier-Spur.

Diese Datei kennt **keinen** Schreibaufruf: Pump.fun-Kaepfe laufen ueber
Solana-Transaktionen mit einer Wallet-Signatur, und diese Spur hat keine
Schluessel. Der Waechter unten ist trotzdem noetig: Wer hier spaeter einen
Pfad ergaenzt, der Geld bewegt (swap, order, transfer ...), bekommt einen
Abbruch, **bevor** ein Prozess startet. Die Gegenprobe steht in kopier.py
beim Import: fehlt der Waechter, startet das Buch nicht.

Was geliefert wird
------------------
  leaderboard()            Taegliche PnL-Rangliste der Trader (Rang, PnL)
  portfolio(wallet)        Offene Positionen eines Traders (Kurs, Marktkapitalisierung)
  letzter_kauf(w,m)        Der letzte Kauf eines Traders auf einem Token
                           (trades/batch) - Zeitstempel und Kurs des Vorbilds
  coin(mint)               Coin-Details (gebannt? nsfw?) fuer das Risiko-Tor
  risiko(mint)             Stufe fuer das Buch: ok oder gesperrt
  preise(punkte)           Letzte gehandelte Kurse - fuer Bericht und GUI

Hosts und Felder sind am 14.09.2026 gegen die echte API geprueft, nicht aus
der Erinnerung geschrieben. Zwei Feldnamen-Fallen, beide gemessen:
  - trades/batch liefert 'priceUSD', der v2-Trades-Endpunkt 'priceUsd'
  - vor dem ersten Abruf testen; die Normalisierung unten deckt beide ab.
"""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

HOST_V3 = "https://frontend-api-v3.pump.fun"
HOST_SWAP = "https://swap-api.pump.fun"
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
TIMEOUT = 25

# Die einzige Kette dieser Spur. Pump.fun ist Solana; das Leaderboard und
# user-portfolio schleppen auch EVM/Base/BNB-Positionen mit, die hier
# gefiltert werden (chainId != 1399811149 -> kette None -> Lage-Zaehler).
KETTEN = {"solana": 1399811149}

# Waechter. Anders als beim OnchainOS-CLI gibt es hier keine
# Unterbefehle - der Schutz ist eine Whitelist von Lese-Pfaden:
# (Host, Methode) -> zulaessige Pfad-Anfaenge. Alles andere wird
# verweigert, bevor eine Verbindung aufgebaut wird. Die Eintraege sind
# absichtlich als Tupel von Woertern formuliert, die auf Schreibabsicht
# deuten, damit der Guard als Abfrage lesbar bleibt.
SCHREIBBEFEHLE = ("swap", "order", "cancel", "transfer", "withdraw", "sign",
                  "payment", "wallet")

_ERLAUBT = {
    (HOST_V3, "GET"): ("/pnl-leaderboard", "/user-portfolio/", "/users/",
                       "/coins/"),
    (HOST_SWAP, "POST"): ("/v1/coins/",),
    (HOST_SWAP, "GET"): ("/v2/coins/",),
}


class Lesefehler(RuntimeError):
    """Die API hat nicht geantwortet, was erwartet wurde."""


class Schreibversuch(RuntimeError):
    """Ein Pfad oder eine Methode wurde angefordert, die diese Spur nicht
    liest. Diese Spur ist papierfest."""


def ruf(url, methode="GET", daten=None):
    """Ein Leseaufruf. Rueckgabe: der geparste JSON-Inhalt - oder Lesefehler.

    Jeder Pfad, der nicht zur Lesewhitelist passt, wird hier abgewiesen,
    bevor eine Verbindung aufgebaut wird - egal ob er durch einen Fehler in
    der Steuerung, einen neuen Codepfad oder ein versehentlich vertauschtes
    Argument entstuebe.
    """
    if any(w in methode.lower() for w in SCHREIBBEFEHLE):
        raise Schreibversuch("Methode '%s' ist nicht lesend - diese Spur "
                             "liest nur." % methode)
    _pruefe_pfad(url, methode)
    anfrage = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    anfrage.method = methode
    if daten is not None:
        anfrage.add_header("Content-Type", "application/json")
        anfrage.data = json.dumps(daten).encode("utf-8")
    try:
        with urllib.request.urlopen(anfrage, timeout=TIMEOUT) as antwort:
            roh = antwort.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raise Lesefehler("HTTP %d von %s" % (e.code, _kurz(url))) from e
    except urllib.error.URLError as e:
        raise Lesefehler("keine Verbindung zu %s (%s)" % (_kurz(url), e)) from e
    except OSError as e:
        raise Lesefehler("Netzfehler bei %s (%s)" % (_kurz(url), e)) from e
    try:
        return json.loads(roh)
    except ValueError as e:
        raise Lesefehler("keine JSON-Antwort von %s (%s): %s"
                         % (_kurz(url), e, roh[:120])) from e


def _pruefe_pfad(url, methode):
    """Host und Pfad gegen die Lesewhitelist - der eigentliche Waechter."""
    import posixpath
    try:
        t = urllib.parse.urlsplit(url)
        host = "%s://%s" % (t.scheme, t.netloc)
        # Normalisieren, damit '..' die Praefix-Pruefung nicht unterlaeuft
        # (/user-portfolio/../swap ist /swap und nicht in der Whitelist).
        pfad = posixpath.normpath(t.path)
    except ValueError as e:
        raise Lesefehler("unbrauchbare URL (%s)" % e) from e
    erlaubt = _ERLAUBT.get((host, methode))
    if erlaubt is None:
        raise Schreibversuch("'%s %s' ist kein Leseaufruf dieser Spur."
                             % (methode, _kurz(url)))
    if not any(pfad.startswith(a) for a in erlaubt):
        raise Schreibversuch("Pfad '%s' ist nicht in der Lesewhitelist."
                             % pfad)
    # Das eine POST dieser Spur liest nur Daten: die letzten Trades eines
    # Traders auf EINEM Token. Alles andere POST ist kein Leseaufruf.
    if methode == "POST" and not pfad.endswith("/trades/batch"):
        raise Schreibversuch("POST auf '%s' ist kein Leseaufruf (nur "
                             "trades/batch)." % pfad)


def _kurz(url):
    return urllib.parse.urlsplit(url).path


# --- die Abfragen -----------------------------------------------------------

def leaderboard(periode="daily", sort="combined", limit=10):
    """Taegliche PnL-Rangliste der Trader - das Feld der Verfolgungsliste.

    period: daily | weekly | monthly   sort: combined | realized | unrealized
    Jeder Eintrag traegt rank, walletAddress, username, pnlUsd, pnlPercent,
    positionsCount und buySpendSol - die gemessenen Zahlen neben dem Feed.
    """
    q = urllib.parse.urlencode({"period": periode, "sort": sort,
                                "limit": limit})
    d = ruf("%s/pnl-leaderboard?%s" % (HOST_V3, q))
    return d.get("entries") or []


def portfolio(wallet):
    """Offene Positionen eines Traders, normalisiert.

    Rueckgabe: {"positions": {mint: {...}}, "summary": {...}} - nur Solana
    (chainId == 1399811149) traegt eine Kette; der Rest bekommt kette None
    und faellt im Buch als 'kette nicht unterstuetzt' aus, ein Lage-Zaehler.
    Die Preise und Marktkapitalisierungen kommen direkt aus dem Endpunkt -
    die Werte sind die des API-Refreshes (updatedAt), nicht von uns geraten.
    """
    d = ruf("%s/user-portfolio/%s" % (HOST_V3, urllib.parse.quote(wallet)))
    aus = {}
    for p in d.get("positions") or []:
        mint = p.get("coinMint")
        if not mint:
            continue
        coin = p.get("coin") or {}
        aus[mint] = {
            "mint": mint,
            "kette": _kette_aus_chainid(p.get("chainId")),
            "symbol": coin.get("symbol") or p.get("symbol") or "?",
            "name": coin.get("name") or "?",
            "preis": _zahl(p.get("tokenPriceUsd")),
            "marktkap_usd": _zahl(coin.get("marketCapUsd")),
            "wert_usd": _zahl(p.get("valueUsd")),
            "updated_at": p.get("updatedAt"),
            "is_exited": bool(p.get("isExited")),
            "dust": bool(p.get("dustFloorFiltered")),
            "vermutlich_verloren": bool(p.get("likelyLost")),
            "callout_zeit": (p.get("callout") or {}).get("calloutTimestamp"),
            "roh": p,
        }
    return {"positions": aus,
            "summary": d.get("summary") or {},
            "stand": d.get("asOfTimestamp")}


def trade_batch(mint, wallets):
    """Die letzten Trades mehrerer Wallets auf EINEM Token (Transaktionsebene).

    Rueckgabe: {wallet: [trade, ...]}, neueste zuerst. Ein Trade traegt
    type (buy|sell), timestamp (ISO-UTC), priceUSD und amountUSD - der
    Zeitstempel ist der des Vorbilds, nicht der Abfragezeit.
    Ein unbekannter Token oder ein Fehler ist ein Lesefehler, kein leeres
    Ergebnis: das Buch entscheidet dann selbst (Kandidat bleibt unbeurteilt).
    """
    wallets = [w for w in wallets if w]
    if not wallets:
        return {}
    d = ruf("%s/v1/coins/%s/trades/batch" % (HOST_SWAP,
                                             urllib.parse.quote(mint)),
            methode="POST", daten={"userAddresses": wallets, "program": "pump"})
    aus = {}
    for w, trades in (d or {}).items():
        liste = []
        for t in trades or []:
            liste.append({
                "tx": t.get("tx"),
                "typ": t.get("type"),
                "zeit_ms": _iso_ms(t.get("timestamp")),
                "preis": _zahl(t.get("priceUSD") or t.get("priceUsd")),
                "betrag_usd": _zahl(t.get("amountUSD")),
                "bonding_curve": bool(t.get("isBondingCurve")),
            })
        aus[w] = liste
    return aus


def letzter_kauf(mint, wallets):
    """Der letzte KAUF je Wallet auf diesem Token - oder None.

    Fuer das Alter des Signals: ist der letzte Kauf des Vorbilds aelter als
    max_alter_signal_sekunden, ist die Position keine frische Entscheidung,
    sondern ein gehaltener Altbestand (den nachzukaufen Zuchtauswahl nach
    dem Ergebnis waere).
    """
    aus = {}
    for w, trades in trade_batch(mint, wallets).items():
        kauf = next((t for t in trades if (t.get("typ") or "") == "buy"), None)
        aus[w] = kauf
    return aus


def coin(mint):
    """Coin-Details eines Tokens (gebannt, nsfw, Marktkapitalisierung)."""
    d = ruf("%s/coins/%s" % (HOST_V3, urllib.parse.quote(mint)))
    return d or {}


def risiko(mint):
    """Betrugsmerkmale eines Tokens vor dem Kauf.

    Die Pump.fun-API hat keinen Sicherheits-Scan wie OnchainOS - verfuegbar
    sind die Felder des Coin-Endpunkts: gebannt, nsfw, verified. Das ist die
    ehrliche Schwaechstelle der Spur und steht so in wachen.json.
    """
    c = coin(mint)
    merkmale = [k for k in ("is_banned", "nsfw") if c.get(k)]
    # 'blockiert' statt 'gesperrt': 'gesperrt' ist ein Filterwort des
    # Dauerlaufs - eine Ablehnungszeile mit diesem Wort ginge nach Telegram.
    stufe = "blockiert" if merkmale else "ok"
    return {"stufe": stufe, "merkmale": merkmale, "roh": c}


def preise(punkte):
    """Kurse zu (kette, token)-Paaren: der letzte gehandelte Preis.

    Fuer den Tagesbericht und die GUI - der Zyklus selbst nimmt Preise aus
    den Portfolio-Snapshots (tokenPriceUsd), weil dort kein zusaetzlicher
    Abruf noetig ist.
    """
    aus = {}
    for kette, mint in punkte:
        if kette not in KETTEN:
            continue
        try:
            d = ruf("%s/v2/coins/%s/trades?limit=1&program=pump"
                    % (HOST_SWAP, urllib.parse.quote(mint)))
        except Lesefehler:
            continue
        trades = d.get("trades") or []
        if not trades:
            continue
        preis = _zahl(trades[0].get("priceUsd") or trades[0].get("priceUSD"))
        if preis:
            aus[(kette, mint)] = preis
    return aus


# --- Kleinkram --------------------------------------------------------------

def _zahl(wert):
    try:
        return float(str(wert).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _iso_ms(wert):
    """ISO-8601 (mit oder ohne 'Z') -> Millisekunden seit der Epoche."""
    if not wert:
        return None
    try:
        t = datetime.fromisoformat(str(wert).replace("Z", "+00:00"))
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        return int(t.timestamp() * 1000)
    except ValueError:
        return None


def _kette_aus_chainid(chainid):
    for name, i in KETTEN.items():
        if str(chainid) == str(i):
            return name
    return None


def main():
    """Der Lagebericht: was der Feed gerade liefert. Nur lesend."""
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--limit", type=int, default=5)
    a = p.parse_args()
    try:
        rang = leaderboard(limit=a.limit)
        w = rang[0]["walletAddress"] if rang else None
        pf = portfolio(w) if w else {"positions": {}}
    except Lesefehler as e:
        print("Lese fehlgeschlagen: %s" % e)
        return 1
    print("Rangliste: %d Trader" % len(rang))
    for e in rang[:a.limit]:
        print("  %2d %-16s %10.0f USD  %5.1f %%  %4d Positionen  %s"
              % (e.get("rank"), (e.get("username") or "?")[:16],
                 _zahl(e.get("pnlUsd")) or 0, _zahl(e.get("pnlPercent")) or 0,
                 e.get("positionsCount") or 0,
                 (e.get("walletAddress") or "")[:14]))
    print("Portfolio von %s: %d Positionen" % (w, len(pf["positions"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
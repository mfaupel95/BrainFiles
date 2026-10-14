---
name: markt-datenquellen
description: Use when building or fixing a crypto/macro data fetch.
tags: [marktdaten, crypto, briefing, api]
---

# Kostenlose Marktdaten fuer Daily-Briefing-Bots

Fuer einen Bot, der taeglich ein Krypto/Briefing baut (Preise, Makro, Fear&Greed,
Funding, ETF), diese schluesselfreien Quellen nutzen. Jede Quelle separat
fehlertolerant abrufen: eine tote Quelle bricht den Lauf NICHT ab, sondern
loggt und hat Platzhalter ("k.a." bzw. None); nie einen Wert erfinden.

## Quellen je Kategorie (verifiziert 10/2026)

- **Preise + 24h/7d-Performance (BTC ETH SOL HYPE KAS XRP ADA):** CoinGecko
gratis — ein Request deckt alle ab:
  `GET https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=<comma-ids>&price_change_percentage=24h%2C7d&order=market_cap_desc`.
  Pro Coin: `current_price`, `price_change_percentage_24h_in_currency`,
  `price_change_percentage_7d_in_currency`.
- **Fear & Greed:** `GET https://api.alternative.me/fng/` → `data[0].value`.
- **BTC-Funding-Rate:** OKX Public `GET https://www.okx.com/api/v5/public/funding-rate?instId=BTC-USDT-SWAP`
  → `data[0].fundingRate` (dezimal, z. B. 0.000031).
- **Makro 10Y / VIX / DXY:** Yahoo Finance Chart-API (frei, kein Key):
  `GET https://query1.finance.yahoo.com/v8/finance/chart/%5ETNX` (10Y),
  `%5EVIX` (VIX), `DX-Y.NYB` (DXY) mit `?range=5d&interval=1d` →
  `chart.result[0].meta.regularMarketPrice`.

## Fallen (kosten Zeit, wenn unerkannt)

- **stooq.com ist anti-bot-gesperrt (10/2026):** alle CSV-Endpunkte
  (`/q/l/?s=...&f=sd2t2ohlcv&h&e=csv`) liefern 404 und die Seite verlangt eine
  JS-PoW-Challenge. Nicht als Makro-Quelle verwenden; Yahoo Chart ist der
  schluesselfreie Ersatz.
- **Yahoo Finance blockt `python-requests`-User-Agent mit HTTP 429** langfristig
  (auch nach Backoff). Statt eines benutzerdefinierten Beschreibungs-UA einen
  echten Browser-UA setzen (`Mozilla/5.0 (...) Chrome/...`), dann antwortet der
  Endpunkt. Zusaetzlich 1-2 s Abstand zwischen mehreren Yahoo-Requests und 429-
  Retry mit kurzem Backoff, weil schnelle Serien drosseln.
- **CoinGecko-Slug ≠ API-Id:** XRP heisst in der API `ripple`, nicht `xrp`.
  Eine `api_id`-Mapping je Coin (Displayname/Symbol/API-Id) in `config.json`
  halten und den Fetch darauf abbilden — sonst fehlt XRP still aus der Antwort.
- **ETF-Fluesse (BTC/ETH) haben KEINE offizielle freie API.** Farside
  (farside.co.uk) aggregiert sie taeglich, aber per Seitenscrape (fragil, kein
  stabiler Key). Als Platzhalter bauen und in Phase 2 als Scrape-Weg verdrahten.
- **10Y-2Y-Kurve ohne FRED-Key nicht ableitbar** (braucht DGS10 und DGS2 mit
  Key). Ohne Key ehrlich `us10y_2y=None` ("k.a.") statt zu raten.

## Struktur (Hausmuster Hybrid)

Deterministische Fetch-Schicht (nur stdlib + requests) in
`Agenten/<Modul>/fetch.py`, Ausgabe als datiertes JSON nach
`Werkstatt/<Modul>/daten/YYYY-MM-DD.json`. Kopf-Kommentar dokumentiert die
JSON-Struktur; `tests/` offline auf Parsing-Funktionen (kein Netz, Dummy-Daten).
Ausgabe-Pfad uber `KRYPTOBRIEF_OUT`-Env oder CLI-Argument steuerbar, damit ein
Live-Lauf nicht die Tests verschmutzt.

- **`repo_root` aus `__file__` zaehlt eine Ebene zu tief, wenn das Modul unter
  `Agenten/<Modul>/` liegt.** `dirname(dirname(fetch.py))` ergibt `Agenten/`,
  nicht die BrainFiles-Wurzel — die Ausgabe landet unter `Agenten/Werkstatt/`.
  Fuer `Agenten/<Modul>/fetch.py` sind es DREI `dirname` bis zur Wurzel; beim
  scharf stellen Ausgabe-Pfad gegen den erwarteten `Werkstatt/<Modul>/daten/`
  pruefen.

## Beispiel-Implementierung

Fertiges, getestetes Muster: `Agenten/KryptoBrief/` (`fetch.py`, `config.json`,
`tests/test_fetch.py`, `README.md`). Live-Lauf sammelt alle 5 Kategorien und
schreibt nach `Werkstatt/KryptoBrief/daten/`. Tests: `python
Agenten/KryptoBrief/tests/test_fetch.py`.

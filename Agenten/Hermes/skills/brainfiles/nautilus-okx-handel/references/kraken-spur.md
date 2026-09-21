# Kraken-Spur (nautilus_kraken) - Adapter-API und Fallen

Zwei Varianten der Nautilus-Trailing-Strategie auf Kraken, gebaut 19.09.2026:
`nautilus_kraken/` (Spot BTC/EUR, EUR, kein Hebel) und `nautilus_kraken_futures/`
(PF_XBTUSD Perpetual, USD, Hebel). Beide Papier, kein Live-Orderpfad.

## Instrument-IDs (oeffentlich ladbar, kein Key)
- Spot: `BTC/EUR.KRAKEN` (CurrencyPair, price_precision=1, size_precision=8)
- Futures-Perpetual: `PF_XBTUSD.KRAKEN` (CryptoPerpetual, price_precision=0, size_precision=4)
- Futures-Liste: PF_* = Perpetual, FF_* = Futures, FI_* = Futures Index

## Adapter-API
- `KrakenDataClientConfig`/`KrakenExecClientConfig` unter Venue `KRAKEN`
- `KrakenEnvironment.LIVE`/`DEMO` - DEMO gibt es NUR fuer Futures
- `KrakenProductType.SPOT`/`FUTURES`
- Env-Vars: `KRAKEN_SPOT_API_KEY/SECRET`, `KRAKEN_FUTURES_*`
- HTTP-Clients: `nautilus_pyo3.KrakenSpotHttpClient`/`KrakenFuturesHttpClient`
  (oeffentliche Instrumente ohne Key)

## Fallen
- **DEMO-Futures-Endpunkt antwortet nicht parsebar** ("Failed to deserialize
  futures response") - der Quote-Feed nutzt deshalb LIVE fuer beide
  Produkttypen (oeffentliche Quotes, nur lesen, kein Key). DEMO-Orders
  (KRAKEN_FUTURES_DEMO_*) sind fuer den spaeteren Live-Orderpfad.
- **Kraken-Spot hat keinen Hebel** - die OKX-Spur war auf SWAP mit max_hebel
  gebaut; auf Spot wird daraus ein reiner Spot-Kauf (1x).
- **Gebuehr**: Spot 0% via Pro-Abo bis 10k EUR/Monat (Kraken-Gebuehr-Regel).
  Futures-Gebuehr 0.05% ist eine ANNAHME, zu pruefen.
- **Waehrungsfelder**: Feldnamen dynamisch aus wachen.json `waehrung`
  (`einsatz_<waehrung>`, `wert_<waehrung>`), Vorgabe USD.
- **Kraken-Adapter kann Fills nicht lesen (nautilus_trader 1.231.0, neueste):**
  `generate_fill_reports` scheitert mit "missing field `postxid`" - der
  Rust-Adapter (nautilus_pyo3) deserialisiert die Kraken-Fill-Antwort nicht.
  Der Exec-Client verbindet und authentifiziert trotzdem (Preflight meldet
  "verbunden"), aber ein Round-Trip schliesst nicht sauber, weil die Fills
  nicht verarbeitet werden. Das blockiert Live-Order-Verifikation ueber
  Nautilus auf Kraken. Vor einem Kraken-Live-Orderpfad diesen Bug pruefen
  (Preflight laufen lassen, auf den Fehler achten); Workaround: Orderpfad
  direkt ueber die Kraken-REST-API (urllib + HMAC) verifizieren, was die
  Keys prueft, aber nicht den Nautilus-Pfad.

## Order-Test (kraken_order_test.py)

- **Default ist read-only Preflight, die Order haengt hinter `--execute`.**
  Die Strategie bekommt ein `execute`-Flag und prueft es im `on_quote_tick`
  VOR dem `submit_order` - ohne das Flag macht sie nie eine Order. Ein
  Order-Smoke-Test, der ohne explizites Flag eine Order aufgibt, ist ein
  Unfall mit echtem Geld.
- **Round-Trip statt offener Position:** market BUY (winzige Menge, ~1 EUR,
  gedeckelt) dann market SELL `reduce_only` - so bleibt keine Position offen.
- **Keys:** Max' Kraken-Spot-Keys heissen `KRAKEN_API_KEY/SECRET` in
  HKCU\Environment, der Adapter erwartet aber `KRAKEN_SPOT_API_KEY/SECRET`.
  Der Test liest die Keys direkt aus HKCU und baut die Exec-Config explizit,
  statt die Umgebung umzubenennen.
- **Preflight-Modus:** Node mit Exec-Client starten, warten bis verbunden
  (Instrument im Cache), stoppen - verifiziert Keys + Authentifizierung ohne
  Geldbewegung. Der Preflight ist der erste Schritt, `--execute` erst wenn
  er gruen ist.

## Architektur (ein Kern, zwei Launcher)
- `run_kraken_paper_node.py`: Node, parametrisiert ueber `KRAKEN_PRODUKT`
  (spot/futures) - Symbol aus wachen.json.
- `handeln.py`: Zyklus, liest `KRAKEN_WACHEN` (default wachen.json),
  `KRAKEN_SUFFIX` (default "", Futures ".futures" fuer getrennte
  Zustand/Journal-Dateien), `KRAKEN_BUS_NAME` (default handel/nautilus_kraken).
- `handeln_futures.py`: Launcher, setzt die env-Variablen und kapselt den
  Lauf selbst mit `ereignis.lauf("handel/nautilus_kraken_futures")` -
  Muster der Spiegel-Schattenbuecher (spiegel_knapp.py).
- `_main()` ist der Kern, `main()` kapselt mit ereignis.lauf. Der Launcher
  ruft `_main()`, nicht `main()` (sonst doppelte Kapselung).

## Verdrahtung (19.09.2026)
- dauerlauf.SPUREN: beide Eintraege mit `python` = nautilus/.venv (nautilus_trader
  liegt nur dort), skript handeln.py bzw. handeln_futures.py.
- lage.py: `_spur_nautilus_kraken_arm(suffix, name, waehrung)` + zwei Holer
  (papierfest, zeigt letzte Quote + Herzschlag).
- auswertung_alle.SPUREN, pruefe_ratschen.RUHT (beide ruhen, keine Ratsche),
  befehle.FAMILIE.
- Bus: test_anbindung_handel.py liest dauerlauf.SPUREN automatisch - der
  Launcher MUSS `ereignis.lauf` + `handel/<spur>` selbst tragen.
- .gitignore: wachen.json/wachen.futures.json spezifisch freigeben (NICHT
  `*.json` - das hebt die zustand-Sperre auf), zustand*/handelsjournal*
  explizit sperren NACH der Freigabe.

## Nachweis (19.09.2026)
- Spot: 180 Quotes/30s @ ~70.690 EUR, Futures: 12.254 Quotes/30s @ ~81.290 USD.
- 24/24 Tests gruen (test_trailing_stop + test_handeln), Bus-Test gruen.
- dauerlauf.SPUREN 30, beide Holer aktiv, Journal ausser Haus nach
  Q:\Handel_Journal\nautilus_kraken(_futures).

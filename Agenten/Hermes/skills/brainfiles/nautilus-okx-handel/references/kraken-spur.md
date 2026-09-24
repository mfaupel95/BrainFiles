# Kraken-Spur (nautilus_kraken) - Adapter-API und Fallen

Zwei Varianten der Nautilus-Trailing-Strategie auf Kraken, gebaut 19.09.2026:
`nautilus_kraken/` (Spot BTC/EUR, EUR, kein Hebel) und `nautilus_kraken_futures/`
(PF_XBTUSD Perpetual, USD, Hebel). Beide Papier. Der Live-Orderpfad laeuft
seit 24.09.2026 direkt ueber die Kraken-REST-API (`kraken_rest.py`), NICHT
ueber den Nautilus-Adapter (der Fills nicht lesen kann) - siehe Abschnitt
"Live-Orderpfad (REST)".

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
- **Der postxid-Fix ist in 2.0.0rc5 VERIFIZIERT (24.09.2026), aber 2.0.0rc5
  ist kein brauchbares Ziel.** Der Fix wirkt (kein "missing field postxid"
  mehr), aber 2.0.0rc5 hat einen NEUEN Parse-Bug (`unknown variant "stop
  market"` - die Kraken-API liefert einen Order-Typ, den der Parser nicht
  kennt) UND die gesamte API ist umgebaut: `TradingNode`/`TradingNodeConfig`
  weg (alles in Rust `_libnautilus`), `LoggingConfig`->`LoggerConfig`
  (common), `InstrumentProviderConfig`->`live`, `model.identifiers`->`model`.
  Ein Upgrade wuerde die laufende nautilus-Spur komplett neu schreiben.
  **Kein Nautilus-Kraken-Orderpfad ist sauber** (1.231.0: postxid;
  2.0.0rc5: stop-market + kompletter Umbau). Der robuste Weg ist der
  REST-API-Orderpfad (urllib + HMAC, wie die bestehende kraken-Spur) - er
  umgeht alle Adapter-Bugs und braucht kein WS. **Dieser Weg ist gebaut**
  (24.09.2026): `kraken_rest.py` + Live-Zweig in `handeln.py`, siehe unten.
- **Der 1.231.0-Adapter routet Orders ueber den privaten WebSocket** - ein
  Key ohne WS-Berechtigung scheitert beim Connect mit `EGeneral:Permission
  denied` (WS-Token), auch wenn die Keys gueltig sind. Der HTTP-Client
  (REST) braucht kein WS. Fuer einen Nautilus-Orderpfad muss der Key also
  zusaetzlich WS-Rechte haben (`Access WebSockets API` im Kraken-Portal).
- **So sieht der WS-Fehler im Order-Smoke-Test aus** (gemessen):
  `[ERROR] TRADER-001.ExecClient-KRAKEN: Error on '_connect'` +
  `RuntimeError(Authentication error: Failed to get WebSocket token: API error:
  EGeneral:Permission denied)`, darunter die Ergebniszeile
  `{"success": false, "entered": false, "closed": false, "failed": false}`
  und der Pfad zur EVIDENCE-JSONL. **Der Erfolg steht in `success`/`entered`,
  nicht in `failed`** — `failed: false` heisst nur "nicht abgestuerzt"; wer auf
  `failed` sieht, haelt einen Lauf fuer gut, in dem nichts passiert ist. Nach
  JEDEM Smoke-Test die Ergebniszeile UND das EVIDENCE-JSONL lesen, nicht nur
  den Exitcode.
- **Diagnose-Reihenfolge bei "Kraken-Order geht nicht":** (1) Smoke-Test
  ohne `--execute` fahren und die Ergebniszeile lesen; (2) bei WS-Fehler
  denselben Schluessel ueber REST gegenvorfuehren (`kraken/kraken.py`:
  `guthaben('ZEUR')` + `offene_orders()`) — kommt dort eine Antwort, ist der
  Schluessel gueltig und es fehlt nur die WS-Berechtigung; (3) erst dann
  Schluessel-/Rechtewechsel als Ursache in Betracht ziehen. Ein
  "Permission denied" ist keine Aussage ueber den Schluessel, sondern ueber
  EIN Recht dieses Schluessels.
- **Fill-Parser ohne Node verifizieren:** `KrakenSpotHttpClient`
  (nautilus_pyo3) direkt nutzen - `await client.request_fill_reports(
  account_id=AccountId.from_str("KRAKEN-001"))` prueft den Fill-Parser
  ohne die ganze Node-API. In 2.0.0rc5: `AccountId` aus `nautilus_trader.model`
  (nicht `model.identifiers`).

## Live-Orderpfad (REST, seit 24.09.2026)

Nautilus bleibt fuer Quotes/Strategie zustaendig; die ORDER laeuft direkt
ueber den hauseigenen `kraken/kraken.py`-REST-Client (markt_kauf,
markt_verkauf, stop_setzen, guthaben) - umgeht postxid-Bug, stop-market-Bug
und die fehlende WS-Berechtigung des Keys.

- **`kraken_rest.py` laedt `kraken/kraken.py` ueber den PFAD** (importlib
  spec_from_file_location), NICHT ueber sys.path - gleiches Muster wie
  `risikostufe`. Es stellt die Order-Funktionen bereit und liest die
  gueltigen Keys `KRAKEN_SPOT_API_KEY/SECRET`.
- **Sperrenkette `sperren_zeile(w)`** liefert die Live-Sperrgruende oder
  `None`: `handel_erlaubt=false`, `freigabe.erfuellt=false`, Freigabefenster
  zu. Der Live-Zweig in `lauf()` rechnet `live = (modus == "live" and not
  sperren_zeile(w))` - nur dann werden Buchungen als echte Orders
  (`markt_kauf`/`markt_verkauf` mit `echt=True`) ausgefuehrt, sonst Papier.
  Die Spur ist damit sicher: solange die Freigabekette zu ist, wird nie eine
  echte Order gesendet.
- **`SPUR_NAME` via `KRAKEN_SPUR_NAME`** (Spot `nautilus_kraken`, Futures
  `nautilus_kraken_futures`) - das Freigabefenster ist JE SPUR getrennt. Der
  Futures-Launcher (`handeln_futures.py`) MUSS `KRAKEN_SPUR_NAME` setzen,
  sonst nutzt er das Fenster der Spot-Spur.
- **Verifikation ohne Geld:** `kraken_rest.markt_kauf(paar, menge,
  echt=False)` ist ein Preflight (keine Order) - prueft Keys, Guthaben und
  die Order-Signatur. Erst wenn der Preflight gruen ist, ist der echte
  ~1-EUR-Round-Trip ueber die Freigabekette der naechste Schritt.
- **Live-Pfad-Tests:** `sperren_zeile` direkt importieren und mit gemocktem
  `freigabefenster.lade` pruefen (4 Faelle: handel_erlaubt=false,
  freigabe.erfuellt=false, Fenster zu, alle offen -> None). Kein Netz, keine
  echten Orders.

## Order-Test (kraken_order_test.py)

- **Default ist read-only Preflight, die Order haengt hinter `--execute`.**
  Die Strategie bekommt ein `execute`-Flag und prueft es im `on_quote_tick`
  VOR dem `submit_order` - ohne das Flag macht sie nie eine Order. Ein
  Order-Smoke-Test, der ohne explizites Flag eine Order aufgibt, ist ein
  Unfall mit echtem Geld.
- **Round-Trip statt offener Position:** market BUY (winzige Menge, ~1 EUR,
  gedeckelt) dann market SELL `reduce_only` - so bleibt keine Position offen.
- **Keys — NUR `KRAKEN_SPOT_API_KEY/SECRET` ist gueltig.** `KRAKEN_API_KEY/SECRET`
  existiert in HKCU\Environment, aber Kraken antwortet darauf `EAPI:Invalid key`
  (gemessen 24.09.2026). Ein Programm, das "Invalid key" meldet, waehrend die
  Haus-kraken.py mit demselben Konto arbeitet, liest den falschen
  Variablennamen, nicht einen falschen Schluessel. Vor jeder
  "Key kaputt"-Aussage beide Namen pruefen. Der Test liest die Keys direkt
  aus HKCU und baut die Exec-Config explizit, statt die Umgebung umzubenennen.
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

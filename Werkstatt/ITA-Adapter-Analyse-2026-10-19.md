# ITA-Adapter-Analyse 2026-10-19 — intelligent-trading-bot

**Zweck:** Prüfen, ob der ITB-Binance-Adapter auf OKX umgebaut werden kann und was das kostet.  
**Quelle:** `Werkstatt/intelligent-trading-bot/` (Fork mfaupel95/intelligent-trading-bot),  
**Tor-Konfiguration:** `Agenten/Handel/fremd_signale/wachen.json`, **Signal-Schema:** `Agenten/Handel/signal_schema.py`.

---

## 1. adapter_quellen.json — existiert nicht mehr

Die Datei `Agenten/Handel/fremd_signale/adapter_quellen.json` ist **nicht auffindbar**.  
An ihre Stelle haben sich drei Zustandsdateien ergänzt:

| Datei | Inhalt |
|---|---|
| `zustand.json` | Live-Positionen (4× BTC-USDC long, alle closed, PnL −0.37 USD) |
| `demo_zustand.json` | Leerer Demo-Zustand (1 signal verarbeitet) |
| `wachen.json` | Tor-Konfiguration: erlaubt Modi `paper`/`demo`, Quellen Liste enthält `intelligent-trading-bot` |

Der ITB-Eintrag in `wachen.json` ist rein deklarativ — er sagt nur, dass ITB als Signalquelle erlaubt ist, nicht wie der Adapter aussieht.

**Bemerkung:** Der PR-Zustand „Phase 0 fertig; in adapter_quellen.json aus" deutet darauf hin, dass die Datei früher existierte und entfernt/umbenannt wurde. Der ITB-Eintrag ist jetzt direkt in `wachen.json:quellen_erlaubt` eingetragen.

---

## 2. ITB-Repo-Struktur und Adapter-Code

### 2.1 Venue-Definition (bereits OKX vorhanden)

`common/types.py`:

```python
class Venue(Enum):
    YAHOO = "yahoo"
    BINANCE = "binance"
    MT5 = "mt5"
    OKX = "okx"
```

OKX ist also **schon als Venue definiert**. Das ist der wichtigste Hinweis: die Konzeptarbeit für OKX ist teilweise bereits erledigt.

### 2.2 Haupt-Service: `service/server.py`

- Importiert `from binance import Client` (line 5) — Binance-spezifisch.
- Bootstrapping (Zeilen 158–186): behandelt nur `Venue.BINANCE` und `Venue.MT5`. Für Binance: `init_client` aus `inputs.collector_binance`, für MT5: `init_client` aus `inputs.collector_mt5`.
- Shutdown (Zeilen 274–279): nur `close_client` für Binance und MT5.
- **OKX fehlt an beiden Stellen** — ein Server mit `venue: "okx"` würde im Bootstrapping stehen bleiben oder abstürzen.

### 2.3 Eingabe-Kollektoren: `inputs/`

| Datei | Inhalt |
|---|---|
| `collector_binance.py` | Vollständig: fetch_klines (Live), health_check, download_klines, Client-Initialisierung |
| `collector_mt5.py` | Vollständig: fetch_klines, health_check, download_klines, init_client, close_client |
| `collector_okx.py` | **Nur download_klines** — historische Kerzen von öffentlicher OKX API v5 (ohne Key). Kein fetch_klines, kein health_check, kein init_client. |
| `collector_yahoo.py` | Nur download_klines |

`inputs/__init__.py` — `get_collector_functions(venue)`:

```python
def get_collector_functions(venue: Venue):
    if venue == venue.BINANCE:
        from inputs.collector_binance import fetch_klines, health_check
        return fetch_klines, health_check
    elif venue == Venue.YAHOO:
        raise NotImplementedError(...)
    elif venue == venue.MT5:
        from inputs.collector_mt5 import fetch_klines, health_check
        return fetch_klines, health_check
    else:
        raise ValueError(f"Unknown collector type: {venue}")   # ← OKX kommt hier nicht an
```

`inputs/__init__.py` — `get_download_functions(venue)`:

```python
def get_download_functions(venue: Venue):
    ...
    elif venue == venue.OKX:
        from inputs.collector_okx import download_klines
        return download_klines          # ← das funktioniert schon
```

**Fazit Kollektor:** Der Downloader für OKX ist vollendet und getestet (`tests/test_collector_okx.py`). Der **Live-Kollektor** (`fetch_klines` + `health_check`) fehlt komplett.

### 2.4 Ausgabe-Trader: `outputs/`

| Datei | Inhalt |
|---|---|
| `trader_binance.py` | Vollständig: trader, update_account_balance, update_order_status, update_trade_status, cancel_order, new_limit_order, execute_order — alles über python-binance Client |
| `trader_mt5.py` | Vollständig: MetaTrader 5 Variante |
| **`trader_okx.py`** | **Existiert nicht** |

`outputs/__init__.py` — `get_trader_functions(venue)`:

```python
def get_trader_functions(venue: Venue) -> dict[str, callable]:
    if venue == venue.BINANCE:
        from outputs.trader_binance import ...
        return {...}
    elif venue == venue.MT5:
        from outputs.trader_mt5 import ...
        return {...}
    else:
        raise ValueError(f"Unknown trader venue: {venue!r}")   # ← OKX nicht registriert
```

**Fazit Trader:** Es gibt KEINE OKX-Trade-Infrastruktur. Der gesamte Orderlebenszyklus muss von Grund auf für OKX API v5 neu geschrieben werden.

### 2.5 Konfigurationen für OKX

Vorhanden — das zeigt, dass OKX konzeptionell vorbereitet wurde:

| Datei | Inhalt |
|---|---|
| `configs/config-okx-in-sample.json` | Vollständige Konfiguration: venue=okx, data_folder=DATA-OKX, Modell-Training, Signals, simulate_model |
| `configs/config-okx-walk-forward.json` | Walk-Forward Variante |
| `configs/_var_V1.json` … `_var_V3.json` | V1/V2/V3 Varianten |
| `DATA-OKX/`, `DATA-OKX-V1/`, `DATA-OKX-V2/`, `DATA-OKX-V3/`, `DATA-OKX-WF/` | Datenordner für verschiedene OKX-Läufe |

**Bemerkung:** Die README.md sagt weiterhin „Exchange: Binance" — die Dokumentation ist nicht auf OKX aktualisiert.

### 2.6 Tests

`tests/test_collector_okx.py` (5 Tests, alle ohne Netz, mit eingespeistem Fetch):

- `test_freq_umrechnung` — Pandas-Frequenz → OKX-Balkenlänge
- `test_inst_id_aus_ordnername` — Ordnername → Instrument-ID
- `test_df_hat_binance_spalten_und_aufsteigende_zeit` — DataFrame-Format
- `test_unbestaetigte_kerze_wird_verworfen` — Nur bestätigte Kerzen
- `test_paginierung_bis_max_rows_und_ohne_doppelte` — Pagination
- `test_paginierung_endet_bei_leerer_seite` — Ende-Bedingung

Der Test deckt **nur den Downloader** ab, nicht den fehlenden Live-Kollektor oder Trader.

---

## 3. Papiermodus

### 3.1 ITB-eigener Papiermodus: **existiert nicht explizit**

ITB hat kein separates Papier/Live-Flag wie z.B. xperp (`--papier`/`--live`). Die relevanten Mechaniken:

| Mechanik | Datei | Funktion |
|---|---|---|
| `simulate_order_execution` | `App.config["trade_model"]` | Druckt nur Order-Spec, führt keine echte Order aus (Binance-Client) |
| `no_trades_only_data_processing` | `App.config["trade_model"]` | Unterdrückt Order-Einfügung komplett, nur Datenverarbeitung |
| `trader_simulation` | `outputs/notifier_trades.py` | Simuliert Trades auf historischen Daten (Backtesting), schreibt Transaktionen in `transactions.txt`, sendet Telegram-Benachrichtigungen |

**Aussage:** ITB kann im Server-Betrieb nur „Live" laufen (mit Binance-Client), oder im Batch-Betrieb (Download → Merge → Features → Labels → Train → Predict → Signals → Output). Im Batch-Betrieb ist alles papierartig, weil keine echte Order eingeht. Es gibt keine dedizierte Papier-Ausführungsschicht.

### 3.2 Papiermodus im umgebenden System (nicht ITB)

Das Handels-Tor `Agenten/Handel/fremd_signale/wachen.json` akzeptiert nur `paper` und `demo`. Das Signal-Schema `signal_schema.py` erzwingt `mode in ("paper", "demo")` — Live wird abgelehnt. Das okx-live-Handels-System (`xperp/`, `omnitrade`) hat eigenen Papiermodus, aber das ist **nicht ITB**.

### 3.3 ITB-Signale und Signal-Schema

ITB erzeugt **keine Signale im `signal_schema.py`-Format**. ITB:

1. Berechnet Features und Labels
2. Trainiert ML-Modelle (SVC, LC, NN, GB, SVC)
3. Sagt Scores vorher (z.B. `high_30_svc`, `low_30_svc`)
4. Kombiniert Scores zu einem `trade_score` (combine generator)
5. Wendet Thresholds an → `buy_signal_column` / `sell_signal_column` (boolean)
6. Gibt Telegram-Nachrichten an ein Kanal (nicht an das Handels-Tor)

Es gibt **keine Schnittstelle**, die ein Dict mit `instrument`, `venue`, `direction`, `size_pct`, `source`, `ts_utc`, `expiry_s`, `mode` ausgibt. ITB-Signale sind nicht konform mit dem Fremd-Signal-Vertrag.

**Folge:** Selbst wenn ITB auf OKX umgebaut wird, würden seine Signale nicht über das fremd_signale-Tor fließen — es sei denn, eine zusätzliche Adapter-Schicht übersetzt ITB-interne Signale ins `signal_schema.py`-Format.

---

## 4. Bewertung OKX-Umbau

### 4.1 Was schon existiert (Grundlage)

- ✅ Venue.OKX in `common/types.py`
- ✅ `inputs/collector_okx.py` — Downloader (historische Kerzen, öffentliche API, keine Authentifizierung), inkl. Tests
- ✅ `inputs/__init__.py:get_download_functions` — OKX-Downloader registriert
- ✅ OKX-Konfigurationsdateien (`config-okx-*.json`, `_var_V*.json`)
- ✅ `DATA-OKX-*` Ordner mit Daten
- ✅ Test-Suite für den OKX-Downloader

### 4.2 Was fehlt (Umbau-Arbeitspaket)

**Paket A — Live-Kollektor für OKX** (`inputs/collector_okx.py` erweitern):

1. `fetch_klines(config, last_kline_dt)` — holt die neuesten Kerzen seit `last_kline_dt` von OKX API v5 `/api/v5/market/history-candles`. Muss im Binance-Spaltenformat zurückgeben (wie der Downloader).
2. `health_check()` — prüft, ob OKX-Datenprovider erreichbar ist (einfacher Ping auf `/api/v5/market/tickers`).

**Paket B — Trader für OKX** (`outputs/trader_okx.py` neu schreiben, von `trader_binance.py` als Muster nehmen):

1. `trader_okx(df, model, config, model_store)` — Haupt-Trade-Loop (Signal auswerten, Order-Entscheidung, Status-Handling)
2. `update_account_balance()` — Kontostand von OKX API v5 `/api/v5/account/balance`
3. `update_order_status()` — Orderstatus von `/api/v5/trade/order/query` oder `/api/v5/account/order-list`
4. `update_trade_status()` — Offene Orders und Positionen
5. `cancel_order()` — Order abbrechen (`/api/v5/account/order-cancel`)
6. `new_limit_order(side)` — Limit-Order einfügen (`/api/v5/trade/order')
7. `execute_order(order_spec)` — Validierung und Submit

**Paket C — Registrierung** (knüpft vorhandene Teile an):

1. `inputs/__init__.py:get_collector_functions` — OKX-Zweig hinzufügen (Fetch + Health)
2. `outputs/__init__.py:get_trader_functions` — OKX-Zweig hinzufügen (Trader-Funktionen)
3. `service/server.py:start_server` — Bootstrapping für OKX: `init_client` und `close_client` (OKX hat andere Auth als Binance — API-Schlüssel + Passphrase + Signatur mit HMac SHA256)
4. Shutdown-Zweig in `server.py` für OKX

**Paket D — Daten-Ordner-Übergabe** (optional, je nach Lauf):

- DATA-OKX-Vorlauf-Daten sind vorhanden. Eine Konfiguration muss auf den richtigen Ordner zeigen.

### 4.3 Risiken und Hürden

| Risiko | Schweregrad | Bemerkung |
|---|---|---|
| OKX Auth ist anders als Binance | Mittel | OKX API v5 benötigt API-Schlüssel, Passphrase, signierte Anfragen (HMac SHA256). Der python-binance-Client funktioniert nicht. Entweder ccxt oder eigene OKX-Client-Implementierung. |
| OKX Instrument-Namenskonvention | Niedrig | ITB verwendet bereits `inst_id()` in `collector_okx.py` (BTCUSDT → BTC-USDT). Das Muster ist vorhanden. |
| Slippage / Preisunterschiede | Niedrig | OKX und Binance haben ähnliche Kurse, aber nicht identisch. Der Trade-Algorithmus muss evtl. Preisanpassungen tolerieren. |
| Signal-Schema-Konformität | Mittel | ITB-Signale sind nicht im `signal_schema.py`-Format. Wenn ITB als Fremd-Quelle ins Handels-Tor einfließen soll, ist eine Signal-Übersetzungsschicht nötig. |
| Dokumentation | Niedrig | README sagt „Exchange: Binance". Würde OKX-Umbau aktualisiert werden müssen. |

### 4.4 Größenordnung

- **Kollektor (Live):** ~150–250 Zeilen Python (ähnlich wie `collector_binance.py` und `collector_mt5.py`)
- **Trader (OKX):** ~300–450 Zeilen (ähnlich wie `trader_binance.py`)
- **Registrierung + Bootstrapping:** ~30–50 Zeilen Änderungen in 3 Dateien
- **Tests für Trader:** ~100–150 Zeilen (mock-basiert, ähnlich wie `test_collector_okx.py`)
- **Gesamt:** ca. 600–900 Zeilen Python, eher konservativ geschätzt

**Bewertung:** Der Umbau ist **machbar mit mittlerem Aufwand**. Die Konzeptarbeit (Venue-Enum, Downloader, Konfigurationen) ist bereits geleistet. Das Fehlende ist Implementierung von Live-Datenabruf und Trade-Ausführung für OKX API v5, plus die Änderungen an 3 Registrierungsstellen. Der größte Singleton ist die OKX-Auth-Integration.

### 4.5 Warum es bisher nicht passiert ist

Die `collector_okx.py`-Datei hat den expliziten Kommentar:

> „Ein Live-Collector (fetch_klines) gibt es hier bewusst nicht - dieser Zweig ist der lesende Teil, Handel läuft nicht über dieses Modul."

Das bedeutet: OKX wurde bisher **nur als Datenquelle für das Modell-Training/-Prediction** genutzt (Batch-Modus), nicht für Live-Handel. Der Handel lief über Binance (oder nicht). Der Übergang von OKX-Data-Only zu OKX-Data+Trade ist genau das, was hier fehlt.

---

## 5. Fazit

**Adapter-Status:** Der ITB-Binance-Adapter ist ein integraler Bestandteil von `service/server.py` und den Modulen `inputs/collector_binance.py` + `outputs/trader_binance.py`. Er ist nicht als separate, isolierte Datei auslagern — er ist in die Server-Logik und die venue-spezifischen Kollektor-/Trader-Module eingemauert.

**OKX-Schrittplan (vorschlag):**

1. `inputs/collector_okx.py` um `fetch_klines` + `health_check` erweitern (Paket A)
2. `outputs/trader_okx.py` neu schreiben, von `trader_binance.py` abgeleitet, OKX API v5 Endpunkte (Paket B)
3. `inputs/__init__.py`, `outputs/__init__.py`, `service/server.py` anpassen (Paket C)
4. Tests für Kollektor und Trader ergänzen
5. Konfigurationstest: `python -m service.server -c configs/config-okx-in-sample.json` in Paper-Modus (simulate_order_execution=true) laufen lassen
6. README aktualisieren

**Signal-Konformität:** ITB-Signale sind nicht direkt im `signal_schema.py`-Format. Falls ITB-Signale ins fremd_signale-Tor fließen sollen, bräuchte es eine zusätzliche Adapter-Schicht, die ITB-interne Scores/Thresholds in das Signal-Dict-Format übersetzt. Das ist unabhängig vom OKX-Umbau zu lösen.

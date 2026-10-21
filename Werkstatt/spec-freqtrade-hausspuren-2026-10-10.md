# Spec: Haus-Spuren als Freqtrade-Bots + Leitstand-Reiter (10.10.2026)

**Auftrag Max (10.10.2026):** Freqtrade untersuchen, aus den Spuren bzw. dem
Handelswissen mehr Trading-Agenten entwickeln und in `leitstand.py` einbinden.
Ziel laut Max: **möglichst viele Dry-Run-Bots** (Breite, Papierrunden sammeln).
Reihenfolge laut Max: **erst Ansatz A, dann B.**

## Ausgangslage (gemessen 10.10.2026)

- 3 Bots laufen als Container (`freqtrade-trading-agent` 8081, `-topmovers`
  8082, `-marktlage-regime` 8083), dry_run, je ~600 MB RAM. Alle drei sind im
  2-Jahres-Backtest negativ; Ursache laut `freqtrade/bots.json` `_offen`:
  Gebühr × Rundenzahl, Signal-Ausstieg als Frequenzquelle, Futures halbiert
  die Kosten.
- Leitstand: 7 Reiter; Freqtrade erscheint nur in der Handelszentrale
  (Reiter „Überwachen“) über `freqtrade_bridge.py` (nur GET).
- Haus-Spuren mit belegter Kante (`MaxHirn/Wissen/Prognose-Spuren-Backtest.md`,
  7000 h, 0,10 %/Seite): `macd_mtf` long +2,28 %/Runde, `squeeze` long
  +1,57 %/Runde. `wavetrend`, `supertrend` negativ. Die 11 `klassik_*`-Spuren
  haben keinen Backtest-Motor (`backtest_urteile.json` → `ohne_motor`).

## Umfang

**Portiert (nur OHLCV, 17 Bots):** `klassik_sma`, `klassik_ema`,
`klassik_macd`, `klassik_bollinger`, `klassik_donchian`, `klassik_rsi`,
`klassik_rsi2`, `klassik_donchian_trend`, `klassik_sr_breaks`,
`klassik_pmax`, `klassik_supertrend`, `macd_mtf`, `squeeze`, `wavetrend`,
`supertrend`, `trendwende_btc`, `orb`.

**Nicht portiert, mit Grund in `bots.json` → `nicht_portierbar`:**
`prophet_signal` (Modell + Abhängigkeit), `iv_wand`, `iv_waelle`, `liq_wand`,
`moondev_whale/liquidation/sentiment` (Fremddaten), `gitter` (Gitterleiter
passt nicht ins Ein-/Ausstiegsmodell), `mosaic`, `xperp`, `kraken`, `omniquant`
(eigene Live-Pfade, keine Signalregel zum Übertragen).

Ausgeschlossen: Live-Handel. Alle Bots `dry_run: true`. Die Bridge bleibt
rein lesend (kein `forceenter`/`forceexit`).

## Phase 1 — Ansatz A: Adapter `HausSpur`

### Komponenten

1. **`freqtrade/user_data/strategies/HausSpur.py`** — eine Strategie für alle
   Spuren. Liest aus der Config `hausspur: {"name": "<spur>"}`.
   - Regelquelle: `klassik_*` aus `klassik_regeln.REGELN`; `macd_mtf`,
     `squeeze`, `wavetrend`, `supertrend`, `trendwende_btc`, `orb` über ein
     kleines Register `hausspur_regeln.py` (neben `klassik_regeln.py`), das
     dieselbe Signatur `einstieg(k, w) -> "long"|"short"|None`,
     `ausstieg(k, seite, w) -> grund|None` aus den vorhandenen Spur-Modulen
     liefert. **Importiert, nicht nachgebaut.** Spuren, deren Signal nicht in
     dieser Form vorliegt, bekommen in `hausspur_regeln.py` einen dünnen
     Wrapper um die vorhandene Funktion — keine neue Regel.
   - Je Kerze: Liste `[ts, o, h, l, c, v]` aus dem DataFrame, gleitendes
     Fenster `fenster` (Vorgabe = `mindest_kerzen` der Spur, sonst 300),
     `einstieg()` auf `k[:i+1]`. Live/Dry-Run rechnet nur die letzten
     `nachrechnen` Kerzen (Vorgabe 3), Backtest alle.
   - `w` = die `wachen.json` der Spur (Zeitrahmen, Stop, Ziel-R, `nur_long`).
     Stop = `stop_prozent` der Spur (fehlt er: 6,0 % wie die Moon-Dev-Bots),
     `minimal_roi = {"0": ziel_r_vielfaches × stop}`.
   - `trading_mode: futures`, `margin_mode: isolated`, Hebel 1,
     `can_short = True` (kurze Seite nur, wenn die Spur sie hat und
     `nur_long` nicht gesetzt ist).
   - Schutzschicht wie `moondev_basis.protections()`.
2. **Einbindung des Haus-Codes in den Container:** `bots.py` mountet
   `Agenten/Handel` read-only nach `/haus`; `HausSpur.py` hängt `/haus` an
   `sys.path`. Fehlt der Mount, verweigert die Strategie beim Laden mit
   lesbarem Grund (kein stilles Null-Signal).
3. **`freqtrade/bots.json`** — 17 Einträge, `strategie: "HausSpur"`,
   `hausspur: "<name>"`, Ports 8084–8100, Paare aus der `wachen.json` der Spur
   in Binance-Futures-Schreibweise (`BTC/USDT:USDT`), Zeitrahmen aus
   `kerzen_zeitrahmen` (4H → `4h`). `_stand` auf 2026-10-10.
4. **`freqtrade/bots.py`** — `config_fuer()` übernimmt `hausspur`,
   `trading_mode`, `margin_mode`; `cmd_start` setzt den `/haus`-Mount und
   `--memory 700m`; neues Kommando `urteile` schreibt die letzte
   Backtest-Zeile je Bot nach `freqtrade/urteile.json`
   (`{name: {stand, runden, netto_prozent, max_ruecklauf, zeitraum}}`).
5. **Leitstand-Reiter „FreqTrade“** — `leitstand_freqtrade.py`, in `REITER`
   als achter Eintrag, Kürzel Strg+8, in `TAKT_SICHTBAR`.
   - Oben: Tabelle aller Bots aus `freqtrade_bridge.uebersicht()`, Spalten
     Bot · Spur · Zustand (läuft/taub mit Grund) · offen · Runden ·
     Netto % · Backtest (aus `urteile.json`, mit Datum; fehlt: „—“).
   - Unten: Detail des gewählten Bots — offene Trades und letzte 20
     geschlossene, mit den Formatierern der Handelszentrale
     (`freqtrade_offen_zeile`, `freqtrade_zu_zeilen`); keine zweite
     Formatierung.
   - Abfrage im Hintergrund-Thread, Ergebnis über `after()` in die Oberfläche
     (der Reiter darf den Rahmen nie blockieren; 20 Bots × 4 s Zeitgrenze).
   - `titel_zusatz()`: „ (n/m)“ = laufende/gesamt; `status()`: taube Bots.
   - Schreibt nichts, startet nichts.

### Datenfluss

`wachen.json` der Spur → `bots.py configs` → `config.<bot>.json` → Container
(HausSpur importiert Regel aus `/haus`) → API 127.0.0.1:<port> →
`freqtrade_bridge` → Reiter. Backtest: `bots.py backtest` → `urteile.json` →
Reiter.

### Fehlerfälle

- Regel wirft → Kerze ohne Signal, Warnung im Bot-Log (wie `klassik_regeln`).
- Spur unbekannt / Mount fehlt → Strategie lädt nicht, Container-Log nennt den
  Grund; der Reiter zeigt den Bot als „taub“.
- Bot offline → Bridge liefert `erreichbar: False`, Reiter zeigt Grund.

### Tests (Phase 1)

- `freqtrade/tests/test_hausspur.py`: auf einer festen Kerzenreihe liefert
  `HausSpur` je Kerze dieselben Signale wie `REGELN[name][0](k[:i+1], w)`
  (für jede der 17 Spuren); unbekannte Spur → Fehler mit Namen.
- `freqtrade/tests/test_bots.py` erweitert: Config enthält `hausspur`,
  futures, Mount und Speichergrenze; alle Ports eindeutig.
- `tests/test_leitstand_freqtrade.py`: Tabellenzeilen aus einer
  Bridge-Attrappe; Offline-Bot; fehlende `urteile.json`; Reiter-Schnittstelle
  (`refresh`, `titel_zusatz`, `status`).
- Bestehende Leitstand- und Bridge-Tests bleiben grün.

### Inbetriebnahme

`bots.py configs` → `bots.py daten` → `bots.py backtest` (2 Jahre) →
`bots.py urteile` → **Max gibt den Start frei** → `bots.py start` (17 ×
~600 MB ≈ 10 GB RAM). Ein Bot mit Backtest-Verlust wird trotzdem gestartet
(Ziel Breite), der Reiter zeigt das Urteil daneben.

## Phase 2 — Ansatz B: vektorisierte Strategien

Je Spur eine pandas-Strategie `HausSpur<Name>` (z. B. `HausSpurKlassikEma`),
Indikatoren vektorisiert über das ganze DataFrame. Zweck: schneller Backtest
und Hyperopt. **Der Adapter bleibt die Referenz:** jede B-Strategie hat einen
Gleichheitstest gegen `HausSpur` auf derselben Kerzenreihe (Signale je Kerze
identisch; Abweichung = Test rot). Erst bei grünem Test darf `bots.json` einen
Bot von `HausSpur` auf die B-Fassung umstellen. Reihenfolge: zuerst
`macd_mtf` und `squeeze` (belegte Kante), dann `klassik_*`.

## Arbeitsweise

- Zweig `claude/freqtrade-hausspuren` von `master`, Arbeitsbaum
  `.worktrees/freqtrade-hausspuren`, `BRAINFILES_BEREICH=handel`.
- Containerstart nur nach Max' Freigabe. Kein Push ohne Anweisung.
- Wissen nachziehen: `MaxHirn/Wissen/Handelsbots.md` (Abschnitt Freqtrade)
  nach Phase 1.

## Erledigt, wenn

- Phase 1: 17 Bots in `bots.json`, Tests grün, `urteile.json` mit 17 Zeilen,
  Leitstand zeigt Reiter „FreqTrade“ mit allen 20 Bots; nach Freigabe laufen
  die Container und antworten auf `/api/v1/ping`.
- Phase 2: B-Fassung für `macd_mtf` und `squeeze` mit grünem
  Gleichheitstest; übrige Spuren folgen einzeln.

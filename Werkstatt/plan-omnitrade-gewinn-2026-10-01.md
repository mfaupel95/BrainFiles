---
id: 20261001-plan-omnitrade-gewinn
title: 'omnitrade — von 0 Runden zu echtem Gewinn (Plan)'
tags: [handel, plan, omnitrade]
created: 2026-10-01
updated: 2026-10-01
status: plan
summary: 'Stand des omnitrade-Konstrukts, die drei Engpaesse (Drawdown/Groesse, Gebuehr, Stichprobe) und der Weg zu einem belegten, live fahrbaren Betrieb.'
---

# omnitrade — von 0 Runden zu echtem Gewinn

> Plan, nicht Ausfuehrung. Alle Zahlen sind aus echten Laeufen vom 30.09./01.10.2026
> und mit Pfad belegt. Nichts hiervon ist gebaut.

**Ziel (Max, 01.10.2026):** mit dem omnitrade-Konstrukt moeglichst schnell
moeglichst gewinnbringend handeln.

**Der Satz, der alles entscheidet:** „schnell" und „gewinnbringend" ziehen in
diesem Konstrukt in **entgegengesetzte** Richtungen. Schnelle Takte bringen die
Runden, kosten aber 1,2 % je Runde und liefern 28 % Trefferquote; langsame Takte
liefern 2-9 Runden in 60 Tagen — zu wenig, um irgendetwas zu beweisen. Der Weg
fuehrt deshalb nicht ueber „mehr Signale", sondern ueber **erst messen, dann
genau eine Strategie live**.

---

## 1. Was das Konstrukt heute ist (belegt)

| Teil | Ort | Zustand |
|---|---|---|
| Rust-Workspace | `Werkstatt/omnitrade` | 7 Crates, CLI `omnitrade-cli` (backtest/validate/live/kill), Build gruen, 277 Tests (13.09.2026). Privater Fork `mfaupel95/omnitrade`, upstream `jackby03/omnitrade` (AGPL). |
| Strategien | `Werkstatt/omnitrade/strategien/*.omni` | 41 `.omni`-Skripte, DSL mit adx/ema/macd/rsi/bb/donchian/atr/stoch/trailing_stop/take_profit. Zwoelf davon erst am 30.09. aus Pine-Vorlagen gebaut. |
| Live-Laeufe | `Werkstatt/omnitrade/status/*.json` | Vier Laeufe auf **OKX-Demo (testnet)**, 1h, BTCUSDC/ETHUSDC, `adx_macd` + `rsi30_stop5`. **Alle mit 0 Orders.** Lebendig ist einer: PID 51896 (`live_rsi30_stop5_BTCUSDC`, Start 01.10. 00:37). |
| Haus-Spur | `Agenten/Handel/omnitrade` | Papier, `handel_erlaubt=false`, `freigabe.erfuellt=false`. Spiegelt `net_quantity` ins Haus-Buch, Live-Zweig waere Kraken/USDC (`mindest_guthaben 60`, Konto hat ~25 USDC). Dauerlauf: 01.10. 02:47 „omnitrade (papier) ok", Q: byte-gleich. 31 Tests gruen. |
| Messwerkzeug | `Agenten/Handel/omnitrade/intervalle_messen.py` | Faehrt die `.omni`-Skripte ueber 5m/15m/1h/4h × mehrere Gebuehrensatze durch den **echten Rust-Backtest** (`omnitrade-cli backtest`). Rohzahlen in `cache/intervalle-*.json`. |

**Wichtige Trennung:** Der Rust-Lauf rechnet und entscheidet auf **OKX-Demo**; er
kann dort nicht echt handeln. Der einzige echte Orderweg des Konstrukts ist der
Live-Zweig der Haus-Spur (Kraken-Spot, USDC). Es ist also ein
**Entscheider-Ausfuehrer-Paar mit Verzoegerung** (1h-Takt + Statusdatei-Polling).

---

## 2. Der gemessene Stand (30.09.2026, 22:14)

Echter Rust-Backtest, BTC-USDT, **60 Tage**, 10.000 USD Einsatz, **volle
Positionsgroesse (0,1 BTC ≈ 78 % des Kontos)**, ohne Risikosteuerung.
Rohzahlen: `Agenten/Handel/omnitrade/cache/intervalle-20260930-221405.json`.

| Takt | Strategie | Gebuehr/Seite | PnL | Runden | Treffer | Drawdown |
|---|---|---|---|---|---|---|
| 15m | adx_macd | 0,05 % | +838 (+8,4 %) | 43 | 27,9 % | **78,2 %** |
| 15m | adx_macd | 0,60 % | — | — | — | Order scheitert (`InsufficientBalance`) |
| 1h | adx_macd | 0,05 % | +1.398 (+14,0 %) | 9 | 33,3 % | 75,2 % |
| 1h | adx_macd | **0,60 %** | **+635 (+6,4 %)** | 9 | 33,3 % | 79,7 % |
| 1h | adx_macd_trail | 0,60 % | **−484 (−4,8 %)** | 16 | 37,5 % | 88,9 % |
| 1h | rsi_long_only_trail | 0,60 % | **−670 (−6,7 %)** | 20 | 45,0 % | 90,6 % |
| 4h | adx_macd | 0,05 % | +1.630 (+16,3 %) | **2** | 100 % | 72,1 % |
| 4h | adx_macd | 0,60 % | +1.461 (+14,6 %) | **2** | 100 % | 73,0 % |
| 4h | rsi_long_only_trail | 0,60 % | +246 (+2,5 %) | 11 | 63,6 % | 83,0 % |

Die erste Messung derselben Nacht (22:10) ist **unbrauchbar**: `adx_macd` brach
mit `UndefinedFunction { name: "adx" }` ab, bei 0,6 % Gebuehr lief jede zweite
Zeile in `InsufficientBalance`, und die rsi-Zeilen waren durchweg negativ
(−1.314 bis −79). Sie zeigt nur, wie leicht man hier eine falsche Zahl glaubt.

### Die drei Engpaesse

1. **Der Drawdown ist das K.-o., nicht der PnL.** 72-98 % — die Backtests
   setzen ~78 % des Kontos in **eine** Position. Kein Stop, kein
   Groessenfaktor, keine Risikogrenze. Jede Zeile dieser Tabelle waere live ein
   Kontotod, unabhaengig vom Vorzeichen.
2. **Die Gebuehr entscheidet ueber den Weg, nicht die Strategie.** Auf
   Kraken-Spot (0,6 %/Seite = **1,2 % je Runde**, an zwei echten Fuellungen
   gemessen) kippen 4 von 6 geprueften Kombinationen ins Minus. Dieselbe
   Strategie auf 1h verliert 7,6 Punkte PnL allein an Gebuehren (14,0 % → 6,4 %).
3. **Die Stichprobe ist zu klein fuer „schnell".** 1h: 9 Runden in 60 Tagen
   (≈1 je 6,7 Tage), 4h: 2 Runden. Bei 4h sind 100 % Trefferquote **keine
   Trefferquote**, sondern zwei Muenzwuerfe. Kein Walk-Forward, kein
   Out-of-Sample — die Repo-Tests (EMA50/200 1d, 23.09.) sind in-sample/oos
   getrennt, aber auf einem anderen Takt und Instrument.

**Nebenbefund, der sofort zaehlt:** Von vier Live-Laeufen lebt **einer**
(PID 51896). Die Wache `omnitrade-lauf-wache.py` prueft nur `status/live.json` —
und das ist die Datei des **toten** `adx_macd`-Laufs von 30.09. 13:37. Der
einzige lebende Lauf ist unbeobachtet (das ist T-222, hier bestaetigt).

---

## 3. Der Weg (Phasen, in dieser Reihenfolge)

### Phase 0 — Wache richtig stellen (10 min, sofort)
Ohne das laeuft alles Weitere blind.

1. `Agenten/Hermes/scripts/omnitrade-lauf-wache.py` auf **alle** `status/*.json`
   erweitern: je Datei ein Urteil ueber `omnitrade_lauf.beurteile`, Meldung mit
   Dateiname, Symbol und Script; Schluessel der Merkdatei = Dateiname + Urteil
   (ohne PID, sonst meldet sie bei jedem Neustart neu).
2. **Verifikation:** Wache von Hand laufen lassen; sie muss den lebenden
   `live_rsi30_stop5_BTCUSDC` als gesund und `live.json` als „beendet (PID tot)"
   melden. Test in `test_omnitrade_lauf_wache.py` um den Mehrdatei-Fall
   erweitern (Attrappen-Statusordner, kein Netz).

### Phase 1 — Messung handelbar machen (Kern, ~2 h)
`intervalle_messen.py` rechnet richtig, stellt aber die falsche Frage. Drei
Aenderungen, alle im Werkzeug, kein Eingriff in die Strategien:

1. **Positionsgroesse als Parameter** (`--einsatz`, `--risiko-pro-trade`): statt
   „0,1 BTC" eine Groesse, die dem Haus-Massstab entspricht
   (Risiko je Position / Stop-Abstand). Ohne das ist jede Zahl unbrauchbar.
2. **Gebuehrensatz des ECHTEN Weges als Vorgabe:** 0,006 (Kraken-Spot-Taker,
   gemessen 22.09.) — und die 0,0005 nur als Vergleichsspalte, nicht als
   Hauptzahl. Zusaetzlich den Ausstieg nicht nur als Marke, sondern wie live.
3. **In-Sample/Out-of-Sample trennen** (`--split 0.7`): dieselbe Strategie
   zuerst auf den ersten 42 Tagen waehlen, dann auf den letzten 18 Tagen
   nachrechnen. Eine Strategie, die nur in-sample gut ist, faellt damit heraus.
4. **Instrumentenbreite:** BTC, ETH, SOL (Daten liegen unter `daten/`).
5. **Verifikation:** Die Tabelle aus §2 muss reproduzierbar sein (gleiche
   Zahlen bei gleichem Aufruf); ein Lauf mit `--split 0.7` nennt beide Haelften
   getrennt; `InsufficientBalance` darf bei risiko-normierter Groesse nicht mehr
   auftreten.

### Phase 2 — Entscheiden (30 min, mit Max)
Aus der neuen Tabelle **eine** Zeile waehlen, nach **Erwartungswert nach
Gebuehr**, nicht nach PnL — und nach dem Kriterium: mindestens 20 Runden in
beiden Haelften. Voraussichtliches Ergebnis der Rechnung: `adx_macd` auf **1h**
ist der einzige Kandidat mit Runden **und** positivem Vorzeichen nach Gebuehr;
15m scheitert an 27,9 % Trefferquote mal 1,2 % Gebuehr, 4h an der Stichprobe.

Offene Entscheidung fuer Max (hier, nicht spaeter): **welcher Orderweg?**
Kraken-Spot kostet 1,2 %/Runde, OKX-XPERP 0,1 % (12x billiger) — der Haus-Code
fuer beide liegt fertig vor (`kraken/kraken.py`, `xperp/okxf.py`), und die
Frage „Kraken oder OKX" entscheidet bei 9 Runden in 60 Tagen ueber mehrere
Prozent. Kraken-USDC braucht zusaetzlich Guthaben (25 gegen Tor 60).

### Phase 3 — Live-Pfad scharf machen (1 h)
Erst **nach** Phase 1/2, mit belegten Zahlen — nicht auf Zuruf.

1. Guthaben klaeren: Kraken-USDC ueber 60 bringen (T-115/T-256) **oder** den Weg
   auf OKX umstellen (dann `boerse`, `kraken_quote`, `guthaben_waehrung` in
   `Agenten/Handel/omnitrade/wachen.json` nachziehen und die XPERP-Margin-Wahrheit
   beachten: USDC, nicht USDT).
2. Grenzen in `wachen.json` an das Messergebnis anpassen (`live_max_pro_trade_usd`,
   `stop_prozent`), nicht an ein Gefuehl.
3. Freigabekette: `handel_erlaubt=true` + `freigabe.erfuellt=true` + Fenster —
   `freigabe.erfuellt` setzt **Max**, nicht der Agent.
4. **Verifikation:** `handeln.py --vorschau` mit `MAXHIRN_ROUTINE=1` nennt
   **einen** Grund, und zwar das Fenster; die erste Live-Zeile im Journal traegt
   `modus=live` und eine echte `ord_id`.

### Phase 4 — Automatisierung (2 h)
Heute spiegelt die Spur den Rust-Lauf mit 1h-Verzoegerung. Fuer „schnell" fehlt:

1. **Kuerzerer Takt:** `--interval` kann 15m/5m (Commit `ed13a3f`), die Laeufe
   stehen aber auf 1h. Erst nach Phase 2 umstellen — 15m war nach Gebuehr
   negativ.
2. **Start/Aufsicht:** Die vier Laeufe von Hand zu starten ist der Grund, warum
   drei tot sind. Ein Waechter (Cron, 15 min, no_agent) sollte fehlende Laeufe
   melden — **nicht** selbst starten (Doppelorder-Risiko auf einem Konto).
3. **Ein Entscheider, ein Ausfuehrer:** Solange der Rust-Lauf auf Demo und die
   Haus-Spur auf Kraken rechnet, sind es zwei Buecher. Der Abgleich
   (`boersenstops.py`-Muster aus dem scanner) fehlt hier noch: Buch gegen
   Boerse, Waisen-Stops, Geister.

---

## 4. Was absichtlich NICHT angefasst wird

* **Keine Strategie umgeschrieben, kein Parameter geraten.** Die 41 `.omni`
  bleiben, wie sie sind; geaendert wird zuerst das Messwerkzeug.
* **Kein Kraken-Adapter in Rust** (Entscheidung Max, Weg B): zweiter Schluessel,
  zweiter Nonce-Zaehler. Der Haus-Orderweg fuehrt aus.
* **`freigabe.erfuellt` bleibt false**, bis Max es setzt.
* **Die vier laufenden/abgestorbenen Live-Laeufe** werden nicht neu gestartet —
  solange Phase 1 nicht durch ist, waere das Rauschen.
* **`Agenten/Handel/nautilus-rust`** (das Lehrstueck mit 5 Crates) ist **nicht**
  omnitrade — nicht verwechseln, nicht mitoptimieren.
* Fremdarbeit paralleler Sitzungen (u. a. `daten/messung/`, `strategien/` der
  Spur vom 30.09. 21:33/22:14) bleibt liegen, wird nur gelesen.

## 5. Risiken

* **Ein Backtest ueber 60 Tage ist keine Validierung.** Auch nach Phase 1 bleibt
  die Stichprobe duenn (9-43 Runden). Der erste echte Schritt muss klein sein
  (1 Platz, kleinster Betrag) — genau dafuer steht `live_max_pro_trade_usd` da.
* **Die 78-%-Positionsgroesse ist kein Backtest-Artefakt, sondern eine
  Werkzeug-Eigenschaft.** Wer Phase 1 ueberspringt und die Zahlen aus §2 als
  „Strategie ist profitabel" liest, schaltet einen Kontotod scharf.
* **Gebuehrenannahme an einer echten Fuellung pruefen** (Hausregel): Kraken 0,6 %
  ist gemessen, ein Abo-Rabatt wuerde die Rechnung sofort umdrehen.
* **Zwei Buecher** (Rust-Demo und Haus-Kraken) koennen auseinanderlaufen, wenn
  der Lauf stirbt — daher Phase 0 vor allem anderen.

## 6. Naechster Schritt (eine Aktion, unter 2 Minuten)

`Agenten/Hermes/scripts/omnitrade-lauf-wache.py` auf alle `status/*.json`
erweitern und von Hand laufen lassen — danach weiss man, welcher Lauf lebt und
welcher nicht, und alles Weitere steht auf einem belastbaren Bild.
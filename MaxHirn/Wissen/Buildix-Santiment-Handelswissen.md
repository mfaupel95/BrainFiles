---
id: 20260913-buildix-santiment
title: 'Orderflow- und Verhaltensdaten: Buildix & Santiment'
tags: [handel]
created: 2026-09-13
updated: 2026-09-16
related:
  - id: 20260902-analyse-quellen
  - id: 20260908-volumen-drift-signal
  - id: 20260913-cvd-divergenz-signal
  - id: 20260905-btc-analyse-sta
  - id: 20260901-saisonalitaet-signal
  - id: 20260907-marktlage-september-2026
summary: 'Zwei neue externe Handelswissen-Quellen, am 13.09.2026 erstmals mit Scrapling geerntet: Buildix (Hyperliquid-Orderflow, 530+ Paare, CVD/VPIN/OBI/OFI-Logik) und Santiment (1100+ On-Chain-, Social- und Dev-Metriken) — was sie bieten, welche Kennzahlen als Wissen tragfähig sind und was sich im eigenen Stack nachbauen lässt.'
---

# Orderflow- und Verhaltensdaten: Buildix & Santiment

Zwei neue Quellen für Handelswissen, am **13.09.2026** erstmals mit Scrapling
0.4.15 (StealthyFetcher + echtes Chrome) geerntet. Werkzeug und Rohdaten:
`Werkstatt/scrapling-wissen/` (venv + `holen.py`, Rohdaten in `roh/`).

> Hinweis: „sentiment.net“ heißt tatsächlich **santiment.net** (Academy unter
> `academy.santiment.net`); `/academy/` auf der Hauptdomain ist ein 404.

## Buildix — buildix.trade

**Was:** Orderflow-Analyseplattform für Hyperliquid. 530+ Paare (Screener:
591), 5 Börsen (HL, Binance, Bybit, OKX, dYdX), 24+ Metriken, 100 % On-Chain,
$85B+ Tagesvolumen (Eigenangabe). Preise: Free / Starter $9 / Trader $19 / Pro
$39 / Whale $79 / API $249 je Monat.

**Screener (frei):** Live-Daten je Paar — Preis, 24h-%, Volumen, OI, Funding —
dazu ein Signal-Label aus „CVD-4h-Divergenz“: STRONG BUY (accumulation near
lows) / STRONG SELL (distribution near highs) / NEUTRAL.

**Metriken (Deep View):**

- **CVD** (Cumulative Volume Delta): kumulierte aggressive Käufe − Verkäufe.
  Divergenz zu Preis = stärkstes Signal (Rally ohne CVD = schwach, Reversal
  wahrscheinlich).
- **OBI** (Order Book Imbalance): Bid- vs. Ask-Liquidität in den Top-10-
  Buchleveln, −100 %…+100 %. > +20 % = Stütze, < −20 % = Widerstand; Flip von
  + auf − = Stütze entfernt.
- **OFI** (Order Flow Imbalance): Veränderung der Buchvolumina zwischen
  Snapshots = „Geschwindigkeit“ des Buches; Spikes zählen mehr als Werte.
- **VPIN** (Flow Toxicity): Trades in fixen Volumen-Buckets (z. B. $500K),
  Einseitigkeit je Bucket über 50 Buckets. < 45 % normal, 45–70 % erhöht,
  > 70 % Gefahrenzone (informed flow, Squeeze-/Crash-Risiko).
- **Kyle's Lambda**: Preisimpact je $1M Volumen (Regression). Spike =
  Liquidität weg, Volatilität kommt; hoch + VPIN hoch = gefährliche Kombination.
- **Absorption Detection**: hohes Volumen-Delta bei minimaler Preisbewegung =
  verborgener Käufer/Verkäufer; eines der stärksten Reversal-Signale.
- **Markout Analysis**: wohin der Preis nach Trades geht (1s/5s/30s/5min).
  Positive Buy-Markout = „toxic flow“ (Smart Money aktiv, nicht gegenan
  handeln); negative = Retail-Noise (Mean-Reversion günstig).
- **Smart Money Delta**: CVD je Kohorte — Whales (Top 5 % Volumen), HLP
  (Protokoll-MM), Retail (Wallet-Klassifikation auf Hyperliquid). Whale/Retail-
  Divergenz = klassisches Setup.
- **Footprint / Volume Profile / TPO**: Volumen je Preislevel, POC/VAH/VAL,
  Market Profile / Auction Theory.
- **Regime Detection** (Trend/Range/Volatil), **Cross-Asset Correlation**
  (CVD-Lead-Lag, z. B. BTC-CVD führt ETH-Preis um Sekunden; Korrelationsbruch =
  Frühwarnung).
- Weitere Tools: Liquidation Heatmap (echte On-Chain-Whale-Level + OI-skalierter
  Retail-Schätzwert), Sweep Detector (Stop-Hunts mit Delta-Flip-Bestätigung),
  Liquidity Magnet, Carry Desk, Fragility Screener, Whale Liquidation Ladder,
  Hidden Liquidity Radar, Cross-Exchange (Spot-Arb), Bridge Flow (USDC-
  Nettoflüsse HL L1), Wallet Explorer, AI Query (BYOK), HYPE Burns, Custom
  Alerts (Telegram/E-Mail).

**Learn Academy:** 21 Lektionen / 7 Module (Modul 1 frei, ab Starter alle):
Foundations (Buch + Tape), Core Metrics (CVD-Divergenz, OBI, Funding, OI),
Microstructure (VPIN, Absorption, Volume Profile), Execution/Risk, Event-Driven
(Macro-Prints, Unlocks, Expiries, Weekend-Flow), AI-Assisted.

**Bewertung:** inhaltlich substanziell — die Metriken sind definiert und die
meisten aus Marktdaten nachbaubar (siehe unten). Tiefen-Daten kosten; API erst
ab Whale-Tier ($249/Monat, 50k Requests/Tag). robots.txt erlaubt `/`, sperrt
`/api/`, `/dashboard/`, `/auth/*` — die öffentlichen Seiten sind frei erntbar.

## Santiment — santiment.net

**Was:** Behavioral-Analytics-Plattform seit 2016: 1100+ Metriken, 2500+
Assets, 12 Blockchains, 3M+ geparste Social-Messages/Monat, 75M+ gelabelte
ETH- und 65M+ BTC-Adressen. Produkte: Sanbase (Plattform), SanAPI, Sansheets
(Sheets-Plugin), SanR, Santiment Queries; **AI Toolkit mit MCP-Connector und
Agent-Skills** (potenziell direkt in Hermes nutzbar).

**Metrikfamilien:**

- Financial: Preis, Marketcap, Volumen, FDV, Mean Coin Age, RSI, Gini,
  BTC-vs-S&P500-Divergenz, M2.
- Social/Sentiment: Social Volume, Social Dominance, Trending Coins/Words,
  Sentiment-Scores (seit 2014 Marktführer in Sentiment-Metriken).
- Development: GitHub-/Dev-Activity (seit 2017).
- On-Chain Network Value: MVRV, NVT, Realized Value, Mean Realized Price,
  Network Profit Loss (NRPL), Hodl Waves.
- On-Chain Activity: Daily Active Addresses, Network Growth, Active
  Deposits/Withdrawals.
- Weitere On-Chain: Age Consumed, Dormant Circulation, Supply on/off
  Exchanges, Velocity, Exchange Inflow/Outflow, Whale Transactions, Top
  Holders, Stock-to-Flow, Thermocap.
- Derivatives: Funding Rates + Open Interest aggregiert über BitMEX, Binance,
  Bitfinex, Deribit, FTX, dYdX, Huobi.
- NFT- und Adress-Metriken (Top Transfers, Historical Balance, Labels).

**Handelswissen (Academy „For Traders“):**

- **Social-Volume-Spike während einer Rally = lokaler Top-Indikator**, v. a.
  bei Mid-/Low-Caps („Peak Hype“ — der Aufmerksamkeitsschub ist meist
  Pump-bedingt, riskante Einstiegszeit).
- **Mean Dollar Invested Age (MDIA):** steigend = Hodler-Akkumulation;
  Einbrüche = plötzliche Bewegung ruhender Coins. BTC-Tops gingen historisch
  mit starken MDIA-Einbrüchen einher.
- **MVRV Long/Short Divergence:** 0-Kreuzung markierte historisch das Ende des
  Bärenzyklus (Beispiel 07.05.2019: BTC $5.830 → $8.000 binnen einer Woche).
- **DAA-Preis-Divergenz:** Preis fällt + Daily Active Addresses steigen =
  Einstieg; Gegenteil = Top (für BTC, ETH und andere geprüft).
- **Token Age Consumed:** Spikes = ruhende Coins bewegen sich = Vorwarnung für
  Volatilität — Richtung unbestimmt, erst weiter analysieren.
- **Token Velocity:** Fallstudie ETH-Mixer 2017/18 — Velocity trennt
  technische von spekulativer Aktivität (reiner Transaktionsvolumen-Rückgang
  war nicht Exodus, sondern Mixer-Ende).
- **Network Growth** (neue Adressen/Tag) = Adoptions-Proxy für Projekte.

**Bewertung:** Metriken teils exklusiv (custom-built, Methodik dokumentiert),
Daten seit 2009 — für Backtests geeignet. Datenzugang kostenpflichtig
(Sanbase/SanAPI); SAN-Token gibt 20 % Rabatt. Keine freie API ohne Konto.

## Markt-Schnappschuss (Ernte 13.09.2026, ~14:55 MESZ, Buildix-Screener)

BTC 76.704,50 $ (−0,77 %; Vol 783,91M $; OI 2,82 Mrd. $; Funding −0,0011 %);
ETH 2.476,55 $ (−2,28 %; OI 2,42 Mrd. $; Funding +0,0012 %); SOL 99,61 $
(−2,37 %); HYPE 77,53 $ (−3,41 %); ZEC 1.091,85 $ (−5,84 %); PONS −13,96 %;
ETHFI −11,86 %. Signale: ETH/FET/BNB STRONG SELL (CVD-4h-Divergenz bearish),
TRX STRONG BUY. Funding fast überall leicht positiv (+0,001 %-Bereich) = leicht
überhebelt long, keine Extremwerte.

## Umsetzbarkeit im eigenen Stack

- **CVD — gebaut am 13.09.2026.** Als 4h-Divergenz-Komponente im XPERP-/SWAP-
  Signal, aus dem OKX-Taker-Volumen je Kontrakt. Herkunft der Zahlen, Rangfolge
  und Schwellen-Kalibrierung: [[CVD-4h-Divergenz-Signal]].
- **Funding, OI, Liquidations:** aus OKX-Marktdaten (Ticker, Funding,
  Liquidation-Channel) nachbaubar, noch nicht gebaut; das Volumen-Drift-Signal
  ist ein verwandter Nachbau ([[Volumen-Drift-Signal]]).
- **VPIN:** aus dem Trade-Tape (fixe Volumen-Buckets) nachbaubar.
- **OBI/OFI:** brauchen Orderbuch-Snapshots (OKX-Websocket) inkl. Speicherung.
- **Hyperliquid-On-Chain** (Whale-Wallets, echte Liquidations-Level): nur über
  HL-API oder Buildix-Paywall.
- **Santiment-Metriken — geprüft am 13.09.2026, ohne eigene API-Integration
  nutzbar.** Der offizielle MCP-Connector (`https://api.santiment.net/mcp`,
  Streamable HTTP, Server-Kennung `sanbase-metrics` 1.0.0) spricht OAuth 2.0
  mit PKCE. Die Werkzeugliste ist **live** geprüft und nennt acht Werkzeuge:
  `metrics_and_assets_discovery_tool`, `fetch_metric_data_tool`,
  `assets_by_metric_tool`, `insight_discovery_tool`, `fetch_insights_tool`,
  `trending_stories_tool`, `combined_trends_tool`, `show_chart`. `initialize`
  und `tools/list` antworten **ohne** Anmeldung, der erste `tools/call` kommt
  als **HTTP 401** mit
  `WWW-Authenticate: Bearer resource_metadata="…/.well-known/oauth-protected-resource"` —
  Werkzeugliste offen, Daten hinter der Anmeldung. Laut Connector-Doku liefert
  `fetch_metric_data_tool` unter anderem `mvrv_usd` und
  `daily_active_addresses` (dazu `exchange_inflow_usd`/`outflow`, Supply,
  Network Growth, Social); die Metriknamen selbst sind nur über den
  angemeldeten Aufruf `metrics_and_assets_discovery_tool` nachprüfbar. Hermes
  kann OAuth-MCP: `hermes mcp add santiment --url https://api.santiment.net/mcp
  --auth oauth`, danach `hermes mcp login santiment`. Der Anmeldeschritt läuft
  im Browser gegen ein (kostenloses) Santiment-Konto — das ist Max' Teil, nicht
  automatisierbar; bezahlte Stufen schalten die volle On-Chain-Tiefe frei.
  Kein eigener SanAPI-Bau, kein Schlüssel im Klartext.

## SanAPI direkt: am 16.09.2026 gemessen und gebaut

Auf Max' Auftrag („Gh repo integrieren und für santiment api einsetzen") wurde
zuerst das **Wissen** geholt und dann die API selbst angefasst. Ergebnis: der
MCP-Weg ist **nicht** der einzige.

| | |
|---|---|
| Repo | `Werkstatt/santiment` — Fork `mfaupel95/santiment` von `api-evangelist/santiment`; **keine Software**, nur Dokumentation + das vollständige GraphQL-Schema (83 KB, 179 Query-Felder) |
| Zugang | `https://api.santiment.net/graphql`, POST, **anonym nutzbar** (Stufe `SANAPI FREE`) |
| Werkzeug | `Agenten/Handel/santiment_daten.py` (nur Standardbibliothek, nur lesend) |
| Tests | `Agenten/Handel/tests/test_santiment_daten.py` (10, ohne Netz) |

**Was ohne Schlüssel wirklich geht** (`santiment_daten.py --probe`, 5 von 5):
Schema/Introspektion, Projekt-Discovery (`allProjects`: slug, name, ticker,
marketcapUsd), `getTrendingWords`, und `getMetric` — z. B.
`daily_active_addresses/bitcoin` mit echten Tageswerten.

**Die Schranke ist pro Metrik und wird von der API selbst genannt.**
`social_volume_total` z. B. erlaubt anonym nur `from` 2025-09-16 bis `to`
**2026-08-17** — rund einen Monat Rückstand; andere Metriken reichen bis in die
Gegenwart. `erlaubtes_fenster()` liest diese Grenze aus der Fehlermeldung,
statt sie zu raten: `python santiment_daten.py --fenster social_volume_total`.

**Ein Schlüssel ist optional.** Fehlt `SANTIMENT_API_KEY` (Benutzervariable,
gelesen aus `HKCU\Environment` wie in `melder.py`), läuft alles anonym
mit kleineren Fenstern. Ein kostenloses Konto hebt sie; der Schlüssel gehört
nach [[Zugaenge]] und **nicht** in eine `.env` im Fremd-Repo.

Der MCP-Connector bleibt der zweite, breitere Weg: acht Werkzeuge, aber
`tools/call` hinter OAuth — dafür braucht es Max' Browser-Anmeldung
(`hermes mcp add santiment --url https://api.santiment.net/mcp --auth oauth`,
dann `hermes mcp login santiment`). Die Datentiefe ist dort dieselbe
Kontostufe.

Verwandt: [[Analyse-Quellen]], [[Volumen-Drift-Signal]], [[Marktlage-September-2026]], [[XRP-Analyse-STA-September-2026]], [[BTC-Analyse-STA-September-2026]]

---
id: 20260916-moon-dev-agenten
title: 'Moon-Dev-Agenten: was liegt vor, was läuft, was ist vorgemerkt'
tags: [handel, ki-agenten]
created: 2026-09-16
updated: 2026-09-16
related: [20260919-moon-dev-code-studien, 20260916-repo-bots]
summary: 'Stand der installierten Moon-Dev-Repos (46 Agenten, TradingView-MCP, Research-Material), die vier Haus-Spuren daraus und was vorgemerkt ist.'
---

# Moon-Dev-Agenten: was liegt vor, was laeuft, was ist vorgemerkt

Stand 16.09.2026. Anlass: Max hat die Moon-Dev-Repos installieren lassen und
wollte die Bots in den Handelsspuren sehen. Diese Notiz haelt fest, was daraus
geworden ist und was **vorgemerkt** ist - damit die 46 Agenten nicht als
Halbwissen im Kopf bleiben.

## Was liegt wo

| Ort | Was |
|---|---|
| `Werkstatt/moon-dev-ai-agents` | 46 Agenten, `.venv` mit allen requirements (numpy, pandas, ta-lib, torch, whisper, anthropic, openai, groq) |
| `Werkstatt/Trading-View-MCP-for-AI-by-Moon-Dev` | MCP-Server fuer TradingView, `.venv` fertig |
| `Werkstatt/Harvard-Algorithmic-Trading-with-AI` | Research-/Backtest-Material, kein `requirements.txt` |
| `Werkstatt/Moon-Dev-Code` | Sammlung (PDFs/Strategien), kein Code |
| `Agenten/Handel/moondev_*` | die vier Haus-Spuren (siehe unten) |
| Hermes-Profile | `moon-dev-agents`, `moon-dev-code`, `harvard-trading`, `tradingview-mcp` (je mit `terminal.cwd` im Repo) |

Alle vier Klone: `origin` = Fork unter `mfaupel95`, `upstream` = Original.
Quelle der Agenten ist der Nachbau `yolojewjitsu/moon-dev-ai-agents` - das
Original `moondevonyt/moon-dev-ai-agents` ist nicht mehr oeffentlich (404, auch
unter `...-for-trading`).

**Keine `.env` mit echten Schluesseln.** `.env_example` nennt nur die Namen
(`MOONDEV_API_KEY`, `SOLANA_PRIVATE_KEY`, `ANTHROPIC_KEY`, `OPENAI_KEY`,
`DEEPSEEK_KEY`, `BIRDEYE_API_KEY`, `RPC_ENDPOINT`, `HYPER_LIQUID_...`).
Zugaenge stehen ausschliesslich in `Wissen/Zugaenge.md`.
Seit dem 16.09.2026 liegt zusaetzlich eine `.env` **ohne einen einzigen
Schluessel**: nur `OLLAMA_MODEL` und `OLLAMA_BASE_URL` (lokal, siehe unten).
Sie ist gitignoriert und bleibt auf diesem Rechner.

## Was laeuft (vier Spuren, alle Papier)

| Spur | Quelle | Regel |
|---|---|---|
| `moondev_funding` | **echte Bot-Funktion** `nice_funcs_hl.get_funding_rates()`, gerufen im Bot-venv | ab +-100 % Funding im Jahr; positiv -> short |
| `moondev_listingarb` | CoinGecko `/coins/markets` + Binance `/exchangeInfo` (oeffentlich) | long, wenn gross (>= 1 Mrd USD Marktkapital, >= 30 Mio Volumen) und bei Binance nicht handelbar |
| `moondev_topmovers` | CoinGecko `/coins/markets` (oeffentlich) | long bei +8 % bis +40 % in 24 h und >= 20 Mio Volumen |
| `moondev_marktlage` | CoinGecko `/coins/markets` (oeffentlich) | BTC long bei +2 % und Marktbreite >= 60 %, short spiegelbildlich |

Alle vier: kein Sprachmodell, kein Orderpfad, `--live` verweigert, eigenes
Journal + Spiegelung nach `Q:\Handel_Journal\<spur>`. Die drei CoinGecko-Spuren
teilen sich `Handel/moondev_daten.py` (Abruf) und `Handel/moondev_buch.py`
(Buch) - eine Buchhaltung fuer alle, damit ein Fehler nur an einer Stelle
stecken kann.

## Vorgemerkt: die uebrigen Agenten

Sie sind nach dem gruppiert, was einen Weiterbau **blockiert**. Ohne die
fehlende Zutat ist keine Spur daraus zu bauen, ohne Zahlen zu erfinden.

**A - brauchen `MOONDEV_API_KEY` (Daten fehlen ohne Schluessel)**
`liquidation_agent` (Liquidations-Cluster), `whale_agent` (Wallet-Bewegungen),
`funding_agent` (Funding ueber alle Boersen), `rbi_agent`/`rbi_agent_v2`
(Research-Backtest-Iteration), `clips_agent`, `solana_agent`, `tx_agent`.
Ohne Schluessel liefern diese Agenten keine Daten - ein Nachbau der Daten
waere eine andere Spur mit anderer Aussage.

**B - brauchen einen LLM-Schluessel (das Urteil ist der Bot)**
`trading_agent`, `strategy_agent`, `sentiment_agent`, `copybot_agent`,
`chartanalysis_agent`, `focus_agent`, `research_agent`, `code_runner_agent`,
`million_agent`, `rbi_batch_backtester`, `compliance_agent`.
Der Weg ueber **lokales Ollama** ist seit dem 16.09.2026 verdrahtet (Max'
Auftrag, Abschnitt unten) - die Agenten laufen damit ohne bezahlten
Schluessel. Der Weg ueber den OmniRoute-Router bleibt ungenutzt. Die
Warnung steht weiter: eine Spur, die auf einem Modellurteil steht, haengt am
Modell - genau das vermeiden die Haus-Regeln bei den Messreihen.

**C - brauchen Solana-RPC oder ein Wallet**
`sniper_agent` (neue Token-Launches), `copybot_agent`, `phone_agent`.
Ein oeffentlicher RPC reicht zum Lesen; ein Wallet kommt nicht in Frage
(echtes Geld, kein Papier).

**D - kein Handelsbezug, gehoert nicht in den Handel**
`tiktok_agent`, `tweet_agent`, `shortvid_agent`, `clip_agent`,
`chat_agent*`, `youtube-*`, `demo_countdown`, `clean_ideas`,
`chat_question_generator`, `stream_agent`.
Diese Agenten machen Inhalte, keine Signale.

## Lokales Ollama als LLM (16.09.2026)

Auftrag von Max: „Moondev local ollama als llm". Drei Aenderungen im Repo
`Werkstatt/moon-dev-ai-agents` (Commit `9541cb8`, auf den Fork gepusht):

| Datei | Aenderung |
|---|---|
| `src/models/ollama_model.py` | Standardmodell ist jetzt `OLLAMA_MODEL` aus der Umgebung, sonst `qwen35-8k:latest` — vorher stand dort fest `llama3.2`, das hier **nie installiert war**; `OLLAMA_BASE_URL` umstellbar; Modellliste auf die drei lokalen Modelle gezogen |
| `src/models/model_factory.py` | `DEFAULT_MODELS['ollama']` aus der Umgebung; fehlt einem angefragten bezahlten Anbieter der Schluessel, laeuft der Aufruf **lokal weiter** statt `None` zu liefern (`MOONDEV_LOKAL_STATT_FEHLT=false` schaltet es ab) |
| `.env` | nur `OLLAMA_MODEL=qwen35-8k:latest` und `OLLAMA_BASE_URL=http://127.0.0.1:11434/api`, gitignoriert |

**Modellwahl:** `qwen35-8k:latest` (3,0 GB, passt in die 8 GB VRAM) ist der
Standard. `qwen36-35b-a3b:8k` (22,7 GB) laeuft nur auf CPU/RAM und ist ein
Vielfaches langsamer — als Ausnahme brauchbar, nicht als Voreinstellung.
`gemma-e4b-8k` ist schnell, war im Vertragstest aber unzuverlaessig.

**Nachweis** (`src/models/test_ollama_lokal.py`, aus dem Repo-venv): Factory
meldet `Available models: [ollama]`, Standardmodell `qwen35-8k:latest`, ein
echter Aufruf antwortet `PONG` — und `get_model("claude", ...)` liefert ohne
Schluessel das Ollama-Modell statt `None`.

**Nicht angefasst:** die `MODEL_TYPE`-Konstanten der 46 Agenten. Wer einen
Agenten fahren will, setzt sie einzeln (Muster `clips_agent`: `"ollama"` +
Modellname); der Rueckfall in der Factory deckt die uebrigen ab.

## Wenn es weitergehen soll

1. **Gruppe A mit Schluessel:** `MOONDEV_API_KEY` in `Wissen/Zugaenge.md`
   eintragen und in die `.env` des Repos legen (nicht in die Haus-Dateien).
   Danach `liquidation_agent` als Spur: Liquidations-Cluster sind ein klares,
   pruefbares Signal, und die Datenfunktion liefert DataFrames.
2. **Gruppe B mit Ollama:** eine Spur, die EINEN Agenten mit
   `AI_MODEL=ollama:<modell>` fahren laesst und seine Empfehlung als Signal
   liest. Grenze ehrlich benennen: das Buch haengt dann am Modell.
3. **Gruppe C:** `sniper_agent` mit oeffentlichem RPC als
   Beobachtungsspur (neue Paare), bevor irgendwo ein Wallet ins Spiel kommt.

Jede dieser Spuren folgt derselben Vorlage: `moondev_daten.py` (Abruf),
`moondev_buch.py` (Buch), eigene `handeln.py` mit `quelle()` und `signal()`,
`wachen.json`, README, Tests mit Modulwaechter und Eintrag in
`dauerlauf.SPUREN`.

## Die 47 Agenten im Ueberblick (Repo-README, 13.10.2026)

Vollstaendige Liste aus `Werkstatt/moon-dev-ai-agents/README.md` — die
Original-Beschreibung jedes Agenten, wie sie im Repo steht:

| Agent | Beschreibung |
|---|---|
| `trading_agent` | Analysiert Token-Daten per LLM fuer einfache Handelsentscheidungen |
| `strategy_agent` | Verwaltet und fuehrt Strategien aus dem `strategies/`-Ordner aus |
| `risk_agent` | Ueberwacht Portfolio-Risiko, erzwingt Positionslimits und PnL-Schwellen |
| `copy_agent` | Ueberwacht Copy-Bot auf potenzielle Trades |
| `whale_agent` | Ueberwacht Whale-Aktivitaeten, meldet Waleinstiege |
| `sentiment_agent` | Analysiert Twitter-Sentiment für Krypto-Tokens mit Sprachansagen |
| `listingarb_agent` | Identifiziert vielversprechende Solana-Tokens auf CoinGecko vor dem Listing bei Binance/Coinbase, parallele AI-Analyse |
| `focus_agent` | Sammelt waehrend Codingsessions zufaellige Audio-Proben fuer Fokus-Scores und Sprachwarnungen |
| `funding_agent` | Ueberwacht Funding-Raten ueber Boersen hinweg, AI-Analyse mit Sprachansagen |
| `liquidation_agent` | Verfolgt Liquidationen mit konfigurierbaren Zeitfenstern (15min/1hr/4hr), AI-Analyse |
| `chartanalysis_agent` | Analysiert Krypto-Charts per LLM fuer Kauf/Verkauf/Empfehlung |
| `fundingarb_agent` | Verfolgt Funding-Raten auf Hyperliquid fuer Arbitrage zwischen HL und Solana |
| `rbi_agent` | Nutzt DeepSeek zum Recherchieren von Handelsstrategien aus Videos/PDFs/Worten, schickt an Backtest-Agent |
| `tweet_agent` | Erstellt Tweets aus Text per DeepSeek oder anderen Modellen |
| `video_agent` | Erstellt Videos aus Text per ElevenLabs-Audio und Rohmaterial |
| `new_or_top_agent` | Betrachtet neue und Top-Coins von CoinGecko |
| `chat_agent` | Ueberwacht YouTube-Live-Chat, moderiert und beantwortet bekannte Fragen |
| `clips_agent` | Schneidet lange Videos in kurze Clips |
| `phone_agent` | KI-Agent fuer Telefonanrufe |
| `sniper_agent` | Ueberwacht neue Solana-Token-Launches, analysiert und snipet |
| `tx_agent` | Verfolgt Transaktionen der Copy-Liste, druckt sie aus |
| `solana_agent` | Kombiniert Sniper- und TX-Agent zur Auswahl interessanter Memes |
| `million_agent` | Nutzt Million-Token-Kontext von Gemini als Wissensbasis |
| `tiktok_agent` | Scrollt TikTok, macht Screenshots von Videos und Kommentaren fuer Consumer-Daten |
| `compliance_agent` | Prueft Arbitrage-Werbung auf Facebook/Tiktok auf Compliance |
| `research_agent` | Fuellt `ides.txt` fuer den RBI-Agent |

**Haus-Stand:** Vier davon laufen als Papier-Spuren (Tabelle obig), die
anderen sind nach Blockern gruppiert (Abschnitt "Vorgemerkt" obig).

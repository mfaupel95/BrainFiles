# Moon-Dev-Agenten: was liegt vor, was laeuft, was ist vorgemerkt

Stand 16.09.2026. Anlass: Max hat die Moon-Dev-Repos installieren lassen und
wollte die Bots in den Handelsspuren sehen. Diese Notiz haelt fest, was daraus
geworden ist und was **vorgemerkt** ist - damit die 46 Agenten nicht als
Halbwissen im Kopf bleiben.

## Was liegt wo

| Ort | Was |
|---|---|
| `Werkstatt/Repos/moon-dev-ai-agents` | 46 Agenten, `.venv` mit allen requirements (numpy, pandas, ta-lib, torch, whisper, anthropic, openai, groq) |
| `Werkstatt/Repos/Trading-View-MCP-for-AI-by-Moon-Dev` | MCP-Server fuer TradingView, `.venv` fertig |
| `Werkstatt/Repos/Harvard-Algorithmic-Trading-with-AI` | Research-/Backtest-Material, kein `requirements.txt` |
| `Werkstatt/Repos/Moon-Dev-Code` | Sammlung (PDFs/Strategien), kein Code |
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
Zwei Wege, beide bewusst **nicht** gegangen: (1) Ollama lokal
(`src/models/ollama_model.py` ist vorhanden; Modelle wie `qwen36-35b-a3b:8k`
liegen bereit), (2) der OmniRoute-Router. Beides macht das Buch von einem
Sprachmodell abhaengig - genau das, was die Haus-Regeln bei den Messreihen
vermeiden.

**C - brauchen Solana-RPC oder ein Wallet**
`sniper_agent` (neue Token-Launches), `copybot_agent`, `phone_agent`.
Ein oeffentlicher RPC reicht zum Lesen; ein Wallet kommt nicht in Frage
(echtes Geld, kein Papier).

**D - kein Handelsbezug, gehoert nicht in den Handel**
`tiktok_agent`, `tweet_agent`, `shortvid_agent`, `clip_agent`,
`chat_agent*`, `youtube-*`, `demo_countdown`, `clean_ideas`,
`chat_question_generator`, `stream_agent`.
Diese Agenten machen Inhalte, keine Signale.

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

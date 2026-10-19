# Handelsregeln — Moon Dev AI Agents

> Überführt aus den README-Dateien des Repos Werkstatt/moon-dev-ai-agents (moon-dev-gui verknüpft). Stand: 2026-10-13.

## 1. Projektübersicht

Moon Dev AI Agents ist ein experimentelles KI-Handelssystem mit 47 Agenten für Algorithmic Trading. Es ist **kein** handelsfertiges System — der Code dient der Forschung und erfordert eigene Strategieentwicklung und Validierung.

**Wichtige Disclaimer aus README.md:**
- Keine Gewinn-Garantien, kein Token, keine Handelsstrategie included
- Nutzer muss eigene Strategie entwickeln, testen und validieren
- KI-Agenten können profitables Trading nicht garantieren
- Trading inhärent risikoreich

## 2. Agenten-Bibliothek (47 Agenten)

### Handelsrelevante Agenten
| Agent | Funktion | Status |
|-------|----------|--------|
| `trading_agent` | Token-Daten via LLM analysieren, Handelsentscheidungen | ✅ |
| `strategy_agent` | Verwaltet/ausführt Strategien aus strategies/ | ✅ |
| `risk_agent` | Portfolio-Risiko, Positionslimits, PnL-Schwellen | ✅ |
| `copy_agent` | Copy-Bot überwacht, potentielle Trades | ✅ |
| `whale_agent` | Whale-Aktivität überwacht, Alert bei Eintritt | ✅ |
| `sentiment_agent` | Twitter-Sentiment für Krypto-Tokens | ✅ |
| `listingarb_agent` | Solana-Tokens vor Binance/Coinbase-Listing identifizieren | ✅ |
| `liquidation_agent` | Liquidation-Events mit konfigurierbaren Zeitfenstern | ✅ |
| `chartanalysis_agent` | Krypto-Charts analysieren, Buy/Sell/Nothing | ✅ |
| `funding_agent` | Funding-Raten über Börsen hinweg, extreme Werte | ✅ |
| `fundingarb_agent` | Funding-Rate Arbitrage zwischen Hyperliquid und Solana | ✅ |
| `new_or_top_agent` | Neue/Top-Coins von CoinGecko API | ✅ |
| `coingecko_agent` | CoinGecko-Marktdaten | ✅ |
| `sniper_agent` | Neue Solana-Token-Launches, Sniping | ✅ |
| `solana_agent` | Solana-Memes filtern, Sniper+TX Agent | ✅ |
| `tx_agent` | Transaktionen von Copy-Liste beobachten | ✅ |

### Research/Content-Agenten
| Agent | Funktion | Status |
|-------|----------|--------|
| `rbi_agent` | DeepSeek nutzen, Strategien aus Videos/PDFs/Worten recherchieren | ✅ |
| `research_agent` ideas.txt | Füllt ideas.txt für endlosen RBI-Agent | ✅ |
| `tweet_agent` | Tweets via DeepSeek/andere Modelle | ✅ |
| `video_agent` | Text zu Videos (ElevenLabs + raw_video) | ✅ |
| `clips_agent` | Lange Videos in kurze Clips schneiden | ✅ |
| `chat_agent` | YouTube-Live-Chat moderieren & antworten | ✅ |
| `phone_agent` | Telefonanrufe via Twilio | ✅ |
| `million_agent` | Million-Context-Window via Gemini | ✅ |
| `tiktok_agent` | TikTok scrollen, Screenshots+Kommentare extrahieren | ✅ |
| `compliance_agent` | Facebook/TikTok Ad-Compliance | ✅ |
| `focus_agent` | Audio-Samples während Coding, Focus-Scores | ✅ |

### Sonstige
- `base_agent`, `api` — Basis-Agenten (keine eigenständigen Agenten)

## 3. Model Factory

Einheitliche Schnittstelle für mehrere KI-Modell-Anbieter:

### Verfügbare Anbieter & Modelle
| Anbieter | Modelle | Status |
|----------|---------|--------|
| OpenAI | gpt-5, gpt-4o, gpt-4o-mini, o1, o1-mini, o3-mini | Cloud-Key |
| Claude (Anthropic) | claude-3-opus, claude-3-sonnet, claude-3-haiku | Cloud-Key |
| Gemini | gemini-2.0-flash-exp, gemini-2.0-flash, gemini-1.5-flash, gemini-1.5-pro | Cloud-Key |
| Groq | mixtral-8x7b, gemma2-9b, llama-3.3-70b, llama-3.1-8b, llama-guard-3-8b, deepseek-r1-distill | Cloud-Key |
| DeepSeek | deepseek-chat, deepseek-reasoner, deepseek-r1 | Cloud-Key |
| **Ollama (lokal)** | deepseek-r1, gemma:2b, llama3.2 | Kostenlos, privat |

### Empfehlung
- **Hausstandard**: Ollama (lokal, kein Schlüssel nötig) mit gemma-4-E4B-it-OBLITERATED-Q8_0
- **Cloud**: Ergänzend bei Bedarf (OpenAI/Claude/Gemini/DeepSeek)

## 4. Strategie-System

### Basis-Strategie (`BaseStrategy`)
- Alle Strategien erben von `BaseStrategy`
- Methode `generate_signals()` muss implementiert werden
- Signale werden vom LLM vor Ausführung bewertet
- Position Sizing basiert auf Signalstärke

### Signal-Format
```python
{
    'token': 'TOKEN_ADDRESS',
    'signal': 0.85,          # 0-1
    'direction': 'BUY',      # 'BUY', 'SELL', oder 'NEUTRAL'
    'metadata': {}           # strategie-spezifische Daten
}
```

### Private Strategien (`strategies/`)
- Dateinamens-Präfixe für git-ignore: `private_`, `secret_`, `dev_`
- Diese werden nicht in Git versioniert

## 5. RBI-Swarm (Research-Backtest-Implement)

### Konzept
- **Research**: KI recherchiert Strategien aus Videos/PDFs/Worten
- **Backtest**: Kodiert und testet Backtests
- **Implement**: Setzt erfolgreiche Strategien um

### Sub-Agenten-Katalog
54 Sub-Agenten in Kategorien:
- **Core Development**: coder, planner, researcher, reviewer, tester
- **Consensus**: byzantine-coordinator, raft-manager, gossip-coordinator, security-manager, crdt-synchronizer, quorum-manager, performance-benchmarker
- **Swarm**: hierarchical-coordinator, mesh-coordinator, adaptive-coordinator, collective-intelligence-coordinator, swarm-memory-manager
- **GitHub**: pr-manager, code-review-swarm, issue-tracker, release-manager, workflow-automation
- **Performance**: load-balancer, performance-monitor, topology-optimizer, resource-allocator, benchmark-suite

### SPARC-Methodologie
- Specification → Pseudocode → Architecture → Refinement → Completion
- Test-Driven Development mit paralleler Ausführung

## 6. Börsen-Adapter & API

### Verfügbare Adapter (in GUI)
| Adapter | Typ | Daten |
|---------|-----|-------|
| OKX | Börsen | Öffentliche Daten + bestätigte Orders |
| Kraken | Börsen | Öffentliche Daten + bestätigte Orders |
| Binance | Börsen | Öffentliche Daten + bestätigte Orders |
| Solana RPC | Wallet | Balance (öffentlicher RPC) |

### Order-Sicherheit
- Orders brauchen Checkbox "Order wirklich senden" UND geklickten Button
- Private Schlüssel werden nur gelesen, nie gespeichert/angezeigt
- Order-Limit: OKX 0.0002 BTC, Kraken 0.001 XBT, Binance 0.0005 BTC

## 7. Start & Betrieb

### GUI-Start
- `START_GUI.bat` → Pre-flight Checks → GUI starten
- Direkt: `.venv/Scripts/pythonw.exe moongui.py`
- Logs: `moongui_logs/`

### Agenten-Start
- Agenten starten über GUI-Button (Kindprozesse mit Repo-venv)
- Haus-Agenten: Funding, Kraken, Listingarb, New/Top, Liquidation, CoinGecko, Whale
- Alle anderen Agenten Doppelklick in Bibliothe

### Empfohlene Vorgehensweise
1. Ollama lokal starten oder Cloud-Key konfigurieren
2. Strategien in `src/strategies/custom/` implementieren
3. Backtests durchführen und validieren
4. Agenten einzeln starten und überwachen
5. Risikomanagement aktivieren (risk_agent)

## 8. Quelle & Lizenz

- Repo: `Werkstatt/moon-dev-ai-agents`
- Fork von: yolojewjitsu/moon-dev-ai-agents
- Upstream gepflegt über `Agenten/Werkzeuge/repos-updaten.py`

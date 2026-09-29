# OpenTerminal UI Setup Guide für Handelszentrale

**Datum:** 29.09.2026  
**Version:** OpenTerminalUI (Hitheshkaranth)  
**MCP-Support:** 45 Trading-Tools über Model Context Protocol

---

## Quick Start

### 1. Repository klonen
```bash
# Falls noch nicht vorhanden
git clone https://github.com/Hitheshkaranth/OpenTerminalUI.git ~/OpenTerminalUI
cd ~/OpenTerminalUI
```

### 2. Dependencies installieren
```bash
# Node.js Variante (schneller für Development)
npm install

# Python Variante (FastAPI Backend)
pip install -r requirements.txt
```

### 3. Server starten
```bash
# Node.js
npm run dev          # http://localhost:5173

# Python FastAPI
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

### 4. Browser öffnen
```
http://localhost:5173  (Node.js)
oder
http://localhost:8000  (Python)
```

---

## MCP-Integration (45 Trading-Tools)

### MCP-Server aktivieren

**Datei:** `.mcp/config.json` (oder `.mcp.json` bei Claude Desktop)

```json
{
  "mcpServers": {
    "openterminal": {
      "command": "node",
      "args": ["path/to/openterminal-mcp-server.js"],
      "env": {
        "OPENTERMINAL_API_URL": "http://localhost:8000",
        "OPENTERMINAL_API_KEY": "your-api-key"
      }
    }
  }
}
```

### Verfügbare MCP-Tools (Auswahl)

**Read-Only Tools (38):**
```
- get_watchlist()              → Beobachtungsliste abrufen
- get_portfolio_summary()      → Portfolio-Übersicht
- get_asset_quote(symbol)      → Kurse abrufen
- get_chart_data(symbol, timeframe)
- get_technical_indicators(symbol)
- get_sector_performance()
- get_portfolio_performance()
- get_holdings()               → Positionen auflisten
- get_market_news()            → Marktnachrichten
- search_assets(query)
- get_crypto_board()           → Crypto Top Movers
- get_sentiment_analysis()
- list_backtest_results()
```

**Read-Write Tools (7):**
```
propose_add_watchlist(symbol)        → Watchlist bearbeiten
propose_set_alert(symbol, price)     → Alert setzen
propose_create_paper_trade(...)      → Paper-Trade erstellen
propose_export_portfolio()
propose_run_backtest(strategy, params)
propose_close_position(symbol)
```

---

## REST API Dokumentation

### Endpoints

**Base URL:** `http://localhost:8000`

#### **Portfolio & Watchlist**
```
GET    /api/portfolio             → Portfolio-Details
GET    /api/watchlist             → Beobachtungsliste
POST   /api/watchlist             → Symbol hinzufügen
DELETE /api/watchlist/{symbol}    → Symbol entfernen
```

#### **Marktdaten**
```
GET    /api/quote/{symbol}              → Aktueller Kurs
GET    /api/chart/{symbol}/{timeframe}  → Kerzendaten
GET    /api/indicators/{symbol}         → Technische Indikatoren
GET    /api/sector-performance          → Sektor-Performance
```

#### **Trading**
```
POST   /api/paper-trade                 → Paper-Trade platzieren
GET    /api/paper-trades                → Paper-Trades auflisten
POST   /api/alerts                      → Alert setzen
GET    /api/alerts                      → Alle Alerts
```

#### **Backtesting**
```
POST   /api/backtest                    → Backtest starten
GET    /api/backtest/results            → Backtest-Ergebnisse
GET    /api/backtest/status/{id}        → Status eines Backtests
```

---

## Datenquellen (kostenlos, keine API-Keys)

**Aktien & ETFs:**
- Yahoo Finance (über yfinance)
- Nasdaq, NYSE
- TradingView Charts

**Crypto:**
- CoinGecko (kostenlos, kein Key nötig)
- Binance API (öffentlich)

**Wirtschaftsindikatoren:**
- FRED (Federal Reserve Economic Data)
- Forex Factory
- Makro-Dashboard

---

## Backtesting-Integration

### 1. Strategie hochladen
```bash
# Datei: strategies/my_strategy.py
PUT /api/strategies
{
  "name": "RSI_SMA_Strategy",
  "code": "...",
  "parameters": {
    "rsi_period": 14,
    "sma_period": 50
  }
}
```

### 2. Backtest konfigurieren
```json
POST /api/backtest
{
  "strategy": "RSI_SMA_Strategy",
  "start_date": "2024-01-01",
  "end_date": "2024-09-01",
  "initial_capital": 10000,
  "symbols": ["BTC/USDT", "ETH/USDT"],
  "timeframe": "5m"
}
```

### 3. Ergebnisse analysieren
```bash
GET /api/backtest/results/{backtest_id}

Returns:
{
  "total_return": 0.25,        # 25%
  "sharpe_ratio": 1.8,
  "sortino_ratio": 2.1,
  "max_drawdown": -0.12,       # 12%
  "win_rate": 0.58,            # 58%
  "trades": 145,
  "profit_factor": 2.3
}
```

---

## Paper Trading (Papiergeld-Simulation)

### Workflow
1. **Portfolio initialisieren:** $10,000 Papiergeld
2. **Strategien testen:** Ohne echtes Geld
3. **Trades simulieren:** Echtzeit-Kurse, simulierte Execution
4. **Performance vergleichen:** Mit Backtest-Ergebnissen

```bash
POST /api/paper-trade
{
  "symbol": "BTC/USDT",
  "action": "BUY",
  "quantity": 0.5,
  "order_type": "market"
}
```

---

## Integration in Handelszentrale

### Python-Client für OpenTerminal
```python
# openterminal_interface.py
import httpx
import asyncio
from typing import List, Dict

class OpenTerminalClient:
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
    
    async def get_portfolio(self) -> Dict:
        """Portfolio-Übersicht abrufen"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/api/portfolio"
            )
            return response.json()
    
    async def get_watchlist(self) -> List[Dict]:
        """Beobachtungsliste abrufen"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/api/watchlist"
            )
            return response.json()
    
    async def get_quote(self, symbol: str) -> Dict:
        """Aktuellen Kurs abrufen"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/api/quote/{symbol}"
            )
            return response.json()
    
    async def get_chart_data(self, symbol: str, timeframe: str = "5m") -> List[Dict]:
        """Kerzendaten abrufen"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/api/chart/{symbol}/{timeframe}"
            )
            return response.json()
    
    async def place_paper_trade(self, symbol: str, action: str, quantity: float) -> Dict:
        """Paper-Trade platzieren"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/api/paper-trade",
                json={
                    "symbol": symbol,
                    "action": action,  # "BUY" oder "SELL"
                    "quantity": quantity,
                    "order_type": "market"
                }
            )
            return response.json()
    
    async def run_backtest(self, strategy: str, start_date: str, end_date: str) -> Dict:
        """Backtest starten"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/api/backtest",
                json={
                    "strategy": strategy,
                    "start_date": start_date,
                    "end_date": end_date,
                    "initial_capital": 10000
                }
            )
            return response.json()
```

---

## MCP-Bridge für Hermes

### Hermes-Skill: OpenTerminal Integration

**Datei:** `Agenten/Hermes/skills/brainfiles/openterminal-mcp/SKILL.md`

```markdown
# OpenTerminal MCP Bridge

Max hat die OpenTerminal UI als Multi-Broker-Terminal laufen.
Dieser Skill gibt Hermes Zugriff auf seine 45 Trading-Tools über MCP.

## Verfügbare Tools

### Portfolio-Abfragen
- get_portfolio_summary()    → Gesamtstatus
- get_holdings()             → Positionen
- get_performance()          → Performance-Metriken

### Marktdaten
- get_quote(symbol)          → Aktueller Kurs
- get_chart_data(...)        → Kerzen/Charts
- get_technical_indicators() → Indikatoren (RSI, SMA, etc.)

### Backtesting
- run_backtest(strategy)     → Strategie testen
- get_backtest_results()     → Ergebnisse

### Paper Trading
- place_paper_trade(...)     → Simulierter Trade
- close_position(...)        → Position schließen

## Integration

1. MCP-Server in Hermes registrieren:
   ```bash
   hermes -p <bot> mcp add openterminal ...
   ```

2. In Skills/Prompts nutzen:
   ```
   @openterminal get_portfolio_summary()
   → Gibt Max' aktuelles Portfolio
   ```

3. Beispiel-Workflow:
   ```
   User: "Zeige mir meine Top 3 Performer"
   Hermes:
   1. @openterminal get_portfolio_summary()
   2. Sortiere nach Performance
   3. Zeige Top 3 mit Kurs-Charts
   ```
```

---

## Troubleshooting

### Problem: "CORS Error" beim API-Zugriff
**Lösung:** CORS in OpenTerminal-Config aktivieren:
```json
{
  "cors": {
    "enabled": true,
    "origins": ["localhost:*", "127.0.0.1:*"]
  }
}
```

### Problem: "Chart-Daten laden nicht"
**Lösung:** TradingView/Yahoo-Finance APIs überprüfen:
```bash
# Test
curl http://localhost:8000/api/quote/BTC

# Sollte aktuelle Daten zurückgeben
```

### Problem: "Backtest dauert zu lange"
**Lösung:** Timeframe erhöhen oder Datum-Range verkürzen:
- Statt 5m: 15m oder 1h nutzen
- Statt 1 Jahr: 3 Monate testen

---

## Next Steps

1. **Setup:** npm install & npm run dev
2. **Test:** http://localhost:8000 öffnen
3. **MCP:** MCP-Server registrieren
4. **Integration:** Python-Client in Zentrale einbauen
5. **Backtest:** Erste Strategie testen

---

**Co-Authored-By:** Claude Haiku 4.5 <noreply@anthropic.com>

# FreqTrade Setup Guide für Handelszentrale

**Datum:** 29.09.2026  
**Zielversion:** FreqTrade 2024.12 (aktuell)  
**Zielumgebung:** Lokal (Windows) oder Docker

---

## Option 1: Docker Setup (Empfohlen)

### Vorteil
- Keine lokalen Dependencies nötig
- Reproduzierbar
- Leicht zu isolieren

### Installation
```bash
# Docker Image pullen
docker pull freqtradeorg/freqtrade:latest

# Arbeitsverzeichnis vorbereiten
mkdir -p ~/freqtrade_workdir/user_data/strategies
cd ~/freqtrade_workdir

# FreqTrade Docker Container starten (mit REST API)
docker run -d \
  --name freqtrade \
  -v ~/.freqtrade/user_data:/freqtrade/user_data \
  -p 8080:8080 \
  freqtradeorg/freqtrade:latest \
  trade --strategy SampleStrategy --config user_data/config.json
```

### REST API aktivieren (config.json)
```json
{
  "api_server": {
    "enabled": true,
    "listen_ip_address": "0.0.0.0",
    "listen_port": 8080,
    "verbosity": "info",
    "enable_openapi": true,
    "jwt_secret_key": "your-secret-key-min-32-chars-long"
  }
}
```

---

## Option 2: Native Installation (Windows/Linux)

### Voraussetzungen
```
- Python 3.11+
- pip & virtualenv
- Build Tools (MSVC auf Windows, gcc auf Linux)
- TA-Lib (Optional, für technische Indikatoren)
```

### Installation Schritt-für-Schritt

```bash
# 1. Virtual Environment erstellen
python -m venv venv
source venv/Scripts/activate  # Windows: venv\Scripts\activate

# 2. FreqTrade installieren
pip install freqtrade

# 3. Benutzerverzeichnis erstellen
freqtrade create-userdir --userdir ./user_data

# 4. Standard-Konfiguration kopieren
freqtrade show-config > user_data/config.json

# 5. Konfiguration anpassen (REST API aktivieren)
# → Bearbeiten Sie user_data/config.json (siehe oben)

# 6. Test-Run durchführen
freqtrade trade --strategy SampleStrategy --dry-run
```

---

## Konfiguration: REST API + Börse

### Minimal-Config (config.json)

```json
{
  "max_open_trades": 1,
  "stake_currency": "USDT",
  "dry_run": true,
  "dry_run_wallet": 1000,
  
  "exchange": {
    "name": "binance",  # oder: kraken, okx, bybit
    "key": "your-api-key",
    "secret": "your-api-secret",
    "pair_whitelist": ["BTC/USDT", "ETH/USDT"],
    "pair_blacklist": []
  },
  
  "api_server": {
    "enabled": true,
    "listen_ip_address": "127.0.0.1",
    "listen_port": 8080,
    "verbosity": "info",
    "enable_openapi": true,
    "jwt_secret_key": "your-32-char-secret-key-here!"
  },
  
  "telegram": {
    "enabled": false
  }
}
```

---

## REST API Testen

### 1. JWT Token generieren
```bash
curl -X POST http://localhost:8080/api/v1/token \
  -H "Content-Type: application/json" \
  -d '{"username":"freqtrader","password":"your-password"}'
```

### 2. Trades auslesen
```bash
curl -H "Authorization: Bearer <TOKEN>" \
  http://localhost:8080/api/v1/trades
```

### 3. Performance-Metriken
```bash
curl -H "Authorization: Bearer <TOKEN>" \
  http://localhost:8080/api/v1/profit
  
curl -H "Authorization: Bearer <TOKEN>" \
  http://localhost:8080/api/v1/performance
```

### 4. Alle verfügbaren Endpoints
```
GET    /api/v1/status              → Bot-Status
GET    /api/v1/trades              → Alle Trades (max 500)
GET    /api/v1/profit              → Profit/Loss Übersicht
GET    /api/v1/performance         → Performance pro Pair
GET    /api/v1/daily               → Tägliche Statistik
GET    /api/v1/balance             → Wallet-Balance
GET    /api/v1/whitelist           → Trading-Paare
POST   /api/v1/forceenter          → Manuellen Trade auslösen
POST   /api/v1/forceexit           → Position schließen
POST   /api/v1/stop                → Bot stoppen
POST   /api/v1/start               → Bot starten
POST   /api/v1/reload_config       → Konfiguration neu laden
WebSocket: /api/ws                 → Live-Updates
```

---

## Backtesting Setup

### 1. Daten herunterladen
```bash
freqtrade download-data \
  --timeframe 5m \
  --timerange 20240101-20240901 \
  --exchange binance \
  --pairs BTC/USDT ETH/USDT
```

### 2. Backtest durchführen
```bash
freqtrade backtesting \
  --strategy SampleStrategy \
  --timeframe 5m \
  --timerange 20240101-20240901 \
  --stake-amount 100 \
  --dry-run-wallet 10000
```

### 3. Ergebnisse analysieren
```bash
freqtrade show-backtest-results \
  --backtest-result-file user_data/backtest_results/backtest-result-latest.json
```

---

## Dry-Run Phase (vor Live-Trading)

**Mindestdauer:** 7 Tage  
**Ziel:** Validierung, dass Backtest-Ergebnisse auch in echter Marktumgebung gelten

```bash
# Dry-Run mit echten Daten, aber simulierten Orders
freqtrade trade \
  --strategy SampleStrategy \
  --dry-run \
  --dry-run-wallet 10000
```

**Zu überprüfen:**
- Win Rate (sollte ±50% Backtest-Rate sein)
- Sharpe Ratio (sollte ähnlich sein)
- Drawdown (sollte nicht größer sein)
- Keine unerwarteten Fehler

---

## Strategie-Entwicklung

### Eigene Strategie erstellen
```bash
freqtrade new-strategy --strategy MyStrategy
```

### Strategie-Vorlage (user_data/strategies/MyStrategy.py)
```python
from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib

class MyStrategy(IStrategy):
    MINIMAL_ROI = {
        "0": 0.10  # 10% Profit → Exit
    }
    
    STOPLOSS = -0.10  # 10% Loss → Exit
    
    TIMEFRAME = '5m'
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # RSI Indikator
        dataframe['rsi'] = talib.RSI(dataframe['close'], timeperiod=14)
        
        # SMA
        dataframe['sma'] = talib.SMA(dataframe['close'], timeperiod=50)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Long Entry: RSI < 30 UND Preis > SMA
        dataframe.loc[
            (dataframe['rsi'] < 30) &
            (dataframe['close'] > dataframe['sma']),
            'enter_long'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit: RSI > 70
        dataframe.loc[
            (dataframe['rsi'] > 70),
            'exit_long'] = 1
        
        return dataframe
```

---

## Integration in Handelszentrale

### Python-Client für FreqTrade-REST-API
```python
# freqtrade_interface.py
import httpx
import json
from typing import List, Dict

class FreqTradeClient:
    def __init__(self, api_url: str = "http://localhost:8080", jwt_token: str = ""):
        self.api_url = api_url
        self.jwt_token = jwt_token
        self.headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json"
        }
    
    async def get_trades(self) -> List[Dict]:
        """Alle offenen Trades auslesen"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/api/v1/trades",
                headers=self.headers
            )
            return response.json()
    
    async def get_profit(self) -> Dict:
        """Profit/Loss Übersicht"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/api/v1/profit",
                headers=self.headers
            )
            return response.json()
    
    async def get_performance(self) -> List[Dict]:
        """Performance pro Pair"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/api/v1/performance",
                headers=self.headers
            )
            return response.json()
    
    async def get_balance(self) -> Dict:
        """Wallet Balance"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/api/v1/balance",
                headers=self.headers
            )
            return response.json()
    
    async def force_exit(self, trade_id: int) -> Dict:
        """Position forciert schließen"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/api/v1/forceexit",
                headers=self.headers,
                json={"tradeid": str(trade_id)}
            )
            return response.json()
```

---

## Troubleshooting

### Problem: "Failed building wheel for sdnotify"
**Lösung:** Docker verwenden oder systemtweite Dependencies installieren:
```bash
# Ubuntu/Debian
sudo apt-get install build-essential python3-dev

# macOS
brew install python-build
```

### Problem: "Exchange API-Key ungültig"
**Lösung:** 
- Testnet-Keys verwenden (OKX, Binance haben Testnet)
- Oder readonly API-Key (read-only für Daten, kein Handel)

### Problem: "Backtest-Ergebnisse stimmen nicht überein"
**Lösung:**
- Dry-Run mindestens 7 Tage durchführen
- Lookahead-Bias prüfen (Strategien sollten nur Past Data nutzen)
- Market-Fees beachten (unterschiedliche Börsen → unterschiedliche Gebühren)

---

## Nächste Schritte

1. **Setup Choice:** Docker oder Native? → Docs befolgen
2. **Test-Börse:** OKX Testnet empfohlen (kostenlos, ohne echte Schritte)
3. **Erste Strategie:** SampleStrategy backtesten
4. **Dry-Run:** 7 Tage Validierung
5. **Integration:** Python-Client in Handelszentrale einbauen
6. **Live-Trading:** Erst nach erfolgreicher Dry-Run Phase

---

**Co-Authored-By:** Claude Haiku 4.5 <noreply@anthropic.com>

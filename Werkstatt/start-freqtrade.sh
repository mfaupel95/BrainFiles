#!/bin/bash
# FreqTrade Docker Start Script
# Nutze auf lokaler Maschine: bash start-freqtrade.sh

set -e

echo "🚀 Starting FreqTrade with Docker..."

# 1. Verzeichnis vorbereiten
mkdir -p ~/freqtrade_workdir/user_data/{strategies,logs}
cd ~/freqtrade_workdir

# 2. Config kopieren (ersetze YOUR_KEY und YOUR_SECRET!)
cat > user_data/config.json << 'EOF'
{
  "max_open_trades": 3,
  "stake_currency": "USDT",
  "dry_run": true,
  "dry_run_wallet": 10000,

  "exchange": {
    "name": "binance",
    "key": "YOUR_API_KEY_HERE",
    "secret": "YOUR_API_SECRET_HERE",
    "pair_whitelist": ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
    "pair_blacklist": []
  },

  "api_server": {
    "enabled": true,
    "listen_ip_address": "0.0.0.0",
    "listen_port": 8080,
    "enable_openapi": true,
    "jwt_secret_key": "max-freqtrade-secret-key-min-32-chars-long"
  },

  "telegram": {"enabled": false},
  "db_url": "sqlite:///tradesv3.sqlite"
}
EOF

echo "✓ Config created at user_data/config.json"

# 3. Docker starten
docker run -d \
  --name freqtrade \
  -v ~/.freqtrade/user_data:/freqtrade/user_data \
  -p 8080:8080 \
  -e FREQTRADE__EXCHANGE__KEY="${FT_API_KEY}" \
  -e FREQTRADE__EXCHANGE__SECRET="${FT_API_SECRET}" \
  freqtradeorg/freqtrade:latest \
  trade --strategy SampleStrategy

echo "✓ FreqTrade Container gestartet"
echo ""
echo "🌐 API verfügbar unter: http://localhost:8080"
echo "📊 OpenAPI Docs: http://localhost:8080/docs"
echo ""
echo "Teste die API:"
echo "curl -X GET http://localhost:8080/api/v1/status"
echo ""
echo "Logs anschauen:"
echo "docker logs -f freqtrade"

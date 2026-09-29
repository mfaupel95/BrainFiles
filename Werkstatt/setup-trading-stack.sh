#!/bin/bash
# Automatisches Setup: FreqTrade + OpenTerminal
# Nutze: bash setup-trading-stack.sh

set -e

echo "🚀 Trading Stack Setup (FreqTrade + OpenTerminal)"
echo "=================================================="

# ============ FREQTRADE ============
echo -e "\n📊 [1/3] FreqTrade Setup..."

# Verzeichnis
mkdir -p ~/freqtrade_workdir/user_data/{strategies,logs}
cd ~/freqtrade_workdir

# Python venv (falls lokal)
if command -v python3 &> /dev/null; then
    python3 -m venv venv
    source venv/bin/activate
    pip install --quiet freqtrade 2>/dev/null && echo "✅ FreqTrade installiert" || echo "⚠️  FreqTrade pip-install fehlgeschlagen (normal in Remote-Env)"
else
    echo "⚠️  Python nicht gefunden — nutze Docker"
fi

# Config
cat > user_data/config.json << 'EOF'
{
  "max_open_trades": 3,
  "stake_currency": "USDT",
  "dry_run": true,
  "dry_run_wallet": 10000,
  "exchange": {
    "name": "binance",
    "key": "TEST_KEY",
    "secret": "TEST_SECRET",
    "pair_whitelist": ["BTC/USDT", "ETH/USDT"]
  },
  "api_server": {
    "enabled": true,
    "listen_ip_address": "0.0.0.0",
    "listen_port": 8080,
    "jwt_secret_key": "max-freqtrade-secret-key-min-32-chars"
  },
  "telegram": {"enabled": false}
}
EOF

echo "✅ FreqTrade Config erstellt"

# ============ OPENTERMINAL ============
echo -e "\n💻 [2/3] OpenTerminal UI Setup..."

cd ~
if [ ! -d "OpenTerminalUI" ]; then
    git clone https://github.com/Hitheshkaranth/OpenTerminalUI.git 2>/dev/null && echo "✅ OpenTerminal geklont" || echo "⚠️  Git clone fehlgeschlagen"
else
    echo "ℹ️  OpenTerminal bereits vorhanden"
fi

cd OpenTerminalUI
if command -v npm &> /dev/null; then
    npm install --silent 2>/dev/null && echo "✅ OpenTerminal Dependencies installiert" || echo "⚠️  npm install fehlgeschlagen"
else
    echo "⚠️  Node.js nicht gefunden"
fi

# ============ ZUSAMMENFASSUNG ============
echo -e "\n=================================================="
echo "✅ SETUP ABGESCHLOSSEN"
echo "=================================================="
echo -e "\n📊 FreqTrade:"
echo "   Config: ~/freqtrade_workdir/user_data/config.json"
echo "   Start (Docker): docker run -p 8080:8080 freqtradeorg/freqtrade:latest"
echo "   Start (Python): cd ~/freqtrade_workdir && freqtrade trade"
echo "   API: http://localhost:8080"
echo ""
echo "💻 OpenTerminal:"
echo "   Pfad: ~/OpenTerminalUI"
echo "   Start: cd ~/OpenTerminalUI && npm run dev"
echo "   Browser: http://localhost:5173"
echo ""
echo "🧪 Test:"
echo "   python3 Werkstatt/test-freqtrade-api.py"
echo ""
echo "=================================================="

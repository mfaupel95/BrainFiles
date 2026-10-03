#!/bin/bash
# T-198: was traegt die KURZE Seite? Derselbe Bot, dreimal dieselbe Strategie,
# nur die Seite unterscheidet sich - dazu der Spot-Vergleichslauf vom 30.09.
#
# WARUM FUTURES: `can_short = True` laedt im Spot-Modus nicht
# (strategy_resolver). Erst `trading_mode: futures` macht die kurze Seite
# moeglich - und rechnet dabei die FUNDING-RATE mit (eigene Kerzenreihe,
# geladen mit `download-data --trading-mode futures`).
#
# Die Zahlen sind eine MESSUNG, kein Umbau: der laufende Bot auf 8083 faehrt
# weiter Spot und long-only.
#
# Aufruf: bash messung-shortseite.sh
set -u
cd "$(dirname "$0")" || exit 1
FRT="./.venv/Scripts/freqtrade.exe"
TR="${TR:-20240929-20260929}"
mkdir -p logs
CFG="user_data/config.marktlage-regime.futures.json"

for seite in long short beide; do
    echo "=== Futures / Seite $seite $TR"
    MSYS_NO_PATHCONV=1 "$FRT" backtesting \
        --config "$CFG" \
        --config "user_data/messung/seite-$seite.json" \
        --strategy MoonDevMarketRegimeFutures \
        --timerange "$TR" \
        --cache none --export trades \
        > "logs/bt-short-$seite.txt" 2>&1
    echo "   exit=$? -> logs/bt-short-$seite.txt"
done
echo "fertig"
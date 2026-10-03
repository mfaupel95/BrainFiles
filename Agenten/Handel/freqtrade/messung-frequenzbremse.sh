#!/bin/bash
# T-197: Frequenzbremse messen. Vorher/nachher mit DEMSELBEN Backtest.
#
# WARUM LOKAL: Am 01.10.2026 antwortete die Docker-Engine nicht mehr (CLI haengt,
# kein Container, kein Image). Freqtrade 2026.9 ist deshalb in ein eigenes venv
# unter Agenten/Handel/freqtrade/.venv installiert - dieselben Configs, dieselben
# Daten (user_data/data/binance), derselbe Zeitraum. Der Docker-Weg bleibt der
# Hausweg; dieser Lauf ist die Messung, nicht ein Umbau.
#
# Aufruf:  bash messung-frequenzbremse.sh all
#          bash messung-frequenzbremse.sh trading-agent voll
set -u
cd "$(dirname "$0")" || exit 1
FRT="./.venv/Scripts/freqtrade.exe"
TR="${TR:-20240929-20260929}"
mkdir -p logs backtest_results

strat_von() {
    case "$1" in
        trading-agent)    echo MoonDevTradingAgent ;;
        topmovers)        echo MoonDevTopMovers ;;
        marktlage-regime) echo MoonDevMarketRegime ;;
        *) echo "" ;;
    esac
}

lauf() {   # lauf <bot> <variante>
    bot="$1"; var="$2"; strat="$(strat_von "$bot")"
    if [ -z "$strat" ]; then echo "unbekannter Bot: $bot"; return 1; fi
    cfg="user_data/config.$bot.signal-an.json"
    if [ "$var" = "vor" ]; then
        cfg="$cfg --config user_data/messung/aus.json"
    else
        cfg="$cfg --config user_data/messung/$var.json"
    fi
    echo "=== $bot / $var ($strat) $TR"
    MSYS_NO_PATHCONV=1 "$FRT" backtesting \
        --config $cfg \
        --strategy "$strat" \
        --timerange "$TR" \
        --cache none --export trades \
        --export-filename "backtest_results/t197-$var-$bot.json" \
        > "logs/bt-$var-$bot.txt" 2>&1
    echo "   exit=$? -> logs/bt-$var-$bot.txt"
}

fall="$1"; var="${2:-}"
if [ "$fall" = "all" ]; then
    for v in vor nur-ziel nur-stop nur-abstand6 nur-abstand24 nur-abstand48 \
             nur-vorfilter voll voll-abstand24; do
        lauf trading-agent "$v"
    done
    for bot in topmovers marktlage-regime; do
        lauf "$bot" vor
        lauf "$bot" voll
    done
else
    lauf "$fall" "$var"
fi
echo "fertig"
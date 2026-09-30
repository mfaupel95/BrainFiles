#!/bin/bash
# Die drei portierten Moon-Dev-Bots als eigene Freqtrade-Container.
#
# PROBEBETRIEB: dry_run steht in user_data/bots/<name>.json auf true. Diese
# Bots geben keine Order an eine Boerse - sie rechnen mit Echtkursen und
# fuehren ein Papierbuch. Warum das so bleibt, steht in bots.json.
#
# ZWEI DINGE, DIE MAN LEICHT FALSCH MACHT:
#
# 1. Jeder Bot braucht eine EIGENE Datenbankdatei (--db-url). Ohne sie schreiben
#    alle drei in dieselbe user_data/tradesv3.sqlite, ueberschreiben sich
#    gegenseitig und die Buecher sind nicht mehr auseinanderzuhalten.
# 2. Der API-Port steht IM Bot-Aufsatz (api_server.listen_port) UND im
#    Port-Mapping. Beide muessen dieselbe Zahl tragen - der Aufsatz bestimmt,
#    wo freqtrade IM Container lauscht, das Mapping, wo es aussen erscheint.
#
# Zugangsdaten der Weboberflaeche stehen allein in user_data/config.json und
# werden hier NICHT angefasst.
cd "$(dirname "$0")" || exit 1
export MSYS_NO_PATHCONV=1
UD="$(pwd -W 2>/dev/null || pwd)/user_data"

starte() {
    name="$1"; strat="$2"; port="$3"
    docker rm -f "freqtrade-$name" >/dev/null 2>&1
    docker run -d --name "freqtrade-$name" --restart unless-stopped \
        -v "$UD:/freqtrade/user_data" \
        -p "127.0.0.1:$port:$port" \
        freqtradeorg/freqtrade:stable \
        trade \
        --config /freqtrade/user_data/config.json \
        --config "/freqtrade/user_data/bots/$name.json" \
        --strategy "$strat" \
        --db-url "sqlite:////freqtrade/user_data/tradesv3-$name.sqlite"
    echo "  freqtrade-$name -> Port $port (Strategie $strat)"
}

echo "Starte die drei Bots:"
starte trading-agent    MoonDevTradingAgent 8081
starte topmovers        MoonDevTopMovers    8082
starte marktlage-regime MoonDevMarketRegime 8083

echo
echo "Warte 25 s auf den ersten Herzschlag ..."
sleep 25
docker ps --filter "name=freqtrade-" --format "  {{.Names}} | {{.Status}} | {{.Ports}}"
echo
echo "Letzte Zeilen je Bot:"
for n in trading-agent topmovers marktlage-regime; do
    echo "--- freqtrade-$n ---"
    docker logs --tail 4 "freqtrade-$n" 2>&1 | sed 's/^/    /'
done

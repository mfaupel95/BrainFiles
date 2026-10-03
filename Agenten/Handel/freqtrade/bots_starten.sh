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
# Zugangsdaten der Weboberflaeche stehen je Bot in seiner AUFSATZ-Datei
# config.<name>.json (eigene Zufallswerte, von `bots.py configs` geschrieben)
# und werden hier NICHT angefasst. Die Basis-config.json liefert die
# Boersen-Schluessel und die gemeinsamen Einstellungen; der Aufsatz bringt
# Strategie, Port und das EIGENE Passwort mit. Seit 01.10.2026 laedt der
# Starter den Aufsatz config.<name>.json statt des alten bots/<name>.json -
# vorher trug der Aufsatz keine Zugangsdaten, und jeder Container akzeptierte
# nur das Basis-Passwort (gemessen 30.09. und 01.10.2026: 401 auf 8081-8083
# mit dem Aufsatz-Passwort). Der tiefe Merge von Freqtrade mischt beide.
#
# ALTFLAST (30.09.2026): Der Vorgaenger-Container `freqtrade` auf Port 8080
# (SampleStrategy, kein Bot) ist gestoppt. Er faehrt nicht in diesem Skript und
# wird hier auch nicht gestartet - der Zweck ist bis heute unbekannt (T-201).
# Er machte den Live-Test der Bridge rot: mit DENSELBEN Zugangsdaten aus
# user_data/config.json antwortete er auf ping 200, auf show_config aber 401,
# waehrend die drei echten Bots (8081-8083) beides mit 200 beantworten - er
# trug ein anderes Passwort im Speicher. Gestoppt ist der Test uebersprungen
# statt rot.
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
        --config "/freqtrade/user_data/config.$name.json" \
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

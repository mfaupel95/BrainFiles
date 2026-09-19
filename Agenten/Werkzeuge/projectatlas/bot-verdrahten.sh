#!/usr/bin/env bash
# Haengt einen Repo-Bot an SEINEN ProjectAtlas (idempotent).
# Aufruf: bash bot-verdrahten.sh <botname>   (Botname = Hermes-Profil, z. B. openterminal)
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PA="$HERE/bin/projectatlas.exe"
HERMES="/c/Users/faupe/Documents/BrainFiles/Agenten/Hermes/bin/hermes.exe"
export HERMES_HOME="C:\\Users\\faupe\\Documents\\BrainFiles\\Agenten\\Hermes"
unset PYTHONHOME PYTHONPATH

bot="${1:-}"
if [ -z "$bot" ]; then echo "Aufruf: bash bot-verdrahten.sh <botname>"; exit 2; fi

cwd="$("$HERMES" -p "$bot" config get terminal.cwd 2>/dev/null | tr -d '\r' | tail -1)"
if [ -z "$cwd" ] || [ ! -d "$cwd" ]; then echo "FEHLER: Arbeitsverzeichnis von '$bot' nicht gefunden ($cwd)"; exit 1; fi
echo "Bot      : $bot"
echo "Repo     : $cwd"

if [ ! -f "$cwd/.projectatlas/projectatlas.db" ]; then
  echo "-> noch kein Atlas, init laeuft"
  ( cd "$cwd" && "$PA" --format json init > "$HERE/logs/bot-$bot.json" 2> "$HERE/logs/bot-$bot.err" ) \
    || echo "   HINWEIS: init meldete einen Fehler (siehe logs/bot-$bot.err)"
fi

if [ ! -f "$cwd/.projectatlas/projectatlas.db" ]; then
  echo "FEHLER: kein Atlas fuer '$bot' (init fehlgeschlagen) - Eintrag uebersprungen"
  exit 1
fi

db_native="$(cygpath -w "$cwd/.projectatlas/projectatlas.db")"
cfg_native="$(cygpath -w "$cwd/.projectatlas/config.toml")"
# EIN printf 'Y\n' reicht NICHT: die Frage "Enable all 43 tools?" blieb damit
# unbeantwortet (hermes endete mit "Cancelled.", der Eintrag blieb unveraendert,
# gemessen 19.09.2026). `yes |` liefert so viele Y, wie Prompts kommen.
yes | "$HERMES" -p "$bot" mcp add projectatlas \
  --command "$(cygpath -w "$PA")" \
  --args --require-version 0.4.5 --db "$db_native" --config "$cfg_native" mcp 2>&1 | tail -3
"$HERMES" -p "$bot" mcp test projectatlas 2>&1 | grep -E "Connected|Tools discovered|fehlgeschlagen|error"

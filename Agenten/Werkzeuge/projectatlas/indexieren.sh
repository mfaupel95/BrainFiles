#!/usr/bin/env bash
# ProjectAtlas: alle Arbeits-Repos indexieren (idempotent, mehrfach ausfuehrbar).
# Laeuft ueber die Host-Shell (git-bash); Logs unter Agenten/Werkzeuge/projectatlas/logs/.
# Mit Argumenten (bash indexieren.sh <name>...) nur die genannten Repos unter
# Werkstatt/ (Name = Ordnername); ohne Argumente alle Repos.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PA="$HERE/bin/projectatlas.exe"
ROOT="/c/Users/faupe/Documents/BrainFiles"
LOG="$HERE/logs"
mkdir -p "$LOG"

repos=()
if [ "$#" -gt 0 ]; then
  # Repo-Filter: nur die genannten Repos unter Werkstatt/ (Name = Ordnername).
  for name in "$@"; do
    [ -d "$ROOT/Werkstatt/$name/.git" ] && repos+=("$ROOT/Werkstatt/$name")
  done
else
  for d in "$ROOT"/Werkstatt/*/; do [ -d "$d/.git" ] && repos+=("${d%/}"); done
  for n in CryptoPredictions CryptoTrade FinRL freqtrade intelligent-trading-bot OmniRoute omnitrade RLTrader security-skills-claude-code skillspector trailofbits-skills; do
    [ -d "$ROOT/Werkstatt/$n/.git" ] && repos+=("$ROOT/Werkstatt/$n")
  done
  [ -d "$ROOT/Agenten/Handel/nautilus/.git" ] && repos+=("$ROOT/Agenten/Handel/nautilus")
  [ -d "$ROOT/Agenten/Hermes/hermes-agent/.git" ] && repos+=("$ROOT/Agenten/Hermes/hermes-agent")
fi

echo "Kandidaten: ${#repos[@]}"
for r in "${repos[@]}"; do
  name="$(basename "$r")"
  # Projektatlas-Zustand gehoert nicht in den Fremd-Klon (nur lokal, ohne die .gitignore des Originals anzufassen)
  mkdir -p "$r/.git/info" 2>/dev/null
  if [ -f "$r/.git/info/exclude" ]; then
    grep -qxF '.projectatlas/' "$r/.git/info/exclude" || printf '.projectatlas/\n' >> "$r/.git/info/exclude"
  else
    printf '.projectatlas/\n' > "$r/.git/info/exclude"
  fi
  t0=$(date +%s)
  # Ausschluss-Vorphase: config.toml muss existieren, sonst schlaegt ignore add fehl
  # (gemessen 19.09.2026). .venv/node_modules/__pycache__/build/dist/target sind
  # Standard-Ausschluss von v0.4.5; nur .next/.turbo fehlen und werden ergaenzt.
  ( cd "$r" && "$PA" --format json init --no-scan >/dev/null 2>&1 )
  for ign in .next .turbo; do
    [ -d "$r/$ign" ] && ( cd "$r" && "$PA" ignore add --kind dir-name "$ign" >/dev/null 2>&1 )
  done
  ( cd "$r" && "$PA" --format json init > "$LOG/$name.json" 2> "$LOG/$name.err" )
  rc=$?
  t1=$(date +%s)
  db="$r/.projectatlas/projectatlas.db"
  if [ -f "$db" ]; then size=$(( $(stat -c %s "$db") / 1048576 )); else size=-1; fi
  printf '%-34s rc=%s %4ss db=%sMB\n' "$name" "$rc" "$((t1-t0))" "$size"
done
echo "=== Fehlerdateien mit Inhalt ==="
for f in "$LOG"/*.err; do [ -s "$f" ] && { echo "--- $(basename "$f")"; head -3 "$f"; }; done
echo "=== Gesamtgroesse ==="
# Ueber die REPO-LISTE, nicht per `find`: find folgt der Junction
# Werkstatt -> O:\Werkstatt nicht (gemessen 15.09.2026) und meldete
# "2 Atlanten, 1.0 MB" statt der echten 33 Atlanten und 5,1 GB.
gesamt=0; zahl=0
for r in "${repos[@]}"; do
  db="$r/.projectatlas/projectatlas.db"
  [ -f "$db" ] || continue
  s=$(stat -c %s "$db" 2>/dev/null || echo 0)
  gesamt=$((gesamt + s)); zahl=$((zahl + 1))
done
awk -v n="$zahl" -v b="$gesamt" 'BEGIN {printf "%d Atlanten, %.1f MB\n", n, b/1048576}'
echo FERTIG

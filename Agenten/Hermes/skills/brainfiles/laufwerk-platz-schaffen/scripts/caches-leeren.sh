#!/usr/bin/env bash
# Reproduzierbare Caches und Muell leeren - mit Zahl je Ordner.
#
# Aufruf ueber das `terminal`-Werkzeug, als EIN Hintergrundauftrag mit
# Ausgabedatei (npm/pnpm/du laufen einzeln in das Terminal-Zeitlimit von ~420 s):
#   bash caches-leeren.sh > <scratch>/cache-leeren.txt 2>&1
#
# Grundregel: die Meldung eines Werkzeugs ist keine Quittung, die
# Ordnergroesse vor/nach ist es. Deshalb messen wir selbst.
#
# Jede Messung laeuft unter `timeout`: ein inhaltsadressiertes Store (pnpm)
# braucht fuer EIN `du` mehrere Minuten und wuerde den Lauf sonst blockieren.
# Eine fehlende Zahl heisst "nicht fertig gemessen", nicht "0 MB".
set -u
LAUF="${LOCALAPPDATA:-$HOME/AppData/Local}"
LAUF_MSYS=$(printf '%s' "$LAUF" | sed -e 's|\\|/|g' -e 's|^C:|/c|')
ORDNER=("pip" "pnpm" "npm-cache" "uv" "CrashDumps" "Temp")
MESS_TIMEOUT=90

mess() {
  local wert
  wert=$(timeout "$MESS_TIMEOUT" du -sm "$LAUF_MSYS/$1" 2>/dev/null | cut -f1)
  printf '%s' "${wert:-(nicht gemessen)}"
}

echo "df vorher: $(df -m /c | tail -1)"
for n in "${ORDNER[@]}"; do printf '%-12s %s MB\n' "$n" "$(mess "$n")"; done

echo '--- Reinigung ---'
pip cache purge            && echo 'pip ok'
npm cache clean --force    && echo 'npm ok'
pnpm store prune           && echo 'pnpm ok'
uv  cache clean            && echo 'uv ok'

# CrashDumps und Temp: nur Inhalte, Dateien in Benutzung bleiben liegen
for n in CrashDumps Temp; do
  find "$LAUF_MSYS/$n" -mindepth 1 -maxdepth 1 -exec rm -rf {} + 2>/dev/null || true
done

echo '--- nachher ---'
for n in "${ORDNER[@]}"; do printf '%-12s %s MB\n' "$n" "$(mess "$n")"; done
echo "df nachher: $(df -m /c | tail -1)"

#!/bin/bash
# Next.js-Seite sondieren: HTML speichern, API-Hosts finden, Chunks laden,
# Endpunkt-Builder extrahieren. Aufruf (git-bash):
#   bash chunks-sondieren.sh <seiten-url> [ausgabe-ordner]
# Ausgabe-Ordner Vorgabe: C:/Users/$(whoami)/AppData/Local/Temp/pf-chunks
SEITE="$1"
if [ -z "$SEITE" ]; then echo "Aufruf: bash chunks-sondieren.sh <seiten-url> [ordner]"; exit 2; fi
TMP="${2:-C:/Users/$(whoami)/AppData/Local/Temp/pf-chunks}"
mkdir -p "$TMP"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
HOST="$(echo "$SEITE" | sed -E 's#https?://([^/]*)/.*#\1#')"

curl -s -m 30 -A "$UA" -o "$TMP/seite.html" "$SEITE"
echo "HTML: $(wc -c < "$TMP/seite.html") Bytes"

echo "--- fremde Hosts im HTML ---"
grep -oE 'https?://[a-zA-Z0-9.-]+' "$TMP/seite.html" | sort | uniq -c | sort -rn | head -25

echo "--- Chunk-URLs sammeln ---"
grep -oE 'src="[^"]*_next/static/[^"]*"' "$TMP/seite.html" \
  | sed 's/src="//;s/"$//' | sort -u > "$TMP/urls.txt"
echo "URLs: $(wc -l < "$TMP/urls.txt")"
i=0
while read -r u; do
  i=$((i+1))
  curl -s -m 30 -A "$UA" -o "$TMP/c_$i.js" "https://$HOST$u"
  # Kleine Chunks (Polyfills, Utilities) verwerfen
  if [ "$(wc -c < "$TMP/c_$i.js")" -lt 8000 ]; then rm -f "$TMP/c_$i.js"; fi
done < "$TMP/urls.txt"
echo "Gehalten: $(ls "$TMP" | grep -c '\.js$') Chunks, gesamt $(du -sh "$TMP" | cut -f1)"

echo "--- Basis-Konstanten (CLIENT/PROFILE/... = https://...) ---"
grep -hoE '[A-Z_]+[:=]"[a-z]+://[^"]*"' "$TMP"/*.js 2>/dev/null | sort -u | head -20

echo "--- Endpunkt-Builder: NAME:(...)=>{let x=new URL("/pfad",t.BASIS) ---"
grep -hoE '[A-Z_0-9]+:\([^)]*\)=>\{let [a-z]=new URL\("[^"]*",[a-zA-Z._]+\)' "$TMP"/*.js 2>/dev/null | sort -u | head -40

echo "--- alle new-URL-Pfade ---"
grep -hoE 'new URL\("[^"]*"' "$TMP"/*.js 2>/dev/null | sort -u | head -40

echo "--- Server-Validierungs-Hinweise (must be one of) ---"
grep -hoE '"message":[^]]*' "$TMP"/*.js 2>/dev/null | head -5

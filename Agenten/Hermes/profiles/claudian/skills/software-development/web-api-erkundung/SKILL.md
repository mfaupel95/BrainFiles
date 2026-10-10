---
name: web-api-erkundung
description: "Findet JSON-Endpunkte einer Web-App in deren JS-Bundles."
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Web, API, ReverseEngineering, Next.js]
---

# Web-API-Erkundung

Findet die **ungeschriebenen JSON-Endpunkte** einer Web-App, ohne SDK, Key
allein
oder Doku: Die Seite selbst (HTML + JS-Bundles) verraet ihre API-Hosts,
Pfade und Feldnamen. Sie funktioniert, wenn der alte API-Host tot ist (der
Browser-Backend haengt), wenn "die Doku gibt es nicht" oder ein Screenshot
zeigt, welche Daten die App anzeigt, aber nicht woher. Reine Lese-Sondierung:
kein Login, kein Schreiben, keine UI-Automation. Werkzeuge: bash + curl +
grep (ueber die Hermes-Tools `terminal` und `write_file` aufgerufen).
Bewaehrt am 14.09.2026: Pump.fun-Copy-Trading-Rangliste (alle Endpunkte in
agenten/handel/kopier/lesen.py).

## When to Use

- "Gibt es eine API fuer X?" und die Doku ist leer oder veraltet.
- Eine fremde Web-App zeigt Daten, die ein Papierbuch/Agent brauchen soll.
- Der bekannte API-Host antwortet nicht mehr (DNS-Fehler 1016 = Host
  eingestellt, nicht blockiert).
- Ein Screenshot der App zeigt Felder, deren Quelle unbekannt ist.
- Browser-Automation haengt (cloud-Backend tot) - die Sondierung laeuft
  trotzdem per curl weiter.

## Prerequisites

- bash (git-bash/MSYS) + curl + grep auf dem Rechner (Windows-Host: ja).
- Schreibzugriff auf einen Temp-Ordner (`C:/Users/<user>/AppData/Local/Temp`
  funktioniert fuer native curl UND bash, `/tmp` nur fuer bash).
- Browser-UA-Header, sonst antworten manche Seiten nicht:
  `Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0 Safari/537.36`
- KEINE Schluessel noetig - nur oeffentliche Endpunkte der Seite.

## How to Run

1. Seite pruefen: `web_extract` auf die Seiten-URL - oft stecken die Daten
   schon server-gerendert im HTML (Ranglisten, Listen, Adressen).
2. Verbindung vom Rechner testen (write_file + `terminal`), HTML sichern.
3. API-Hosts im HTML finden (grep), Chunks laden, Endpunkt-Builder greppen.
4. Endpunkte probieren; aus Validierungsfehlern die erlaubten Werte lesen.
5. Feldnamen paarweise prüfen (gleiche Bedeutung, andere Schreibweise).

Der Ladeschritt 3 ist als Skript hinterlegt:
`bash scripts/chunks-sondieren.sh <seite-url> [ausgabe-ordner]`

## Quick Reference

```
# Seite laden und API-Hosts im HTML finden
curl -s -m 30 -A "$UA" -o $TMP/seite.html "$SEITE"
grep -oE 'https?://[a-zA-Z0-9.-]+' $TMP/seite.html | sort -u

# Chunk-URLs sammeln (Next.js): src=".../_next/static/chunks/..."
grep -oE 'src="[^"]*_next/static/[^"]*"' $TMP/seite.html \
  | sed 's/src="//;s/"$//' | sort -u

# Basis-Konstanten im JS: CLIENT:"https://..." / PROFILE: / SWAP_API:
grep -hoE '[A-Z_]+[:=]"[a-z]+://[^"]*"' $TMP/*.js

# Endpunkt-Builder: NAME:({args})=>{let x=new URL("/pfad",t.CLIENT)
grep -hoE '[A-Z_0-9]+:\([^)]*\)=>\{let [a-z]=new URL\("[^"]*",[a-zA-Z._]+\)' $TMP/*.js

# Target-Erklaerung vom Server: falsche Werte liefern die erlaubten
grep -hoE '"message":"[^"]*must be one of[^"]*"' ...
```

## Procedure

1. **App + Daten bestaetigen** - `web_extract <seiten-url>`. Die Antwort ist
   zugleich Datenquelle (SSR) und Beweis, dass es die Ansicht gibt.
2. **Verbindung vom Rechner testen** - Kommandos als Skript per `write_file`
   nach `cache/blocked-scripts/` (grosse Einzeiler blockt der Parser), dann
   `bash <pfad>` im `terminal`. HTTP-Status pruefen: `530` = Cloudflare
   blockt die API-Subdomain, `1016`/DNS = Host existiert nicht mehr.
3. **API-Hosts aus dem HTML** - `grep -oE 'https?://[a-zA-Z0-9.-]+'` und
   sortieren. Neben dem Haupt-Domain stehen da die API-Subdomains
   (`frontend-api-v3.…`, `profile-api.…`, `swap-api.…` - typische Namen).
4. **JS-Chunks laden** - URL-Liste aus `src="..._next/static/..."` ziehen,
   jede laden, Dateien < 8 KB verwerfen (Polyfills, Utilities).
   Query-Strings (`?dpl=…`) VOR dem Speichern abtrennen: ein Dateiname mit
   `?` bricht jede spaetere Verarbeitung.
5. **Basis + Endpunkt-Builder greppen** - `CLIENT:"https://…"` nennt die
   Basis; `new URL("/pfad", t.CLIENT)` den Pfad. Der Builder-Name sagt,
   was der Endpunkt liefert (`PNL_LEADERBOARD`, `PORTFOLIO`).
6. **Endpunkte probieren** - gezielte curl-Aufrufe mit plausiblen Parametern.
   Server-Validierung als Bibel: Fehler „must be one of: daily, weekly,
   monthly“ zaelt die erlaubten Werte auf - die Fehlermeldung IST die Doku.
7. **Feldnamen normalisieren** - gleiches Feld, andere Schreibweise je
   Endpunkt (`priceUSD` vs `priceUsd`) - in lesen.py beide abdecken und per
   Test belegen. Ergebnis-Objekte nach chainId/Symbol filtern (eine
   Rangliste kann mehrere Ketten mischen).
8. **Gegen den Screenshot/Nutzerbeleg pruefen** - die gefundenen Zahlen
   muessen mit dem passen, was der Nutzer sieht.

## Pitfalls

- **Alte Hosts nicht erinnern, sondern neu finden.** `frontend-api.pump.fun`
  war tot (DNS 1016), die App nutzt `frontend-api-v3.pump.fun`. Der Hostname
  steht im HTML, nicht in der Erinnerung.
- **Native curl vs MSYS-/tmp:** natives Windows-curl schreibt nach
  `C:\Users\…\AppData\Local\Temp`, bash liest sein eigenes `/tmp` - ein
  `grep /tmp/datei` nach `curl -o /tmp/datei` findet nichts, wenn curl
  nativer Windows-build ist. Immer explizite Windows-Pfade verwenden.
- **Chunk-URLs mit Query-String:** `basename` zerlegt sie falsch; mit
  fortlaufender Nummer speichern (`c_$i.js`).
- **Cloudflare-530 auf API-Subdomains bei funktionierender Haupt-Domain:**
  normal fuer Rechenzentren. Aus der Residential-IP laeuft die Haupt-Domain;
  einzelne API-Pfade (z. B. `GET /users/…`) koennen trotzdem durchkommen.
- **Browser-Backend haengt:** nicht endlos neu versuchen - nach 1-2
  Fehlschlaege auf curl-Skripte wechseln; die Sondierung braucht keinen
  Browser.
- **Server-gerenderte Daten sind kostenlos:** wenn die Liste schon im HTML
  steht, braucht es fuer den ersten Kontakt keinen API-Abruf.
- **POST kann lesend sein:** ein Batch-Trades-Endpunkt war `POST` trotz
  reiner Lese-Semantik - beim Einbau in eine Papierspur die Whitelist als
  (Host, Methode)-Paar fuehren (Muster: kopier/lesen.py).

## Verification

Ein Probe-Aufruf des entdeckten Endpunkts liefert HTTP 200 mit JSON, dessen
Werte zur sichtbaren App-Seite passen:

```
curl -s -m 20 -A "$UA" \
  "https://frontend-api-v3.pump.fun/pnl-leaderboard?period=daily&sort=combined&limit=3"
# -> {"entries":[{rank,walletAddress,username,pnlUsd,...}]} - und die
#    Usernamen/PnL decken sich mit dem, was die App zeigt.
```

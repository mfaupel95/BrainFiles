# OKX-MCP

Dritter selbst gebauter MCP-Server (nach `archiv/` und `kraken/`). Bindet
Max' OKX-Konto (Spot, Margin, Futures/Swap, Grid-Bots) über die REST-API v5 an.

Angelegt am 02.09.2026.

## Zugangsdaten

Drei Werte, OKX braucht anders als Kraken zusätzlich eine Passphrase:

| Variable | Inhalt bei OKX |
|---|---|
| `OKX_API_KEY` | „API Key" |
| `OKX_API_SECRET` | „Secret Key" |
| `OKX_API_PASSPHRASE` | Die Passphrase, die beim Anlegen des Keys selbst vergeben wurde |

Jede der drei Variablen wird beim Aufruf frisch (kein Caching) in dieser
Reihenfolge gesucht — die erste Quelle mit einem echten Wert gewinnt:

1. **Prozess-Umgebungsvariable** — nur relevant, falls der Server je mit
   `env` in `claude_desktop_config.json` gestartet wird.
2. **Zentrale `.env`-Datei** unter `%USERPROFILE%\.env`
   (`C:\Users\faupe\.env`) — Max' zentraler Sammelpunkt für alle API-Keys
   über mehrere Tools hinweg. Einfache `KEY=WERT`-Zeilen, `#` für
   Kommentare.
3. **Windows-Registry** (`HKCU\Environment`, dieselbe Stelle, an der
   `setx`/die Windows-Umgebungsvariablen-Oberfläche schreiben) — Fallback
   für Altwerte, falls die `.env`-Datei (noch) nichts Brauchbares enthält.

Platzhalterzeilen wie `OKX_API_KEY=<YOUR_OKX_API_KEY_HERE>` zählen dabei
**nicht** als gesetzt — sie werden übersprungen, damit ein unausgefüllter
Platzhalter in der `.env`-Datei keinen echten Wert aus der Registry
verdeckt. `okx_status` zeigt unter `"quellen"` an, welche der drei Quellen
für jede Variable gerade tatsächlich greift, ohne den Wert selbst
preiszugeben.

Optional: `OKX_DEMO=1` (über dieselben drei Quellen) schaltet alle privaten
Aufrufe auf OKX' simulierte Handelsumgebung um (braucht einen eigenen
Demo-API-Key aus dem Demo-Trading-Bereich der OKX-App) – gut zum Testen ohne
echtes Geld.

Die Werte stehen **nicht** im Vault, nicht in `claude_desktop_config.json`
und in keiner Ausgabe dieses Servers — auch nicht gekürzt. `okx_status`
meldet nur, *ob* sie gesetzt sind, *woher* sie kämen und ob OKX sie
akzeptiert.

Bei Registry-Werten muss **Claude Desktop neu gestartet** werden, damit eine
Änderung greift (ein laufender Prozess erbt neu gesetzte
Windows-Umgebungsvariablen nicht). Bei der `.env`-Datei genügt es, den
Server neu aufzurufen — sie wird bei jedem Zugriff neu gelesen.


## Rechte am OKX-Schlüssel

Beim Anlegen des API-Keys in der OKX-App (Profil → API) ankreuzen:

- **Lesen** (Read) — Pflicht für alle lesenden Werkzeuge.
- **Traden** (Trade) — nötig für `okx_order_aufgeben`, `okx_order_stornieren`,
  `okx_grid_bot_stoppen`.

**Nicht ankreuzen: „Withdraw" / Auszahlen.** Dieser Server implementiert
bewusst kein Auszahlungs-Werkzeug — selbst wenn das Recht gesetzt wäre, gäbe
es hier keinen Weg dorthin.

Empfehlung: IP-Whitelist auf diesen Rechner setzen, wenn OKX das anbietet —
schützt zusätzlich, falls der Schlüssel je durchsickert.

## Werkzeuge

**Ohne Schlüssel (öffentlich):**

| Werkzeug | Zweck |
|---|---|
| `okx_kurs` | Letzter Kurs, Geld/Brief, Hoch/Tief, Volumen |
| `okx_paare_suchen` | OKX-Instrumenten-IDs finden (Spot/Margin/Swap/Futures/Option) |
| `okx_candles` | OHLCV-Kerzen, 1 Minute bis 1 Monat |

**Mit Schlüssel (lesend, braucht „Lesen"):**

| Werkzeug | Zweck |
|---|---|
| `okx_status` | Prüft nur die Anbindung |
| `okx_guthaben` | Trading-Konto-Bestände je Währung |
| `okx_positionen` | Offene Margin/Swap/Futures-Positionen inkl. PnL, Hebel, Liq.-Preis |
| `okx_offene_orders` | Alle offenen regulären Orders |
| `okx_geschlossene_orders` | Zuletzt geschlossene/stornierte Orders (7 Tage) |
| `okx_trades` | Tatsächlich ausgeführte Fills |
| `okx_grid_bots` | Status aller Grid-Bots (Spot- und Futures-Grid), laufend + Verlauf |

**Mit Schlüssel (schreibend, braucht „Traden"):**

| Werkzeug | Verhalten |
|---|---|
| `okx_order_aufgeben` | **Standard: nur Entwurf.** OKX kennt anders als Kraken keinen serverseitigen Prüfmodus — bei `echt_ausfuehren=False` wird die Order nur zusammengebaut und der Marktpreis dazugestellt, es geht NICHTS an OKX raus. Erst `echt_ausfuehren=True` platziert wirklich — diesen Schritt macht Max. |
| `okx_order_stornieren` | Storniert eine offene Order. |
| `okx_grid_bot_stoppen` | Stoppt einen laufenden Grid-Bot. Legt **keinen** neuen an. |

## Bewusst nicht enthalten

- **Auszahlungen** — kein Werkzeug dafür, unabhängig vom Schlüsselrecht.
- **Neuen Grid-Bot anlegen** — zu viele Parameter (Range, Grid-Anzahl,
  Investition, Hebel, Long/Short/Neutral), um das blind per Tool-Aufruf zu
  tun. Bots weiterhin über die OKX-App anlegen; dieser Server liest ihren
  Status und kann sie stoppen.

## Testen

```
.venv\Scripts\python.exe okx_mcp.py
npx -y @modelcontextprotocol/inspector .venv\Scripts\python.exe okx_mcp.py
```

Ohne gesetzte Umgebungsvariablen starten die öffentlichen Werkzeuge trotzdem —
nur die privaten melden dann, dass die Variablen fehlen.

## Fallstricke

- **Fehler stecken im JSON-Feld `code`** (Anfrage-Ebene, `"0"` = ok) bzw. pro
  Order in `data[i].sCode` — auch wenn der HTTP-Status selbst schon 4xx ist
  (z. B. bei `50119 "API key doesn't exist"`, HTTP 401). Der Server liest
  den JSON-Body auch bei Fehlerstatus aus, statt nur den nackten HTTP-Fehler
  zu zeigen.
- **Zeitstempel-Toleranz ist eng** (~30 Sek.) — bei „Timestamp expired"
  zuerst die Systemuhr des Rechners prüfen.
- **`tdMode`** muss zum Kontotyp passen: `cash` für Spot, `cross`/`isolated`
  für Margin/Swap/Futures. Falscher Modus → Order wird abgelehnt.
- Secret wird bei OKX **nicht** base64-dekodiert (anders als bei Kraken) —
  direkt als UTF-8-Bytes für den HMAC verwendet. Bei eigenen Änderungen daran
  denken.

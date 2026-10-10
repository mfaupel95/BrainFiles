# Desktop-Verbindungsfehler: ECONNRESET / 500-Flut auf `/api/*`

Symptome (Electron-Konsole bzw. `logs/desktop.log`):

| Meldung | Bedeutung |
|---|---|
| `Error: read ECONNRESET` bei `[hermes:api <METHOD> <pfad>]` | Electron-Main verlor die HTTP-Verbindung zum Backend waehrend des Lesens — fast immer Folge einer 500-Flut, selten ein eigener Fehler |
| gleiche 500-Zeile alle ~2 s | Polling-Endpoint: der Desktop fragt `/api/local-models/status` im 2-s-Takt; die wiederholte Zeile IST die Quelle |
| `Timed out connecting to Hermes backend after 30000ms` | Backend antwortet nicht mehr (ueberlastet/haengt) — Nachhall des Verbindungsabbruchs, kein zweiter Fehler |

## Diagnose-Reihenfolge

1. **Gateway gesund?** `gateway_state.json` — `running` + Plattformen `connected` heisst: die
   Ursache sitzt im Desktop-Backend-Pfad, nicht im Gateway (ein Gateway-Restart hilft dann
   nicht).
2. **Die 500-Flut finden:** `grep -n "hermes:api.*Error" logs/desktop.log | tail`. Der eine
   Request mit ECONNRESET im selben Zeitfenster ist die Folge, nicht die Ursache.
3. **Fuer `GET /api/local-models/status` (bekannte Quelle):** der Endpoint
   (`hermes_cli/web_routers/local_models.py`, `_staged_row`) macht `stat()` auf jede stagede
   GGUF in `Agenten/Hermes/models/`. Ein Symlink, dessen Ziel fehlt, wirft dort ungefangen
   FileNotFoundError -> 500. Pruefen: `ls -la Agenten/Hermes/models/` (tote Links erscheinen
   als `lrwxrwxrwx`), Ziel mit `test -e <ziel>` / `readlink` gegenpruefen. `preset skip …`-
   Meldungen sind NICHT die Ursache — `preset_for_model` faengt Header-Fehler und gibt
   `None` zurueck; die Warnung steht nur, weil der llama-server die Datei nicht lesen kann.
4. **Fix:** den toten Symlink loeschen. Der Katalogeintrag bleibt als klickbares Modell im
   Picker stehen und legt die Datei beim Download neu an — kein Katalog-Eingriff noetig.
5. **Nachweis ohne Auth-Token:** die API antwortet sonst 401. Der Desktop poollt selbst:
   keine NEUEN `hermes:api … Error`-Zeilen NACH dem Fix (Zeitstempel vergleichen, ~2-s-
   Rhythmus) ist der Beleg, nicht ein `curl`-Status.

## Harmlose Nachbarn (KEINE Reparatur)

- `preset skip Ternary-Bonsai-…gguf: unknown ggml tensor type 143` — der VERWALTETE
  llama-server (18434) kann ternäre Gewichte nicht laden; Bonsai laeuft separat (eigener
  Server auf 8080), die Warnung ist erwartet.
- MCP-Test-500er (`POST /api/mcp/servers/<name>/test`) — Test-Klick auf einen nicht
  angemeldeten MCP-Server (algolia/robinhood/postman …), normales „nicht konfiguriert".

## models/-Ordner aufraeumen: Katalogeintrag, Symlink, Router-Slug — drei verschiedene Dinge

Vor jeder Frage „brauchen wir dieses Modell noch?" die drei Schichten trennen —
Grep-Treffer auf den Modellnamen sagen sonst nichts:

- **Katalogeintrag** (`hermes_cli/local_runtime/catalog.json`): committeter Hermes-Quelltext,
  der Picker zeigt ihn als klickbaren Download (z.B. Qwen3.6-35B mit 22,6 GB). Loeschen
  waere eine Checkout-Modifikation, die der naechste `hermes update` ueberschreibt — lassen;
  der Eintrag allein laedt nichts und verursacht keinen Fehler.
- **Symlink in `Agenten/Hermes/models/`**: nur diese Dateien zaehlt der Status-Endpoint beim
  `stat()` (tote Links -> 500). Ein Link zeigt meist auf die echte Datei unter
  `O:\Modelle\GGUF\`. Vor dem Loeschen pruefen, WER den Pfad liest: der Bonsai-Starter
  `bonsai-27b.ps1` laedt direkt von `O:\Modelle\GGUF\…` (eigene `$Modell`-Variable), NICHT
  durch den models/-Link — den Link kann man entfernen, die echte Datei bleibt und der
  Dienst startet unveraendert.
- **Config-Referenz `qwen/qwen3.6-35b-a3b`** (config.yaml, profiles/*/config.yaml): das ist
  ein ROUTER-SLUG (Cloud ueber den qwen-Provider), kein Verweis auf das lokale GGUF. Ein
  Treffer in configs beweist NICHT, dass die lokale Datei benutzt wird.

Entscheidungsweg: (1) referenziert irgendwer die LOCALE Datei (meist niemand — die
Handels-Spuren laufen ueber Ollama bzw. Bonsai, nicht ueber den verwalteten llama-server)?
(2) ist der Katalogeintrag Checkout-Quelltext (committet = Standard, lassen)? (3) passt die
Dateigroesse in den VRAM (22,6 GB Q4 auf einer 8-GB-Karte = kein Download anstossen)? Erst
dann einen Symlink loeschen — und die Wirkung mit einem Beobachtungsfenster belegen: die
`preset skip`-Warnzeilen in errors.log haben ihre eigenen Zeitstempel, neue duerfen NACH dem
Loeschen nicht mehr kommen (Anzahl vorher/nachher vergleichen, Uhrzeitquelle je Log-Datei
nicht mischen — Desktop-Log, errors.log und die Sandbox-Uhr koennen verschiedene Zeiten
zeigen).

## Telemetry-Ordner blockiert (shared_metrics)

`telemetry/shared_metrics/` kann so kaputte Rechte tragen, dass selbst der eigene Benutzer
`WinError 5` auf lesen UND loeschen bekommt (ein Prozess mit fremdem Kontext hat ihn
angelegt); Hermes loggt dann laufend `shared metrics initialization failed`. Die Warnung ist
harmlos (Telemetrie degradiert), aber der Log-Rauschen bleibt bis zur Reparatur.

Reparatur in EINEM erhoehten Lauf (UAC, Skript schreibt sein eigenes Log per `Set-Content`):

    icacls <pfad> /grant <user>:(OI)(CI)F /T /C

Das genuegt — kein `takeown` noetig (`takeown /D Y` ist ohnehin ungueltige Syntax, das ist
kein Teilfehler). Fehlerzeilen im Log des elevated Skripts (z.B. takeown) heissen NICHT,
dass der Fix fehlschlug — das Ergebnis am ZIEL lesend belegen (`ls`, `Test-Path`,
`icacls` ohne Fehler) und erst dann „repariert" melden.

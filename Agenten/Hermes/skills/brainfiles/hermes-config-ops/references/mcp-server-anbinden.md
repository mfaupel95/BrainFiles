# Fremden MCP-Server anbinden (HTTP/OAuth)

Nicht der Manifest-Abgleich (den macht `mcp-sync`), sondern die Frage „geht
dieser Anbieter ueberhaupt, und mit welchem Befehl".

1. **Erst den Handschlag pruefen, ohne Zugang.** Ein HTTP-MCP-Endpunkt ist
   read-only in Minuten pruefbar: `POST` auf die URL mit
   `Content-Type: application/json` und
   `Accept: application/json, text/event-stream`, Rumpf
   `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{...}}}`.
   Die Antwort nennt `serverInfo` und eine `mcp-session-id` — letztere bei
   `tools/list` und `tools/call` als Header mitschicken. Typisches Bild:
   `initialize` und `tools/list` antworten **ohne** Anmeldung, erst
   `tools/call` kommt als `401` mit
   `WWW-Authenticate: Bearer resource_metadata=...` → **OAuth**.
2. **Anbinden nur ueber Hermes-Kommandos, nie per YAML.** `hermes mcp add
   <name> --url <url> --auth oauth` (statischer Header: `--auth header`),
   danach `hermes mcp login <name>`; `hermes mcp --help` fuehrt zusaetzlich
   `reauth`, `list`, `test`, `configure`. Der Token kommt ausschliesslich ueber
   diesen Weg.
3. **`hermes mcp add`/`remove` stellen MEHRERE Prompts — ein einzelnes
   `printf 'Y\n'` reicht nicht.** Die Rueckfragen (Anlegen/Ueberschreiben,
   "Enable all N tools?", bei `remove` "Remove server?") kommen nacheinander;
   ein einzelnes Y beantwortet nur den ersten, der naechste Prompt bekommt EOF
   und der Aufruf endet mit `Cancelled` **ohne** zu schreiben. Der Eintrag in
   `config.yaml` bleibt dann der ALTSTAND — und `hermes mcp test` meldet trotzdem
   "✓ Connected", weil es den alten Eintrag testet. Falscher gruener Nachweis:
   nach einem `Cancelled` ist die Verbindung zu einem ANDEREN Ziel belegt.
   `yes |` (unendlicher Y-Strom) beantwortet alle Prompts. Danach IMMER die
   gespeicherte Config lesen und den `--db`/`--url`-Pfad gegen die Absicht
   halten (bei Bots je Profil `profiles/<bot>/config.yaml`), nicht nur auf
   "Connected" vertrauen.
4. **Der Anmeldeschritt gehoert dem Nutzer.** OAuth laeuft im Browser gegen
   SEIN Konto und laesst sich von einem Agenten nicht abschliessen — als
   offenen Schritt melden („Kandidat, ein Klick fehlt"), nie als erledigt.
5. **Im Ergebnis trennen, was live geprueft ist und was aus der Doku stammt.**
   Handschlag und Werkzeugliste sind pruefbar; Metriknamen, Feldlisten und
   Tarifgrenzen stehen oft nur in der Anbieter-Doku. Beides ausdruecklich
   benennen — ein „funktioniert" ohne diese Trennung ist eine Behauptung.
6. **Erst danach der Manifest-Eintrag**, und als Kandidat mit Begruendung:
   `mcp-sync`.

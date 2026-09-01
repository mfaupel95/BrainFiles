# Archiv-MCP

Stellt Max' Dateiarchiv als MCP-Server bereit — damit ist die Volltextsuche
nicht mehr nur über den Skill `archiv` in Claude Code erreichbar, sondern über
jeden MCP-fähigen Client.

## Werkzeuge

| Werkzeug | Zweck |
|---|---|
| `archiv_suchen` | Volltextsuche, optional auf eine Kategorie eingeschränkt |
| `archiv_datei_lesen` | indexierter Volltext einer Datei aus einem Treffer |
| `archiv_statistik` | Umfang und Alter des Index |
| `posteingang_stand` | was unversorgt in `Posteingang/` liegt |

## Bewusst nur lesend

Der Server öffnet die Datenbank mit `mode=ro` und kann weder einsortieren noch
löschen noch neu indexieren. Das bleibt bei `sort_inbox.py` und `index.py`,
wo Max den Lauf sieht.

`archiv_datei_lesen` gibt **den indexierten Text** zurück, nicht die Datei von
der Platte. Ein Pfad, der nicht im Index steht, wird abgewiesen — das Werkzeug
kann also keine beliebige Datei vom Rechner ausgeben.

## Betrieb

Der Server liest `../../../MaxHirn/Archiv/ArchivSuche/archiv_index.db`, relativ
zu dieser Datei aufgelöst (bzw. `%MAXHIRN_VAULT%/Archiv/…`, wenn gesetzt). Ein Umzug des Vaults ändert daran nichts; nur die Umgebung
muss danach einmal neu gebaut werden:

```
uv sync
```

Starten (stdio):

```
.venv\Scripts\python.exe archiv_mcp.py
```

Prüfen:

```
npx -y @modelcontextprotocol/inspector .venv\Scripts\python.exe archiv_mcp.py
```

## Registrierung

Eingetragen in `Archiv/.mcp.json` als `archiv`. Nach dem Eintragen muss Claude
neu gestartet werden; die Verbindung lässt sich dann mit `/mcp` prüfen.

## Zwei Fallstricke

- **`stdout` gehört dem Protokoll.** Ein `print()` zum Debuggen zerstört die
  JSON-RPC-Verbindung; der Fehler sieht dann aus wie ein Verbindungsabbruch.
  Diagnoseausgaben deshalb ausschließlich nach `stderr`.
- **Das MCP-SDK hat mit Version 2 die API umbenannt** — `FastMCP` heißt jetzt
  `MCPServer` und liegt unter `mcp.server.mcpserver`. Anleitungen im Netz zeigen
  überwiegend noch die alte 1.x-Form.

## Stand

Geprüft am 2026-08-13 gegen den echten Index: 7566 Dateien
(3645 Dokumente, 2927 Bilder, 907 Musik, 87 Videos), davon 3810 per OCR
erschlossen. Index zuletzt gebaut am 2026-08-08.

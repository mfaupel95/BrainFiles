# Betrieb: Wartung, Sicherung, Kommandokarte

## Taegliche Wache im Haus

- Hermes-Cron `gbrain-maintenance` (Job `f8137b52e0ac`, `no_agent`, taeglich `0 6 * * *`,
  Ausgabe nach `all`), Skript `Agenten/Hermes/scripts/gbrain-maintenance-wache.py`.
- Sie faehrt `wsl.exe -d archlinux /workspace/gbrain/bin/gbrain doctor --fast --json`
  und meldet NUR echte Fehler; leere Ausgabe heisst alles gut.
- Warnungen wie `serve IPC socket not present` sind bei einer reinen CLI-Installation der
  NORMALFALL (gemessen 02.10.2026: `status: warnings`, `health_score: 90`,
  `brain_checks_score: 100`, 73 Skills erreichbar) - kein Fehler.
- Die Installation verlangt genau EINE native Routine mit der Kennung
  `gbrain-maintenance-2e8fa54d-6f9f-4726-89e9-caf8a624b61a`; mehr wird nicht angelegt.

## Kein Dienst (Entscheidung Max, 01.10.2026)

`serve`, `cron` und Daemons werden NICHT gestartet - die Installation verbietet es
ausdruecklich (`instructions/maintenance.md`: "Do not start serve, cron, or a daemon.").
Bei einem Ausfall wird wiederholt. Erst wenn Schreiben mehrfach hintereinander
scheitert, ist der Dienst die richtige Antwort. Diese Frage nicht erneut stellen.

## Sicherung und Wiederherstellung (Anweisung der Installation)

```
gbrain backup create --output /absolute/private/path/unique.gbrain-backup
    # andere Schreiber vorher anhalten; das Elternverzeichnis muss existieren
    # Archive enthalten den vollen Datenbankzustand, moeglicherweise Zugangsdaten
gbrain backup restore /absolute/path/archive.gbrain-backup --into /absolute/new-root
    # ersetzt NIE eine vorhandene Wurzel und quarantaeniert unfertige Jobs
```

Nach einer Wiederherstellung: Laufzeit mit dem Setup-Helfer neu einrichten,
ausgeschlossene Zugangsdienste neu verbinden, die Routine erst nach der Pruefung wieder
anhaengen. **Keine Automatik startet bei einer Wiederherstellung von selbst.**
Abdeckungspruefungen und Markdown-Exporte sind KEINE vollstaendigen Sicherungen.

## Was ein Fakt wert ist (gemessen 02.10.2026)

GBrain ist das Gehirn fuer BELEGTE Aussagen, nicht fuer Laufzeitstaende.

**Speichern:**
- Messergebnisse mit Datum und Beleg (Commit, Cache-Pfad, Log) - z. B. "rollierender
  Backtest: 17/22 Fenster positiv, Summe -295 USD".
- Entscheidungen von Max mit seinem Wortlaut als Anker ("Hebel 7", "auto freigabe erlaubt").
- Offene Aufgabennummern (T-291, T-292) NUR mit einem Stichwort, nie der ganze Task-Text -
  `MaxHirn/Archiv/TASKS.md` ist die Quelle.

**Nicht speichern:** aktuelle Positions- oder Guthabenzahlen (aus der `wachen.json`
nachlesbar), Zykluslogs, alles, was eine Auswertung jederzeit neu rechnet. Ein Fakt, dem
in drei Wochen niemand den Beleg mehr zuordnen kann, ist Ballast.

## Kommandokarte der Installation (gbrain 0.51.0.0)

Hilfetext in Abschnitte gegliedert; die fuer Memory-Arbeit wichtigen Befehle:

| Zweck | Befehl |
|---|---|
| Fakt schreiben | `remember <fact> --provenance ... [--entity ...]` |
| Fakt lesen | `recall --grep <wort>` / `recall "<entitaet>"` |
| Fakt zuruecknehmen | `forget <fact-id> --reason <text>` |
| Zustand | `doctor [--json] [--fast] [--probe-pglite]`, `stats`, `health` |
| Engine | `engine status [--json] [--probe]`, `db-repair [--yes] [--json]` |
| Seiten | `get <slug>`, `put <slug>`, `list [--type T] [--limit N]` |
| Seitensuche | `search <query>`, `query <question> [--no-expand]`, `ask` (Alias) |
| Import/Sync | `import <dir> [--no-embed]`, `sync [--source <id>]` |
| Embeddings | `embed [<slug>\|--all\|--stale]`, `migrate embeddings --to <p:model>` |
| Quellen | `sources ...` (Frueher `repos`, seit v0.19.0 abgeloest) |
| Code | `code-def`, `code-refs`, `code-callers`, `code-callees`, `reindex-code` |
| Verwaltung | `config [show\|get\|set]`, `history <slug>`, `revert <slug> <version-id>` |
| MCP | `serve [--surface verbs\|starter\|full]`, `serve --http [--port N]` |
| Wartung | `doctor`, `backup create/restore`, `upgrade`, `check-update` |

`gbrain <command> --help` gibt es nur fuer einen Teil der Befehle - `recall` und `forget`
antworten mit einem Stub, der auf den Haupt-Hilfetext verweist.

## Weitere Anweisungen der Installation (im WSL lesbar)

- `/workspace/gbrain/instructions/gbrain-skill.md` - Bedienregeln (siehe
  `references/lesen-und-korrigieren.md`).
- `/workspace/gbrain/instructions/maintenance.md` - Routine, Sicherung, Verbote.
- `/workspace/gbrain/.gbrain/agent-install/receipt.json` - Empfangsbestaetigung
  (Zustand `ready`).

# Sitzungsspeicher aufraeumen (archivierte Gespräche loeschen)

Auftrag dieser Referenz: `state.db` verkleinern, indem archivierte (= weich ausgeblendete)
Sitzungen endgueltig weggehen. Der Auftrag ist die **Dateigroesse**, nicht die Zeilenzahl.

## Was "archiviert" bedeutet

`hermes sessions archive` setzt nur `sessions.archived = 1` — die Sitzung ist aus den Listen
weg, aber voll rueckrufbar. Genau das ist der Unterschied zum gewuenschten Loeschen, und die
Ueberschaetzung geht in beide Richtungen: wer `archived` zaehlt, glaubt, es sei schon weg.

    python - <<'PY'
    import sqlite3
    c = sqlite3.connect("file:$HERMES_HOME/state.db?mode=ro", uri=True)
    print("Sessions gesamt/archiviert:", c.execute(
        "select count(*), sum(archived) from sessions").fetchone())
    print("Nachrichten in archivierten:", c.execute(
        "select count(*) from messages where session_id in"
        " (select id from sessions where archived=1)").fetchone()[0])
    print("pin/hidden:", c.execute(
        "select id, hidden, pinned, title from sessions"
        " where pinned=1 or hidden=1").fetchall())
    PY

Alles ueber `mode=ro` lesen — nie mit einem Schreibzugriff auf `state.db` messen, waehrend
Agenten darauf laufen. `sessions/request_dump_*.json` ist eine **andere** Sache (Debug-Dumps,
Groessenordnung zig MB, `du -sh sessions`) und wird von keinem Prune beruehrt.

## Ausnahmen zuerst sichern

Zwei Gruppen ueberleben einen Prune nicht von selbst:

- `hidden = 1` (Bot-Chat-Zeilen) — der Prune sieht nur `archived`.
- `pinned = 1` — `pin` ist der dauerhafte Keep-Haken; `_note_pinned_skipped` meldet sie nur.

Also vor dem Lauf beide Ausnahmen **`hermes sessions pin <id>`** geben (der Pin gilt dann auch
fuer die automatische Archiv-Umlaufregel). `--include-pinned` wuerde sie mitloeschen — das ist
eine Entscheidung des Nutzers, keine Voreinstelle des Werkzeugs.

## Backup

Die Datei ist offen (WAL). Ein `shutil.copy` liefert Zufallsdaten, wenn der WAL-Checkpoint
gerade laeuft. Nutze die SQLite-Backup-API:

    python - <<'PY'
    import sqlite3, datetime as dt, os
    ziel = f".sicherung/state.db.bak-pre-prune-{dt.datetime.now():%Y%m%d-%H%M%S}"
    s = sqlite3.connect("file:state.db?mode=ro", uri=True)
    d = sqlite3.connect(ziel); s.backup(d); d.close(); s.close()
    print(os.path.abspath(ziel), os.path.getsize(ziel))
    PY

## Grenze waehlen (das ist eine Nutzerentscheidung)

| Kommando | Wirkung |
|---|---|
| `prune` (blank) | Vorgabe 90 Tage |
| `prune --include-archived` | archived-Zeilen werden ueberhaupt erst Kandidaten |
| `prune --older-than 7d` | nur was aelter als 7 Tage **zuletzt aktiv** war |
| `prune --source cron --include-archived` | JEDER Filter **hebt** die 90-Tage-Vorgabe auf |

`--older-than` misst die **letzte Aktivitaet**, nicht das Startdatum — eine lang laufende,
heute benutzte Sitzung faellt darunter nicht. Trockenlauf zuerst, immer:

    hermes sessions prune --include-archived --older-than 7d --dry-run

und die Ausnahmezeilen pruefen, nicht nur die Zahl:

    hermes sessions prune --include-archived --older-than 7d --dry-run | grep -i "<titel>"

leer heisst: gerettet.

## Writer stoppen (der Punkt, an dem es scheitert)

    hermes sessions prune --include-archived --older-than 7d --yes

    PID 12345 (python.exe -m hermes_cli.main -p default --cli …): state.db
    Rewriting the database under a live writer is how every agent ends up refusing turns …
    Stop them first (`hermes gateway stop`, quit the Desktop app, pause cron), then re-run.

Halter sind typischerweise: der Gateway (`tools/python-…\.exe -I -c runpy …`), **jede** laufende
TUI/CLI-Kindsitzung und das Dashboard/serve-Backend. Prozessbild holen ueber
`Get-CimInstance Win32_Process -Filter "Name='python.exe' or Name='pythonw.exe' or Name='Hermes.exe'"`
und nach `state.db`/Gateway-Kommandozeile filtern — **nicht** nach PID, die wird nach Nutzung
wiederverwendet. `hermes pause` raeumt cron und Kanban-Dispatch mit; danach die Kandidaten noch
einmal gegen den Pin-Stand pruefen und erst dann stoppen.

Reihenfolge danach: Prune → **`hermes sessions optimize`** (FTS-Merge + VACUUM + WAL-Checkpoint;
`--force` auch hier weglassen) → `hermes gateway start` → `hermes sessions stats`.

## Belege

    hermes sessions stats                # Sessions/Messages/Database size
    python -c "import sqlite3;c=sqlite3.connect('state.db');print(c.execute('pragma freelist_count').fetchone())"
    ls -l state.db

Der Dateinamen-Zeitstempel ist der beste Beleg: nach VACUUM muss die Datei kleiner sein, nicht
nur die `page_count`. Bleibt sie gleich, hat der VACUUM nicht stattgefunden (Writer, oder
`optimize` wurde übersprungen) — nicht die geloeschten Sitzungen sind dann der Befund.

## Fallen

- **`--force` ist keine Loesung — ausser fuer `prune` allein.** Der Wächter existiert, weil
  ein Rewrite unter aktivem Schreiber in retired-WAL-Fehler für alle Agenten endet. Aber
  `prune` loescht nur Zeilen in einer Transaktion und ueberspringt offene Sitzungen per
  Turn-Lease (`exclude_active_write_guards=True`) — wenn man IN einer TUI/CLI-Sitzung sitzt
  und die eigene Session nicht stoppen kann, ist `prune --force` der pragmatische Weg und
  laeuft sauber (gemessen 05.10.2026: 240 Sessions, FTS danach konsistent). Das Risiko liegt
  in `optimize`/VACUUM, das Exklusivzugriff braucht — das unter Last NICHT mit `--force`
  fahren, sondern als eigenen Schritt, wenn die Writer weg sind, oder offen lassen (die
  Freelist-Seiten werden wiederverwendet, die Datei schrumpft nur nicht).
- **Nach dem Prune sofort optimieren.** Ohne VACUUM bleibt die Datei so gross wie vorher; wer
  nur die Zahl der Zeilen ansieht, meldet Erfolg ohne Wirkung.
- **`sessions delete <id>` ist nicht von der Halter-Sperre betroffen** — fuer einen einzelnen
  Notrefall (Sitzung mit Secrets) ist das der schnellere Weg, aber es umgeht die Sicherung:
  vorher pinnen ist kein Schutz, sondern das Gegenteil.
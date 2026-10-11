# Hermes-Sitzungsspeicher: offene Sitzungen lesen, pruefen, abschliessen

Gedistillt aus `hermes-agent/hermes_state_sessions.py`, `hermes_cli/sessions_cmd.py`,
`hermes_cli/foreign_sessions.py` und dem Live-Speicher (Stand 18.09.2026).
Laden mit `skill_view(name='sammelauftrag', file_path='references/sitzungsspeicher.md')`.

## Wo der Speicher liegt

- **Default-Profil:** `Agenten/Hermes/state.db` (SQLite).
- **Jedes Bot-Profil hat eine eigene DB:** `Agenten/Hermes/profiles/<name>/state.db`.
  Ein Sweep nur ueber die Default-DB sieht die Bot-Sitzungen nicht.
- Nur lesend oeffnen: `sqlite3.connect("file:<pfad>?mode=ro", uri=True)`.
  Ein fehlendes `-wal` ist kein Fehler.

## Tabelle `sessions` (relevante Spalten)

| Spalte | Bedeutung |
|---|---|
| `id` | Sitzungskennung (z. B. `20260918_122648_98073785`, `bg_*` fuer Hintergrund) |
| `source` | `cli`, `telegram`, `tui`, `a2a`, `desktop`, `photon`, `subagent`, `tool` |
| `started_at` / `last_activity_at` | REAL-Epoch. `last_activity_at` ist die Frische-Quelle. |
| `ended_at` / `end_reason` | **`ended_at IS NULL` = offen.** `end_reason` sagt, WIE es endete. |
| `message_count` / `tool_call_count` | Umfang. `message_count=0` = reine Huelle (Gateway-Schluessel). |
| `archived` / `hidden` / `pinned` | `archived`=weich versteckt, `pinned`=Keep-Flag (nie automatisch archivieren), `hidden`=aus Listen. |
| `title` / `cwd` / `git_branch` | Kontext. `cwd` zeigt, woran gearbeitet wurde. |
| `profile_name` | Profil, dem die Sitzung gehoert. |

## Tabelle `messages`

- `id` ist **global ueber alle Sitzungen** — nie `WHERE session_id=… AND id>N` schneiden,
  das versteckt genau die gesuchten Zeilen. Pro `session_id` nach `timestamp` ordnen.
- `active=1` = lebender Verlauf, `active=0` = komprimierte Altstaende.
- Assistentenzeilen mit leerem `content` sind reine Werkzeugaufruf-Turns; die
  `role='tool'`-Zeile darunter zeigt, woran gearbeitet wurde.
- Die letzte Zeile einer abgebrochenen Sitzung ist oft ein Werkzeugergebnis ohne
  Nachsatz — der Assistent starb **vor** dem Bericht, nicht weil die Arbeit fehlte.

## `end_reason` — was endgueltig ist und was nicht

`hermes_state_common._RECOVERABLE_END_REASONS`:
`agent_close`, `ws_orphan_reap`, `superseded_by_resume`, `startup_orphan_reap`.
Diese Enden sind **wiederaufnahmefaehig**: die Sitzungswiederaufnahme holt die Zeile
zurueck. Sie sind „verlassen“, nicht „erledigt“.

Endgueltige Enden (Beispiele aus dem Live-Speicher): `session_reset`, `cli_close`,
`session_switch`, `new_session`, `tui_shutdown`, `cron_complete`.

**Konsequenz fuer den Abschluss:** eine Sitzung mit `ended_at IS NULL` ist offen;
eine mit wiederaufnahmefaehigem `end_reason` ist verlassen, aber nicht tot. Beide
sind Abschluss-Kandidaten, aber nur `archive` (weich) ist dafuer sicher — `prune`
loescht endgueltig.

## CLI-Oberflaeche (`hermes sessions …`)

Aufruf ueber das `terminal`-Werkzeug, vorher `PYTHONHOME`/`PYTHONPATH` entfernen:
`powershell -NoProfile -Command "Remove-Item Env:PYTHONHOME, Env:PYTHONPATH -ErrorAction SilentlyContinue; & 'Agenten/Hermes/bin/hermes.exe' sessions …"`

| Unterbefehl | Zweck |
|---|---|
| `list [--source S] [--limit N] [--workspace W]` | juengste Sitzungen (kann NICHT nach „offen“ filtern) |
| `archive [Filter] [--dry-run] [--yes]` | **weich verstecken** (umkehrbar, kein Datenverlust) |
| `prune [Filter] [--dry-run] [--yes]` | **loeschen**; schliesst Archivierte/Angeheftete nur mit `--include-archived`/`--include-pinned` ein |
| `prune --never-active [--older-than AGE]` | loescht Schluessel-Zeilen, die nie benutzt wurden (0 msgs/tokens/tools) |
| `pin` / `unpin` / `pinned` | Keep-Flag setzen/entfernen/auflisten |
| `rename` | Titel setzen |
| `export` | JSONL/Markdown/QMD exportieren |
| `import` | Claude-Code-/Codex-CLI-Sitzung importieren (einseitig) |
| `stats` | Speicherstatistik |
| `browse` | interaktiver Picker (browsen, suchen, fortsetzen) |

`archive`-Filter (gelten auch fuer `prune`): `--older-than AGE` (`5h`/`2d`/ISO),
`--newer-than`, `--before`/`--after`, `--source`, `--title`, `--end-reason`,
`--cwd`, `--min-/max-messages`, `--model`, `--provider`, `--user`, `--chat-id`,
`--chat-type`, `--branch`, `--min-/max-tokens`, `--min-/max-cost`,
`--min-/max-tool-calls`.

## Slash-Kommandos (in einer Sitzung)

- `/sessions` — browsen und fortsetzen.
- `/resume <name>` — benannte Sitzung fortsetzen.
- `/new` — neue Sitzung (frisches `session_id` + Historie).
- `/save` — aktuelle Unterhaltung exportieren.
- `/quit --delete` — CLI beenden und Sitzungshistorie entfernen.

## Abschluss-Semantik (aus dem Code)

- `end_session(session_id, end_reason)` setzt `ended_at`/`end_reason`; **der erste
  Endgrund gewinnt** (ein spaeteres `end_session` no-op auf einer schon beendeten Zeile).
- `reopen_session()` loescht `ended_at`/`end_reason` wieder (Wiederaufnahme).
- `promote_to_session_reset()` ist fuer Reset-Grenzen: es ueberschreibt auch
  wiederaufnahmefaehige Enden, damit die Wiederaufnahme die Zeile nicht zurueckholt.
- `archive_sessions()` = `set_session_archived(True)` je Kandidat, idempotent,
  **kein** `ended_at`-Stempel — Archiv und Ende sind unabhaengig.
- `maybe_auto_archive(idle_days=3)` archiviert automatisch Sitzungen, die 3 Tage
  inaktiv sind (ausser angeheftete); `state_meta.last_auto_archive` begrenzt die
  Laeufe. Das ist der Grund, warum „offen“ und „archiviert“ zusammen vorkommen.

## Fremde Sitzungen (Claude Code, Codex CLI)

- `hermes_cli/foreign_sessions.py` liest deren On-Disk-Speicher **nur lesend**
  (Quellen: `claude-code`, `codex-cli`).
- `hermes sessions import` zieht eine solche Sitzung EINSEITIG nach Hermes
  (erfuellt die Rollen-Alternation). Import ist kein Schliessen der Fremd-Sitzung.
- Max betreibt Claude und Hermes auf derselben Wissensschicht: die Claude-Sitzung
  selbst schliesst Hermes nicht — sie wird nur gelesen/importiert.

## Messwerte (Live, 18.09.2026, Default-Profil)

- 172 Sitzungen gesamt; 54 offen (`ended_at IS NULL`); 118 beendet; 33 archiviert;
  2 angeheftet; 1 versteckt.
- Offene nach Quelle: cli 31, a2a 13, telegram 4, tui 3, desktop 1, photon 1, subagent 1.
- `end_reason`-Verteilung: `agent_close` 48, `session_reset` 21, `startup_orphan_reap` 20,
  `cli_close` 11, `ws_orphan_reap` 8, `session_switch` 4, `new_session` 3,
  `tui_shutdown` 2, `cron_complete` 1.
- Viele offene `a2a`-Sitzungen mit 3 Nachrichten sind PONG-Test-Huellen — reine
  Abschluss-Kandidaten.

## Fallen

- **`archive` ist kein Loeschen.** Es setzt nur `archived=1` (weiches Verstecken,
  umkehrbar). `prune` loescht endgueltig und schuetzt Archivierte/Angeheftete
  standardmaessig — nur mit `--include-*` werden sie mitgenommen.
- **`prune` ohne Filter loescht standardmaessig 90 Tage.** Immer `--dry-run` zuerst.
- **`list` kann nicht nach „offen“ filtern.** Fuer den Bestand offener Sitzungen
  die DB direkt lesen (Skript `scripts/offene_sitzungen.py`) oder `browse`.
- **Angeheftete Sitzungen sind Keep-Flags.** Vor einem Massen-Abschluss
  `hermes sessions pinned` lesen und nie archivieren/prunen, was Max angeheftet hat.
- **Jedes Profil hat eine eigene DB.** Ein Sweep nur der Default-DB verpasst die
  Bot-Sitzungen unter `profiles/<name>/state.db`.
- **`id` ist global.** Nie `id > N` als Fenster nutzen.
- **Leere Assistentenzeilen sind Werkzeug-Turns.** Beim Inhaltslesen nach
  `length(content)>0` filtern, sonst steht "(nichts)" trotz voller Sitzung.
- **Zeitstempel sind gemischt: REAL-Epoch ODER ISO-String.** `ended_at` (und
  andere `*_at`-Spalten) liegen mal als Float (Unix-Epoch), mal als ISO-String
  mit `Z` vor — eine Altersrechnung, die nur `str(ts).replace('Z', …)` kennt,
  crasht mit `AttributeError: 'float' object has no attribute 'replace'`. Beide
  Formen behandeln: Float -> `fromtimestamp(ts, tz=utc)`, String ->
  `fromisoformat(str(ts).replace('Z','+00:00'))`.
- **`archive --older-than` zaehlt `last_activity_at`, nicht `ended_at`.** Eine
  Bucket-Rechnung auf `ended_at` sagt deshalb NICHT, was der Filter treffen
  wird — der Trockenlauf-Kopf nennt die echte Grenze ("last active before …").
  Beide Uhren pruefen oder den Filter aus vorher/nachher Zaehlern verifizieren.

# Sitzungen schliessen: erledigte Gespraeche abschliessen

Gedistillt aus `hermes_cli/sessions_cmd.py` und dem Live-Speicher (Stand 18.09.2026).
Laden mit `skill_view(name='sammelauftrag', file_path='references/sitzungen-schliessen.md')`.

## Der Kern in einem Satz

Eine Sitzung ist **erledigt**, wenn ihre Arbeit fertig ist und nichts mehr
wiederaufgenommen werden muss. Erledigte Sitzungen werden **archiviert** (weiches
Verstecken, umkehrbar), nie geloescht. `prune` loescht endgueltig und ist nur fuer
genuin tote Huellen gedacht.

## Drei Zustandsachsen, unabhaengig voneinander

| Achse | Spalte | Bedeutung |
|---|---|---|
| offen/beendet | `ended_at` | `IS NULL` = offen. Beendet heisst NICHT erledigt. |
| sichtbar/archiviert | `archived` | `1` = weich versteckt, umkehrbar. |
| angeheftet | `pinned` | Keep-Flag: nie automatisch archivieren. |

`archive` setzt nur `archived=1` und stempelt KEIN `ended_at` — Archiv und Ende
sind unabhaengig. Deshalb koennen offene UND archivierte Sitzungen zusammen
vorkommen (gemessen 18.09.2026: 54 offen, 33 archiviert, 2 angeheftet).

## Was „erledigt“ wirklich heisst

- **`ended_at IS NULL` = offen**, auch wenn seit Wochen still. Offene Sitzungen
  werden von `archive`/`prune` stillschweigend uebergangen („N open sessions also
  match these filters but will be skipped because prune only deletes ended
  sessions“). Ein „No sessions match“ bei `--older-than 30d` ist KEIN Beweis,
  dass nichts offen ist.
- **Wiederaufnahmefaehige Enden sind verlassen, nicht erledigt:**
  `agent_close`, `ws_orphan_reap`, `superseded_by_resume`, `startup_orphan_reap`
  holt die Sitzungswiederaufnahme zurueck. Nur archivieren, nie loeschen.
- **Endgueltige Enden** (Beispiele): `session_reset`, `cli_close`,
  `session_switch`, `new_session`, `tui_shutdown`, `cron_complete`.
- **Reine Huellen** (`message_count=0`, Gateway-Schluessel) sind Kandidaten fuer
  `prune --never-active` — sie wurden nie benutzt.

## Der Abschluss-Befehlssatz

Aufruf ueber das `terminal`-Werkzeug, vorher `PYTHONHOME`/`PYTHONPATH` entfernen:

```bash
powershell -NoProfile -Command "Remove-Item Env:PYTHONHOME, Env:PYTHONPATH -ErrorAction SilentlyContinue; & 'Agenten/Hermes/bin/hermes.exe' sessions …"
```

| Befehl | Zweck |
|---|---|
| `hermes sessions list [--source S] [--limit N]` | juengste Sitzungen (kann NICHT nach „offen“ filtern) |
| `hermes sessions pinned` | Keep-Flags lesen — VOR jedem Massen-Abschluss |
| `hermes sessions archive [Filter] --dry-run` | Trockenlauf: was wuerde versteckt? |
| `hermes sessions archive [Filter] --yes` | wirklich archivieren (weich, umkehrbar) |
| `hermes sessions prune --never-active --older-than 30d --dry-run` | Huellen-Trockenlauf |
| `hermes sessions prune --never-active --older-than 30d --yes` | Huellen endgueltig loeschen |
| `hermes sessions pin/unpin <id>` | Keep-Flag setzen/entfernen |

`archive`-Filter (gelten auch fuer `prune`): `--older-than AGE` (`5h`/`2d`/ISO),
`--newer-than`, `--before`/`--after`, `--source`, `--title`, `--end-reason`,
`--cwd`, `--min-/max-messages`, `--model`, `--provider`, `--user`, `--chat-id`,
`--chat-type`, `--branch`, `--min-/max-tokens`, `--min-/max-cost`,
`--min-/max-tool-calls`.

## Ablauf (immer Trockenlauf zuerst)

1. `hermes sessions pinned` lesen — Angeheftete ausnehmen.
2. Bestand aufnehmen: `scripts/offene_sitzungen.py` (offen) und
   `scripts/beendete_sitzungen.py` (beendet, noch nicht archiviert).
3. Trockenlauf: `hermes sessions archive --older-than 30d --dry-run`.
4. Pruefen, was der Trockenlauf zeigen wuerde (nicht blind bestaetigen).
5. Wirklich archivieren: `hermes sessions archive --older-than 30d --yes`.
6. Huellen separat: `hermes sessions prune --never-active --older-than 30d --dry-run`
   dann `--yes` — nur wenn der Trockenlauf ausschliesslich 0-Nachrichten-Huellen zeigt.
7. Nachweis: Zaehler aus `offene_sitzungen.py`/`beendete_sitzungen.py` davor/danach
   vergleichen — nur das beweist, was `archive` bewegt hat.

## Fallen

- **`archive` ist kein Loeschen.** Es setzt nur `archived=1` (umkehrbar). `prune`
  loescht endgueltig und schuetzt Archivierte/Angeheftete standardmaessig — nur
  `--include-*` nimmt sie mit.
- **`prune` ohne Filter loescht standardmaessig 90 Tage.** Immer `--dry-run` zuerst.
- **`list` kann nicht nach „offen“ filtern.** Fuer den Bestand die DB direkt lesen
  (Skripte) oder `browse`.
- **Jedes Profil hat eine eigene `state.db`.** Ein Sweep nur der Default-DB verpasst
  die Bot-Sitzungen unter `profiles/<name>/state.db`.
- **Angeheftete Sitzungen sind Keep-Flags.** Nie archivieren/prunen, was Max
  angeheftet hat.
- **Fremde Sitzungen (Claude/Codex) schliesst Hermes nicht.** Sie werden nur
  gelesen oder per `hermes sessions import` einseitig uebernommen.
- **`id` ist global ueber alle Sitzungen.** Nie `id > N` als Fenster nutzen.
- **Leere Assistentenzeilen sind Werkzeug-Turns.** Beim Inhaltslesen nach
  `length(content)>0` filtern.

## Messwerte (Live, 18.09.2026, Default-Profil)

- 172 Sitzungen gesamt; 54 offen; 118 beendet; 33 archiviert; 2 angeheftet; 1 versteckt.
- `end_reason`-Verteilung: `agent_close` 48, `session_reset` 21,
  `startup_orphan_reap` 20, `cli_close` 11, `ws_orphan_reap` 8, `session_switch` 4,
  `new_session` 3, `tui_shutdown` 2, `cron_complete` 1.
- Viele offene `a2a`-Sitzungen mit 3 Nachrichten sind PONG-Test-Huellen — reine
  Abschluss-Kandidaten.

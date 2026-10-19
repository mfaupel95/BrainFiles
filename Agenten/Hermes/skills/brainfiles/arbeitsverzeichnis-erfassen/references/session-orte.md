# Session- und Chat-Speicher ueber alle Ordner ab C:/Users/faupe

Bestandsaufnahme 14.10.2026. Hermes' `state.db` ist NICHT der einzige
Sitzungsspeicher. Fuer einen vollstaendigen Durchgang alle Orte abklopfen;
jeder hat ein eigenes Format und eigene Signale fuer offene Punkte.

## 1. Hermes (state.db) — der Hauptspeicher

- `Agenten/Hermes/state.db` (Default-Profil) + `profiles/<name>/state.db` je Bot.
- Skripte: `sammelauftrag/scripts/offene_sitzungen.py` (offen),
  `beendete_sitzungen.py` (beendet, unarchiviert).
- Stand 14.10.2026: 884 Sitzungen, 167 offen (155 still >24 h), 102 beendet
  unarchiviert, 2 angeheftet.

## 2. Claude Code CLI (~/.claude/projects/)

- Ein Ordner JE ARBEITSVERZEICHNIS (cwd), Name = Pfad mit `-` statt `\` und `:`.
  Darin je Sitzung eine `.jsonl` (neuester Eintrag am ENDE).
- Groesste Projektordner (14.10.): `O--Werkstatt-Repos-caveman` (208 jsonl),
  `C--Users-faupe-Documents-BrainFiles` (87), `...-MaxHirn` (68),
  `...-MaxHirn-Claude` (54), `C--Users-faupe` (27), `...-Agenten-Handel` (19).
- Lese-Rezept und offene-Punkt-Signale: `sammelauftrag/references/claude-sessions.md`.

## 3. Claude Desktop (MSIX-Container)

- `AppData/Local/Packages/Claude_*/LocalCache/Roaming/Claude/claude-code-sessions/
  <profil>/<unterordner>/local_*.json` — je Sitzung eine JSON mit NUR Metadaten
  (title, model, cwd, branch, cliSessionId, isArchived, lastActivityAt).
- Transcript liegt NICHT hier, sondern unter `~/.claude/projects/<encoded-cwd>/<cliSessionId>.jsonl`.
- Stand 14.10.: 168 `local_*.json` unter `Claude_pzs8sxrjxfjjc`.

## 4. Codex (~/.codex/)

- `sessions/2026/*.jsonl` — aktive Sessions (Stand 14.10.: 300).
- `archived_sessions/rollout-*.jsonl` — archivierte.
- `history.jsonl`, `session_index.jsonl`, `transcription-history.jsonl` — Indizes.
- `..codex-global-state.json` (2 MB) + `.bak` + mehrere `.tmp-*` (Wracks).

## 5. Cursor (~/.cursor/)

- Nur `cli-config.json` + `statsig-cache.json` — KEINE Session-Speicher gefunden.

## 6. BrainFiles intern (Uebergaben / Sitzungsreste)

- `Werkstatt/Austausch/` — HANDOVER-*.md + Uebergaben je Datum (nicht versioniert).
- `Werkstatt/Sitzungen/` (z. B. m3u_cleaner), `Werkstatt/Protokolle/`.
- `MaxHirn/sammelauftrag-*.md` — fruehere Sammelauftraege.

## Regeln

- Fremde Sitzungen (Claude/Codex/Cursor) schliesst Hermes NICHT — nur lesen
  oder per `hermes sessions import` einseitig uebernehmen.
- `archive`/`prune` greifen nur auf BEENDETE Hermes-Sitzungen; offene bleiben
  unberuehrt. Vor Massen-Abschluss `hermes sessions pinned` lesen.
- Die Desktop-JSON ist kein Transcript; neueste Sitzung != neuester Stand
  (Desktop schreibt `local_*.json` auch bei Fokus-Wechsel neu).
- Ein leerer `.jsonl`-Projektordner ist eine frisch geoeffnete, nie benutzte
  Sitzung — kein offener Punkt.

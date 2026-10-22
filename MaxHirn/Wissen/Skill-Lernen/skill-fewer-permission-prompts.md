---
name: skill-fewer-permission-prompts
description: Trockenlauf des Skills fewer-permission-prompts — Transkripte auf häufige Read-only-Befehle analysieren, Allowlist in .claude/settings.json ergänzen; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Häufig genutzte Read-only-Befehle aus Transkripten extrahieren und in Projekt-Allowlist eintragen.

**Lauf:** 2026-10-22, trockenlauf.

**Ablauf:**
1. Transkripte: `~/.claude/projects/<sanitized-cwd>/*.jsonl` — bis zu 50 neueste JSONL-Dateien
2. Tool-Calls extrahieren: Bash-Befehle (führendes Token + erstes Subkommando), MCP-Tool-Namen
3. Nur Read-only behalten (kein Write/Delete/Push/Install)
4. Bereits auto-erlaubte Befehle weglassen: `ls`, `cat`, `git status`, `git log`, `gh pr view` etc.
5. Muster wählen: `Bash(git log *)` (Varianten), `Bash(foo)` (einzel), MCP verbatim — nie Interpreter-Wildcard (`python3 *` etc.)
6. Priorisieren: ≥3 Vorkommen, Top 20
7. In `.claude/settings.json` des Projekts mergen (bestehende Einträge erhalten)

**Muster-Syntax:**
- `Bash(git log *)` — Leerzeichen vor `*` nötig für Prefix-Matching
- `Bash(foo)` — exakt
- MCP: voller Tool-Name verbatim

**Nie erlauben:** Interpreter-Wildcards (`python3 *`, `node *`, `bash *`, `npx *`), Mutations-Befehle.

**Ausgabe:** Tabelle mit Rang, Pattern, Count, Beschreibung; dann Merge in settings.json; dann Bericht.

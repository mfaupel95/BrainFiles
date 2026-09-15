# Werkzeugnamen: Claude Code → Hermes

Beim Übernehmen eines Skills in die Hermes-Kopie werden die Werkzeugnamen im Text
umgesetzt. Im Vault bleibt der Claude-Name stehen — sonst ist die Kopie nicht mehr
per Hash gegen die Quelle prüfbar.

| Claude Code | Hermes |
|---|---|
| `AskUserQuestion` | `clarify` |
| `WebFetch` | `web_extract` |
| `WebSearch` | `web_search` |
| `Read` | `read_file` |
| `Write` | `write_file` |
| `Edit` | `patch` |
| `Bash` | `terminal` |
| `Glob`, `Grep` | `search_files` (Volltext: `rg` über `terminal`) |
| `TodoWrite` | `todo_list` |
| `Task` | `delegate_task` |
| `Skill` | `skill_view` / `skill_manage` |

## Regeln

- **Erst nachsehen, dann umsetzen.** Vor jeder Umsetzung prüfen, ob das Hermes-Werkzeug
  in der Werkzeugliste der laufenden Sitzung steht. Ein geratener Name erzeugt Aufrufe
  ins Leere, die im Text des Skills niemandem auffallen.
- Nur in `Agenten/Hermes/skills/`-Kopien umsetzen, **nie** in `MaxHirn/.claude/skills/`.
- Nichts darüber hinaus glätten: Zeilenumbrüche, Überschriften und Formulierungen
  bleiben wie im Vault.
- Frontmatter (`version`, `platforms`) **nicht** nachrüsten: Skills im Claude-Format
  werden auch ohne diese Felder geladen. Hermes-Format-Skills bringen sie mit.
- Fachbegriffe und Pfade nicht "verbessern": Vault-relative Aufrufe
  (`Archiv\ArchivSuche\.venv\Scripts\python.exe`, `..\Agenten\Routinen\…`) sind für
  Claude Code mit dem Vault als Arbeitsverzeichnis richtig und bleiben so.

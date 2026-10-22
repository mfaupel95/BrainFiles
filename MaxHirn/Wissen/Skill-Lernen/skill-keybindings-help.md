---
name: skill-keybindings-help
description: Trockenlauf des Skills keybindings-help — ~/.claude/keybindings.json erstellen/ändern; Kontexte, Aktionen, Chord-Bindings, Unbind; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Claude-Code-Tastenbelegung in `~/.claude/keybindings.json` anpassen.

**Lauf:** 2026-10-22, trockenlauf.

**Immer zuerst lesen** (Datei existiert möglicherweise): mit Edit zusammenführen, nie komplett ersetzen.

**Dateiformat:**
```json
{
  "$schema": "https://www.schemastore.org/claude-code-keybindings.json",
  "$docs": "https://code.claude.com/docs/en/keybindings",
  "bindings": [
    {
      "context": "Chat",
      "bindings": {
        "ctrl+e": "chat:externalEditor"
      }
    }
  ]
}
```

**Modifier:** `ctrl`, `alt`/`opt` (= `meta` im Terminal), `shift`, `cmd`/`super`/`win`

**Chord:** Leerzeichen-getrennte Keystrokes: `ctrl+k ctrl+s` (3 Sekunden Timeout)

**Unbind:** `"ctrl+g": null`

**Binding verschieben:** Alten Key auf `null`, neuen Key auf die Aktion.

**Verbotene Keys (hardcoded):**
- `ctrl+c`, `ctrl+d` (Exit/Interrupt)
- `ctrl+m` (= Enter), `ctrl+[` (= Escape), `ctrl+i` (= Tab), `ctrl+h` (= Backspace)

**Wichtige Kontexte:**
- `Global`: überall aktiv
- `Chat`: Chat-Input fokussiert
- `Task`: laufender Task
- `Transcript`, `DiffPanel`, `Pane`, `Confirmation`, `Autocomplete`

**Nützliche Aktionen:**
- `chat:externalEditor` (Standard: `ctrl+g`)
- `chat:submit` (Standard: `enter`)
- `chat:stash` (Standard: `ctrl+s`)
- `app:toggleTodos` (Standard: `ctrl+t`)
- `app:openArtifact` (Standard: `ctrl+]`)
- `chat:newline` (Standard: `ctrl+j`)

**User Bindings addieren** zum Default — bestehende Standards bleiben aktiv außer explizit auf `null` gesetzt.

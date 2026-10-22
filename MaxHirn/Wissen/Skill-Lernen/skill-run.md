---
name: skill-run
description: Trockenlauf des Skills run — App tatsächlich starten und mit ihr interagieren (nicht Test-Suite); Projekt-Skill zuerst prüfen; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** App starten und als Nutzer mit ihr interagieren — nicht nur Tests.

**Lauf:** 2026-10-22, trockenlauf.

**Erst Projekt-Skill prüfen:**
```bash
d=$PWD; while :; do grep -Hm1 '^description:' "$d"/.claude/skills/*/SKILL.md 2>/dev/null; [ -e "$d/.git" ] || [ "$d" = / ] && break; d=$(dirname "$d"); done
```
→ Passenden Skill verbatim folgen. Nur wenn nichts passt: Muster unten.

**App-Typen und Muster:**
| Typ | Werkzeug | Datei |
|---|---|---|
| CLI | direkte Ausführung, Exit-Code, stdin/stdout | examples/cli.md |
| Web-Server/API | Background-Launch + curl | examples/server.md |
| TUI | tmux send-keys / capture-pane | examples/tui.md |
| Electron/Desktop | Playwright `_electron` + xvfb | examples/electron.md |
| Browser | Dev-Server + chromium-cli | examples/playwright.md |
| Library/SDK | import-and-call Smoke-Skript | examples/library.md |

**Wichtig:** Starten allein reicht nicht — mit der App interagieren:
- CLI: repräsentativen Befehl eingeben, Exit-Code und Output prüfen
- Server: berührte Route per curl aufrufen
- TUI: Navigation per send-keys, Ergebnis per capture-pane
- GUI: Schaltfläche klicken, Screenshot lesen (leeres Fenster = Fehlstart)

**Nach Ersteinrichtung:** `/run-skill-generator` empfehlen, damit die Schritte als Projekt-Skill festgehalten werden.

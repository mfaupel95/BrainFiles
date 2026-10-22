---
name: skill-project-memory-project-memory
description: Trockenlauf des Skills project-memory:project-memory — lokale SQLite-Datenbank (.project-memory/memory.db) für projektübergreifende Fakten; kein externer API-Aufruf; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Projekt-Fakten über Sitzungen hinweg in lokaler SQLite-Datenbank speichern.

**Wann nutzen:** Architekturentscheidungen, Namenskonventionen, Umgebungsdetails, Befehle die immer genutzt werden sollen — wenn Nutzer "remember" sagt oder dauerhaften Fakt nennt.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill geladen. Lokal, kein API-Aufruf. Nutzt Python-Skript + SQLite.

**Gelernt — Bedienung:**

```bash
python3 <skill-pfad>/scripts/mem.py <befehl> [args]
```

| Befehl | Verwendung |
|---|---|
| `add <key> <text> [--tag TAG]` | Speichern/aktualisieren |
| `get <key>` | Eine Memory abrufen |
| `search <wörter>` | Suchen (key, text, tag) |
| `list [--tag TAG]` | Alle auflisten, neueste zuerst |
| `forget <key>` | Löschen |

**Schlüsselformat:** kebab-case (`auth-strategy`, `deploy-command`). Tags: `decision`, `convention`, `env`.

**Wann abrufen:**
- Projektstart mit `.project-memory/`-Ordner → einmal `list`
- Vor Frage zu vergangenen Entscheidungen → `search`
- Immer melden wenn Antwort aus Memory kommt

**Housekeeping:**
- Erster `add` legt `.project-memory/` an + `.gitignore` (kein Commit)
- Team-Sharing: `.gitignore` löschen

**Nie speichern:** Passwörter, API-Keys, Tokens, persönliche Daten.

**Unterschied zu auto-memory:** auto-memory (`memory/MEMORY.md`) ist für den Agenten selbst; project-memory ist für Projekt-Fakten die der Nutzer explizit persistieren will.

**Grenzen:** Lokal pro Projekt; keine Cloud-Sync; Datenbank nicht versioniert (standardmäßig).

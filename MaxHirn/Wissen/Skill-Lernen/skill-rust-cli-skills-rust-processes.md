---
name: skill-rust-cli-skills-rust-processes
description: Trockenlauf des Skills rust-cli-skills:rust-processes — Rust-Kindprozesse sicher spawnen, verwalten, beenden; Streams, Exit-Status, Timeouts, Prozessgruppen.
metadata:
  type: reference
---

**Zweck:** Kindprozesse in Rust korrekt spawnen, verwalten und beenden — von `Command` bis Prozessgruppen.

**Wann nutzen:** Bei Rust-Code der externe Prozesse startet, Pipes verwaltet oder Timeouts implementiert.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill geladen. ~1 Seite. Kurz, präzise.

**Gelernt — Kern-Regeln:**
- **`Command` mit expliziten Argumenten** — niemals Shell-Text zusammenbauen (Injection-Gefahr)
- `OsStr`-Argumente beibehalten; executable lookup, working directory und inherited environment bewusst wählen
- Streams: inherited, discarded oder captured — je nach Aufgabe
- `output`/`wait_with_output` sammeln alles im Speicher → für große Outputs **bounded streaming**
- stdout UND stderr gleichzeitig drainieren — eine blockiert, während die andere wartet → Deadlock
- **stdin-Writer schließen** wenn Input fertig ist
- Spawn-Fehler ≠ nonzero exit ≠ Signal-Terminierung — alle drei getrennt behandeln
- **`Drop` auf `Child` weder stoppt noch reap't** den Prozess!
- Timeout beendet das Warten, nicht die Ausführung → nach Timeout noch den Prozess killen + warten
- Für Prozessketten: Platform-Process-Groups oder Job-Facilities (Windows Job Objects)
- Secrets aus Command-Diagnostics heraushalten

**Grenzen:** Windows Batch-Dateien brauchen eigene Quoting-Regeln. Runtime-spezifische Child-Wrapper (tokio etc.) verhalten sich anders als std — prüfen!

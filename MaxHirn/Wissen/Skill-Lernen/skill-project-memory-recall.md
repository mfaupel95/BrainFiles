---
name: skill-project-memory-recall
description: Trockenlauf des Skills project-memory:recall — ruft gespeicherte Projekt-Memories per Stichwort ab; nutzt agent-memory:memory-search (externe API); übersprungen.
metadata:
  type: reference
---

**Zweck:** Gespeicherte Projekt-Erinnerungen per Stichwort abrufen.

**Wann nutzen:** Wenn Kontext aus früheren Sitzungen gebraucht wird.

**Lauf:** 2026-10-22, übersprungen — nutzt `agent-memory:memory-search` (externe API).

**Ergebnis:** Skill lädt, leitet dann an `agent-memory:memory-search` weiter → externe Abfrage.

**Grenzen:** Externe API — kein Trockenlauf möglich. Für lokale Persistenz: auto-memory-System unter `C:\Users\faupe\.claude\projects\...\memory\` vorziehen.

---
name: skill-project-memory-remember
description: Trockenlauf des Skills project-memory:remember — speichert Projekt-Memories über externe API; nutzt agent-memory; übersprungen.
metadata:
  type: reference
---

**Zweck:** Projekt-Erinnerungen dauerhaft speichern (sitzungsübergreifend).

**Wann nutzen:** Wenn Kontext für spätere Sitzungen gespeichert werden soll.

**Lauf:** 2026-10-22, übersprungen — nutzt externe agent-memory-API.

**Ergebnis:** Skill lädt, leitet dann an externe Speicher-API weiter.

**Grenzen:** Externe API. Lokale Alternative: auto-memory unter `memory/` im Projekt-Verzeichnis.

---
name: skill-api-drift-detector-check-drift
description: Trockenlauf des Skills api-drift-detector:check-drift — scannt Codebase auf API-Drift (veraltete Aufrufe, geänderte Signaturen); lokales Scanning-Tool; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Codebase auf API-Drift prüfen — Stellen wo Code noch eine alte API-Version nutzt, während die API sich geändert hat.

**Wann nutzen:** Nach API-Updates, vor Deployments, wenn Deprecation-Warnungen auftauchen.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill lädt. Lokales Scanning-Tool — scannt Codebase-Dateien.

**Grenzen:** Konkrete Bedienung aus `api-drift-detector:api-drift-detector` (Meta-Skill) — dort vollständige Doku.

---
name: skill-api-drift-detector-api-drift-detector
description: Trockenlauf des Skills api-drift-detector:api-drift-detector — findet Stellen wo Frontend, Backend und Datenbank über die Form derselben Daten uneinig sind; TypeScript-Projekte; lokal; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** API-Drift in Projekten finden — wo Frontend, Backend, DB-Schema voneinander abweichen (Feldnamen, -typen, Optionalität, Enums, Verschachtelung).

**Wann nutzen:** Bei TypeScript-Projekten vor dem Merge, wenn Typen aus OpenAPI/GraphQL-Codegen geändert wurden, wenn Laufzeitfehler auf Formunterschiede hindeuten.

**Lauf:** 2026-10-22, trockenlauf.

**Gelernt — Ablauf:**

1. **Quellen suchen** — Frontend-Typen (`src/types/`, `*.d.ts`, generierte Clients), Backend-DTOs/Validierungsschemas (zod, yup, class-validator, OpenAPI-Spec), DB-Schema (Prisma, Drizzle, SQL-Migrationen).
2. **Entitäten vergleichen** — Feldnamen, Typen, Optionalität, Enums, Verschachtelung.
3. **Compiler bestätigen** — `npx tsc --noEmit` wenn `tsconfig.json` vorhanden (nichts installieren).
4. **Befund melden** — Schweregrade: Laufzeitbruch | Riskant | Kosmetisch.

**Schweregrade:**
- **Laufzeitbruch:** fehlende/umbenannte Pflichtfelder, falsche Typen
- **Riskant:** optional vs. required, fehlende Enum-Werte
- **Kosmetisch:** Namenskonventionen

**Abgrenzung zu `check-drift`:** `check-drift` ist der Auslöse-Shortcut, `api-drift-detector` ist das vollständige Rezept.

**Grenzen:** Nur TypeScript-Projekte sinnvoll; kein Install; Änderungen erst nach Bestätigung.

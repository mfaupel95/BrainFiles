---
name: skill-superpowers-systematic-debugging
description: Trockenlauf des Skills superpowers:systematic-debugging — 4-Phasen-Debugprozess; kein Fix ohne Ursachenanalyse; 3+ Fixes = Architekturproblem; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Bugs systematisch debuggen: immer Ursache finden, bevor gefixt wird. Symptom-Fixes verboten.

**Wann nutzen:** Jedes technische Problem — Tests, Bugs, unerwartetes Verhalten, Performance, Build-Fehler; besonders unter Zeitdruck und bei "offensichtlichen" Fixes.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill geladen. ~4 Seiten. Klares 4-Phasen-Framework mit Eskalationslogik.

**Gelernt — Die 4 Phasen:**

**Kernregel:** `NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST`

| Phase | Inhalt | Kriterium |
|---|---|---|
| 1. Root Cause | Fehler lesen, reproduzieren, Änderungen prüfen, Beweise sammeln | WHAT und WHY verstehen |
| 2. Pattern | Funktionierende Beispiele finden, Unterschiede identifizieren | Differenz erklärt |
| 3. Hypothesis | Eine Hypothese, minimaler Test, eine Variable | Bestätigt oder neu |
| 4. Implementation | Failing Test erst, dann Fix, dann Verifizierung | Bug weg, Tests grün |

**Phase 1 — Besonderheiten:**
- Multi-Komponenten-Systeme: Instrumentierung je Komponentengrenze, einmal laufen lassen, dann analysieren
- Data-Flow-Tracing: rückwärts tracen bis zur Quelle (nicht am Symptom patchen)

**Phase 4 — Eskalation:**
- Fix 1-2 fehlgeschlagen → zurück zu Phase 1 mit neuem Wissen
- **Fix ≥ 3 fehlgeschlagen → STOPP: Architekturproblem fragen**
- Zeichen für Architekturproblem: jeder Fix enthüllt neues Problem an anderer Stelle, massive Refactoring nötig, Fixes erzeugen neue Symptome

**Red Flags (alle → zurück zu Phase 1):**
- "Quick fix jetzt, später untersuchen"
- "Wahrscheinlich X, lass mich das fixen"
- "Ich verstehe es nicht ganz, aber das könnte helfen"
- "Noch ein Fix-Versuch" (nach ≥ 2 Versuchen)

**Häufige Rationalisierungen:**

| Entschuldigung | Wirklichkeit |
|---|---|
| "Einfaches Problem, kein Prozess nötig" | Einfache Bugs haben auch Ursachen |
| "Notfall, keine Zeit" | Systematisch ist schneller als Raten |
| "Ich sehe das Problem schon" | Symptome sehen ≠ Ursache verstehen |

**Unterstützende Techniken** (im selben Verzeichnis):
- `root-cause-tracing.md` — rückwärts durch den Call Stack
- `defense-in-depth.md` — Validierung auf mehreren Ebenen
- `condition-based-waiting.md` — Polling statt Timeouts

**Grenzen:** Prozess erfordert Disziplin; Zeitdruck verleitet zum Überspringen. Regel: systematisch ist trotzdem schneller.

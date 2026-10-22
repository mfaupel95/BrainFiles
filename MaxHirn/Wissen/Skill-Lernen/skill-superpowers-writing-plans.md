---
name: skill-superpowers-writing-plans
description: Trockenlauf des Skills superpowers:writing-plans — Implementierungsplan für agentenbasierte Ausführung; File-Struktur zuerst; Step-Granularität; Self-Review; Übergabe an SDD oder executing-plans; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Implementierungsplan schreiben der vollständig und unambig ist — für Agenten die die Codebase nicht kennen.

**Wann nutzen:** Nach `superpowers:brainstorming`, wenn eine Spec vorliegt und Implementierung folgen soll.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill geladen. ~5 Seiten. Vollständigstes Planungs-Framework.

**Gelernt — Ablauf:**

**1. Scope-Check:** Mehrere unabhängige Subsysteme → separate Pläne.

**2. File-Struktur vor Tasks:**
- Eine Verantwortung je Datei
- Dateien die zusammen ändern → zusammen halten
- In bestehenden Codebasen: etablierte Patterns folgen

**3. Task-Größe:** Kleinste Einheit mit eigenem Test-Zyklus, die ein Reviewer sinnvoll separat ablehnen könnte.

**4. Step-Granularität:** Ein Schritt = eine Aktion mit prüfbarem Ergebnis:
- "Fehlschlagenden Test schreiben" = Schritt
- "Test ausführen um sicherzustellen er schlägt fehl" = Schritt
- "Minimalen Code implementieren" = Schritt
- "Tests ausführen, bestätigen sie grün sind" = Schritt
- "Committen" = Schritt

**Plan-Header (Pflicht):**
```markdown
# [Feature] Implementation Plan
> For agentic workers: REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans
**Goal:** ...
**Spec:** [Pfad zur Spec]
## Global Constraints
## Review Focus
```

**Task-Struktur:**
```
### Task N: [Name]
**Files:** Create/Modify/Test
**Interfaces:** Consumes / Produces (exakte Signaturen)
- [ ] Step 1: Fehlschlagenden Test schreiben [Code-Block mit exakten Werten]
- [ ] Step 2: Test ausführen, Fehler verifizieren [Befehl + erwartete Ausgabe]
- [ ] Step 3: Implementieren [Signatur + Datei; Body nur wenn nötig]
- [ ] Step 4: Test grün verifizieren
- [ ] Step 5: Committen
```

**Self-Review (selbst, kein Subagent):**
1. Spec-Abdeckung: Jede Anforderung → ein Task?
2. Step-Scan: Jeder Step = genau eine vernünftige Aktion?
3. Typ-Konsistenz: Signaturen konsistent über Tasks?
4. Review Focus: Unbeschriebene Eingabeklassen → Test hinzufügen
5. Proportion: Plan nicht länger als Spec? Keine Code-Transkription?

**Übergabe:**
- Plan speichern unter `docs/superpowers/plans/YYYY-MM-DD-<name>.md`
- Partner zur Wahl: Subagent-driven (gründlicher, teurer) oder Native (schneller, ein Review am Ende)
- Empfehlung mit Begründung geben

**Grenzen:** Plan ist für Agenten die die Codebase nicht kennen — deshalb exakte Werte aus der Spec, keine "TBD".

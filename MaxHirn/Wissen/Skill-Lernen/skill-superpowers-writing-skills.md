---
name: skill-superpowers-writing-skills
description: Trockenlauf des Skills superpowers:writing-skills — TDD auf Prozessdokumentation angewendet; Baseline-Test vor Skill schreiben; Form nach Fehlertyp wählen; SDO; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Skills nach TDD-Prinzip schreiben: zuerst Baseline-Test (ohne Skill), dann Skill schreiben, dann verifizieren dass Agenten sich korrekt verhalten.

**Wann nutzen:** Wenn ein neuer Skill geschrieben oder ein bestehender signifikant geändert werden soll.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill geladen. ~10 Seiten. Umfangsreichster superpowers-Skill.

**Gelernt — TDD-Mapping:**

| TDD | Skill-Erstellung |
|---|---|
| Test schreiben | Druckszenario mit Subagent |
| Test schlägt fehl (RED) | Agent verletzt Regel ohne Skill |
| Produktionscode schreiben (GREEN) | Skill-Dokument schreiben |
| Test besteht | Agent hält sich an Skill |
| Refactor | Lücken schließen |

**Form nach Fehlertyp (kritisch):**

| Baseline-Fehler | Richtige Form | Falsche Form |
|---|---|---|
| Regel unter Druck gebrochen | Prohibition + Rationalisierungstabelle | Weiche Empfehlung |
| Falsche Ausgabe-Form | Positives Rezept / Kontrakt | Verbotsliste |
| Fehlendes Element | Strukturell: Pflichtfeld im Template | Prosa-Erinnerungen |
| Bedingungsabhängiges Verhalten | Konditional mit beobachtbarem Prädikat | Unbedingte Regel + Ausnahmen |

**SDO (Skill Discovery Optimization) — Beschreibungsfeld:**
- Beginnt mit "Use when..." — NUR Auslöse-Bedingungen, KEINE Workflow-Zusammenfassung
- Workflow in Beschreibung = Agent folgt Beschreibung statt Skill-Body zu lesen
- Schlüsselwörter: Fehlermeldungen, Symptome, Tools, Synonyme

**Skill-Typen:**
- Technique (Methode mit Schritten)
- Pattern (Denkweise)
- Reference (API-Docs, Syntax)

**Bulletproofing Disziplin-Skills:**
- "Violating the letter is violating the spirit" früh einbauen
- Rationalisierungstabelle aus Baseline-Tests
- Red-Flags-Liste zur Selbstprüfung
- Jeden Schlupfweg explizit schließen

**RED-GREEN-REFACTOR:**
1. RED: Druckszenario ohne Skill — genaue Rationalisierungen dokumentieren
2. GREEN: Minimalen Skill schreiben der diese Rationalisierungen adressiert
3. REFACTOR: Neue Lücken schließen, bis bulletproof

**Micro-Tests vor vollen Szenarien:**
- 5+ Reps je Formulierungsvariante
- Immer No-Guidance-Control einschließen
- Varianz = Metrik (5 verschiedene Interpretationen = Formulierung bindet nicht)

**Qualitätsregeln:**
- Eine exzellente Beispieldatei (keine 5 Sprachen)
- Flowcharts nur für nicht-offensichtliche Entscheidungen
- Token-Effizienz: getting-started <150 Wörter; andere <500

**Grenzen:** Aufwendigster Prozess aller superpowers-Skills — 3-Phasen-Zyklus + Micro-Tests + Pressure-Szenarien.

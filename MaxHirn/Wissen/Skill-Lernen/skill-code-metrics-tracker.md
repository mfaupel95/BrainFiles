---
name: skill-code-metrics-tracker
description: Trockenlauf des Skills code-metrics-tracker — Komplexität, Größe, Duplikation messen (metrics.py), Zeitverlauf tracken, Refactor-Kandidaten priorisieren.
metadata:
  type: reference
---

**Zweck:** Code-Metriken messen (zyklomatische Komplexität, Größe, Duplikation), über Zeit verfolgen und Refactoring-Kandidaten priorisieren.

**Wann nutzen:** Bei Code-Reviews, vor Refactoring, um Hotspots zu finden. Proaktiv nach größeren Änderungen.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill geladen. ~1 Seite. Klar strukturiert, sofort anwendbar.

**Gelernt — Nutzung:**

```bash
# Messen
python3 <skill-path>/scripts/metrics.py <dir>
python3 <skill-path>/scripts/metrics.py src --threshold 15 --dup-lines 8

# Zeitverlauf tracken
python3 <skill-path>/scripts/metrics.py src --save .metrics/2026-10-22.json
python3 <skill-path>/scripts/metrics.py src --compare .metrics/2026-10-22.json

# Churn ermitteln
git log --since="6 months ago" --name-only --format= | sort | uniq -c | sort -rn | head -30
```

**Sprachen:** Python (exakt via ast), JS/TS/Java/Kotlin/C#/Go/PHP/Rust/Swift/C/C++ (Branch-Counting, ~ESLint complexity). Vendor/build/generated/migration übersprungen.

**Priorisierung Refactor-Kandidaten (Reihenfolge):**
1. **Komplexität × Churn** — komplex + oft geändert = Fehlerherd
2. **Duplikation von Logik** (nicht Boilerplate) — zwei Pricing-Rules > zwei ähnliche Test-Setups
3. **Test Coverage** — ungetesteter komplexer Code braucht erst Charakterisierungstests

**Erste Schritte je Kandidat:** Funktion extrahieren, Conditional Chain durch Lookup ersetzen, Early Returns, duplizierte Blöcke zusammenführen.

**Grenzen:** Nie ohne Aufforderung refactorn. Immer eine Funktion auf einmal + Tests danach. Keine präziser klingenden Scores als die gemessenen Zahlen.

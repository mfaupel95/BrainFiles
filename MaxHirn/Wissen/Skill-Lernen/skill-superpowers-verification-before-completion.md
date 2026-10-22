---
name: skill-superpowers-verification-before-completion
description: Trockenlauf des Skills superpowers:verification-before-completion — keine Fertig-Aussage ohne frische Verifikation; 5-Schritt-Gate vor jedem Claim; Agent-Berichte separat verifizieren; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Verhindern dass Abschluss-Behauptungen ohne Belege gemacht werden.

**Wann nutzen:** Immer vor Fertig-Aussagen, Commits, PRs, Aufgabenwechsel, Agenten-Delegation.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill geladen. ~2 Seiten. Kompaktes Gate-Pattern.

**Gelernt — Das Gate:**

```
VOR jedem Fertig-Claim:
1. IDENTIFY  — Welcher Befehl beweist den Claim?
2. RUN       — Vollständig ausführen (frisch, jetzt)
3. READ      — Vollständige Ausgabe lesen, Exit-Code prüfen
4. VERIFY    — Bestätigt die Ausgabe den Claim?
5. DANN ERST — Claim machen + Beleg zitieren
```

Jeden Schritt überspringen = lügen, nicht verifizieren.

**Häufige Fehler:**

| Claim | Braucht | Nicht ausreichend |
|---|---|---|
| Tests grün | Test-Ausgabe: 0 Failures | Vorheriger Lauf, "sollte passen" |
| Bug behoben | Originales Symptom testen: grün | Code geändert, angenommen behoben |
| Anforderungen erfüllt | Zeile-für-Zeile Checkliste | Tests grün |
| Agent fertig | VCS-Diff zeigt Änderungen | Agent meldet "Erfolg" |

**Red Flags (alle → STOPP):**
- "sollte", "wahrscheinlich", "scheint"
- Zufriedenheit VOR Verifikation ("Perfekt!", "Fertig!", "Super!")
- Agent-Berichten vertrauen ohne eigene Prüfung
- Teilverifikation ("Linter grün" ≠ Build grün)

**Rationalisierungen:**

| Entschuldigung | Wirklichkeit |
|---|---|
| "Bin überzeugt" | Überzeugung ≠ Beweis |
| "Linter grün" | Linter ≠ Compiler |
| "Agent sagte Erfolg" | Separat verifizieren |
| "Andere Formulierung, gilt nicht" | Spirit über Letter |

**Grenzen:** Gilt für alle Formulierungen die Erfolg implizieren — nicht nur wörtliche Fertig-Aussagen.

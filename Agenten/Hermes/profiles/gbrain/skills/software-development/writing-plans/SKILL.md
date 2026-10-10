---
name: writing-plans
description: Use when ein Implementierungsplan vor dem Code noetig ist.
---

# Implementierungsplaene schreiben

Einen umfassenden Implementierungsplan schreiben, der einen Entwickler ohne Kontext und ohne Geschmacksannahmen durchfuehrt: welche Dateien, welcher Code, welche Tests, wie verifizieren. Das Ganze in haeppchengrosse Aufgaben zerlegen. Prinzipien: DRY, YAGNI, TDD, haeufige Commits.

Annahme: faehiger Entwickler, kennt aber Werkzeug und Problemdomaene nicht - und Testdesign auch nicht. Alles hinschreiben, nichts voraussetzen.

**Speicherort:** `docs/plans/YYYY-MM-DD-<feature>.md` (Nutzerpraeferenz kann abweichen).

## Scope-Check

Deckt die Spezifikation mehrere unabhaengige Teilsysteme ab, gehoert sie schon beim Brainstorming zerlegt. Falls nicht: separate Plaene vorschlagen - einer pro Teilsystem. Jeder Plan produziert eigenes, testbares, funktionierendes Ergebnis.

## Dateistruktur

Vor den Aufgaben festlegen, welche Dateien entstehen oder aendern und wofuer jede verantwortlich ist. Hier fallen die Zerlegungsentscheidungen.

- Einheiten mit klaren Grenzen und wohldefinierten Interfaces; jede Datei eine klare Verantwortung.
- Kleinere, fokussierte Dateien bevorzugen: Kontext einmal halten, Edits zuverlaessiger.
- Dateien, die sich gemeinsam aendern, gehoeren zusammen. Nach Verantwortung zerlegen, nicht nach technischer Schicht.
- In bestehender Codebasis Mustern folgen. Keine eigenmaechtige Umstrukturierung von Dateien, die man gerade aendert; ist eine Datei ausgewuchert, darf ein Split Teil des Plans sein.

Jede Aufgabe = eigenstaendige, in sich stimmige Aenderung.

## Aufgaben-Groesse

Eine Aufgabe ist die kleinste Einheit mit eigenem Testzyklus, die ein Reviewer-Gate wert ist. Setup/Config/Doku in die Aufgabe falten, deren Ergebnis sie braucht; nur trennen, wo ein Reviewer die eine Aufgabe ablehnen, die Nachbarin aber genehmigen kann. Jede Aufgabe endet mit einem unabhaengig testbaren Ergebnis.

**Haeppchengroesse - jeder Schritt eine Aktion (2-5 Minuten):** "Test schreiben" -> "Laufen lassen, sicherstellen dass er fehlschlaegt" -> "Minimale Implementierung" -> "Tests laufen lassen, sicherstellen dass gruen" -> "Committen".

## Plan-Kopf (jeder Plan beginnt damit)

```markdown
# [Feature] Implementierungsplan

**Ziel:** [Ein Satz: was entsteht]
**Architektur:** [2-3 Saetze Ansatz]
**Tech-Stack:** [Schluesseltechnologien]
```

**Projektweite Anforderungen** (Versionsgrenzen, Abhaengigkeitslimits, Naming-/Copy-Regeln, Plattform): eine Zeile je Punkt, Werte woertlich aus der Spezifikation. Gelten fuer jede Aufgabe implizit.

## Aufgaben-Struktur

```markdown
### Aufgabe N: [Komponente]

**Dateien:**
- Neu: `exact/path/file.py`
- Aendern: `exact/path/existing.py:123-145`
- Test: `tests/exact/path/test.py`

**Interfaces:**
- Konsumiert: [was diese Aufgabe von frueheren nutzt - exakte Signaturen]
- Produziert: [worauf spaetere Aufgaben sich stuetzen - Funktionsnamen, Parameter- und Rueckgabetypen. Der Ausfuehrende sieht nur die eigene Aufgabe; hier erfaehrt er, wie Nachbaraufgaben die Interfaces nutzen.]

- [ ] **Schritt 1: Fehlschlagenden Test schreiben** (Testcode zeigen)
- [ ] **Schritt 2: Test laufen lassen und Fehlschlag verifizieren**
  Run: `pytest tests/path/test.py::test_name` - Erwartet: FAIL
- [ ] **Schritt 3: Minimale Implementierung** (Code zeigen)
- [ ] **Schritt 4: Test laufen lassen, PASS verifizieren**
- [ ] **Schritt 5: Committen**
```

## Keine Platzhalter

Jeder Schritt enthaelt den echten Inhalt. Planfehler, die zum Scheitern fuehren:
- "TBD", "TODO", "spaeter implementieren"
- "Passende Fehlerbehandlung einfuegen" / "Validierung hinzufuegen" ohne Angabe was
- "Tests schreiben" ohne Testcode
- "Wie Aufgabe N" (Wiederholung statt Referenz)
- Schritte beschreiben WAS ohne WIE zu zeigen (Code-Bloecke bei Code-Schritten Pflicht)
- Referenzen auf Typen/Funktionen, die in keiner Aufgabe definiert sind

## Self-Review

Nach dem Schreiben den Plan mit frischen Augen gegen die Spezifikation pruefen:
1. **Spezifikations-Abdeckung:** jeden Abschnitt durchgehen - welche Aufgabe implementiert ihn? Luecken als Aufgaben ergaenzen.
2. **Platzhalter-Scan:** nach den roten Flaggen oben suchen, beheben.
3. **Typ-Konsistenz:** Namen/Signaturen spaeterer Aufgaben muessen zu frueher definierten passen (z.B. `clearLayers()` in Aufgabe 3 vs. `clearFullLayers()` in Aufgabe 7 - ein Bug).

Gefundene Probleme inline beheben, danach erneut reviewen.

## Uebergabe

Nach dem Speichern dem Nutzer die Auswahl anbieten:
1. **Delegierte Ausfuehrung (empfohlen):** pro Aufgabe ein frischer Subagent (delegate_task), Review zwischen den Aufgaben, schnelle Iteration.
2. **Inline-Ausfuehrung:** Aufgaben in der Session mit dem Skill executing-plans abarbeiten, Batch-Checkpoints zum Review.

Adaptiert aus obra/superpowers (Fork mfaupel95/superpowers), 16.09.2026.

---
name: skill-rust-cli-skills-rust-testing
description: Trockenlauf des Skills rust-cli-skills:rust-testing — verhaltensorientiertes Rust-Testen: Fixtures, Regressionstests, I/O-Injection, Property Tests.
metadata:
  type: reference
---

**Zweck:** Rust-Tests methodisch schreiben: Verhalten prüfen (nicht Implementierungsdetails), Fehler nachweisen, korrekte Assertions.

**Wann nutzen:** Bei Rust-Unit/Integration-Tests, Regressionen fixen, Test-Reviews.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill geladen. ~1 Seite. Kompakt, prinzipienbasiert.

**Gelernt — Kern-Regeln:**
- **Behavior first:** Welches Observable Promise könnte eine Änderung brechen?
- Fixture-Werte müssen korrekte Implementierung von plausiblem Fehler unterscheiden — unabhängig von der Implementierung herleiten
- Mit normalen Werten und direkten Aufrufen anfangen; einfache `Read`/`Write`-Implementierungen für I/O-Verhalten statt großer Mock-Frameworks
- Nur Kollaboratoren außerhalb der getesteten Property ersetzen; keine Traits die nur fürs Mocking von internem Choreography existieren
- **Regression-Loop:** Assertion soll gegen den Fehler scheitern, dann nach Reparatur bestehen
- Assertion darf relevante Unterschiede nicht verlieren (kein lossy trimming, sorting das einen Fehler verbirgt)
- Byte-Grenzen, Aliase, Reihenfolge prüfen wenn Teil des Contracts
- **Round-Trip allein reicht nicht** — Encoder und Decoder können denselben Fehler teilen
- Wartezeiten begrenzen, Worker joinen, deren Fehler propagieren
- Property-Tests / Fuzzing wenn Eingaberaum oder Invariante es rechtfertigen; gefundene Fehler als Regression behalten

**Grenzen:** Keine vollständige Feature-Matrix, Fuzz-Kampagne, Miri-Run oder Prozess-Harness nur weil der Skill sie erwähnt — nur wenn die Aufgabe es verlangt.

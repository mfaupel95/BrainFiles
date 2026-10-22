---
name: skill-rust-cli-skills-rust-testing
description: Trockenlauf des Skills rust-cli-skills:rust-testing - zählt die Tests im Rust-Teil des Handelsstacks lesend und nennt die Lücken bei Fehlerpfaden, Dateien und Prozessen.
metadata:
  type: reference
---

**Zweck:** Prüft, ob ein Test die Eigenschaft erkennen würde, die eine Änderung brechen könnte. Erwartungen werden unabhängig von der Implementierung formuliert. Ein Test, der nur kompiliert oder nicht gefunden wird, belegt nichts.

**Wann nutzen:** Vor einer Änderung, um Lücken zu erkennen, und bei Reviews, ob Tests die relevante Eigenschaft wirklich abdecken.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: vorhandene Tests im Rust-Teil und Lücken beschreiben. Keine Tests geschrieben, cargo nicht ausgeführt.

**Ergebnis:**

Bestand (lesend): 21 Testfunktionen in sechs Dateien:
- `omnitrade-risk/src/lib.rs`: 3
- `quant-alpha/src/cross_panel.rs`: 3
- `quant-planes/src/main.rs`: 2
- `quant-signal/src/lib.rs`: 2
- `quant-strategy/src/evidence.rs`: 4
- `quant-strategy/src/main.rs`: 7

Kein Ordner `tests/` mit Integrationstests gefunden. Die Tests sind also Unit-Tests innerhalb der Quelldateien.

Lücken, nach Gewicht:
1. **Fehlerpfade:** Ein Test für das Fehlen oder Beschädigen von `Cargo.lock` in `quant-planes` fehlt. Dort steht `expect`, also Panic.
2. **Exit-Codes:** Kein Test prüft, dass die Programme bei Verstoß 1 zurückgeben und bei Erfolg 0. Das ist der Vertrag, auf den `pruefen.ps1` sich verlässt.
3. **Eingabedatei:** Kein Test für `ranked_book.json` mit fehlender, leerer oder ungültiger Datei in `quant-strategy`.
4. **Ausgabe:** Kein Test prüft, dass die Ergebnisdatei vollständig geschrieben wird, auch wenn der Lauf danach scheitert.
5. **Prozess:** Die Programme sind nicht als gebaute Binärdateien getestet. Das Zusammenspiel mit Argumenten und Pipes ist ungeprüft.

Vorgeschlagen, nicht geschrieben: Tests zu Punkt 1 bis 3 als Unit-Tests mit kleinen Eingaben. Punkt 2 als Prozesstest, wenn der Exit-Code als Vertrag gilt.

**Gelernt:** Die Tests prüfen Berechnungen gut verteilt. Die Lücke liegt an den Grenzen: Datei, Exit-Code und Fehlerpfad. Bei einem Handelswerkzeug sind genau diese Stellen die teuren.

**Grenzen:** Gezählt und nach Dateiname bewertet, nicht gelesen. Ob die vorhandenen Tests ihre Erwartungen unabhängig vom Code formulieren, ist nicht geprüft. Cargo nicht ausgeführt, also keine Angabe, ob die Tests grün sind.

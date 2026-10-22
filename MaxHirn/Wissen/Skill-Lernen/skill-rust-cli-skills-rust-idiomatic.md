---
name: skill-rust-cli-skills-rust-idiomatic
description: Trockenlauf des Skills rust-cli-skills:rust-idiomatic - sucht im Rust-Teil des Handelsstacks nach auffälligen Mustern (Clone, unwrap, Ownership) und unterscheidet echte Verträge von bloßer Schreibweise.
metadata:
  type: reference
---

**Zweck:** Macht Eigentum und Erwartungen von Aufrufern im gewöhnlichen Rust sichtbar. Verlangt vor einer Änderung der Darstellung, Abwesenheit, Mutation, Reihenfolge, Fehler und Lebensdauer von Ressourcen zu klären. Ein Clone ist nicht falsch, nur weil er auffällt.

**Wann nutzen:** Bei Reviews und Umbauten, wenn Lesbarkeit oder Fehlerverhalten betroffen sind. Nicht für Umbauten ohne Anlass.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: auffällige Muster im Rust-Teil beschreiben und sagen, welche wirklich ändern würden. Nichts geändert.

**Ergebnis:**

Bestand (lesend): Eine Textsuche findet im Rust-Teil nur wenige Stellen:
- `quant-planes/src/main.rs:26` und `:31`: `name.clone()` und `d.clone()` beim Durchlaufen von `Cargo.lock`. Kosten sind bei dieser Datei klein. Die Clones sind nötig, weil die Menge `seen` den Besitz hält. Keine Änderung nötig.
- `quant-planes/src/main.rs:54` und `:55`: `expect` beim Lesen und Parsen von `Cargo.lock`. Das ist ein Vertragsproblem, kein Stilproblem: Ein Fehler wird zum Panic, obwohl der Aufrufer eine Meldung und einen Exit-Code erwartet. Diese Stelle würde ich ändern.

Nicht geprüft: Iteratoren und Ownership-Muster in den Crates `quant-alpha`, `quant-signal`, `quant-strategy` und `omnitrade-risk`. Die Suche nach `unwrap` und `clone` bildet nicht ab, wie die Daten fließen.

Empfehlung: Nur die `expect`-Stellen ändern. Die Clones nicht anfassen, solange kein Messwert auf ein Problem zeigt. Ein Umbau allein wegen des Musters wäre ein Stilwechsel ohne Gewinn.

**Gelernt:** Ein Muster ist nur dann ein Befund, wenn es einen Vertrag verletzt oder einen messbaren Nachteil hat. Die Suche nach Schlüsselwörtern liefert Kandidaten, keine Fehler.

**Grenzen:** Nur Textsuche. Der Datenfluss der einzelnen Funktionen wurde nicht gelesen.

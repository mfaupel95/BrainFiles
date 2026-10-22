---
name: skill-rust-cli-skills-rust-debugging
description: Trockenlauf des Skills rust-cli-skills:rust-debugging - beschreibt, wie ein Fehler im Rust-Teil des Handelsstacks eingegrenzt würde, mit Backtrace, Logging und Reproduktion, ohne Code zu ändern.
metadata:
  type: reference
---

**Zweck:** Sucht die erste sichtbare Abweichung zwischen beabsichtigtem und tatsächlichem Ablauf. Wählt das kleinste Signal, das zum Symptom passt, und sucht gezielt nach einer Beobachtung, die die Hauptvermutung widerlegen könnte.

**Wann nutzen:** Bei Fehlern im Lauf, bei Abweichungen zwischen Debug- und Release-Build, bei Hängern und bei Fehlern, die nur unter bestimmten Eingaben auftreten.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: beschreiben, wie ein Fehler im Rust-Teil eingegrenzt würde. Nichts geändert, nichts ausgeführt.

**Ergebnis:**

Vorgehen, in dieser Reihenfolge:
1. **Symptom festhalten:** Exit-Code, stdout und stderr getrennt und unverändert sichern. Die Unterschiede zwischen diesen Kanälen sind oft der erste Hinweis.
2. **Schicht bestimmen:** Kompilierfehler, Startfehler des Prozesses, fachlicher Fehler oder Absturz. Jede Schicht hat eigene Werkzeuge.
3. **Backtrace lesen:** `RUST_BACKTRACE=1` für den Lauf. Aufrufer bis zur eigenen Verantwortung verfolgen, nicht nur die oberste Zeile.
4. **Logging:** Gezielt an der Grenze, an der die Abweichung vermutet wird, mit Eingabewerten. Keine Schlüssel oder Zugangsdaten in die Ausgabe.
5. **Reproduktion:** Den Fehler mit der kleinsten Eingabe nachstellen, die dasselbe Symptom zeigt. Danach die Eingabe nur so weit verkleinern, wie das Symptom bleibt.
6. **Widerlegung:** Eine Beobachtung wählen, die die Hauptvermutung widerlegen würde.

Typische Fälle im Handelsstack:
- **Verschiedene Ergebnisse im Debug- und Release-Build:** Overflow-Verhalten und `debug_assert` vergleichen, nicht gleich einen Compilerfehler annehmen.
- **Dateien und Puffer:** Kurze Lese- und Schreiboperationen prüfen, bevor man Daten verwirft.
- **Kindprozesse:** stdout und stderr getrennt lesen, sonst blockiert die Pipe.

Werkzeuge: Debugger oder Profiler nur, wenn Laufzeitbelege nötig sind. Miri findet einige Fehler mit undefiniertem Verhalten, nicht alle.

**Gelernt:** Ein Fehler lässt sich mit der ersten Abweichung eingrenzen, nicht mit der letzten Fehlermeldung. Das Lesen von stdout und stderr getrennt hat in der Beschreibung denselben Stellenwert wie der Backtrace.

**Grenzen:** Der Ablauf ist allgemein beschrieben. Es gab keinen gemeldeten Fehler im Rust-Teil, auf den er angewendet wurde.

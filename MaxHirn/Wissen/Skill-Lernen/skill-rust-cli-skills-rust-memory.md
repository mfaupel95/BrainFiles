---
name: skill-rust-cli-skills-rust-memory
description: Trockenlauf des Skills rust-cli-skills:rust-memory - sucht im Rust-Teil des Handelsstacks nach Stellen, an denen Speicher mit der Eingabe wächst, und nennt die sinnvolle Grenze.
metadata:
  type: reference
---

**Zweck:** Bestimmt, was live bleibt, wie groß es werden kann und wer es freigibt. Trennt Anzahl der Allokationen, Heap, Spitzen-RSS und Stack. Eine Verkleinerung wird erst nach Benennung des wachsenden Begriffs gewählt.

**Wann nutzen:** Bei Eingaben, die wachsen können, bei Parallelisierung und bei Speicherdruck auf dem Handelsrechner.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Wachstumsstellen im Rust-Teil beschreiben und eine sinnvolle Grenze nennen. Nichts geändert, nichts gemessen.

**Ergebnis:**

Bestand (lesend), Sammlungen mit möglicher Wachstumsgröße:
- `quant-alpha/src/cross_panel.rs:8` bis `:10`: `assets` als `Vec<String>`, `matrix_a` und `matrix_b` als `Vec<f64>`. Die Matrizen wachsen mit Zahl der Assets und Zeitreihenlänge. Das ist der wahrscheinlichste Ort für Speicherdruck.
- `quant-strategy/src/main.rs:160`: Rückgabe einer Liste von Datenpunkten `Vec<nautilus_model::data::Data>`. Die Länge hängt vom Eingabeumfang ab. Die Liste wird vollständig gehalten, nicht gestreamt.
- `quant-signal/src/lib.rs:36`: `weights: Vec<RankedWeight>`. Wächst mit dem Universum an Instrumenten.
- `quant-planes/src/main.rs:19`: `HashMap` über alle Lock-Pakete. Begrenzt durch die Abhängigkeitszahl, unkritisch.

Ungeprüft: Die Größe von `ranked_book.json` beträgt 291 Byte. Das ist klein, aber ob es eine Obergrenze gibt, steht nirgends.

Vorgeschlagene Grenze:
1. Den wachsenden Begriff zuerst benennen: Anzahl Assets oder Länge der Zeitreihe.
2. Eine Obergrenze aus dem Universum ableiten. Beim Handelsstack ist die Zahl der Instrumente durch die Börse begrenzt. Ein fester Wert im Code, mit Fehlermeldung bei Überschreitung.
3. Messung vor der Änderung: Spitzenspeicher für einen realistischen Lauf. Ohne Messung keine Umstellung auf andere Speicherformen.
4. Nicht ändern: die `Vec<f64>`-Matrizen, solange die Messung keinen Druck zeigt. Sie sind kompakt.

**Gelernt:** Bei einem Handelsstack mit wenigen Instrumenten ist Speicher wahrscheinlich kein Engpass. Die Frage ist eher, ob eine unerwartet große Eingabe still viel Speicher verbraucht, und dafür reicht eine Obergrenze mit Fehlermeldung.

**Grenzen:** Nur Textsuche nach `Vec<` und `HashMap<`. Keine Messung, keine Obergrenze gefunden, Größen der Eingaben im Betrieb nicht bekannt.

---
name: skill-rust-cli-skills-rust-filesystem
description: Trockenlauf des Skills rust-cli-skills:rust-filesystem - prüft lesend, wie der Rust-Teil des Handelsstacks Dateien liest und schreibt, und welche Risiken bei Atomarität, Pfaden und Pufferung bestehen.
metadata:
  type: reference
---

**Zweck:** Trennt die Schreibweise eines Pfads vom tatsächlich geöffneten Objekt. Verlangt für Ersetzungen eine temporäre Datei auf demselben Dateisystem und einen atomaren Abschluss. Unterscheidet atomar sichtbar von dauerhaft auf der Platte.

**Wann nutzen:** Beim Schreiben von Ergebnisdateien, bei Lesen von Eingabedateien, die sich während des Laufs ändern können, und bei Ersetzungen, die bei einem Fehler die alte Datei erhalten müssen.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Dateizugriffe des Rust-Teils und ihre Risiken beschreiben. Nichts geändert.

**Ergebnis:**

Bestand (lesend), vier Zugriffe:
1. `quant-alpha/src/main.rs:87`: `std::fs::write(out_path, json)`. Schreibt direkt auf den Zielpfad. Bricht der Lauf mitten im Schreiben ab, bleibt eine halbe Datei zurück, und die alte ist verloren.
2. `quant-planes/src/main.rs:54`: liest `Cargo.lock` mit `expect`. Fehlt die Datei, bricht das Programm mit Panic ab statt mit einer Fehlermeldung.
3. `quant-strategy/src/main.rs:76`: liest `ranked_book.json` über einen relativen Pfad. Das Ergebnis hängt vom Arbeitsverzeichnis ab. Startet das Programm aus einem anderen Ordner, liest es eine andere Datei oder findet keine.
4. `quant-strategy`: parst die Datei mit `serde_json`. Wird die Datei während des Lesens von einem anderen Prozess geschrieben, kann der Inhalt halb sein.

Die Datei `ranked_book.json` ist 291 Byte groß.

Vorgeschlagene Änderungen, nicht ausgeführt:
- **Schreiben:** Temporäre Datei im selben Verzeichnis, Inhalt schreiben, Puffer leeren, dann atomar umbenennen. Die Datei bleibt bei einem Fehler unverändert.
- **Pfade:** Den Eingabepfad als Argument oder über das Projektverzeichnis festlegen, nicht über das Arbeitsverzeichnis.
- **Lesen:** Eine Datei, die gerade geschrieben wird, erkennen (Größe, Zeitstempel oder ein Schreib-Marker) oder den Lauf wiederholen.
- **Fehler:** Fehlende Dateien mit Meldung und Exit-Code beantworten, nicht mit Panic.

Nicht zugesichert: Atomar sichtbar ist nicht dasselbe wie dauerhaft nach einem Stromausfall. Dafür fehlt ein Synchronisieren der Datei und des Verzeichnisses.

**Gelernt:** Die Ergebnisdatei ist die Grundlage für Handelsentscheidungen. Eine halbe oder alte Datei, die still als gültig gelesen wird, ist ein größeres Risiko als ein Abbruch mit Fehlermeldung.

**Grenzen:** Die Zugriffe wurden über eine Textsuche gefunden. Ob es weitere Zugriffe über andere Funktionen gibt, ist nicht ausgeschlossen. Der Stromausfall-Fall wurde nicht geprüft.

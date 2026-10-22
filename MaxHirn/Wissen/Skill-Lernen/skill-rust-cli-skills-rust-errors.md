---
name: skill-rust-cli-skills-rust-errors
description: Trockenlauf des Skills rust-cli-skills:rust-errors - prüft lesend, wie Fehler im Rust-Teil des Handelsstacks modelliert und an Skripte gemeldet werden, ohne Code zu ändern.
metadata:
  type: reference
---

**Zweck:** Verfolgt einen Fehler von der Operation, die weiß, was passiert ist, bis zur Grenze des Prozesses. Unterscheidet erwartete Fehler (Result) von Programmfehlern (Panic). Legt fest, ob ein Lauf bei Einzelfehlern abbricht oder weitermacht. Verlangt, dass Erfolg nur gemeldet wird, wenn Ausgabe und Dateien vollständig sind.

**Wann nutzen:** Beim Entwurf der Fehlerbehandlung, bei unerklärlichen Erfolgsmeldungen trotz Fehler und vor Änderungen am Exit-Verhalten.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Fehlerbehandlung im Rust-Teil beschreiben und an Skripte melden. Nichts geändert.

**Ergebnis:**

Bestand (lesend):
- `quant-strategy` nutzt `anyhow` mit `bail!` bei ungültigen Instrument-IDs. Das ist eine Fehlerbehandlung über eine Anwendungsgrenze, ohne eigene Fehlertypen.
- `quant-planes` beendet das Programm über `std::process::exit` mit den Codes 0 und 1. `process::exit` überspringt Destruktoren, also auch das Leeren von Puffern.
- Die Crates `quant-alpha`, `quant-signal` und `omnitrade-risk` wurden nicht auf ihre Fehlerbehandlung geprüft.

Vorgeschlagene Modellierung:
1. **Erwartete Fehler** als Result, mit Kontext: welche Datei, welche Zeile, welcher Schritt. Die Ursache bleibt erhalten.
2. **Fehlertypen** nur dort, wo Aufrufer verschieden reagieren. Ein Typ für Eingabefehler, einer für Ausführungsfehler, sonst Anyhow.
3. **Exit-Codes** fest: 0 nur bei vollständigem Erfolg. Eingabefehler, Laufzeitfehler und Teilerfolg haben eigene Codes, die in der Dokumentation stehen.
4. **Ausgabe:** Fehler einmal an der CLI-Grenze melden, auf stderr. Keine Schlüssel im Kontext.
5. **Erfolg nur nach Abschluss:** Puffer leeren und Dateien schließen, bevor 0 gemeldet wird. `process::exit` vermeiden, damit Destruktoren laufen.
6. **Leere Ergebnisse** sind bei Strategie-Läufen eine gültige Antwort, kein Fehler. Sie müssen aber vom Fehlerfall unterscheidbar sein.

Gefahr für Skripte: Ein Programm, das eine Fehlermeldung ausgibt und 0 zurückgibt, täuscht Automatisierung. `pruefen.ps1` verlässt sich auf den Exit-Code.

**Gelernt:** Die Frage für ein Handelswerkzeug ist nicht, wie der Fehler heißt, sondern ob der Exit-Code stimmt. Ein falsch positiver Erfolg ist teurer als ein Fehlalarm.

**Grenzen:** Nur die Stellen gesehen, die eine Suche nach `anyhow`, `exit` und `unwrap` findet. Der Ablauf der Fehler durch die Module ist nicht gelesen.

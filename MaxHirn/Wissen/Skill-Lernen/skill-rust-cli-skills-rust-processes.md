---
name: skill-rust-cli-skills-rust-processes
description: Trockenlauf des Skills rust-cli-skills:rust-processes - prüft lesend, ob der Rust-Teil des Handelsstacks Kindprozesse startet, und nennt die Fehler bei Exit-Codes, Pipes und Wartezeiten.
metadata:
  type: reference
---

**Zweck:** Verfolgt jedes Kind von Start bis Endstatus und Freigabe der Ressourcen. Trennt Fehler beim Start von einem Exit-Code ungleich null oder einem Signal. Schreibt vor, dass jede Standard-Eingabe nach Abschluss geschlossen wird und dass ein Timeout das Warten beendet, nicht die Ausführung.

**Wann nutzen:** Wenn ein Programm andere Programme startet, ruft oder deren Ausgabe liest.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: prüfen, ob der Rust-Teil Kindprozesse startet, und die Fehlerfälle beschreiben. Nichts geändert, nichts ausgeführt.

**Ergebnis:**

Bestand (lesend): Eine Textsuche nach `Command::new`, `process::Command` und `spawn()` im Rust-Teil findet keine Treffer. Die drei Programme starten also keine Kindprozesse. Der Aufruf kommt von außen, durch Skripte wie `pruefen.ps1` oder durch den Handelsbetrieb.

Das verschiebt die Frage: Der Rust-Teil selbst ist kein Kindprozess-Verwalter. Der Vertrag liegt beim Aufrufer. Diese Stellen sind zu prüfen:
1. **Exit-Code:** Das Skript muss `$LASTEXITCODE` auswerten. Die Programme geben 0 bei Erfolg und 1 bei Verstoß zurück. Ein Skript, das nur die Ausgabe liest, übersieht Fehler.
2. **Pipes:** `quant-strategy | head` schließt die Pipe früh. Das ist ein Fehler im Aufrufer, nicht im Programm, aber das Programm darf dabei nicht still mit Erfolg enden.
3. **Wartezeit:** Ein Aufruf ohne Zeitgrenze kann ewig hängen. Der Aufrufer sollte eine Zeitgrenze setzen und den Prozess bei Überschreitung beenden.
4. **Windows-Aufruf:** Die Pfade in `pruefen.ps1` laufen über PowerShell. Dort gelten eigene Quoting-Regeln für Argumente.

Empfehlung: Den Aufrufer prüfen, nicht den Rust-Teil. Kein Eingriff im Programm nötig, solange es keine Kindprozesse startet.

**Gelernt:** Ein Programm, das selbst keine Kindprozesse startet, verschiebt das Risiko auf den Aufrufer. Für den Handelsstack gehört der Exit-Code-Vertrag in das Skript, das die Programme aufruft.

**Grenzen:** Nur Textsuche im Rust-Teil. Die Aufrufer in `pruefen.ps1` und im Handelsbetrieb wurden nicht gelesen.

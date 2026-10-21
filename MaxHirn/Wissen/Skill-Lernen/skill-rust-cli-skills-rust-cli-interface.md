---
name: skill-rust-cli-skills-rust-cli-interface
description: Trockenlauf des Skills rust-cli-skills:rust-cli-interface - beschreibt die Kommandozeilen-Schnittstelle der Rust-Programme im Handelsstack (Argumente, Exit-Codes, Ausgabe für Mensch und Maschine).
metadata:
  type: reference
---

**Zweck:** Behandelt ein Kommando als Schnittstelle für Menschen und Programme: Eingaben, Ausgabekanäle, Exit-Verhalten und Nebenwirkungen. Legt fest, welche Parser-Mechanik genutzt wird, und trennt Daten (stdout) von Diagnose (stderr).

**Wann nutzen:** Beim Entwurf oder Umbau eines Kommandos, bei Änderungen an Argumenten oder Ausgabeformaten, und wenn Skripte ein Kommando aufrufen.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: die Schnittstelle der Rust-Programme im Handelsstack beschreiben, ohne Code zu schreiben. Nichts geändert.

**Ergebnis:**

Bestand (lesend): Mehrere Crates in `Agenten/Handel/nautilus-rust/` haben einen Einstiegspunkt `src/main.rs`: `quant-alpha`, `quant-planes`, `quant-strategy`. Ob sie ein Parser-Crate wie clap nutzen, ist nicht geprüft.

Vorgeschlagene Schnittstelle:
- **Argumente:** Ein Parser, nach Möglichkeit der bestehende. Pflichtangaben und Kombinationen werden im Parser geprüft, nicht im Programm. Pfade als `PathBuf`, damit nicht-UTF-8-Pfade funktionieren. Ein Wert, der mit `-` beginnt, braucht `--` davor.
- **Vorrang:** Argumente vor Umgebungsvariablen vor Konfigurationsdatei. Ein ausdrückliches `false`, `0` oder ein leerer Wert überschreibt den Standardwert, ein fehlender Wert nicht.
- **Exit-Codes:** `0` für Erfolg, eine feste Zuordnung für Eingabefehler, Laufzeitfehler und Abbruch. Die Zuordnung steht in der Dokumentation des Kommandos, nicht nur im Code.
- **Ausgabe für Menschen:** Ergebnis auf stdout, Fortschritt und Warnungen auf stderr. Farben nur, wenn ein Terminal erkannt wird und der Nutzer das nicht abgeschaltet hat.
- **Ausgabe für Maschinen:** Ein festes Format, zum Beispiel JSON Lines, mit gleichbleibendem Schema und Reihenfolge. Skripte parsen keine Schmuckausgabe.
- **Steuerzeichen:** In Diagnosen werden unsichere Steuerzeichen aus Eingabedaten entschärft, bevor sie ausgegeben werden.
- **Interaktion:** Keine Rückfrage, wenn stdin umgeleitet ist. Eine Rückfrage ist nur dann erlaubt, wenn sie Teil des Vertrags ist.

Prüfbefehle, wenn umgesetzt: Hilfe und Version ohne Nebenwirkungen, ungültige Eingaben mit dem erwarteten Exit-Code, umgeleitete Ausgabe ohne Schmuck.

**Gelernt:** Die Schnittstelle eines Handelswerkzeugs ist ein Vertrag mit den Skripten, die es aufrufen. Schemaänderungen sind dort schwerer zu bemerken als Fehler im Programm selbst.

**Grenzen:** Der Bestand wurde nur an der Dateiliste geprüft. Ob die drei Programme Argumente, Exit-Codes oder JSON-Ausgabe bereits so umsetzen, ist nicht gelesen.

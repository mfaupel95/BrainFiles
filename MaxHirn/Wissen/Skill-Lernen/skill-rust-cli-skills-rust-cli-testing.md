---
name: skill-rust-cli-skills-rust-cli-testing
description: Trockenlauf des Skills rust-cli-skills:rust-cli-testing - beschreibt, wie die Kommandozeilen-Programme des Rust-Teils im Handelsstack getestet werden sollten, ohne Tests zu schreiben oder cargo auszuführen.
metadata:
  type: reference
---

**Zweck:** Wählt die kleinste Prüfgrenze, die die Aussage wahr macht. Parser-Tests belegen die Grammatik, nicht den Prozessstatus oder das Terminalverhalten. Prozessaussagen brauchen das gebaute Programm. Testdaten liegen in eigenen Temporärordnern.

**Wann nutzen:** Beim Anlegen von Tests für Kommandozeilen-Programme, besonders bei Exit-Codes, Ausgabeformaten und Dateiwirkungen.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Teststrategie für die Kommandozeilen-Programme im Rust-Teil beschreiben. Keine Tests geschrieben, nichts ausgeführt.

**Ergebnis:**

Bestand (lesend): Im Ordner `Agenten/Handel/nautilus-rust/` gibt es keinen Ordner `tests/` mit Rust-Dateien in den Crates, und kein `Cargo.toml` nennt `assert_cmd`. Die Programme sind also noch ungetestet, soweit sich das aus den Dateien sagen lässt.

Vorgeschlagene Prüfgrenzen:
1. **Parser-Tests (Unit):** Grammatik, Pflichtangaben, Konflikte, Vorrang von Argumenten vor Umgebungsvariablen. Schnell, ohne Prozess.
2. **Prozesstests (Integration):** Das gebaute Programm mit `assert_cmd` oder gleichwertig aufrufen. Dort werden Exit-Code, stdout, stderr und Dateiwirkungen geprüft.
3. **Terminal:** Nur wenn die Farb- oder Interaktionsaussage getestet werden soll. Sonst reicht ein umgeleiteter Lauf.

Was jeder Test prüfen müsste:
- **Exit-Codes:** Erfolg, Eingabefehler, Laufzeitfehler, je ein Fall.
- **Ausgabe:** stdout nur mit Ergebnis, stderr nur mit Diagnose. Bei JSON das Schema gegen eine feste Erwartung, nicht gegen einen Snapshot, den man ungeprüft übernimmt.
- **Fehler nach Teilarbeit:** Ein Lauf, der nach dem Schreiben einer Datei scheitert, darf keine halbe Datei hinterlassen.
- **Nicht-UTF-8-Pfade:** nur auf Windows prüfen, wo das relevant ist.

Fixtures: Jeder Test bekommt einen eigenen Temporärordner. Der Wächter für den Ordner bleibt bis zum Ende des Prozesstests aktiv.

**Gelernt:** Ein Test, der nur den Parser prüft, beweist nicht, dass das Programm mit dem richtigen Exit-Code endet. Bei einem Handelswerkzeug, das Skripte aufrufen, ist der Exit-Code Teil des Vertrags.

**Grenzen:** Der Bestand wurde nur über Dateinamen und Konfigurationssuche geprüft. Ob es Tests in anderen Dateien gibt, ist nicht ausgeschlossen. Die Empfehlung gilt, soweit die Suche reicht.

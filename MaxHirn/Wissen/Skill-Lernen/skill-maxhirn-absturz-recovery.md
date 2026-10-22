---
name: skill-maxhirn-absturz-recovery
description: Trockenlauf des Skills MaxHirn:absturz-recovery - beschreibt, wie der Stand des Lern-Fortschritts und der Lernnotizen nach einem Absturz geprüft würde.
metadata:
  type: reference
---

**Zweck:** Routine nach einem Absturz: Arbeitsbaum prüfen, unvollendete Aufgaben finden, Umgebungen testen, Index prüfen, Git-Integrität prüfen.

**Wann nutzen:** Als erste Aktion nach einem unerwarteten Neustart.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: beschreiben, wie Fortschritt und Lernnotizen nach einem Absturz geprüft würden. Nichts geändert.

**Ergebnis:**

Bestand (lesend): `Werkstatt/Projekte/skill-lernen/` enthält nur `fortschritt.md` mit 127 Datenzeilen. Im Vault gibt es 30 Notizen mit Präfix `skill-` in `MaxHirn/Wissen/Skill-Lernen/`, aber keine Notiz mit dem Namen `absturz-recovery`. Dieser Lauf ist daher nur im Fortschritt und in der Notiz selbst vermerkt.

Die Routine passt nur teilweise:
1. **Arbeitsbaum:** `git status` erfasst die Lernnotizen. Der Ordner `Werkstatt/` ist nicht versioniert. Eine Änderung dort taucht in Git nicht auf. Der einzige Schutz ist der stündliche Zwischenstand-Zweig.
2. **TASKS.md:** Die Routine verlangt die Prüfung offener Aufgaben. Für Lernnotizen gibt es keine Aufgabenliste. Der Schritt entfällt.
3. **Umgebungen:** `.venv` und `index.db` betreffen das Archiv, nicht den Lern-Fortschritt. Der Schritt entfällt.
4. **Index:** Abgleich jeder `skill-`-Notiz mit `INDEX.md`. Das geht über Dateinamen und Zeilensuche und ist ohne Ausführung möglich.
5. **Integrität:** `git fsck` betrifft nur Git-Objekte. Für die Lernnotizen gilt das nur, wenn sie committet sind.

Vorgeschlagene Prüfung nach Absturz: Fortschritt auf Spaltenzahl und Statuswerte prüfen (siehe Notiz zu `agent-protocols:plan`), jede Notiz gegen den Index abgleichen, dann den Zwischenstand-Zweig auf die letzte Fassung der Dateien prüfen.

**Gelernt:** Die Routine ist für Archiv und Handel gebaut. Die Lern-Dateien liegen außerhalb des versionierten Bereichs und brauchen daher eigene Prüfschritte.

**Grenzen:** Nur Dateiliste und Zeilenzählung. Der Zwischenstand-Zweig wurde nicht geprüft, und die Inhalte der Notizen nicht gelesen.

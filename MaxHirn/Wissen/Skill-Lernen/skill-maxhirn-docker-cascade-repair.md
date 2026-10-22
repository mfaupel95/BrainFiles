---
name: skill-maxhirn-docker-cascade-repair
description: Trockenlauf des Skills MaxHirn:docker-cascade-repair - beschreibt, woran man im Lern-Ablauf erkennt, ob ein Docker-Hang die Läufe stört, ohne Docker oder Prozesse anzufassen.
metadata:
  type: reference
---

**Zweck:** Repariert eine bekannte Kaskade: Docker hängt, MCP-Server starten im Kreis, hunderte Python-Prozesse erschöpfen den Commit-Speicher, geplante Aufgaben sterben mit Heap Corruption (3221225786). Kein Code-Fehler, sondern Speichererschöpfung.

**Wann nutzen:** Bei Docker-Hang, Fehler 3221225786, mehr als hundert Python-Prozessen oder erschöpftem Commit-Speicher.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: beschreiben, wie ein Docker-Hang im Lern-Ablauf zu erkennen wäre. Nichts gemessen, nichts gestartet, nichts beendet.

**Ergebnis:**

Woran der Lern-Ablauf einen Docker-Hang erkennt:
1. **Ausfall der Skill-Läufe:** Ein Skill, der Docker oder MCP braucht, meldet Verbindungsfehler. Der Lern-Ablauf selbst braucht weder Docker noch MCP, außer der Trockenlauf ruft einen Server auf.
2. **Fehlende Notizen:** Bricht ein Lauf in der Mitte ab, fehlt die Notiz, und der Fortschritt zeigt keinen Eintrag. Das ist das sichtbare Zeichen einer Kaskade.
3. **Messung:** Anzahl der Python-Prozesse über 100 und freier Commit-Speicher unter 5 GB. Beides wäre vor einem Lauf zu prüfen, nicht während.

Für den Lern-Ablauf heißt das: Die Kaskade betrifft ihn nur mittelbar. Ein Trockenlauf eines reinen Wissens-Skills ist unanfällig. Ein Lauf, der einen MCP-Server braucht, ist anfällig.

**Gelernt:** Der Lern-Ablauf sollte vor jedem Lauf den Zustand messen, nicht nur bei Fehlern. Eine Prüfung der Prozesszahl kostet nichts und verhindert einen halben Lauf.

**Grenzen:** Der Skill wurde nicht ausgeführt. Der Zustand des Systems wurde nicht gemessen, weil das Messen selbst einen Prozess braucht und das Ergebnis dieses Laufs nicht verändern würde.

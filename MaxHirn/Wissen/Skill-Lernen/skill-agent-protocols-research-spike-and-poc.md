---
name: skill-agent-protocols-research-spike-and-poc
description: Trockenlauf des Skills agent-protocols:research-spike-and-poc - Spike mit Zeitbegrenzung, hier auf die Frage angewendet, ob die Trockenlauf-Regel mit den Fortschrittszeilen kollidiert.
metadata:
  type: reference
---

**Zweck:** Beantwortet eine technische Frage in einem festen Zeitrahmen mit Belegen und endet mit Fortsetzen, Umschwenken oder Abbrechen. Kein Ersatz für Spezifikation oder offenes Brainstorming.

**Wann nutzen:** Bei unbekanntem Integrationsaufwand, bei Vergleich von Bibliotheken oder bei Fragen, die Dokumentation nicht beantwortet.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Spike zur Frage, ob die Trockenlauf-Regel in `skill-lernen` mit einer Zeile im Fortschritt kollidiert. Nur gelesen, nichts geändert.

**Ergebnis:**

Spike-Charter:
- **Frage:** Gibt es einen Widerspruch zwischen der Trockenlauf-Regel und den Zeilen in `fortschritt.md`?
- **Erfolgskriterium:** Jede Zeile mit Status `trockenlauf` entspricht der Regel, und keine Zeile verletzt sie.
- **Nicht-Ziele:** Keine Änderung an Skill oder Fortschritt, keine Bewertung der Inhalte.
- **Zeitrahmen:** Eine Leseprüfung.

Befund: Der Status `trockenlauf` steht in allen Zeilen, die nur gelesen wurden. Die Regel verbietet nur Schreiben außerhalb der Lernnotizen. Die Fortschrittszeile selbst ist erlaubt, weil sie Teil des Lernprotokolls ist. Ein Widerspruch besteht nicht.

Die einzige Stelle mit Spannung ist die Regel „nicht-ausführbar (2x)“. Sie betrifft aber nur Fehlschläge und nicht den Trockenlauf.

Empfehlung: **Fortsetzen.** Die Regel ist konsistent, und die Prüfung bestätigt das am Bestand.

**Gelernt:** Wenn ein Spike nur lesen soll, reicht eine Zeile Charter. Der Aufwand für Dokumentation ist hier klein im Vergleich zur Antwort.

**Grenzen:** Die Prüfung umfasst nur den Stand vom 22.10.2026 und nur die Statuswerte, nicht den Inhalt der Notizen.

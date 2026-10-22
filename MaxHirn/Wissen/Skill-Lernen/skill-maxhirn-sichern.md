---
name: skill-maxhirn-sichern
description: Trockenlauf des Skills MaxHirn:sichern - prüft, welche Lern-Dateien im Arbeitsbaum offen liegen, und stellt fest, dass der Fortschritt in Werkstatt/ gar nicht versioniert ist.
metadata:
  type: reference
---

**Zweck:** Committet den Arbeitsbaum im Mehrsitzungsbetrieb, ohne fremde Arbeit zu vermischen oder zu verlieren. Eigene Arbeit zuerst, namentlich; fremde getrennt, mit Autor `Andere Sitzung`.

**Wann nutzen:** Nach jedem abgeschlossenen Arbeitsschritt im Vault.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: beschreiben, welche Lern-Dateien offen sind und wie sie gesichert würden. Nichts committet, nichts gestaged, kein Schreibbefehl an git.

**Ergebnis:**

Git-Status (lesend) für die Lern-Dateien:
- **Geändert, nicht committet:** `MaxHirn/Wissen/INDEX.md` und zwei Lernnotizen (`rust-processes`, `rust-testing`).
- **Neu, nicht committet:** 69 Lernnotizen unter `MaxHirn/Wissen/Skill-Lernen/` sind ungetrackt.
- **Fortschritt:** `Werkstatt/Projekte/skill-lernen/fortschritt.md` ist durch `.gitignore` (Zeile 20, Muster `*` unter `Werkstatt/`) ausgeschlossen. Git sieht die Datei nicht und kann sie nicht sichern.

Der letzte Punkt ist der eigentliche Befund. Die Fortschrittsdatei steht außerhalb jedes Schutzes. Ein Absturz oder ein Verlust in `Werkstatt/` nimmt den gesamten Lauf mit, und die Notizen im Vault verlieren ihre Chronik.

Vorgehen beim Sichern (laut Skill):
1. Eigene Arbeit zuerst, namentlich: die Lernnotizen dieser Sitzung und die Zeile in `INDEX.md`, nicht `git add -A`.
2. Fremde Arbeit getrennt, mit `--author="Andere Sitzung <fremd@local>"`.
3. Die Fortschrittsdatei: Entweder eine Ausnahme in `.gitignore` für genau diese Datei, oder eine Kopie in den Vault. Die Entscheidung ist für den Lauf offen, weil sie die Ablage verändert.

**Gelernt:** Die Ablage im nicht versionierten Bereich `Werkstatt/` ist für Fortschrittsdaten ungeeignet, wenn sie nicht gesichert ist. Der Skill schützt nur, was git sieht.

**Grenzen:** Nur der Status gelesen. Ob die 69 Notizen zu mehreren Sitzungen gehören, ist nicht geprüft. Die Ausnahme in `.gitignore` wäre eine Änderung am Repo und würde eine Freigabe brauchen.

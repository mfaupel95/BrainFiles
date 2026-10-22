---
name: skill-skills-date-sim
description: Trockenlauf des Skills skills:date-sim — Koreanischer Sokotan-Simulator: Gesprächsfähigkeiten trainieren, ehrliche Bewertung, Nachbericht mit Lernziel.
metadata:
  type: reference
---

**Zweck:** Gesprächs- und Empathietraining durch simuliertes Blind Date. Nicht Fantasie — Übung. Ehrliches Scoring, Autopsie-Bericht nach Ende.

**Wann nutzen:** `/date-sim` für Gesprächstraining, Empathie-Übungen, Feedback zu Kommunikationsmustern.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill geladen. ~4 Seiten. Aufwendig strukturiert, sehr eigenständig (liest eigene `references/`-Dateien).

**Gelernt — Ablauf:**
1. **Setup** — 3 Fragen: Schwierigkeit (편안함/보통/까다로움), Ort (카페/술집/전시/밥집), Partner (Zufällig empfohlen)
2. **Partner generieren** — liest `references/personas.md`, würfelt echte Zufallszahl, fixiert: Name, Alter, Beruf, Gesprächsstil, 2 Lieblingsthemen, 1 Mine, **1 verborgenes Bedürfnis (wird erst im Bericht verraten)**
3. **Turn-Loop** — 8–12 Turns je nach Schwierigkeit, Horaz nach `references/scoring.md`, 8-Block-Gauge `▓▓░░░░░░ 33 (+3)`, Kommentar pro Turn
4. **Abbruch** — bei Horaz ≤ 0 bricht die Simulation ab (Partner geht von selbst)
5. **Autopsie-Bericht** — gezählt (nicht geschätzt): Eigenreden-Anteil, Fragen, Reaktionen; 3 Schlüsselmomente mit Originalzitat; verborgenes Bedürfnis enthüllt; **genau 1 Trainingsaufgabe**; bei ≥3 gleichen Befunden → "Chronische Schwäche"
6. **Verlauf-Datei** — `~/.claude/date-sim/history.jsonl`, append pro Session, feste Tags aus scoring.md

**Scoring-Logik:**
- Start: 30; Null/Minus für neutrale Antworten ("네", "그렇네요"); großer Minus für übersehene Signale
- Höfe-Kurve nicht nur aufwärts — realistisch modelliert
- Schwierigkeitsgrad skaliert Strafmultiplikator (×0.7 bis ×1.3)

**Sicherheitsregeln:**
- Keine realen Personen; Minderjährige verboten; sexuelle Wendung → Abbruch; Bericht bewertet Äußerungen, nicht Charakter

**Grenzen:** Nur Training, kein Beziehungscoach. Verborgenes Bedürfnis ist Kern des Lerneffekts — daher konsequent verborgen bis Bericht.

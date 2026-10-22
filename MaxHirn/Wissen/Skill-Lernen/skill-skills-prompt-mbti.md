---
name: skill-skills-prompt-mbti
description: Trockenlauf des Skills skills:prompt-mbti — Prompt-Gewohnheiten aus echten Session-Logs zählen und als MBTI-ähnliche Typkarte ausgeben; Coaching auf Basis echter Zahlen.
metadata:
  type: reference
---

**Zweck:** Eigene Prompt-Gewohnheiten analysieren: Tageszeit, Frageanteil, Arbeitsweise, Lieblingsworte — alles aus echten Logs gezählt, nicht geschätzt. Ausgabe als Typkarte + konkretes Coaching.

**Wann nutzen:** `/prompt-mbti` für Selbstreflexion, periodische Überprüfung (empfohlen: monatlich), nach Verhaltensänderungen.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill geladen. ~5 Seiten. Aufwendig, datengetrieben, ehrlich.

**Gelernt — Ablauf:**
1. Zeitraum fragen (AskUserQuestion): Heute / 7 Tage / 30 Tage / Gesamt
2. `scripts/analyze.sh` ausführen → liest `~/.claude/projects`, `~/.codex/sessions`, `~/.hermes/state.db`
3. `scripts/render.sh` → HTML + PNG Karte
4. `references/types.md` → Typ-Code lesen
5. Ergebnisblatt schreiben

**4 Achsen (aus `references/types.md`):**
- L/N: Nacht- vs. Tagarbeit (Frühmorgen-Anteil)
- D/S: Detailreich vs. kurz (Median-Länge der Prompts)
- T/F: Aufgabenorientiert vs. Fragorientiert (Fragezeichen-Anteil)
- W/R: Breit vs. fokussiert (Repository-Verteilung)

**Zeitregel:** Tag beginnt um 05:00 Uhr (wie `skills:truman`).

**Ergebnisblatt-Blöcke:** Typkarte + Begründungszahlen + Gewohnheiten + Je-Tool (wenn >1) + Auffälligkeiten + 1 Empfehlung.

**Coaching-Prinzipien:**
- Zahlen immer nennen ("neue Woche 22%", nie "manchmal nachts")
- Empfehlung aus tatsächlichen Zahlen ableiten, kein Template
- **Genau 1 Wochenaufgabe** — die kleinste, heute in 30 Minuten umsetzbare
- "Soll ich das jetzt umsetzen?" fragen + bei Ja direkt umsetzen (Hook, AGENTS.md-Abschnitt, Skill)
- Nächste Messung empfehlen (1 Monat)

**Skill-Generierungs-Trigger:** Wenn Befehl ≥20x wiederholt, oder Skill-Aufrufe <5/100 Prompts, oder Wiederholmuster in Lieblingsworten → Skill-Prompt erstellen.

**Datenschutz:** Kein Original-Text wird ausgegeben, nur Häufigkeiten. Bei Veröffentlichung: nach sensiblen Worten im Ranking fragen; Repository-Namen maskieren anbieten.

**Grenzen:** Braucht `jq` (sonst Stopp + Installationsanleitung). Hermes braucht `sqlite3`. <100 Prompts → Typkarte mit "Kleine Stichprobe"-Warnung.

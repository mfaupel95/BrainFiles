---
name: skill-skills-worklog
description: Trockenlauf des Skills skills:worklog — Sitzungs-Abschluss-Ritual nach einem Arbeitszyklus; Patchnote + Spec-Update + Backlog-Update in einem Schritt.
metadata:
  type: reference
---

**Zweck:** Nach einem abgeschlossenen Arbeitszyklus (Bugfix, Feature, Refactor) Dokumentation kompakt erledigen: Patchnote + optionale Spec-Aktualisierung + Backlog-Synchronisation. Kein vollständiger feature-flow nötig.

**Wann nutzen:** `/worklog` nach freier Arbeit ohne feature-flow; oder `/worklog <Thema>` wenn der Zyklus mehrere Stränge hatte.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill geladen. ~2 Seiten. Schlanker Sitzungs-Ausgang, komplementär zu `daily` (Eingang) und `feature-flow` (Vollzyklus).

**Gelernt — Ablauf:**

**Step 0 — Arbeit klären (vor dem Schreiben):**
1. `git status --short` + `git diff` + Branch-Name
2. Commits seit Abzweigung: `git log --oneline main..HEAD`
3. Gesprächs-Kontext: warum, was wurde geändert?
→ Ein-Satz-Zyklusfazit; unklar → einmal nachfragen

**Konventionen entdecken (kein Hardcoding):**
- Priorität: CLAUDE.md / AGENTS.md / docs/README.md → Struktur befolgen
- Fallback: `docs/_inbox/patch/`, `docs/feature-specs/`, `backlog.md`
- Notfalls: CHANGELOG.md anlegen + User befragen

**Ausgaben (User wählt Kombination):**

| Situation | Ausgaben |
|---|---|
| Einmaliger Bugfix/Refactor ohne Spec-Änderung | A + C |
| Spec hat sich geändert | A + B + C |
| Wiederverwendbares Muster entdeckt | + D |

**A. Patchnote** — "Was wurde warum getan?" Release-Note-Ton, zeitgebunden, nie mehr aktualisieren.
- Pfad: `<patch-dir>/YYYY-MM-DD-<slug>.md`
- Frontmatter: `date`, `tags`, `status: draft`
- Abschnitte: 0. Querverweis · 1. Kernfluss · 2. Entscheidungen · 3. Offen/Nachfolge · 4. Commits
- Kurzform: Abschnitte 0+4 weglassen wenn Änderung klein

**B. Feature-Spec-Aktualisierung** — Nur wenn sich die Spec ändert. Nur aktueller Stand, kein Verlauf im Text. Verlauf: Patchnote-Link in Änderungshistorie.

**C. Backlog-Aktualisierung** — Erledigte Items abhaken, neue Nachfolge-Items eintragen. Patchnote §3 und neue Backlog-Items müssen übereinstimmen.

**D. Research-Note-Kandidat** — Kandidaten als Liste anbieten, User wählt:
```
1. <Muster-Punkt>
2. <Muster-Punkt>
→ Nummer / zusammenführen / ablehnen
```

**Checkpunkte:**
- Vor Schreiben: Ausgaben mit User bestätigen
- Nach Schreiben: Ton + Umfang abgleichen
- Commit-Format: nicht erzwungen — Projekt-Konvention hat Vorrang

**Verhältnis zu anderen Skills:**
- `daily` = Sitzungs-Eingang; `worklog` = Sitzungs-Ausgang
- `feature-flow` Steps 8–9 = gleicher Ablauf; `worklog` ist die herausgelöste Version

**Grenzen:** Braucht zugängliche git-Daten. Ohne Änderungen (kein Commit, kein Diff) → kein Patchnote-Inhalt.

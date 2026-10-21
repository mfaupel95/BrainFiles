---
name: skill-anthropic-skill-creator
description: Trockenlauf des Skills anthropic-skills:skill-creator — vollständiger Lifecycle für neue Skills: Capture Intent → Interview → SKILL.md → Evals → Iteration → Description Optimization.
metadata:
  type: reference
---

**Zweck:** Skills erstellen, testen und iterativ verbessern. Vom ersten Entwurf bis zur optimierten Triggering-Description. Enthält auch Blind-Comparison und Packaging.

**Wann nutzen:** Wenn ein neuer Skill entstehen soll oder ein bestehender Skill verbessert werden soll. Mit "vibe" statt formaler Eval-Pipeline auch als leichter Feedback-Loop nutzbar.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Sehr langer, sehr detaillierter Skill (~15 Seiten). Vollständige Methodologie.

**Gelernt — Prozess:**
1. **Capture Intent** — Was soll der Skill tun? Wann triggern? Welches Output-Format?
2. **Interview** — Edge Cases, Input/Output-Format, Beispieldateien, Erfolgskriterien
3. **SKILL.md schreiben** — name, description (primärer Trigger-Mechanismus!), Skill-Body
4. **Test-Cases** — 2-3 realistische Prompts in `evals/<case>/` (prompt.md, case.yaml, graders/)
5. **Runs** — WITH-Skill + Baseline (ohne Skill oder alte Version) parallel in einem Turn spawnen
6. **Assertions** — Während Runs laufen: quantitative Asserts schreiben, in graders/ speichern
7. **Viewer** — `eval-viewer/generate_review.py` IMMER vor eigener Bewertung laufen lassen
8. **Feedback** — Nutzer reviewed, gibt Feedback, Skill wird verbessert, nächste Iteration
9. **Description Optimization** — `scripts/run_loop.py` mit 20 Trigger-Eval-Queries (10 should/10 should-not)

**Wichtige Regeln:**
- Description ist der Trigger-Mechanismus — "pushy" formulieren (Undertriggering-Problem!)
- `eval-viewer/generate_review.py` IMMER starten BEVOR eigene Bewertung — Mensch first
- Workspace: `<skill-name>-workspace/iteration-N/<case-name>/with_skill|without_skill/`
- `eval_metadata.json` in jedes Case-Verzeichnis — sonst Viewer zeigt "(No prompt found)"
- grading.json: Felder heißen `text`, `passed`, `evidence` (nicht name/met/details!)
- Bei Cowork/headless: `--static <path>` statt Browser-Server

**Anatomy of a Skill:**
```
skill-name/
├── SKILL.md (required, <500 Zeilen ideal)
└── scripts/   references/   assets/
```

**Grenzen:** Vollständige Pipeline (Subagents, Browser-Viewer) nur in Claude Code. Auf Claude.ai: keine Subagents, kein Browser → inline testen, Viewer weglassen, Baseline weglassen. Description Optimization braucht `claude -p` CLI — nur Claude Code.

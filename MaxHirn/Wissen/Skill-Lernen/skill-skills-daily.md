---
name: skill-skills-daily
description: Trockenlauf des Skills skills:daily — koreanischer Tages-Orientierungs-Skill: Backlog+Patch+Git lesen, schnelle Karte + Aufgabenempfehlung ausgeben.
metadata:
  type: reference
---

**Zweck:** Schnelle Session-Orientierung: „Wo bin ich, was soll ich heute tun?" Liest Backlog, Patch-Notes, Git-Status → eine Bildschirmseite Karte + Top-3-Empfehlungen.

**Wann nutzen:** Zu Sessionbeginn, morgens als Routine. Trigger: `/daily`, `/daily <keyword>` oder Natursprache wie "오늘 뭐하지".

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill geladen. ~1,5 Seiten. Koreanisch verfasst, aber universell anwendbar.

**Gelernt:**
- Liest: Backlog (backlog.md/TODO.md/gh issues), Patch-Notes (letzte 3), Git-Status + Log
- Findet Konventionen selbst per Glob — kein Hardcoding
- Ausgabe: 2 Blöcke — "Schnelle Karte" (Branch/Uncommitted/letzte Patches) + "Heute empfohlen" (Top 3)
- Priorisierung: 1. keine Blocker 2. Laufendes fortführen 3. Quick Wins 4. User-Keyword
- **Nur lesend** — keine Dateiänderungen, keine Commits
- Ergänzt `skills:worklog` (daily = Eingang, worklog = Ausgang eines Arbeitszyklus)
- Kann als Morgen-Routine geplant werden (Headless → Scratchfile statt Chat)

**Grenzen:** Ausgabe soll in 5 Sekunden erfassbar sein — keine langen Analysen. Blockierte Items nicht als Top-1 empfehlen.

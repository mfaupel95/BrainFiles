---
name: skill-agent-protocols-shipping-and-launch
description: Sicheres Deployen — Pre-Launch-Checkliste, Feature-Flag-Lifecycle, Staged-Rollout mit Schwellenwerten, Rollback-Plan, Post-Launch-Verifikation.
metadata:
  type: reference
---

**Zweck:** Vollständige Pre-Launch-Checkliste (Code/Security/Performance/Accessibility/Infrastructure/Docs). Feature-Flag-Lifecycle (Deploy OFF → Team → 5% → 25% → 50% → 100% → Aufräumen, Deadline 2 Wochen). Rollout-Entscheidungstabelle: grün/gelb/rot nach Error-Rate und P95-Latenz. Rollback-Plan-Vorlage mit Trigger-Bedingungen und Zeitschätzungen.

**Wann nutzen:** Vor jedem Production-Deploy, besonders bei signifikanten Features, Daten-Migrationen, neuen Integrationen. Auch als Kurskorrektur wenn man "mal schnell deployen" möchte.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill vollständig geladen. ~5 Seiten. Sehr vollständig — die umfassendste Checkliste des Skill-Satzes.

**Gelernt:** Rollout-Schwellenwerte quantifiziert: Error-Rate >2x Baseline = sofort zurückrollen, 10–100% über Baseline = beobachten. "It's Friday afternoon, let's ship it" als explizites Red-Flag. Feature-Flag-Aufräum-Deadline (2 Wochen nach vollem Rollout) — verhindert Flag-Friedhöfe. Für Handels-Agenten direktes Äquivalent: neues Handelssignal zuerst nur im Papiermodus aktivieren, dann 5% des Kapitals, etc.

**Grenzen:** Web-App-zentriert (Feature Flags, CDN, CSP). Für PowerShell-Routinen gilt: Checkliste vereinfacht auf "Tests grün, Backup vorhanden, Rollback-Schritt notiert". Für Handelssystem gilt: Papiermodus → Demo → Live mit kleiner Positionsgröße ist das Äquivalent zum Staged Rollout.

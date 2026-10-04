---
id: 20260918-handel-stack-repo
title: 'Handel-Stack als eigenes Repo'
tags: [handel, betrieb]
created: 2026-09-18
updated: 2026-09-18
related: [20260830-routinen, 20260830-verbindungen, 20260916-repo-bots]
summary: 'Agenten/Handel als privates GitHub-Repo mfaupel95/handel-stack gespiegelt: Umfang, Ausschlüsse, fehlende CI-Workflows und Schnappschuss-Charakter.'
---

# Handel-Stack als eigenes Repo

Stand 18.09.2026. Der Handelsstack liegt als **privates** GitHub-Repo
`mfaupel95/handel-stack` — ein Spiegel von `Agenten/Handel`. Arbeitskopie:
`Werkstatt/handel-stack` (echter Ordner, keine Junction).

- PR #1 (Zweig `feat/import-handels-stack`, Basis `main`): 604 Dateien, ~20 MB.
- Enthalten: alle Papier-Spuren mit Wachen, Zustand und Journal, der Dauerlauf,
  die Auswertungen, die Handelszentrale, Tests und die Datengrundlage.
- Nicht enthalten: `.venv`, `node_modules`, `__pycache__`, `*.log`/`*.pid`,
  verschachtelte Git-Repos (`nautilus`, `OpenAlice/workspaces`),
  `OpenAlice/sealing.key`, `OpenAlice/data/config/auth.json`, `.github/workflows`.
- `nautilus` bringt eine eigene `.gitignore` mit — deshalb fehlen
  `nautilus/zustand.json` und `nautilus/handelsjournal.csv` im Repo.
- CI-Workflows fehlen, weil der gh-Token keinen `workflow`-Scope hat:
  `gh auth refresh -s workflow`, dann in einem Folge-PR nachziehen.
- Laufzeitstände (Zustand, Journal, Ablehnungen) ändern sich durch den laufenden
  Dauerlauf — ein Import ist immer nur ein Zeitpunkt-Schnappschuss. Codedateien
  sind byte-gleich mit der Quelle.

Verwandt: [[Routinen]], [[Verbindungen]], [[Repo-Bots]]

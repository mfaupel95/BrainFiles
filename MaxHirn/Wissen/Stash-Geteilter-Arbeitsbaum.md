---
id: 20261008-stash-geteilter-arbeitsbaum
title: 'git stash im geteilten Arbeitsbaum'
tags: [betrieb, struktur]
created: 2026-10-08
updated: 2026-10-08
related: ["20260830-schutzregeln"]
summary: 'Warum `git stash` im Mehrsitzungsbetrieb Arbeit einfriert und beim Pop gegen Zwischencommits konfligiert; Ablösung durch sofortiges Committen.'
---

# git stash im geteilten Arbeitsbaum

**Regel: Im geteilten Arbeitsbaum nie `git stash`.** Eigene Arbeit wird nach
jedem Arbeitsschritt sofort committet — `stash` ist die Ablösung davon, nicht
die Ergänzung.

## Was passiert ist (Fall „Vault-Schutzschicht", 08.10.2026)

Am 07.10. um 02:22 wurde uncommittete Arbeit (10 Dateien, u. a. moondev-Tests,
TASKS.md, Verbesserer-Plan) in einen Stash gelegt, um den Pull/Push sauber zu
ziehen. In den folgenden ~16 Stunden committeten andere Sitzungen zwischendurch
(1e88e12e „T-160 nachgezogen", c580fe52, 57d43e9d, ef5cd5ec, u. a.) — 14
Zwischencommits. Der spätere `stash pop` erzeugte **7 Konflikte**; in allen
sieben war die Repo-Fassung die neuere (überarbeitete Tests, TASKS-Einträge
unter „Erledigt", Universumszählung 37/111 statt 36/105), der Stash überall die
ältere.

## Auflösungsmuster, falls es doch passiert

Bei einem Pop-Konflikt gilt: **OURS = aktueller Repo-Stand, THEIRS = der
ältere Stash.** Die Seiten nicht per Gefühl, sondern per Datum entscheiden:

1. Stash-Datum lesen (`git log -1 --format='%ci' 'stash@{0}'`).
2. Die Commits auflisten, die die Datei **seither** berührt haben
   (`git log --oneline <stash-parent>..HEAD -- <datei>`).
3. Berührt die neuere Arbeit dieselben Zeilen, gewinnt die Repo-Fassung
   (`git checkout --ours -- <datei>`), sonst prüfen, ob der Stash etwas
   enthält, was im Repo noch fehlt.
4. Jede aufgelöste Datei auf Konfliktmarker prüfen (`grep -c '<<<<<<<'`).
5. Stash erst droppen, wenn `git diff HEAD 'stash@{0}'` für jede betroffene
   Datei die erwartete Restdifferenz zeigt und push+fetch synchron sind
   (`rev-list --left-right --count origin/master...master` → `0  0`).

## Wo die Regel sonst noch steht

In allen drei Regeldatei-Paaren: `CLAUDE.md` = `AGENTS.md` an der Wurzel
(Abschnitt „Bereichs-Besitz"), in `MaxHirn/` (Abschnitt „Mehrere Sitzungen
gleichzeitig") und in `Werkstatt/` (Regel 3 der Sechs Regeln), dazu als
Einzeiler in `Agenten/Handel/AGENTS.md`.

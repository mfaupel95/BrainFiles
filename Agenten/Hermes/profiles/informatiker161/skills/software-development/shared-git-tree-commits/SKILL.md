---
name: shared-git-tree-commits
description: Commit in a shared Git tree; verify foreign diffs first.
version: 1.0.0
author: Informatiker161
license: Proprietary
metadata:
  hermes:
    tags: [git, fremdarbeit, multi-session, workflow]
    related_skills: [codebase-inspection]
---

# Commits im geteilten Arbeitsbaum

Klasse: mehrere Sitzungen (Claude, Hermes, Bots) schreiben in denselben Git-Baum.
Alle Regeln aus `MaxHirn/Wissen/Schutzregeln.md` gelten (immer erneut lesen), diese
Skill verdichtet die Arbeit daran.

## When to Use

Wenn ein Git-Arbeitsbaum von mehreren Sitzungen geteilt wird und fremde uncommettete
Aenderungen vorliegen: vor einem sicheren Commit einsetzen. Ausloeser: `git status`
zeigt fremde Dateien, grosse Diffs auf config-Skripten, `ahead N`-Hinweise, oder die
Aufgabe, Arbeit fremder Sitzungen sauber zu sichern.

## Ablauf vor jedem Commit

1. **`git fetch origin` + `git status -sb`** lesen. `ahead N` = N unpushed eigene
   Commits, Seite fuer Seite pruefen, bevor gepusht wird.
2. **Fremde uncommettete Aenderungen nie liegen lassen und nie mit eigener Arbeit
   vermischen.** Eigener getrennter Commit, Autor `--author="Andere Sitzung <fremd@local>"`
   (echten Namen nur, wenn der Urheber wirklich feststeht). In die Ich-Form nur die
   eigene Arbeit.
3. **Freshness-Gate (10-Minuten-Regel):** mtime jeder zu fassenden Datei pruefen
   (`stat -c '%y  %n'`). Liegt eine < 10 min zurueck, ruht sie nicht — dort arbeitet
   gerade eine andere Sitzung. Solche Dateien liegen lassen und im Bericht melden,
   NICHT committen. Die andere Sitzung committet ihre Arbeit meist selbst — der
   scheinbar "stehende" Rest kann sich noch waehrend der eigenen Pruefung verschieben.
4. **EOL-Churn quantifizieren, bevor entschieden wird.** Eine grosse Diff-Zahl je
   Datei ist oft fast komplett CRLF/LF-Neuformatierung durch eine Fremdsitzung; die
   echte Aenderung ist klein. Trennen mit:
   ```bash
   git diff --ignore-cr-at-eol -w -- <pfad> | wc -l
   ```
   Erst daraus ergibt sich, ob ueberhaupt eine echte inhaltliche Aenderung vorliegt
   (der User entscheidet dann ueber sie) oder nur EOL-Rauschen (nichts zu committen).
5. **Namen-Theke:** `git diff --numstat` zeigt leere Eintraege → nur mode/EOL,
   dann bleibt die Datei unangetastet. `git add <pfad>` namentlich, nie
   `git add -A` / `.` / `-a`.

## Befund vor dem Zugriff

- Liste der Fremdarbeit mit Diff-Charakter (echte Aenderung vs. EOL) VOR dem
  ersten Commit zeigen. Der User bestaetigt, welche Aenderungen von ihm sind;
  jede bestaetigte Gruppe bekommt einen eigenen Commit.
- Feste Reihenfolge im Bericht: was committet wurde (Hash + Autor), was aktiv
  schreibt und deshalb NICHT angefasst wurde, was nur EOL ist, was pushen muss.

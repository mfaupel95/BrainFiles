---
name: arbeitsverzeichnis-erfassen
description: "Bestand erfassen, Wichtiges merken, Aufgaben in Kanban."
version: 0.1.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [Bestandsaufnahme, Memory, Kanban, Git]
---

# Arbeitsverzeichnis erfassen und uebertragen

Systematischer Durchgang durch den BrainFiles-Arbeitsbaum: Git-Stand pruefen,
unmerged Files sicher aufloesen, das Wichtige dauerhaft in die `memory` sichern
und offene Aufgaben aus TASKS.md als gruppierte Kanban-Karten vergeben.
Macht KEINEN Umbau, KEINEN Live-Handel und fasst fremde (parallele
Sitzungs-)Arbeit weder an noch committet sie. Kern-Stoerung: der geteilte
Git-Index und die leeren Kanban-Boards — beides ist erwartet, kein Befund.

## When to Use

- "durchsuche das arbeitsverzeichnis, merke dir alles wichtige"
- "uebertrage den inhalt und die ergebnisse nach Hermes"
- "offene Aufgaben mit kanban angehen"
- Bestandsaufnahme zu Beginn einer neuen Session / nach einer Pause
- Ein Befund (z. B. MaxHirn/Wissen/*-Befund-JJJJMMTT.md) liegt vor und soll dauerhaft gesichert und in Aufgaben uebersetzt werden

## Prerequisites

- BrainFiles-Wurzel als Arbeitsverzeichnis (`cd "$HERMES_HOME/../.."`)
- Git-Bash-Terminal (`terminal`), Kanban-Boards handel/wartung/repos/wissen
- TASKS.md ist die EINZIGE Quelle offener Aufgaben (Boards sind meist leer)

## How to Run

Agentischer Workflow — ausgefuehrt ueber Hermes-Werkzeuge in der Reihenfolge
unter Procedure. Kein Einzeiler; je Schritt ein echter Lauf mit Beleg.

## Quick Reference

```
git status --porcelain                      # Gesamtbild inkl. Fremdarbeit
ls -la .git/index.lock                      # Alter der Sperre (0 Byte + 0 git-Prozesse = Wrack)
grep -c '^- \[ \]' MaxHirn/Archiv/TASKS.md  # Anzahl offener Aufgaben
GIT_INDEX_FILE=<scratch>/idx_<thema> git read-tree HEAD && git add <eigene> && git commit
python <skill>/scripts/konflikt_aufloesen.py <unmerged-datei>
kanban_list   # je Board; Duplikat-Ausgabe = wiederholen
kanban_create # gruppiert, mit assignee + priority, T-Nummern im body
```

## Procedure

1. **Bestandsaufnahme** — ein `terminal`-Aufruf mit `git status --porcelain`,
   `git branch --show-current`, `git log origin/master..HEAD --oneline | head`
   und `git log -5 --oneline`. Danach `read_file` auf TASKS.md (offene Aufgaben),
   dann `kanban_list` je Board. Kanban-Boards auf "done" ist NORMAL — offene
   Aufgaben liegen in TASKS.md.

2. **Unmerged File aufloesen** — fuer jede `UU`-Datei aus dem Status: beide
   Seiten vergleichen (`git show HEAD:<pfad>` gegen Arbeitsbaum), die NEUERE
   gewinnt (generiert_at / Zeitstempel im Inhalt), dann
   `python Agenten/Hermes/skills/brainfiles/arbeitsverzeichnis-erfassen/scripts/konflikt_aufloesen.py <pfad>`
   — behaelt die Seite nach `=======`, validiert JSON, erhaelt CRLF/LF.

3. **Memory sichern** — die Kern-Erkenntnisse (Befund, kritische Luecken,
   Lektionen) als EINEN dichten `memory`-Eintrag (target=memory) anlegen.
   Fakten, die nur eine Aufgabe betreffen, gehoeren NICHT hierher.

4. **Committen mit eigenem Index** — Fremdarbeit einer parallelen Sitzung
   liegt oft schon STAGED im geteilten Index. Vor dem Commit `git diff
   --cached --stat` lesen; bei fremden Pfaden: `export
   GIT_INDEX_FILE=<scratch>/idx_<thema>`, `git read-tree HEAD`, `git add
   <eigene Pfade>`, `git commit`, danach `unset GIT_INDEX_FILE`. NIE `git
   commit` ohne Pfadangabe, NIE `git add -A`.

5. **Echten Index nachziehen** — nach dem Commit `git add <eigene Pfade>`
   im ECHTEN Index, sonst meldet `git status` die frisch committeten Dateien
   als geloescht und fremdarbeit-einziehen.ps1 committet sie erneut.

6. **Kanban-Karten vergeben** — offene TASKS gruppieren (wenige Karten statt
   je Punkt eine), Board je Thema (handel/wartung/repos/wissen), `assignee`
   + `priority` setzen (P1 = dringend), T-Nummern in den body, Hausverbote
   in jede Karte (kein Live-Schalter, nur eigene Pfade stagen).

## Pitfalls

- **index.lock-Fehler bei jedem git-Aufruf:** Lock-Alter pruefen UND echte
git-Prozesse zaehlen (alle `git.exe` sind `git fsmonitor--daemon` und beweisen
nichts — nach 'fsmonitor' in der CommandLine filtern). 0 Byte + 0 echte
Prozesse = Wrack: UMBENENNEN (`mv .git/index.lock .git/index.lock.verwaist-JJJJMMTT`),
nie loeschen. Bei >0 echten Prozessen warten.
- **kanban_list liefert `[Duplicate tool output]`:** wiederholen, bis echte
Ergebnisse kommen (in dieser Session brauchte es 4 Anlaeufe).
- **CRLF-Dateien:** Konflikte/JSON per `read_bytes()`/`write_bytes()` mit
`b"\r\n"`-Erhalt loesen. Danach `git diff --numstat` pruefen — eine gewollte
Zeile muss 1/1 zeigen, nie die ganze Datei.
- **Fremdarbeit im Index ist kein Fehler:** Skills/config.yaml einer
parallelen Sitzung liegen gelassen, nur eigene Pfade committen.
- **Komprimiertes Wissen nicht erfinden:** Titel/Befunde offener TASKS, die
im transkribierten Protokoll fehlen, mit `session_search` zurueckholen statt
zu raten.
- Verwandter Skill fuer die tiefen Index-/Zweig-Faelle: `arbeitsbaum-git-hygiene`
(brainfiles).

## Verification

```
git log origin/master..HEAD --oneline | head   # eigener Commit vorhanden
kanban_list                                     # neue ready-Karten sichtbar
```

Beide muessen den eigenen Commit bzw. die eigenen Karten zeigen; `git status
--porcelain` darf nur noch Fremdarbeit/untracked zeigen.
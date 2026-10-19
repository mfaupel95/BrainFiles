---
name: dateischwund-diagnose
description: "Use when Dateischwund geprueft wird: echt oder committet."
version: 1.0.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [brainfiles, wachen, dateischwund, diagnose]
    related_skills: [befund-zu-fix, trugschluesse, wirkung-nachweisen]
---

# Dateischwund-Diagnose

## When to Use

- Auftrag lautet 'Dateischwund pruefen' oder 'Probleme reparieren' im Zusammenhang mit verschwundenen Dateien.
- Eine dateischwund-*-Wache hat gemeldet oder soll geprueft werden (lebt sie, was hat sie gefunden).
- Verwaiste `__pycache__`-`.pyc`-Dateien sollen beurteilt/geraumt werden.

Hausphaenomen: frisch geschriebene .py-Dateien verschwinden aus dem Arbeitsbaum, nur die `__pycache__`-`.pyc` bleibt liegen. Drei Wachen beobachten das. Sie melden nur — sie holen nichts zurueck und loeschen nichts.

## Wo die Wachen stehen

Je Wache ein Hermes-Cron (no_agent, alle 15 min, leere Ausgabe = nichts senden) + Skript unter `Agenten/Hermes/scripts/` + Merkdatei unter `Agenten/Hermes/cache/`:

- `dateischwund-wache.py` beobachtet `Agenten/Hermes/scripts/` → Merkdatei `dateischwund-wache.json` (Keys: `stand`/`gemeldet`/`lauf`)
- `dateischwund-wache-handel.py` beobachtet den Quelltext von `Agenten/Handel/` (ausgenommen .venv, node_modules, daten, cache, logs, state, docs, target) → Merkdatei `dateischwund-wache-handel.json` (Keys: `stand`/`zeit`/`gemeldet`; `gemeldet` = Epoch-Floats)
- `dateischwund-wache-baum.py` beobachtet den ganzen Baum, v. a. `profiles/*/skills/` → Merkdatei `dateischwund-wache-baum.json`

Die drei JSON-Strukturen UNTERSCHEIDEN sich. Nie Schluessel raten — zuerst `list(d.keys())` drucken, sonst liest man `None`-Werte und meldet eine gesunde Wache als tot.

## Ablauf

1. **Lebendigkeit belegen**: Merkdatei-mtime muss juenger als der Cron-Takt sein (frisch = der Cron lief selbst, nicht nur ein Handlauf). Dann jedes Skript von Hand: `python <skript>.py` → Exit 0 + leere Ausgabe = kein Befund.
2. **Meldungen lesen**: das `gemeldet`-Dict zeigt, was die Wache je angekuendigt hat. Praefixe: `merk:` = frueher gemeldeter Schwund (bleibt als Erinnerung stehen), `git:` = Datei stand in HEAD und fehlt im Arbeitsbaum — nur `git:`-Eintraege sind Kandidaten, `merk:`-Eintraege sind Geschichte.
3. **Bestand gegen Arbeitsbaum scannen**: `git ls-files <ordner> | while read f; do test -f "$f" || echo "FEHLT: $f"; done` — findet Dateien im Index, die im Baum fehlen, ohne dass git status sie benennt.
4. **Befund sortieren** (je verdaechtiger Datei):
   - `git cat-file -e HEAD:<pfad>` gelingt UND `git status --porcelain` zeigt ` D` → nur aus dem Arbeitsbaum weg = AKTIVER Schwund, aus HEAD zurueckholen.
   - `git cat-file -e HEAD:<pfad>` schlaegt fehl UND git status zeigt keine ` D` → die Loeschung ist bereits COMMITTET (Hausmechanismus: fremdarbeit-einziehen committet >30-min-alte Loeschungen als 'Fremdarbeit uebernommen'). Kein aktiver Schaden — der Inhalt existiert fast immer weiter (Haupt-Skill-Baum oder Parent-Commit, `git show <commit>^:<pfad>`).
   - `git log --all --oneline -- <pfad>` LEER → die Datei war NIE versioniert (Scratch/Probe). Nicht suchen, nicht wiederherstellen; die verwaiste .pyc ist der einzige Rest.
5. **Loeschung als Absicht erkennen**: dieselben Dateinamen fehlen in vielen Profilen + Ordner-mtimes frisch + Inhalt im Hauptbaum vorhanden = getrimmte Bot-Skill-Sets, kein Schwund. Committete Loeschungen nur zurueckspielen, wenn der Inhalt sonst nirgends existiert.
6. **Verwaiste .pyc raeumen** (Stufe-2-Wegwerf): `for pc in root.rglob('*.pyc'): mod = pc.name.split('.cpython')[0]; (pc.parent.parent / (mod + '.py')).exists()` — fehlt die Quelle UND das Modul war nie in git, ist das Loeschen der .pyc gefahrlos.

## Pitfalls

- **Fehlt die Datei auch in HEAD, ist kein Schwund aktiv.** Committete Loeschung, Inhalt ueber Parent-Commit belegbar. 'Committed' heisst nicht 'Absicht': die Wache kann die Vermisstenmeldung ausgeben, BEVOR die Routine sie committet — der Inhaltsbeweis ist der Parent-Commit bzw. der Hauptbaum, nicht der Git-Status.
- **Getrackte Dateien koennen kurz fehlen und wieder da sein** (parallele Sitzungen verschieben/umbenennen im Arbeitsfluss). Eine `gemeldet`-Zeile mit inzwischen vorhandener Datei ist ein transientes Ereignis, kein Befund.
- **Bot-Profil-Skill-Loeschungen nicht automatisch zurueckspielen** — Profile tragen absichtlich getrimmte Skill-Sets; Quelle ist und bleibt `Agenten/Hermes/skills/`.
- Fremde ' D'-Eintraege (z. B. unter Werkstatt/) sind Arbeit einer parallelen Sitzung: liegen lassen, die Fremdarbeit-Routine uebernimmt sie — nie selbst committen.
- Wachen-None-Werte erst pruefen: die beiden aelteren Wachen tragen `zeit`, nicht `lauf` — Werte aus `list(d.keys())` lesen.

## Bericht an Max (feste Reihenfolge)

1. Gesund/aktiv: Wachen liefen (Zeit der Merkdatei), Exit 0, 0 neue Befunde.
2. Was die Meldungen waren — committete Trims statt Verlust, mit Inhaltsnachweis (Hauptbaum/Parent-Commit).
3. Was repariert wurde (z. B. pyc-Waisen entfernt, verbleibend 0).
4. Was absichtlich NICHT angefasst wurde (fremder ' D'-Eintrag, kein Rueckspielen der Trims).
5. Eine naechste Aktion unter zwei Minuten (meist: nichts, naechster automatischer Check in 15 min).

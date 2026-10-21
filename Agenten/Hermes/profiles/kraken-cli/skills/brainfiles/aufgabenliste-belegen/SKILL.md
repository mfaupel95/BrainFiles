---
name: aufgabenliste-belegen
description: "Use when Behauptungen aus TASKS.md mit Quelldaten belegen."
version: 0.1.0
author: Hermes Agent
license: MIT
category: brainfiles
platforms: [windows]
metadata:
  hermes:
    tags: [Aufgabenliste, TASKS, Belege, Messen, Kanban, Handel]
    related_skills: [aufgabenliste-pflegen, hermes-cron-wartung]
---

# Behauptungen aus der Aufgabenliste mit Quelldaten belegen

Ein Ticket beschreibt einen Zustand ("6 von 40 passen", "der Vorschlag ist
blockiert", "18 Profile tragen eine Liste"). Solche Zahlen sind meist aus einem
Zwischenstand abgeleitet und veralten oder waren nie geprueft. Dieses Skill
sagt, wie man jede Behauptung an der Quelle nachmisst, die Korrektur ins Ticket
schreibt und die Aenderung committet.

**Anlegen und Formatieren** der Liste: `aufgabenliste-pflegen`. Dieses
Skill ist die Beleg-Seite davon.

**Die belegte Entscheidung eintragen** (Config/Notiz aendern, committen,
pushen): `brainfiles-schreibzugriff`.

## When to Use — Wann

- "rechnen und Luecken schliessen", "weiter mit den offenen Punkten"
- ein Ticket behauptet Zahlen (Anzahlen, Bandbreiten, Prozentsaetze)
- ein Ticket behauptet einen Zustand ("blockiert", "fehlt", "ist leer")
- eine Entscheidung soll auf einer Ticket-Zahl beruhen

## Wo die Wahrheit liegt

- Das lebende Board ist `MaxHirn/Archiv/TASKS.md` — eine git-verfolgte Datei im
  BrainFiles-Repo (Branch `master`). Tickets stehen unter `## Offen`.
- Die Kanban-Datenbanken (`Agenten/Hermes/kanban/boards/*/kanban.db`) sind
  NICHT die Quelle: sie tragen alte oder leere Staende, das `default`-Board hat
  nicht einmal eine `tasks`-Tabelle. Wer dort sucht, findet nichts.
- Primaerquelle je Behauptung ist die Datei, die die Arbeit erzeugt hat:
  Journal-CSV, `wachen.json`/`prognose.json`, `config.yaml`, Log. Erst die
  lesen, dann rechnen.

## Ablauf

1. **Behauptungen in pruefbare Zahlen zerlegen.** Jede Zahl und jeden
   Zustandssatz aus dem Ticket als eigene Zeile notieren. "6 von 40" sind zwei
   Zahlen; "blockiert" ist ein Zustand mit einem Beleg (Log/Commit).
2. **Primaerquelle finden.** Die Datei, die die Arbeit schreibt, nicht eine
   Ableitung. Bei mehreren parallelen Buchern (`.csv` + `.hoch/.mittel/.weit`)
   alle zaehlen oder ausdruecklich sagen, welches.
3. **Selbst nachzaehlen, nicht lesen.** Ein kurzes Skript im Scratch-Ordner
   (nie `-c`/Heredoc in der MSYS-bash) liest die Quelle und druckt die
   Verteilung. Vorlage: `scripts/journal-zahlen.py`. *Fertig, wenn* jede
   Ticket-Zahl eine eigene Messung hat.
4. **Vokabular und Schluesselpfad vor dem Zaehlen klaeren.** Ein Buch fuehrt
   fuer dasselbe Ereignis mehrere Aktionsnamen; eine Config fuehrt mehrere
   `disabled`-Schluessel unter verschiedenen Eltern. Erst die tatsaechlichen
   Werte ausgeben, dann filtern.
5. **Korrektur ins Ticket schreiben, nicht ersetzen.** `NACHTRAG`/`KORREKTUR`
   mit Datum unter den bestehenden Kontext. Die alte Zahl stehen lassen und
   benennen, was falsch war — sonst wiederholt sie der naechste Leser.
6. **Committen und pushen** (BrainFiles-Repo). Eine Zeile Commit-Nachricht je
   korrigierter Zahl. Erst `git add <datei>` — nie ein `git add -A` in diesem
   Repo, es liegen fremde Aenderungen im Baum.

## Fallen

- **Ticket-Zahlen driften — immer nachzaehlen.** In einer Sitzung waren drei
  von drei Behauptungen falsch: eine Anzahl um wenige zu hoch, ein Zustand
  ("blockiert") laengst ueberholt, eine Liste als vorhanden beschrieben, die in
  Wahrheit leer war. Aus einem Zwischenstand abgeleitete Zahlen sind eine
  Hypothese, kein Beleg.
- **Gleiches Wort, anderer Schluessel.** `plugins.disabled` und
  `skills.disabled` sind verschiedene Dinge; `[]` ist eine LEERE Liste, kein
  Trim. Vor "Profil X traegt eine disabled-Liste" den vollen Pfad UND die
  Laenge pruefen — und den Elternschluessel, nicht nur das Wort `disabled`.
- **Ein Ereignis, mehrere Aktionsnamen.** Ein Journal kann dieselbe Handlung
  als `EINSTIEG` und als `eroeffnen` fuehren (mit eigenem `grund`). Wer nur
  einen Namen zaehlt, uebersieht die Haelfte — und "0 live" kann "3
  gescheiterte Live-Eroeffnungen" heissen.
- **Zustandsbehauptungen an Commit/Log pruefen, nicht an der Beschreibung.**
  "blockiert" ist widerlegt, wenn ein spaeterer Lauf `angewendet` protokolliert
  und ein Commit genau die Parameter setzt. `anwendungslog.json` + `git show`
  sind der Beleg, nicht das Ticket.
- **Auch der genannte MECHANISMUS ist eine Behauptung.** Ein Ticket kann sagen
  "die Spur faellt in den Kontrakt-Zweig und der liest das Feld" — und der
  Codepfad existiert gar nicht (Spur fehlt in der `WACHEN`-Map, das importierte
  Modul prueft etwas anderes). Vor dem Eintragen den genannten Codepfad LESEN
  (`grep` nach Spur und Feld), sonst schreibt man einen Wert, den niemand
  liest. Das Eintragen selbst: `brainfiles-schreibzugriff`.
- **Delegierte Messung: Ergebnis pruefen, nicht die Zusage.** Ein Subagent, der
  in einer `ls`/`read_file`-Schleife haengt, liefert nichts. Bei kurzen
  Messungen selbst rechnen; bei delegierten den Live-Transkript-Stand ansehen,
  bevor man auf das Ergebnis wartet.
- **Veralteter `git index.lock` blockiert den Commit.** In diesem Repo laeuft
  oft ein zweiter git-Prozess. Kurz warten, dann `rm -f .git/index.lock` — erst
  danach `git add/commit`. Ein Abbruch mit "index.lock: File exists" ist kein
  Inhaltsfehler.

## Antwortform (Hausregel)

- Ergebnis zuerst, danach der Beleg; Zahlen aus der Datei, nicht geschaetzt.
- **Eine** begruendete Empfehlung statt einer Optionsliste.
- Max fuenf sichtbare Punkte je Gruppe, wichtigster zuerst; am Ende genau EINE
  naechste Aktion, unter zwei Minuten machbar.
- Was noch zur Entscheidung liegt, getrennt von dem, was schon belegt ist.

## Beleg-Tiefe

- Wo die Handelsdaten liegen und welches Werkzeug welche Spur messt:
  `references/handel-stack-datenquellen.md`.

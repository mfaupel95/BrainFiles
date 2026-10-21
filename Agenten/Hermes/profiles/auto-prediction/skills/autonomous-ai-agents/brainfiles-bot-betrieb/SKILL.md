---
name: brainfiles-bot-betrieb
description: Use when acting as a BrainFiles repo-bot in the fleet.
version: 1.0.0
author: auto-prediction-bot
license: MIT
metadata:
  hermes:
    tags: [bot-flotte, routing, telegram, gemeinsamer-arbeitsbaum, tickets]
    related_skills: [auto-prediction-harness, hermes-agent]
---

# BrainFiles: ein Bot unter Bots

Der Nutzer betreibt je Fremd-Repo einen Hermes-Bot (ein Profil, ein `terminal.cwd`)
plus Rollen ohne Repo (Wartung, Verteil-Bot, Recherche). Diese Skill regelt, was
gilt, BEVOR man einen Auftrag ausfuehrt: Zustaendigkeit, Verteilung, fremde
Bereiche, Messen im gemeinsamen Baum. Repo-Inhaltliches gehoert in die
profil-eigene Skill, nicht hierher.

## When to Use

- Eine Telegram-/Kanal-Nachricht kommt an, deren Gegenstand nicht mein Repo ist.
- Der Auftrag heisst "verteile", "gib das weiter", "wer ist zustaendig".
- Es geht um fremde Profile (`Agenten/Hermes/profiles/*`), fremde Repos oder das
  Ticket-Board `MaxHirn/Archiv/TASKS.md`.
- Ich soll in einem Baum schreiben, in dem zeitweise eine zweite Sitzung arbeitet
  (BrainFiles-Wurzel), oder pruefen, ob eine Aenderung wirklich gelandet ist.

## Erste Handlung jeder Sitzung

`Agenten\Hermes\profiles\rule_repo-bots.md` lesen (liegt ABSICHTLICH eine Ebene
ueber den Profilen, gilt fuer alle Bots). Sie traegt Stil und Betriebsregeln;
diese Skill traegt das, was beim Anwenden zusaetzlich Zeit kostet.

## Gehoert der Auftrag mir?

- Jeder Kanal-Bot sieht JEDE Nachricht seiner Telegram-Gruppe (eigenes Token,
  gleiches `TELEGRAM_ALLOWED_CHATS`). Ein Auftrag, der an einen anderen Bot
  adressiert ist, kommt trotzdem an - auf eine Frage antworten sonst fuenf Bots.
- Zustaendigkeit MESSEN, nicht raten: `terminal.cwd` aus
  `Agenten/Hermes/profiles/<bot>/config.yaml`, `description` aus `profile.yaml`,
  Rolle aus `SOUL.md`. Passt der Auftrag nicht zu meinem Repo/Arbeitsbereich,
  fuehre ich ihn nicht selbst aus.
- Umgekehrt genauso wichtig: eine Absage ist kein Ergebnis. Ist eine andere Rolle
  zustaendig, den Auftrag DORTHIN bringen (verteilen) und die Verteilung mit dem
  gemessenen Effekt belegen - der Nutzer will die Erledigung, nicht die
  Zustaendigkeitsklaerung.

## Verteilen ist der Hausweg

```bash
cd /c/Users/faupe/Documents/BrainFiles
python Agenten/Werkzeuge/lotse-route.py --liste              # alle Ziele + Beschreibung
python Agenten/Werkzeuge/lotse-route.py --suche <stichwort>  # welches Ziel passt
python Agenten/Werkzeuge/lotse-route.py --an <ziel> "<auftrag>"   # wirklich abschicken
```

- `--an` startet tatsaechlich `hermes.exe -p <ziel> chat -q "<auftrag>"` aus der
  BrainFiles-Wurzel; Kaltstart 30-60 s, inneres Zeitlimit 1800 s.
- Den Auftragstext vollstaendig und woertlich formulieren: Zielpfade, gewuenschtes
  Ergebnis, Sicherungen (Kopie vorher) und was NICHT getan werden soll. Das Kind
  hat keinen Gespraechskontext.
- Mehrere unabhaengige Auftraege an den `lotse`-Bot (er ist der Verteiler), nicht
  selbst nacheinander abarbeiten.
- Nennt `--suche` kein Ziel, ist die zustaendige Rolle eine Werkzeugkette/eine
  Sitzung (z.B. `Agenten/Handel`) statt eines Bots: dann den Auftrag mit exakten
  Dateipfaden uebergeben und sagen, wer ihn ausfuehrt - nicht selbst hineinschreiben.

## Fremde Bereiche: nicht schreiben

- Nicht in fremde Profile (`Agenten/Hermes/profiles/*/config.yaml`) oder fremde
  Repos schreiben - ausser es ist ausdruecklich MEIN Auftrag.
- Live-nahe Konfiguration (`Agenten/Handel/*/wachen.json`, `prognose*.json`, alles
  mit `handel_erlaubt`) nie selbst editieren: daran haengen Freigaben und Orderwege.
  Solche Tickets werden verteilt, nicht ausgefuehrt.
- Das gemeinsame Board ist `MaxHirn/Archiv/TASKS.md` (`T-0NN`, Status
  `[ ] [~] [?] [!] [x]`). Nutzer-Entscheidungen kommen als kurze Bestaetigungen auf
  Ticket-Nummern; ohne Auftrag dort nichts aendern.

## Messen statt glauben im gemeinsamen Arbeitsbaum

- Vor jedem Schreiben `git status --porcelain` im BrainFiles-Baum: es arbeitet
  zeitweise eine zweite Sitzung im selben Baum (`MM` = Index UND Arbeitsbaum
  geaendert). Nur eigene Pfade stagen, nie `git add -A`, nie `git stash`.
- Ob eine Aenderung wirklich gelandet ist: Arbeitsbaum gegen HEAD vergleichen und
  ZAEHLEN statt lesen - `git show HEAD:<pfad>` und die Trefferzahl programmatisch
  vergleichen (z.B. Eintraege unter `skills.disabled`).
- Reine Zeilenenden-Aenderung isolieren:
  `git diff --ignore-cr-at-eol --numstat -- <pfad>`. Meldet das `0/0`, waehrend
  `git diff --numstat` hunderte Zeilen zeigt, unterscheidet sich nur CR/LF - vor
  dem Commit klaeren, sonst geht die Datei mit gemischten Enden in den Index.
- Ein abgeschickter `--an`-Lauf, der das Zeitlimit MEINES Aufrufs ueberschreitet,
  ist nicht gescheitert: das Kind laeuft weiter. Nicht neu abschicken (das startet
  einen zweiten Schreiber am selben Baum), sondern den Effekt im Baum messen und
  den laufenden Prozess in Ruhe lassen.

## Antwortform fuer den Nutzer

- Deutsch, Ergebnis zuerst, nummerierte Punkte, hoechstens 5 sichtbare Punkte,
  EINE begruendete Empfehlung, am Ende genau EINE naechste Aktion.
- Jede Zahl im Bericht stammt aus einem gemessenen Befehl (kein Gedaechtniswert).
  Fremde Analyse-Texte sind Zwischenstaende, keine Quelle: Git-Stand und
  Datei-Inhalt immer selbst nachmessen, bevor man sie als Befund weitergibt.

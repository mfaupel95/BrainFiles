---
name: topic-router
description: "Use when mehrere Themen gemischt: ein Agent je Thema."
category: autonomous-ai-agents
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [delegation, orchestration, routing]
    related_skills: [subagent-delegation]
---

# TOPIC-Router: Jedes Thema bekommt seinen eigenen Agenten

## When to Use

Eine Anfrage, die mehrere in sich geschlossene Arbeitsstraenge mischt — z. B.
«Pruef den Git-Stand UND trag die offenen Tasks nach» oder «Repariere X und
hole parallel die Zahlen fuer Y». Der Router zerlegt sie in Themen und startet
je Thema GENAU EINEN Agenten; er selbst fuehrt keine Themenarbeit aus, sondern
prueft und fuehrt zusammen.

## Der Router-Prompt

Kurzfassung hier; die vollstaendige, kopierfertige Fassung liegt in
`references/router-prompt.md` — zum Einfuegen in ein Profil (SOUL.md), einen
Delegations-Brief oder die eigene Arbeitsanweisung.

> DU BIST DER TOPIC-ROUTER. Du fuehrst keinen Auftrag selbst aus — du zerlegst
> ihn in Themen und gibst jedes Thema GENAU EINEM eigenen Agenten.
> 1) THEMEN BESTIMMEN: ein Thema ist ein Arbeitsstrang, der fertig wird, ohne
>    ein anderes Thema gelesen zu haben (eigene Dateien, eigene Werkzeuge,
>    eigene Kriterien). Zwei Themen, die dieselben Dateien brauchen, sind EIN
>    Thema. Lieber zwei echte Themen als fuenf Kunst-Themen.
> 2) JE THEMA EIN AGENT: N Themen -> N Agenten, alle parallel. Jeder bekommt
>    NUR seinen Thementeil (Fragestellung, Kontext, Ergebnis-Vertrag). Ein
>    Agent fasst nie ein anderes Thema an, auch nicht «kurz mit».
> 3) EIN THEMA = KEIN Router-Fall: normal bearbeiten, kein Agent noetig.
> 4) PRUEFEN + ZUSAMMENFUEHREN: jeder Agent-Bericht ist Selbstauskunft —
>    Belege gegen den Baum halten, bevor «erledigt» gesagt wird. Konflikte
>    zwischen Themen ausdruecklich benennen. Die Antwort fuehrt jedes Thema
>    als eigenen Abschnitt, am Ende genau eine Empfehlung und eine naechste
>    Aktion.  

## Mechanik (im Hermes-Haus)

1. **Themen bestimmen** — die Anfrage einmal laut zerlegen, ehe Werkzeuge
   laufen. Zaehlt man mehr als zwei Themen, ist der Router-Fall sicher; bei
   einem klaren Hauptthema mit einem Nebenwunsch ebenfalls (Nebenwunsch wird
   ein eigener Agent, Hauptthema bleibt bei der Sitzung oder ist der zweite).
2. **Je Thema ein Agent** — ein `delegate_task` mit genau so vielen
   `tasks`-Eintraegen wie Themen; KEIN Platzhalter-Eintrag (kostet einen
   Parallel-Slot und laeuft sinnlos). Jeder `context` nennt: das Thema, die
   Pfade, die Regeln/Verbote, den Ergebnis-Vertrag als EINZEILIGE Prosa
   (kein `output_schema` fuer Artefakte — ein Schema auf Prosa-Arbeit
   erzeugt die «Antwortform verfehlt»-Schleife).
3. **Waehrend die Kinder laufen** — eigene, unabhaengige Arbeit machen und
   den Zug beenden; Ergebnisse kommen zwischen den Zuegen. Nicht pollen.
4. **Pruefen und zusammenfuehren** — jeden Bericht gegen die eigenen Belege
   halten (git status, Dateien, Zahlen), Konflikte benennen, dann EINE
   Antwort mit einem Abschnitt je Thema.

## Grenzen

- **Arbeitsstraenge muessen disjunkt sein.** Zwei Kinder im selben Baum
  serialisieren sich ueber gemeinsame Lock-/Zieldateien und kollidieren bei
  derselben Datei. Ueberlappende Themen zusammenlegen (Regel oben), nicht
  parallel starten.
- **Eine offene Entscheidung gehoert NICHT ins Kind.** Ein Goal der Form
  «baue X so, dass es zu Y passt» laesst das Kind konstruieren statt
  ausfuehren und verbrennt sein Budget. Wer die Entscheidung selbst treffen
  kann, schreibt sie in den `context` («haenge an die BESTEHENDE Zeile an»)
  und laesst nur noch ausfuehren; ist sie wirklich offen, zurueck an den
  Nutzer statt raten.
- **Kinder lesen von Null.** Alles, was das Kind vor der ersten Zeile lesen
  muss, steht im `context` (Anker: Datei, Funktion, Zeile, der zu ersetzende
  Text). Ein Kind, das die Umgebungsfalle nicht kennt, schreibt in eine Kopie,
  die verschwindet, und meldet trotzdem Erfolg.
- **Ausfuehrungsarbeit gehoert aufs billige Modell.** Lesen, Befunde deuten
  und die eine Empfehlung formuliert die Sitzung; Umsetzen geht an die Kinder
  (Regel aus subagent-delegation).

## Abgrenzung

- `subagent-delegation`: der technische Unterbau — Kette pruefen, Fehler
  deuten, Transcript lesen. Der TOPIC-Router ist die Aufteilungs-Entscheidung
  davor.
- `a2a-telegram-skills` / Bot-Profil `lotse`: Verteilung auf feste Bot-Profile
  (ein Bot je Repo). Der Router verteilt THEMEN, nicht Profile.
- Profil-/Config-Fragen: `hermes-config-ops`.

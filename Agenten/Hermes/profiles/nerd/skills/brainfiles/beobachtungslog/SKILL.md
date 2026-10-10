---
name: beobachtungslog
description: Use when ein Skill-Verbesserungsbedarf auffaellt. Beobachtung als Markdown loggen.
version: 0.1.0
author: Hermes
platforms: [windows]
metadata:
  hermes:
    tags: [Skills, Beobachtung, Selbstverbesserung, BrainFiles]
---

# Beobachtungslog — Skill-Verbesserung aus echter Arbeit

Schlanker Eigenbau nach Bewertung des fremden Claude-Meta-Skills „Task
Observer / One Skill to Rule Them All" (Eoghan Henn, rebelytics.com, CC BY
4.0) — siehe `Wissen/Task-Observer-Metaskill.md`. Übernommen wurden nur das
**Prinzip** (Beobachtungen aus echter Arbeit sammeln statt Skills nur
reaktiv zu pflegen) und das **Dateiformat** (ein Markdown pro Beobachtung,
Frontmatter). Bewusst NICHT übernommen: die 11.076-Token-Hauptdatei, die
Aktivierungspflicht vor jedem Tool-Aufruf, der Id-Verhandlungs-Mechanismus
mit Kollisions-Schutz, die Sibling-Familien-Prüfung — das läuft der
Skill-Ausmist-Linie vom 11.09.2026 zuwider (127→48 Skills, ~4.380→~1.248
Tokens/Anfrage).

## When to Use

- Eine Korrektur von Max zeigt: ein Skill fehlt eine Regel, oder die Regel
  wird nicht durchgesetzt.
- Ein manuelles Muster wiederholt sich zum zweiten Mal im selben Auftrag
  oder über Sitzungen hinweg (z. B. „schon wieder ein Attachment manuell
  ins Vault übertragen").
- Max fragt direkt: „Beobachtungen?", „was ist dir aufgefallen?", „Task
  Observer".
- **Nicht verwenden für:** einmalige Korrekturen ohne Wiederholwert,
  Vorlieben, die schon in einem Skill stehen, Bugs ohne Methodik-Bezug.
  Testfrage: würde das auch in einem anderen Projekt/Auftrag Sinn ergeben?
  Eher nein → gehört in den Auftragskontext, nicht ins Log.

## Storage

`MaxHirn/Wissen/Beobachtungen/log/` — ein Markdown pro Beobachtung, in Git
(Wissen/ ist bereits per `.gitignore`-Freigabe `!MaxHirn/Wissen/**/*.md`
versioniert, kein Nachtrag nötig). Dateiname
`JJJJMMTT-HHMMSS-kurzer-slug.md` — der Zeitstempel ersetzt die
Id-Verhandlung des Originals: parallele Sitzungen (in diesem System
Alltag, siehe Memory „ARBEITSBAUM") kollidieren praktisch nie, weil jede
ihren eigenen Zeitstempel schreibt, ohne eine gemeinsame Zähler-Datei zu
lesen oder zu sperren.

## Procedure

1. **Beobachtung sofort schreiben**, nicht im Kopf vormerken — im selben
   oder nächsten Werkzeug-Aufruf, per `write_file` nach
   `MaxHirn/Wissen/Beobachtungen/log/<Zeitstempel>-<slug>.md`:

   ```markdown
   ---
   id: JJJJMMTT-HHMMSS
   title: Kurzer Titel
   status: open            # open | actioned | declined | parked
   skill: [betroffener-skill]   # Liste, existierender Skill-Name; kann leer sein
   proposes_skill:         # Liste neuer Skill-Namen; kann leer sein
   date: JJJJ-MM-TT
   session_context: Worum ging es im Auftrag
   parked_until:           # nur bei status: parked
   resolved:               # Datum, nur wenn nicht mehr open
   resolution:             # was gemacht wurde, nur wenn nicht mehr open
   ---

   **Beobachtung:** Was ist passiert, so konkret, dass es in vier Wochen
   ohne das Gespräch verständlich ist.

   **Vorschlag:** Konkrete Änderung — bei bestehendem Skill den Abschnitt
   nennen, bei neuem Skill Umfang und Kernbausteine.

   **Prinzip:** Die verallgemeinerbare Lehre — das wichtigste Feld.
   ```

2. **Ziel prüfen.** Ein Name in `skill:` muss ein Skill sein, der
   tatsächlich existiert (`search_files(pattern=name, target='files',
   path='Agenten/Hermes/skills')`) — sonst gehört er in
   `proposes_skill:`.
3. **Am Sitzungsende oder auf Zuruf zusammenfassen.** Nicht automatisch
   handeln — nur auflisten (gruppiert nach `skill:`), eine Zeile je
   Beobachtung, und fragen, welche jetzt umgesetzt werden sollen.
4. **Umsetzen nur auf einen dieser drei Wege:** (a) expliziter Auftrag
   („setz Beobachtung X um"), (b) die Beobachtung zeigt, dass ein Skill
   gerade falsch läuft und Max das sofort wissen muss, (c) eine
   gelegentliche manuelle Sammelrunde („zeig offene Beobachtungen").
   Danach `status`, `resolved`, `resolution` im selben Schritt
   nachziehen — die Datei wird direkt bearbeitet (`patch`), nicht neu
   geschrieben.

## Quick Reference

- Offene Beobachtungen zählen: `search_files(pattern='status: open',
  path='MaxHirn/Wissen/Beobachtungen/log', target='content')`
- Nach Skill filtern: `search_files(pattern='skill:.*<name>', ...)`
- Neue Beobachtung: `write_file` nach `MaxHirn/Wissen/Beobachtungen/log/<JJJJMMTT-HHMMSS>-<slug>.md`
- Bestehende ändern: `patch` auf genau diese eine Datei, nie die
  Verzeichnis-Inhalte neu schreiben

## Pitfalls

- **Kein Ersatz für `hermes curator usage`.** Der Curator misst
  Nutzungshäufigkeit (welcher Skill lädt wie oft), dieses Log erfasst
  WARUM ein Skill nicht reicht. Beide ergänzen sich, keiner ersetzt den
  anderen.
- **Kein Automatismus vor jedem Tool-Aufruf.** Das war der Kernfehler des
  Originals für dieses System — die Beobachtung entsteht bewusst, wenn
  ein Muster tatsächlich auffällt, nicht als Pflichtprüfung jeder Aktion.
- **Keine Zugänge/Geheimzahlen in `session_context` oder `Beobachtung`.**
  `Wissen/Zugaenge.md`-Inhalte, Handelszahlen mit Kontobezug — nach den
  Schutzregeln draußen halten, auf die Regel verweisen statt den Wert zu
  zitieren.
- **Ein leeres `search_files`-Ergebnis bei bekanntem Inhalt ist ein
  Warnsignal**, kein „keine offenen Beobachtungen" — Pfad und Muster
  gegenprüfen, bevor „nichts offen" behauptet wird.

## Verification

Eine Beobachtung ist sauber geloggt, wenn die Datei unter
`MaxHirn/Wissen/Beobachtungen/log/` mit vollständigem Frontmatter
(`id`, `title`, `status`, `date`, `session_context`) existiert und
`git status` sie als neue Datei zeigt (Stufe-2-Bereich in
`Wissen/` — commitbar wie jede andere Notiz, siehe `brainfiles-auftrag`).

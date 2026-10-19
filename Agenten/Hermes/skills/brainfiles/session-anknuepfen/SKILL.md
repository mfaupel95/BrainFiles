---
name: session-anknuepfen
version: 0.1.0
author: Hermes
description: "Letzte offene Session mit offenem Handlungsbedarf finden."
metadata:
  hermes:
    tags: [Sitzung, Fortsetzen, OffenePunkte, BrainFiles]
---

# Session anknuepfen

Findet die letzte (juengste) Session mit offenem Handlungsbedarf oder nicht
umgesetzter Empfehlung, oeffnet ihren Stand und arbeitet die offenen Punkte
weiter. Es schliesst NICHT Sessions zusammen und macht keinen Sammeleinkauf
ueber alle Altlasten (das ist `sammelauftrag`); es nimmt genau EINE Session
und fuehrt sie zu Ende. Fremde Arbeit im Baum wird dabei gelesen, aber nie
mitcommittet.

## When to Use

- "Letzte offene Session oeffnen und anknuepfen" (Originalauftrag 19.09.2026).
- "Wo waren wir stehengeblieben?", "Was war offen?", "Anknuepfen an letzte Sitzung".
- "Nicht umgesetzte Empfehlung umsetzen" / "Offenen Handlungsbedarf abarbeiten".
- Nach einem Abbruch oder einer Zeitluecke weiterarbeiten.

## Prerequisites

- BrainFiles-Repo-Wurzel (hier: C:\Users\faupe\Documents\BrainFiles) als
  Arbeitsverzeichnis; Terminal laeuft in bash/MSYS, PowerShell-Aufrufe nur mit
  -NoProfile und einfachen Anfuehrungszeichen.
- Zugriff auf `session_search` (Hermes-Session-Speicher, query + session_id).

## How to Run

1. Offene-Punkte-Quellen einsammeln (alle unabhaengig parallel):
   - `session_search` mit den Stichworten "offen", "naechster Schritt",
     "Entscheidung Max", "nicht umgesetzt", "TODO" - neueste Treffer zuerst.
   - `git status --porcelain` im Repo (uncommittete/fremde Aenderungen).
   - `Werkstatt/` auf Uebergaben/Durchgangsware pruefen (search_files).
   - Offene Fristen: `read_file` MaxHirn/Wissen/Fristen.md.
   - Hermes: cron-Outputs unter Agenten/Hermes/cron/output/ und
     delegation-Transkripte unter Agenten/Hermes/cache/delegation/live/.
2. Kandidaten nach Zeitstempel sortieren; die NEUESTE Session mit offenem
   Punkt waehlen und ihr Transkript via `session_search` (query=
   Session-Kennung oder Stichwort, session_id=...) oeffnen.
3. Stand extrahieren: Was ist fertig? Was ist offen (Handlungsbedarf /
   Empfehlung)? Welche Kontextfaeden (Dateien, Commits, PIDs) gehoeren dazu?
4. Offene Punkte der Reihe nach ABARBEITEN, jeder Schritt mit echtem Lauf
   belegt (Test, Befehl, Lesevorgang), nicht nur beschreiben.
5. Eigenen Arbeiten committen: `git add` mit EXPLIZITER Pfadliste (nie
   `git add -A`), Commit, ggf. push. Fremde Aenderungen liegen lassen.
6. Abschlussbericht: Was jetzt konkret funktioniert, was absichtlich NICHT
   angefasst wurde (Fremdarbeit, laufende Prozesse), und welche Entscheidung
   noch auf Max wartet.

## Quick Reference

- session_search(query="<stichwort>", session_id="<id>") - Sitzung finden/lesen.
- bash: `git status --porcelain`, `git log --oneline -5`, explizites `git add <pfad>...`.
- Geschaetzte Dauer: Finden + Lesen ~5 min, Abarbeiten 30-120 min je Komplexitaet.

## Procedure

1. `git status --porcelain` (<repo>) - sieht fremde und eigene Aenderungen.
   ACHTUNG: Es kann eine ZWEITE Hermes-Sitzung auf demselben Baum laufen
   (Sibling-Subagent) - deren Aenderungen sind fremd und bleiben liegen.
2. `session_search` mit offenen-Punkte-Stichworten; die neueste Treffer-Session
   oeffnen. War die Session komprimiert ("[SKILL_PRUNED]" oder
   "CONTEXT COMPACTION"), den genannten session_id-Anker fuer
   `session_search` nutzen, um verlorene Details zurueckzuholen.
3. Aus dem Transkript die offenen Punkte als Liste ziehen. Jede Behauptung
   aus Selbstberichten VERIFIZIEREN: Commit-Hash mit `git branch -r --contains`
   bzw. `git log` pruefen, Dateien mit `read_file`/`ls` nachweisen. Ein
   gemeldeter Commit, der nirgends existiert, ist ein Falschbefund.
4. Punkte in sinnvoller Reihenfolge abarbeiten (erst deterministische Fixes,
   dann Verdrahtung, dann Betriebseingriffe wie Neustarts). Vor jedem
   schreibenden Zugriff Schutzregeln (MaxHirn/Wissen/Schutzregeln.md) beachten.
5. Betriebsneustart (z. B. Dauerlauf nach SPUREN-Aenderung): Prozesse per
   `powershell.exe -NoProfile` + Get-CimInstance finden (CommandLine-
   Filter, NICHT nur Prozessname), PID-Dateien lesen, mit `taskkill /F /T
   /PID <nr>` beenden (im bash: EINFACHER Slash, // wird nicht konvertiert),
   dann Start-ScheduledTask. Wrapper-Tasks enden selbst auf "Ready", der
   Prozess laeuft losgeloest weiter - also den Prozess pruefen, nicht den
   Task-State.
6. Committen nur eigene Pfade. Danach `git status` nochmals: fremde
   Dateien muessen unangetastet im Baum stehen.

## Pitfalls

- `git add -A` verboten: es nimmt Fremdarbeit mit (Sibling-Subagent fuehrt
  Aenderungen auf demselben Baum, z. B. Bus/stand.json).
- Die gefundene "letzte Session" kann NOCH LAUFEN: vor dem ersten eigenen
  Schreibzugriff ihre letzte Aktivitaet messen (juengste Message im
  session_search-Scroll, frische mtimes, neue Commits). Ist sie aktiv oder
  eben erst aktiv gewesen, nichts schreiben und nicht committen - geteilter
  Index heisst, ihr Commit nimmt eigene Dateien mit oder umgekehrt. Kurz
  warten, erneut pruefen, erst bei Ruhe uebernehmen; ihre uncommittete
  Arbeit faellt sonst dem Fremdarbeit-Lauf in den eigenen Namen.
- Selbstberichte sind keine Belege: einen gemeldeten Commit/Push vor dem
  Weitermachen gegen Git pruefen (Hash in origin/master?).
- `taskkill //F` im bash scheitert mit "Argument/Option ungueltig" - dort
  ist die MSYS-Pfadkonvertierung abgeschaltet; EINFACHER Slash verwenden.
- Offene Entscheidungen (z. B. "Key geben oder skip", "interaktive Einrichtung")
  nicht stillschweigend vorentscheiden: als offene Punkte im Abschlussbericht
  nennen, bis Max antwortet.
- Skills mit [SKILL_PRUNED] vor Nutzung neu laden (skill_view) - der Inhalt
  ist sonst unbrauchbar.

## Verification

Ablauf gilt als gelungen, wenn: (1) mindestens ein offener Punkt mit echtem
Lauf abgearbeitet und committet ist (git log zeigt den Commit), (2) `git
status` keine fremden Dateien in den Commit gezogen hat, (3) der Bericht die
noch offenen Entscheidungen fuer Max benennt.

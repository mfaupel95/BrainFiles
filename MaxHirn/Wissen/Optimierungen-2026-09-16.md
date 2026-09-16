---
id: 20260916-optimierungen-finden
title: 'Optimierungen finden'
tags: [betrieb]
created: 2026-09-16
updated: 2026-09-16
related: [20260830-routinen]
summary: 'Wöchentliche Prüfung der Routinen selbst — Läufe ohne Ende-Zeile, Leichen in der Aufgabenplanung, Prozess-Drift. Warum die Systemprüfung das nicht sieht, was am 16.09.2026 gefunden wurde und wie es belegt wird.'
---

# Optimierungen finden

Auf Max' Anweisung vom 16.09.2026 gebaut: eine Routine, die nicht die Daten
nachmisst, sondern **die Routinen selbst** — damit ein Lauf, der still
abgebrochen ist, nicht monatelang wie ein ordentlicher Lauf aussieht.

| | |
|---|---|
| Zeitplan | montags 09:45 ([[Routinen]]) |
| Aufgabe | `MaxHirn-Optimierungen-Finden`, angelegt über `Routinen/optimierungen-finden-aufgabe.ps1` |
| Rechnung | `Agenten/Hermes/scripts/optimierungen-finden.py` (nur Standardbibliothek, nur lesend) |
| Hülle | `Agenten/Routinen/optimierungen-finden.ps1` (Protokoll + Bus-Meldung) |
| Protokoll | `Routinen/logs/optimierungen-finden-letzter-lauf.log` |
| Meldung | als `hinweis` über den Bus — nur bei Befund, nie bei Befundfreiheit |

## Die Lücke, die sie schließt

**Ein abgebrochener Lauf meldet nichts.** Wird eine Aufgabe von außen beendet
(Herunterfahren, Absturz, `Stop-ScheduledTask`), schreibt der Wrapper keine
Ende-Zeile ins Protokoll — und der Bus wertet nur *Ende*-Ereignisse aus. Es gibt
also kein Ereignis, das gemeldet werden könnte. Der Lauf ist im Journal nicht
als Fehler sichtbar, sondern gar nicht.

**Die Systemprüfung sieht es nicht.** `Routinen/systempruefung.ps1` hält einen
Ergebniscode wie `3221225786` (0xC000013A, von außen beendet) für unauffällig —
zu Recht: ein Wächter, der bei jedem Herunterfahren abgeschnitten wird, wäre
sonst Dauerfeuer. Nur bei der *Sicherung* ist derselbe Code ein Befund.

## Woran es messbar ist

Jede Wrapper-Routine im Ordner `Routinen/` schreibt nach demselben Muster: als
erste Zeile `=== Lauf <Zeitstempel> ===`, am Ende eine Zeile, die mit `ENDE`
beginnt (`ENDE ok …` oder `ENDE FEHLER …`). Das ist der Prüfstein:

- Kopfzeile vorhanden, **keine** Ende-Zeile, Aufgabe läuft nicht gerade
  → angefangen und nicht zu Ende gelaufen.
- Ende-Zeile mit `FEHLER` → Lauf ist durchgelaufen und hat einen Fehler gemeldet.

Dauerlauf-Protokolle (wachsen endlos) und Berichte (`.md`) haben keine
Ende-Zeile — ohne die Kopfzeilen-Bedingung wären sie Dauerbefunde.

## Was am 16.09.2026 gefunden wurde

Der erste Lauf hat zwei echte Befunde und keine Fehlalarme geliefert:

1. **Sicherung 20:00 abgebrochen** (0xC000013A, Rechner ging aus). Im Protokoll
   `sicherung-letzter-lauf.log` stand danach nur die Kopfzeile. Die nächste
   Sicherung holt den Rückstand nach, weil robocopy den Unterschied kopiert —
   gemerkt hat es bis dahin niemand.
2. **Zweitkopie gescheitert**: der vom Anmelde-Trigger nachgeholte Lauf um
   21:08:40 endete mit `robocopy-Code 11 - FEHLER`, Exitcode 1, nach 59 s statt
   der üblichen 8 s. `J:` hat 479 unkorrigierte Lesefehler (siehe
   `Wissen/Hardware.md`); ein Kopierziel mit Lesefehlern meldet genau so.
3. **Zahlen beim ersten Lauf**: 84 Python-Prozesse, 3.652 MB, davon 28
   MCP-Server-Prozesse in vier Sätzen (je ein Satz pro laufendem Hermes-Prozess),
   0 verwaiste MCP-Server.

**Kandidat, den die Maschine nicht findet:** `DCA-Faelligkeit` (ruft
`Handel/agent.py check`) und `MaxHirn-DCA-Pruefung` (ruft `Routinen/dca-pruefung.ps1`)
tun dasselbe. Solche *semantischen* Doppelungen sind maschinell nicht sicher
erkennbar — dafür bräuchte es eine Liste bekannter Paare, und die wäre schneller
veraltet als nützlich. Bleibt Handarbeit.

## Wie man es belegt

```powershell
# Rechnung mit allen Zahlen, ohne Zustand zu schreiben:
python Agenten\Hermes\scripts\optimierungen-finden.py --alles --ohne-state

# Hülle wie aus dem Zeitplan:
powershell -ExecutionPolicy Bypass -File Agenten\Routinen\optimierungen-finden.ps1

# Zustand der Aufgabe und der nächste Termin:
Get-ScheduledTaskInfo -TaskName 'MaxHirn-Optimierungen-Finden' |
  Format-List LastRunTime, LastTaskResult, NextRunTime

# Was der Bus daraus gemacht hat:
Select-String optimierungen-finden Agenten\Bus\journal\$(Get-Date -Format yyyy-MM-dd).jsonl
```

Erwartet: `LastTaskResult 0`, im Bus drei Zeilen (`start`, `ende` Code 0,
`hinweis` mit dem Befund), und die Meldung auf dem Handy.

## Grenzen

- Sie sieht nur Aufgaben mit Wrapper und dem Muster `=== Lauf …` / `ENDE …`.
  `BrainFiles-Bus`, `DCA-Faelligkeit` und die Hermes-Cron-Jobs
  (`bus-waechter`, `repo-updates-check`, `skill-usage-report`) fallen dadurch
  durch — deren Ausfall bleibt ungemeldet.
- Der Prozess-Vergleich ist ein Drift-Signal, kein Beweis: gemeldet wird erst
  ab +500 MB oder +10 Prozessen gegenüber dem letzten Lauf.
- **Sie ändert nichts.** Kein Löschen, kein Starten, keine Aufgabe wird
  entfernt. Was gemeldet wird, entscheidet ein Mensch — dieselbe Regel wie beim
  Verbesserer (`Agenten/Handel/verbesserer/`).
- Der Zustand für den Vergleich liegt in
  `Routinen/logs/optimierungen-finden-state.json` (im Protokollordner, nicht im
  Vault — er ist Messwert, keine Notiz).

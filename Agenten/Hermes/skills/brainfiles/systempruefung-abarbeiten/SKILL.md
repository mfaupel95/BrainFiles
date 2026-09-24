---
name: systempruefung-abarbeiten
description: Arbeite den Systempruefungsbericht ab.
version: 0.1.0
author: Hermes Agent
license: MIT
category: brainfiles
platforms: [windows]
metadata:
  hermes:
    tags: [Systemcheck, Befunde, Wachen, Reparatur, BrainFiles]
    related_skills: [systemdiagnose, betriebsrunde, trugschluesse, arbeitsbaum-git-hygiene]
---

# Systempruefung abarbeiten

Nimmt den letzten Bericht `Agenten/Routinen/logs/systempruefung-letzter-lauf.md`,
belegt jeden Punkt, behebt ihn, weist die Behebung mit einem echten Lauf nach und
sichert alles. Es ist **keine neue Diagnose** (dafuer `systemdiagnose`), kein
Sammeln (`sammelauftrag`) und kein Einzelauftrag (`brainfiles-auftrag`). Neue
Abhaengigkeiten gibt es nicht: PowerShell 5.1, Stdlib-Python, git.

## When to Use

- "letzte Systempruefung abarbeiten", "was steht in der Nachtpruefung", "die Punkte der Pruefung"
- der Morgenbericht ist da und soll weggearbeitet werden
- ein Punkt der Pruefung wurde schon oefter gemeldet und niemand hat ihn entschieden
- der Bericht wirkt alt, aber der Aufgabenzustand sagt "Ready"

## Prerequisites

- Arbeiten aus der Repo-Wurzel (`C:\Users\faupe\Documents\BrainFiles`).
- `terminal` laeuft hier ueber git-bash; PowerShell-Aufrufe gehen mit
  `powershell -NoProfile -Command "..."`.
- Admin-Aufgaben (`Start-/Stop-ScheduledTask` sind ohne Erhoehung moeglich,
  `Set-/Register-/Disable-ScheduledTask` nicht) in EIN Skript buendeln und per
  `Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile','-File','<pfad>'`
  ausloesen; danach nachmessen.

## How to Run

1. Bericht mit `read_file` oeffnen: `Agenten/Routinen/logs/systempruefung-letzter-lauf.md`.
2. Erstanweisung des Skripts, wenn der Bericht alt ist:
   `terminal`: `powershell -NoProfile -ExecutionPolicy Bypass -File Agenten/Routinen/systempruefung.ps1`
3. Alterswache von Hand: `terminal`:
   `Agenten/Handel/scanner/.venv/Scripts/python.exe Agenten/Hermes/skills/brainfiles/systempruefung-abarbeiten/scripts/berichts-alter.py`
   (jede Python 3.10+ tut es — das Skript nutzt nur die Standardbibliothek)

## Quick Reference

```
Bericht          Agenten/Routinen/logs/systempruefung-letzter-lauf.md
Vollprotokoll    Agenten/Routinen/logs/systempruefung-<JJJJ-MM-TT>.log  (muss mit einer Ende-Zeile enden)
Skript           Agenten/Routinen/systempruefung.ps1
Arbeitsbaum      powershell -NoProfile -ExecutionPolicy Bypass -File Agenten/Routinen/arbeitsbaum-pruefen.ps1
Fremdarbeit      powershell -NoProfile -ExecutionPolicy Bypass -File Agenten/Routinen/fremdarbeit-einziehen.ps1 -Testlauf
Aufgaben         Get-ScheduledTask -TaskName 'MaxHirn-*' | ForEach-Object { $i=Get-ScheduledTaskInfo $_.TaskName; '{0,-42} {1,-9} {2,-4} {3}' -f $_.TaskName,$_.State,$i.LastTaskResult,$i.LastRunTime }
Sicherung prüfen powershell -NoProfile -ExecutionPolicy Bypass -File Agenten/sichern.ps1   (Handlauf, ~4 min)
```

Nicht-0-Codes: `0` sauber, `267009` laeuft, `267014`/`1073807364` von aussen
beendet (bei Dauerlaeufen normal), `2147946720` laeuft schon, `3221225794`
(C0000142) kam nicht hoch, `1` ist ein echter Skriptfehler. Ein Code wird erst
zum Befund mit dem eigenen Protokoll daneben.

## Procedure

1. **Berichtsdatum gegen heute pruefen — VOR allen Befunden.** Steht im Kopf
   `# Systempruefung <Datum>` von heute, ist die Lage frisch. Ist es aelter als
   der letzte geplante Lauf (taeglich 07:00), wurde der Lauf abgebrochen: die
   Punkte darin sind Geschichte, und der eigentliche Befund ist der Pruefer
   selbst. Zweiter Zeuge: das Ende von `systempruefung-<heute>.log` — fehlt die
   Ende-Zeile, wurde der Lauf gekillt (in der Aufgabenplanung dann `267014`).
2. **Protokoll bis zum Abbruchort lesen** (`read_file`, die letzte
   Blockmarke `--- n) ... ---` vor dem Ende ist der Haenger). Ein Block, der
   ungeschuetzt ein fremdes System aufruft (Docker, Netz, Dienst), wartet
   unbegrenzt — dann Zeitgrenze einbauen, nicht nur neu starten.
3. **Jeden Punkt einer Klasse zuordnen:** laufender Zustand (Datei/Prozess),
   Aufgabe mit Code, Konfig-Drift, Portabilitaet, Whitelist-Kandidat
   (Dauerfehlalarm), Fremdarbeit im Baum. Fuer jede Klasse gilt der Beweisweg
   aus `betriebsrunde`.
4. **Wiederkehrende Zeilen in eine Whitelist mit Grund** (im Skript: Muster
   `$gewolltDeaktiviert`, `$gewolltStores`, `$ausgenommen`, Fremd-Baum-Ausschluss
   in Block 6). Nur den NAMEN freistellen, nie eine Loeschung — ein Store oder
   eine Aufgabe, die nicht in der Liste steht, wird weiter gemeldet. Ohne das
   deckt der Dauerfehlalarm die echten Neufunde zu.
5. **Fremdaufrufe im Pruefer mit Zeitgrenze versehen** (Muster DockerMitFrist:
   `System.Diagnostics.Process`, `WaitForExit($Sekunden*1000)`, Ausgabe mit
   `ReadToEndAsync()` lesen, bei Frist `Kill()` und `$null` zurueck). Den
   Zeitueberschreitungs-Fall als EIGENEN Befund melden, nicht als "alles ok".
6. **Beheben, dann mit einem echten Lauf beweisen.** `git diff --numstat` je
   Datei (wenige Zeilen = gewollt, ganze Datei = Zeilenenden verstellt);
   Python: `scanner/.venv/Scripts/python.exe -m py_compile <datei>` plus eine
   Pfadprobe (`Path(__file__).resolve().parents[n]` gegen eine Datei testen, die
   es geben muss). PowerShell: Parser-Syntaxpruefung, dann der Handlauf.
7. **Aufgaben, die nur bei Anmeldung laufen** (`MaxHirn-Nautilus-Docker`,
   `-Optimierungen-Finden`), per `Start-ScheduledTask -TaskName <name>` einmal
   anstossen — die sind idempotent und erneuern `LastTaskResult` auf `0`.
   Dauerkopierer wie `MaxHirn-Sicherung` NICHT zur Unzeit doppelt starten; ein
   Handlauf am Tag ist der Nachweis.
8. **Fremdarbeit einziehen und den Index geradeziehen.**
   `fremdarbeit-einziehen.ps1 -Testlauf` zeigt, was ruht. Nach dem echten Lauf
   kann `git status` ein Paar `D <pfad>` + `?? <pfad>` zeigen: Datei existiert,
   Index sagt geloescht. Erst `git rev-parse HEAD:<pfad>` gegen
   `git hash-object <pfad>` vergleichen; sind die Hashes gleich, mit
   `git add <pfad>` den Index herstellen — das aendert keine Datei.
9. **Verwaiste Sperre:** bricht git mit `index.lock: File exists` ab, Alter
   pruefen und echte `git.exe`-Prozesse ohne `fsmonitor` zaehlen. Ist die Sperre
   0 Byte alt und kein echter Prozess da, UMBENENNEN (z.B.
   `.git/index.lock.verwaist-JJJJMMTT-HHMM`), nie loeschen. Traegt die Sperre den
   Zeitstempel des EIGENEN Commit-Versuchs (Erstversuch 17:11:43, Lock 17:11:43),
   ist sie das Abbruch-Artefakt des eigenen Aufrufs - umbenennen und denselben
   Commit wiederholen.
10. **Bericht neu erzeugen und den Rueckgang zeigen** (Anzahl Entscheidungen
    vorher/nachher) — das ist der Beleg, dass die Rauschfixes greifen.
11. **Committen und pushen:** nur eigene Pfade namentlich, nie `git add -A`;
    `--author="Hermes <hermes@local>"` fuer eigene, `fremd@local` fuer fremde
    Arbeit; `git push origin master`.

## Pitfalls

- **Ein Haenger ist kein "kein Befund".** Der Bericht wird am Ende geschrieben:
  haengt Block 14, fehlen ALLE Bloecke danach, und `letzter-lauf.md` bleibt
  tagealt, waehrend jeden Morgen ein Tageslog entsteht. Der Aufgabenzustand
  sagt dabei "Ready".
- **Protokolle werden je Tag ueberschrieben** (`systempruefung-<heute>.log`):
  ein zweiter Lauf am selben Tag macht den ersten unfindbar. Vor dem Neulauf
  die Befunde notieren.
- **`$LASTEXITCODE` nach einer Pipe pruefen, nicht erst nach dem Filtern mit
  `read_file`-Aequivalenten der Shell** — sonst misst man den Exit des letzten
  Rohrglieds und haelt einen toten Dienst fuer gesund.
- **Ein toter Docker-Daemon nimmt den Container mit.** Fehlt `nautilus-demo`
  samt Image, hilft nur der Neubau: `docker build -t nautilus-demo-node:1.231.0 Agenten/Handel/nautilus`
  dann `docker run -d --name nautilus-demo --restart unless-stopped -e OKX_API_KEY=dummy-node-key -e OKX_API_SECRET=dummy-node-secret -e OKX_API_PASSPHRASE=dummy-node-pass nautilus-demo-node:1.231.0`
  (idempotent auch in `Agenten/Routinen/nautilus-docker-start.ps1`).
- **Robocopy meldet Code 11, wenn Dateien waehrend des Laufs entstehen und
  vergehen** (Cache-, Cron-Ausgabe-, Log-, Sperrordner). Fix ist `/XD` fuer den
  fluessigen Ordner, NICHT `/R` erhoehen.
- **Nicht jeder Nicht-0-Code ist ein Fehler** — `267014` bei einem Dauerlauf ist
  der Normalfall beim Herunterfahren. Umgekehrt: ein Code `0` beweist ohne das
  eigene Protokoll nichts.
- **Angebotene Loeschungen aus der Pruefung sind Vorschlaege**, keine Auftraege.
  Modelle (`Modelle/`, Stufe 2) erst nach Rueckfrage bei Max loeschen; vorher
  pruefen, ob eine Kopie auf `G:`/`Q:` liegt (Modelle sind von der Sicherung
  ausgenommen, meist gibt es keine).
- **Der Bericht traegt ein UTF-8-BOM** (PowerShell `Set-Content -Encoding UTF8`):
  ein Anker `^#` findet die Kopfzeile nicht, solange das BOM nicht abgeschnitten
  ist (`text.lstrip("\ufeff")`). Gilt fuer jeden Parser auf diese Logs.
- **Testsuiten schreiben in echte Spuren** (Bedingung 4) — nach einem Testlauf
  kurz `spiegelstand.py` gegenproben, bevor man "Basis unberuehrt" behauptet.

## Verification

- `read_file` auf `systempruefung-letzter-lauf.md`: Kopfzeile von heute, Ende
  des Tagesprotokolls mit Ende-Zeile, Entscheiden-Liste kleiner als vorher.
- `git status --porcelain` nennt nur frische Fremdarbeit (< 30 min) und keine
  eigenen Dateien mehr; `git log --oneline origin/master..master` ist leer.
- Fuer jede behobene Aufgabe steht `LastTaskResult 0` mit frischem `LastRunTime`
  oder der Handlauf mit "ENDE ok".

## Wache

`scripts/berichts-alter.py` meldet mit Exit 1, wenn der Bericht aelter als die
Schwelle ist (Standard 26 h, `--stunden N`). Gedacht fuer einen Cronjob
(`cronjob_manage`, no_agent, taeglich nach dem Prueflauf): leere Ausgabe = still.
Invoke through the `terminal` tool.

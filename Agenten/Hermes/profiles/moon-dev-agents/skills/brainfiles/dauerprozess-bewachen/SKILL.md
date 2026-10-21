---
name: dauerprozess-bewachen
description: "Lang laufende Prozesse starten und per Cron bewachen."
version: 0.1.0
author: Hermes
platforms: [windows]
category: brainfiles
metadata:
  hermes:
    tags: [Windows, Dauerprozess, Waechter, Cron]
---

# Einen Dauerprozess starten und bewachen

Gilt fuer alles, was laufen soll und nicht endet: Bus, Handels-Dauerlauf,
Handelszentrale, Router, Atlas-Watcher. Der Ablauf ist immer derselbe: Start ueber
eine `.cmd`, Zustand ueber eine PID-Datei, Wache als Hermes-Cron `no_agent`.

## Wann

- „X soll laufen / dauerhaft laufen / starten / im Hintergrund“
- „starte Y neu, wenn es abstuerzt“, „warum ist X wieder aus“
- Eine Komponente soll nicht mehr an eine Agentensitzung gebunden sein

## Ablauf

1. **Starter als idempotentes Skript** (`<komponente>-start.ps1`) neben die
   Komponente legen: erst PID-Datei lesen und pruefen, ob der Prozess lebt ->
   „laeuft schon“ + Exit 0. Nur sonst starten.
2. **Start ueber eine `.cmd` je Ziel, nicht die EXE direkt.** In der `.cmd` macht
   die Shell die Umleitung, dann `start "" /b "<exe>" <argumente> >> "<log>" 2>&1`.
   Aufruf des Starters:
   `Start-Process -FilePath 'cmd.exe' -ArgumentList @('/c', "<pfad>.cmd") -WindowStyle Hidden`.
3. **PID nach dem Start ermitteln** (`Get-Process <name>` vorher/nachher vergleichen,
   den juengsten nehmen) und in `<komponente>.pid` schreiben — das ist der einzige
   Zustand, dem die Wache glaubt.
4. **Wache als Hermes-Cron**, nicht als Windows-Aufgabe:
   `cronjob_manage action=create name=<komponente>-waechter schedule='15m'
   script=<wache>.py no_agent=true deliver='telegram'`.
   Die Wache gibt **nichts** aus, wenn alles laeuft (leere Ausgabe sendet nichts),
   und beschreibt nur den Befund, wenn sie eingreift. Nicht-0-Exit oder Timeout
   loest die Fehlermeldung aus.
5. **Gegenproben in beide Richtungen, vor dem Bericht:**
   (a) Prozess laeuft -> Wache gibt 0 Zeichen aus, Exit 0;
   (b) `Stop-Process -Id <pid> -Force` -> Wache meldet „PID ... laeuft nicht“,
   startet neu, schreibt die neue PID, Exit 0.
6. **Wirksamkeit der Komponente selbst belegen** (nicht nur den Prozess): eine
   Eingabe erzeugen und nachsehen, dass die Ausgabe nachzieht.

## Zweite Instanz derselben Komponente

Soll derselbe Code ein zweites Mal laufen (gleiche Spuren, anderer Parameter),
ist er ein EIGENER Dauerprozess - kein zweiter Aufruf derselben Datei:

1. **Eigene PID-Datei und eigenes Log** (`<komponente>.<variante>.pid`,
   `.<variante>.log`). Eine gemeinsame Sperre meldet der zweiten Instanz
   „laeuft schon“, ein geteiltes Log macht beide ununterscheidbar (wer ist
   abgestuerzt?).
2. **Starter parameterisieren, Basis-Namen unveraendert lassen.**
   `<start>.ps1 -Risiko mittel` bildet Sperre, Log und Melde-Namen aus der
   Variante; die Basis behaelt ihre alten Namen - sonst suchen alle vorhandenen
   Aufgaben, Auswertungen und Fenster ploetzlich woanders.
3. **Eigene Wache fuer die zweite Instanz.** Die bestehende Wache startet nur die
   Basis; ohne zweite Aufgabe ist die Variante nach jedem Neustart einfach weg.
   Gegenprobe: `Start-ScheduledTask` auf die neue Aufgabe muss die Logzeile
   „laeuft bereits (PID …, Variante …)“ erzeugen, Exit 0 - sie startet nicht doppelt.
4. **Der Eingabekanal gehoert GENAU EINER Instanz.** Telegram-`getUpdates`,
   gemeinsame Warteschlangen und Freigabedateien: die zweite laeuft stumm, liest
   keine Befehle, oeffnet/schliesst keine Fenster der ersten. Zwei Abrufer an
   einem Bot verschlucken sich gegenseitig (Telegram 409).
5. **Getrennte Zustands-/Ergebnisdateien je Instanz**, sonst ueberschreiben sie
   sich die Positionen. Sind die Namen abgeleitet (`datei()`), ist das EINE Zeile
   in der gemeinsamen Bibliothek statt eines Sonderwegs je Aufrufer.

## Pitfalls

- **`Start-Process -RedirectStandardOutput` blockiert bei einem Dauerprozess** —
  der Aufrufer wartet auf das Ende des Kindes, also nie. Symptom: der Startbefehl
  laeuft in den Timeout, obwohl der Prozess danach laeuft. Die Umleitung gehoert in
  die `.cmd`, der Starter kehrt sofort zurueck.
- **Ein aus der Agentensitzung gestarteter Hintergrundprozess stirbt mit ihr.**
  Symptom: Stunden spaeter endet er mit Exit 127, waehrend der per `.cmd`
  gestartete weiterlaeuft — das ist kein Fehler der Komponente und kein Grund zur
  Annahme, der Dauerbetrieb sei weg. Deshalb fuehrt der Weg ueber die `.cmd`
  (Schritt 2), und Testprozesse werden danach beendet, damit kein Doppelbetrieb
  bleibt.
- **Die Uhr messen, bevor ein Ausbleiben gemeldet wird** (`date`): aus den letzten
  Zeitstempeln im Kopf eine Uhrzeit weiterzaehlen erzeugt Fehlalarme („Zyklus seit
  2 h ausgeblieben"). Gegenprobe in derselben Reihenfolge: PID lebt -> Log-Zeile des
  Starters -> `Get-ScheduledTaskInfo` (`last_run`/`next_run`) -> erst dann urteilen.
- **Ein Statuskommando der Komponente beschreibt nicht immer den Prozess.**
  Beispiel `projectatlas watch-status`: meldet `active: false` auch bei laufendem
  Watcher, weil es einen Durchgang meint. Wer damit prueft, startet einen zweiten
  Prozess. Maßgeblich ist die PID-Datei plus `Get-Process`.
- **Unter Windows ist ein venv-Prozess ein PAAR** (Launcher-Shim + Kind). Ein
  `Stop-Process` auf die verfolgte PID laesst das Kind weiterlaufen - und das
  schreibt unsichtbar in dieselben Dateien. Vor „beendet“ per
  Kommandozeilen-Abfrage pruefen, dass KEIN Glied der Kette mehr laeuft, und
  beide PIDs beenden. Umgekehrt gilt: das Paar ist kein Doppellauf (nicht Alarm
  schlagen, bevor ParentProcessId/ExecutablePath geprueft sind).
- **Eine Messreihe mit zwei Schreibern ist unbrauchbar.** Hat ein versehentlich
  parallel laufender Test- oder Zweitprozess in dieselben Zustands- und
  Journaldateien geschrieben, sind die Zahlen dieser Minuten Mischwerte:
  Dateien loeschen und die Reihe sauber neu starten, statt die Vermischung
  spaeter herausrechnen zu wollen.
- **`Get-CimInstance Win32_Process` mit `CommandLine`-Filter ist teuer** in einem
  gewachsenen Prozessbaum. Zuerst PID-Datei und `Get-Process` nutzen; NUR wenn
  zwei gleichnamige Prozesse unterschieden werden muessen (Basis vs. Variante -
  `Get-Process` zeigt keine Argumente), ist die WMI-Abfrage das Mittel - dann
  einmal gezielt, nicht in einer Schleife.
- **`Register-ScheduledTask` braucht Administrator** („Zugriff verweigert“) — der
  Hermes-Cron laeuft ohne Erhoehung und heilt zusaetzlich einen toten Prozess, was
  ein Autostart-Eintrag nicht kann. Nur wenn Max eine sichtbare Aufgabe will,
  braucht es einen erhoehten Aufruf von ihm.
- **Ein Prozess je Ziel.** `watch` und Verwandte nehmen EIN Ziel; „alle 33 Repos“
  sind 33 Prozesse. Bewusst nur das Standardziel anbinden und das im Bericht sagen.
- **Ein Waechter darf nicht ueber den Weg melden, den er ueberwacht.** Eine Wache,
  die ihren Befund in den Bus oder in die ueberwachte Warteschlange schreibt,
  schweigt genau beim Ausfall. Deshalb Cron/Scheduler direkt nach Telegram.
- **`subprocess` mit `text=True`** stirbt an Umlauten aus `tasklist`/`powershell`:
  die Konsole schreibt cp1252, nicht UTF-8. `encoding="cp1252", errors="replace"`
  setzen, sonst reisst ein `UnicodeDecodeError` im Lesethread den Aufruf ab.
- **Kein Doppelbetrieb.** Nach einem Test mit `Stop-Process` pruefen, dass genau EIN
  Prozess der Komponente laeuft (`Get-Process <name>`); verwaiste PID-Dateien nach
  dem Aufraeumen loeschen.
- **Nach jedem Deploy des Starters die Routine-Zeile nachziehen**
  (`Wissen/Routinen.md`) — sonst weiss die naechste Sitzung nichts von der Wache.

## Verification

Eingerichtet ist ein Dauerprozess, wenn alle drei stehen: (a) der Prozess laeuft und
PID-Datei und `Get-Process` stimmen ueberein, (b) die Wache gibt bei laufendem
Prozess **nichts** aus und startet nach einem `Stop-Process` nachweislich neu,
(c) die Komponente tut ihre Arbeit — mit einer erzeugten Eingabe und der
beobachteten Ausgabe belegt.

## Abgrenzung

- Was die Komponente fachlich tut: ihr eigener Skill (z. B. `projectatlas`)
- Dienstzustaende und Ereignisse pruefen: `systemdiagnose`
- Eine geplante Aufgabe an den Bus melden: `bus-integration`

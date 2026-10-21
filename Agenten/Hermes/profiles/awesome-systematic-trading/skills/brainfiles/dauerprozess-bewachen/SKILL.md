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
   startet neu, schreibt die neue PID, Exit 0;
   (c) **Alarmrichtung ohne Eingriff:** die Wache nimmt einen abweichenden Port
   bzw. ein `--nicht-starten` an, damit sich Meldung und Befund zeigen lassen,
   ohne den echten Dienst zu stoppen — sonst kostet jede Probe einen echten
   Ausfall, und die Probe wird deshalb nicht gemacht.
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

## Doppelbetrieb erkennen und beenden

- **Eine PID-Datei als Sperre hat ein Zeitfenster.** `Test-Path` → PID lesen →
  Prozess pruefen → starten ist Pruefen-dann-Handeln: feuern zwei Ausloeser
  gleichzeitig (Anmelde-Trigger und Zeit-Trigger derselben Komponente), sehen
  beide „frei" und starten doppelt. Auch eine neu vergebene PID laesst eine tote
  Sperre lebendig aussehen, und `IgnoreNew` in der Aufgabe hilft nicht,
  wenn der Starter den Prozess abgekoppelt startet und selbst schon fertig ist.
  Wer genau eine Instanz will, laesst den **Prozess selbst** eine exklusive
  OS-Dateisperre (`msvcrt.locking`/`fcntl.flock`) ueber seine Laufzeit halten und
  sich mit klarer Meldung beenden, wenn er sie nicht bekommt — eine stale PID
  ist keine Sperre.
- **Variante heisst nicht automatisch getrennte Zustandsdateien.** Der Starter
  kann die Sperre je Variante bilden („Basis und Stufenlauf duerfen gleichzeitig
  laufen"), waehrend beide Varianten in **dieselben** Zustands- und
  Journaldateien schreiben. Vor dem Einrichten einer zweiten Variante die
  Zustandspfade im Code lesen, nicht dem Kommentar im Starter glauben: ohne
  getrennte Pfade ist die zweite Variante kein eigener Dauerprozess, sondern
  Doppelbetrieb auf gemeinsamem Zustand (doppelte Ueberwachung, doppelte
  Einstiege, konkurrierende Schreibvorgaenge).
- **Ueberzaehlige Instanzen beenden: erst sichern, dann pruefen, dann PID-genau
  beenden.** Reihenfolge: (1) die Zustandsdateien in einen eigenen Ordner
  kopieren — ein Abbruch mitten im Schreiben hinterlaesst eine halb geschriebene
  JSON, die der Ueberlebende als „keine Positionen" liest und dann nicht mehr
  ueberwacht; (2) aus dem Journal den `modus` der letzten Zeilen lesen, um zu
  wissen, ob echte (Live-)Positionen offen sind und wer sie weiter ueberwachen
  muss; (3) beenden per PID fuer **Launcher UND Kind**, nie per Prozessname;
  (4) danach nachlesen, dass jede Zustandsdatei wieder parst und die
  Positionszahl unveraendert ist, und dass genau EIN Prozess der Komponente
  laeuft.
- **Ein langsamer Rechner ist ein Symptom, keine Ursache.** Vor jedem
  Neustart oder Update die Doppelbetriebe zaehlen: Python-Prozesse nach
  Kommandozeile gruppieren und je Gruppe die Eltern-Kind-Paare trennen. Vier
  Instanzen desselben Dauerlaufs heissen vierfache Scan-/Netzlast je Takt —
  und bei gemeinsamen Zustandsdateien zusaetzlich vierfache
  Positionsueberwachung.

## Pitfalls

- **`Start-Process -RedirectStandardOutput` blockiert bei einem Dauerprozess** —
  der Aufrufer wartet auf das Ende des Kindes, also nie. Symptom: der Startbefehl
  laeuft in den Timeout, obwohl der Prozess danach laeuft. Die Umleitung gehoert in
  die `.cmd`, der Starter kehrt sofort zurueck.
- **Den Dauerprozess nie ueber eine Pipe des Aufrufers starten**
  (`& powershell -File <starter> *>&1 | Add-Content $protokoll`). Das Kind haelt die
  Pipe offen, der Starter kehrt also nie zurueck — mit drei Folgen, die zusammen wie
  ein Fehler der Komponente aussehen: (1) die geplante Aufgabe bleibt auf „Running“,
  (2) das eigene Protokoll ist von aussen gesperrt (`Get-Content` meldet „Device or
  resource busy“, die `ENDE`-Zeile als Beleg fehlt), und (3) wer die Aufgabe beendet
  (`^C` im Protokoll des Kindes, Aufgabencode 267014 = „von aussen beendet“), reisst
  den laufenden Dienst mit — der Ausfall beginnt Minuten nach dem Start, und der
  Aufgabencode liest sich dabei harmlos. Richtig: das Startskript losgeloest in
  eigener Konsole starten
  (`Start-Process -FilePath 'powershell.exe' -ArgumentList @('-ExecutionPolicy','Bypass','-NoProfile','-File', ('"' + $starter + '"')) -WindowStyle Hidden`)
  — eigener Prozessbaum, ueberlebt die Sitzung — und danach **selbst** auf den Port
  warten (`while (-not (Test-PortOffen $port)) { … Start-Sleep -Seconds 3 }`, Frist
  grosszuegig, der erste Lauf baut notfalls erst). Die Rueckkehr des Starters ist der
  Befund, nicht die Ausgabe des Kindes.
- **Vor jedem Ausfallurteil fragen, ob die Komponente ueberhaupt eine Wache hat.**
  Eine fehlende Wache ist der eigentliche Befund — ohne sie ist die Ausfallzeit die
  Zeit bis zum Zufall (gefunden wird der Ausfall dann von einer Sitzung, die den Port
  zufaellig antippt). Deshalb zuerst die Wachenliste ansehen (Hermes-Cron-Liste und
  `Get-ScheduledTask -TaskName 'MaxHirn-*'`, Zustand `Ready` heisst nur „registriert“),
  dann nach dem Muster aus Schritt 4 nachruesten.
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
- **Geplante Routine-Aufgaben versteckt registrieren** (`-WindowStyle Hidden` in
  der Task-Action): eine sichtbare Aufgabe zeigt bei JEDEM Lauf ein
  PowerShell-Fenster. Drei Dauerlauf-Aufgaben feuern je 30 Minuten (Dauerlauf
  selbst + Waechter + Mittel-Waechter) — das ist das „andauernd flackernde
  Fenster". Beim Anlegen Hidden von Anfang an mit aufnehmen; Bestandsaufgaben per
  `Set-ScheduledTask -Action` nachziehen (interaktive Aufgaben ohne Erhoehung,
  `LogonType=ServiceAccount`-Aufgaben erhoeht). Wrapper-Kinder muessen auch
  versteckt starten (`Start-Process -WindowStyle Hidden` oder pythonw), sonst
  bleibt deren Konsole sichtbar, wenn nur der Wrapper versteckt ist.
- **Ein Dienst-Task mit `python.exe` bei Interactive-Logon zeigt ein DAUER-
  Konsolenfenster** — auch wenn der Wrapper versteckt ist: `-WindowStyle Hidden`
  versteckt die PowerShell, nicht das Konsolen-Subsystem eines python.exe.
  Diagnose bei „aufploppender Konsole“: alle Task-Aktionen listen
  (`Get-ScheduledTask … | % Actions[0]`) und nach `python.exe` (sichtbar) vs.
  `pythonw.exe` (versteckt) filtern — Dienste, die ihr Journal auf die Platte
  schreiben (Prints nur Status), auf pythonw umstellen. **Die Live-Aktion einer
  `-RunLevel Highest`-Aufgabe zu aendern verweigert die normale Sitzung
  (0x80070005, `Set-ScheduledTask` wie `Register-ScheduledTask`)** — solche
  Fixes als weiteren Schritt in das vorhandene Admin-Skript legen
  (`vorsorge-*-admin.ps1`), damit EINE Admin-Sitzung alles erledigt.
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
- **`Start-ScheduledTask` auf eine Aufgabe mit `MultipleInstances=IgnoreNew`
  ist ein No-Op, wenn der Scheduler die Aufgabe noch als „Running“ sieht** —
  der ALTE Prozess (mit dem ALTEN Code) laeuft einfach weiter, ohne
  Fehlermeldung und ohne dass ein neuer Prozess entsteht. Nach jeder
  Codeaenderung an einem so registrierten Dauerprozess zuerst
  `Get-ScheduledTaskInfo` pruefen, dann den KOMPLETTEN Prozessbaum beenden
  (`taskkill /F /T /PID <Wurzel-PID>` — ein einfaches `Stop-Process` auf die
  Wurzel-PID laesst Kinder weiterlaufen), erst DANACH neu starten und am
  Zeitstempel im Log verifizieren, dass die beobachtete Instanz wirklich seit
  dem Neustart laeuft — sonst wird der alte, ungepatchte Lauf fuer einen
  Beleg des Fixes gehalten.
- **Eine `CommandLine -like '*Suchtext*'`-Abfrage trifft oft die eigene
  Suchanfrage**, wenn das Terminal den Befehl selbst in einer Bash-/
  PowerShell-Huelle mit dem vollen Text weiterreicht — der gesuchte String
  taucht dann in der Kommandozeile des Abfrageprozesses auf und erzeugt
  Phantomtreffer, die wie ein echter laufender Prozess aussehen. Vor
  „laeuft noch“ das `CommandLine`-Feld ansehen (nicht nur die PID zaehlen);
  ein Treffer, dessen Kommandozeile die eigene Abfrage enthaelt, ist kein
  echter Prozess.

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

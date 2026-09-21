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

## Wache auf eine DATEI statt auf einen Prozess

Manchmal ist nicht ein Prozess zu bewachen, sondern ein Ergebnis: „melde die
erste echte Order dieser Spur“, „melde, wenn das Buch sich aendert“. Der Aufbau
ist derselbe Cron `no_agent`, nur das Kriterium ist eine Datei.

1. **Ein Zustand in `cache/`, ein Befund je NEUEM Ereignis.** Die Wache merkt
   sich in einer eigenen JSON den letzten Stand (z. B. die Zahl der
   Ereigniszeilen) und meldet nur die Differenz. Ohne diesen Merker meldet sie
   entweder bei jedem Lauf dasselbe (Spam) oder nie (weil sie den alten Stand
   als neu liest).
2. **Erstlauf still stellen.** Beim ersten Lauf nur den Stand schreiben und
   nichts senden — sonst kommt beim Einrichten sofort eine Meldung ueber
   Ereignisse, die der Nutzer laengst kennt.
3. **Auch Zustandswechsel melden**, nicht nur neue Zeilen (z. B. „Fenster zu,
   laeuft wieder Papier“). Ein stiller Rueckfall sieht sonst aus wie „die Spur
   tut nichts“.
4. **Die Wache sieht nur, was geschrieben wird.** Ein Fehlerpfad, der seine
   Meldung nach stderr schreibt und die Zeile im Datenfile auslaesst, ist fuer
   die Wache unsichtbar — und der Supervisor meldet die Spur trotzdem als „ok“,
   weil er stderr verwirft. Gehoert genau dieser Fehler ueberwacht (darf der
   Schluessel wirklich ordern?), muss der Fehler ZUERST eine Zeile im
   ueberwachten File bekommen — mit eigenem Kennzeichen, damit die Wache ihn
   anders formatiert als den Normalfall. Diese Zeile ist kein Buchungssatz:
   sie darf die Auswertung nicht verfaelschen (Kennzeichen ausserhalb der
   Buchungs-Menge waehlen und das in der Auswertung pruefen).
5. **Gegenprobe ohne echte Ereignisse:** die Wache in einem Einmal-Aufruf gegen
   ein Temp-File mit erfundener Zeile laufen lassen — sie muss genau einmal
   melden und beim zweiten Lauf schweigen. Danach `cronjob_manage action=run`
   fuer den echten Weg; ein Lauf mit leerer Ausgabe ist der Beweis, dass der
   still bleibende Fall still bleibt.
6. **Mehrere Objekte derselben Art: EIN Modul, je Objekt ein duenner Wrapper.**
   Fuenf Buecher heissen nicht fuenf Wachenskripte: die Rechnung (letzter Stand,
   Differenz, Fensterwechsel) liegt EINMAL in `scripts/<familie>_wache.py` mit
   einer Tabelle `{objekt: {datei, schluessel, waehrung}}`, und je Cron-Job gibt
   es eine Wrapper-Datei, die `main("<objekt>")` aufruft. Sonst muss jede
   Verbesserung in N Kopien nachgezogen werden, und eine Kopie wird vergessen.
7. **Nur Handelszeilen melden, nicht jede Zeile mit dem Ziel-Modus.** Ein
   Journal schreibt im Live-Modus auch Verwaltungszeilen (Funding alle 8 h,
   Rollover, Zyklus, Quote) — eine Wache, die stumpf auf `modus == live`
   filtert, meldet alle 8 h ein „Ereignis“, das keine Order ist. Die
   Ausschlussliste aus der Fachlogik uebernehmen (hier: dieselben Wortlaute
   `funding/rollover/zyklus/quotes/info` wie in der Runden-Zaehlung), statt sie
   in der Wache neu zu erfinden.

## Wache auf PROZESSE (wenn ein Prozesskriterium geprueft wird)

Eine Wache, die Prozesse zaehlt, ist die fehleranfaelligste Bauform: sie schlaegt
Alarm, wenn ihre Zaehlregel falsch ist, nicht wenn etwas kaputt ist. Eine Wache,
die bei JEDEM Lauf dasselbe meldet, ist deshalb zuerst ein Fehler der Wache -
pruefe die Regel, nicht den Zustand. Drei Regeln, ohne die es nicht geht:

1. **Je Einheit zaehlen, nicht ueber alles.** Ein Dienst unter Windows ist ein
   PAAR (Startprogramm + Interpreter). Erwartet sind **genau zwei Prozesse je
   Kind** (4 Kinder = 8). Eine Gesamtzahl oder das ALTER als Kriterium ist
   falsch: ein Agent laeuft legitim stundenlang, sein Paar altert mit (gemessen:
   eine Wache meldete „8 Prozesse aelter als 1 h = Leak" alle 15 Minuten, obwohl
   genau der Normalzustand vorlag).
2. **Erst ab der Aufraeum-Schonfrist zaehlen.** Raeumt der Treiber selbst auf
   (jeder Zyklus, Schonfrist z. B. 300 s), stehen nach jedem Neustart junge
   Waisen im Zaehlfenster, die in Minuten von allein verschwinden. Wer sie
   mitzaehlt, alarmiert bei jedem Neustart. Also nur Prozesse aelter als die
   Schonfrist als Befund werten — und die Gesamtzahl ebenfalls so filtern.
3. **Zwei Bedingungen fuer einen Treffer: Kennung UND Prozessname.** Eine
   `CommandLine`-Suche nach dem Modulnamen trifft auch die eigene Abfrage und
   jede Huelle, die den Text enthaelt — in beide Richtungen schaedlich: die
   Wache zaehlt Phantome (kraken=5 statt 2), und ein Aufraeumer, der das fuer ein
   Kind haelt, BEENDET seine eigene Suche per `taskkill /T`. Immer zusaetzlich auf
   `python.exe`/`pythonw.exe` (bzw. den echten Programmnamen) filtern.

**`powershell` immer mit absolutem Pfad aufrufen**
(`%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe`): unter der
Aufgabenplanung ist der PATH ein anderer als in einer Sitzung. Symptom einer
leeren Prozessliste ist NICHT ein Fehler, sondern **stilles Nichtstun** — der
Treiber raeumt dann nichts auf und meldet trotzdem „ok". Wo „leer = nicht raten"
gilt, muss die leere Liste LAUT protokolliert werden, und die Abfrage je Zyklus
EINMAL laufen (Ergebnis an die Aufraeumfunktion durchreichen, nicht zweimal fragen).

Gegenprobe in beide Richtungen: auf gesundem System gibt die Wache **nichts** aus,
und im Treiber-Log steht die Aufraeumzeile mit der Zahl der beendeten Waisen.

## Wache auf die DAUER eines Ausfalls (Neustart-Schleifen sichtbar machen)

Ein Zustands-Waechter („laeuft / laeuft nicht“) sieht eine Neustart-Schleife
nicht: er startet brav neu, jeder Lauf meldet Erfolg, und dass der Dienst den
halben Tag weg war, faellt nur als Nebenwirkung auf (gescheiterte Auftraege,
unklare Meldungen an den Nutzer). Dafuer eine ZWEITE, unabhaengige Wache - nicht
in den Neustart-Waechter hineinbauen: stirbt der Neustart-Waechter, muss die
Messung weiterlaufen.

1. **Zustand = Ausfallbeginn, nicht „aus“.** Eigene JSON in `cache/`:
   `{"seit": <ISO>, "gemeldet": <bool>}`. Erster Lauf mit zu Port: nur den
   Beginn schreiben, lautlos.
2. **Meldeschwelle in Sekunden** (Startwert 300): ein Neustart von zwei Minuten
   ist Betrieb, kein Befund. Darunter nichts ausgeben.
3. **Zweiter Lauf im selben Ausfall schweigt** (`gemeldet` setzen) - sonst feuert
   die Wache bei jedem Takt denselben Alarm.
4. **Die Erholung melden, sobald die Schwelle ueberschritten war**, mit der
   gemessenen Dauer, und den Zustand danach loeschen. Ein Ausfall ohne
   Erholungsmeldung laesst offen, ob es weitergeht.
5. **Den Zustand des Neustart-Waechters in den Befund schreiben** (Windows:
   `Get-ScheduledTask`/`Get-ScheduledTaskInfo`). Sonst ist „Dienst weg“ nicht von
   „Waechter tot“ zu unterscheiden - und genau dafuer ist die zweite Wache da.
6. **Fuenf Richtungen belegen, bevor „fertig“ gemeldet wird:** gesund = lautlos;
   Ausfall ueber der Schwelle = Alarm mit Dauer; zweiter Lauf = lautlos; Ausfall
   unter der Schwelle = lautlos; wieder offen = Erholungsmeldung plus geloeschter
   Zustand. Dafuer nimmt das Skript Pruefhaken (`--port`, `--stand`,
   `--schwelle`) und laeuft gegen einen geschlossenen Port / eine
   Temp-Zustandsdatei - nie gegen den echten Dienst.
- **Ein Pruefhaken ist ein eigener Code-Pfad und gehoert in die Probe.** Liegt der
  Zustandspfad als `Path` im Modul und kommt ueber den Haken als `str`, bricht
  `pfad.parent` NUR im Pruefweg ab, waehrend der Produktivpfad gesund aussieht.
  Im Schreib-/Lesepfad zuerst `pfad = Path(pfad)` normalisieren, und die Probe
  ueber genau diesen Weg fahren.

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
- **Ein Watchdog mit hoher `RestartCount` kann einen Crash-Loop stundenlang
  verstecken.** `RestartCount 99 / RestartInterval 1 min` startet einen sofort
  wieder abstuerzenden Prozess brav neu — der Scheduler zeigt `Running`/`Ready`
  ohne Fehlermeldung, waehrend in Wahrheit seit Stunden kein einziger Zyklus
  durchlief. Prozess-**Uptime** (`Get-Process <name> | Select StartTime`) gegen
  den Zeitpunkt des letzten VOLLSTAENDIGEN Zyklus im eigenen Log halten — klafft
  das auseinander (Prozess wenige Minuten alt, letzter echter Erfolg Stunden
  zurueck), ist es ein Crash-Loop und kein gesunder Dauerbetrieb, auch wenn
  gerade ein Prozess laeuft.
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
  schreiben (Prints nur Status), auf pythonw umstellen. Das gilt fuer den
  Wrapper **und** fuer die vom Treiber gespawnten Kinder: ein Supervisor, der
  seine Agenten mit `python.exe` (Repo-venv) startet, poppt bei jedem
  Kindprozess ein Fenster auf; `pythonw.exe` im Startbefehl des Supervisors
  (nicht nur im Task) schaltet ALLE Kindfenster ab, die Ausgabe laeuft weiter
  in die ag_log-Dateien.
- **Einen Konsolen-Rundgang fahren: alle Task-Aktionen nach Sichtbarkeit
  klassifizieren, nicht raten.** Der schnelle Diagnose-Scan fuer
  "aufploppende Fenster" listet die Top-Aufgaben (`MaxHirn-*`, `BrainFiles-*`,
  `Hermes-*`) und stuft jede Action in drei Klassen ein: `-WindowStyle Hidden`
  im Arguments => versteckt; `pythonw.exe` / `wscript //B` => fensterlos (ok);
  alles andere => `CHECK` (potenziell sichtbar). `CHECK` heisst noch nicht
  Fenster: `pythonw` ist immer fensterlos, aber jedes `python.exe` und ein
  `powershell.exe` OHNE `-WindowStyle Hidden` zeigt eine Konsole. Echte
  Verursacher sind oefters die leisen Nebenlaeufer (ein Waechter, der alle
  2 Minuten feuert, ohne Hidden ist das staendige Flackern) als die grossen
  Dauerlauefe. Fuer den Endcheck die laufenden Prozesse nach
  `ExecutablePath`/Kommandzeile ansehen — nicht nur die Action lesen.
- **Den Fix in BEIDE Schichten schreiben: die Live-Task-Action UND das
  Registrierungs-Wrapper-Skript.** `Set-ScheduledTask` aendert die laufende
  Aufgabe, aber der Anleger (`*-aufgabe.ps1` im Routinen-Ordner) traegt die
  ALTE Executable/Argumente weiter (`python.exe`, ohne Hidden). Wer nur den
  Task fixen, gibt den Fix beim naechsten Re-Registrieren zurueck. Beides
  patchen (pythonw + Hidden), versionskontrolliert committen.
- **Eine Aktion zu aendern verweigert die normale Sitzung, sobald die Aufgabe
  aus erhoehtem Kontext registriert wurde — unabhaengig vom `-RunLevel` des
  Prinzipals** (0x80070005, `Set-ScheduledTask` wie `Register-ScheduledTask`).
  Auch eine `Limited`-Principal-Aufgabe weist einen nicht erhoehten
  Action-Umbau ab; `Principal.RunLevel` vorhersagen zu wollen in die Irre.
  Solche Fixes als weiteren Schritt in das vorhandene Admin-Skript legen
  (`vorsorge-*-admin.ps1`), damit EINE Admin-Sitzung alles erledigt. Das
  Admin-Skript schreibt sein Ergebnis in eine Log-Datei (das Fenster ist
  versteckt); der Aufrufer liest die Datei statt der stdout der erhoehten
  Sitzung.
- **Ein laufender Treiber, der je Zyklus eine neue Kindgeneration spawnt und die
alte nicht beendet, ist ein Speicherleck — und die Symptome tauchen ANDERSWO auf.**
Der Treiber gilt als gesund (Prozess lebt, Log frisch), waehrend sich die Kinder
stapeln: gemessen 84 gleichartige Agentenprozesse, 80 davon aelter als eine Stunde,
aus einem einzigen Tag. Sichtbar wird das nicht am RAM, sondern am **Commit-Limit**:
bei 28 GB freiem RAM war das Commit zu 99 % reserviert (`Win32_OperatingSystem`:
`FreeVirtualMemory` gegen `TotalVirtualMemorySize`), und danach scheiterten fremde
Dinge — jede Puffer-Anforderung eines Modellladers, `git commit`, ganze Werkzeugaufrufe
(`WinError 1455`). Diagnose: Prozesse nach Kommandozeilen-MUSTER des Kindes gruppieren
(nicht nach Name), `CreationDate` ansehen und die Generationen zaehlen; erwartet ist
EINE je laufendem Zyklus. Aufraeumen durch Beenden der alten Generationen per PID,
dann Commit frei nachmessen — und den Fix im Treiber nachziehen (Kinder vor dem
naechsten Spawn beenden), sonst ist der Speicher in Stunden wieder weg.
  Der Gegenentwurf, der sich bewaehrt hat (moondev_dauerlauf, 21.09.2026):
  (a) Stoppen beendet den ganzen BAUM (`taskkill /T /F /PID`) — das Kind ist
  unter Windows ein PAAR, das Startprogramm allein zu beenden laesst den
  Interpreter als Waise stehen; (b) jeder Zyklus raeumt VOR dem Spawn auf:
  Prozesse mit der Kennung des Kindes, die zu keinem lebenden Kind gehoeren
  und aelter als eine Schonfrist sind (300 s), werden beendet — die Schonfrist
  schuetzt einen gerade startenden Enkel; (c) stirbt die verfolgte Wurzel,
  wird ihr Baum VOR dem Neustart beendet, sonst laufen mit jedem Zyklus zwei
  Kinder desselben Namens. Erwarteter Ruhezustand: GENAU zwei Prozesse je Kind
  (Startprogramm + Interpreter) — 4 Kinder = 8 Prozesse, gemessen nach dem
  Fix; vorher 84. Prozessliste ueber `Get-CimInstance Win32_Process` (wmic ist
  auf Windows 11 abgekuendigt), und bei fehlgeschlagener Abfrage NICHT
  aufraeumen statt zu raten. Wer die Aufraeumfunktion aus einer frischen
  Instanz ruft, erschlaegt die legitimen Kinder des laufenden Treibers — der
  Aufruf gehoert in den Zyklus des laufenden Treibers.
  Symptomkatalog (was bei erschoepftem Commit alles scheitert), die Messbefehle und
  die Route fuer einen Massenlauf, der im Sandbox-Terminal abbricht:
  `references/massenprozesse-und-commit-limit.md`.
- **Ein Test, der `protokolliere()` prueft, schreibt in die ECHTE Logdatei.**
  Der Modulpfad des Logs ist eine Konstante; ein Test des Aufraeumens landete
  damit als Zeile im Betriebsprotokoll des Treibers ("PIDs 600") und war dort
  nicht von einem echten Befund zu unterscheiden. In `setUp` die Logkonstante
  auf einen Temp-Ordner umbiegen (`m.LOG = Path(tmp)/"log.txt"`) — dieselbe
  Falle wie bei den Handels-Spuren (journal_zweitziel).
- **Ein toter Supervisor laesst seine Kinder als Waisen weiterlaufen.**
  Endet der Treiber von aussen (`Get-ScheduledTaskInfo`-Result 267014), bleiben
die von ihm gespawnten Agentenprozesse am Leben — sichtbare Konsolenfenster,
die "laufende Aufgaben" vortaeuschen, obwohl der Supervising-Prozess weg ist.
  Vor dem Bericht pruefen, ob der Treiber ueberhaupt noch laeuft
  (`State=Ready` statt `Running`, Result=267014): wenn nicht, die Kinder per
  PID beenden (`Get-CimInstance` nach dem Agenten-Modulnamen filtern, nie per
  Prozessname), Treiber per `Start-ScheduledTask` neu starten und das
  Prozesspaar samt Kindern nachverifizieren. Das Speichern der Orphans ist
  Aufraeumen, kein Bestandsfehler.
- **Ein Prozess je Ziel.** `watch` und Verwandte nehmen EIN Ziel; „alle 33 Repos“
  sind 33 Prozesse. Bewusst nur das Standardziel anbinden und das im Bericht sagen.
- **Ein Waechter darf nicht ueber den Weg melden, den er ueberwacht.** Eine Wache,
  die ihren Befund in den Bus oder in die ueberwachte Warteschlange schreibt,
  schweigt genau beim Ausfall. Deshalb Cron/Scheduler direkt nach Telegram.
- **Das Wachenskript liegt unter `Agenten/Hermes/scripts/` — ein Skript neben der
  Komponente wird nicht angenommen.** `cronjob_manage` erwartet einen Pfad RELATIV
  zu diesem Ordner; ein absoluter Pfad auf einen anderen Ort (z. B.
  `Agenten/Handel/…`) wird abgewiesen. Gehoert die Logik fachlich zur Komponente,
  also einen duennen Wrapper in `scripts/` legen, der die eigentliche Datei ueber
  `importlib.util.spec_from_file_location` laedt (NICHT ueber `sys.path` — ein
  Eintrag kann gleichnamige Module verdecken) und deren `main()` aufruft; beide
  Dateien versionieren. Der Wrapper haelt dieselbe Melde-Regel ein: leere Ausgabe,
  wenn es nichts zu melden gibt.
- **`subprocess` mit `text=True`** stirbt an Umlauten aus `tasklist`/`powershell`:
  die Konsole schreibt cp1252, nicht UTF-8. `encoding="cp1252", errors="replace"`
  setzen, sonst reisst ein `UnicodeDecodeError` im Lesethread den Aufruf ab.
- **Ein neuer Prozess gleich nach dem Neustart ist kein Befund.** Wer seinen
  eigenen Treiber neu startet, erzeugt regelmaessig Waisen der VORIGEN Instanz:
  `Stop-Process` auf die Treiber-PID beendet den Baum nicht, und die Kinder des
  alten Laufs leben weiter, bis der neue sie beim Aufraeumen erwischt. Vor jeder
  Aussage „zu viele Prozesse" die Startzeit der Treiberinstanz gegen die
  `CreationDate` der Prozesse halten — was vor dem Neustart entstand, ist
  Altlast, kein Doppellauf.
- **Nicht jeder Codefix braucht einen Neustart des Treibers.** Startet der Treiber
  je Zyklus ein KIND als eigenen Prozess (typisch `handeln.py`), liest das Kind die
  Datei bei jedem Start neu — ein Fix in der Komponente wirkt also im NAECHSTEN
  Zyklus, ohne den Treiber anzufassen (nachgemessen: das Aufraeumen einer Spur lief
  schon vor dem Treiber-Neustart). Ein Neustart ist noetig, wenn sich der
  TREIBER-Code selbst aendert (seine Konstanten, seine Modulliste) — der laufende
  Prozess hat das Modul beim Start importiert.
- **Vor dem Neustart eines Treibers mit echten Ordern pruefen, dass kein Kind
  gerade im Order-Zyklus steht.** Die Prozessliste nach dem Kommandozeilen-Merkmal
  des Live-Laufs filtern (z. B. `--live`) und warten, bis keines mehr laeuft —
  ein `taskkill /T` mitten im Zyklus reisst eine Order ab. Danach Baeume PID-genau
  beenden, Basis UND Variante neu starten und im Log den frischen Zyklus plus die
  unveraenderte Live-Position nachweisen.
- **Kein Doppelbetrieb.** Nach einem Test mit `Stop-Process` pruefen, dass genau EIN
  Prozess der Komponente laeuft (`Get-Process <name>`); verwaiste PID-Dateien nach
  dem Aufraeumen loeschen.
- **Nach jedem Deploy des Starters die Routine-Zeile nachziehen**
  (`Wissen/Routinen.md`) — sonst weiss die naechste Sitzung nichts von der Wache.
- **Ein Kind, das mit Exit-Code 0 endet, ist im Supervisor-Log unsichtbar.**
  Ein Supervisor, der nur bei `code != 0` die stderr des Kindes loggt, zeigt bei
  einem Kind, das nach wenigen Sekunden sauber endet, nur „gestartet … gestoppt“
  ohne Grund — und die Sterbeschleife sieht aus wie ein Kinderfehler, obwohl der
  Treiber selbst von aussen abgebrochen wird (Task-Result 3221225786). Diagnose:
  das Kind EINMAL direkt mit der Umgebung starten, die der Supervisor setzt
  (die env-Variablen, die er dem Kind mitgibt — nicht die eigene Shell-Umgebung),
  und die stderr ansehen; laeuft es dort, ist der Treiber das Problem, nicht das
  Kind. Danach den Task-Weg pruefen: `Get-ScheduledTaskInfo`-Result 3221225786
  = der Treiber wurde abgebrochen, nicht die Kinder.
- **`Start-ScheduledTask` auf eine Aufgabe mit `MultipleInstances=IgnoreNew`**
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
- **Kommandozeilen-Filter praezise auf den SKRIPTnamen stellen, nicht auf einen
  gemeinsamen Wortstamm.** `*dauerlauf*` matcht auch `moondev_dauerlauf.py`
  und andere verwandte Treiber desselben Stamms — eine „laueft noch“-/Instanzen-
  Zaehlung wird damit um eine fremde Prozessgruppe falsch (gemessen: 9 Treffer,
  davon 6 Fremdprozesse). Vor dem Zaehlen die Trefferliste je Prozess gegen den
  vollen Skriptnamen halten oder auf den exakten Pfad filtern
  (`CommandLine` endet auf `handel\dauerlauf.py`).
- **Vor einem manuellen Neustart den Cron-Verlauf des Waechters lesen, nicht
  nur den Live-Zustand.** Ein `no_agent`-Hermes-Cron schreibt jeden Lauf nach
  `Agenten/Hermes/cron/output/<job-id>/<zeitstempel>.md` — bei Erfolg leer
  (`silent (empty output)`), bei Eingriff mit Befund und Startversuch. Die
  Job-ID liefert `hermes.exe cron list`. Mehrere Dateien in Zeitfolge zeigen,
  ob der Waechter einen Ausfall bereits selbst geheilt hat, bevor manuell
  eingegriffen wird — sonst ist der manuelle Neustart entweder ueberfluessig
  oder verdeckt, dass der Waechter allein schon ausgereicht haette.

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

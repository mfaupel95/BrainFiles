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
   **Die entscheidende Frage ist, ob der EIGENE PORT belegt ist — nicht, ob die
   Gegenstelle gesund ist.** Ein Starter, der die Gegenstelle proben laesst,
   wird zur Spawn-Schleife, sobald sie weg ist: die Antwort wird nie „gesund",
   jeder Versuch erzeugt einen weiteren Prozess, und kein Zeitpunkt beendet ihn.
   Zwei getrennte Fragen: `_laeuft(port)` (eigener Port, `socket.create_connection`)
   und `_gesund()` (Gegenstelle). **Nur bei freiem Port starten; bei belegtem
   Port melden** („laeuft, meldet aber ungesund — kein zweiter Start"), nicht
   ein zweites Mal starten. Ein belegter Port laesst keinen zweiten Prozess zu,
   auch wenn der gerade Versuch eine Fehlermeldung wirft.
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
   **Das Skript gehoert nach `profiles/<profil>/scripts/`.** Der Cron loest einen
   Skriptpfad ausschliesslich innerhalb des Home auf, das ihn faehrt
   (`cron/scheduler_script.py::_resolve_script_path`): ein Pfad ausserhalb endet mit
   „resolves outside the scripts directory“, ein Name aus `Agenten/Hermes/scripts/`
   mit „Script not found“. Eine Wache fuer ein Profil also neben dieses Profil legen,
   nicht in die Haus-Ablage — und die Ablage in der Whitelist freigeben
   (`!Agenten/Hermes/profiles/*/scripts/` **und** `…/scripts/**`), sonst liegt die
   Wache ausserhalb von Git und verschwindet unbemerkt. Gegenprobe:
   `git check-ignore -v <pfad>` (Exit 1) und `git status --porcelain` zeigt `??`.

   **Was der Auftrag aufruft, muss ENDEN.** Ein Poller oder Dauerlauf als Skript
   laeuft bis in den Timeout und hinterlaesst einen Lauf im Zustand `running`, der
   die naechsten Feuertests verdeckt. Vor dem Einplanen am Dienst pruefen, ob der
   Unterbefehl einen Einmal-Lauf hat (`<cli> run --once`). Zahlen aus einer Datenbank
   gehoeren ohnehin nicht in einen Modelllauf: `no_agent` kann sich nicht verplaudern
   und kostet keine Tokens. Braucht ein Modelllauf den Klon, `workdir` auf das Repo
   setzen — ein Agent startet im Home des Profils und findet `Werkstatt/` von
   dort nicht.
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

## Sitzungs-Loop oder dauerhafte Wache

Zwei verschiedene Dinge heissen „Loop“ — vor dem Einrichten unterscheiden, sonst
wird eine Sitzungsschleife fuer einen Dauerbetrieb gehalten:

- **Sitzungs-Loop** (`/loop <intervall> <aufgabe>`, Alias `/proactive`): weckt nur
die laufende Sitzung im Takt, endet mit `LOOP_COMPLETE` in der Antwort, mit
`--times N` oder am Rueckfall-Budget (`loops.max_ticks`, Vorgabe 100);
`loops.min_interval_seconds` hebt zu kurze Takte auf 30 s an. Steuerung:
`/loop status | pause | resume | stop`. **Stirbt mit der Sitzung** — nie als
Ersatz fuer eine Wache verwenden, auch wenn „richte einen Loop ein“ danach klingt.
- **Dauerhafte Wache**: Hermes-Cron `no_agent` mit Skript (Ablauf oben).
Ueberlebt Sitzung und Neustart.

Eine neue dauerhafte Schleife ist eine Entscheidung, kein Handgriff: die
Hausregel (fuenf Fragen, alle mit ja — Wiederkehr belegt, Pruefkriterium in einer
Zeile, stiller Erfolg, entscheidungsarm, rein lesend) steht in
`Agenten/Hermes/skills/brainfiles/skill-schleifen/SKILL.md`. Dieses Skill liegt im
HAUPTbaum; ein Bot-Profil hat eine eigene Skill-Bibliothek und laedt es nicht per
`skill_view` — als Datei lesen.

### Wo die Cron-Auftraege wirklich liegen

- **`cronjob_manage action='list'` liest den Cron-Speicher des AKTUELLEN Profils.**
  Ein Profil kann 0 Auftraege melden, waehrend das Haus seine Auftraege faehrt: sie
  liegen im Speicher des Startprofils (`Agenten/Hermes/cron/jobs.json`), und das
  `cron/`-Verzeichnis eines frisch angelegten Profils enthaelt nur `output/` und
  gar keine `jobs.json`. Vor „es laeuft kein Auftrag“ und vor jedem Anlegen den
  Ist-Stand an der Datei lesen — `jobs.json` ist eine Liste von Dicts mit u. a.
  `name, state, schedule, script, no_agent, last_run_at, last_status,
  last_delivery_error, failure_streak` — und mit `hermes cron list` gegenhalten.
- **Ein in einem Profil angelegter Auftrag feuert nur im Scope dieses Profils.**
  Vorher klaeren, welches Home der Scheduler liest: sonst entsteht ein Auftrag,
  den niemand ausfuehrt, oder ein zweiter Auftrag fuer dieselbe Arbeit.
- **Die eigene Antwort ist nicht die Quelle fuer den Ist-Stand.** „X laeuft
  schon“/„X fehlt“ aus dem Gedaechtnis oder aus einem Werkzeug mit falschem Scope
  ist keine Messung; die Datei und `hermes cron list` sind es.

## Was ein Cron-Auftrag nicht sein kann: den Gateway selbst betreffen

**Ein Auftrag, der den Gateway neu startet, laeuft NICHT als Cron — er wird
abgelehnt, und die Ablehnung nennt den Grund.** `cronjob_manage action=create`
mit einem Skript, das `hermes gateway restart`/`stop` aufruft, endet mit

> *„Blocked: cron job contains a gateway lifecycle command … to prevent
> agent-driven SIGTERM-respawn loops under launchd/systemd supervision"*

Das ist strukturell, nicht kosmetisch: **ein Cron-Auftrag laeuft INNERHALB des
Gateways.** Ein Restart von dort beendet den eigenen Prozess, die Aufsicht
startet ihn neu, der Auftrag feuert wieder — die Schleife, die die Sperre
verhindert. Die Meldung sagt den Ausweg selbst: *„Run `hermes gateway restart`
from a shell outside the running gateway instead."* **Eine Ablehnung ist
Anleitung — ihren Text lesen, nicht umgehen wollen.**

**Der Weg fuer alles Zeitversetzte, das den Gateway betrifft:** ein
Hintergrundprozess aus einer Shell AUSSERHALB des Gateways, mit
`persist_on_release=true` (sonst stirbt er an `/new`, Kompression oder
Sitzungsende) und `notify=true` (sonst meldet sich nichts). Fuer „in N Minuten"
braucht das Skript einen eigenen Warteschalter (`--nach-sekunden N`) und
schreibt den Zielzeitpunkt SOFORT ins Protokoll, bevor es schlaeft — sonst ist
nicht belegbar, dass der Lauf angesetzt ist.

Das Skript haelt den Zustand **vorher und nachher** fest, wartet aktiv auf das
Erfolgskriterium (nicht blind `sleep`) und berichtet den Vergleich, statt
„gestartet" zu melden. Muster: `profiles/<profil>/scripts/gateway-neustart-geplant.py`.

**Nicht ueber `action='run'` umgehen wollen.** Ein sofortiges Feuern im
laufenden Gateway ist derselbe Selbstmord; der Umweg ueber eine Warteschlange
hilft nicht.

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
- **Ein Watchdog mit hoher `RestartCount` kann einen Crash-Loop stundenlang
  verstecken.** `RestartCount 99 / RestartInterval 1 min` startet einen sofort
  wieder abstuerzenden Prozess brav neu — der Scheduler zeigt `Running`/`Ready`
  ohne Fehlermeldung, waehrend in Wahrheit seit Stunden kein einziger Zyklus
  durchlief. Prozess-**Uptime** (`Get-Process <name> | Select StartTime`) gegen
  den Zeitpunkt des letzten VOLLSTAENDIGEN Zyklus im eigenen Log halten — klafft
  das auseinander (Prozess wenige Minuten alt, letzter echter Erfolg Stunden
  zurueck), ist es ein Crash-Loop und kein gesunder Dauerbetrieb, auch wenn
  gerade ein Prozess laeuft.
- **`RestartOnFailure` deckt einen SAUBEREN Stop nicht ab — die Gegenrichtung
  derselben Falle.** Eine Aufgabe mit `RestartCount 999 / Interval PT1M` startet
  nur nach einem UNERWARTETEN Abbruch neu; ein regulaerer `stop`/`restart`
  beendet sie, und **nichts startet sie von selbst**. Hat die Aufgabe als
einzigen Trigger einen `LogonTrigger` (der Normalfall bei Autostart-Diensten),
  bleibt der Dienst bis zur naechsten Anmeldung unten. Wer einen Dienst
  absichtlich stoppt, muss den Wiederanlauf **selbst einplanen** — sonst ist der
  Ausfall still, und niemand vermisst ihn bis zum naechsten Login.
  Diagnose vor dem Urteil: `schtasks /query /tn <name> /xml` lesen und die
  `<Triggers>` (nur Logon? nur Zeit?) gegen `<RestartOnFailure>` halten. Ein
  hoher `RestartCount` sagt nichts ueber den Stop-Fall.
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

## Ein Dienst, der sich vermehrt (Spawn-Schleife)

Symptom: eine Prozessgruppe waechst im Minutentakt, jedes neue Mitglied hat
dasselbe Startskript in der Kommandozeile, der Rechner wird langsam, ohne dass
ein einzelner Prozess viel tut. **Die Ursache ist fast immer die Startbedingung,
kein Leck und kein Waechter.**

Diagnose in dieser Reihenfolge:

1. **Prozesse nach Kommandozeile gruppieren** (Befehl siehe `systemdiagnose`)
   und je Gruppe zaehlen — die Zahl der Gruppe ist die Vielfachheit.
2. **Den Starter benennen, nicht das Kind.** Je Gruppe den Elternprozess suchen
   und dessen Kommandozeile lesen: das Kind ist das Opfer, der Starter ist der
   Erzeuer. Ein Kind, das selbst Kinder hat, ist eine Kette, kein Befund.
3. **Im Starter die Startbedingung lesen:** fragt es den **eigenen Port** oder
   die **Gegenstelle**? Letzteres ist die Ursache, sobald die Gegenstelle weg
   ist — die Antwort wird nie „gesund", also startet jeder Zyklus neu.
4. **Die Wachstumsrate messen:** Anzahl **vorher und nachher** ueber ein bekanntes
   Intervall, nie aus einer einzigen Zahl schliessen.

Fix: die Startbedingung auf den eigenen Port stellen (Schritt 1 oben). Dann die
Gegenprobe in **drei Faellen** am echten Modul laden und je Fall die Prozesszahl
vorher/nachher vergleichen:

| Fall | erwartetes Ergebnis |
|---|---|
| Port belegt, Gegenstelle gesund | kein Start |
| Port belegt, Gegenstelle tot | kein Start, nur Meldung |
| Port frei | genau ein Start |

Der zweite Fall ist der, der die Schwemme erzeugt hat — er muss bewiesen sein,
sonst ist der Fix eine Vermutung.

### Zwei Windows-Fallen, die den Fix wirkungslos machen

Ein korrekter Port-Test genuegt NICHT, wenn der Dienst selbst mehrere Besitzer
zulaesst. Beide Fallen erzeugen dasselbe Bild: viele Prozesse, alle "erfolgreich",
keiner beendet sich — und der Port-Test sieht trotzdem "belegt" oder "frei"
je nach Zeitpunkt.

1. **`SO_REUSEADDR` unter Windows laesst einen ZWEITEN Prozess denselben Port
   binden — ohne Fehler.** `http.server.HTTPServer` setzt
   `allow_reuse_address = True` von Haus aus. Unter Unix erlaubt das nur das
   Wiederverwenden eines Sockets im TIME_WAIT; unter Windows ist es ein
   Freibrief: kein `OSError`, kein Beenden, zwei Prozesse teilen sich den Port.
   Gemessen an einem Adapter auf 127.0.0.1: 6 Prozesse, keiner endete.
   **Fix:** in einer eigenen Server-Klasse `allow_reuse_address = False` setzen
   und das Binden in `try/except OSError` legen — der zweite Start endet dann
   mit `WinError 10048` und kann **still mit Exitcode 0** zurueckkehren (belegter
   Port ist der Normalfall, kein Fehler; ein Exitcode != 0 laesst jede Wache
   einen "Fehlschlag" melden und neu starten).
2. **`socket.getfqdn()` im Startweg — der Socket ist gebunden, aber nicht im
   Zustand LISTEN.** `HTTPServer.server_bind()` ruft `socket.getfqdn(host)`;
   `server_activate()` (das `listen()`) laeuft erst danach. Zeigt Docker Desktop
   `kubernetes.docker.internal` auf 127.0.0.1, dauert die umgekehrte DNS-Abfrage
   GEMESSEN 8,03 s. In diesem Fenster meldet `Get-NetTCPConnection -State Listen`
   "frei" und `socket.create_connection` bekommt "connection refused": jeder
   Aufrufer startet einen weiteren Dienst, obwohl der erste schon bindet.
   **Fix:** eine Server-Klasse, die `server_bind()` ueberschreibt und den Namen
   SETZT statt zu erfragen (`socketserver.TCPServer.server_bind(self)` + 
   `self.server_name = "127.0.0.1"` + `self.server_port = self.server_address[1]`).
   Der Name wird nur im Fehlertext gebraucht.

**Dazu gehoert die Reihenfolge im Startweg: erst binden, dann die Gegenstelle
fragen.** Steht die langsame Abfrage (`modelle()`, `tags`, Health-Check) VOR dem
Binden, ist der Port waehrend ihrer Laufzeit noch frei — dasselbe Rennfenster.

**Diagnose, wenn der Dienst trotz Fix nicht hochkommt:** den Start in
Einzelschritte zerlegen und jeden messen (Modul laden, Schluessel lesen,
`getfqdn`, Binden, Gegenstelle). Bleibt der Prozess bei ~0,03 s CPU und 1 Thread
stehen, wartet er auf etwas — die Einzelmessung zeigt, worauf. Laeuft jeder
Schritt einzeln schnell, aber der Start als Ganzes nicht, liegt es an der ART des
Starts: ein Dienst, der aus einer PTY/Pipe heraus gestartet wird, kann haengen.
Dann genau so starten, wie der spaetere Aufrufer es tut (abgesetzt:
`DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`, stdout in eine DATEI statt in eine
Pipe), und erst dann urteilen.
- **`subprocess` mit `text=True`** stirbt an Umlauten aus `tasklist`/`powershell`:
  die Konsole schreibt cp1252, nicht UTF-8. `encoding="cp1252", errors="replace"`
  setzen, sonst reisst ein `UnicodeDecodeError` im Lesethread den Aufruf ab.
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
  **Die Zustellung ist der zweite Beleg, nicht nur der Lauf:** in
  `profiles/<profil>/cron/executions.db` steht je Lauf `delivery_outcome` —
  `suppressed` bei leerer Ausgabe, `delivered` bei Befund. Ein Auftrag mit
  `last_status: ok` kann trotzdem nichts zugestellt haben; wer nur den Status liest,
  belegt die Wirkung nicht. Die Alarmrichtung ist ohne Eingriff in echte Daten
  pruefbar, wenn das Skript seinen Zustand in eine eigene Merkdatei schreibt: die
  Merkdatei praeparieren (alten Zeitstempel bzw. geleerte Befundliste setzen),
  `cronjob action='run'`, dann muss im `cron/output` genau die erwartete Meldung
  stehen. Deshalb bekommt so ein Wachenschritt einen `--merkdatei`-Schalter — ohne
  ihn kostet jede Probe einen echten Ausfall und wird deshalb nicht gemacht.
- **Der erste Lauf einer Merkdatei-Wache ist eine Grundlinie, keine Meldung.** Fehlt
  die Merkdatei, ist der Bestand „neu“ — ein Bericht ueber tausende Zeilen, der wie
  ein Fehlalarm aussieht und den Empfaenger gegen die Wache abstumpft. Den
  Erster-Lauf-Fall (`letzte_ts == 0`) erkennen und schweigen lassen; der Merkstand
  wird trotzdem geschrieben, damit der zweite Lauf echt vergleicht.
- **Berichtstakt und Sammeltakt duerfen nicht gleich sein.** Ein Bericht im selben
  Takt wie der Sammler liest den Sammelvorgang mitten im Lauf: der Merkstand steht
  dann auf dem hoechsten Zeitstempel, die eben noch nicht gelesenen Fuellungen
  liegen darunter und sind beim naechsten Lauf unsichtbar. Den Bericht langsamer
  takten als den Sammler (gemessen: Sammler 20 Min, Bericht 60 Min) und im Bericht
  NUR lesen, nie selbst sammeln — zwei Schreiber auf einer Zustandsdatei sind
  Doppelarbeit und ein Mischstand.
- **Ein Skript, das in zwei Ablagen liegen kann, darf seine Wurzel nicht zaehlen.**
  Dasselbe Wachenschritt-Skript liegt je nach Einbau in `Agenten/Hermes/scripts/`
  ODER in `Agenten/Hermes/profiles/<profil>/scripts/` (der Cron loest nur im
  eigenen Profil auf, siehe Schritt 4) — eine feste Zahl von `dirname`-Aufrufen
  ist in der einen der beiden Ablagen falsch, und der Fehler faellt erst zur
  Laufzeit auf. Die Wurzel aufwaerts suchen: vom eigenen Ordner nach oben, bis ein
  Verzeichnis die erwartete Struktur traegt (z. B. `Werkstatt/<name>`), mit
  einer Umgebungsvariable als Uebersteuerung und einem Rueckfall auf den
  Vorgabepfad.
- **Ein abgeloester Auftrag bleibt scharf, auch in einem fremden Profil.** Wird eine
  Wache durch eine andere ersetzt, feuert die alte weiter (jedes Profil hat seinen
  eigenen Cron-Speicher) — doppelte Meldung, und wenn sie einen Modelllauf startet,
  doppelte Kosten. Beim Ersetzen den alten Auftrag suchen (alle
  `profiles/*/cron/jobs.json` nach dem Namen durchsuchen, nicht nur den eigenen
  Speicher) und den Befund melden; `pause` statt `remove`, damit der Verlauf bleibt.
  Einen fremden Cron-Speicher nicht selbst anfassen — das ist die Entscheidung des
  Nutzers. Ein Lauf, der `running` stehen bleibt, laesst `last_run_at` auf `None`:
  „nie gelaufen“ und „haengt noch“ sehen in der Auftragsliste gleich aus, das Alter
  aus `executions.db` entscheidet.

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

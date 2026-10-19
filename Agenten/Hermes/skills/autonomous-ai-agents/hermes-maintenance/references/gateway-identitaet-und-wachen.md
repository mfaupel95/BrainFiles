# Gateway-Identitaet: warum `hermes update` abbrach - und die Wachen dafuer

Fall vom 29.09.2026. Der Lauf kam bis zum Gateway-Schritt und starb dort; die
Wachen, die das kuenftig verhindern sollen, brachten zwei eigene Fallen mit.

## 1. Das Symptom

`hermes update` endet nach dem Pre-update-Snapshot mit `exit_code 1`:

    Stopping Windows gateway process(es) before updating Hermes...
    Paused gateway profile(s): default
    stop_reason: RuntimeError: Could not map Windows gateway PIDs to profiles:
                 Could not inspect gateway PID for profile default

Der Code-Teil ist bis dahin in Ordnung - der Abbruch sitzt zwischen "Gateway
pausieren" und "Code tauschen".

## 2. Zwei Ursachen - beide muessen gemessen werden

1. **Startform.** Der Update-Restart-Watcher startet den Gateway als
   `python -I -c "<bootstrap>" … gateway run`. Der kanonische Matcher
   `gateway.status.looks_like_gateway_runtime_command_line` verweigert `-c`
   ABSICHTLICH (Upstream-Issue #107002): eine Bootstrap-Zeile ist keine
   belastbare Identitaet. Zweite bekannte Form: `runpy.run_module('hermes_cli.main',
   run_name=…)` - zwischen Modulname und Unterbefehl stehen dann Argumente, ein
   Muster auf `-m <paket> gateway run` findet nichts.
2. **Fehlende PID-Metadaten.** `gateway.pid` fehlt bzw. der Lock meldet
   `active gateway lock has no PID metadata`. Die PID steht trotzdem in
   `gateway.lock` - sie wird nur nicht gelesen.

Die Sicht des Updaters ist die Messgroesse, nicht der Port:

    python -c "from hermes_cli.gateway import find_profile_gateway_processes as f; \
               print([(x.profile, x.pid) for x in f(strict=True)])"

`RuntimeError` = der Updater sieht den Gateway nicht (das ist der Abbruchgrund).
`[('default', <pid>)]` = die Sicht ist gut, der naechste Lauf traegt.
Aus dem Checkout heraus mit `hermes-agent/venv/Scripts/python.exe` fahren
(`PYTHONHOME`/`PYTHONPATH` vorher entfernen).

## 3. Die Reparatur: klassisch starten

- Der Gateway muss in einer Form laufen, die der Updater kennt:
  `-m hermes_cli.main gateway run`. Genau das tut der Launcher
  `gateway-service/Hermes_Gateway_<suffix>.vbs`; ihn starten ist die Reparatur.
- **Der Launcher muss `pythonw.exe` nehmen, nicht `python.exe`.** Er startet
  ueber `WScript.Shell.Run <zeile>, 0, False` (Fensterstil 0 = versteckt) - und
  Stil 0 startet ein **Konsolen**programm GAR NICHT: kein Prozess, KEINE
  Fehlermeldung, der Aufruf kehrt sauber zurueck. Gemessen mit zwei
  `cscript`-Proben, die eine Datei schreiben liessen und danach `Test-Path`
  darauf fragten:

      Ziel                     Stil 0   Stil 1   Stil 2   Stil 3   Stil 7   Stil 8
      cmd /c echo ...          nein     ja       nein     ja       nein     ja
      python.exe (Konsole)     nein     ja        -        -        -        -
      pythonw.exe (GUI)        JA       ja        -        -        -        -

  `sh.Exec` und das FileSystemObject arbeiten normal - es trifft nur diesen
  einen Weg. Ein Launcher, der `python.exe` mit Stil 0 startet, kann deshalb
  NIE etwas starten, und der Waechter protokolliert derweil im Zwei-Minuten-Takt
  "kein Gateway-Prozess - Neustart ausgeloest". Reparatur: in der VBS auf
  `tools\python-3.14.7+<stand>-win32-x64\pythonw.exe` umstellen (GUI-Subsystem,
  laeuft mit Stil 0 versteckt). Wer den Start von Hand nachsehen will, faehrt
  dieselbe Zeile mit `python.exe` aus einer Konsole. `hermes update` schreibt die
  VBS neu und setzt sie wieder auf `python.exe` - nach JEDEM Lauf nachsehen.
- **`sh.Run` nie glauben, immer nachmessen.** Der Beweis ist der Kindprozess
  bzw. eine Datei, die er geschrieben hat, nicht die Erfolgsmeldung. Ein
  VBS-Einzeiler, der eine Datei schreibt, plus `Test-Path` darauf, entscheidet
  in zehn Sekunden, ob ein Startweg ueberhaupt funktioniert.
- Fehlende PID-Metadaten aus `gateway.lock` rekonstruieren (PID + Zustand
  `running`), nicht aus dem Bauch schreiben.
- Danach erneut messen: Discovery-Liste, `hermes gateway status`,
  `hermes update --plan`. Erst wenn die Discovery den Profilnamen nennt, ist der
  naechste Update-Lauf aussichtsreich.

## 4. Die Wache dazu (Hermes-Cron, `no_agent`)

- Skript `Agenten/Hermes/scripts/gateway-identitaet-wache.py`, Cron
  `gateway-identitaet-wache` (taeglich, `no_agent`, `deliver telegram`): **leere
  Ausgabe = alles gut**, nichts wird gesendet.
- Sie prueft genau die Bedingung des Updaters
  (`find_profile_gateway_processes(strict=True)`), nicht einen Port.
- Blindfall: klassischer Neustart - aber **nur wenn kein `hermes update` laeuft**
  und **hoechstens einmal pro Tag** (Merker im Zustand). Ein Neustart waehrend
  eines Updates zerlegt genau den Lauf, den die Wache schuetzen soll.
- Meldungen **mit Wirkung** (durchgefuehrter Neustart) immer senden, auch wenn der
  Kern identisch ist: `melden(..., erzwingen=True)`. Die Wiederholungssperre
  verschluckt sonst den einzigen Beleg, dass die Wache gearbeitet hat.
- Aufbau wie jede Haus-Wache: nur Standardbibliothek (der Cron laeuft nicht in der
  venv der Komponente), Fachmodule per `importlib.util.spec_from_file_location`
  ueber den PFAD laden, Zustand in `cache/`, Tests nach
  `Agenten/Handel/tests/` (dort liegen die Haus-Suiten).

## 5. Die zwei Wachen-Fallen aus diesem Fall

**(a) Eine Prozessabfrage traegt ihren Suchtext selbst.**
`Where-Object { $_.CommandLine -match 'hermes_cli.main update' }` findet die
laufende Abfrage - also meldet die Wache IMMER "es laeuft ein Update" und heilt
nie. Gegenmittel: Muster aus Teilen bauen (`'hermes_cli.main' + ' ' + 'update'`),
`$_.ProcessId -ne $PID` setzen, `$_.Name -eq 'python.exe'` ergaenzen, `-like`
statt `-match`. Test, der das festnagelt: die Abfrage darf sich selbst nicht finden.

**(b) Eine Wache, die eine ADRESSE prueft statt die Bedingung.**
`gateway-waechter.ps1` fuehrte "Port 9900 ist die Wahrheit" und startete den
Gateway, sobald der Port zu war. Seit dem Update derselben Woche lauscht der
Gateway auf einem Named Pipe und bedient Webhooks auf Port 8644 - **TCP 9900
bleibt zu, waehrend der Dienst gesund laeuft**. Folge: 128 Zeilen "Neustart
ausgeloest" an einem Tag, und jeder Neustart reisst die laufenden Verbindungen mit.

Richtige Bedingung: es laeuft ein Prozess `hermes_cli.main gateway run` (ohne
`--profile`) UND er antwortet - Control-Pipe ODER Port.

**Der Pipe-Check ist auf diesem Host TOT - der Waechter traegt allein Port 9900.**
`[System.IO.Directory]::GetFiles('\\.\pipe\')` (und `Get-ChildItem '\\.\pipe\'`)
werfen hier `DirectoryNotFoundException` (der Pfad wird zu `C:\pipe` aufgeloest),
werden im `catch` geschluckt und liefern IMMER `$pipe_da = $false`. Die
"Control-Pipe ODER Port"-Bedingung ist also in Wahrheit nur der Port. Das ist
harmlos, solange der Gateway 9900 bindet (gemessen 14.10.2026: offen) - aber
irrefuehrend: wer den Pipe-Zweig fuer tragend haelt, sucht den Ausfall an der
falschen Stelle. Vor jeder Aussage "der Waechter prueft Pipe ODER Port" die
Port-Realitaet messen (`Test-NetConnection 127.0.0.1 -Port 9900`); ist 9900 zu,
obwohl der Dienst gesund laeuft, ist der Pipe-Check zu reparieren, nicht zu
ignorieren. Antwortet ein alter Prozess nicht, ist EIN Neustart je 30 Minuten
erlaubt (Merkerdatei) - sonst entsteht die Schleife wieder.

**(c) Eine Wache, die nur EINEN Programmnamen kennt.**
`gateway-waechter.ps1` suchte hart `Name='python.exe'` bzw.
`ProcessName -eq 'python'`. Ein Launcher, der auf `pythonw.exe` umgestellt wird
(GUI-Subsystem - der einzige Weg, ein Python versteckt zu starten, siehe
Abschnitt 3), ist fuer so eine Wache unsichtbar: sie sieht einen gesunden
Gateway nicht und startet im Takt weiter neu. Immer BEIDE Namen suchen -
`Name='python.exe' or Name='pythonw.exe'` bzw.
`ProcessName -in @('python','pythonw')` - und die Wache danach einmal von Hand
laufen lassen: sie muss still bleiben (exit 0, keine neue Logzeile).

**(d) Ein Muster, das nur den MODULNAMEN fordert, trifft jeden Unterbefehl.**
Die Wache nahm als zweite Startform `run_module\('hermes_cli\.main'` - das trifft
JEDEN `runpy`-Start des Hauptmoduls, auch den **Dashboard**
(`sys.argv = ['…main.py', 'dashboard', '--no-open', …]`). Solange der Dashboard
lief, hielt die Wache ihn fuer den Gateway und startete nichts: **2,5 h Ausfall
unbemerkt**, waehrend `gateway_state.json` weiter `running` meldete und die
Control-Pipe fehlte. Das Muster muss den UNTERBEFEHL fordern und den Nachbarn
ausschliessen:

    if ($c -match 'hermes_cli\.main gateway run') { return $true }
    if ($c -match 'run_module\(''hermes_cli\.main''' -and $c -match "'gateway'" `
        -and $c -notmatch "'dashboard'") { return $true }

Gegenprobe VOR dem Einbau: denselben WMI-Filter von Hand fahren und die Treffer
AUFLISTEN. Steht ein fremder Dienst darin (Dashboard, TUI-Backend, Agent), ist
das Muster zu breit - und die Wache wird genau in dem Moment blind, in dem sie
gebraucht wird.

**(e) Das Selbstzeugnis kann luegen - Frische vor PID glauben.**
`gateway_state.json` meldete `gateway_state: running` mit einer PID, die laengst
tot war: wird der Prozess hart gekillt (SIGKILL/OOM/Kill durch einen Nachfahren),
schreibt kein Exit-Pfad den Zustand fort, und die Datei bleibt auf dem letzten
Stand stehen. Deshalb VOR dem PID-Glauben zwei Zeilen: Alter von `updated_at`
(Herzschlag, gegen den SCHREIBRHYTHMUS gerechnet) und `Get-Process -Id <pid>`.
**Die Frische-Grenze nicht raten — der Gateway schreibt seinen Stand gemessen nur alle
~7 Minuten** (`updated_at` 16:05:13 -> 16:12:36). Eine 600-s-Grenze erklaerte damit einen
gesunden, nur schreibtraegen Dienst fuer tot, und der Waechter startete im 12-Minuten-Takt
einen zweiten (Logzeile "kein Gateway-Prozess - Neustart ausgeloest", obwohl er lief);
mit 1800 s bleibt er still, und die Antwortpruefung (Control-Pipe ODER Port) traegt das
Urteil ohnehin mit. Wer eine Frische-Pruefung in eine BESTEHENDE Wache einbaut, misst den
Rhythmus vorher aus den Zeitstempeln der Datei selbst — sonst schliesst der Fix eine
Luecke und reisst gleich eine neue auf. Ohne sie ist "der Zustand
sagt running" keine Messung, sondern eine Behauptung. Der harte Kill hinterlaesst
in `logs/gateway.log` die Zeile `exited UNCLEANLY (no exit path ran - SIGKILL /
OOM / VM death, or a process kill issued by the agent or one of its descendants)`
mit `last_heartbeat_at` - das ist der Zeitpunkt, ab dem die Datei nicht mehr gilt.

**(f) Ein deaktivierter Waechter-Task = ungeschuetzter Gateway, und nichts faengt es ab.**
Der 5-h-Ausfall (13.10.2026) war KEIN Erkennungsfehler: der Waechter-Task war
**deaktiviert** (letzter Lauf 12.10. 17:43, erst ~23:53 wieder aktiviert), also lief
er im Ausfall-Fenster gar nicht und konnte den Gateway nicht neu starten. Ein
deaktivierter Task kann sich nicht selbst reaktivieren, und ein NUR-meldender Check
laesst das Fenster bis zum naechsten Crash offen (13.10.: der Morgenbericht meldete
den deaktivierten Waechter, 8 h spaeter kam der Ausfall). Die Systempruefung aktiviert
kritische Waechter deshalb SELBST wieder: Block 9 fuehrt die Liste $kritischeWaechter
(derzeit MaxHirn-Gateway-Waechter), reaktiviert per `schtasks /Change /ENABLE` und
meldet es als ``[erledigt]`` - gewollt Deaktivierte bleiben in der Allowlist
$gewolltDeaktiviert unangetastet. ZWEI FALLEN: (1) `Enable-ScheduledTask` scheitert
auf diesen Tasks mit 0x80070005 (Administrationsrechte, auch fuer den eigenen
Limited-Task) - `schtasks /Change /ENABLE`|`/DISABLE` laeuft ohne Elevation; eine
nicht-erhoehte Routine nimmt IMMER schtasks. (2) Eine Selbstheilung nie am ECHTEN
Waechter testen (das hiesse, ihn zum Test zu deaktivieren = schutzlos): einen
Wegwerf-Task anlegen (`schtasks /Create /TN 'MaxHirn-<x>Test' /TR '...' /SC ONCE /ST
23:59 /F`) und deaktivieren, den Namen TEMPORAER in die kritische Liste aufnehmen,
den Lauf ausfuehren, die ``[erledigt] wieder aktiviert``-Zeile im Protokoll
nachweisen, dann Liste zurueckbauen, Task loeschen und die vom Testlauf
ueberschriebenen Berichte aus einer Sicherung zurueckschreiben.
Diagnose, ob ein Task in einem Zeitfenster ueberhaupt lief: `wevtutil qe
"Microsoft-Windows-TaskScheduler/Operational" /q:"*[System[TimeCreated[@SystemTime>=
'<start>Z' and @SystemTime<='<end>Z']]]" /f:text /c:200` und nach dem Tasknamen
greppen - `Get-WinEvent` mit Zeitfilter lief hier in den 90-s-Timeout, wevtutil war
sofort da. Ein leeres Waechter-Log im Ausfall-Fenster ist ZWEIDEUTIG ("lief nicht"
ODER "lief und fand den Gateway gesund" - Erfolgsmeldungen gehen in den Bus, nicht
ins Log); erst das TaskScheduler-Ereignislog entscheidet. Und: ein Waechter, der
mehrfach am Tag einen instabilen Gateway neu startet, wird gern deaktiviert, um die
Neustart-Serie zu stoppen - genau dann ist der Gateway schutzlos. Die Neustart-Serie
ist der Befund, der gefixt gehoert, nicht der Waechter.

**Zaehlen, nicht glauben.** Ob eine Prozesswache in einer Schleife haengt, verraet
nicht die einzelne Logzeile ("kein Prozess - Neustart ausgeloest" liest sich
richtig), sondern die ZAHL der Neustarts gegen die Takte im selben Zeitraum.
Vor/Nach-Vergleich derselben Zaehlung ist der Beleg.

## 6. Der Beweislauf: das Update wirklich fahren

1. Belegskript als `.ps1` schreiben, das die Head-Revision VOR und NACH dem Lauf
   protokolliert und `EXIT` anhaengt (`BEFORE_HEAD`, `AFTER_HEAD`, `Abstand`, `EXIT=`),
   `PYTHONIOENCODING=utf-8` setzen, `hermes update --yes` fahren.
2. **Abgekoppelt starten** (`Start-Process … -WindowStyle Hidden`): der Lauf
   pausiert und startet den Gateway neu, jede Werkzeug-Rueckkehr reisst es mit.
3. Log am ENDE lesen. Erfolg ist nicht der Exit-Code, sondern:
   `Restarting Windows gateway profile(s): default` plus
   `Fleet version check: ✓ default (pid …) @ <sha> — up to date`.
4. Danach fragen: Discovery-Liste, Dashboard (`Start-ScheduledTask
   -TaskName 'Hermes_Dashboard'`, dann HTTP 200 auf 9119), Wache (muss still sein).
5. `EXIT=1` wegen eines nicht zurueckgeholten Dienstes ist der bekannte Fall
   (Dashboard) - siehe Abschnitt "Nach dem Lauf: Exit 1 …" in SKILL.md.

## 7. Restblocker: `[WinError 5] Zugriff verweigert: <HERMES_HOME>/tools/.displaced-*/<datei>`

Der Lauf bricht beim "Source update preparation" ab, weil er ein vom pm-Installer
zurueckgelassenes `.displaced-<hash>`-Verzeichnis aufraeumen will und an einer Datei darin
scheitert (Rechte oder noch ein Zugriff). Getroffen wurden schon `node.exe` und
`DLLs\libcrypto-3-x64.dll` - dieselbe Klasse, anderer Dateiname; das Verfahren ist
dasselbe. Erkennen:

    ls -la --time-style=+%d.%m_%H:%M <HERMES_HOME>/tools | grep displaced
    Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -like '*displaced*' }

Ein `.displaced-*` ohne Prozess darauf ist ein Aufraeumrest und darf weg: nach dem
Entfernen zieht der naechste Lauf die restlichen Commits nach. Ein `.previous-*`
gehoert zum Rollback der Tool-Tauschaktion und bleibt unangetastet. Achtung: Den
Blocker zu raeumen schliesst die Obligation NICHT - der Standalone-Tail committet den
Dependency-Stempel nicht, Abschlussverfahren in `references/update-schwanz-endlosschleife.md`.

## 8. Zwei Fallen beim Aufschreiben (beide erlebt)

- **Die Uhr der Sandbox geht falsch.** `date` im Terminal-Werkzeug liefert die Uhr
  des Docker-Containers, nicht des Rechners - gemessen 7,5 h Rueckstand, weil der
  Container nach dem Ruhezustand nicht nachzieht. Folge: jede frisch geschriebene
  Datei traegt einen Stunden alten Zeitstempel, gilt damit als "ruhend" und wird
  von `Agenten/Routinen/fremdarbeit-einziehen.ps1` als **fremde Arbeit** committet
  (`Author: Andere Sitzung <fremd@local>`, Meldung "38 ruhende Datei(en)").
  Datum/Zeit fuer Notizen, Commits und Fristen nur vom Host (`Get-Date` ueber die
  Host-PowerShell) oder aus `git log -1 --format=%ci` nehmen.
- **Der Git-Index gehoert allen Sitzungen.** Vor jedem Commit `git status --porcelain`
  auf die ERSTE Spalte pruefen (vorgemerkt = fremd) und nur eigene Pfade stagen;
  `git diff --cached --numstat` zeigt, was wirklich drin liegt. Bei einem
  `Write`-Fehlschlag (write_file verweigert ohne vorheriges Lesen) meldet `git add`
  sonst still die ALTE Fassung als aktuell.
- **Eine Datei mit fremden ZEILEN laesst sich nicht per `git add <pfad>` sauber committen.**
  `hermes config set` schreibt die GANZE `config.yaml` neu und nimmt dabei mit, was eine
  parallele Sitzung dort schon geaendert hatte (im Diff nicht unterscheidbar von der eigenen
  Zeile: `git diff --numstat` zeigte 5/2 fuer eine einzige neue Einstellung). Richtig ist ein
  Blob-Commit: Eigen-Version bauen (HEAD-Fassung + eigene Zeilen, Zeilenende aus dem
  ROHEN Text ableiten), dann
  `git hash-object -w --path=<pfad> <eigen-datei>` -> `git update-index --cacheinfo
  100644,<sha>,<pfad>` -> `git commit` OHNE Pfadangabe. Gegenprobe: `git diff --cached
  --numstat` muss genau die eigenen Zeilen zeigen (hier 2/0). Der Arbeitsbaum behaelt die
  fremden Aenderungen und bleibt danach korrekt als ` M` stehen. Gegenprobe vorher:
  `diff <(git show HEAD:<pfad>) <(tr -d '\r' < <backup von vor dem Eingriff>)` zeigt, was
  schon vor dem eigenen Schreiben anders war.

## 9. Abschluss (gehoert zum Auftrag)

- Wiki nachziehen: `Wiki/Betrieb/Hermes.md` (Abschnitt Gateway-Identitaet),
  `Wiki/Betrieb/Wachen-und-Aufgaben.md` (Wache prueft Bedingung, nicht Adresse),
  `Wiki/Lektionen/Wahrheit-pruefen.md` (Prozessabfrage traegt ihren Suchtext selbst).
- **Jeden nicht angefassten Punkt als Aufgabe** in `MaxHirn/Archiv/TASKS.md`
  eintragen (oben unter `## Offen`, eigene ID, Kontext / Naechster Schritt /
  Angelegt / Betrifft), Erledigtes unter `## Erledigt`. Das ist eine stehende
  Hausregel, nicht optional.
- Nur eigene Pfade committen (`git add <pfad>`), dann pushen und die unpushed-Zahl
  nachzaehlen (`git rev-list --count origin/master..HEAD` muss 0 sein).

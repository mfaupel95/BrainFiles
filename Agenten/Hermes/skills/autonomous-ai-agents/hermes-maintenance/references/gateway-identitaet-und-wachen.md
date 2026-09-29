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
`--profile`) UND er antwortet - Control-Pipe ODER Port:

    [System.IO.Directory]::GetFiles('\\.\pipe\\') | Where-Object { $_ -match 'hermes-gateway' }

Das aus einer **Datei** ausfuehren (`.ps1`), nie als `-Command`: die Bash-Huelle
frisst die Backslashes und die Probe wird falsch (leeres Ergebnis, das wie "kein
Pipe" aussieht). Antwortet ein alter Prozess nicht, ist EIN Neustart je 30
Minuten erlaubt (Merkerdatei) - sonst entsteht die Schleife wieder.

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

## 7. Restblocker: `[WinError 5] Zugriff verweigert: <HERMES_HOME>/tools/.displaced-*/node.exe`

Der Lauf bricht beim "Source update preparation" ab, weil er ein vom pm-Installer
zurueckgelassenes `.displaced-<hash>`-Verzeichnis aufraeumen will und an einem
`node.exe` darin scheitert (Rechte oder noch ein Zugriff). Erkennen:

    ls -la --time-style=+%d.%m_%H:%M <HERMES_HOME>/tools | grep displaced
    Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -like '*displaced*' }

Ein `.displaced-*` ohne Prozess darauf ist ein Aufraeumrest und darf weg: nach dem
Entfernen zieht der naechste Lauf die restlichen Commits nach. Ein `.previous-*`
gehoert zum Rollback der Tool-Tauschaktion und bleibt unangetastet.

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

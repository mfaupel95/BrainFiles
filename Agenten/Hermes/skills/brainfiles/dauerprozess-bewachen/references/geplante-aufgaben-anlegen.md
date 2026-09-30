# Eine Windows-Aufgabe anlegen, die auch wirklich dort ankommt

Gilt fuer jede neue geplante Aufgabe (`MaxHirn-*`) und fuer den Selbstheiler, der
eine verschwundene Aufgabe nachzieht.

## Warum der uebliche Weg aus dem Werkzeug-Terminal NICHT zaehlt

- `Register-ScheduledTask` aus der Sandbox meldet Erfolg (`State Ready` +
  naechster Lauf) — die Aufgabe ist im NAECHSTEN Aufruf nicht mehr da, weil die
  Sandbox ihren eigenen Aufgaben-Speicher hat (auch `Get-ScheduledTask -TaskName`
  findet dort sogar VORHANDENE Host-Aufgaben nicht, `HRESULT 0x80070002`).
- Verlaessliche Sichten: die AUFZAEHLUNG
  (`Get-ScheduledTask | Where-Object TaskName -like 'MaxHirn-*'`) und
  `schtasks /query /tn <name>`.
- Deshalb: **Anlegen per `schtasks /create /xml`, Pruefen per `schtasks /query`,
  Starten per `schtasks /run`** — und der Beweis ist ein ZWEITER Aufruf, nicht
  der, der angelegt hat.

## XML-Vorlage

`schtasks` verlangt die Datei in **UTF-16LE** (`[System.IO.File]::WriteAllText($pfad,
$xml, [System.Text.Encoding]::Unicode)`), sonst bricht der Import ab. Die vier
Einstellungen, die eine Haus-Aufgabe ausmachen:

| Einstellung | Wert | Warum |
|---|---|---|
| `MultipleInstancesPolicy` | `IgnoreNew` | sonst waechst je Ausloesung eine Instanz dazu |
| `StartWhenAvailable` | `true` | holt einen Lauf nach, wenn der Rechner zur Zeit war |
| `Hidden` | `true` | kein aufblitzendes PowerShell-Fenster |
| `ExecutionTimeLimit` | `PT6H` | lange Erstlaeufe erlaubt, ein Haenger steht nicht ewig |

Weiter: `<LogonType>InteractiveToken</LogonType>` + `<RunLevel>LeastPrivilege</RunLevel>`
(interaktiver Benutzer, keine Erhoehung noetig), Trigger als `<CalendarTrigger>` mit
`<ScheduleByDay><DaysInterval>1</DaysInterval>`, Aktion als `powershell.exe` mit
`-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "<skript>"`.
Anschliessend `Start-ScheduledTask`/`schtasks /run` einmal feuern und den echten
Lauf im Protokoll des Skripts nachsehen — die Registrierung allein ist kein Beweis,
dass die Aktion stimmt.

## Der Selbstheiler (Cron, `no_agent`, aus dem Gateway)

Pflichtteile des Skripts:

1. **Existenz pruefen ueber `schtasks /query`**, nicht ueber Cmdlets.
2. **Drei Zustaende unterscheiden:** `da` (nichts ausgeben), `abgeschaltet`
   (`schtasks /change /tn <name> /enable`, Meldung), `fehlt` (Registrar rufen,
   danach NOCHMALS pruefen und nur bei `da` Erfolg melden).
3. **Leere Ausgabe, wenn sie steht** — der Cron sendet dann nichts (Watchdog-Muster).
4. **Nur ASCII-Marker auswerten** (`Aufgabenname`, `Status:`, `Deaktiviert`): die
   Konsolen-Codepage liefert Umlaute als Ersatzzeichen, die Marken bleiben intakt.
5. **`PYTHONHOME`/`PYTHONPATH` vor jedem Kindaufruf entfernen** und `powershell.exe`
   mit `-NoProfile` starten.

Vorlage: `Agenten/Hermes/scripts/ausserhaus-aufgabe-sichern.py`.
Pruefen: `cronjob_manage action=run job_id=<id>` (laeuft im Gateway, also auf dem
Host) und die Ausgabe lesen — ein Lauf, der eine Aufgabe anlegt, sagt das in einer
Zeile; danach ist die Aufgabe auch fuer die naechste Sitzung da.

## Pitfalls

- **Der Pfad zum Registrar ist die haeufigste Falle.** Aus `Agenten/Hermes/scripts/`
  ist die Wurzel `Path(__file__).parents[3]`; mit `parents[2]` entsteht
  `Agenten/Agenten/Routinen/...` und das Skript meldet "Registrar fehlt", obwohl die
  Datei existiert. Pfad ausgeben und gegen `is_file()` pruefen, nicht zaehlen.
- **Nach jeder Reparatur am Cron-Skript den Auftrag sofort feuern** — der
  gespeicherte `last_status` bleibt bis zum naechsten Takt auf `error`.
- **Eine Aufgabe, die nur bei angestecktem Ziel etwas tun kann, behandelt "Ziel
  fehlt" als uebersprungen** (eigener Exitcode, z. B. 2), nie als Fehlschlag: sonst
  meldet die Wache jeden Tag denselben Pseudo-Fehler, und die echte Meldung geht
  darin unter.
- **Zwei Sicherungen fuer dasselbe Ziel bauen:** die Aufgabe, die sichert, UND eine
  Fristwache, die das ALTER des Ziels gegen eine Frist haelt. Faellt die Aufgabe
  aus, ist ihr Ausfall sonst nur daran zu sehen, dass die Kopie still alt wird.

## Wie ein LAUF belegt wird (und wie eine Behauptung widerlegt wird)

- **Nur der Planer beweist die Aufgabe.** Ein Handlauf des Wrapper-Skripts belegt
  das Skript, nicht die Aufgabe - er zeigt nicht, ob Aktion, Trigger und
  Benutzerkontext stimmen. Beleg ist `Get-ScheduledTaskInfo -TaskName <name>` mit
  `LastRunTime`, **`LastTaskResult 0`**, `NextRunTime` (morgen, gleiche Uhrzeit)
  und `NumberOfMissedRuns 0`, plus die ENDE-Zeile des Laufs im Protokoll. Erst
  danach ist „die Aufgabe erneuert X von selbst" gedeckt; vorher heisst es „der
  Wrapper laeuft".
- **Eine Behauptung ueber eine Aufgabe ist kein Befund.** Ein Eintrag in
  `TASKS.md`, ein Wiki-Satz oder ein Protokoll kann „die Aufgabe ist nicht
  registriert" sagen, obwohl sie steht: der Name-Lookup meldet Vorhandenes als
  fehlend (`HRESULT 0x80070002`), waehrend die Aufzaehlung sie zeigt. Vor dem
  Nachlegen - und vor dem Eintragen eines solchen Befunds - mit DREI Sichten
  messen: `schtasks /query /tn <name>`, `Get-ScheduledTask -TaskName <name>` und
  die Aufzaehlung `Get-ScheduledTask | Where-Object TaskName -like 'MaxHirn-*'`.
  Ein Lauf von Hand im Protokoll ist kein Gegenbeweis: er stammt nicht vom Planer,
  und sein Zeitstempel verraet nur, dass jemand das Skript aufgerufen hat.
- **Der Aufgabenname gehoert in den Befund, nicht das Wort „Aufgabe".**
  Verschwundene, abgeschaltete und nie angelegte Aufgaben sehen im Bericht gleich
  aus; ohne den Namen und den Zustand (`Ready`/`Disabled`) ist der Befund nicht
  nachpruefbar.

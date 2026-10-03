---
id: 20260921-windows-umgebung
title: 'Lektionen — Windows-Umgebung'
tags: [lektion, windows]
created: 2026-09-21
updated: 2026-09-23
related: ['[[Betrieb/Docker-und-Sandbox]]', '[[Betrieb/Hermes]]']
summary: 'PYTHONHOME-Vergiftung, Pfadaufloesung relativer Programme, Werkzeugsuche, Umgebungsvariablen-Stores, Commit-Limit, Kindprozesse beenden, Groessen messen unter Junctions.'
---

# Windows-Umgebung

## 1. `hermes.exe` startet nicht: PYTHONHOME entfernen

**Regel.** Vor jedem Aufruf eines Python-Programms / venv-Starters aus einer
MCP-/Supervisor-Kette: `Remove-Item Env:PYTHONHOME, Env:PYTHONPATH`.

**Ursache.** Nicht der Supervisor. Ein **uv-venv** (`AppData\Roaming\uv\python\...`)
setzt `PYTHONHOME` in die eigene Prozessumgebung; jedes Kind erbt sie und stirbt mit
`Fatal Python error: init_import_site ... _thread ... start_joinable_thread`, obwohl das
Ziel-venv gesund ist.

**Dauerhafter Fix.** venvs auf python.org-Basis bauen
(`...\Programs\Python\Python313\python.exe -m venv .venv`) — setzt kein PYTHONHOME.
Alle sechs MCP-Server-venvs wurden am 18.09.2026 so umgestellt; der Fix wirkt erst in
NEUEN Sitzungen.

## 2. Relative Programmnamen werden gegen das cwd des KINDES aufgeloest

**Regel.** `Popen([".venv\\Scripts\\pythonw.exe", ...], cwd=<repo>)` faellt mit
`FileNotFoundError` um. Jeden relativen Programmpfad VOR dem Start gegen `cwd`
aufloesen und eine absolute Liste uebergeben.

**Warum.** `argv[0]` wird gegen das Arbeitsverzeichnis des AUFRUFERS aufgeloest, nicht
gegen das `cwd` des Kindes.

## 3. Werkzeugsuche: `which` luegt unter MSYS

**Regel.** „X ist nicht installiert" nur nach `Get-Command X` in PowerShell sagen.

**Warum.** `which` im MSYS-Shell sieht nur die MSYS-PATH. Gemessen: VS Code liegt in
`AppData\Local\Programs\Microsoft VS Code\bin\code.cmd` — `which code.cmd` findet nichts,
PowerShell schon.

## 4. Umgebungsvariablen: der Store entscheidet

**Regel.** Windows-Benutzervariablen ueber
`[Environment]::GetEnvironmentVariable(name,'User')` lesen (bzw. `'System'` fuer
`setx /M`).

**Warum.** `Get-ItemProperty HKCU\Environment` loest in der MCP-PowerShell auf einen
ANDEREN Benutzerkontext auf: gesetzte Variablen erschienen leer, obwohl vorhanden. Auch
ein MCP-Client reicht Benutzervariablen **nicht** an Serverprozesse durch — direkt aus
der Registry lesen oder einen `env`-Block setzen.

**Zusatzfalle.** Eine Datei oder ein Schluessel kann unsichtbar kaputt sein: Der
Registry-Eintrag `#ANTHROPIC_API_KEY` trug ein Rautenzeichen im **Namen** und war
dadurch unbrauchbar.

## 5. Das echte Limit ist der Commit, nicht der RAM

**Regel.** Bei „Modell startet nicht" / `ggml_backend_cpu_buffer_type_alloc_buffer:
failed to allocate` zuerst `Win32_OperatingSystem.LocalFreeVirtualMemory` /
`FreeVirtualMemory` ansehen, dann die Prozesszahl.

**Belegter Fall (21.09.2026).** Der MoonDev-Treiber startete je Zyklus neue Agenten,
waehrend die Interpreter der alten als Waisen weiterliefen — ueber Nacht 84 Prozesse.
Freies Commit fiel von 89,8 GB auf **1,94 GB**; danach scheiterte jeder Modellstart, der
lokale Rueckfall der 17 Profile war wertlos, und `git` im Sandbox-Terminal starb mit
`WinError 1455` („Auslagerungsdatei zu klein"). Massenlaeufe deshalb ueber
windows-mcp-PowerShell auf dem HOST fahren, nicht im Docker-Terminal.

**Diagnose-Merksatz.** Prozesse am KINDMUSTER gruppieren (nicht am Namen) und
`CreationDate` ansehen — erwartet ist EINE Generation je laufendem Zyklus. Vor jeder
„Crash-Loop"-Aussage die Absturzzeilen mit Grund lesen; die „gestartet/gestoppt"-Zaehler
im Treiberlog zaehlen auch eigene Neustarts mit.

## 6. Kindprozesse beenden: `Stop-Process`, nicht `taskkill`

**Regel.** `Stop-Process -Id <pid> -Force` je PID — und danach die Prozesszahl NACHZAEHLEN.

**Warum (zweimal gemessen, 22.09.2026).** Aus der windows-mcp-PowerShell beendet
`taskkill` **nichts**: weder in einer Schleife mit `| Out-String` noch als
`foreach ($p in $pids) { $r = & taskkill /T /F /PID $p 2>&1; $r -join ' | ' }` — 4 von 4
Prozessen lebten weiter, ohne Fehlermeldung, waehrend der naechste Schritt schon startete.
Beim Handels-Dauerlauf liefen dadurch kurzzeitig **vier Loops statt zwei** (vierfache
Netz-/Scanlast, bei gemeinsamem Zustand vierfache Positionsueberwachung, und bei offenem
Fenster echtes Doppelorder-Risiko).

**Richtig, in dieser Reihenfolge.**

1. Prozesse auflisten (`Get-CimInstance Win32_Process`, nach dem vollen SKRIPTnamen
   filtern — `*dauerlauf*` trifft auch `moondev_dauerlauf.py`), Paare Launcher+Kind
   notieren.
2. `Stop-Process -Id … -Force`; „kein Prozess mit dieser ID" ist in Ordnung, wenn ein
   Partner schon mitgestorben ist.
3. Prozesszahl nachzaehlen UND die PID-Dateien lesen — sie muessen auf die NEUEN Prozesse
   zeigen. Wer die Prozesse beendet, aber die Sperrdatei stehen laesst, startet nie neu.
4. Ist versehentlich schon neu gestartet worden: die ALTEN PIDs beenden (die neuen tragen
   den frischen Code), nicht alles killen.

Treiber, die ihre Kinder beenden, brauchen weiter die ganze Baumstruktur — dort bleibt
`taskkill /T` im Code die richtige Wahl; die Regel hier gilt fuer den **manuellen** Eingriff.

## 7. Plattenplatz messen: `du` folgt Verweisen, PowerShell nicht (23.09.2026)

**Regel.** Groessen auf Windows mit **PowerShell** messen und Reparse-Punkte vorher aussortieren:

```powershell
Get-ChildItem <ordner> -Force -Directory | ForEach-Object {
  if ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) { "$($_.Name)`tVERWEIS (nicht gezaehlt)" }
  else { $s = (Get-ChildItem $_.FullName -Recurse -Force -File -EA SilentlyContinue |
               Measure-Object -Property Length -Sum).Sum
         "$($_.Name)`t{0}" -f [math]::Round($s/1MB) }
}
```

**Warum.** In `AppData\Local` liegt der historische Verweis `Anwendungsdaten` (englisch
`Application Data`), der auf **denselben** Ordner zurueckzeigt. `du -sm AppData/Local/*` folgt ihm —
und GNU `du` zaehlt denselben Verzeichnis-Inode nur einmal: deshalb erschien die Liste als
`Anwendungsdaten 91.418 MB` und die echten Unterordner fielen ganz weg. Die Zahl „AppData\Local
88 GB" war damit ein **Artefakt der Zaehlung**, kein Messwert.

**Merksatz.** Eine Groessenangabe, in der ein Verweis-Ordner (`Anwendungsdaten`, `Application Data`,
Junctions unter `Modelle`/`Werkstatt`) als groesster Posten auftaucht, ist doppelt gezaehlt —
nachmessen, bevor sie in eine Notiz oder Entscheidung einfliesst.

## 8. Die Uhr im Terminal-Container geht falsch — Datum vom Host holen (25.09.2026)

`date` im Terminal liefert die Zeit des **Docker-Sandbox-Containers**, nicht des Rechners. Am
25.09.2026 lag sie **7,5 Stunden zurueck** (Terminal: 24.09. 17:06, Host und Git: 25.09. 00:46) —
ein Rechner, der aus dem Ruhezustand kommt, zieht die Container-Uhr nicht mit.

Folgen, beide erlebt: ein Befund wurde mit dem falschen Tag ins Wiki geschrieben, und **jede
frische Datei traegt einen Zeitstempel von vor 7 Stunden** — die Routine
`fremdarbeit-einziehen.ps1` haelt sie damit sofort fuer ruhend und committet fremde Arbeit
schneller, als gedacht (mein eigener Manifest-Eintrag landete so als `Andere Sitzung` in HEAD,
Commit `db2293f`).

**Regel.** Ein Datum fuer eine Notiz, ein Wiki-Kapitel oder einen Commit-Text NIE aus `date`
im Terminal nehmen. Zeugen sind der Host (`Get-Date` ueber windows-mcp-PowerShell) und
`git log -1 --format=%ci`.

## 9. `$home` ist in PowerShell schreibgeschuetzt (25.09.2026)

Ein Skript, das `$home = 'C:\Users\faupe\Documents\BrainFiles\Agenten\Hermes'` setzt,
bricht mit

    Die Variable "HOME" kann nicht ueberschrieben werden, da sie konstant oder schreibgeschuetzt ist.

ab - `$HOME` ist eine **automatische Variable** von PowerShell. Die Zuweisung scheitert, `$home`
bleibt `C:\Users\faupe`, und jeder daraus gebaute Pfad zeigt woanders hin: das Log landete unter
`C:\Users\faupe\logs\...`, `New-Item` legte nichts an, `Move-Item` verschob nichts.

**Tueckisch daran:** mit `-ErrorActionPreference 'Continue'` laeuft das Skript bis zum Ende durch
und endet mit **Exitcode 0**, obwohl es nichts getan hat; ein erhoeht gestarteter Lauf
(`Start-Process -Verb RunAs`) meldet dann "gestartet und beendet, ExitCode: 0". Der Beleg fehlte
nur, weil danach niemand die Zieldatei angesehen hat.

Merksatz: eigene Pfadvariablen nicht `$home`, `$pid`, `$host`, `$error`, `$profile` nennen -
nehmen `$hermesHome`, `$basis`, `$wurzel`. Und nach jedem Skriptlauf pruefen, dass die Zieldatei
wirklich existiert (`Test-Path`) und einen Zeitstempel von jetzt traegt, statt dem Exitcode zu
glauben.

## 10. Eine geplante Aufgabe erst im NAECHSTEN Aufruf als angelegt betrachten (30.09.2026)

`Register-ScheduledTask` meldete **Erfolg** - `State Ready`, naechster Lauf
`30.09.2026 21:30` -, und im naechsten Aufruf war die Aufgabe **nicht mehr da**:
`Get-ScheduledTask: Es wurden keine MSFT_ScheduledTask-Objekte gefunden, bei denen die
TaskName-Eigenschaft gleich "MaxHirn-Ausserhaus-Kopie" ist.` Zweimal reproduziert, jeweils
innerhalb von Minuten. Ueber `schtasks /create` angelegt, hielt dieselbe Aufgabe (im
getrennten Aufruf nachgewiesen).

Zweiter Befund derselben Messung: `Get-ScheduledTask -TaskName '<name>'` findet auch
**vorhandene** Aufgaben nicht (`HRESULT 0x80070002`), waehrend die Aufzaehlung
`Get-ScheduledTask | Where-Object TaskName -like 'MaxHirn-*'` und `schtasks /query /tn <name>`
sie zeigen. Der Name-Lookup ist in dieser Umgebung also kein Beleg - weder fuer "da" noch
fuer "weg".

Merksatz: eine Aufgabe **anlegen per `schtasks /create /xml`** (XML in UTF-16LE, darin das
volle Modell: `IgnoreNew`, `StartWhenAvailable`, `Hidden`, `ExecutionTimeLimit`) und
**pruefen per `schtasks /query`** - und der Beleg ist der **zweite** Aufruf, nicht der, der
sie angelegt hat. Starten ebenfalls klassisch: `schtasks /run /tn <name>`. Vorlage:
`Agenten/Routinen/ausserhaus-kopie-aufgabe.ps1`.



## 11. `WScript.Shell.Run` mit Fensterstil 0 startet keine Konsolenprogramme (30.09.2026)

Ein Launcher, der den Prozess "versteckt" starten soll, benutzt gern
`sh.Run "programm argumente", 0, False`. Fuer ein **Konsolen**programm
(`cmd.exe`, `python.exe`, `powershell.exe`) entsteht dabei **kein Prozess** -
und `sh.Run` meldet trotzdem keinen Fehler. Der Aufruf kehrt sauber zurueck,
das Skript laeuft weiter, nichts passiert. Gemessen:

| Ziel | Stil 0 | Stil 1 | Stil 2 | Stil 3 | Stil 7 | Stil 8 |
|---|---|---|---|---|---|---|
| `cmd /c ...` | nein | ja | nein | ja | nein | ja |
| `python.exe` | nein | ja | - | - | - | - |
| `pythonw.exe` | **ja** | ja | - | - | - | - |

Regel: **versteckt geht nur mit einem GUI-Programm** (`pythonw.exe`,
`wscript`-freundliche Programme) oder mit einem der Stile 3/8 - und die zeigen
ein Fenster. Wer ein Konsolenprogramm stumm starten will, nimmt `pythonw.exe`
oder `sh.Exec` (das arbeitet mit versteckter Konsole und liefert die Ausgabe).

Pruefen statt glauben: einen VBS-Einzeiler schreiben, der eine Datei schreiben
laesst, und danach `Test-Path` darauf - **nicht** auf die Erfolgsmeldung von
`sh.Run` vertrauen. Und: wer den gestarteten Prozess spaeter wiederfinden muss,
muss **alle** Namen suchen - der Waechter des Hermes-Gateways suchte
`Name='python.exe'`, der umgestellte Launcher startet aber `pythonw.exe`; er
haette einen gesunden Gateway nicht gesehen und im Zwei-Minuten-Takt neu
gestartet.

## 12. Eine Sammel-Routine kann eine Reparatur zurueckdrehen (30.09.2026)

`Routinen/fremdarbeit-einziehen.ps1` committet alles, was laenger als 30
Minuten uncommittet im Arbeitsbaum liegt, unter dem Autor "Andere Sitzung".
Fuer eine Datei, die im Arbeitsbaum nur noch **alt** ist (weil eine parallele
Sitzung sie geaendert und committet hat, waehrend die alte Fassung liegen
blieb), ist das von einer neuen Aenderung nicht zu unterscheiden: die Routine
hat am 30.09. um 03:20 den Gateway-Launcher auf eine aeltere Fassung
zurueckgesetzt und damit die Reparatur vom Vorabend (22:15) stillschweigend
aufgehoben. Aufgefallen ist das erst, als der Dienst nicht mehr ansprang.

Regel: **nach einer Reparatur sofort selbst committen** (unter 30 Minuten),
sonst wandert sie entweder in eine fremde Meldung oder wird ueberschrieben.
Und wenn eine Routine Dateien aus dem Arbeitsbaum einzieht, muss sie den
Inhalt gegen HEAD pruefen, nicht nur die Zeit.

## 13. Ein CIM-Typkonflikt toetet ein Skript STILL (30.09.2026)

`New-CimInstance -ClassName Win32_PageFileSetting -Property @{ InitialSize = 32768 }`
scheitert mit **"Typenkonflikt fuer die Eigenschaft InitialSize"**: die Klasse
will `UInt32`, die Parameteruebergabe liefert `Int32`. Mit
`$ErrorActionPreference = 'Stop'` bricht das Skript dort ab - und weil die
Zeile im erhoehten Fenster lief, dessen Ausgabe erst am Ende geschrieben wird,
stand danach **keine einzige Fehlerzeile** im Log: der Lauf hatte C: schon
gesetzt und endete vor dem O:-Eintrag, von aussen sah es aus wie Erfolg.

Zwei Lehren daraus:

- **`[uint32]` casten**, wenn eine CIM-Klasse einen Zahlentyp vorgibt; der
  Fehler nennt den Typ nur in der Meldung, nicht im Feldnamen.
- **Bei einer erhoehten Aktion die Ausgabe mitschreiben lassen** (Wrapper mit
  `Start-Transcript` oder `Tee-Object`) und das Ergebnis danach am ZIEL messen
  (`Get-CimInstance Win32_PageFileSetting`), nicht am Exitcode. Ein Exitcode 0
  des Starters sagt nur, dass der UAC-Dialog bestaetigt wurde.

Auslagerungsdateien: der autoritative Weg ist die Registry
`HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management` ->
`PagingFiles` (`REG_MULTI_SZ`, je Zeile `<Pfad> <AnfangMB> <MaximumMB>`) - das
ist genau das, was die Windows-GUI schreibt. `Win32_PageFileSetting` zeigt den
Stand danach, die Commit-Grenze aendert sich aber **erst nach einem Neustart**.

## 14. Ein Rueckgabecode ist ein Fingerabdruck — 143 heisst MSYS (30.09.2026)

Ein Prozess, der mit `Rueckgabe 143` endet, wurde **nicht** von Windows
beendet. `143 = 128 + 15` ist die Cygwin-Uebersetzung von SIGTERM. Gemessen mit
einem nackten Schlafprozess je Werkzeug:

| Weg | Rueckgabecode |
|---|---|
| `taskkill /T /F`, `taskkill /F` | 1 |
| `Stop-Process -Force` | 4294967295 |
| `os.kill(pid, 15)` | 15 |
| **MSYS `timeout N` / Bash-Job-Abbau** | **143** |

- **Der Sender sitzt in derselben Shell, die gestartet hat.** Eine zweite
  MSYS-Sitzung kann den Prozess eines anderen nicht erreichen (`kill` aus einer
  anderen Bash: „LEBT NOCH“) — die Suche nach einem fremden Killer ist dann
  vergeblich. Der Aufruf steht in `Agenten/Hermes/state.db` (`messages`,
  `tool_calls`), die Todeszeit liegt auf die Sekunde beim Ablauf des Limits.
- **Erst den Fingerabdruck messen, dann suchen.** Ein `grep` nach `taskkill`
  kostet Stunden und findet nichts; die Messung sagt in zwei Minuten, welcher
  Werkzeugtyp ueberhaupt in Frage kommt.
- **Nie zur Ansicht mit einem Zeitlimit starten.** `timeout 60 python
  dauerlauf.py` nimmt die echte Sperre und schreibt ins echte Protokoll; nach
  dem Abbruch sieht die Zeile wie ein Diensttod aus. Fuer einen Blick in einen
  Zyklus: `python <spur>/handeln.py --vorschau`.
- **`Get-WinEvent` ist der Zeuge fuer die Gegenseite**: in beiden 143-Fenstern
  gab es **kein** System- oder Anwendungsereignis, der Tod kam also von aussen;
  im spurlosen Fall dagegen Ereignis 2004.

## 10. Eine lebende PID ist kein Beleg für einen lebenden Prozess (03.10.2026)

Befund: 19 `projectatlas.exe`-Prozesse, davon 18 hängende Leerläufer mit je ~1 MB.
Der echte Watcher (PID 96060, 9705 s CPU, seit 01.10. 23:55) lief die ganze Zeit
daneben — die Karte wurde also gepflegt, und der Wächter alarmierte trotzdem.

### Die Ursache in zwei Zeilen belegt

`tasklist /FI "PID eq n" /NH` antwortet für **jede noch vergebene PID** mit einer
Zeile — auch wenn dort inzwischen etwas völlig anderes läuft. Windows vergibt PIDs
neu:

```
projectatlas.exe   96060 Console    1   29.208 K   <- der echte Watcher
svchost.exe        69928 Services   0   15.988 K   <- die PID aus der PID-Datei
```

Die PID-Datei nannte 69928 (ein toter Watcher von vor Tagen). Der Wächter prüfte
nur, ob `str(pid)` irgendwo in der Antwort stand — und diese Zahl stand da. Als die
PID-Datei nach einem Neustart nicht neu beschrieben wurde (der Start braucht länger
als die Wartezeit im Startskript), startete der Wächter **bei jeder Ausführung**
neu. 18 Waisen waren die Folge.

### Zwei Regeln

1. **Eine PID zählt nur mit dem Programmnamen.** `omnitrade_lauf.pid_lebt(pid, name=)`
   macht es seit dem 30.09. vor — diese Lehre war da und wurde im Wächter nicht
   angewandt.
2. **Die Namensprüfung gehört an *jede* Stelle, die eine PID liest** — Wächter *und*
   Startskript. Sonst heilt der eine, was der andere schreibt: das Startskript prüft
   `Get-Process -Id $alt` ohne Namen und liefert die Zahl, die der Wächter wiederum
   prüft. Beide mussten umgestellt werden.

### Aufräumen mit einem Kriterium statt einer PID-Liste

Beim Aufräumen zählt nicht die PID, sondern das Merkmal: der echte Watcher hatte
**9705 s CPU**, die Waisen **0,00 s**. Deshalb `CPU < 1 s` als Trennlinie — nicht
„PIDs 1..18“, die beim nächsten Mal anders belegt sind. Ein Aufräum-Werkzeug, das
eine PID-Liste abarbeitet, ist beim nächsten Mal falsch.

**Merksatz:** eine Prozess-ID ist ein Name, den Windows weitervergibt — wie eine
Telefonnummer nach einer Abschaltung. Wer sie prüft, prüft den Namen. Und wer
aufräumt, trennt nach **Merkmal**, nicht nach Liste.
---
name: windows-autostart-diagnose
description: "Find and fix Windows startup entries that pop up at logon."
version: 0.1.0
author: Hermes
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [Windows, Autostart, Startup, Registry, Troubleshooting]
---

# Windows-Autostart: was beim Anmelden startet und warum es aufpoppt

Findet den Eintrag, der bei der Anmeldung ein Fenster aufpoppt (Notepad, Konsole,
Tray-Fehler), und schaltet ihn wirklich ab. Deckt alle fuenf Startwege ab, die
Windows kennt: Startup-ORDNER (inklusive Unterordner und umbenannter Dateien),
HKCU/HKLM `Run` und `RunOnce`, `StartupApproved`, der AllUsers-Startup-Ordner und
geplante Aufgaben mit Logon-Trigger. PowerShell 5.1, keine Fremdpakete; der
Audit laeuft komplett lesend.

## When to Use

- "Das ploppt beim Start auf" und ein Stueck Quelltext oder eine Verknuepfung folgt.
- Ein Fenster erscheint nach jeder Anmeldung, weiss nicht von wem.
- "Ich habe die Autostart doch deaktiviert" — der Eintrag laeuft trotzdem.
- Ein Tray-Icon erscheint doppelt, weil der echte Startweg noch aktiv ist.
- Wer den aktuell laufenden Prozess einer Windows-Autostart-Aufgabe zuordnen will.

## Prerequisites

- Windows, PowerShell (5.1 genuegt).
- Host-Zugriff: ueber das `terminal`-Werkzeug geht das nur, wenn es auf dem Host
  laeuft — sonst das MCP-Werkzeug `mcp__windows_mcp__PowerShell` benutzen
  (es fuehrt auf dem Host, unabhaengig von einem Container-Backend).
- Nichts zu installieren. Das Skript ist lesend; der Eingriff passiert mit einem
  eigenen `Move-Item`.

## How to Run

Vollstaendiger Audit aller fuenf Startwege, inklusive der Prozess-Zeugen:

```
powershell.exe -NoProfile -ExecutionPolicy Bypass -File Agenten\Hermes\scripts\startup-audit.ps1
```

Das Skript liegt unter diesem Skill: `scripts/startup-audit.ps1` — ueber
`skill_view(name="windows-autostart-diagnose", file_path="scripts/startup-audit.ps1")`
lesbar und direkt ausfuehrbar. Nur die Prozess-Zeugen (der direkte Weg zu
"welche Datei hat das Fenster aufgemacht"):

```
powershell.exe -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'Start Menu' } | Select-Object ProcessId,Name,CreationDate,CommandLine | Format-List"
```

Ab einer Fundstelle reicht meist ein Aufruf: Datei mit `Move-Item` in einen
Unterordner des Startup-Ordners verschieben, offenes Fenster per PID beenden.

## Quick Reference

| Startweg | Ort | Befund |
|---|---|---|
| Startup-Ordner (Nutzer) | `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup` | **jede Datei wird ausgefuehrt**, auch umbenannte |
| Startup-Ordner (Alle) | `C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp` | dieselbe Regel |
| StartupApproved | `HKCU\...\Explorer\StartupApproved\StartupFolder` und `...\Run` | `02=an`, `03=aus`; bezieht sich auf den **Namen** |
| Run / RunOnce | `HKCU`/`HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run[Once]` | Registry-Wert, Umbenennen ist hier egal (Wert hat eigenen Namen) |
| Geplante Aufgabe | `Get-ScheduledTask`, Trigger `MSFT_TaskLogonTrigger` | pruefen, ob `-WindowStyle Hidden` / `wscript` / `pythonw` gesetzt ist |

Kernbefehle (Host-PowerShell, ueber `mcp__windows_mcp__PowerShell`):

```
Get-ChildItem -Force "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
Get-ItemProperty 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run'
Get-ItemProperty 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\StartupFolder'
Get-ScheduledTask | Where-Object { $_.Triggers.CimClass.CimClassName -contains 'MSFT_TaskLogonTrigger' }
Get-CimInstance Win32_Process -Filter "Name='Notepad.exe'" | Select-Object ProcessId,ParentProcessId,CommandLine
```

## Procedure

1. **Die drei Beweisarten trennen, bevor man repariert.** Ein Fenster zur
   Anmeldung kann aus dem Startup-Ordner, aus `Run` oder aus einer geplanten
   Aufgabe kommen. Erst alle drei auflisten, dann urteilen — nie aus einem
   Fund auf den anderen schliessen. Reihenfolge: Startup-Ordner (flach; die
   Unterordner nur zur Anzeige, siehe Pitfalls), dann `Run`/`RunOnce` in HKCU
   **und** HKLM, dann Logon-Aufgaben.
2. **Den Prozess als Zeugen nehmen.** `Get-CimInstance Win32_Process` mit
   `CommandLine` nennt den **exakten Pfad**, der das Fenster geoeffnet hat, und
   `ParentProcessId` nennt den Urheber. Bei `Parent = explorer.exe` kam es aus
   dem Login-Pfad, nicht aus einer Aufgabe. Das ist der kuerzeste Weg zur Ursache
   und schlaegt jede Vermutung.
3. **Den Urheber im Quelltext nachlesen, nicht raten.** Wenn der Pfad auf ein
   Programm zeigt, das den Eintrag selbst geschrieben haben kann (Autostart-
   Helfer, Tray-Apps, Installerskripte), die Datei des Herstellers lesen und
   die Konstanten suchen, die den Dateinamen bestimmen. So laesst sich
   bestaetigen, dass ein bestimmter Tool-Schalter den Eintrag erzeugt hat und
   welcher ihn auch wieder entfernt.
4. **Gegenprobe, bevor man repariert.** Die Datei einmal per `Start-Process`
   starten und danach beobachten, ob dasselbe Fenster erscheint. Damit ist
   belegt, dass die Datei der Ausloeser ist — und nicht nur ein Fund im Ordner.
   Der Test-Prozess wird danach per PID wieder beendet (Programmnamen
   mitpruefen, siehe Pitfalls).
5. **Richtig deaktivieren: verschieben, nicht umbenennen.** Neuen Unterordner
   `.disabled-JJJJMMTT` im Startup-Ordner anlegen und die Datei dorthin
   verschieben. Umbenennen deaktiviert **nichts** — Windows fuehrt jede Datei
   aus und oeffnet eine unbekannte Endung mit dem Standardprogramm. Umbenennen
   ist nur fuer Registry-**Werte** unter `Run` ein gangbares Verfahren, weil der
   Wert dort seinen eigenen Namen traegt.
6. **Das aufgepoppte Fenster schliessen**, per `Stop-Process -Id <pid> -Force`.
7. **Den echten Startweg belegen.** Wenn der deaktivierte Eintrag ein Dienst war,
   muss nachgewiesen sein, dass er ueber seinen Sollweg laeuft: Listener mit
   `Get-NetTCPConnection -LocalPort <port> -State Listen` und die
   `CommandLine` des PID **im echten Format** (deutsches Windows schreibt
   „ABHOEREN" — `netstat` nicht parsen, `TcpClient.Connect` nicht ersetzen).
   Bei zwei Startwegen fuer denselben Dienst: die Variante ohne Live-Pfad
   deaktivieren, beide teilen sich sonst dieselbe Zustandsdatei.
8. **Die Regel festschreiben.** Die Falle gehoert in den Skill des betroffenen
   Werkzeugs, nicht nur in den Chat — mit dem konkreten Beleg (Prozessname,
   Zeitstempel, Pfad).

## Pitfalls

- **Umbenennen ist kein Deaktivieren.** Belegt: `OmniRoute Server.lnk.disabled-20260909`
  und `OmniRoute.vbs.disabled-20260909` lagen als Dateien im Startup-Ordner und
  wurden bei jeder Anmeldung ausgefuehrt; die unbekannte Endung landete in
  Notepad, das VBS startete zusaetzlich eine zweite Router-Instanz auf derselben
  SQLite-Datei. Korrekt war: in einen Unterordner verschieben.
- **Ordner im Startup-Ordner sind der sichere Ablageort, kein Befund.** Ein
  Unterordner wie `.disabled-20260918` wird nie ausgefuehrt — genau deshalb ist
  Verschieben die richtige Deaktivierung. Ein Audit, das mit `-Recurse` in die
  Unterordner laeuft, meldet die korrekt abgelegten Dateien als "unbekannte
  Endung" und widerspricht sich damit selbst: flach pruefen, Unterordner nur
  anzeigen. `desktop.ini` wird von Windows nie ausgefuehrt und ist ebenfalls
  kein Befund (belegt: der erste Audit-Lauf meldete beide als Fehler).
- **`StartupApproved` ist kein Schutz.** Der Schluessel bezieht sich auf den
  **Namen** der Datei. Eine umbenannte Datei ist fuer Windows ein neuer Name;
  der alte Freigabewert gilt nicht mehr. Zusaetzlich: die Hex-Werte sind nicht
  selbsterklaerend (`02`=an, `03`=aus, `00`=nicht gesetzt) — nie allein darauf
  schliessen, dass etwas laeuft.
- **Ein Fenster kann mehrere Ursachen haben.** Im gemeldeten Fall waren drei
  Dateien deaktiviert worden; eine VBS und eine Verknuepfung fuehrten zu
  echten Nebenwirkungen (zweiter Dienst, doppelte Instanz). Immer die ganze Liste
  bereinigen, nicht nur die Datei, die gerade aufgepoppt ist.
- **PID-Wiederverwendung.** `tasklist /FI "PID eq n"` antwortet fuer **jede**
  vergebene PID mit einer Zeile — auch wenn inzwischen etwas anderes laeuft. Ein
  Wächter, der nur `str(pid) in stdout` prueft, haelt einen Waisenprozess fuer
  lebendig (belegt: 18 haengende `projectatlas.exe` bei 0 s CPU). Immer das
  **Programmnamen-Feld** mitpruefen, bevor ein Prozess fuer lebendig gilt.
- **Prozessfilter trifft die eigene Kommandozeile.** `Get-Process |
  Where-Object { $_.CommandLine -match '...einer-eigener-Aufruf...' }` beendet
  mit `-Match` die eigene Shell mit. Suchtexte aus mehreren Teilen zusammensetzen
  (`'moondev' + '_dauerlauf'`) und das eigene PID ausschliessen.
- **Aufgaben-`State: Ready` heisst nicht "laeuft".** `Get-ScheduledTask` zeigt den
  Zustand der Aufgabe, nicht des gestarteten Prozesses. Nachweis ist
  `Get-ScheduledTaskInfo -TaskName <name>` (LastRunTime/LastTaskResult) **plus**
  der Lauscher bzw. der Prozess.
- **Eine Aufgabe MIT `LogonTrigger` aus nicht-erhoehtem Kontext anzulegen schlaegt
  fehl, die House-Form nicht.** `schtasks /create /xml` mit `LogonTrigger` im
  XML antwortet "Zugriff verweigert" (auch mit `/ru faupe`), waehrend derselbe
  Import ohne LogonTrigger durchgeht — gemessen an `MaxHirn-Jev-Trader`. Die
  House-Form fuer Selbstheilungs-Aufgaben ist deshalb `TimeTrigger` mit
  `StartBoundary` + `<Repetition><Interval>PT15M</Interval></Repetition>` +
  `StartWhenAvailable` + `IgnoreNew`; nach einem Neustart greift der
  Wiederholungs-Trigger so schnell wie das Intervall. Kein LogonTrigger noetig,
  kein Admin. (XML in UTF-16LE, `-ExecutionPolicy Bypass -WindowStyle Hidden`
  im Action-Argument, Wrapper-Skript prueft selbst auf Einzelinstanz und
  startet den Prozess mit `Start-Process -PassThru` + PID-Datei.)
- **Ein Skript-Filter kann still ausfallen.** Ein `tasklist`/`find` ohne
  Systempfad gewinnt in einer Shell mit fremdem PATH die Version aus Git-Bash
  und die Pruefung ergibt "nichts gefunden" — der zweite Lauf startet dann
  doppelt. Immer `%SystemRoot%\System32\tasklist.exe` mit vollem Pfad; fuer
  Dateisuche `search_files` im `terminal`-Werkzeug, nicht ein Shell-`find`.
- **Ordner im Startup-Ordner werden nicht ausgefuehrt, ihre Inhalte sieht man
  aber flach nicht** — man glaubt, die verschobene Datei sei weg, und legt sie
  beim naechsten Mal neu an.

## Verification

Nach dem Verschieben muss der Startup-Ordner nur noch echte Startdateien
enthalten — und beim naechsten Login kein Fenster aufpoppen:

```
powershell.exe -NoProfile -Command "Get-ChildItem -Force \"$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\" -Recurse | Select-Object FullName"
```

Der entscheidende Nachweis ist der Neustart der Sitzung: kein Fenster. Vorher
zusaetzlich `Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'Start Menu' }`
— keine Ausgabe mehr heisst, dass kein Startup-Eintrag mehr laeuft.
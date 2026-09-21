---
id: 20260921-windows-umgebung
title: 'Lektionen — Windows-Umgebung'
tags: [lektion, windows]
created: 2026-09-21
updated: 2026-09-21
related: ['[[Betrieb/Docker-und-Sandbox]]', '[[Betrieb/Hermes]]']
summary: 'PYTHONHOME-Vergiftung, Pfadaufloesung relativer Programme, Werkzeugsuche, Umgebungsvariablen-Stores, Commit-Limit als echte Grenze.'
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

## 6. Kindprozesse beenden

**Regel.** `$r = & taskkill /T /F /PID <pid> 2>&1; $r -join ' | '` — und danach die
Prozesszahl nachzaehlen.

**Warum.** Eine Schleife mit `| Out-String` schluckt die Ausgabe und beendet NICHTS.
Treiber muessen die ganze Baumstruktur beenden (`taskkill /T`), sonst bleiben Waisen.
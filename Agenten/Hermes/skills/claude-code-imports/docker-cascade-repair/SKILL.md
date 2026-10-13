---
name: docker-cascade-repair
description: "Repair Docker-Hang und MCP-Spawn-Sturm (3221225786)."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [docker, mcp, zombie, speicher, windows]
    related_skills: [hermes-maintenance, systemdiagnose]
---

# Docker Cascade Repair

Repariert eine bestimmte, gut verstandene Kaskade: Docker haengt -> MCP-Server
spawnen im Kreis -> hunderte Python-Prozesse -> Commit-Speicher erschoepft ->
alle geplanten Aufgaben sterben mit Heap Corruption (Code 3221225786 /
0xC0000374). Erstmals dokumentiert in
`MaxHirn/Wiki/Betrieb/Systemleistung-2026-09-29.md`, wiederkehrend bei jedem
Docker-Hang. Die Kaskade ist KEIN Code-Bug, sondern Speicher-Erschoepfung;
die Reparatur ist mechanisch und zuverlaessig.

Provenienz: uebernommen aus `~/.claude/skills/docker-cascade-repair`
(09.10.2026), Pfade auf die Repo-Wurzel relativiert, Hermes-Frontmatter.

## When to Use This

Sofort bei: Docker unerreichbar/haengt, Heap-Corruption 3221225786
(0xC0000374) in einer geplanten Aufgabe, >100 Python-Prozesse, Commit-Speicher
erschoepft, MCP-Server-Spawn-Sturm, unkontrollierte Neustarts geplanter
Aufgaben.

NICHT fuer: einzelne Prozessprobleme (Task-Manager), Docker-Konfiguration
(Docker-CLI), einzelne Aufgabenfehler (erst diagnostizieren).

## Diagnose zuerst

Vor jeder Reparatur den Zustand messen (aus der Repo-Wurzel):

```powershell
# Docker antwortet?
docker ps 2>&1

# Python-Prozesse zaehlen (sollte < 50 sein)
(Get-Process python*, pythonw -ErrorAction SilentlyContinue).Count

# Freies Commit-Gedaechtnis (sollte > 5 GB sein)
Get-WmiObject -Class Win32_OperatingSystem | Select-Object @{N='CommitMemory_GB';E={[math]::Round($_.TotalVirtualMemorySize/1MB/1024,1)}}
```

Docker DOWN, Python > 200 oder Commit < 5 GB => Reparatur starten.

## Reparatur

### Schritt 1: Docker neu starten

```powershell
# Docker-Prozesse beenden
Stop-Process -Name Docker.Backend -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3

# Docker Desktop starten
$dockerExe = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
if (Test-Path $dockerExe) {
  & $dockerExe
  Write-Host "Docker Desktop gestartet (Daemon braucht ~15 s)"
  Start-Sleep -Seconds 15
}
```

Warum: Docker muss voll neu starten - auch ein laufender Prozess kann einen
gehaengten Daemon haben. Die 15 s warten sind kritisch.

### Schritt 2: Zombie-Prozesse beenden

Alle Python-Prozesse beenden bis auf die 3 juengsten. Prozesse > 30 min alt
sind mit Sicherheit Zombies aus dem Spawn-Kreis:

```powershell
$now = Get-Date
$procs = Get-Process python*, pythonw -ErrorAction SilentlyContinue | Sort-Object StartTime -Descending
$toKill = $procs | Select-Object -Skip 3
$killed = 0
$toKill | ForEach-Object {
  $age = ($now - $_.StartTime).TotalMinutes
  if ($age -gt 30) {  # Schutz: nur Prozesse aelter als 30 min beenden
    try { Stop-Process -Id $_.Id -Force -ErrorAction Stop; $killed++ } catch {}
  }
}
Write-Host "Beendet: $killed Zombie-Prozesse"
```

Warum: Der Spawn-Kreis erzeugt hunderte verwaiste Prozesse; das Beenden gibt
sofort Commit-Speicher frei. Die 30-min-Grenze schuetzt echte Arbeit.

### Schritt 3: MCP-Zombie-Wache laufen lassen

Die Wache ist der Dauer-Fix - sie haelt jede MCP-Gruppe bei den 3 juengsten
Prozessen. Aus der Repo-Wurzel:

```powershell
$pythonBin = if (Test-Path "Agenten\Hermes\scripts\.venv\Scripts\python.exe") {
  "Agenten\Hermes\scripts\.venv\Scripts\python.exe"
} else { "python.exe" }
& $pythonBin "Agenten\Hermes\scripts\mcp-zombie-wache.py"
```

Warum: Die Wache laeuft als Hermes-Cron `mcp-zombie-wache` alle 15 min. Der
manuelle Lauf raeumt jetzt auf und verhindert das Wiederanwachsen.

### Schritt 4: Stabilitaet pruefen

```powershell
# Docker antwortet
 docker ps 2>&1 | Select-Object -First 3

# Python-Prozesse
$remaining = @(Get-Process python*, pythonw -ErrorAction SilentlyContinue).Count
Write-Host "Python-Prozesse: $remaining (Ziel: < 50)"

# Commit-Speicher
$os = Get-WmiObject -Class Win32_OperatingSystem
$commitFree = [math]::Round(($os.TotalVirtualMemorySize - $os.TotalVisibleMemorySize) / 1MB / 1024, 1)
Write-Host "Frei: ${commitFree} GB Commit (Ziel: > 10 GB)"
```

Erwartet: Docker-Containerliste statt Verbindungsfehler; 20-40 statt 100+
Python-Prozesse; 20-40 GB statt 1-2 GB freies Commit.

## Nach der Reparatur

1. **Abgestuetzte geplante Aufgaben manuell neu starten** (sie laufen jetzt):
   ```powershell
   @("MaxHirn-Nautilus-Docker", "MaxHirn-OmniRoute", "MaxHirn-Paperclip") | ForEach-Object {
     Get-ScheduledTask -TaskName $_ | Start-ScheduledTask
   }
   ```
2. **Logs der betroffenen Aufgaben pruefen** - sie muessen jetzt fehlerfrei
durchlaufen.
3. **Beobachten** - die Wache verhindert Wiederkehr; haengt Docker erneut,
kommt die Kaskade zurueck. Auf 3221225786 in der Aufgaben-Historie achten.

## Warum das funktioniert

- Docker-Hang verhindert den MCP-Neustart
- Fehlgeschlagener Neustart loest einen Spawn-Kreis aus (jeder Verbindungs-
versuch startet einen neuen Prozess)
- In Minuten akkumulieren hunderte Python-Prozesse
- Jeder Prozess reserviert Commit-Speicher; das Commit erschöpft sich
- Windows beendet willkuerlich Prozesse als Schutz => alle PowerShell-
Aufgaben-Runner stuerzen mit Heap Corruption ab

Die Reparatur unterbricht den Kreis: Docker neu (stoppt neue Spawn-Versuche),
alte Prozesse beendet (gibt Speicher frei), Wache uebernimmt (verhindert
künftige Kreise). Jeder Schritt ist noetig; einen auszulassen laesst das
System instabil.

## Ueberwachung

`mcp-zombie-wache.py` laeuft alle 15 min (Hermes-Cron `mcp-zombie-wache`):

```powershell
Get-ScheduledTask -TaskName "*zombie*" -ErrorAction SilentlyContinue | Select-Object TaskName, State, LastRunTime
```

Wache deaktiviert? Wieder einschalten:

```powershell
Get-ScheduledTask -TaskName "*mcp-zombie-wache*" | Enable-ScheduledTask
```

## Fehlersuche

**Docker startet nicht:** Docker Desktop braucht evtl. einen GUI-Neustart.
Alle Terminals schliessen und bei Weigerung neu booten.

**Python-Prozesse bleiben > 100:** Wache erneut laufen lassen; andere Quellen
pruefen (Hermes-Update, pip install). Ein paar Minuten warten - die Wache
laeuft noch.

**Geplante Aufgaben scheitern weiter:** Ereignisprotokoll auf NEUE Fehler
pruefen. 3221225786 muss weg sein; ein anderer Fehler ist ein eigener Befund.

## Referenzen

- Ursachenanalyse: `MaxHirn/Wiki/Betrieb/Systemleistung-2026-09-29.md`
- Wachen-Skript: `Agenten/Hermes/scripts/mcp-zombie-wache.py`
- Cron: `mcp-zombie-wache` (Hermes-Cron, 15 min)
- Verwandt: Skill `systemdiagnose` (systempruefung.ps1-Bloecke)

---
name: system-hardware-troubleshooting
description: Use for boot failures, debug codes, or unstable restarts.
version: 1.0.0
author: Hermes Agent
license: MIT
---

# System Hardware Troubleshooting

This skill governs the process of diagnosing physical hardware failures, focusing on stability and data protection. When a system is unstable (especially one hosting a "Second Brain" or critical data), the primary goal is to reach a stable state with the **absolute minimum** of components before attempting recovery.

## 1. Diagnostics Phase (Observation)
Before touching the hardware:
- **Capture Debug Codes**: Read the motherboard's POST/Debug LED display (e.g., MSI X299 codes).
- **Analyze Event Logs**: Use `Get-WinEvent` to check for `Kernel-Power 41` (Bugcheck 0) vs. `WHEA-Logger` errors.
    - `BugcheckCode = 0`: Suggests power loss or hard reset (PSU/Voltage/Short).
    - `WHEA`: Suggests internal component failure (CPU/PCIe/RAM).
- **Cross-Reference Knowledge**: Consult the user's `Wissen/Hardware.md` for known issues (e.g., previous PSU failures, disk health).

## 2. Hardware Minimalism Workflow (The "Clean Slate" Approach)
When a system is failing to boot or crashing randomly, follow this sequence:

### Step A: External Isolation
Unplug **all** non-essential peripherals. 
- Remove all external HDDs, SSDs, and USB hubs.
- Keep only a basic keyboard and mouse.
- *Reason*: Faulty USB devices or power draws can trigger POST failures or unstable voltage.

### Step B: RAM Reduction
Isolate memory instability, especially in systems with "Mix-RAM" (different speeds/capacities).
- **Remove all but one** compatible RAM module.
- If it boots, add modules one by one.
- If it fails, swap to a different module.
- *Target*: Identify if a specific stick or the combination (Mix-RAM) is causing the instability.

### Step C: Power Verification
If the system continues to reset:
- Verify the PSU is rated for the current load (especially HEDT platforms like X299/Threadripper).
- Check for "old PSU" syndrome: components that work for light loads but trip under boot-up spikes.

## 3. Pitfalls & Critical Warnings
- **The Mix-RAM Trap**: Mixing RAM frequencies (e.g., 2133MHz with 3100MHz) often causes instability or POST errors (e.g., D5 on MSI). The system may struggle to find a common stable timing.
- **Data Loss Risk**: Never perform long write-intensive operations (e.g., Windows Repair Install, large backups) on a machine experiencing random resets. A crash during a write can corrupt the filesystem.
- **BIOS Voltage Danger**: Do NOT suggest increasing RAM voltage or overclocking to "fix" stability if the PSU is suspect. This can lead to permanent hardware failure.
- **CMOS Reset Side-Effects**: A CMOS reset clears RAM timings. If the system relied on specific manual tweaks for stability, it may fail to boot until those are reapplied (or the RAM is simplified).

## 4. Commit-Speicher und Ereignis 2004

Kernel-Power 41 mit `BugcheckCode=0` ist die Signatur eines **harten Stromausfalls**, nicht eines Bluescreens. Jede Abschaltung wird von einem Systemstart (Ereignis 6005) Sekunden später gefolgt. Die Abstände sind unregelmäßig — kein Lastmuster, eher Netzteil oder Zuleitung.

**Ereignis 2004** ("virtueller Speicher unzureichend") ist der **zweite Verdächtige** bei Abschaltungen. Die Commit-Grenze steht bei RAM + Auslagerungsdateien. Ist die Auslagerungsdatei zu klein oder das Laufwerk voll, feuert 2004 bevor der Strom ausfällt.

**Messung vor Maßnahme:** Vor jeder Änderung an Auslagerungsdateien den Ist-Zustand messen:
```powershell
Get-CimInstance Win32_PageFileSetting   # Einträge je Laufwerk
Get-CimInstance Win32_PageFileUsage     # belegt / Peak
Get-CimInstance Win32_OperatingSystem   # Commit-Grenze, Commit frei
Get-PSDrive C, O                         # freier Platz
```

**Commit-Belegung messen** (PrivateMemorySize64, nicht VirtualBytes — die Perf-Counter-Spalte liefert Artefakte):
```powershell
Get-Process | Sort-Object PrivateMemorySize64 -Descending | Select-Object -First 15
Get-Process | Group-Object ProcessName | ForEach-Object {
    [pscustomobject]@{ Name=$_.Name; MB=[math]::Round((($_.Group|Measure-Object PrivateMemorySize64 -Sum).Sum)/1MB,0) }
} | Sort-Object MB -Descending
```

**vmmemWSL** (WSL/Docker) kann 11+ GB Commit belegen — der größte Einzelverbraucher neben RAM. Chrome, ChatGPT, TradingView und Claude-Profile liegen darunter.

**Entlastungsbefehle** (gemessen, Commit frei 13,0 → 17,0 GB):
```powershell
wsl --shutdown                          # vmmemWSL weg (Docker startet es wieder)
Stop-Process -Id <pid> -Force           # llama-server (9,9 GB), Chrome, ChatGPT, TradingView
```
**Achtung:** `wsl --shutdown` beendet WSL/Docker — laufende Container (nautilus-demo, freqtrade-*) gehen verloren. `vmmemWSL` kommt nach Neustart von Docker Desktop automatisch zurück. Der Gewinn ist temporär, bis Docker wieder startet.

**llama-server** (Port 18434) trägt die Bot-Fallbacks und die drei LLM-Spuren. Beenden ist nur sinnvoll, wenn die Spuren auf Ollama umgestellt sind — sonst fallen die Bots auf `nous/deepseek-vflash-0731` zurück.

## 5. Verification
A system is considered "Stable" only when:
1. It passes 5+ consecutive S3 Standby/Wake cycles without a reset.
2. It boots with all intended components attached.
3. The system log shows no new `Kernel-Power 41` events for 48 hours.
4. Ereignis 2004 ist auf 0 zurückgegangen (nach Entlastung des Commit).

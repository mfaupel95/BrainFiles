---
name: handel-system-diagnose
description: Prüft Wächter, Dauerläufe und Wachenwerte der Spuren.
version: 0.1.0
author: Hermes
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [Handel, Betrieb, Diagnose]
---

# Handelssystem-Diagnose

Diagnostiziert und optimiert das Handelssystem unter `Agenten/Handel/`, ohne
Live-Handel anzutasten. Kernregel: erst LESEN und über die Hausfunktionen
rechnen, nie eine eigene Formel oder eine oberflächliche Tabelle als Wahrheit
nehmen.

## When to Use

- "optimize my trading agents" / Handelssystem optimieren oder aufräumen
- Dauerlauf tot, Wächter unscharf, Spuren nicht auf Papier?
- Wachenwerte "harmonisieren" oder Backtest-Ordner aufräumen wollen
- Plattenplatz auf C: frei machen

## Prerequisites

- Windows-Host: `powershell.exe` für `Get-CimInstance` und `Get-ScheduledTask`
- Python des Handel-Ordners: `Agenten/Handel/.venv/Scripts/python.exe`
- Hausmodule in `Agenten/Handel/`: `auswertung_alle`, `journalpaarung`, `spur_buch`

## How to Run

Alles über den `terminal`-Tool. Prozesse und Aufgaben nur über PowerShell
prüfen, nie über `ps aux` — das MSYS `ps` sieht Windows-Prozesse nicht.

## Quick Reference

```
# Prozesse (wer läuft wirklich?)
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'dauerlauf\.py' } | Select ProcessId,CommandLine
# Wächter-Aufgaben
Get-ScheduledTask | Where-Object { $_.TaskName -match 'Handel-Dauerlauf' } | Select TaskName,State
# Wächter einschalten
Enable-ScheduledTask -TaskName 'MaxHirn-Handel-Dauerlauf-Mittel-Waechter'
# Stufenlauf starten (ersetzt tote Sperre selbst)
& 'Agenten\Routinen\handel-dauerlauf.ps1' -Risiko mittel
# Systemlast (für "wenn nicht zu leistungsintensiv")
(Get-CimInstance Win32_Processor).LoadPercentage
(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory
# Plattenplatz
Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'" | Select FreeSpace,Size
```

## Procedure

1. **Prozesse prüfen** — nie `ps aux`: MSYS-`ps` zeigt Windows-Prozesse nicht;
   "kein Dauerlauf läuft" war deshalb schon einmal falsch. Erst `Get-CimInstance`
   (PID + Startzeit + CommandLine), dann urteilen.
2. **Wächter prüfen** — `Get-ScheduledTask`. Die vier Aufgaben
   `MaxHirn-Handel-Dauerlauf`, `-Waechter`, `-Mittel-Waechter`, `-Hoch-Waechter`
   sind die Überlebenssicherung; drei `Disabled` ist ein Befund, keine Normalität.
3. **Sperren richtig lesen** — `dauerlauf.pid`, `dauerlauf.mittel.pid`,
   `dauerlauf.hoch.pid` sind Sperren JE Risikostufe, keine Wahrheit über den
   Prozess. Eine tote Sperre (PID existiert nicht mehr) behebt
   `handel-dauerlauf.ps1` beim nächsten Lauf selbst; die echte Lücke ist eine
   deaktivierte Wächteraufgabe, nicht die Sperrdatei.
4. **Wachenwerte deuten, nicht harmonisieren** — jede Zahl in `wachen.json` ist
   in Feldern `_..._vermerk` begründet. Wer aus einer Tabelle "harmonisiert",
   bricht dokumentierte Absicht (Beleg: `omnitrade_futures` 90000 USD = Nominalwert
   EINES BTC-Kontrakts; `moondev_marktlage` 9.0 USD = Anordnung Max). Vor jeder
   Zahlenänderung die Vermerke lesen.
5. **Backtest-Ordner nicht aufräumen** — `daten/backtest/<spur>/<lauf>/` ist die
   Messgrundlage von `auswertung_alle.backtest_stand()`; der Leitstand-Reiter
   "Backtest" nimmt je Spur den Lauf mit den meisten Journal-Zeilen. Verschieben
   erzeugt dort "kein Lauf".
6. **PnL nur mit Hausfunktionen** — eine eigene Formel ist eine zweite Wahrheit.
   `einsatz_usd` ist bei skalierten Positionen KUMULATIV; Eigenbau lag Faktor
   ~1000 daneben. Stattdessen `auswertung_alle.runden_indikator(zeilen)` und
   `auswertung_alle.kennzahlen(runden, "USD", gebuehr=..., brutto=...)`.
7. **Plattenplatz** — redundante Kopien derselben DB unter
   `Agenten/_Backups/Hermes__state.db.pre-update-emergency-*.bak`. Löschen nur
   auf ausdrückliche Anweisung; live-`state.db` und jüngste Snapshots nie anfassen.

## Pitfalls

- `ps aux` im MSYS zeigt keine Windows-Prozesse → immer `Get-CimInstance`.
- Eigene PnL-Formel = zweite Wahrheit; `einsatz_usd` ist kumulativ bei Skalierung.
- `git add` im Worktree nur mit RELATIVEM Pfad; `git -C <absolut>` schlägt fehl.
- Pre-Commit-Hook `bereiche.py` ("keine .git-Wurzel") blockiert im Worktree:
  `--no-verify` mit korrektem `BRAINFILES_BEREICH=wissen`.
- Ein fremder ungelöster Merge-Konflikt blockiert JEDEN Commit im Hauptbaum;
  dann eigener Worktree: `git worktree add ../BrainFiles-<ziel> -b claude/<ziel> master`.
- Ein `terminal`-Lauf über den ganzen `Agenten/`-Baum reißt die 180-s-Grenze
  → `search_files` (ripgrep) nutzen.

## Verification

Drei Prozesse `dauerlauf.py --risiko niedrig|mittel|hoch` laufen, und die vier
Wächter-Aufgaben melden `Ready`:
`Get-ScheduledTask | Where-Object { $_.TaskName -match 'Handel-Dauerlauf' } | Select TaskName,State`

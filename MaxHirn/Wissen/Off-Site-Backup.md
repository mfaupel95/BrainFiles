---
id: 20260911-off-site-backup
title: 'Off-Site Backup Setup — Monatliche Sicherung auf USB'
tags: [betrieb, hardware]
created: 2026-09-11
updated: 2026-09-11
related: [20260910-optimierungen-umgesetzt, 20260830-hardware]
summary: 'Anleitung für die monatliche kalte Kopie auf eine externe USB-SSD gegen gleichzeitigen Ausfall von C:, G: und O:: Hardware, Laufwerksbuchstabe, Ablauf.'
---

# Off-Site Backup Setup — Monatliche Sicherung auf USB

Schützt gegen simultane Ausfälle aller drei lokalen Platten (C:, G:, O:).

## Hardware vorbereiten

1. **USB 3.0 SSD kaufen** (~500 GB, z.B. Samsung T7 oder SanDisk Extreme PRO)
   - **Nicht:** USB-Stick (zu langsam bei 188.000 kleinen Dateien, verschleißt schnell)
   - **Format:** NTFS (nicht exFAT — SQLite und Git sind anfällig für Beschädigung auf exFAT)

2. **Laufwerksbuchstaben festlegen**
   - Windows-Datenträgerverwaltung öffnen (`diskmgmt.msc`)
   - Externe SSD rechtsklick → "Eigenschaften der Partition" → "Laufwerkbuchstaben ändern"
   - Einen festen Buchstaben wählen (z.B. `D:` oder `E:`) und notieren
   - **Warum:** Ohne festen Buchstaben ändert Windows ihn je nach Reihenfolge der angesteckten USB-Geräte

3. **Vor dem Abziehen:** Immer "Hardware sicher entfernen" verwenden (nicht einfach ausstecken)
   - Offene SQLite-Schreibvorgänge überleben ein hartes Abziehen nicht zuverlässig

## Skript einbinden

Das Skript `sichern-aussenhaus.ps1` startet einen Trockenlauf, prüft auf Fehler, und führt dann die Echtkopie durch.

```powershell
# Einmalig: Test mit Laufwerk D:\
powershell -ExecutionPolicy Bypass -File Agenten\sichern-aussenhaus.ps1 -Laufwerk D

# Nur Prüfung ohne echte Kopie:
powershell -ExecutionPolicy Bypass -File Agenten\sichern-aussenhaus.ps1 -Laufwerk D -NurPruefen

# Echte Sicherung (nach erfolgreichem Test):
powershell -ExecutionPolicy Bypass -File Agenten\sichern-aussenhaus.ps1 -Laufwerk D
```

## Geplante Aufgabe (optional, für regelmäßige Erinnerung)

Wenn das Skript monatlich automatisch laufen soll:

```powershell
# PowerShell als Admin öffnen:
$task = @{
  TaskName = 'BrainFiles-Off-Site-Backup'
  Action = New-ScheduledTaskAction -Execute 'powershell' `
    -Argument '-ExecutionPolicy Bypass -File "C:\Users\faupe\Documents\BrainFiles\Agenten\sichern-aussenhaus.ps1" -Laufwerk D'
  Trigger = New-ScheduledTaskTrigger -At 14:00 -DaysInterval 30
  User = $env:USERNAME
}
Register-ScheduledTask @task -Force
```

Nach jedem Durchlauf im Log nachschauen: `Agenten\Routinen\logs\aussenhaus-letzter-lauf.log`

## Was das Skript macht

1. **Laufwerk prüfen** — USB-SSD erreichbar?
2. **Klartext-Zugangsdaten scannen** — (gleich wie `sichern.ps1`)
3. **Trockenlauf** (`/L`) — Was würde kopiert werden? Fehler prüfen.
4. **Echtkopie** — Mit `/MT:16` parallel (16 Threads)
5. **Atomare Übergabe** — Alt-Backup umbenennen, neues live setzen
6. **Verifizierung** — 5 zufällige Dateien MD5-prüfen gegen Original

## Was wird kopiert?

- ✓ `MaxHirn/` (45 GB) — Vault, Archiv-Struktur
- ✓ `Agenten/` (4 GB) — MCP-Server, Routinen, Sicherungsskripte
- ✓ `O:\Archiv` (44 GB) — Archivdaten (physisch auf O:, seit 07.09.2026)
- ✗ `Modelle/` — Modellgewichte sind neu herunterladbar (51 GB gespart)
- ✗ `Werkstatt/` — Transiente Übergaben (1 GB gespart)
- ✗ `.venv`, `__pycache__`, `node_modules`, `.git/` — alle reproduzierbar

**Gesamtgröße:** ~95 GB (konservativ mit Puffer)

## Datenverlustschutz

| Szenario | Folge |
|---|---|
| C: fällt aus | → G: (20:00 Sicherung) oder O: (21:00 Zweitkopie) oder USB (monatlich) |
| G: fällt aus | → C: (live) oder O: (21:00) oder USB (monatlich) |
| O: fällt aus | → C: (live) oder G: (20:00) oder USB (monatlich) |
| Alle drei gleichzeitig | → USB (monatlich, off-site) |
| USB fällt aus | → Kein Datenverlust; nächste monatliche Sicherung ist eine neue USB |

## Monitoring

Das Skript schreibt nach jedem Lauf ein Protokoll:

```powershell
# Letzten Lauf prüfen:
Get-Content Agenten\Routinen\logs\aussenhaus-letzter-lauf.log

# Nach "ERFOLG" suchen:
Select-String "ERFOLG" Agenten\Routinen\logs\aussenhaus-letzter-lauf.log
```

Wenn die geplante Aufgabe läuft, aber kein Protokoll entsteht → USB nicht erreichbar oder Pfad falsch.

## Troubleshooting

| Fehler | Ursache | Lösung |
|---|---|---|
| "Laufwerk D: existiert nicht" | USB nicht angestöpselt | USB einstecken |
| "robocopy-Code 16" | Dateien gesperrt (Claude läuft) | Claude beenden (Skript macht das automatisch) |
| "robocopy-Code 11" | Fehler auf robocopy-Ebene | Laufwerk auf Fehler prüfen (`chkdsk D: /F`) |
| "nur X GB verfügbar, aber Y erwartet" | USB zu klein | Größere SSD kaufen oder alte `.alt-*` Backups löschen |
| Verifizierung schlägt fehl | Korruption während Kopie | USB prüfen, Kopie wiederholen |

## Wartung

- **Monatlich:** Skript ausführen, Protokoll prüfen
- **Jährlich:** USB kontrollieren — MD5-Check gegen Original (oder einen frischen Full-Copy machen)
- **Nach Umzug:** Pfade in Skript überprüfen (sollten relativ sein, aber verifizieren)

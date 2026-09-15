---
name: system
description: Untersucht Windows-Probleme am Arbeitsrechner mit gezielten Abfragen statt Rundumscans — Abstürze ohne Bluescreen, hängender Explorer, nicht erkannte Geräte, abstürzende Dienste, fehlende Programme im PATH. Benutzen bei "der PC ist abgestürzt", "warum hängt", "scanne mein System auf Fehler", "wird nicht erkannt", "Ereignisanzeige", "repariere", "warum funktioniert X nicht mehr".
---

# Windows-Diagnose

**Erst nachschlagen, dann messen.** [[Hardware]] (657 Zeilen) hält den Stand von
Laufwerken, Netzteil, Absturzmustern und bereits ausgeschlossenen Ursachen fest.
[[Miniaturansichten]] hält fest, was beim Vorschaubild-Problem nachweislich
**nicht** half. Beides zuerst lesen — sonst wird ein bereits ausgeschlossener
Weg ein zweites Mal gegangen.

Offene Systempunkte stehen in `Archiv/TASKS.md` (T-002 bis T-004).

## 1. Gezielt abfragen, nicht scannen

Ein Rundumscan der Ereignisanzeige liefert tausende Zeilen und keine Antwort.
Diese Abfragen haben in den bisherigen Sitzungen tatsächlich zur Ursache geführt:

```powershell
# Unerwarteter Neustart / Stromverlust (das Leitsignal bei Abstürzen ohne Bluescreen)
Get-WinEvent -FilterHashtable @{LogName='System';Id=41,6008;StartTime=(Get-Date).AddDays(-30)} -ErrorAction SilentlyContinue | Select-Object TimeCreated,Id

# Plattenfehler: 153 = E/A-Fehler wiederholt, 140 = NTFS-Warnung
Get-WinEvent -FilterHashtable @{LogName='System';ProviderName='disk','Microsoft-Windows-Ntfs','volmgr';StartTime=(Get-Date).AddDays(-7)} -ErrorAction SilentlyContinue | Group-Object Id -NoElement

# Hardwarefehler der CPU/RAM/PCIe-Ebene
Get-WinEvent -FilterHashtable @{LogName='System';ProviderName='Microsoft-Windows-WHEA-Logger';StartTime=(Get-Date).AddDays(-30)} -ErrorAction SilentlyContinue | Select-Object -First 5

# Dienstabstürze: 7031/7034 = unerwartet beendet, 7023 = mit Fehler beendet
Get-WinEvent -FilterHashtable @{LogName='System';Id=7023,7031,7034;StartTime=(Get-Date).AddDays(-7)} -ErrorAction SilentlyContinue | Group-Object {$_.Properties[0].Value} -NoElement | Sort-Object Count -Descending | Select-Object -First 10
```

`-ErrorAction SilentlyContinue` gehört dazu: findet die Abfrage nichts, wirft
`Get-WinEvent` einen Fehler statt eine leere Menge zurück und bricht das Skript ab.

## 2. Die Fallen, die Zeit gekostet haben

**Kein Bluescreen heißt nicht „kein Absturz".** Bei Stromverlust und bei
Zugriffen auf ausgelagerte Seiten einer verschwundenen Platte schreibt Windows
weder Bluescreen noch `MEMORY.DMP`. Wer nach einem Speicherabbild sucht und
keins findet, schließt daraus fälschlich, es sei nichts passiert. Das Signal ist
Ereignis **41** ohne vorheriges 1001.

**Ein abstürzender Dienst überschreibt das Protokoll.** `WSearch` stürzte ab
dem 24.08.2026 rund 1.200-mal täglich ab; das Systemprotokoll reichte dadurch
nur noch wenige Stunden zurück. Deshalb **immer zuerst** prüfen, wie weit das
Protokoll überhaupt reicht — sonst wird eine Lücke als Beweis gelesen:

```powershell
(Get-WinEvent -LogName System -Oldest -MaxEvents 1).TimeCreated
```

**WMI lügt bei VRAM.** `Win32_VideoController.AdapterRAM` meldet für die
RTX 3060 Ti 4 GB — ein Überlauf des 32-Bit-Feldes. Tatsächlich 8 GB.

**Nicht jede Reparatur wirkt durch das, was sie tut.** Beim
Vorschaubild-Problem war die Registry vor und nach dem erfolgreichen Handgriff
messbar identisch (1438 `Bags`-Einträge, 63 Werte in `Explorer\Advanced`).
Wirkte das Zurücksetzen oder das Neuöffnen der Fenster? Ungeklärt. Bei einer
Reparatur, die aus mehreren Schritten besteht, **einen nach dem anderen** —
sonst ist am Ende unbekannt, welcher geholfen hat.

## 3. Bevor etwas verändert wird

Systemeingriffe fallen unter die Ansagepflicht: **erst sagen, was genau
passiert, dann bestätigen lassen.** Registry, Dienste, Autostart, Energieplan,
Umgebungsvariablen, Treiber — nichts davon ohne Ansage.

Ein Eingriff wird als Skript in `Routinen/` abgelegt, nicht als Befehlsfolge im
Chat ausgeführt. Vorbild: `Routinen/einmalig-20260828-absturzbehebung.ps1` mit
`-Testlauf` und `-Rueckgaengig`. Vorteile: Max kann es mit erhöhten Rechten
selbst starten, es ist prüfbar, und es ist umkehrbar.

**Adminrechte hat diese Sitzung nicht.** Braucht ein Schritt sie, wird das
Skript geschrieben und der Aufrufbefehl genannt — nicht versucht und dann
gemeldet, dass es nicht ging.

## 4. Nach jedem Befund

- Neue Erkenntnis mit Datum nach [[Hardware]] (oder die passende Notiz), nicht
  in die Chatantwort. **Auch die Negativbefunde** — „geprüft, war es nicht" ist
  beim nächsten Mal das Wertvollste.
- Bleibt etwas offen, sofort nach `Archiv/TASKS.md`, nicht am Sitzungsende.
- Zahlen gemessen angeben: „1.200 Abstürze täglich", nicht „sehr oft".

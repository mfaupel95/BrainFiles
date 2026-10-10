---
name: erhoehte-windows-aktion
category: system
description: Use when a Windows change needs admin rights.
version: 0.1.0
author: Hermes
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [Windows, Admin, UAC, Registry, CIM, Beleg]
    related_skills: [wirkung-nachweisen, trugschluesse, systemdiagnose, windows-host-zugriff]
---

# Erhoehte Windows-Aktion — belegen, nicht bestaetigen

Fuehrt eine Aenderung aus, die Adminrechte braucht (Auslagerungsdatei, Dienst,
geplante Aufgabe, HKLM-Registry), und **misst das Ergebnis am Ziel** statt am
Exitcode des Starters. Enthaelt den Ablauf Trockenlauf -> erhoeht starten ->
Ausgabe mitschreiben -> am Ziel nachsehen. Nicht enthalten: Prozesswachen
(`dauerprozess-bewachen`), Hermes-Config (`hermes-config-ops`), Systemcheck
(`systemdiagnose`). Nur Hausmittel: PowerShell 5.1, WMI/CIM, Registry — kein
Fremdwerkzeug.

## When to Use

- eine Aenderung braucht Adminrechte und Max hat sie freigegeben (`mach das`, `ja`)
- ein erhoehtes Skript meldet Erfolg, aber am System hat sich nichts geaendert
- eine Aenderung wirkt erst nach einem Neustart (Auslagerung, Speicher, Dienst)
- ein Wert soll gesetzt werden, den die Windows-GUI sonst schreibt (Auslagerungsdatei,
  Umgebungsvariable, Firewall, geplante Aufgabe)
- eine Datei unter `HKLM` ist zu aendern (Registry-Weg statt WMI)

**Don't use for:** eine normale (nicht erhoehte) Aenderung an einer Datei im Repo —
dafuer `brainfiles-auftrag`; das Messen einer Wirkung ohne Adminbezug — `wirkung-nachweisen`.

## Prerequisites

- **UAC-Prompt:** Max bestaetigt ihn, wenn die Aktion vorher klar benannt wurde. Den
  Grund im Bericht nennen, nicht offen lassen („braucht Admin").
- **Stufe 1:** vorher `.bak-JJJJMMTT` neben die Zieldatei, `-Rueckgaengig` im Skript.
- Skripte und Wrapper nach `Agenten/Hermes/cache/scratch/` schreiben (`write_file`),
  Beleg-Logs nach `Agenten/Hermes/logs/`.
- Aufruf immer als Datei: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File <pfad>`
  — nie als `-Command` aus bash (Backticks und verschachtelte Quotes zerfallen).

## How to Run

```bash
# 1) Ist-Stand messen (nie aus dem Skriptkopf annehmen)
powershell.exe -NoProfile -Command "Get-CimInstance Win32_PageFileSetting | Format-Table Name,InitialSize,MaximumSize"
# 2) Trockenlauf des Zielskripts
powershell.exe -NoProfile -ExecutionPolicy Bypass -File <ziel.ps1> -Testlauf
# 3) erhoeht starten MIT Ausgabe-Mitschnitt (Fenster schliesst sofort)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/erhoeht-starten.ps1 -Skript <ziel.ps1> -Argumente '-Anlegen'
# 4) am ZIEL messen — nicht den Exitcode des Starters glauben
```

## Quick Reference

| Zweck | Aufruf |
|---|---|
| Ist-Stand Auslagerung | `Get-CimInstance Win32_PageFileSetting` |
| belegte Auslagerung | `Get-CimInstance Win32_PageFileUsage` |
| Commit-Grenze | `Get-CimInstance Win32_OperatingSystem` -> `TotalVirtualMemorySize` (KB) |
| Registry-Wahrheit | `HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management` -> `PagingFiles` (`REG_MULTI_SZ`, je Zeile `<Pfad> <AnfangMB> <MaximumMB>`) |
| erhoeht + Log | `scripts/erhoeht-starten.ps1 -Skript <ps1> [-Argumente '-Anlegen'] [-Log <datei>]` |
| Belege | `Agenten/Hermes/logs/<thema>-JJJJMMTT.log` |

## Procedure

1. **Ist-Stand messen, bevor du planst.** Ein Skriptkopf beschreibt den Zustand von
   damals; zwischen zwei Laeufen kann jemand von Hand umgestellt haben (gemessen: die
   Auslagerungsdatei auf C: stand selbstverwaltet, der Eintrag auf O: war ganz weg).
   Ohne diese Messung baust du eine Aenderung auf einer Annahme.
2. **Zielskript schreiben** mit `-Testlauf` (nur rechnen, nie schreiben) und
   `-Rueckgaengig`. Jede Zeile, die `Write-Host` ausgibt, gehoert in den Trockenlauf —
   er ist der Vertrag, den du vor dem UAC-Prompt liest.
3. **Trockenlauf fahren und die Ausgabe LESEN** (nicht nur den Exitcode): er muss den
   Ist-Stand und den Soll-Stand je Zeile nennen.
4. **Wrapper mit Ausgabe-Mitschnitt bauen** (`scripts/erhoeht-starten.ps1`): das
   erhoehte Fenster schliesst sofort, seine Ausgabe ist sonst verloren. Der Wrapper
   laesst das Zielskript in ein Log schreiben (`*>&1 | Tee-Object -FilePath <log>`) und
   gibt am Ende den Log-Schwanz auf der normalen Konsole aus.
5. **Erhoeht starten** und warten (`Start-Process -Verb RunAs -Wait`).
6. **Am ZIEL messen:** denselben Abruf wie in Schritt 1 wiederholen. Der Exitcode des
   Starters sagt nur, dass der UAC-Dialog bestaetigt wurde — er ist kein Beleg.
7. **Idempotenz gegenpruefen:** den Trockenlauf erneut fahren. Er muss jetzt
   „schon gesetzt, nichts zu tun" melden. Das ist der Beweis, dass Schritt 5 gewirkt hat.
8. **Wirkung mit Bedingung dokumentieren:** braucht die Aenderung einen Neustart, das
   ausdruecklich hinschreiben und eine eigene Aufgabe dafuer anlegen
   (`MaxHirn/Archiv/TASKS.md`, ID frisch lesen).
9. **Lektion ins Wiki** (`MaxHirn/Wiki/Lektionen/Windows-Umgebung.md`) und alles mit
   `Agenten/Hermes/cache/scratch/commitmsg_<thema>.txt` committen.

## Pitfalls

- **Ein CIM-Typkonflikt toetet das Skript STILL.** `Win32_PageFileSetting.InitialSize`
  ist `UInt32`; ein `Int32` aus der Parameteruebergabe loest „Typenkonflikt fuer die
  Eigenschaft InitialSize" aus. Mit `$ErrorActionPreference='Stop'` bricht der Lauf dort
  ab — und weil die Ausgabe erst am Ende geschrieben wird, steht im Log **keine**
  Fehlerzeile: der Lauf hatte C: schon gesetzt und endete vor dem O:-Eintrag, von
  aussen sah es nach Erfolg aus. Immer `[uint32]` casten.
- **`New-CimInstance` kann auch ohne Typfehler still scheitern.** Faellt der WMI-Weg aus,
  ist der Registry-Weg der richtige (es ist der Weg der GUI): `New-ItemProperty -Path
  'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management' -Name
  PagingFiles -PropertyType MultiString -Value @('C:\pagefile.sys 8192 8192',
  'O:\pagefile.sys 32768 32768') -Force`. `-Force` ist Pflicht, sonst bleibt der alte Wert.
- **`PagingFiles` ist `REG_MULTI_SZ`, kein String.** Ein einzelner String macht daraus
  eine Zeile mit Leerzeichen und Windows ignoriert beide Eintraege.
- **Die Wirkung kommt erst beim Start.** WMI zeigt den Soll-Zustand sofort, die
  Commit-Grenze (`TotalVirtualMemorySize`) erst nach dem Neustart. Ohne Neustart ist die
  Aenderung gesetzt, aber wirkungslos — das gehoert in die Meldung.
- **Eine selbstverwaltete Auslagerungsdatei waechst unbegrenzt.** Auf einem Laufwerk mit
  wenig Platz fuellt sie es (gemessen: 21 GB auf C: bei 19,3 GB frei). Grosse Dateien
  gehoeren auf das Laufwerk mit Platz, und die Groesse wird FEST gesetzt (`Anfang =
  Maximum`), nicht „System verwaltet".
- **`Start-Process -Verb RunAs` kann seine Ausgabe NICHT umleiten**
  (`-RedirectStandardOutput` ist mit `RunAs` unzulaessig). Deshalb schreibt das Ziel
  selbst ins Log — der Umweg ueber den Wrapper ist kein Komfort, sondern notwendig.
- **PS 5.1 kennt die 3-Argument-Form von `[System.IO.File]::Move` nicht** und
  `Move-Item` ohne `-Force` tut bei VERSTECKTEN Dateien still nichts. Fuer Umbenennen:
  `Move-Item -LiteralPath <quell> -Destination <ziel> -Force`, danach `Test-Path` auf
  BEIDE Pfade.
- **`Write-Host` ueberlebt das erhoehte Fenster NICHT.** `Tee-Object` schreibt nur, was
  durch die Pipeline laeuft; die eigenen `Write-Host`-Zeilen des Wrappers gehen an die
  Host-Konsole und sind mit dem Fenster weg (gemessen: im Log fehlte genau die
  `EXITCODE=`-Zeile). Alles, was den Lauf belegen soll, mit `Add-Content -LiteralPath
  <log> -Value ...` schreiben.
- **Werte nie mit `reg query` ausgeben** — das druckt Secrets im Klartext ins
  Sitzungsprotokoll. Zur Pruefung nur die Existenz messen
  (`[Environment]::GetEnvironmentVariable('<name>','User')`) und Laenge/Anfang nennen.
- **Ein Log in UTF-16.** PowerShell schreibt roehrige Logs in UTF-16LE; `iconv` aus bash
  liefert dann leer. Mit `read_file` oder `powershell Get-Content` lesen.

## Verification

Ein erhoeht gesetzter Wert ist belegt, wenn Trockenlauf, Ziel-Abruf und Idempotenz
zusammenpassen:

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File <ziel.ps1> -Testlauf   # "schon gesetzt"
powershell.exe -NoProfile -Command "Get-CimInstance Win32_PageFileSetting | Format-Table Name,InitialSize,MaximumSize"
powershell.exe -NoProfile -Command "(Get-CimInstance Win32_OperatingSystem).TotalVirtualMemorySize"  # erst nach Neustart der neue Wert
```

Erwartet: der Trockenlauf meldet nichts zu tun, der Ziel-Abruf zeigt den Soll-Wert, und
wo ein Neustart noetig ist, steht das als eigene Aufgabe — nicht als „erledigt".

Der Wrapper selbst hat einen Selbsttest, der OHNE UAC und ohne Aenderung am System
laeuft (Syntax unter 5.1, verbotene Aufrufe, Log-Mechanik samt Exitcode):

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/pruefe-erhoeht-starten.ps1
# Erwartet: SYNTAX OK / sauber: ... / MECHANIK OK / ERGEBNIS: bestanden (Exit 0)
```

**Real-Lauf bestaetigt 2026-10-07 (Karte t_4aa83567):** der Wrapper wurde mit einem
harmlosen Zielskript echt unter UAC gefahren — Wrapper-Exit 0, Ziel-Exit 0, Log mit
Admin=True, UAC-Dialog von Max bestaetigt (00:28:45-00:28:51). Protokoll:
`Agenten/Hermes/kanban/boards/wartung/attachments/t_02601aee/protokoll-abschluss-t_02601aee.md`

---
name: tagesbriefing
description: Erstellt einen kurzen Überblick über den Tag — Termine, offene Punkte aus den Projekten, was im Posteingang liegt. Benutzen bei "Tagesbriefing", "was steht heute an", "guten Morgen", "Überblick", oder als morgendliche Routine.
---

# Tagesbriefing

Ziel: ein Bildschirm, keine Seite. Max soll in 30 Sekunden wissen, woran er ist.

## Zusammentragen

**1. Kontext** — [[Profil]] und [[Projekte]] lesen. Ohne das wird das Briefing
generisch.

**2. Termine** — falls der Kalender angebunden *und angemeldet* ist, die Termine
von heute holen. Ist er es nicht: nicht anlegen, nicht raten, nur einmal kurz
erwähnen, dass Termine fehlen (siehe [[Verbindungen]]).

**3. Offene Punkte** — aus [[Projekte]] die Zeilen „Nächste Schritte" und alle
offenen Kästchen `- [ ]` aus dem Vault:

```powershell
Select-String -Path "Wissen\*.md","Dashboard.md" -Pattern "^\s*- \[ \]"
```

**4. Posteingang** — nur die Zahl, nicht die Dateiliste:

```powershell
$pe = if ($env:ARCHIV_ROOT) { $env:ARCHIV_ROOT } else { 'Archiv' }
Get-ChildItem (Join-Path $pe 'Posteingang') -Recurse -File | Measure-Object | Select-Object Count
```

**5. System** — der letzte Bericht der Systemprüfung ([[Systempruefung]]):

```powershell
Get-Content ..\Agenten\Routinen\logs\systempruefung-letzter-lauf.md
```

Nur die Abschnitte „Seit gestern neu" und „Zu entscheiden" ins Briefing, und
auch die nur, wenn sie nicht leer sind. Ist der Bericht nicht von heute, das
kurz sagen statt raten.

## Ausgeben

```
## Heute, <Wochentag> <Datum>

**Termine**
- <Zeit> <Titel>          (oder: keine / Kalender nicht angebunden)

**Dran**
- <höchstens drei Punkte, die heute wirklich zählen>

**Nebenbei**
- <z. B. 12 Dateien im Posteingang>

**System**
- <„Seit gestern neu" / „Zu entscheiden" aus der Systemprüfung, oder: nichts>
```

## Regeln

- **Höchstens drei Punkte unter „Dran".** Eine vollständige Liste ist kein
  Briefing. Lieber weglassen und begründen.
- Nichts erfinden. Fehlt eine Quelle, steht das da — keine Platzhaltertermine.
- Keine Ratschläge zur Lebensführung, keine Motivationssätze.
- Nichts versenden und nichts ändern. Das Briefing liest nur.

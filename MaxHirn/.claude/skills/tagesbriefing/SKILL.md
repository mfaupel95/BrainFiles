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
Get-ChildItem Archiv\Posteingang -Recurse -File | Measure-Object | Select-Object Count
```

## Ausgeben

```
## Heute, <Wochentag> <Datum>

**Termine**
- <Zeit> <Titel>          (oder: keine / Kalender nicht angebunden)

**Dran**
- <höchstens drei Punkte, die heute wirklich zählen>

**Nebenbei**
- <z. B. 12 Dateien im Posteingang>
```

## Regeln

- **Höchstens drei Punkte unter „Dran".** Eine vollständige Liste ist kein
  Briefing. Lieber weglassen und begründen.
- Nichts erfinden. Fehlt eine Quelle, steht das da — keine Platzhaltertermine.
- Keine Ratschläge zur Lebensführung, keine Motivationssätze.
- Nichts versenden und nichts ändern. Das Briefing liest nur.

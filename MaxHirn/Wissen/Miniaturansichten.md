---
id: 20260830-miniaturansichten
title: 'Miniaturansichten im Explorer (Stand 25.08.2026)'
tags: [system]
created: 2026-08-25
updated: 2026-08-25
related: []
summary: 'Warum der Explorer keine Vorschaubilder mehr zeigte und was dagegen geholfen hat.'
---

# Miniaturansichten im Explorer (Stand 25.08.2026)

Am 25.08.2026 zeigte der Explorer für Bilder und Videos nur noch generische
Platzhalter-Symbole statt Vorschaubildern — auch in „Sehr große Symbole",
auch im Datei-Öffnen-Dialog von Paint, auch bei nachweislich intakten Dateien.

## Was geholfen hat

**Explorer → `⋯` → Optionen → Reiter *Ansicht* → „Standardwerte wiederherstellen"**,
danach **alle Explorer-Fenster schließen und neu öffnen**.

Zwei Klicks, kein Registry-Eingriff, kein Neustart.

**Die Wirkursache ist nicht isoliert.** Vor und nach dem Handgriff wurde die
Registry verglichen — sie war *unverändert*: `Bags` 1438 Einträge wie vorher,
`Streams\Defaults` weiterhin dieselben 3 Einträge, `IconsOnly` durchgehend 0,
63 Werte in `Explorer\Advanced` wie zuvor, `ShellState` fehlte vorher wie
nachher. Es ist deshalb offen, ob das Zurücksetzen wirkte oder das Neuöffnen
der Fenster (siehe `SeparateProcess` unten). Beim nächsten Mal: **erst nur die
Fenster neu öffnen**, das trennt die beiden Fälle.

## Was nachweislich nicht half

Alles gemessen, nicht vermutet — diese Liste spart beim nächsten Mal Stunden:

| Geprüft | Ergebnis |
|---|---|
| Thumbnail-Cache geleert | 36,1 MB → 3 MB, wirkungslos |
| Icon-Cache | war ohnehin frisch angelegt, wirkungslos |
| `IconsOnly` | 0 (korrekt) |
| `VisualFXSetting` | 3 = Benutzerdefiniert (korrekt) |
| Gruppenrichtlinien | keine Thumbnail-Sperre in HKCU/HKLM |
| Thumbnail-Handler + DLLs | alle registriert und vorhanden |
| `sfc /scannow` | keine Integritätsverletzungen |
| PowerToys (15 Module) | beendet + Explorer neu, wirkungslos |
| Fotos-App | Status Ok |
| Ordneransichten (Bags) | Reset vorbereitet, war unnötig |
| Tote `P:`-Verweise in `Pictures` | keine `desktop.ini` mit `P:` |

## Der Test, der die Richtung vorgibt

`Routinen/thumbnails-pruefen.ps1` prüft über `IShellItemImageFactory`, ob
Windows überhaupt Miniaturen **erzeugen** kann. Das trennt die zwei Fälle, die
im Explorer identisch aussehen:

- **Erzeugung schlägt fehl** → Datei kaputt oder Handler/Codec defekt
- **Erzeugung klappt, Explorer zeigt nichts** → Anzeigeproblem, wie hier

Am 25.08.2026 lieferten **98 von 98** intakten Bildern eine Miniatur, ebenso ein
Video. Damit war die Erzeugung freigesprochen und die halbe Fehlersuche hinfällig.

Entscheidend ist dabei das Flag `SIIGBF_THUMBNAILONLY` (0x08): Ohne dieses Flag
gibt Windows ersatzweise das Dateisymbol zurück, und der Test meldet immer
Erfolg — auch wenn keine echte Miniatur existiert.

## Drei Fallen, die Zeit gekostet haben

**`reg query … /v Wert` scheitert im Bash-Werkzeug.** Git Bash wandelt `/v` in
einen Pfad um, die Abfrage bricht mit „Ungültige Syntax" ab. Für die Registry
immer PowerShell benutzen. Eine so gescheiterte Abfrage darf nicht als
gemessener Wert weitergetragen werden — genau das ist hier passiert.

**`SeparateProcess = 1`** (in `Explorer\Advanced`): Jedes Ordnerfenster liest
seine Einstellungen nur **beim Öffnen**. `F5` übernimmt eine Registry-Änderung
nicht — ein länger offenes Fenster misst den Stand von vorhin. Nach jeder
Änderung Fenster schließen und neu öffnen.

**Ein leerer Wert ist kein Defekt.** Der fehlende `FolderType` in den `Bags` sah
nach Beschädigung aus — der Ordnertyp steckt aber in der GUID des
Unterschlüssels, das ist normal. Ebenso `ShellState`: fehlt, und das System
funktioniert trotzdem.

## Nicht mit echtem Datenverlust verwechseln

Rund 18–23 % der Dateien in `Archiv/Bilder` sind 0xFF-Füllbytes aus dem
Netzteildefekt (siehe [[Hardware]] und `Archiv/BESCHAEDIGTE_DATEIEN.md`). Dort
kann es prinzipiell keine Vorschau geben. Das Skript zählt diese Dateien
getrennt, damit sie nicht als Anzeigefehler durchgehen.

Verwandt: [[Hardware]]

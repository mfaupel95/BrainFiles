---
id: 20260902-systempruefung
title: 'Systemprüfung'
tags: [betrieb]
created: 2026-09-02
updated: 2026-09-13
related: [20260830-routinen, 20260830-ordnerstruktur, 20260830-portabilitaet]
summary: 'Tägliche Morgenroutine, die das KI-System nach still gebrochenen Dingen absucht — tote Junctions, doppelte Ollama-Stores, absolute Pfade, kaputte MCP-Pfade, knapper Plattenplatz, fehlgeschlagene Aufgaben.'
---

# Systemprüfung

Seit dem 02.09.2026. Nach dem Umzug des Systems (Ordnertrennung 30.08.2026,
`Modelle/` als Junction auf `O:\Modelle`) bricht Verschiedenes still: ein
Skript zeigt auf den alten `MaxHirn\`-Pfad, ein `npm`-Baum voller Junctions
zeigt ins Leere, `OLLAMA_MODELS` wurde umgehängt und der alte Store bleibt als
totes Gewicht liegen. Nichts davon meldet sich von selbst.

Die Routine `Agenten/Routinen/systempruefung.ps1` läuft **täglich 07:00** und
sucht gezielt danach ab. Sie ist im Kern lesend; eindeutig reproduzierbaren
Müll räumt sie selbst weg (siehe unten).

## Was geprüft wird

| # | Prüfung | Reaktion |
|---|---|---|
| 1 | Git: uncommittete Dateien älter als 1 h, Alter des `zwischenstand`-Zweigs | melden |
| 2 | Tote Junctions (Ziel existiert nicht mehr) | außerhalb `node_modules`: selbst entfernen · in `node_modules`: melden (`npm install` oder Server weg) |
| 3 | Verwaiste Ollama-Blob-Stores neben dem aktiven (`OLLAMA_MODELS`) | alle Blobs auch im aktiven Store → selbst löschen · sonst melden |
| 4 | `.venv`-Reste mit „kaputt" im Namen; `pyvenv.cfg` → `home` existiert nicht | Rest mit funktionierendem `.venv` daneben → selbst löschen · sonst melden |
| 5 | `C:\Users\faupe`-Pfade und `\MaxHirn\MCP-Server` / `\Claude\`-Fragmente in `*.ps1`/`*.py` | melden (Portabilität) |
| 6 | `command`-Pfade in allen `.mcp.json` lösen auf | melden |
| 7 | Freier Platz auf `C:` (< 20 GB), `O:` (< 40 GB), `G:` (fehlt / < 15 GB) | melden |
| 8 | `.bak-*`-Handkopien, leere Gerüst-Ordner in `Modelle`, `Kimi-K2.7-Code`-Größe | melden |
| 9 | `MaxHirn-*`-Aufgaben: deaktiviert, letzter Lauf ≠ Code 0, oder seit dem erwarteten Abstand nicht mehr gestartet | melden |
| 10 | Regelwerk: die vier `CLAUDE.md`/`AGENTS.md`-Paare deckungsgleich (SHA256), Skills als Ordner mit `SKILL.md`, `updated:` in geänderten Notizen | melden |
| 11 | Bedingung 4: Journal und Zustand jeder Handelsspur **byte-genau** gegen `Q:\Handel_Journal\…` | melden |
| 12 | Handels-Dauerlauf: Prozess vorhanden, letzter Zyklus im Bus-Journal nicht älter als 45 min | melden |

Block 5 nimmt zwei Orte aus: `Routinen/umzug/` (eingefrorene Migrationsskripte)
und `Agenten/Hermes/cache/` (Wegwerf- und Probenskripte, nicht versioniert).
Beide tragen absolute Pfade mit Absicht; ohne die Ausnahme meldete der Block
jeden Tag dieselben 14 Cache-Dateien und wäre damit ein Dauerfehlalarm.

Die Blöcke 11 und 12 rufen
`Agenten/Handel/spiegelstand.py` auf — nur lesend, Rückgabecode 0 = jede Spur im
Dauerlauf ist byte-gleich. Spuren außerhalb des Dauerlaufs (`kraken` mit eigenem
Zeitfenster, `orb` als Altbestand) werden mitgeprüft, aber gekennzeichnet und
nicht als Fehler gezählt. Dieselbe Rechnung liefert die Zeile „Journal außer
Haus" im Tagesbericht (`tagesbericht.spiegelzeile()`).

Neue Prüfungen kommen als eigener nummerierter Block ins Skript — Reihenfolge
und Nummern sind der Vertrag mit dem „Seit gestern neu"-Vergleich.

## Ausgabe

- `Agenten/Routinen/logs/systempruefung-JJJJ-MM-TT.log` — Vollprotokoll je Lauf,
  30 Tage aufgehoben.
- `Agenten/Routinen/logs/systempruefung-letzter-lauf.md` — strukturierter
  Bericht, stabiler Name. Vier Abschnitte: **Seit gestern neu** (Punkte, die im
  Bericht von gestern noch nicht standen), **Selbst erledigt**, **Zu
  entscheiden**, **Zur Kenntnis**.

Der Bericht erreicht Max auf drei Wegen:

1. **SessionStart-Hook** in `MaxHirn/.claude/settings.local.json`: Beim Öffnen
   einer Claude-Sitzung wird der Kopf des Berichts eingeblendet, wenn er von
   heute ist und etwas zu entscheiden übrig bleibt.
2. **`tagesbriefing`-Skill**: liest den Bericht als Abschnitt „System" ein.
3. **Aufgabenplanung**: `MaxHirn-Systempruefung`, täglich 07:00, „Starten sobald
   möglich" (wie die anderen Routinen — [[Routinen]]).

## Von Hand

```
powershell -ExecutionPolicy Bypass -File Agenten\Routinen\systempruefung.ps1 -NurPruefen
```

`-NurPruefen` unterdrückt jeden Aufräum-Schritt — nur Bericht. Ohne den Schalter
löscht der Lauf die selbst-erledigbaren Fälle.

## Grenzen

- Kein Duplikat-Abgleich über ganze Ordner — dafür ist der Skill `vergleich` da.
- Prüft nur `BrainFiles/` und `O:\Modelle`, nicht den restlichen Benutzerordner.
- Findet keine inhaltlichen Fehler in Skripten, nur kaputte Pfade und Struktur.

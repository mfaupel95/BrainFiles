---
id: 20260910-brainfiles-bus
title: 'BrainFiles Bus'
tags: [system, betrieb]
created: 2026-09-10
updated: 2026-09-10
related: [20260830-routinen]
summary: 'Der zentrale Meldedienst für alle geplanten Aufgaben. Wie man ihn startet, prüft und betreibt.'
---

# BrainFiles Bus

Der Bus meldet den Start und die Beendigung aller geplanten Aufgaben (Routinen) an ein zentrales Journal, wertet deren Erfolg aus und sichert Fehler auf dem Handy.

**Kernregel: Ein toter Bus darf niemals einen Lauf abbrechen** — alle Erzeuger schreiben lokal ins Journal zurück.

## Von Hand starten

```bash
python Agenten/Bus/bus.py
```

Der Bus benutzt Port 8766 (nachzuschauen in `Agenten/Bus/bus.json`, falls belegt). Die Adresse ist `127.0.0.1` — nur lokal, von diesem Rechner aus erreichbar.

Der Bus wird danach im Hintergrund laufen und alle Ereignisse von Routinen sammeln.

## Automatisch starten (bei Systemstart)

**Nur als Administrator ausführen:**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File Agenten\Routinen\bus.ps1
```

Danach:

- **Aufgabentitel:** `BrainFiles-Bus`
- **Trigger:** Bei Systemstart
- **Aktion:** `python Agenten\Bus\bus.py`
- **Bei Fehler:** Neustart nach 1 Minute, maximal 99 Versuche
- **Zeitlimit:** unbegrenzt

Die Aufgabe wird danach automatisch mit dem Rechner gestartet und läuft im Hintergrund.

## Den Bus prüfen

**Läuft der Bus gerade?**

```powershell
Get-Content Agenten/Bus/bus.json | ConvertFrom-Json | Select-Object -Property port, pid
```

Gibt Port und Prozess-ID aus. Ist die PID vorhanden, läuft der Bus.

**Wie viele Ereignisse sind heute gesammelt?**

```bash
python -c "import sys; sys.path.insert(0, 'Agenten/Bus'); import journal; events = journal.lesen(); print(f'{len(events)} Ereignisse heute'); components = {e['wer'] for e in events}; print(f'{len(components)} Komponenten: {sorted(components)}')"
```

**Tagesmeldung anschauen:**

```bash
python -c "import sys; sys.path.insert(0, 'Agenten/Bus'); import sprecher; s = sprecher.Sprecher(None, {}, wurzel=None); print(s.tagesmeldung())"
```

## Das Journal

Liegt in `Agenten/Bus/journal/JJJJ-MM-TT.jsonl` — täglich eine neue Datei, JSONL-Format (je eine Zeile = ein Ereignis).

Beispiel-Zeile:

```json
{
  "id": "ccf770b20abb42c3b88a41421c35968c",
  "wer": "routine/sicherung",
  "was": "start",
  "code": null,
  "dauer_s": null,
  "text": "",
  "log": "Agenten/Routinen/logs/sicherung-letzter-lauf.log",
  "zeit": "2026-09-10T20:00:00+02:00"
}
```

**Acht Felder, immer dieselben:**

- `id` — UUID, eindeutig je Ereignis
- `wer` — `routine/X` oder `handel/Y` oder andere
- `was` — `start` oder `ende`
- `code` — Exitcode (nur bei `ende`, `null` bei Erfolg)
- `dauer_s` — Laufdauer in Sekunden (nur bei `ende`)
- `text` — Freitext-Grund bei Fehler (sonst `""`)
- `log` — Relativer Pfad zum Protokoll (sonst `""`)
- `zeit` — ISO-8601 mit Zeitzone

## Tests

```bash
python Agenten/Bus/tests/test_ende_zu_ende.py
```

Führt alle 8 Modultests aus und nimmt die vier Abnahmepunkte ab:

1. Alle Komponenten melden Start und Ende
2. Ein erzwungener Fehler erscheint binnen einer Minute auf dem Handy
3. Ein gestoppter Bus lässt einen Lauf durchlaufen
4. Die Tagesmeldung listet alle Läufe des Tages

## Gefälle zwischen Bus und Routinen

| | Bus | Routine |
|---|---|---|
| startet | bei Systemstart oder von Hand (`python bus.py`) | wie geplant (Aufgabenplanung) |
| prüft | alle Ereignisse, wertet aus, sendet Meldungen | führt eine Aufgabe aus, meldet Start und Ende |
| bei Fehler des Busses | Routine meldet ins lokale Journal zurück | keine Blockade, sauberer Abschluss garantiert |
| bei Fehler der Routine | Bus sieht Exit-Code und sendet Warnung | toter Bus kostet nichts — Routine protokolliert lokal |

## Abruf und Steuerung

Teilprojekt 2 — hier nicht.

## Deutung und Alarme

Teilprojekt 3 — hier nicht.

## Wer nutzt den Bus?

- Alle Routinen in `Agenten/Routinen/` — jede ruft `Melde-Start` und `Melde-Ende` auf
- Alle Handelsspuren (Scanner, Kraken, XPERP) — jede meldet ihre Zyklen
- Der Handels-Dauerlauf — meldet seine 15-Minuten-Takte

Der Sprecher im Bus-Prozess liest aus dem Journal, wertet Fehler aus und sendet sie an Telegram — das ist der Melder für Fehler und die Tagesmeldung.

## Neubeginn nach Umzug

Die Datei `bus.ps1` erzeugt einen absoluten Pfad zur Laufzeit; nach einem Umzug des Vaults muss das Skript einmal neu laufen (mit Administrator-Rechten), damit die Aufgabe den neuen Pfad erfasst.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File Agenten\Routinen\bus.ps1
```

Danach sind Port, PID und Pfad aktualisiert, und die Aufgabe startet wieder automatisch.

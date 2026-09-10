# BrainFiles Bus

Der Bus meldet den Start und die Beendigung aller geplanten Aufgaben an ein zentrales Journal, wertet deren Erfolg aus und sichert Fehler auf dem Handy.

Ein toter Bus darf niemals einen Lauf abbrechen — alle Erzeuger schreiben lokal ins Journal zurück.

## Dateien

- `bus.py` — Der HTTP-Dienst. Schreibt ins Journal, verteilt Ereignisse an den Sprecher.
- `journal.py` — Der einzige Ort der Wahrheit: `journal/JJJJ-MM-TT.jsonl`.
- `ereignis.py` — Python-Erzeuger: Stellt lokale Versuche an, fällt sonst ans Journal zurück.
- `Ereignis.ps1` — PowerShell-Erzeuger: `Melde-Start` und `Melde-Ende`.
- `auffaellig.py` — Regeln für Fehlerauswertung: Exitcode, Median-Dauer, Ausbleiben.
- `sprecher.py` — Der Melder: tastet Fehler und Tagesmeldungen aus, fädelt sich in `bus.py` ein.
- `bus.json` — Der Port und die PID des laufenden Busses.

## Von Hand starten

```bash
python bus.py
```

Der Bus benutzt Port 8766 (in `bus.json` nachzuschauen, falls belegt). Die Adresse ist `127.0.0.1` — nur lokal.

## Registrieren für Systemstart

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File Agenten\Routinen\bus.ps1
```

Erfordert Administrator-Rechte. Danach:

- Aufgabenplanung: `BrainFiles-Bus`
- Trigger: Bei Systemstart
- Aktion: `python Agenten\Bus\bus.py`
- Bei Fehler: Neustart nach 1 Minute, maximal 99 Versuche
- Zeitlimit: unbegrenzt

## Journal

Liegt in `Agenten/Bus/journal/JJJJ-MM-TT.jsonl` — tägliche Rotation, JSONL-Format, 8 Felder je Zeile:

```json
{
  "id": "uuid (eindeutig je Ereignis)",
  "wer": "routine/sicherung oder handel/dauerlauf oder ...",
  "was": "start oder ende",
  "code": "Exitcode (nur bei was=ende, null bei Erfolg)",
  "dauer_s": "Laufdauer in Sekunden (nur bei was=ende, null bei Fehler)",
  "text": "Freitext-Grund (nur bei Fehler, sonst '')",
  "log": "Relativer Pfad zum Protokoll (sonst '')",
  "zeit": "ISO-8601 mit Zeitzone"
}
```

## Tests

```bash
python tests/test_ende_zu_ende.py
```

Führt alle 8 Modultests aus und nimmt die vier Abnahmepunkte ab:

1. Alle Komponenten melden Start und Ende
2. Ein erzwungener Fehler erscheint binnen einer Minute auf dem Handy
3. Ein gestoppter Bus lässt einen Sicherungslauf durchlaufen
4. Die Tagesmeldung listet alle Läufe des Tages

## Abruf und Steuerung

Teilprojekt 2. Hier geht das nicht.

## Deutung

Teilprojekt 3. Hier geht das nicht.

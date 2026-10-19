---
id: 20260930-desktop-verknuepfungen
title: 'Desktop-Verknuepfungen fuer die UI-Fenster'
tags: [betrieb, werkzeuge]
created: 2026-09-30
updated: 2026-09-30
related: [20260921-spuren-uebersicht]
summary: 'Vier Verknuepfungen (Handelszentrale, Werkzeug-Zentrale, Freqtrade-Bots, MoonDev-GUI), erzeugt von Agenten/Werkzeuge/desktop-verknuepfungen.ps1 - und warum das Arbeitsverzeichnis das Entscheidende ist.'
---

# Desktop-Verknuepfungen fuer die UI-Fenster

Stand 30.09.2026. Erzeugt und geprueft von
`Agenten/Werkzeuge/desktop-verknuepfungen.ps1` (idempotent, ersetzt vorhandene
Verknuepfungen gleichen Namens):

```
powershell -ExecutionPolicy Bypass -File Agenten\Werkzeuge\desktop-verknuepfungen.ps1
```

| Verknuepfung | Ziel | Arbeitsverzeichnis |
|---|---|---|
| Handelszentrale | `powershell -File Agenten\Routinen\handelszentrale.ps1` | `Agenten\Routinen` |
| Werkzeug-Zentrale | `repos-zentrale\.venv\Scripts\pythonw.exe repos_zentrale.py` | `Agenten\Werkzeuge\repos-zentrale` |
| Freqtrade-Bots | `cmd /c start` der drei Web-UIs 8081/8082/8083 | `Agenten\Handel\freqtrade` |
| MoonDev-GUI | `moon-dev-ai-agents\.venv\Scripts\pythonw.exe moongui.py` | `Werkstatt\moon-dev-ai-agents` |

## Warum ein Skript und nicht vier Klicks

**Eine Verknuepfung braucht Target, Argumente UND Arbeitsverzeichnis.** Fehlt das
dritte, startet das Programm im falschen Ordner und findet seine Dateien nicht.
Genau so entstanden zwei Reste auf dem Desktop: Textdateien, deren NAME der
ganze fehlgeschlagene Befehl war
(`CUsersfaupeDocumentsBrainFiles...pythonw.exe repos_zentrale.py.txt`). Beide
wurden entfernt, dazu eine Verknuepfung auf ein DEAKTIVIERTES Ziel
(`Startup\.disabled-20260918\MoonDev-GUI.vbs`).

Die Handelszentrale laeuft ueber ihren WRAPPER, nicht direkt: er prueft den
Fenstertitel und startet nichts, wenn schon ein Fenster offen ist - ein zweites
Fenster zeigt dasselbe und laesst sich spaeter nicht von einem Dienst
unterscheiden.

## Fallen beim Bauen (beide erlebt)

1. **`$args` ist in PowerShell eine automatische Variable.** Ein Funktions-
   parameter dieses Namens laesst `$s.Arguments = $args` mit
   `System.Object[] kann nicht in string konvertiert werden` abbrechen.
   Parameter `$argumente` nennen.
2. **Keine Umlaute in einer `.ps1`.** PowerShell 5.1 liest eine Datei ohne BOM
   als ANSI: `Verknuepfung` mit ue ist im Vergleich ein anderer Name, und ein
   `Remove-Item -LiteralPath` mit ausgeschriebenem Namen findet nichts -
   lautlos. Aufraeumen deshalb ueber Muster
   (`Get-ChildItem -Filter '*moongui.py*'`), nicht ueber Namen.

## Nachweis

Die Gegenprobe steht am Ende des Skripts und prueft je Verknuepfung, ob ihr
Ziel existiert (`Ziel-existiert=True`) und welches Arbeitsverzeichnis gesetzt
ist. Ein Klick auf die Verknuepfung ist kein Nachweis - der Fenstertitel ist
es: `Handelszentrale - 39 Spuren (Papier, nur lesend)` bzw.
`Zentrale · Repos · Werkstatt · Handel`.
---
name: archiv
description: Durchsucht Max' eigenes Dateiarchiv (Bilder, Videos, Musik, Dokumente) per Volltextsuche mit OCR. Immer VOR einer Internetsuche benutzen, wenn es um eigene Unterlagen gehen könnte — Rechnungen, Verträge, Belege, Anleitungen, Notizen, Rezepte, Fotos, Screenshots, Musik. Auch bei Fragen wie "wo war nochmal", "hab ich das irgendwo", "finde die Rechnung von", "welches Dokument".
---

# Archiv durchsuchen

## Wann

Bei jeder Frage, deren Antwort in Max' eigenen Unterlagen liegen könnte. Im
Zweifel: erst hier suchen, das kostet einen Aufruf. Erst wenn nichts kommt oder
die Frage allgemeines Weltwissen braucht, ins Internet.

## Wie — zuerst der Server

Der MCP-Server `archiv` beantwortet die Suche in **einem** Aufruf, ohne venv und
ohne Pfadgefummel: `archiv_suchen` (Suche), `archiv_datei_lesen` (Volltext einer
Fundstelle), `archiv_statistik` (Umfang und Indexdatum), `posteingang_stand`.

Das ist der kürzere Weg und wird trotzdem selten genommen: In 53 Sitzungen
kam der Server auf **acht** Aufrufe, während 462 Befehle dieselbe Arbeit über
die Kommandozeile erledigten (gemessen 28.08.2026, siehe [[Werkzeuge]]).

## Wenn der Server nicht da ist

Taucht `mcp__archiv__*` nicht in der Werkzeugliste auf — etwa in einer
CLI-Sitzung außerhalb der Desktop-Anwendung —, geht es über die Kommandozeile.
Vom Vault-Wurzelordner aus:

```powershell
Archiv\ArchivSuche\.venv\Scripts\python.exe Archiv\ArchivSuche\search_cli.py "suchbegriff"
```

Läuft die Sitzung bereits in `Archiv/`, entfällt das führende `Archiv\`.

Optionen:

- `--category Dokumente` — einschränken auf `Bilder` | `Videos` | `Musik` | `Dokumente`
- `--limit N` — Anzahl Treffer (Standard 5)

## Suchbegriffe wählen

Die Suche ist eine Volltextsuche, kein Sprachmodell. Deshalb:

- **Nicht** die Frage des Nutzers wörtlich übergeben („wo ist meine Rechnung von
  der Autowerkstatt letztes Jahr").
- **Sondern** die tragenden Begriffe: `Autowerkstatt Rechnung`, notfalls in zwei
  Läufen `Werkstatt` und `Inspektion`.
- Bei null Treffern einmal mit einem allgemeineren Begriff nachfassen, bevor du
  aufgibst. Danach ehrlich sagen, dass nichts im Archiv liegt.

## Wenn nichts gefunden wird, obwohl etwas da sein müsste

Wahrscheinlich sind seit dem letzten Lauf Dateien dazugekommen. Dann einmal neu
indexieren:

```powershell
Archiv\ArchivSuche\.venv\Scripts\python.exe Archiv\ArchivSuche\index.py
```

Das dauert und schreibt viel Ausgabe — nur die letzten Zeilen lesen
(`| Select-Object -Last 5`), nicht den ganzen Lauf.

## Nicht im Index

`Archiv/Software/` ist bewusst ausgenommen (Installationsdateien, ELSTER-Zertifikate).
Dort nicht suchen und nichts daraus verschieben.

# Digitales Archiv – Struktur

Zentrale Ordnerstruktur zum Sammeln, Ordnen und Katalogisieren aller digitalen Medien und Dateien.
Ziel: ein durchsuchbares, KI-gestütztes Nachschlagewerk – vor jeder Internetsuche wird zuerst hier geschaut.

## Aufbau

```
Bilder/
Videos/
Musik/
Dokumente/
├── Gewerblich/
│   ├── Rechnungen/
│   ├── Angebote/
│   ├── Bedienungsanleitungen/
│   ├── Sonstige Dokumente/
│   └── Maks Sound/
└── Privat/
    ├── Rezepte/
    ├── Bedienungsanleitungen/
    ├── Wohnen/
    ├── Gesundheit/
    ├── Ausbildung Tischler/
    ├── Finanzen und Versicherungen/
    ├── Vertraege/
    ├── Behoerden und Ausweise/
    ├── Fahrzeug-KFZ/
    ├── Bewerbung/
    └── Studium/
```

Weitere Ordner können jederzeit im Explorer angelegt werden – Suche und
Posteingang-Sortierung erkennen sie automatisch (siehe unten).

## Konventionen

- **Bilder / Videos / Musik**: Rohmedien, unabhängig von Dokumenten.
- **Dokumente/Gewerblich**: alles rund um "Maks Sound" und sonstige geschäftliche Unterlagen.
- **Dokumente/Privat**: persönliche Unterlagen, thematisch sortiert.
- Neue Unterkategorien nach Bedarf ergänzen, statt Dateien in "Sonstige Dokumente" zu sammeln.

## Ort der Daten

Seit dem 07.09.2026 liegen `Bilder/`, `Videos/`, `Musik/`, `Dokumente/`,
`Software/` und `Posteingang/` physisch auf `O:\Archiv\` (keine Junction mehr).
`ArchivSuche/` und die Steuerdateien bleiben auf `C:`. Die Werkzeuge finden die
Daten über die Umgebungsvariable `ARCHIV_ROOT`.

## Such-Tool

`ArchivSuche/` indexiert diese Ordner (Volltext + OCR) und macht sie durchsuchbar –
per Kommandozeile (für Claude) und per lokaler Web-Oberfläche (`Suche_starten.bat`).
Details: [ArchivSuche/README.md](ArchivSuche/README.md). Siehe auch [CLAUDE.md](CLAUDE.md).

## Posteingang

`Posteingang/` ist der Drag-and-Drop-Ordner: Dateien reinziehen, dann per Klick auf
„Posteingang einsortieren“ (Weboberfläche) oder `python sort_inbox.py` automatisch
in die passenden Ordner oben einsortieren lassen.

## Nächster Schritt

Ordner mit echten Dateien befüllen (per Posteingang oder direkt).

## Hinweis

`FocusTimer/` und `Worktrees/` (sowie `.claude/`) sind bestehende Ordner aus einem früheren
Coding-Projekt in diesem Verzeichnis und wurden nicht angetastet.

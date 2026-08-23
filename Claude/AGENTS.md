# Digitales Archiv

## Schutzregeln (verbindlich)

`Dokumente/`, `Bilder/`, `Videos/`, `Musik/` sind Originale ohne Zweitquelle —
lesen ja, schreiben nein. Nicht löschen, nicht verschieben, nicht umbenennen,
außer Max ordnet es in derselben Sitzung für genau diese Datei an. Soll etwas
weg: nach `Posteingang/_zu_loeschen/` verschieben, entschieden wird von Hand.
Kein Git, keine Historie — vollständig in
[Wissen/Schutzregeln.md](../Wissen/Schutzregeln.md).

## Überblick

Dieser Ordner ist Max' zentrales digitales Archiv (Bilder, Videos, Musik, Dokumente)
mit einem lokalen Such-Tool in `ArchivSuche/`. Siehe [README.md](README.md) für die
Ordnerstruktur.

## Wichtig: Archiv-Suche zuerst nutzen

Bevor du für eine Anfrage von Max eine Internetsuche (WebSearch/WebFetch) startest,
prüfe zuerst, ob die Antwort bereits in seinem eigenen Archiv liegt (eigene
Rechnungen, Anleitungen, Verträge, Notizen, Rezepte usw.):

```
cd ArchivSuche
.venv\Scripts\python.exe search_cli.py "suchbegriff"
```

Optional mit Filter: `--category Dokumente` (Bilder | Videos | Musik | Dokumente),
`--limit N`.

**Findet die Stichwortsuche nichts, semantisch nachsuchen** (seit 19.08.2026):

```
.venv\Scripts\python.exe vektor_suche.py "frage in eigenen worten"
```

Die Volltextsuche braucht das richtige Wort, die semantische die richtige
Bedeutung. Beispiel: „wie schuetze ich Lautsprecher vor Ueberlastung" findet den
Peak-Limiter-Abschnitt in einem gescannten Handbuch, in dem weder „schuetzen"
noch „Ueberlastung" vorkommt. Umgekehrt ist die Volltextsuche bei Aktenzeichen,
Rechnungsnummern und Eigennamen zuverlaessiger — `--hybrid` zeigt beides.

Der Vektorindex deckt nur Dateien mit mindestens 200 Zeichen Text ab
(1076 von 7631). Details: [ArchivSuche/VEKTORSUCHE.md](ArchivSuche/VEKTORSUCHE.md).

Erst wenn beide nichts liefern oder die Frage allgemeines Weltwissen verlangt,
mit Internetsuche fortfahren.

Falls seit dem letzten Lauf neue Dateien hinzugekommen sind und die Suche nichts
findet, wo eigentlich etwas erwartet wird, zuerst neu indexieren:

```
.venv\Scripts\python.exe index.py
.venv\Scripts\python.exe vektor_index.py    # danach auch den Vektorindex
```

## Posteingang

Max zieht neue Dateien einfach in `Posteingang/`. Wenn er dich bittet, den
Posteingang einzusortieren (oder du dort Dateien vorfindest, die noch nicht in
der Archiv-Struktur liegen), führe aus:

```
cd ArchivSuche
.venv\Scripts\python.exe sort_inbox.py
```

Dateien, die das Skript nicht sicher zuordnen konnte, bleiben im Posteingang
liegen (Ausgabe zeigt Grund + Vorschau) – lies den Inhalt und verschiebe sie
dann selbst gezielt in den passenden Unterordner von `Dokumente/` (oder
`Bilder/`/`Videos/`/`Musik/`), statt sie zu raten. Danach `index.py` laufen
lassen, falls `sort_inbox.py` das nicht schon automatisch getan hat.

## Was nicht im Index ist

Der Ordner `Software/` (Installationsdateien Linux/Windows) ist bewusst vom Index
ausgenommen. Die verwertbaren Inhalte der dortigen iCloud-Sicherung (Dokumente,
Bilder, Musik, Videos) wurden bereits ins Archiv übernommen; zurückgeblieben sind
nur Software-Reste sowie – bewusst unangetastet – Max' ELSTER-Zertifikate (`.pfx`).

Die beschädigten PDFs aus dieser iCloud-Sicherung (639 Stück, reine 0xFF-Füllbytes
ohne jeden Inhalt – fehlgeschlagene iCloud-Downloads) wurden gelöscht. Die im
Posteingang verbliebenen PDFs sind alle intakt; sie ließen sich nur inhaltlich
nicht sicher einer Kategorie zuordnen – das ist keine Fehlfunktion der Sortierung.

Details zum Tool (Aufbau, OCR, Web-Oberfläche, Sortierregeln): [ArchivSuche/README.md](ArchivSuche/README.md)

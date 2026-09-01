# Archiv-Suche

Durchsucht die Ordner `Bilder/`, `Videos/`, `Musik/`, `Dokumente/` im Archiv-Root
(Volltext aus PDF/Word/Excel/Text, Musik-Tags, OCR für Bilder/Scans falls installiert)
und legt einen lokalen SQLite-Volltextindex an.

## Musikbibliothek zusammenführen (`musik_zusammenfuehren.py`)

Für den Fall einer zerstreuten/zerstörten Musiksammlung: dasselbe Stück liegt
mehrfach vor – anderer Dateiname, anderes Format, andere Qualität, teils falsche
Tags. Namensvergleich hilft da nicht.

```
# Nur untersuchen, nichts verändern:
python musik_zusammenfuehren.py analyse "D:\Musik" "E:\Backup\Musik"

# Beste Fassung je Stück als AIFF erzeugen:
python musik_zusammenfuehren.py zusammenfuehren "D:\Musik" --ziel "D:\Musik_bereinigt" --dry-run
python musik_zusammenfuehren.py zusammenfuehren "D:\Musik" --ziel "D:\Musik_bereinigt"

# Zusätzlich offizielle Metadaten online abgleichen (kostenloser Schlüssel von acoustid.org):
python musik_zusammenfuehren.py zusammenfuehren "D:\Musik" --ziel "D:\Musik_bereinigt" --online --acoustid-key DEIN_SCHLUESSEL
```

**Wie es Duplikate erkennt:** über den akustischen Fingerabdruck (Chromaprint),
nicht über Dateinamen. Verglichen wird die Bit-Übereinstimmung der Rohfingerabdrücke
mit Ausgleich kleiner Zeitversätze; die Spieldauer dient als Vorfilter. Ab 88 %
Übereinstimmung gilt es als dieselbe Aufnahme (identische Aufnahmen liegen typisch
bei 95 %+, verschiedene Stücke bei ~50 %).

**Qualitätsreihenfolge:** verlustfrei schlägt verlustbehaftet, danach zählen
Bittiefe, Abtastrate, Bitrate, Kanäle.

**Metadaten:** Pro Feld wird aus allen Duplikaten der häufigste Wert genommen
(bei Gleichstand der vollständigste) – so ergänzen sich die Kopien gegenseitig.
Mit `--online` werden nur Lücken und Widersprüche über AcoustID/MusicBrainz
aufgelöst; ein einhelliger lokaler Wert bleibt bestehen.

**Ausgabe:** verlustfreies AIFF (16 oder 24 Bit, je nach Quelle) mit vollständigen
ID3v2-Tags. Wichtig: Der AIFF-Muxer schreibt ohne `-write_id3v2 1` nur den Titel,
aber weder Interpret noch Album/Jahr/Genre – die Option ist daher fest gesetzt.

**Sicherheit:** Alle Originale wandern in `<ziel>/_Duplikate`, nichts wird gelöscht.

Benötigt: `fpcalc` (Chromaprint) und `ffmpeg`/`ffprobe` – beide installiert;
das Skript findet sie auch, wenn der PATH nach einer winget-Installation noch alt ist.

## Ordner vergleichen & Duplikate bereinigen (beliebige Laufwerke)

`ordner_abgleich.py` – unabhängig vom Archiv nutzbar, z. B. um doppelte
„Dokumente“-Ordner auf verschiedenen Laufwerken zu bereinigen:

```
# Nur vergleichen, nichts verändern:
python ordner_abgleich.py vergleich "O:\Documents" "G:\Documents"

# Unikate aus Sekundär nach Primär kopieren (mit Verifikation),
# bei Namenskonflikt gewinnt die neuere Datei:
python ordner_abgleich.py zusammenfuehren "O:\Documents" "G:\Documents" --dry-run
python ordner_abgleich.py zusammenfuehren "O:\Documents" "G:\Documents" --loeschen
```

Nutzt für die Dateierfassung PowerShell statt Python (`pathlib.stat()` macht
unter Windows einen Systemaufruf pro Datei und wird bei zehntausenden
Dateien – vor allem auf externen Platten mit vielen kleinen Dateien wie
Sample-Bibliotheken – unbrauchbar langsam bis hängend; PowerShells
`Get-ChildItem` schafft dieselbe Menge in Sekunden). Massenlöschungen laufen
über `robocopy /MIR` von einem leeren Ordner statt `Remove-Item -Recurse`,
das bei großen Baumstrukturen spürbar langsamer ist.

## Posteingang – automatisches Einsortieren

`../Posteingang/` ist der Drag-and-Drop-Ordner: Dateien einfach reinziehen.
Per Klick auf **„Posteingang einsortieren“** (Weboberfläche) oder
`python sort_inbox.py` (Kommandozeile) werden sie automatisch anhand von
Dateityp und erkannten Schlüsselwörtern (z. B. "Rechnung", "Mietvertrag",
"Zutaten", "Kfz") in die passenden Ordner verschoben und der Index aktualisiert.

Bilder werden zusätzlich per OCR geprüft: sieht ein Bild wie ein gescanntes
Dokument aus (z. B. eine fotografierte Rechnung), wird es wie ein Dokument
einsortiert statt nach `Bilder/`.

Dateien, die sich nicht sicher zuordnen lassen, bleiben unangetastet im
Posteingang liegen und werden mit kurzer Begründung/Vorschau aufgelistet –
diese am besten von Hand einsortieren oder Claude fragen.

## Nutzung für dich

Doppelklick auf **`Suche_starten.bat`** öffnet die Such-Oberfläche im Browser
(`http://127.0.0.1:8756`, nur lokal erreichbar). Über den Button
**„Index aktualisieren“** wird neu eingelesen, über **„Posteingang
einsortieren“** wird der Posteingang automatisch verteilt.

Suchergebnisse lassen sich direkt öffnen oder im Explorer anzeigen.

## Nutzung für Claude (Kommandozeile)

```
cd ArchivSuche
.venv\Scripts\python.exe search_cli.py "suchbegriff"
.venv\Scripts\python.exe search_cli.py "suchbegriff" --category Dokumente --limit 5
```

Index manuell (neu) aufbauen:

```
.venv\Scripts\python.exe index.py          # inkrementell, nur neue/geänderte Dateien
.venv\Scripts\python.exe index.py --full   # alles neu extrahieren
```

Der Index ist inkrementell: unveränderte Dateien (Größe + Änderungsdatum gleich)
werden übersprungen, gelöschte Dateien automatisch aus dem Index entfernt.

## Unterstützte Dateiformate

- **Dokumente** (Volltext): PDF, Word, Excel, PowerPoint, OpenDocument, Text/Markdown/CSV
- **Bilder** (Volltext per OCR): JPG, PNG, HEIC/HEIF, GIF, BMP, TIFF, WebP
- **Musik** (Tags): MP3, FLAC, WAV, AIF/AIFF, M4A, OGG, AAC, Opus, WMA
- **Videos**: MP4, MOV, AVI, MKV, MPG/MPEG, FLV, WMV, WebM, 3GP
- **Musikprojekte** → Maks Sound: Ableton (.als), FL Studio (.flp), Cubase, Pro Tools
- **CAD/Konstruktion**: bleiben im Posteingang, da inhaltlich nicht lesbar –
  sie werden gezielt von Hand einsortiert

## Feste Sortierregeln nach Dateinamen

Unabhängig vom Inhalt gilt (in `sort_inbox.py`, `PREFIX_RULES`):

- `Rechnung_*` → `Dokumente/Gewerblich/Rechnungen`
- `Angebot_*` → `Dokumente/Gewerblich/Angebote`

Weitere Masken lassen sich dort einfach ergänzen.

## Eingebaute Sicherungen

`sort_inbox.py` trifft mehrere Entscheidungen von sich aus, damit ein Lauf
nichts Wertvolles überschreibt oder falsch ablegt. Der Kontext in
`Archiv/CLAUDE.md` verweist hierher statt die Zahlen zu kopieren.

### Duplikate – der Inhalt entscheidet, nicht der Name

Landet beim Einsortieren eine Datei auf einen bereits vorhandenen Namen,
entscheidet der **Inhalt** (Größe + SHA1), nicht das Änderungsdatum: bei
Byte-Gleichheit wird die Posteingang-Kopie gelöscht, die Archivdatei bleibt.
Weicht der Inhalt ab, wird **nichts** gelöscht – die neue Datei wird als
"(2)" abgelegt. Früher entschied das Änderungsdatum; das hätte in einem Lauf
1001 gleichnamige, aber inhaltlich verschiedene Icon-Dateien blind abgeräumt.

### Icons landen nicht in `Bilder/`

`.ico`, `.icns`, `.cur`, `.ani` immer. PNG und SVG dann, wenn sie quadratisch
(±2 %), höchstens 512 px groß und unter 64 KB sind → `Software/Windows/Icon`.
Größe **und** Maße müssen zutreffen, sonst wäre ein kleines echtes Foto
betroffen. Die 64-KB-Schwelle ist an den echten Daten gemessen: sie erfasst
1151 von 1152 bekannten Icons, ohne einen einzigen zusätzlichen Fehltreffer
bei den 2927 echten Bildern im Archiv. Maße werden ohne Bildbibliothek direkt
aus dem PNG-Header bzw. dem `<svg>`-Tag gelesen (`ICON_*` in `sort_inbox.py`).

### Zertifikate und Schlüssel werden nie automatisch verschoben

Entscheidend ist die **Endung**, nicht der Dateiname – ein ELSTER-Zertifikat
heißt schlicht `Ann21_elster_….pfx` und enthält kein verräterisches Wort:
`.pfx`, `.p12`, `.pem`, `.key`, `.jks`, `.keystore`, `.crt`, `.cer`, `.kdbx`,
`.kdb`, `.asc`, `.gpg`, `.ppk`, `.ovpn` (`SENSITIVE_EXTS`). Zusätzlich Namen
mit `passw`, `kennwort`, `credential`, `secret`, `private key`
(`SENSITIVE_NAME_PATTERNS`). Solche Dateien werden gemeldet und bleiben liegen.

### Build-Artefakte werden übersprungen

`.pyc`, `.pyo`, `.pyd`, `.toc`, `.pyz` sowie alles unterhalb von
`__pycache__/`, `build/`, `dist/`, `.venv/`, `.egg-info`, `node_modules/`,
`.app/`, `__MACOSX/` (`SKIP_EXTS` / `SKIP_PFAD_MUSTER` in `sort_inbox.py`).
`.spec` bleibt bewusst drin – die Datei gehört zum Quellcode.

## Geschwindigkeit

Indexierung und Posteingang-Sortierung laufen parallel auf mehreren
Prozessorkernen (bis zu 12, mit Reserve für den Rest des Systems). Nur das
tatsächliche Verschieben/Schreiben in die Datenbank läuft nacheinander im
Hauptprozess, damit sich nichts gegenseitig überschreibt. Effekt: eine
Indexierung, die einkernig Stunden brauchte, dauert jetzt Sekunden bis wenige
Minuten.

## Was indexiert wird

Alle Ordner auf oberster Ebene werden automatisch erfasst – auch neu angelegte.
Ausgenommen sind (`EXCLUDE_DIRS` in `index.py`):

- `Software/` – Installationsdateien und eine iCloud-Sicherung (rund 48.000 Dateien,
  kein Archivinhalt; mit ihnen dauerte ein Indexlauf Stunden statt Sekunden)
- `Posteingang/`, `ArchivSuche/` sowie alte Projektordner

Soll ein Ordner wieder aufgenommen werden, einfach aus `EXCLUDE_DIRS` entfernen.

## Dateien

- `index.py` – Indexer (Metadaten + Volltext + OCR)
- `search_cli.py` – Kommandozeilen-Suche
- `sort_inbox.py` – sortiert `Posteingang/` automatisch in die Archiv-Struktur ein
- `sort_ordner.py` – sortiert lose Root-Dateien in einem BELIEBIGEN Ordner (auch
  außerhalb dieses Archivs, z.B. auf anderen Laufwerken) in Themen-Unterordner
  ein, die direkt dort angelegt werden. Reine Dateiname-Klassifizierung, rührt
  bestehende Unterordner nicht an, lässt Zertifikate/Zugangsdaten und Dateien mit
  Hinweisen auf nicht jugendfreie Inhalte unangetastet liegen. Aufruf:
  `python sort_ordner.py "Pfad\Zielordner" --dry-run` (Testlauf) bzw. ohne
  `--dry-run` zum tatsächlichen Einsortieren, `--details` für die volle Liste.
- `server.py` – lokaler Webserver + JSON-API
- `static/index.html` – Such-Oberfläche
- `archiv_index.db` – SQLite-Index (wird automatisch erzeugt/aktualisiert)
- `.venv/` – Python-Umgebung mit allen Abhängigkeiten

## OCR für Scans/Bilder

Tesseract OCR ist installiert (`C:\Program Files\Tesseract-OCR`) mit Sprachpaketen
Deutsch + Englisch im lokalen `tessdata/`-Ordner dieses Projekts. Texterkennung in
Bildern/gescannten Rechnungen läuft automatisch bei jedem Indexlauf mit – auch für
PDFs ohne Textebene (reine Scans).

**Rückfall bei Scan-PDFs (seit 10.08.2026).** `pypdf` liefert bei bildbasierten
PDFs 0 bis 30 Zeichen; solche Dateien waren im Volltextindex leer und nur über
den Dateinamen auffindbar. Bleibt die Ausbeute unter **100 Zeichen je gelesener
Seite**, rendert der Indexer die Seiten mit `pypdfium2` bei 200 dpi zu Bildern
und schickt sie durch dieselbe Tesseract-Routine wie Bilder. Übernommen wird das
Ergebnis nur, wenn es länger ist als der direkt extrahierte Text. Grenzen:
maximal 20 Seiten, 180 Sekunden je Datei, 30 MB Dateigrösse (`OCR_MAX_MB`),
20 Sekunden je Seite. In `files_meta` steht dann `extract_status = ok_ocr` und
`ocr_used = 1`.

Eine gerenderte Seite wird über ihre **Breite** begrenzt, nicht über die längste
Kante. `thumbnail()` zieht bei ungewöhnlich hohen Seiten die Breite mit herunter:
das Xcube-Handbuch (710 × 2129 pt) landete so bei 68 dpi, und die Texterkennung
fand null Zeichen auf einer voll bedruckten Seite. Mit Breitenbegrenzung sind es
8.610 Zeichen.

## Robustheit

Mehrere Schutzmechanismen verhindern, dass eine einzelne Datei den ganzen Lauf blockiert:

- Tesseract wird als eigener Prozess mit hartem Zeitlimit aufgerufen (die Python-Anbindung
  konnte hängende OCR-Prozesse unter Windows nicht zuverlässig beenden)
- Bilder werden vor der Texterkennung auf 2000 px verkleinert – für Textkennung
  ausreichend und um ein Vielfaches schneller als Handyfoto-Auflösung
- PDFs: maximal 60 Seiten und 60 MB, beschädigte Dateien werden übersprungen; die
  Texterkennung als Rückfall ist zusätzlich auf 20 Seiten und 180 s je Datei begrenzt
- Der Index wird alle 25 Dateien zwischengespeichert; ein Abbruch verwirft nicht den ganzen Lauf
- Die Datenbank läuft im WAL-Modus: Suchen funktionieren auch während eines Indexlaufs
- Gesperrte Dateien (z. B. in Excel geöffnet) werden übersprungen statt den Lauf abzubrechen

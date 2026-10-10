# Eine Parallelsitzung ins Wiki spiegeln — Fallunterscheidung und Belege

Tiefe zu `fremdarbeit-uebernehmen`, Schritt 4. Der Byte-Weg macht das Schreiben
einfach; die Messungen davor und die Fallen danach entscheiden, ob die
Ablage stimmt.

## Zeilenenden messen, nicht annehmen

Das Haus ist nicht zeileneinheitlich. Der Anhaenge-Weg leitet das Zeilenende aus
dem ROHEN Text ab, aber die Messung entscheidet, welche Form die neue Zeile
bekommt und ob `numstat` danach ueberhaupt eine kleine Zahl zeigt:

```bash
python - <<'PY'
for p in ['MaxHirn/Wiki/Handel/Lektionen.md', 'MaxHirn/Wiki/Werkzeuge/Hermes-Wartung.md']:
    b = open(p, 'rb').read()
    print('%-46s crlf=%4d lf=%4d' % (p, b.count(b'\r\n'), b.count(b'\n')))
PY
```

Gemessen im Haus: `Lektionen/` und `Betrieb/` durchgehend **LF**,
`Werkzeuge/Hermes-Wartung.md` LF, `Werkzeuge/Marktdaten-…md` **CRLF**,
`MaxHirn/Archiv/TASKS.md` **gemischt**. Ein gemischtes File braucht die
Entscheidung ausdruecklich (`--crlf`/`--lf`), nicht nach Majoritaet.

## Frontmatter-Schluessel und INDEX

`updated:` und `stand:` sind gemischt, manche Seite hat gar keinen YAML-Kopf.
**Lesen, nicht raten:** `Lektionen/*` und `Betrieb/*` tragen `updated:`,
`Werkzeuge/*` ueberwiegend `stand:`.

Beim Erweitern einer Seite wird die **INDEX-Zeile mitverbreitert**, nicht nur
bei einer neuen Seite ergaenzt — die Zeile beschreibt die Seite und muss sagen,
was dazugekommen ist. Sonst zeigt der Index auf eine Seite, deren Umfang er
nicht mehr wiedergibt.

## Was in den Commit gehoert und was nicht

| Inhalt | eigener Commit? |
|---|---|
| Wiki-Seite (neu oder erweitert) | ja |
| `INDEX.md`-Zeile | ja, im selben Commit |
| fremde Skills, Werkzeuge, Referenzdateien | nein — unter „nicht angefasst“ nennen |
| Scratch-Skript und Commit-Meldung | nein (Scratch, nicht versioniert) |
| `TASKS.md`, juenger als 10 Minuten | nein — gehoert der anderen Sitzung |

## Fallunterscheidung beim Lock

| Beobachtung | Befund | Schritt |
|---|---|---|
| `File exists`, Datei beim Messen schon weg | Wrack einer beendeten Operation | einmal wiederholen |
| `File exists`, 0 Byte, 0 echte `git.exe` ohne `fsmonitor` | verwaistes Lock | `Move-Item -Force` umbenennen, nie loeschen |
| `File exists`, ein echter `git.exe` laeuft | laufender Commit einer anderen Sitzung | warten |
| `could not open .git/MERGE_HEAD` | andere Sitzung zieht gerade | pruefen, ob mein Inhalt schon in HEAD ist |

PowerShell: `Get-CimInstance Win32_Process -Filter "Name='git.exe'"` und
`CommandLine -notlike '*fsmonitor*'` — **nicht** `str(pid) in stdout` vom
`tasklist`, das antwortet fuer jede vergebene PID mit einer Zeile.

## Weitere Fallen

- **`patch` normalisiert den Frontmatter-Schluessel und sonst nichts.** Nach
  jedem Patch `git diff --numstat` lesen: eine Zeile geplant = wenige Zahlen,
  die ganze Datei = Kodierung verstellt.
- **`write_file` verweigert das Ueberschreiben ohne vollstaendigen Vor-Les** und
  gibt dann `None` statt `bytes_written` zurueck — der anschliessende `git add`
  nimmt still die alte Fassung. Bei `bytes_written: null` den Schritt wiederholen.
- **Ein Skript mit `open(p,'w')` schneidet die Datei beim Oeffnen ab**, bevor
  die erste Assertion fallen kann. Deshalb Inhalt ZUERST zusammenbauen,
  `assert ergebnis != alt`, und `open(p,'wb')` in der letzten Zeile.
- **Nach dem Schreiben selbst lesen.** Ein Schreibwerkzeug kann Nicht-ASCII
  einschleusen, das die Formdatei verstellt; `bytes_written` bestaetigt nur die
  Landung, nicht den Inhalt.
- **Beim Einfuegen per Byteslice die Schnittgrenze aus der LAENGE des Kopfes
  rechnen, nie aus einer hartkodierten kleinen Zahl.** `b[:7]` statt
  `b[:len(kopf)]` kuerzt den Kopf (`## Offen` -> `## Offe`) und zerstoert die
  Datei, ohne dass ein Fehler faellt. Nach dem Schreiben `assert
  open(p,'rb').read().startswith(kopf)` als Gegenprobe. War die Datei vorher
  clean gegen HEAD, holt `git checkout HEAD -- <datei>` sie verlustfrei zurueck
  und der Insert wird mit der korrekten Grenze wiederholt — nie auf dem
  kaputten Stand weiterbauen.
- **Block innerhalb DERSELBEN Datei verschieben: die Einfuegeposition erst
  NACH dem Entfernen berechnen.** Ein vorher berechneter Index zeigt nach dem
  Schnitt in die Mitte eines anderen Eintrags (T-380 landete mit 5-Spaces-
  Einrueckung im Block T-382). Und die Schnittgrenze des Entfernens
  Zeile-fuer-Zeile pruefen: ein `find` auf den naechsten Block-Marker kann eine
  Whitespace-Only-Zeile des Nachbarn mitnehmen, die dann fremd attribuiert
  wird — der Diff zeigt sie, byte-genau zurueckholen.
- **Verweigert `write_file` trotz vollstaendigem Vor-Les weiter** (der
  Partial-View-Zustand bleibt nach einem frueheren `offset`-Lesen haengen),
  hilft kein weiterer write_file-Versuch: den ganzen Inhalt in Python
  zusammenbauen (`assert b'\r' not in neu`), mit `open(p,'wb')` schreiben und
  `git diff --numstat` pruefen.
- **Die Fremdarbeit-Routine sammelt ein, was 30 min liegt** und attribiert es
  einem „Anderen Sitzung"-Commit. Wer seine Arbeit nicht selbst committet,
  verliert die Zuschreibung — das ist die Faustregel, nicht nur beim Spiegeln.
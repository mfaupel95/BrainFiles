# Eine Waechter pruefen — Muster und Fallunterscheidung

Tiefe zu `wirkung-nachweisen`, Abschnitt „Pitfalls“. Waehrend eine Waechter
gemeldet wird, ist die Frage nie „ist der Dienst tot", sondern **was genau hat
der Waechter gesehen**. Ein Waechter, der sein Ziel nicht findet, meldet
Stille — dieselbe Stille, die „alles gesund" bedeutet.

## Die drei Zustaende, die gleich aussehen

| Beobachtung | Gesunder Lauf | Ziel fehlt | Wirkungsloser Schalter |
|---|---|---|---|
| Ausgabe des Kindes | leer | **leer** | gefuellt, aber ohne Wirkung |
| Exitcode | 0 | **0** | 0 |
| `returncode` geprueft | — | **nein** (genau das ist der Fehler) | ja |

Die zweite Spalte ist die Wette, an der ein Waechter stirbt: `subprocess.run`
auf einen fehlenden Pfad liefert **leere Ausgabe statt eines Fehlers**, und
`capture_output=True` schluckt auch einen Fehlercode, den niemand liest.

## Muster 1: der Werkzeugpfad

```python
# FALSCH - HIER ist die Datei, der Pfad zeigt ins Leere
HIER = Path(__file__).resolve()
ZIEL = HIER / "wache.py"              # -> <datei>/wache.py, ein VERZEICHNIS

# RICHTIG - der Ordner ist der Anker
HIER = Path(__file__).resolve()
SCRIPTS = HIER.parent
ZIEL = SCRIPTS / "wache.py"

# auch richtig - dann ist HIER selbst der Ordner
HIER = Path(__file__).resolve().parent
ZIEL = HIER / "wache.py"
```

Geprueft wird der Pfad, BEVOR er benutzt wird, und ein Fehlercode des Kindes
ist eine Ausnahme:

```python
if not ZIEL.is_file():
    raise FileNotFoundError("Waechter fehlt: %s" % ZIEL)
r = subprocess.run([...], capture_output=True, text=True)
if r.returncode != 0:
    raise RuntimeError("Waechter endete mit %d" % r.returncode)
```

Im Aufrufer gehoert die Ausnahme in einen **gemeldeten** Zweig (Exit 2), nie in
den stillen.

## Muster 2: der Zaehlmuster beim Zaehlen

```python
# FALSCH - zaehlt dieselbe Teilmenge zweimal
vorhanden = len(alt) + len(alle_dateien)      # alt ⊂ alle_dateien

# RICHTIG - eine Groesse aus der Menge, im Schleifenkopf
vorhanden = 0
for datei in dateien:
    vorhanden += 1
    if zu_alt(datei):
        alt.append(datei)
```

Jede Groesse, die aus einer Menge folgt, wird aus der Menge **berechnet**.
Zwei Zaehlstaende zu addieren, von denen einer die Teilmenge des anderen ist,
verschiebt jede daraus abgeleitete Zahl (Luecke, geschaetzte Laufzeit). Der
Fund kam hier nicht aus der Messung, sondern aus einem Test, der `30 - 3 = 27`
rechnet und 24 bekommt.

## Muster 3: Gegenprobe statt Beschreibung

Ein Test, der eine Regel prueft, muss **rot werden koennen**. Zwei Formen:

```bash
# Form A: Regel im Werkzeug veraendern
cp werkzeug.py /tmp.bak
sed -i 's/^MAX_ALTER_TAGE = 5$/MAX_ALTER_TAGE = 10 ** 9/' werkzeug.py
python -m unittest test_wache        # muss ROT werden
cp /tmp.bak werkzeug.py               # zurueck, muss wieder GRUEN sein

# Form B: Fehlerfall in den Test einbauen
# dieselbe Regel, ein Wert bekannt verschieden
```

Ohne die Gegenprobe hat der Test den Fehler **beschrieben**, nicht gefunden.

## Fallunterscheidung: welcher Befund ist es?

| Beobachtung | Befund | Naechster Schritt |
|---|---|---|
| Ausgabe leer, Ziel existiert nicht | Fehlpfad | Pfad ueber den Ordner bauen, `is_file()` pruefen |
| Ausgabe leer, Ziel laeuft, Wirkung fehlt | Wirkungsloser Schalter | Werkzeugweg pruefen, nicht die Daten |
| Exitcode != 0, Ausgabe ignoriert | Verschluckter Fehler | `returncode` lesen, in Ausnahme wandeln |
| Ausgabe gefuellt, Zahl falsch | Zaehler/Doppelzaehler | Groesse aus der Menge rechnen |
| Nur im Worktree rot | Umgebungsartefakt | dieselben Suiten im HAUPTBAUM fahren |

**Ein Watchdog darf seinen Befund nie aus einer Still ableiten**, die er nicht
selbst geprueft hat: „leer heisst gesund" und „leer heisst kaputt" sind
dieselbe Beobachtung.

## Was ein Auditor melden darf

Ein Auditor meldet die **FORM**, nicht den Zustand: „diese Datei baut ihren
Werkzeugpfad aus einem Datei-Anker", nicht „dieses Werkzeug fehlt". Die zweite
Aussage waere ein Befund ohne Beleg. Werkzeug:
`Agenten/Hermes/scripts/audit-werkzeugpfad.py --ordner <ordner>` (Exit 1 =
Befund, Exit 0 = sauber), mit Test `test_audit_werkzeugpfad.py`.

**Breite zuerst messen, dann verengen.** Ein Muster, das elf Wachen meldet,
von denen die ersten zwei den Fehler aktiv abfangen, ist schlimmer als keines —
es trainiert den Leser darauf, die Meldung zu uebergehen. Wer einen Auditor
verwirft, schreibt die Begruendung in den Commit: welche Datei, welche Zeile,
warum der Befund falsch war.
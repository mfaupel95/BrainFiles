# Eine Änderung über ALLE Spuren ausrollen

Auslöser: „das gilt für alle Spuren", „Bedingung 4 überall", ein Befund, der
mehrere Spuren betrifft, oder ein neuer Kosten-/Ausstiegsgrund, der nicht in
einer Spur stehen bleiben darf. Erprobt am 13.09.2026 (Journal außer Haus für
acht Spuren, von denen nur zwei kopierten).

Zweites erprobtes Beispiel, diesmal mit **einem zentralen Schalter** (Faktor auf
alle Beträge, zweite Dateinamen, eigener zweiter Dauerlauf):
`references/risikostufen.md` — dort steht auch, was dabei ausdrücklich NICHT
mitwandern darf (Marktdaten, Messwerte, der Spiegel).

Der Ablauf ist immer derselbe: **Inventar → Ziel(e) → Code-Anker → Tests →
echter Lauf → Automatik-Nachweis → Doku → Commits**. Kein Schritt darf
übersprungen werden, weil der vorige grün aussah — genau die Reihenfolge
macht den Unterschied zwischen „sieht fertig aus" und „ist fertig".

## 1. Inventar ziehen, nicht erinnern

```
search_files: pattern "<symbol>" path Agenten/Handel file_glob *.py
search_files: pattern "<feld>"   path Agenten/Handel
```

Je Spur aus den **Dateien** lesen, was gilt (`wachen.json`, `zustand.json`),
nicht aus dem Kopf. Für Bedingung 4 direkt:
`journal-spiegelung/scripts/spiegelstand-pruefen.py` (Ziel + Kopiestand +
Herzschlag aller Spuren in einer Tabelle).

Aus dem Inventar eine Tabelle bauen: *Spur → hat Aufruf? hat Ziel? Ziel wohin?*
Der häufigste Befund ist eine **halbe** Verdrahtung: Feld gesetzt, aber niemand
kopiert — oder Aufruf vorhanden, Ziel `null`.

## 2. Stufe 1: sichern, dann ändern

- Vor jeder Datei unter `Agenten/Handel/` ein `.bak-JJJJMMTT` anlegen.
  Existiert schon eins von heute, **nicht überschreiben** — dann
  `.bak-JJJJMMTT-vor-<thema>` (das ältere bleibt erhalten).
- Versionierte Dateien zusätzlich über den Verlauf absichern:
  `git show HEAD:Agenten/Handel/<spur>/<datei>` ist der echte Vorher-Stand,
  wenn der Arbeitsbaum committet war.
- `.bak`-Dateien gehören nicht in den Commit (Whitelist-`.gitignore` deckt sie).

## 3. Ziele setzen — exakt, nicht neu geschrieben

`wachen.json` nie per `json.dump` komplett neu schreiben: Kommentarzeilen
(`_zweck`, `_journal_zweitziel`) gehen verloren, Schlüsselreihenfolge und
Zeilenenden ändern sich, `git diff` zeigt die ganze Datei.

Stattdessen **byte-genau ersetzen** (Skript über `execute_code`):

- Vorher prüfen: `raw = open(p,"rb").read()`, `b"\r\n" in raw` — Zeilenenden
  feststellen und im Ersatz mitführen (`swap/wachen.json` ist CRLF, alle
  anderen hier LF).
- Muster als Raw-String, Trefferzahl auf `1` asserten, danach `json.load` — die
  Datei muss weiter parsen.
- **Das fuzzy `patch`-Werkzeug re-indentiert CRLF-JSON** und kann dabei in einem
  Aufruf mehrere Zeilen auf 8 Spaces ziehen statt sauber eine zu loeschen
  (getroffen an `swap/` und `xperp/`, beide CRLF). Zeile vorher mit `repr()`
  bauen, Loeschung byte-exakt per Regex: `re.subn(br'^[ \t]*"<key>":\s*<wert>,\r?\n', b"", raw, count=1)`
  und nachher `json.loads`. Kronzeuge dafuer, dass eine json-Aenderung gelandet
  ist, ist der Diff: eine entfernte Zeile muss als `-` ZEILE und nur als solche
  erscheinen, nicht als Umformatierung des umgebenden Blocks.
- **Jede Spur bekommt einen eigenen Zielordner.** Ein Ziel, das auf den Ordner
  einer anderen Spur zeigt, ist eine Zeitbombe: gleiche Dateinamen, der
  zweite Schreiber überschreibt die Kopie der ersten Spur (so stand `swap` auf
  `...\xperp`).
- Fehlt der Schlüssel ganz (omniquant, spiegel), ihn mit Kommentarzeile an
  passender Stelle einfügen — nicht nur den Wert.
- Bei jeder Änderung an `wachen.json` gilt die Hausregel: eigener Commit,
  `.bak` vorher, echter Lauf danach, die Zahlen in der Commit-Nachricht.

## 4. Code-Anker setzen — mit Beweis, nicht mit Gefühl

Alle Ersetzungen in **einem** `execute_code`-Lauf, je Paar `(alt, neu)`:

1. `count == 1` asserten (Mehrfachtreffer oder verrutschte Stelle fällt sofort
   auf, statt als stiller Doppelersatz durchzugehen).
2. Schreiben mit `newline=""`, damit LF/CRLF erhalten bleiben.
3. Danach `ast.parse` über die neue Datei.

Dabei gilt:

- **Alle Zyklenpfade erwischen, nicht nur den Normalweg.** In jeder Spur gibt
  es den Normalabschluss UND Notausstiegs-Zweige (Kill-Switch, alter
  Herzschlag), die vorzeitig `return`en. Der Notausstieg gehört erst recht
  außer Haus. Muster: `if w.get("journal_zweitziel"): _spiegeln(w)` unmittelbar
  nach `schreibe_zustand(z)` / `vermerke…`.
- **Erst schreiben, dann kopieren.** Herzschlag und Journal müssen stehen,
  bevor etwas auf ein externes Laufwerk zugreift.
- **Reihenfolge prüfen: Vorschau darf nicht schreiben.** Eine `--vorschau`, die
  den Zustand setzt, erzeugt je Zyklus einen zweiten Herzschlag (der
  Dauerlauf fragt jede Spur zusätzlich mit `--vorschau` ab) und lässt die
  Kopie älter aussehen als den eigenen Zustand.
- Die Rechnung nur **einmal** im Haus halten und über den Dateipfad laden
  (`importlib.util.spec_from_file_location`), wenn das Zielmodul in einem
  fremden venv liegt oder gleichnamige Module existieren — nie einen zweiten
  Ordner auf `sys.path` legen, in dem `okx.py`/`handeln.py` liegen.
- **Den Haken dorthin setzen, wo der Betrieb liest.** Ein Faktor, Filter oder
  Schalter gehört in die Funktion, die Betrieb UND Werkzeug gemeinsam benutzen
  (`lade_wachen()` / `wachen()`), nicht in `lauf()` oder `main()`. Sonst muss
  der Test nachbauen, was der Lauf tut, und prüft danach die Nachbildung statt
  der Spur. Gegenprobe: die Spurendatei per `importlib` laden und IHRE Funktion
  befragen — eine im Test wiederholte Formel beweist nur die Formel.
- **Pfadtyp erhalten.** Beim Umbiegen von Dateinamen (`datei()`) muss aus `str`
  wieder `str` und aus `Path` wieder `Path` werden: die Spuren benutzen beide
  Formen, und `.read_text()`/`.exists()` auf einem zurückgegebenen `str` fällt
  erst im Zyklus auf, nicht beim Start.

## 5. Tests richtig aufrufen (und die Zahl nennen)

```
cd Agenten/Handel/<spur> && PYTHONPATH=. <venv-python> -m unittest discover -s tests -t tests
```

Fallen beim Aufruf:

- **Einzeln gestartete Testdateien laufen ins Leere.** `python -m unittest test_session`
  aus `<spur>/tests` scheitert mit `ModuleNotFoundError: No module named 'session'` —
  die Spurenmodule liegen im Ordner DARUEBER, den nur die Sammlung auf den Pfad legt.
  Nie einzeln starten.
- **`-t .` ist der erste Versuch, `-t tests` der Rueckfall.** Hat `tests/` ein
  `__init__.py` (orb, orbk), laeuft
  `cd Agenten/Handel/<spur> && <venv-python> -m unittest discover -s tests -t . -p "test_*.py"`;
  ohne `__init__.py` scheitert `-t .` mit **„Start directory is not importable"**,
  und dann ist `-t tests` (mit `PYTHONPATH=.`) richtig. Die Meldung sieht wie ein
  Testfehler aus, obwohl gar nichts lief.
- **Einzeln gestartete Testdateien laufen gegen das falsche Modul.** Bei
  gleichnamigen Modulen zweier Spuren (`handeln.py`, `auswertung.py`, `gui.py`)
  liefert `import handeln` das zuerst gefundene — ein Test kann deshalb
  fehlschlagen, obwohl der Code richtig ist, und umgekehrt grün sein, ohne den
  eigenen Code zu prüfen. Deshalb die **Sammlung** laufen lassen und die
  Testzahl aus der Ausgabe im Bericht nennen.
- Die richtige Zahl ist die der Sammlung: `Ran 61 tests … OK` schlägt jede
  Summe von Teilläufen (im Zweifel beide Zahlen prüfen; eine Teillauf-Summe,
  die als Gesamtzahl im Commit steht, ist ein Fehler im Beleg).

## 6. Echter Lauf je Spur und byte-genaue Prüfung

```
cd Agenten/Handel/<spur> && <venv-python> <skript>.py --papier
then: vergleiche handelsjournal.csv und zustand.json byte-genau mit dem Ziel
```

- Die Kopie trägt die **Quell-mtime** (`copy2` erhält die Metadaten) — das
  Alter der Kopie ist also kein Beweis für den Kopierzeitpunkt. Inhalt
  vergleichen, nicht Zeitstempel.
- Ein Datenvergleich per Zeile/`json.load` reicht nicht: **byte-genau** (`cmp`,
  in Python `open(...,"rb").read()`) prüfen. Nur so fällt ein
  Zeilenende- oder Reihenfolgeunterschied auf.
- Ganze Spur-Tabellen mit einem Aufruf prüfen:
  `journal-spiegelung/scripts/spiegelstand-pruefen.py`.

## 7. Den Automatikpfad beweisen, nicht nur den Handstart

Ein Handstart beweist den Handstart. Der Dauerlauf startet jede Spur als
**Unterprozess** — ein neuer Zyklus genügt, es braucht **keinen Neustart**
des Dauerlaufs (im laufenden Prozess steht nur `SPUREN` selbst).

1. Nächsten Zyklus abwarten (Takt steht in der Kommandozeile des laufenden
   Prozesses, meist `--takt 15`).
2. Im Bus-Journal nachsehen: `Bus/journal/<JJJJ-MM-TT>.jsonl`, je Spur
   `start` + `ende` mit `code: 0`.
3. Danach erneut byte-genau vergleichen. Erst dann ist die Änderung bewiesen.

Das zeitliche Fenster gehört in den Bericht („letzter automatischer Zyklus
22:12:58–22:13:50, alle Codes 0").

## 8. Doku — drei Orte, keiner ersetzt den anderen

- **README der Spur**: Abschnitt mit Ziel, Reihenfolge (erst Herzschlag, dann
  Kopie), Sichtbarkeit im Zustand.
- **Wissensnotiz** (`Wissen/`): der Stand über alle Spuren — und veraltete
  Aussagen derselben Notiz mitrichten (`journal_zweitziel: null` stand dort
  noch, als es längst gesetzt war). `updated:` im Frontmatter mitziehen.
- **Skills**: den Fach-Skill (z. B. `journal-spiegelung`) und den Sammel-Skill
  (`handel-spuren`) fortschreiben, wenn sich Mechanik oder Wahrheit geändert
  hat. Ein Skill, der den alten Stand behauptet, ist schlimmer als keiner.

## 9. Commits — getrennt nach Regel, gepusht je Repo

- `wachen.json`-Änderung: **eigener** Commit, nie mit anderer Arbeit gebündelt,
  `.bak` vorher, echter Lauf danach.
- Code + Tests + README: zweiter Commit.
- Wissensnotiz: dritter Commit.
- Ein Spur-Repo mit **eigenem `.git`** (nautilus) wird separat committet und
  gepusht — der Sammel-Commit erreicht es nicht.
- Zum Schluss je Repo `git log --oneline -1 origin/<zweig>` gegen `HEAD`
  stellen: erst wenn beide dieselbe Zeile zeigen, ist es gespeichert.

## Fallen

- **Das `freigabe`-Tor entscheidet nur das Feld `erfuellt`; `min_wochen`/
  `min_runden`/`netto_positiv` sind Doku, keine Sperren.** Live bleibt gesperrt,
  solange `erfuellt` nicht von Hand gesetzt ist — ein entfernter
  `papierlauf_min_runden`-Wert oeffnet also KEINEN Live-Pfad (die Wachen-lesenden
  Pfade in freigabe.py und wachen_pruefung.py prüfen nur `erfuellt`). Wird ein
  solches Schwellwert-Feld entfernt, ist das eine Doku-Aenderung, kein
  Sicherheits-Eingriff: im Abschlussbericht so benennen und die
  `erfuellt=false`-Sperre weiter ausweisen. Umgekehrt, in die andere Richtung:
  ein leuchtendes Feld (`netto_positiv: true`) ohne gesetzten Haken fuehrt
  trotzdem nicht zu Live. Wer die Freigabebedingung selbst lockern will, setzt
  den Haken — nicht die Zahl daneben.
- **Testzyklen spiegeln mit.** Faehrt ein Test den vollen `lauf()` und patcht
  dabei nur `ZUSTAND`/`JOURNAL` auf Temp-Pfade, kopiert die Spiegelung die
  **Temp-Datei an das echte Ziel** — die gute Kopie außer Haus ist danach durch
  einen Teststand ersetzt (im Zielordner liegen plötzlich 200-Byte-Dateien mit
  fremden Positionen). Gegenmittel: das Wachen-Fixture im Test muss ein
  **Temp-Ziel** tragen (oder `None`) — nicht die echte `wachen.json`-Kopie mit
  Q:-Ziel verwenden. Wer nur „Ziel existiert" prüft, sieht das nie.
- **Ein Treffer ist kein Stand.** Der `ok`-Rückgabecode des Laufs sagt nichts
  über die Kopie; sichtbar ist der Ausfall nur über den Vermerk im Zustand
  (`journal_zweitziel_ok`/`_info`) — und der muss im Zustand **stehen**, nicht
  nur gedruckt werden (der Dauerlauf protokolliert bei Code 0 nur „ok").
- **Fremde Schreiber.** An diesem Baum arbeiten mehrere Sitzungen. Weicht eine
  Kopie ab, zuerst die **Zeitstempel** beider Seiten ansehen und im Bus-Journal
  nach Aufrufen suchen, die nicht aus dem eigenen Lauf stammen — statt den
  eigenen Code zu verdächtigen. Erst danach ändern.
- **Der häufigste fremde Schreiber ist der eigene Testlauf.** Ein von Hand
  gestarteter Dauerlauf lebt als **Prozesspaar** weiter (venv-Shim + echtes
  Python), auch wenn er beendet aussieht — vor dem nächsten Start über die
  Kommandozeile nachsehen, nicht über den Prozessnamen:
  `Get-CimInstance Win32_Process -Filter "Name like 'python%'" | Where-Object { $_.CommandLine -like '*dauerlauf.py*' }`.
  Danach die PID-Datei mitnehmen (`dauerlauf.<stufe>.pid`), sonst meldet der
  Wächter fälschlich „läuft bereits". Waren zwei Schreiber auf denselben
  Büchern, sind deren Zahlen wertlos: verwerfen (lokal UND am Zweitziel) und neu
  beginnen — die Basisdateien bleiben unangetastet.
- **Modulnamen-Kollisionen** (zwei `handeln.py`, zwei `auswertung.py`, `gui.py`):
  über den Dateipfad laden und die Fixtures der Tests mitziehen.
- **Keine Behauptung über fremde Spuren im Code** — Zustand lesen, nicht
  schreiben, was „alle Spuren" tun.

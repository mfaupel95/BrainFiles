# Brief-Vorlagen und Schnellpruefungen fuer ein Code-Audit

Vier Vorlagen. Jede ist **eine Zeile Prosa** fuer `goal` und `context` — der
Parser des Dispatchers stolpert ueber eingebettete Zeilenumbrueche, escaped
Anfuehrungszeichen und verschachtelte Schemata im Context, und ein Kind mit
`output_schema` auf einem Auftrag mit Prosa-Werkzeugen reformatiert endlos.

## 1. Der Nur-Lesen-Vertrag (in jeden Context)

> Umgebung: Windows, das Terminal-Werkzeug laeuft in einer Sandbox auf
> demselben Host. Native Programme brauchen Pfade als C:/Users/... mit
> Schraegstrichen, MSYS-Pfade schlagen bei nativen Programmen fehl, cd als
> Bash-Befehl geht. Die Sandbox-Uhr geht rund sieben Stunden nach: Datum nie
> aus date nehmen, sondern aus Dateizeitstempeln oder git log. Viele Dateien
> sind CRLF. Eine parallele Sitzung arbeitet an denselben Dateien; fremde
> Arbeit wird nicht angefasst und nicht bereinigt: <Namen aufzaehlen>. Fuer
> den Handel: die Spuren duerfen unter keinen Umstaenden in ihre echten
> Ordner schreiben (Zustand, Journal, ablehnungen.csv), und handeln.py darf
> nicht im echten Modus laufen.

## 2. Der Auftrag (goal, vier Bereiche)

> Finde echte BUGS in <Bereich>. NUR LESEN, KEINE DATEI AENDERN, kein
> schreibender git-Befehl, kein Commit, kein Dienststart, kein
> schtasks create oder run. Untersuche <Umfang>. Suche nach <Fehlerklassen
> des Bereichs>. Fuer jeden Befund: Schwere, Datei:Zeile, was falsch laeuft,
> Beleg, minimale Fix-Idee in Prosa. Pruefe jeden Verdacht am echten
> Aufrufer im ganzen Baum, nicht nur im eigenen Ordner. Gegenprobe: schreibe
> kleine lesende Wegwerf-Skripte nach Agenten/Hermes/cache/scratch/ und
> fahre sie, damit der Befund nachweislich auftritt und nicht nur im Code
> steht. Antworte mit hoechstens zehn Befunden nach Schwere, Form:
> Schwere, Datei:Zeile, Fehlverhalten, Beleg, Fix-Vorschlag in Prosa.
> Unbelegtes kommt nicht in die Liste. Findest du nichts in einem
> Teilbereich, sage das ausdruecklich statt zu raten.

Fehlerklassen je Bereich (die Auswahl ist der eigentliche Auftrag). Die
Klassen, die sich als reine Verdrahtungspattern wiederholen, stehen mit
Beispielen in `references/fehlerklassen-verdrahtung.md`:

| Bereich | Typische Klassen |
|---|---|
| Orchestrierungskern | Logikfehler, tote Verzweigung, falsch verdrahteter Aufrufer, stille Ausnahme, Zeit-/Zonenfehler, Fehler bei leerem Input, **Betriebsmerkmal, das im Messweg nie ausloest** |
| Betrieb und Dienste | Nachrichtenverlust, haengender Thread, veralteter Zustand meldet gesund, PID-Pruefung ohne Programmnamen, Merkdatei verdeckt den Stand, unbalancierte Formatmarken, Laengengrenze, Test schreibt in Betriebsdaten |
| Viele gleichartige Einheiten | Rundenergebnis falsch (Gebuehr je Seite, Short-Vorzeichen, Prozent gegen Punkte, Einstiegskurs uebernommen statt geholt), toter `sys.path`-Import, Feld wird gelesen und nie geschrieben, Widerspruch zwischen zwei Listen im selben Baum, **Pfad eine Ebene daneben**, **hart gefuehrte Namensliste**, **Satz folgt der Historie statt dem Zustand** |
| Werkzeuge und Config | toter Defaultpfad, lesend aber nie schreibend (oder umgekehrt), falsche Rueckgabe, Race auf Statusdatei, ungepruefte Formatannahme, Widerspruch zwischen Manifest und Wirklichkeit, **Sonde meldet systematisch leer** (Pruefer-Fehler), **Cache beantwortet die Frage**, **Notiz entscheidet ueber eine Zahl** |

## 3. Die vier Schnellpruefungen (Eigenleistung, neben dem Dispatch)

Aus der Repo-Wurzel. Alle vier read-only, zusammen Sekunden.

**a) Python parst.**

```bash
cd /c/Users/faupe/Documents/BrainFiles && python -c "
import ast
from pathlib import Path
bad=[]
for d in ['Agenten/Handel','Agenten/Bus','Agenten/Hermes/scripts','Agenten/Werkzeuge']:
    for p in Path(d).rglob('*.py'):
        s=str(p)
        if '.venv' in s or 'OpenAlice' in s or 'site-packages' in s: continue
        try: ast.parse(p.read_text(encoding='utf-8',errors='replace'))
        except SyntaxError as e: bad.append((s,e.lineno,str(e)[:80]))
print('SYNTAXFEHLER:',len(bad))"
```

`SyntaxWarning` auf dem Weg (ungueltige Escape-Sequenzen) sammeln, aber nicht
als Befund melden — sie stehen in Fremdcode.

**b) PowerShell parst.**

```bash
pwsh -NoProfile -Command "
\$err=0
Get-ChildItem -Path 'Agenten/Routinen','Agenten/Werkzeuge' -Filter *.ps1 -Recurse -File |
  Where-Object { \$_.FullName -notmatch 'OpenAlice|\.venv' } | ForEach-Object {
  \$e=\$null
  [void][System.Management.Automation.Language.Parser]::ParseFile(\$_.FullName,[ref]\$null,[ref]\$e)
  if(\$e -and \$e.Count){ \$err++; Write-Output (\$_.Name + ' :: ' + \$e[0].Message) } }
Write-Output ('PS-PARSE-FEHLER: ' + \$err)"
```

**c) Stille Ausnahmen.** AST ueber `except:` (Typ `None`) und ueber Handler,
deren Rumpf nach Weglassen von `pass`/Docstring leer ist. Beide Klassen in
**eigenem** Code suchen, Fremdcode ausgenommen — `except: pass` in einem
Fremd-Repo ist kein Befund des Hauses.

**d) Verdrahtungslisten vergleichen.** Module **importieren**, Differenz
bilden, dann jeden Namen der Differenz pruefen:

1. Wird er am echten Aufrufer gelesen (Suche ueber den ganzen Baum, **ohne**
   `head` — eine abgeschnittene Trefferliste erzeugt genau das falsche
   „nichts gefunden")?
2. Steht im Modul eine **Prosa-Begruendung**, warum er fehlt? (Docstring,
   Fusszeile, Kommentar neben der Stelle)
3. Gibt es eine eigene Auswertung im Ordner des fehlenden Eintrags?

Erst wenn alle drei Fragen zugunsten eines Befundes ausfallen, wird er
gemeldet. Sonst als widerlegt notieren — die Zahl der widerlegten Kandidaten
gehoert in den Bericht.

## 4. Befund-Form, die den Nutzer erreicht

```
Schwere | Datei:Zeile | was falsch laeuft | ausgefuehrter Beleg | minimaler Fix in Prosa
```

- **Schwere** zuerst: rechnet Buch/Geld/Positionen falsch > Zustand meldet
  gesund, ist es nicht > Fehler in einer Meldung > Untot.
- **Beleg** ist ein ausgefuehrter Lauf, kein Zitat. Ein Codezitat ohne
  Gegenprobe geht als Befund nicht durch.
- **Fix in Prosa**, kein Diff: der Aufrufer entscheidet, nicht das Kind.
- **Rote Tests sind Befunde mit zwei Klassen.** Ein Test, der einen *gelegentlichen*
  Wert festhaelt (Boersensatz, Schalterstand, Zuordnung), ist eine **kaputte
  Pruefung** und wird auf die *Eigenschaft* umgebaut. Ein Test, der nach dem
  Fix rot wurde und die eigene Aenderung sichtbar macht, ist fast immer
  dasselbe. Nachweis in beiden Faellen: eigene Aenderung auf `HEAD`
  zuruecknehmen, Suite erneut fahren, Ergebnis festhalten. „Auf HEAD genauso
  rot" heisst vorbestehend und gehoert als eigene Zeile in den Bericht — nie
  als stille Korrektur.
- **Ein abgebrochener Laufliefert kein Ergebnis.** Eine Logdatei mit viel
  Ausgabe und ohne Zusammenfassungszeile ist kein Testresultat; immer auf die
  Zusammenfassung und den Exitcode pruefen, sonst gilt „unbekannt", nicht
  „gruen". Die Suite dann in Bloecke teilen und je Block fahren.
- Was **nicht** geprueft wurde, steht am Ende als eigener Abschnitt, nicht
  versteckt im Text.
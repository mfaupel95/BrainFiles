---
name: desktop-fenster
description: "Use when ein Desktop-Fenster gebaut oder geprueft wird."
version: 0.1.0
author: Hermes Agent
platforms: [windows]
license: MIT
metadata:
  hermes:
    tags: [oberflaeche, tkinter, layout, design, werkzeuge]
    related_skills: [repos-zentrale, handel-spuren, trugschluesse, wiki-pflege]
---

# Desktop-Fenster: bauen, aendern, lesbar machen

Die Haus-Fenster (`handelszentrale.py`, `leitstand.py`, `repos-zentrale/fenster.py`,
`omniquant/gui.py`) sind tkinter/ttk, dunkel, in derselben Palette und Schrift.
Farben, Schrift, Abstaende und ttk-Stile kommen aus EINER Datei:
`Agenten/Werkzeuge/fenster_design.py`. Wer dort etwas aendert, aendert alle
Fenster; wer daneben eigene Farben setzt, erzeugt einen Wartungsfehler.

## When to Use

- ein Fenster soll gebaut, umgebaut oder "lesbarer/schoener" gemacht werden
- ein Fenster zeigt abgeschnittene Texte, zu kleine Schrift oder ein unscharfes Bild
- eine neue Anzeige (Tabelle, Kopfzeile, Detailbereich) in ein bestehendes Fenster
- "warum ist das Fenster auf meinem Monitor unscharf / halb ausserhalb"
- ein Fenster soll aufgenommen und beurteilt werden (dann `scripts/fenster-foto.ps1`,
  gemessen wird trotzdem mit `messprobe.py`)

**Don't use for:** Web-Oberflaechen (`web-api-erkundung`,
`inspecting-hermes-desktop-dom`), Telegram-Berichte (`tagesbericht`), das
Startfenster selbst (`repos-zentrale`).

## Die eine Designquelle

`Agenten/Werkzeuge/fenster_design.py` importiert tkinter NICHT und ist damit
ohne Fenster pruefbar. Es liefert `FARBEN`, `SCHRIFT_ART`/`SCHRIFT_GROESSE`,
`ABSTAND`, `schrift(basis, rel, fett)`, `zeilenhoehe(basis)`,
`vorzeichen_farbe`, `dpi_bewusst()`, `skalierung(root)`,
`stil_anwenden(style, basis)`. Aufbau und Regeln:
`Werkstatt/design-system-fenster-*.md`.

Laden per **Dateipfad** (importlib), nicht ueber `sys.path`: ein Eintrag auf
`Werkzeuge/` wuerde dort liegende Module (`marktdaten.py`) einblenden und
gleichnamige in `Handel/` verdecken.

## Procedure

1. `dpi_bewusst()` **vor** dem ersten `Tk()` - sonst streckt Windows das fertige
   Bild und jede Schrift wird unscharf. Fehlertolerant halten (`except Exception`).
2. Einmal zentral gestalten: `design.stil_anwenden(ttk.Style(), BASIS)`. Alles,
   was nichts Eigenes setzt, erbt von `"."` - Einzel-Widgets nur fuer
   Abweichungen (fett, andere Groesse).
3. Anzeigelogik als **reine Funktionen** ueber der Klasse: Filter, Gruppen,
   Summenzeile, Textaufbau. Sie sind ohne Fenster pruefbar; die Klasse baut nur
   zusammen, was die Module liefern. Zahlen und Farbwahl gehoeren NICHT in
   `_bauen()`.
4. Farbe traegt Bedeutung (gruen/rot/gelb = Zustand), nie Dekoration - und
   Zustand nie NUR ueber Farbe, immer zusaetzlich als Text (`STARTBAR`, `FEHLT`,
   Vorzeichen).
5. Groesse und Lage im Bild halten (`winfo_screenwidth`/`-height`), die
   Startgroesse mit `skalierung()` strecken. Ein Fenster ausserhalb des Bildes
   ist kein Schoenheitsfehler, es ist unbenutzbar.
6. Rein lesende Fenster schreiben nichts - als Test festhalten (Muster:
   `Agenten/Handel/tests/test_handelszentrale_rein_lesend.py`).

## Layout in Zahlen (die Fehler, die jedes Mal auftreten)

- **Feste Pixelbreiten sind auf einem skalierten Monitor zu schmal.** Mit
  `dpi_bewusst()` setzt Tk die Schrift in Geraetepixeln: `winfo_fpixels('1i')`
  meldet dann z. B. 120 (Faktor 1,25), Consolas 11 hat 22 px Zeilenhoehe.
- **`stretch=True` (Tk-Vorgabe) verfaelscht jede gerechnete Breite.** Tk verteilt
  die Restbreite selbst, die Rechnung gilt dann nicht mehr (gemessen 191 statt
  125 px). Jede Spalte auf `stretch=False` setzen und Breiten ausdruecklich
  vergeben.
- Zeilenhoehe `max(18, Basis*2)` - darunter werden Buchstaben angeschnitten.
- Texte, die in eine Spalte sollen, auf die Spalte kuerzen, nicht die Spalte auf
  den Text wachsen lassen.

### Die eine Breitenregel (Textbedarf schlaegt Wunsch, Platz schlaegt beides)

Spaltenbreiten sind eine **reine Funktion ohne Fenster** - Muster
`handelszentrale.spaltenbreiten(spalten, kopf, wunsch, texte, zeichen_breite,
verfuegbar)`. Feste Pixelzahlen im Aufbau sind der Grund, warum Tabellen nach
einem Umbau oder einem Schriftwechsel ploetzlich abschneiden. Reihenfolge:

1. **Untergrenze je Spalte** = Überschrift und der schlimmste ihrer Texte, bei
   Consolas also `len(text) * zeichen_breite + rand`. Das ist keine Wunschzahl:
   ein Text, der nicht passt, wird still abgeschnitten.
2. **Wunsch** darueber, aber nie darunter. Der Wunsch ist eine Liste nach
   *Rangfolge*, kein Dict - im Aufruf `{"zeit": 260}` bedeutet „eine breite
   Spalte", nicht „alle Spalten 260". Ein Dict, das rueckwaerts vererbt, macht
   aus einer Ausnahme eine ganze Tabelle (+359 px gemessen).
3. **Kuerzen bis in den Platz**, von der letzten Spalte zuerst, in Runden bis
   nichts mehr geht. Ein einziger Durchlauf reicht nicht: kam am Ende noch
   Ueberhang, war er an den vorderen Spalten abgeschnitten.
4. Reicht der Platz auch fuer die Untergrenzen nicht, ist das die **waagerechte
   Leiste**, nicht ein Fehler.

**„ZU BREIT" unterscheidet zwei Sachen, und die Meldung muss es auch.** Brauchen
die Texte mehr als der Baum hergibt, ist Scrollen die richtige Antwort (Text
passt, nur der Platz reicht nicht). Sind die Spalten breiter als ihr Text
noetig, ist es der alte Fehler. Beide sehen in der Summe gleich aus. Die Sonde
sagt deshalb „ZU BREIT - der Text braucht es" gegen „kein UEBERHANG".

**Eine Breite, die nur nach dem Bauen gerechnet wird, ist die alte feste Breite
mit neuem Namen.** Beim Bauen ist die Tabelle leer; nachrechnen muss gegen die
**eingefuegten Zeilen** geschehen, und zwar in zwei Durchgaengen mit
unveraenderter Zeilenzahl - beim ersten war nicht alles gelesen. Eine leere
Tabelle wird trotzdem nach ihren Überschriften gerechnet (sie zeigt genau die).

**Die Zeichenbreite ist eine Messung, keine Konstante.** `8 px` je Zeichen ohne
`dpi_bewusst()`, `10 px` mit. Jeder Fall braucht einen **eigenen Prozess**:
`dpi_bewusst()` muss vor dem **ersten** `Tk()` laufen, sonst misst der zweite
Fall still falsch. Und der Nutzer waehlt die Schrift selbst - sie steht in der
Zustandsdatei des Fensters (Leitstand: `schrift`, 8..16) und die Messprobe
braucht sie als Parameter, sonst misst sie die Vorgabe und nicht den Alltag.

**Der Platz fuer die Kuerzung kommt aus `winfo_width()` - und Tk vermisst ein
neu gebautes oder noch nicht sichtbares Widget erst nach einem
`update_idletasks`, sonst liefert es `1 px` und die Kuerzung unterbleibt
grundsaetzlich.** Ein verborgenes Fenster ist schlimmer: es hat gar keine
Geometrie, die Sonde misst dann eine kleinere Baumbreite als das echte Fenster
und meldet einen Ueberhang, den es nicht gibt. Messfenster deshalb **sichtbar
ausserhalb des Bildschirms** positionieren, nicht `withdraw()`.

## Scrollen: die drei Fälle, die immer wieder auftreten

- **`height=<Anzahl Objekte>` ist kein Layout.** Eine Tabelle, die so viele
  Zeilen anfordert, wie es Daten gibt (gemessen: `height=len(SPUREN)` bei 42
  Spuren), ist hoeher als jedes Fenster — und mit `fill="x"` gepackt gibt es
  nichts zu scrollen, also ist der Rest der Seite unerreichbar. Muster
  `Agenten/Handel/handelszentrale.py`: `tabelle_mit_leiste(rahmen, spalten, kopf,
  breiten, hoehe=..., anker_w=..., dehnen=..., wahl=...)` baut senkrechte UND
  waagerechte Leiste und legt das Mausrad aufs Widget; `scrollbare_seite(eltern)`
  gibt `(wrapper, innen, canvas)` fuer Seiten, die hoeher sind als das Fenster.
- **`bbox("all")` liefert (0, 0, 1, 1), wenn nichts gemessen ist** — nicht None.
  Das als `scrollregion` zu setzen sieht nach Erfolg aus und ist ein
  1-Pixel-Weg; erst ab echter Hoehe setzen (`seite_region_neu`).
- **Das Rad landet auf dem Widget unter dem Zeiger, nicht auf dem Canvas.** Also
  an jede Tabelle einzeln binden UND die Nachfahren der Seite mitbinden; die
  eigenen Handler geben `"break"` zurueck, damit dieselbe Bewegung nicht noch
  einmal die Seite scrollt.

## Pruefen: messen, nicht schauen

Den Fensteraufbau in einen Test nehmen, der das Fenster wirklich baut: so
faellt ein Tippfehler in einem Widgetnamen auf, den reine Funktionstests nicht
sehen. Fuer **Geometrie** (Scrollen, `winfo_width()`) ist ein verborgenes
Fenster unbrauchbar - siehe Pitfalls.

Das Layout wird **gemessen**, nicht angesehen: Spaltenbreite gegen
`tkfont.measure(text)` je Spaltentext stellen und die zu schmalen zaehlen. Der
Befund lautet "N Texte zu schmal", nicht "die Tabelle ist zu breit" - die
Ueberhaenge liegen pro Zelle, nicht pro Spalte.

`scripts/tabellen-messprobe.py` ist die Fassung fuer **jedes** Fenster des
Hauses: `python tabellen-messprobe.py --fenster handelszentrale:Handelszentrale`
baut das echte Fenster, sammelt alle Treeviews unterhalb der Wurzel ein und
misst ohne einen Eingriff in den Fenstercode. Das Muster `modul:Klasse` macht
den Aufrufer zum Parameter, also braucht die Probe keine Kopie je Fenster.
Sonderfaelle der Probe:

  * Das Fenster **sichtbar** bauen und ausserhalb des Bildschirms
    positionieren. `root.withdraw()` erzeugt keine Geometrie - nicht nur
    `yview()` bleibt dort stehen, auch `winfo_width()` liefert eine Zahl, die
    kleiner ist als die des echten Fensters, und die Sonde meldet dann einen
    Ueberhang, den es nicht gibt.
  * Eine Tabelle, die im aktuiven Reiter NICHT sichtbar ist, hat
    `winfo_width() == 1`; ihre Spaltensumme wird ausdruecklich nicht als
    'ZU BREIT' gewertet - sie ist eine Vorgabe, kein Messwert. Fuer alle
    Reiter also einmal umschalten und messen.
  * `winfo_ismapped()` bleibt bei einer einmal gezeigten Notebook-Seite TRUE,
    auch wenn sie nicht mehr vorne liegt. Ohne eigene Pruefung wird dieselbe
    Tabelle unter jedem Reiternamen gezaehlt und die Summe ist das Zwei- bis
    Vierfache der echten Zahl. Die Zuordnung gehoert aus dem **Widget-Pfad**,
    nicht aus `nb.select()` - das steht beim Messen schon auf dem naechsten
    Reiter.
  * Nur **gezeichnete** Zeilen zaehlen (`baum.bbox(iid) is None` heisst: nicht
    sichtbar). Eine Tabelle haelt mehrere hundert Zeilen und zeigt eine mit
    `height=8`; alle zu zaehlen meldete 2276 statt der sichtbaren Zahl.
  * Die Schriftgroesse als Parameter anbieten und den **gespeicherten Wert**
    des Nutzers als Vorgabe nehmen, nicht den Modul-Default.

> Eine Bildbeschreibung ist kein Zeuge. Sie nennt fremde Programme und meldet
> Abschneiden, das die Messung widerlegt (gemessen: "Hinweis abgeschnitten" bei
> 350 px Text in einer 457-px-Spalte). Ein Layoutbefund kommt nur aus der Messung.

**Und die Sonde ist selbst die haeufigste Fehlerquelle.** Drei Befunde, alle am
Fenster nachgewiesen, alle drei in dieser Sonde:

- **Ein Zaehler ohne Abgrenzung zaehlt dasselbe mehrfach.** `winfo_ismapped()`
  bleibt bei einer einmal gezeigten Notebook-Seite TRUE; dieselbe Tabelle wurde
  unter vier Reiternamen gezaehlt (333 statt 124). Alle Zeilen einer Tabelle mit
  `height=8` zu zaehlen zaehlt auch die nicht gezeichneten (2276 statt der
  sichtbaren Zahl) - die Abgrenzung gehoert in den Zaehler, nicht in die
  Bewertung des Ergebnisses.
- **Ein Zustands-Check mit dem falschen Muster erkennt sich selbst.** `if
  "self._flag" in datei` war wahr, weil die Methode die Flag las, nicht weil die
  Zuweisung existierte. Immer auf die **Zeile der Zuweisung** pruefen.
- **Eine Zahl, die sich beim Umbau nicht bewegt, ist auch ein Befund.** Bleibt
  „ZU SCHMAL GESAMT" trotz sicherem Fix auf 0, ist die Sonde falsch, nicht die
  Rechnung.

Ein verdecktes Fenster laesst sich ohne Vordergrund aufnehmen:
`scripts/fenster-foto.ps1` sucht per `EnumWindows` nach dem Titelpraefix und
zeichnet es mit `PrintWindow` in eine PNG. Zwei Fallen darin: `FindWindow` mit
einem Titel, der Sonderzeichen enthaelt, findet nichts (ueber das Praefix
suchen), und ein Bildschirmfoto zeigt sonst das Fenster, das gerade obenauf liegt.

Zahl und Besitzer sichtbarer Fenster nennt `scripts/fenster-zaehlen.ps1`
(`-Liste` gibt Titel, PID und Prozess, `-Prozess <name>` filtert). Zaehlen ist die
Antwort auf "wieder viele Fenster offen": vor und nach einem Probelauf messen -
bleibt die Zahl gleich, hat der Aufruf kein Fenster geoeffnet. Nicht als
`powershell -Command "..."` aus bash aufrufen (die Shell frisst `$variable`),
sondern als Datei mit `-File`.

## Starten

- **Terminal-Fenster: `wt.exe` oeffnet je Aufruf ein NEUES Fenster.** Nach ein
  paar Klicks steht eine Sammlung offen und keins schliesst sich. Soll der Aufruf
  in einem vorhandenen Fenster landen, `wt.exe -w 0 -d <ordner> ...` verwenden -
  das legt einen Tab an (gemessen: Fensterzahl vor und nach dem Aufruf gleich).
  Dazu: **ein** Bauer je Zweck. Baut ein zweites Modul seinen `wt`-Aufruf selbst
  zusammen, wird es bei einer Reparatur uebersehen. `cmd.exe /k` haelt die
  Ausgabe lesbar; wer sie nicht braucht, nimmt `/c`, dann schliesst sich der Tab.
  Beleg statt Gefuehl: `scripts/fenster-zaehlen.ps1` vor und nach dem Klick.
- Fenster mit `pythonw.exe` starten (kein Konsolenfenster).
- Aus einer Agenten-Sitzung heraus per `Popen` starten, **nicht** per
  `cmd /c start` oder `Start-Process`: die melden Erfolg und sind beim Ende des
  Terminalaufrufs wieder weg. Danach in einem ZWEITEN Aufruf die Prozesszahl
  nachzaehlen - "gestartet" sagt nichts ueber "laeuft noch".
- **Vorher UND nachher zaehlen.** Ein gescheiterter Startversuch kann trotzdem
  ein Fenster hinterlassen (aus bash bricht `cmd.exe /c '<name>.cmd'` mit einem
  Syntaxfehler ab und startet das Programm dennoch) - beim naechsten Versuch
  stehen dann zwei Fenster offen. Gezaehlt wird mit PowerShell
  (`Get-Process <name>` bzw. `Get-CimInstance Win32_Process`), Duplikate werden
  nach **PID** beendet, nie nach Prozessname.
- **In bash keine `%VAR%`-Pfade.** `"%SystemRoot%\System32\tasklist.exe" /FI ...`
  wird von der Shell nicht expandiert und die Pruefung faellt still aus;
  `$SYSTEMROOT` benutzen oder gleich PowerShell fragen.
- Beenden nach PID, nie nach Prozessname: ein Musterfilter auf die eigene
  Kommandozeile trifft den Suchenden selbst.

## Desktop-Verknuepfungen (wie der Nutzer das Fenster erreicht)

Die Fenster bekommen je eine Verknuepfung auf dem Desktop - erzeugt von EINEM
idempotenten Skript (`Agenten/Werkzeuge/desktop-verknuepfungen.ps1`), nicht per
Hand geklickt. Ueber `WScript.Shell.CreateShortcut(<pfad>)` setzen:
`TargetPath`, `Arguments`, `WorkingDirectory`, `IconLocation`, dann `Save()` -
und danach auslesen und **pruefen, dass das Ziel existiert**
(`Test-Path $s.TargetPath`).

- **`WorkingDirectory` ist das entscheidende Feld.** Ohne es startet das
  Programm im falschen Ordner und findet seine Dateien nicht - genau daran
  entstehen die Desktop-Reste, deren NAME der ganze fehlgeschlagene Befehl ist
  (`CUsersfaupe...pythonw.exe repos_zentrale.py.txt`). Sie gehoeren mit weg,
  ebenso eine Verknuepfung auf ein DEAKTIVIERTES Ziel
  (`Startup\.disabled-JJJJMMTT\...`): das ist keine Verknuepfung, sondern eine
  Falle.
- **Ein Fenster ueber seinen WRAPPER starten, wenn es einen gibt** - er prueft
  den Fenstertitel und startet nichts, wenn schon ein Fenster offen ist. Zwei
  Fenster zeigen dasselbe und sind spaeter nicht von einem Dienst zu
  unterscheiden.
- **Zwei PowerShell-Fallen, beide erlebt:** (1) `$args` ist eine automatische
  Variable - ein Funktionsparameter dieses Namens laesst
  `$s.Arguments = $args` mit `System.Object[] kann nicht in string konvertiert
  werden` abbrechen (Parameter `$argumente` nennen). (2) **Keine Umlaute in einer
  `.ps1`**: PS 5.1 liest eine Datei ohne BOM als ANSI, ein
  `Remove-Item -LiteralPath` mit ausgeschriebenem Umlautnamen findet dann NICHTS
  und meldet keinen Fehler. Aufraeumen ueber Muster
  (`Get-ChildItem -LiteralPath $desktop -Filter '*<stueck>*'`), nie ueber
  ausgeschriebene Namen - und beim Loeschen Groesse und Pfad notieren.
- **Der Beweis ist der Fenstertitel, nicht der Klick:**
  `Get-Process pythonw | Where-Object { $_.MainWindowTitle }` und den Titel gegen
  die erwartete Zeile halten. Er nennt oft die Zahl der Objekte (`… - 39 Spuren …`)
  und ist damit zugleich die Gegenprobe fuer jede Zahl in der Doku.

## Reihenfolge bei einem Fensterumbau

**Vorher sichern.** Dreifaelle, alle an diesem Umbau: `git show HEAD:<pfad> >
<pfad>` fuer eine Gegenprobe hat die Arbeitsfassung zerstoert und eine
Sicherung, die eine Ebene zu tief lag, das Original mitgeloescht. Der
Weg zurueck war eine Kette idempotenter Umbau-Skripte (`cache/scratch/
wiederherstellen2.py`) - einzeln geordnete, lose Werkzeuge lassen sich nicht
mehr abspielen, weil der zweite Lauf am Anker des ersten scheitert. Vor dem
ersten Schnitt: Kopie neben der Datei, `assert os.path.isfile(...)`, und nach
jedem Schritt `git diff --numstat` (die gewollte Zeilenzahl, kein
Ganzdatei-Diff).

0. **Breite erst bestimmen.** Mehrere Fenster nebeneinander (Handelszentrale,
   Leitstand, Fremd-Repo-GUI) sind eine Aufgabe, kein Fenster: pro Familie ein
   **nur-lesender** Audit als Subagent, alle parallel, jeder mit dem Auftrag
   'Zeilennummer, Fehlverhalten, Gegenbeispiel, Schadensrichtung,
   Ein-Zeilen-Fix - und widerlege deine eigenen Ersterkennungen'. Kein
   Schreibzugriff, kein `git`: eine parallele Sitzung kann im selben Baum
   arbeiten. Der Umbau bleibt beim Hauptagenten, sonst gibt es drei
   auseinanderlaufende Aenderungen an derselben Datei.
1. **Erst messen, dann lesen.** Die Messprobe laufen lassen, BEVOR ueber die
   Datei gelesen wird. Wer von oben an liest, findet die breitesten Spalten
   zuerst und haelt sie fuer die Ursache; die Messung nennt in Sekunden die
   Zahl der Ueberhaenge und die eine Spalte, die zu breit ist.
2. **Reine Logik von der Klasse trennen, bevor man sie testet.** Fehlt die
   Trennung, ist jeder neue Test ein Fenster-Test - langsam und von der
   Maschinenlast abhaengig (228 Tests in 38 s bei gebautem Fenster, ein
   einzelnes Fenster 4 s).
3. **Layout in den BREITEN-Funktionen aendern, nicht in `_bauen()`.** Die
   Breiten sind eine Rechnung ueber Text und Platz, also eine reine Funktion.
4. **Breite auf Text, nicht auf Vorgabe.** Ein Spaltenname, der in keiner
   Zeile vorkommt, verbraucht Breite fuer nichts; eine Spalte mit 5-Summen-
   Text braucht mehr, als ihr Name erfordert.
5. **Nicht `height=len(...)`** (siehe Scrollen) und nicht auf den Reiter warten:
   ein Umbau, der nur im sichtbaren Reiter geprueft wurde, ist in den anderen
   ungeprueft - die Messprobe mit `--breite`/`--hoehe` deckt alle ab, wenn sie
   einmal je Reiter laeuft.
6. **Gegenprobe messen, nicht behaupten.** Nach dem Umbau dieselbe Probe mit
   der Zahl "ZU SCHMAL GESAMT: 0" belegen, und zwar bei ZWEI Fenstergroessen
   (1280 und 1000) - sonst ist der Umbau nur auf dem einen Monitor belegt.
7. **Bei JEDER Schriftgroesse messen, die der Nutzer waehlen kann.** Die
   Vorgabe des Moduls ist nicht sein Alltag - er speichert seine Wahl in der
   Zustandsdatei des Fensters. Gemessen: bei Schrift 11 (Vorgabe) 0
   abgeschnittene Texte, bei seiner gespeicherten Schrift 96.
8. **Jeden Messfehler als solchen benennen, bevor die Zahl zitiert wird.**
   Ein Befund aus einer Sonde, deren Fenster keine Geometrie hatte, ist kein
   Befund am Fenster.

## Pitfalls

- **Der patch-Werkzeug verschiebt die Einrueckung.** Beim Ersetzen eines
  Blocks mit ungleichen Spaces rueckt es den Ersatz um vier Stellen nach
  rechts und erzeugt `IndentationError`. Danach **nicht weiterpatchen** - zwei
  Versuche scheitern genauso. Die Datei vollstaendig mit `read_file` lesen
  (ohne `offset`/`limit`, sonst verweigert `write_file` die
  Ueberschreibung als "partial view") und mit `write_file` neu schreiben.
- **`.children` ist ein Tcl-Iterator, kein Tuple.** `len(baum.children)` und
  `baum.children or ()` ergeben still falsche Zahlen - im gemessenen Fall
  lieferte der Zaehler `(0, 0, 0)` fuer drei Tabellen mit 48, 96 und 6 Zeilen,
  und die Nachrechnung galt danach als "fertig". Immer
  `len(baum.get_children())`.
- **Ein Fremd-Repo-Fenster gehoert nicht in diese Bibliothek.** Liegt die
  Oberflaeche in einem geklonten Fremd-Repo (eigenes `upstream`, Fremdarbeit
  im Arbeitsbaum), wird sie dort geaendert und hier nur der Weg dorthin
  beschrieben - ein fremder SKILL wird nicht importiert und eine fremde Datei
  nicht ueber den Haus-Index committed.
- **`git show HEAD:<pfad> > <pfad>` zerstoert die Arbeitsfassung.** Wird es
  fuer eine Gegenprobe benutzt (alte Version gegen neuen Code testen), ist die
  eigene Aenderung danach weg - und eine Sicherung, die eine Ebene zu tief
  abgelegt war, loescht dabei das Original mit. Also: **vor** der Umleitung
  sichern, die Sicherung mit `assert os.path.isfile(...)` pruefen, oder die
  Gegenprobe in einem zweiten Arbeitsbaum fahren. Wer es doch tut, braucht
  einen Weg zurueck: eine Kette idempotenter Umbau-Skripte (jeder prueft
  zuerst, ob sein Ergebnis schon da ist, und bricht mit `assert` ab, wenn
  sein Anker fehlt) laesst sich mehrfach abspielen - einzeln geordnete,
  lose Werkzeuge nicht.
- Ein Messwerkzeug, das sich an die Fensterklasse bindet (Attribute des
  Fensters voraussetzt), muss beim Schreiben auf einen GEBAUTEN Bildschirm
  getestet werden. Platzhalter-Aufrufe, die nie liefen, sind Messwerkzeuge,
  die nichts messen.
- Farben oder Schrift daneben setzen, statt `fenster_design` zu benutzen.
- Zustand nur ueber Farbe zeigen (rot/gruen) - ein Farbenblinder oder ein
  Ausdruck sieht nichts.
- Die Statuszeile mit Text fuellen, der die Fensterbreite uebersteigt: sie
  schluckt den Rest stillschweigend. Lange Aufschluesselungen gehoeren in die
  Statuszeile (ganze Fensterbreite), nicht in die Kopfzeile neben Knopfe.
- Ein Fenster ohne `winfo_screenwidth`-Pruefung auf einem zweiten Monitor
  platzieren.
- Eine ganze Datei neu schreiben, um eine Spalte zu aendern: erst die reine
  Rechenfunktion aendern und mit einem Test festnageln, dann die Klasse anfassen.
- **`root.withdraw()` hat keine Geometrie.** `yview()` bleibt dort `(0.0, 1.0)`,
  auch mit 40 Zeilen in einer Fuenf-Zeilen-Tabelle — ein Test, der nach
  `yview_moveto` eine Bewegung verlangt, beweist Tk, nicht das Fenster. Geprueft
  wird die Verdrahtung (`yscrollcommand`, `xscrollcommand`, Rad-Bindung) und die
  gesetzte Scrollregion. Fuer eine **Messung** (Sonde, Breitenrechnung) ist
  `withdraw()` zusaetzlich schaedlich: `winfo_width()` liefert dann eine zu
  kleine Zahl, und jede daraus berechnete Breite ist zu breit.
- Zweimal derselbe Funktionsname in einer Datei: Python laesst die LETZTE
  Definition gewinnen, die fruehere ist tot und eine Aenderung daran wirkt wie
  keine. Als AST-Pruefer festhalten (Muster
  `tests/test_handelszentrale_struktur.py`), nicht als Blick.

## Verwandtes

- `repos-zentrale` - das Startfenster, nutzt dieselbe Designquelle.
- `handel-spuren` - Spuren und ihre Anzeige im Handelsfenster.
- `wiki-pflege` - Lehren aus einem Fensterumbau gehoeren ins Wiki.

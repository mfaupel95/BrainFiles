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

## Layout in Zahlen (die zwei Fehler, die jedes Mal auftreten)

- **Feste Pixelbreiten sind auf einem skalierten Monitor zu schmal.** Mit
  `dpi_bewusst()` setzt Tk die Schrift in Geraetepixeln: `winfo_fpixels('1i')`
  meldet dann z. B. 120 (Faktor 1,25), Consolas 11 hat 22 px Zeilenhoehe.
  Spaltenbreiten also aus der WIRKLICHEN Widget-Breite und
  `design.skalierung(root)` rechnen; beim Kuerzen zuerst die Nebenspalten, dann
  die Hauptspalte, zuletzt die Spalte, die den Grund traegt.
- **`stretch=True` (Tk-Vorgabe) verfaelscht jede gerechnete Breite.** Tk verteilt
  die Restbreite selbst, die Rechnung gilt dann nicht mehr (gemessen 191 statt
  125 px). Jede Spalte auf `stretch=False` setzen und Breiten ausdruecklich
  vergeben - mit Abzug fuer Rollbalken und Innenrand (rund 40 px), sonst laeuft
  die letzte Spalte aus dem Fenster; die Restbreite bekommt die breiteste
  Textspalte.
- Zeilenhoehe `max(18, Basis*2)` - darunter werden Buchstaben angeschnitten.
- Texte, die in eine Spalte sollen, auf die Spalte kuerzen, nicht die Spalte auf
  den Text wachsen lassen.

## Pruefen: messen, nicht schauen

Den Fensteraufbau in einen Test nehmen, der das Fenster wirklich baut und
unsichtbar laesst (`root.withdraw()` + `update()`): so faellt ein Tippfehler in
einem Widgetnamen auf, den reine Funktionstests nicht sehen.

Das Layout wird **gemessen**, nicht angesehen: Spaltenbreite gegen
`tkfont.measure(text)` je Spaltentext stellen und die zu schmalen zaehlen.
Muster: `Agenten/Werkzeuge/repos-zentrale/messprobe.py` - baut das Fenster,
druckt jede Breite und nennt die Zahl der zu schmalen Texte.

> Eine Bildbeschreibung ist kein Zeuge. Sie nennt fremde Programme und meldet
> Abschneiden, das die Messung widerlegt (gemessen: "Hinweis abgeschnitten" bei
> 350 px Text in einer 457-px-Spalte). Ein Layoutbefund kommt nur aus der Messung.

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
- Beenden nach PID, nie nach Prozessname: ein Musterfilter auf die eigene
  Kommandozeile trifft den Suchenden selbst.

## Pitfalls

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

## Verwandtes

- `repos-zentrale` - das Startfenster, nutzt dieselbe Designquelle.
- `handel-spuren` - Spuren und ihre Anzeige im Handelsfenster.
- `wiki-pflege` - Lehren aus einem Fensterumbau gehoeren ins Wiki.

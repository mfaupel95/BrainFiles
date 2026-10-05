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

**Die Quelle selbst pruefen, nicht nur ihre Benutzung.** Farbe, Schrift und
Kontrast sind Behauptungen, bis man sie nachrechnet. Zwei Handgriffe, beide
ohne Fenster:

1. **Kontrast gegen WCAG 2.1 rechnen.** Fuer jedes Paar, das im Haus wirklich
   vorkommt (Flaeche x Schrift, Datenflaeche x Nebenspalte, Zellhintergrund x
   Text, Auswahl x Text) das Verhaeltnis `(L1+0.05)/(L2+0.05)` aus der
   relativen Leuchtdichte bilden und gegen 4.5 (Fliesstext) bzw. 3.0 (gross)
   halten. Muster `Agenten/Handel/kontrast_messen.py` (reines Rechnen, keine
   Bildschirm noetig). Ein Wert knapp ueber der Grenze ist der Befund - nicht
   der schoenste Wert im Set.
2. **Die Schrift begruenden, nicht nur setzen.** Eine FESTBREITE Schrift
   (Consolas) fuer Zahlenspalten ist eine Wahl mit Grund und gehoert als solcher
   kommentiert. Eine Vorgabe- oder Systemschrift (Inter, `system-ui`) ist der
   Anti-Slop-Befund "Vorgabe statt gewaehlt" und braucht dieselbe Begruendung
   oder einen Ersatz.

Ein fremder Web-Design-Skill ersetzt diese Quelle nicht: siehe
`fremde-skill-sammlung-einbinden`, Abschnitt "Medienpassung pruefen".

## Procedure

1. `dpi_bewusst()` **vor** dem ersten `Tk()` - sonst streckt Windows das fertige
   Bild und jede Schrift wird unscharf. Fehlertolerant halten (`except Exception`).
   **`tk scaling` ist kein Ersatz dafuer, sondern ein anderer (schlechterer)
   Hebel.** `tk scaling N` aendert nur Tk-interne Punkte in Pixel; WINDOWS weiss
   weiterhin nicht, dass die Anwendung dpi-aware ist, und stretcht das fertige
   Bitmap. Gemessen auf einem 120-dpi-Monitor: `SetProcessDpiAwareness` ->
   `winfo_fpixels('1i')` 119, `skalierung` 1.25, System 3840x2160; ohne ->
   Faktor 1.0, System **3072x1728 = 36 % weniger Bildschirm**, Schrift 8 statt
   10 px je Zeichen. Beides zusammen ergibt 1.666 statt 1.25 - der
   `scaling`-Aufruf macht die dpi-Absicht also zunichtemachen. Faellt er weg,
   wenn `dpi_bewusst()` gesetzt ist. Als Aufruf im `main()` **einer** Fenster
   geht er kaputt, sobald das Fenster als Reiter in ein anderes eingebettet
   wird (`main()` laeuft dort nie) - die DPI-Absicht muss dort stehen, wo der
   Reiter gebaut wird, und gilt prozessweit.
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

**Eine ausdruecklich als schmal benannte Spalte hat eine HARTE Obergrenze** und
ist damit die eine Ausnahme von der Textbedarfsregel: Textbedarf schlägt den
*Wunsch*, aber nicht einen Deckel, den der Aufrufer ausdrücklich gesetzt hat
(`SCHMALE_SPALTEN = ("datei", "pfad", "sha")` → 90 px). Ohne diese Kappung
bekam die Spalte `Datei` bei 80 Zeichen 648 px und schob alles andere aus dem
Fenster. Der Zweck ist der, im Kommentar zu benennen: lange Pfade und Hashes
sollen die Ansicht nicht aufziehen - wer sie braucht, zieht sie auf.

**Der Restplatz geht an die letzte Spalte, aber gedeckelt.** Sonst wird die
letzte Spalte zur Sackgasse aus Leerraum: gemessen stand eine Spalte mit ganzen
Sätzen (14 Erklärungen bis 447 Zeichen) bei 3584 px in einem Baum von 1351 px.
Das ist kein Breitenfehler, sondern ein Text, der in eine Tabellenspalte
gehört - er umbricht, statt die Spalte zu dehnen. Die Deckelung ist eine
Eigenschaft des *Restplatzes*, nicht der Breite: ohne Fenster ist der Baum 1 px
breit, es gibt keinen Rest, und die Spalte traegt nur ihren Textbedarf. Ein
Test dieser Regel braucht darum ein gebautes Fenster oder eine
Vorbedingung.

**„ZU BREIT" unterscheidet zwei Sachen, und die Meldung muss es auch.** Brauchen
die Texte mehr als der Baum hergibt, ist Scrollen die richtige Antwort (Text
passt, nur der Platz reicht nicht). Sind die Spalten breiter als ihr Text
noetig, ist es der alte Fehler. Beide sehen in der Summe gleich aus. Die Sonde
sagt deshalb „ZU BREIT - der Text braucht es" gegen „kein UEBERHANG".

**Eine Breite, die nur nach dem Bauen gerechnet wird, ist die alte feste Breite
mit neuem Namen.** Beim Bauen ist die Tabelle leer; nachrechnen muss gegen die
**eingefuegten Zeilen** geschehen, und zwar in zwei Durchgaengen mit
unveraenderter Zeilenzahl - beim erste war nicht alles gelesen. Eine leere
Tabelle wird trotzdem nach ihren Überschriften gerechnet (sie zeigt genau die).

**Die Nachrechnung muss ENDEN, und ihre Grenze wird VOR dem Rechnen geprueft.**
Eine Konstante `MAX_DURCHGAENGE` im Baum, die nirgends gelesen wird, ist keine
Grenze: die Rechnung laeuft bei jeder Aenderung der Zeilenzahl weiter und
ueberschreibt beim naechsten Takt jede Breite, die der Nutzer gezogen hat
(gemessen: 600 px zurueck auf 200 px nach EINEM `refresh()`). Zwei Regeln
daraus, beide mit Gegenprobe:

- **Die Grenze vor dem Zaehler pruefen, nicht danach.** Sonst feuert sie im
  selben Takt wie das Ziehen und die Nutzerbreite geht doch verloren - der
  Zaehler stand auf 4, die Grenze auf 5, und der fuenfte Durchgang war der
  erste nach dem Ziehen.
- **Gegenprobe bauen, die am Nutzerzeichen haengt:** Spalte breit ziehen, einen
  Takt laufen lassen, danach messen. Das Skript behauptet nicht "der Nutzer
  kann ziehen", es zeigt die gerettete Zahl.

**Jede Fenstereigenschaft, die in eine Messung eingeht, wird VOR den Widgets
gesetzt, die messen - nicht danach.** Wer einmalig beim ersten Befuellen misst
und das Ergebnis merkt, rechnet genau einmal: mit dem Vorgabewert. Später
umgestellt, ist die Tabelle für den Rest der Sitzung zu breit (gemessen: Spalte
`Spur` 177 px bei gespeichertem Schriftgrad, Bedarf 200 px; ein späterer
Tastendruck auf die Schrift änderte die Breite nicht mehr, weil die Sperre
saß). Das betrifft Schriftgrad, Schriftart und jeden Zoom.

**Manche Eigenschaften gehören zweimal gesetzt, aus zwei verschiedenen Gründen.**
Der Stil muss **nach** den Reitern, weil ein Reiter in seinem Bau sein eigenes
Treeview-Theme setzt, das der Rahmen überschreiben muss. Die Schrift muss
**vor** den Reitern, weil sie in deren Breitenrechnung eingeht. Beides ist
dieselbe Funktion an zwei Stellen - wenn man sie an eine Stelle setzt, bricht
entweder die Farbe (Reiter ohne Theme, gemessen `#ffffff` statt `#181825`)
oder die Breite. Vor dem Verschieben beide Tests nacheinander fahren: der
Stiltest und der Breitennachweis.

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

- **JEDER Reiter braucht seine eigene Scrollflaeche, nicht der erste.** Ein
  Reiter bekommt sie, weil sein Inhalt einmal hoeher war als das Fenster; die
  Diagnose an einem Reiter gemacht und dann nicht an den anderen wiederholt,
  laesst zwei Seiten unerreichbar. Gemessen bei 1280x860: zwei Seiten zeigten
  zusammen 262 px von ueber 4000 px Inhalt, ohne Hinweis. Gegenprobe je
  Reiter umschalten - ein nicht vermessener Reiter ist nicht geprueft, sondern
  unbekannt. Bauform und die drei Fehler dabei: Punkt 8 in
  `references/messsonde-fehler.md`.
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

## Fremde Fenster-Oberflaechen einbetten

Eine bestehende GUI als Reiter in ein Notebook (oder als Karte in eine
Seitenleiste) aufzunehmen ist eine eigene Bauform. Sie hat zwei Formen, und
welche vorliegt, entscheidet ueber den Aufwand.

| Form | Beispiel | Was beim Einbetten passiert |
|---|---|---|
| baut in ein uebergebenes Widget | `Klasse(root)` mit `pack()`/`grid()` | fast nichts: `ttk.Frame` ist ein Widget, `after()` geht darauf |
| **ist** selbst ein Fenster | `class X(tk.Tk)` | muss zerlegt werden: Inhalt in ein Frame, Fenster drumherum |
| ist eine **Komposition** ohne eigene Widget-Basis | Klasse mit `self.root = root` | der Container ist das Widget; die Klasse ist es nicht |

**Fensterpflege gehoert dem Fenster, nie dem Inhalt.** `title`, `geometry`,
`minsize`, `protocol` und `destroy` liegen beim Fenster-Wrapper; das Frame
darf keine davon aufrufen. Der Fehler faellt erst zur Laufzeit auf (Fenster im
Fenster), deshalb als **AST-Pruefung des Quelltexts** festhalten - nicht als
Klick: suche in der Frame-Klasse nach `self.title`/`self.geometry`/
`self.minsize`/`self.protocol` und verlange, dass es keine Treffer gibt.

Bei der Zerlegung den **alten Namen als Alias** auf den Fenster-Wrapper
stehen lassen (`Alt = NeuFenster`). Sonst bricht jeder Aufrufer von vor dem
Umbau, und die Anzeigewerte wandern eine Ebene tiefer: wer sie las, nimmt sie
danach aus `fenster.frame`.

**Der Aufrufer darf das schwere Rad nicht selbst importieren.** Fehlt eine
Abhaengigkeit (auch nur in einem frischen venv), waere ein Import im Rahmen ein
**toter Rahmen** - ein Werkzeug nimmt den ganzen Rahmen mit, weil eine
Nebensache fehlt. Der Reiter laedt das Rad zur Laufzeit ueber eine
Ladefunktion mit `try/except ImportError` und **zeigt die
Installationsanweisung**, statt zu crashen. Braucht das Modul Schwester-Dateien
ohne `__init__.py`, gehoert ihr Ordner an den Anfang von `sys.path`.

**Ein `after()`-Timer wird zur Leiche, sobald der Reiter verschwindet, waehrend
das Fenster weiterlebt.** Im eigenen Fenster faellt das nicht auf; eingebettet
meldet Tk beim feuern `invalid command name <id>_poll_queue`. Der Inhalt
bindet deshalb `<Destroy>` und raeumt auf:

```python
def _beim_abbau(self, event=None):
    if event is not None and event.widget is not self:
        return          # nicht der eigene Abbau: Kinder sterben mit
    self._abgebrochen = True
    self.after_cancel(self._poll_id)
```

Dabei **einen laufenden Hintergrundprozess mitstoppen**, sonst bleibt er als
Waise zurueck und haelt den Prozess. Ein Reiter, der etwas haelt, muss dem
Rahmen das ueber `abbrechbar()` sagen - der Rahmen fragt es vor dem Schliessen
und verweigert es mit einer Meldung.

### Zwei Fallen beim Testen dieser Reiter

**Ein Test, der eine Startmethode aufruft, startet den echten Prozess.**
`patch.object(f, "_log")` schluckt nur die Ausgabe — der Aufbau laeuft weiter
(gemessen: 13 s Logausgabe eines echten Baus). Die Naht ist die Funktion, die
den Prozess **baut**, nicht die, die ihn startet: deren `side_effect` wirft,
bevor etwas entsteht.

**Ein Patch auf eine Klasse trifft kein Instanzattribut.** `patch.object(Klasse,
"_gui", ...)` bricht mit `does not have the attribute '_gui'` ab, weil das
Attribut erst in `__init__` entsteht — gemessen viermal in Folge am selben
Aufbau. Dann hilft auch nicht, das Objekt nach dem Bauen zu ersetzen: es
verliert genau die Methoden, die der Test pruefen soll. Die Fassung, die
trägt: **die Klasse im Modul** ersetzen (`patch.object(modul, "GuiKlasse",
Attrappe)`) und danach **nur die Anzeigedaten** am echten Reiter-Objekt
austauschen (`reiter._gui = ...`). Die Reiter-Methoden bleiben echt — nur
ihre Daten sind ersetzt. Merksatz: `patch.object` auf eine Klasse ist fuer
KLASSENATTRIBUTE, Instanzattribute gehoeren dem Objekt.

**Eine Komposition ist kein Widget — `winfo_*` fehlt ihr.** Die dritte Form
der Einbettungstabelle (unten) baut in ein uebergebenes `root` hinein und
erbt selbst nichts von Tk. Wer sie prueft, ruft `gui.winfo_children()` und
bekommt `AttributeError`; wer stattdessen `gui.root` prueft und die Kinder des
**Containers** zaehlt, hat es richtig getroffen. Vor dem Schreiben an der
Grenze lesen, was die Klasse wirklich IST (`class X:` ohne Basis = Komposition),
nicht was sie benutzt.

**Ein geratener Feldname faellt still aus.** Wer `zustand.get("live")` liest,
obwohl die Datei `modus` fuehrt, sieht nie einen Punkt und bekommt es nicht
mit. Das echte `zustand.json` **vor** dem Schreiben ansehen und den Feldnamen
von dort nehmen.

**Ein Knopf, der wie ein Orderweg aussieht und keiner ist, wird beschriftet -
nicht entfernt.** Ein Schalter fuer echtes Handeln sieht per Definition wie
ein Schalter aus. Traegt er nicht dieselben Sperren wie die Hauswege
(Sperrenkette, Freigabefenster, Spiegelung), sagt er das an **drei** Stellen:
beim Anhaeken (erscheinender Hinweis), dauerhaft in der Warnzeile ueber der
Nutzflaeche, und bei jedem Start im Protokoll - das Log ist das Einzige, was
den Lauf *spaeter* noch zeigt. Eine Fussnote wird ueberlesen. Zwei Tests, einer
gegen die Anzeige und einer gegen die Logzeile.

## Der Herzschlag: LEBENDE Zeugen lesen, nicht Dateiformate raten

Eine Statuszeile, die „laeuft nicht“ sagt, ist die gefaehrlichste Anzeige im
Haus: sie sieht wie eine Messung aus und ist eine Vermutung. Sie liest
**zwei** unabhaengige Zeugen — lebt der Prozess, und ist der letzte Eintrag
frisch — und beide muessen stimmen.

**Ein Sperr-/PID-Mechanismus traegt fast immer MEHRERE Felder, und der Leser
nimmt die ganze Zeile.** Gemessen: `sperre.py` schreibt `PID Zeitstempel`,
damit ein Waechter eine verwaiste Sperre erkennt. `int()` auf die ganze Zeile
scheitert still (`ValueError` → `pid = None`), `prozess_lebt(None)` gibt
`None`, und die Statuszeile meldet „laeuft nicht“ fuer einen Lauf, der seit
Stunden laeuft. Also: **das erste Feld nehmen, nicht parsen** —
`int(roh.split()[0])`, mit `try/except` auf `None`. Gleiches Muster bei jeder
Datei, die ein Lock belegt: PID + Zeit, Host + Port, Name + Kennung.

**Warum es drei Tage unentdeckt blieb: der Test schrieb selbst ein
erfundenes Format.** Die Tests legten `"1234"` in die PID-Datei — also genau
das Format, das der Code erwartete, und nie das, das der Schreiber erzeugt.
Eine Attrappe, die dem Code entgegenkommt, beweist nichts; sie beweist nur,
dass der Code mit der Attrappe umgehen kann. **Ein Test, der einen echten
Formatvertrag prueft, schreibt das echte Format hinein** — den Wert, den
der SCHREIBER erzeugt, nicht den, den man selbst fuer richtig haelt. Als
Werkzeug: die Datei einmal mit dem Schreiber erzeugen und byte-genaue
Kopien als Fixture nehmen.

**Der Beweis ist der Aufruf mit den echten Werten, nicht die Rechnung
einzeln.** Dieselbe Funktion liefert beim Aufruf aus dem echten Betrieb
5,35 Minuten und in einer Testumgebung mit alter Basis Tausende — die
isolierte Rechnung kann recht haben und der Aufruf trotzdem falsch sein.
Deshalb am Ende `herzschlag()` (oder was auch immer die Anzeige faedt) **einmal
gegen die echten Dateien** laufen lassen und die Zeile nennen, die sie
zurueckgibt. Eine Statuszeile, die man nur in einer Attrappe gesehen hat,
kann man nicht als gelaufen melden.

**Eine Grenze braucht einen Grund im Bericht, nicht nur eine Zahl.** „Läuft
nicht" bei gleichzeitig lebendem Prozess ist ein Befund, kein Zustand: er
gehoert mit PID, Log-Alter und der gelesenen Zeile in den Bericht, sonst
sieht die naechste Sitzung „Dauerlauf steht" und startet doppelt.

## Tabellen filtern und auf mehrere Zeilen wirken

Freitextfilter allein beantwortet "welche Spuren haben ueber 50 % Treffer"
nicht - die Zahl steht in mehreren Spalten. Bauform, Zahlenregeln und die
Mehrfachaktion auf einer Auswahl stehen in
[references/tabellen-interaktion.md](references/tabellen-interaktion.md).
Kurzform der drei Regeln, die dort begruendet werden: der Spaltenfilter
vergleicht numerisch, wenn ein Vergleichszeichen davor steht (`>50`, `<0`),
sonst als Teilstring; **ohne** Zahl wirft er die Zeile raus statt still nichts
zu finden; eine unbekannte Spalte blendet **nicht** aus. Die Spaltenliste steht
an **einer** Stelle - ein Tuple zu kurz als `values` verliert die hinteren
Spalten bei `ttk.Treeview` ohne Fehlermeldung.

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

**Und die Sonde ist selbst die haeufigste Fehlerquelle.** Zehn belegte
Fehlerbilder mit den Gegenproben - Zaehler ohne Abgrenzung, Zustands-Check mit
falschem Muster, DPI im selben Prozess gemessen, `.children` statt
`get_children()`, die Canvas-Flaeche statt ihres Inhalts gemessen, eine von
dem Konstruktor ueberschriebene `geometry()` - und die Rechnung dahinter
stehen in [references/messsonde-fehler.md](references/messsonde-fehler.md).
**Lies das, bevor du die naechste Sonde schreibst.**

Und die Probe **gegen sich selbst pruefen**, bevor ihre Zahl zitiert wird:
ihre Ausgabe nennt anfanglich, was sie angefordert hat und was das Fenster
tatsaechlich ist. Zwei Ziffern, die sich unterscheiden, machen die ganze
Messung wertlos - und sagen das dann von selbst, statt einen Befund gegen
eine Fenstergroesse zu liefern, die es nicht gibt.

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
   **Die Note eines Audits ist kein Befund.** Ein Subagent, der gegen eine
   Anti-Slop-Checkliste scored, meldet „1/10, praktisch kein Befund" neben
   Zeilen, die ein Funktionsausfall sind - ein Reiter, dessen Inhalt
   unerreichbar war, und eine Breite, die der Nutzer nicht halten konnte.
   Beides fiel unter „der Slop-Score ist niedrig". Also: **jeden Befund
   einzeln gegen die eigene Messprobe stellen**, nicht gegen die Note. Der
   Wert eines Audits ist die Zahl am Anfang; die Arbeit ist darunter. Und:
   ein Audit, das eine Kontrastzahl oder eine Pixelbreite nennt, ohne den
   Weg zu nennen, ist zu behandeln wie jede andere Zahl im Bericht - nach
   dem Preis fragen, gegen die eigene Sonde halten.
   **Ein Fremd-Repo-Fenster wird nach demselben Maß auditiert, aber
   geaendert an ORT UND nicht im Haus-Index.** Steht der Befund am Ende im
   Modulkopf des Fremd-Fensters, ist das eine Entscheidung und kein Reparatur-
   Schema: die fremde Palette bleibt fremd, mit den gemessenen Zahlen und
   dem Grund benannt. Das schuetzt vor der Zerstoerung beim naechsten
   `repos-updaten` und macht den Unterschied sichtbar, statt ihn zu
   ueberziehen.
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
   (1280 und 1000) - sonst ist der Umbau nur auf dem einen Monitor belegt. Und
   **bei JEDER Schriftgroesse, die der Nutzer waehlen kann**: die Vorgabe des
   Moduls ist nicht sein Alltag, er speichert seine Wahl in der Zustandsdatei
   des Fensters (gemessen: bei Schrift 11 null abgeschnitten, bei seiner
   gespeicherten Schrift 96).

## Pitfalls

- **Ein roter Test ist nicht automatisch ein Codefehler - und ein grüner
  erst recht nicht die Regel.** Wird ein Test rot, während du dieselbe Regel
  gerade reparierst, ist zuerst die Frage: welche Seite hat die Erwartung
  eingefroren? Ein Test kann den Fehler festhalten, den du behebst. Gefroren
  war hier eine Erwartung, `stretch == [False, False, True]` - genau das
  Verhalten, das jede gerechnete Breite verfaelscht. **Pruefe die Regel, die
  der Test schuetzt, nicht den Wert, den er einsteckte**, und schreibe ihn so
  um, dass beide Teile der Regel getroffen sind (hier: keine Spalte dehnt
  sich, UND die letzte ist breiter, UND der Zugewinn ist gedeckelt). Wird
  dagegen eine Regel entfernt, ohne ihren Zweck zu pruefen, verliert der Test
  seine Aussage - und mit ihr die Absicherung fuer den naechsten Umbau.
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
- **Ein Messwerkzeug, das sich an die Fensterklasse bindet (Attribute des
  Fensters voraussetzt), muss beim Schreiben auf einen GEBAUTEN Bildschirm
  getestet werden. Platzhalter-Aufrufe, die nie liefen, sind Messwerkzeuge,
  die nichts messen.**
- **Ein Helfer, der seinen Zielpfad aus `__file__` ableitet, kann danebenliegen.**
  Ein Werkzeug, das neben sich sucht statt in einem relativen Pfad, meldet
  "FEHLT: <ziel>", obwohl der Ordner sichtbar daneben liegt - die Meldung
  sieht nach kaputtem Import aus und war eine falsch gezaehlte Zahl von
  `dirname`-Aufrufen (hier eine zu wenige und eine zu viel, in zwei
  Werkzeugen). Gegenprobe statt Fehlersuche: **das Skript behauptet nicht,
  es fragt** - am Anfang einen Existenz-Assert einbauen,
  `assert os.path.isdir(ZIEL), ZIEL`, dann nennt der Fehler den
  RECHNER Pfad statt eines Zielnamens, den man erraten muss.
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

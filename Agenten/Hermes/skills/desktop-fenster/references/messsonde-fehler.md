# Die Messsonde selbst ist die haeufigste Fehlerquelle

Befunde, alle am echten Fenster nachgewiesen, alle in der Sonde, nicht in
der Rechnung. Wer sie kennt, muss sie beim Bau der naechsten Sonde nicht
erneut suchen.

Zwei Sorten, die man beim Reparieren auseinanderhalten muss:

* **Die Sonde misst das Falsche** (Punkte 1-11). Der Code im Fenster ist in
  Ordnung, die Zahl beschreibt eine Oberflaeche, die es nicht gibt.
* **Die Sonde misst richtig, und die Zahl stimmt trotzdem nicht** (Punkt 12).
  Der Fenstercode war falsch - das ist der teuerste Fall, weil man der
  Sonde fast glaubt.

Ein dritter Fall kam dazu, der kein Fenster betrifft: **Punkt 13**, ein
Pruefskript, das den falschen Vordergrund misst.

## 1. `winfo_ismapped()` bleibt bei einer einmal gezeigten Notebook-Seite TRUE

Auch wenn die Seite nicht mehr vorne liegt. Ohne eigene Pruefung wird dieselbe
Tabelle unter jedem Reiternamen gezaehlt; gemessen war die Summe das Zwei- bis
Vierfache der echten Zahl (333 statt 124).

Die Zuordnung Tabelle -> Reiter gehoert aus dem **Widget-Pfad**, nicht aus
`nb.select()` - der steht beim Messen schon auf dem naechsten Reiter, waehrend
noch der alte Aufbau sichtbar ist.

```python
def pfad_von(w):
    teile = []
    while w is not None and w is not root:
        teile.append(str(w))
        w = w.master
    return ".".join(reversed(teile))

for pfad in nb.tabs():
    nb.select(pfad)
    root.update(); root.update_idletasks()
    ziel = pfad_von(root.nametowidget(nb.select()))
    for baum in baeume:
        if baum.winfo_width() <= 2:
            continue                      # nicht vermessen: keine Aussage
        if not pfad_von(baum).startswith(ziel):
            continue                      # gehoert zu einem anderen Reiter
        bericht(...)
```

## 2. Nur gezeichnete Zeilen zaehlen, nicht `get_children()`

Eine Tabelle haelt mehrere hundert Zeilen und zeigt eine mit `height=8`. Die
uebrigen sind ueber die Leiste erreichbar und werden NICHT abgeschnitten. Alle
zu zaehlen meldete 2276 "zu schmal" statt der sichtbaren Zahl.

```python
for iid in baum.get_children():
    if baum.bbox(iid) is None:
        continue            # nicht gezeichnet -> nicht sichtbar
```

`bbox` liefert `None` fuer nicht gezeichnete Zeilen - das ist die Abgrenzung,
nicht eine Fehlerbehandlung.

## 3. `root.withdraw()` hat keine Geometrie

Ein Test darf es nutzen. Eine **Messung** nicht: Tk vermisst ein verborgenes
Widget mit 1 px, die Sonde meldet dann einen Ueberhang, den es nicht gibt
(+114 px fuer eine Tabelle, die mit 1058 px in 1226 px passt).

Messfenster **sichtbar ausserhalb des Bildschirms** positionieren:

```python
root.geometry("1280x860-3200-0")
```

Zusaetzlich: eine Tabelle, die im aktuellen Reiter nicht sichtbar ist, hat
`winfo_width() == 1`. Das ist eine Vorgabe, kein Messwert - nicht als
"ZU BREIT" werten.

## 4. Ein Zustands-Check mit dem falschen Muster erkennt sich selbst

`if "self._flag" in datei` war wahr, weil die Methode die Flag las, nicht weil
die Zuweisung existierte. Ein Zustands-Check auf einen Namen, der drei Stellen
hat (eine Zuweisung, zwei Verwendungen), meldet "steht schon" fuer eine
Zuweisung, die fehlt. **Immer auf die Zeile der Zuweisung pruefen** (`= False`,
nicht der Name).

## 5. Der Nutzer waehlt die Schrift selbst

Die Vorgabe des Moduls ist nicht sein Alltag. Die Wahl steht in der
Zustandsdatei des Fensters (`Leitstand: schrift`, 8..16). Die Sonde braucht sie
als Parameter und prueft **alle** Werte der Spanne - bei Schrift 11 war 0
abgeschnitten, bei seiner gespeicherten Schrift 96.

## 6. `dpi_bewusst()` misst man nicht im selben Prozess

Eine Schrift misst ohne `dpi_bewusst()` 8 px je Zeichen (Consolas 11) und mit
10 px. Wer beide Faelle in einem Prozess messen will, bekommt **immer den
ersten**: das erste `Tk()` hat den DPI-Kontext des Prozesses festgelegt, jede
spaetere `SetProcessDpiAwareness`-Wirkung ist tot. Jeder Fall braucht einen
eigenen Kindprozess (JSON auf stdout). Muster:
`Agenten/Handel/zeichenbreite_dpi.py`.

Merksatz fuer Breiten ausserhalb des Fensters: eine in Pixeln gesetzte Breite
gilt nur fuer die Skalierung, bei der sie gesetzt wurde. Wer ohne Fenster
rechnet, braucht beides - den skalierten Wunsch UND die Zeichenbreite des
echten Fonts, als Parameter, nicht als Konstante.

### `GetDeviceCaps` luegt ohne Awareness - es meldet immer 96

Die physische Monitor-DPI laesst sich nur **nach** `SetProcessDpiAwareness`
ablesen. Ohne sie skaliert Windows die Abfrage auf den logischen Wert: der
erste Lauf meldete 96 dpi und damit Faktor 1.0, dieselbe Maschine lieferte im
dpi-bewussten Zustand `winfo_fpixels('1i')` 119 (120 dpi, Faktor 1.25). Der
gemessene Unterschied, den das klaert: **ein dpi-unawares Fenster sieht 36 %
weniger Bildschirm** (3072x1728 statt 3840x2160). Wer die Skalierung des
Monitors belegen will, setzt die Awareness zuerst.

## 7. „ZU BREIT" ist nicht automatisch ein Fehler

Brauchen die Texte mehr als der Baum hergibt, ist die **waagerechte Leiste**
die richtige Antwort - die hat jede Tabelle. Gemessen bei Schrift 16:
Untergrenzen 1276 px bei 1186 px Platz, kein Ueberhang. Bei Schrift 11
dagegen: 970 px in 954 px, das war echter Ueberhang. Beides sieht in der Summe
gleich aus.

Die Sonde unterscheidet beides ueber die Zahl der zu schmalen Texte und sagt
"kein UEBERHANG, der Text braucht es" gegen "waagerechte Leiste noetig".

## 8. Bei einer Scrollseite misst man die Canvas-Flaeche, nicht den Inhalt

Geprueft, ob der Inhalt einer Seite ueber den sichtbaren Bereich hinausgeht:
`seite.winfo_children()` eines scrollbaren Reiters liefert den **Canvas**, und
dessen Kind ist die Innenflaeche - nicht der Inhalt darin. Die erste Fassung
mass die Kindrekursion nur eine Ebene tief, kam auf 262 px fuer alle drei
Reiter und meldete durchgehend "passt". Nach dem Auslesen bis in die
Innenflaeche waren es 1978/1968/2200 px bei 767 px sichtbar - also drei
Reiter, die alle drei abschneiden.

```python
canvas = [k for k in seite.winfo_children()
          if k.winfo_class() == "Canvas"][0]
innen = canvas.winfo_children()
inhalt = sum(k.winfo_reqheight() for k in innen)
for k in innen:
    for u in k.winfo_children():
        inhalt += u.winfo_reqheight()
```

**Merksatz:** eine Zahl, die bei mehreren Reitern/Seiten gleich aussieht, ist
meist die gemessene Huelle und nicht der Inhalt. Waere der Befund
"nichts schneidet ab" gewesen, haette man ihn ohne diese Gegenprobe als
Entwarnung gemeldet.

### Der Bau: jeder Reiter, nicht der erste

Der Befund, den diese Messung getragen hat: `scrollbare_seite()` war nur am
ersten Reiter gebaut, die beiden anderen Seiten waren blanke Container. Ein
Reiter bekam die Flaeche, weil sein Inhalt einmal hoeher war als das Fenster -
die Diagnose an einem Reiter gemacht und an den anderen nicht wiederholt,
laesst zwei Seiten unerreichbar, ohne dass etwas darauf hinwist. Geprueft
wird das je Reiter, nicht einmal ueber die Tabelle.

Drei Baufehler, die dabei derselbe Weg macht:

- Eine scrollende Seite ist `(wrapper, innen, canvas)`. Dem Container wird der
  **Wrapper** eingetragen; `page.add(innen)` bricht mit „can't add ... as
  slave of", weil die Innenflaeche im Canvas haengt.
- Das Mausrad gehoert an **jede** Seite einzeln: ein Radereignis landet auf
  dem Widget unter dem Zeiger, nicht auf dem Canvas dahinter, und ohne die
  Bindung scrollt die neue Flaeche nicht (siehe Punkt zur Rad-Bindung in
  SKILL.md).
- Ein Reiter, dessen Seite nicht vermessen wurde, ist **nicht geprueft** -
  nicht "unauffaellig". Die Gegenprobe schaltet jeden Reiter um und misst
  Inhalt gegen Sichtbarkeit.

## 9. `geometry()` vor dem Konstruktor ist ein totes Argument

Ein Fenster, das seine Lage selbst setzt (`geometry()` in `__init__`,
`start_lage()`), ueberschreibt eine vorher gesetzte Groesse. Die Sonde
mass 2611x1469 statt der angeforderten 1280x860 - eine Fenstergroesse, die
niemand benutzt, und damit ein Befund gegen eine Oberflaeche, die es so
nicht gibt.

Zwei Regeln daraus: **die Groesse NACH dem Konstruktor setzen**, und die
Sonde **gegenpruefen** statt zu behaupten:

```python
lei = Leitstand(root)
root.geometry("%dx%d-3200-0" % (args.breite, args.hoehe))
print("angefordert %dx%d, tatsaechlich %dx%d"
      % (args.breite, args.hoehe, root.winfo_width(), root.winfo_height()))
```

Die Gegenprobe gehoert in die Ausgabe der Sonde: stimmen die beiden Zahlen
nicht ueberein, ist die Messung wertlos und das sagt die Sonde dann selbst.
Ein Argparse-Schalter, den die Geometrie ueberschreibt, ist ein stiller
Schalter - er sieht wie eine Konfiguration aus und wirkt nicht.

**Zwei Luecken in derselben Sonde, beide aus derselben Ursache:** sie hielt
nur den *sichtbaren* Reiter fuer gemessen und liest das erste `## Offen`
einer Dokumentdatei. Sie zaehlte 2 Tabellen bei 4 Reitern und schrieb einen
Bericht gegen eine Fenstergroesse, die es nicht gibt. Wer eine Sonde baut,
fragt einmal nach: *welche Reiter wurden ueberhaupt gemessen, und ist das die
Menge, die es gibt?*

## 10. Zwei Schriftfamilien in einem Fenster brauchen zwei Messungen

`leitstand_stil.py` setzt Consolas fuer Tabellenzellen und eine
Systemschrift fuer Ueberschriften. Eine Sonde, die durchgaengig die
Tabellenschrift misst, ueberschaetzt den Bedarf der Ueberschriften um rund
ein Viertel (141 px gegen 110 px gemessen). Beide Familien aus dem Fenster
nehmen, nicht aus dem Nachbarmodell:

```python
gross = lei.schrift                       # die Fenstergrundgroesse
schrift_zeile = tkfont.Font(family=hz.SCHRIFT_ART, size=gross)
schrift_kopf = tkfont.Font(family=familie_der_ueberschrift(gross), size=gross)
```

## 11. Eine Zahl, die nach einem Fix SPRINGEN ist, war eine Falschmessung

Das ist der Fall, in dem die Sonde richtig misst und die Zahl trotzdem nicht
stimmt - und deshalb der teuerste, weil man ihm fast glaubt.

Gemessen: nach dem Verschieben des Schriftgrads vor den Reiterbau meldete die
Sonde **mehr** Abschneidungen als vorher (56 → 100). Die naheliegende Deutung
ist "der Fix hat es schlechter gemacht". Die richtige ist die andere: vorher
hat die Rechnung mit dem **Vorgabewert** gelaufen und den echten nicht
gefunden, nachher laeuft sie mit dem gespeicherten und findet ihn zum ersten
Mal. 63 der 100 lagen in einer einzigen Tabelle.

**Die Sonde ist die Kontrollinstanz, nicht der Angeklagte.** Wenn eine Zahl nach
einer Aenderung springt, ist die Frage nicht "welche Aenderung ist schlecht",
sondern "welche Rechnung lief vorher und welche laeuft jetzt". Der Test dazu:

1. Vorher und nachher mit **derselben** Sonde messen, nicht mit einer, die
   zwischendurch dazukam.
2. Die Zahl **auf mehrere Tabellen aufteilen**. Springt eine davon, ist es ein
   Befund; springen alle gleichmaessig, ist es eine globale Aenderung (Schrift,
   Farbe, Skalierung).
3. Nachrechnen, was die Regel mit den konkreten Daten tut - ein reiner
   Aufruf der Breitenfunktion mit den Zeilen aus dem Journal, ohne Fenster.
   Zeigt sie das erwartete Ergebnis, ist die Sonde richtig und der Fenster-
   code war falsch. Zeigt sie das falsche, ist die Sonde es.

**Und wenn beide stimmen, ist es kein Fehler, sondern eine Grenze.** Ein
Satz Text, der in eine Tabellenspalte gehoert (447 Zeichen), wird nicht durch
eine bessere Breitenregel kleiner - er umbricht. Wird eine Spalte sehr breit
gemessen, ist zuerst zu fragen, ob der Text hineingehoert, und erst dann, ob
die Rechnung falsch ist.

## 12. Der Kontrast gehoert gegen den Text, der AUF der Farbe steht

Ein Farbwert, der unter 4,5:1 liegt, ist nur dann ein Befund, wenn er
**Text traegt**. Gemessen zwei Befunde, von denen einer keiner war:

* Ein Knopf mit `bg=#c0392b`, `fg="white"` kam gegen die Standardfarbe auf
  3,23:1 und sah wie ein Befund aus - gegen Weiss sind es 5,44:1, also
  in Ordnung. Das Standardverhaeltnis misst die falsche Flaeche.
* Ein Zellenhintergrund, ein Rahmen und eine Auswahlfarbe tragen gar keinen
  Text. `zebra` bei 1,10:1 und eine Rahmenfarbe bei 1,92:1 sind die Absicht,
  keine Flaeche dunkel zu halten - kein Befund.

Also **je Farbe ihren eigenen Vordergrund mitgeben**, und die Farben ohne
Text getrennt fuehren:

```python
TRAGEND = {"matt": d.FARBEN["blatt"], "hinweis": d.FARBEN["bg"],
           "notaus": "#ffffff"}            # Knopf mit weissem Text
FLAECHE = {"zebra", "dunkelgelb", "rand", "wahl"}   # traegt keinen Text
```

Und das Gegenstueck, das dieselbe Sonde produziert hat: **ein Wert, der
zweimal unter zwei Namen steht** (zwei Namen fuer dieselbe Farbe, einmal als
zweiter Name noch in der Quelle), ist ein Wartungsbefund - unabhaengig vom
Kontrast. Zwei Namen, eine Farbe, drei Namen, wenn die Quelle sie auch
fuehrt.

## 13. Ein Pruefskript liest den WERT aus dem Objekt, nicht aus dem Text

Beim Pruefen einer Palette wurde der Wert per **Regex aus dem Quelltext**
gelesen. Das ging schief, sobald der Wert aus der Quelle kam
(`matt=hz.FARBEN["matt_flache"]`): der Regex las die Erklaerung darueber, die
den ALTEN Wert nennt, und meldete weiter "ueberschreibt die Quelle" fuer
eine Farbe, die genau daraus stammt. Vier Anpassungen des Regex, dann auf
gegeben.

**Kein Regex-Feinschliff hilft, wenn die Aussage im Objekt steht.** Das
Modul laden und die Ableitung lesen:

```python
spec = importlib.util.spec_from_file_location("stil_probe", STIL)
stil = importlib.util.module_from_spec(spec); spec.loader.exec_module(stil)
gefunden = {k: v for k, v in stil.FARBEN.items() if k not in d.FARBEN}
```

Dieselbe Regel in der einen anderen Form, die im selben Lauf auffiel: eine
Zeile **im Kommentar** einer Quelldatei ist kein Wert. Will man den *alten*
Stand lesen, gehoert er in die `.bak` oder in `git show` - nicht in den
Lebendtext daneben.

## 14. Ein Muster, das nichts trifft, macht den Test gruen - ohne zu pruefen

Ein Test sammelte alle `leitstand*.py` ein, um "keine Hexfarben ausserhalb des
Stils" zu erzwingen. Zwei Messskripte kamen mit ins Raster und machten ihn
rot. Der Test wurde auf einen Ausschluss von `*messprobe*` umgestellt - und
war danach gruen, **ohne eine einzige Datei zu pruefen**: das Muster stand auf
`_messprobe` mit fuehrendem Unterstrich, die Datei hiess `leitstand_messprobe`,
und `endswith` traf nie. Die Liste war leer, der Test lief ins Leere.

Zwei Regeln daraus, und die zweite ist die allgemeine:

* Ein Werkzeug baut kein Fenster und gehoert nicht in eine Fenster-Regel.
  Sonst enthaelt es zwangslaeufig die Werte, gegen die die Regel steht.
* **Ein Test, dessen Datensatz leer sein kann, braucht eine Gegenprobe:**
  `assertGreaterEqual(len(self.DATEIEN), 5)` und eine Benennung, die
  beweist, dass die richtige Datei darin ist. Ein Filter, der nichts findet,
  ist kein bestandener Test, sondern ein stiller Ausfall.
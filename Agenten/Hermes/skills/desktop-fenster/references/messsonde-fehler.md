# Die Messsonde selbst ist die haeufigste Fehlerquelle

Zehn Befunde, alle am echten Fenster nachgewiesen, alle zehn in der Sonde,
nicht in der Rechnung. Wer sie kennt, muss sie beim Bau der naechsten Sonde
nicht erneut suchen. Abschnitt 11 weiter unten hat den Sonderfall, dass die
Sonde richtig ist und die **Zahl falsch bleibt, weil sie richtig gemessen hat** -
die Rechnung im Fenster war falsch.

## 1. `winfo_ismapped()` bleibt bei einer einmal gezeigten Notebook-Seite TRUE

Auch wenn die Seite nicht mehr vorne liegt. Ohne eigene Pruefung wird dieselbe
Tabelle unter jedem Reiternamen gezaehlt; gemessen war die Summe das Zwei- bis
Vierfache der echten Zahl (333 statt 124).

Die Zuordnung Tabelle -> Reiter gehoert aus dem **Widget-Pfad**, nicht aus
`nb.select()` - der steht beim Messen schon auf dem naechsten Reiter, waehrend
noch der alte Aufbau sichtbar ist.

Zaehler:

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

Der Sonderfall, der sich nicht allgemein formulieren laesst, ist der
**Bestandsschutz durch zwei Quellen**: kopiert ein Fenster die Palette
statt sie zu importieren, ist sie heute wertgleich und morgen nicht. Die
Messprobe erkennt das nicht - das ist ein Befund aus dem Farbvergleich, siehe
`code-audit` und die Einstiegskapitel dieses Skills.

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
   Befund; springen alle gleichmäßig, ist es eine globale Aenderung (Schrift,
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
# Fehlerklassen der Verdrahtung — die sieben Formen, wiedererkennbar

Alle Beispiele stammen aus einem Audit ueber ein Handelssystem mit Einheiten,
die mehrere Buecher im selben Ordner fuehren. Die uebertragbare Form steht
links, das Beispiel nur als Beleg.

## 1. Der Pfad eine Ebene zu hoch (Werkzeug im Wurzelordner)

Ein Werkzeug, das **im Zielordner** liegt, bildet seine Basis mit einem festen
`dirname`, das eine Ebene hoeher zeigt. Folge: alle Konfigurationsdateien werden
nicht gefunden, `json.load` liefert nicht etwa einen Fehler, sondern ein leeres
Ergebnis — jede Einheit gilt als „aus".

**Merkmal:** einheitliches, unauffaelliges Ergebnis („alles gesperrt"),
obwohl die Zahl der geschaetzten Groesse widerspricht.

**Regel:** in einem Werkzeug, das im Zielordner liegt, ist der Basispfad
selbst der Ordner. Die Faustregel gilt fuer beide Richtungen: eine
Wurzel-Datei zeigt auf den Wurzelordner, eine Spur-Datei auf ihren
Spurordner. Ein Versuch um eine Ebene daneben erzeugt **keinen** Fehler,
sondern leere Daten.

## 2. Ein Name, der auf eine Liste zeigt, die ihm nicht folgen muss

Eine Einheit teilt den Ordner mit einem Hauptbuch und unterscheidet sich nur
durch ein Suffix an den Dateinamen. Der Prüfer fuehrt die Suffix-Namen **hart**
(`("a", "b")`) — jede neue Variante faellt still durch alle Listen.

Zusaetzlich wird das Suffix geraten, indem der Rest des Namens abgeschnitten
wird. Bei einem mehrstufigen Namen (Hauptteil + Unterteil + Variante) liefert
das einen **gueltigen aber falschen** Namen, und wenn es den nicht gibt, greift
der stillschweigende Rueckfall auf die Hauptdatei — geprueft wurde dann das
fremde Buch.

**Regel:** die Liste der Varianten aus der einen Quelle ableiten, die sie
verwaltet; den Suffix **von rechts** kuerzen, bis eine Datei da ist; und den
gefundenen Suffix an **jede** Buchdatei haengen — auch an die, aus der nur ein
Anzeigewert (Zeilenzahl, Alter, Zielhinweis) gelesen wird.

## 3. Ein Betriebsmerkmal, das im Messweg nie ausloest

Ein Schalter, der im Betrieb eine Signalrichtung erkennt, das Signal an einen
**getrennten Ausfuehrer** uebergibt und dann `continue` macht. Im Messweg gibt
es keinen Ausfuehrer: es wird nie gebucht, ohne Fehlermeldung.

**Merkmal:** die Zahl ist nicht kaputt, sie ist **glatt** — 0 Runden ueber
Jahre, eine Quote, die sich nie bewegt, ein Ergebnis, das sich mit den Daten
nicht aendert.

**Regel:** wenn eine Kennzahl auffaellig glatt ist, das Merkmal der
Konfiguration dieser Einheit lesen und fragen, ob es im Messpfad überhaupt
ausloesen kann. Der Fix gehoert an die **Messkonfiguration** (das Merkmal dort
entfernen und den Grund notieren), nicht an die Quelle — und alte Zahlen aus
dieser Quelle sind bis zur Nachrechnung nicht zitierfaehig.

**Zweite Form derselben Klasse:** der Messweg laedt seine Konfiguration aus
dem **Arbeitsspeicher des Aufrufers**, nicht aus der Datei, die er selbst
geschrieben hat. Ein Fix, der nur eine lokale Kopie aendert, ist wirkungslos —
der Aufrufer laedt neu.

## 4. Ein Wert folgt der Historie statt dem Zustand

Ein Satz (Gebuehr, Preis, Kontowert) wird gesetzt, als die Einheit auf einer
Boes[e] handelte. Wechselt die Einheit die Boerse, wandert das Feld nicht mit.
Jede Auswertung rechnet daraufhin mit einem fremden Satz.

**Regel:** die Regel aus dem Feld ableiten, das den Zustand **beschreibt**
(Boesenliste mit Vorrang, Zielboerse), nie aus der Historie oder dem letzten
gemessenen Wert. Und in der Regeltabelle des Setzwerkzeugs muss der Zeile der
Einheit eine eigene Quelle beigelegt sein, sonst wandert sie beim naechsten
Setzlauf wieder zurueck.

## 5. Eine Notiz entscheidet ueber eine Zahl

Ein Pruefer leitet eine Eigenschaft aus dem **serialisierten Objekt** ab
(`json.dumps(w).lower()` auf ein Schluesselwort). Die Felder mit dem Praefix
`_` sind Notizen und erwaehnen genau die Begriffe, nach denen gesucht wird.

**Regel:** Konfigurationswerte stehen in Feldern. Ein Test, der die Praesenz
einer Bemerkung als Beleg akzeptiert, ist kein Test — die Bemerkung ist die
Begruendung, nicht der Nachweis.

## 6. Ein Cache beantwortet die Frage

Ein Modul-Cache wird nur bei **leerem** Inhalt neu geladen. Jeder Lauf, der
danach mit umgebogenem Pfad und eigenen Daten arbeitet, bekommt die alte
Antwort — mit einem Ergebnis, das aussieht wie ein Messwert.

**Regel:** ein Cache darf eine Antwort beschleunigen, aber nie die Frage
beantworten. Wenn ein Test seinen Zielpfad umbiegt, muss der Cache die Frage
an den **aktuellen** Pfad stellen, sonst sieht der Test die Daten des
vorherigen.

## 7. Ein Pruefer liest nicht alles, was er zu lesen glaubt

Ein Muster deckt nicht alle Schreibweisen des Bestands ab (Statuszeichen,
Leerraum nach dem Zeichen, Endung eines Suffixes). Ergebnis: gruen, mit einer
Zahl, die einen Teil des Bestands uebersieht.

**Regel:** nach jeder Aenderung, von der man weiss, dass der Pruefer sie sehen
**muss**, die Zahl des Pruefers sich bewegen sehen. Ein Pruefer, dessen Zahl
starr bleibt, ist kaputt, egal was er sagt — und der Verdacht faellt zuerst
auf ihn, nicht auf die Daten.

## Zusammenfassung: die Formen, nach denen man greift

| Form | Erkennungszeichen |
|---|---|
| Pfad eine Ebene daneben | einheitlich leeres Ergebnis |
| Hart gefuehrte Namensliste | eine neue Variante fehlt in allen Listen |
| Im Messweg nie ausloesend | Zahl ist auffaellig glatt |
| Satz folgt der Historie | Wert passt nicht zur aktuellen Konfiguration |
| Notiz entscheidet ueber Zahl | Bemerkung widerspricht dem Feld |
| Cache beantwortet die Frage | Ergebnis stammt aus fremden Daten |
| Pruefer liest zu wenig | Zahl bewegt sich trotz Aenderung nicht |

## Der Test, der dazugehoert

Nach jeder Reparatur eine **fallende Gegenprobe**: den Fix zuruecknehmen und
den neuen Test laufen lassen. Zwei Fallen, beide gemessen:

- Ein Ersetzungsanker kann den **Kommentar** statt der Codezeile treffen — dann
  bleibt die Gegenprobe faelschlich gruen. Immer gegen die **Codezeile**
  verankern, nicht gegen eine Zeile, die auch im Prosatext vorkommt.
- Ein Test, der eine Betriebsdatei anfasst, braucht **zwei** Schranken:
  Schreibmodus aus **und** Pfad umbiegen. Eine genuegt nicht. Und im `tearDown`
  erst loeschen, dann zuruecksetzen — sonst loescht der Test-Waechter die echte
  Datei.

## Tests, die einen Stand statt einer Regel einfrieren

Ein Test, der einen **gelegentlichen** Wert festhaelt (Boersensatz, Schalter-
stand, Zuordnung), meldet eine Aenderung statt eines Fehlers. Die Reparatur
laeuft ueber die **Eigenschaft**: was muss gelten, unabhaengig vom aktuellen
Wert. Der Nachweis, dass es ein vorbestehender Fehlschlag war: die eigene
Aenderung auf `HEAD` zuruecknehmen und die Suite erneut fahren — gleiches
Ergebnis = vorbestehend und im Bericht benannt.
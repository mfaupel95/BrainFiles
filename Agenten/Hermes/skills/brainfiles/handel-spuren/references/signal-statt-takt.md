# Signal statt Takt: Einstieg und Ausstieg an die Indikatorlage binden

Ausloeser: „weniger handeln", „Ein- und Ausstiege sollen indikatorindiziert
und nicht zeitabhaengig laufen", „die Signale sollen ausloesen, nicht die
Uhr", „die Spur handelt dieselbe Sache 96 Mal am Tag".

Der Befund, der die Regel ausloest: der **Gebuehren-Excess ist ueberall nahe
null**. Eine Spur, die 2,44 % macht und 0,01 % mehr als der Markt, hat keinen
Vorteil - die Gebuehr hat ihn aufgefressen. Dagegen ist die **Zahl der
Runden** die einzige Variable, die Max unmittelbar senken kann: gleiche
Bruttokante je Runde, weniger Runden, weniger Gebuehrenzahlungen.

## Zwei Architekturen, beide im Haus gebaut

**A - im Dauerlauf (28 Spuren).** `spur_buch.trigger_modus == "signal"`:
`vor_signal` im Zustand merkt die zuletzt gesehene Richtung je Instrument;
ein Signalwechsel schreibt einen Auftrag in `signal_queue.json` der Spur
und der Dauerlauf kehrt mit `continue` zurueck. Ein aelterer Eintrag
verfaellt nach 30 Minuten. Ausgefuehrt wird die Queue von einem Hermes-Cron
(`signal-executor.py`, jede Minute, `no_agent`, leere Ausgabe = nichts).

**B - bei Spuren mit eigenem Buch (xperp, scanner, mosaic, kraken).** Diese
fuehren einen eigenen `handeln.py` und wuerden das Flag aus A
**stillschweigend ignorieren**. Fuer sie liegt die Regel einmalig in
`Agenten/Handel/signal_wechsel.py` (`zugelassen`, `ERLAEUT`, `GESPERRT`).

**Vor dem Ausrollen messen, welche Bauart ueberhaupt greift:**
`grep -c spur_buch <spur>/handeln.py`. Eine Spur mit eigenem Buch und ohne
gesonderte Verdrahtung laeuft weiter im Takt - das sieht wie „Flag gesetzt"
aus und ist es nicht.

## Das Gatter steht VOR dem Orderaufruf

Der Gatter gehoert in den Kandidatenloop bzw. vor `anlauf()`, **nicht** ans
Anlegen der Position. Ein erster Versuch stand bei xperp UND beim scanner
hinter dem Kauf: bei Live waere die Order schon draussen gewesen und die
Regel genau einen Zyklus zu spaet gekommen. Wer den Gatter erst dort setzt,
testet es nur am Buch und merkt den Live-Fehler nie.

**Der Schluessel ist die BASIS, nicht das Instrument.** Derselbe Markt
erscheint als `XBT-USD` und als `BTC-USD-um_XPERP`. Am Instrument-Schluessel
zaehlt jeder Wechsel zwischen den Schreibweisen als Richtungswechsel, und die
Regel ist wirkungslos, ohne dass irgendwo eine Fehlermeldung steht. xperp
hatte den Gatter zunaechst auf `a["inst"]` und wurde auf `kandidat["basis"]`
umgestellt.

## Der Fehler, den die Tests am Tag der Einfuehrung meldeten

**Ein Gatter muss auf BEIDEN Wegen denselben Wert zurueckgeben.** Die erste
Fassung gab im Nicht-Flag-Fall `True` (bool) zurueck, im Flag-Fall den
String `ERLAEUT` - und alle Aufrufer pruefen `is not ERLAEUT`. Damit sperrte
das Gatter jede Spur, die das Feld **nicht** gesetzt hat: das genaue
Gegenteil der Regel, und im Bericht unsichtbar, weil es nie einen Fehler
wirft. Drei xperp-Tests sind am selben Tag rot gelaufen.

Also: `if w.get("trigger_modus") != "signal": return ERLAEUT` - derselbe
Wert, derselbe Typ. Und ein Test, der diese Fassung **festhält**
(`test_gegenprobe_doppelter_rueckgabewert`), sonst kommt sie wieder.

**Merksatz allgemein:** ein Sentinel-Vergleich (`is not KONSTANTE`) ist eine
Typ-Zusage. Wer zwei Wege mit verschiedenen Typen versorgt, sperrt nicht die
beabsichtigten Faelle, sondern alle anderen.

## Das Gatter merkt auch den VERWEIGERTEN Zustand

`vor_signal` bildet den **gesehenen** Signalzustand ab, nicht den
ausgefuehrten - es wird bei JEDER Pruefung gesetzt, auch bei der verweigerten.
Sonst passiert die verweigerte Runde beim naechsten Takt erneut durch,
sobald ein anderes Instrument den Vergleich verschiebt.

Je Instrument getrennt: ein zweites Instrument darf nicht am ersten scheitern.

## Ein Weg ausserhalb des Dauerlaufs muss die SPERRKETTE selbst pruefen

Der `signal-executor` laeuft nicht durch `sperren_live()` und pruefte
zunaechst nur `handel_erlaubt` und `freigabe.erfuellt`. **Nicht** geprueft
wurde das Freigabefenster - bei drei live-faehigen Spuren haette eine Queue
aus einem Signalwechsel eine echte Order OHNE Fenster gesetzt: genau die
Luecke, die Handelsregeln Punkt 3 schliesst.

Jeder Weg, der ausserhalb der gewohnten Kette ordert, traegt **alle** Tore
selbst - und **ein Import- oder Lesefehler bedeutet: keine Order.** Ein
Weg, der bei Unsicherheit durchlaesst, ist kein Weg. Gegenprobe je Tor:
eine Spur ohne Freigabe und eine abgeschaltene Spur geben beide `False` zurueck
und lassen den Auftrag in der Queue liegen.

## Die Queue ist STUFENfaehig, sonst ist sie ein Echo

`pfade()` legt Zustand und Journal **je Risikostufe** ab — `risikostufe.datei()`
haengt `.mittel` bzw. `.hoch` an. Jede NEUE Datei einer Spur, die der Dauerlauf
schreibt, gehoert durch denselben Aufruf.

Gemessen: drei Stufen fahren dieselbe Spur mit eigener `vor_signal` und
schrieben in ein fest benanntes `signal_queue.json` — drei Eintraege in acht
Minuten, alle gleiche Richtung, alle gleiches Instrument. Der Executor haette
dieselbe Position **dreimal** angelegt. Kein Fehler, kein Logeintrag; gefunden
hat es erst der Blick in die Queue nach dem Dauerlauf-Neustart.

**Merksatz: ein Dateiname, der NICHT durch `pfade()` laeuft, ist in diesem Haus
kein Zufall.** Derselbe Satz gilt fuer `befehle`, `quelle`, `ziel` und jeden
Schreiber, den eine neue Spur braucht.

Warum kein Test das fand: es gab keinen — die Queue wurde an genau zwei Stellen
gelesen und geschrieben, ohne Gegenprobe ueber zwei Stufen. Wer eine neue
Stufen-Datei einfuehrt, schreibt den Aufruf durch `risikostufe.datei()` UND
prueft ihn ueber zwei Stufen.

## Die Queue ist ein BRIEFKASTEN, kein Protokoll

Zwei Fehler, die erst zusammen sichtbar wurden, und beide waren Folgen von
„wir pflegen sie ja" statt „sie ist ein Postfach":

**1. Der Executor war auf EINE Spur festgenagelt.** `spur = "moondev_signalwelle"`
fest im Code raeumte genau eine von dreizehn Warteschlangen ab. Die uebrigen
wuchsen unbegrenzt. Ein Werkzeug, das eine Liste namentlich verdrahtet statt
sie zu durchsuchen, verliert still, sobald eine Spur dazukommt — also genau
dann, wenn man es braucht. **Ein Sammler sammelt: er enumeriert die Dateien
selbst** (`alle_queues()` ueber `os.listdir`), statt eine Namenliste zu pflegen.

**2. Eine Verfallsregel, die nur die RUECKGABE filtert, laesst die Datei wachsen.**
`spurqueue()` hat 30-Minuten-Eintraege herausgefiltert — aber nur aus dem
Ergebnis, das es zurueckgibt; die Datei blieb unveraendert. Und der Zweig
„Auftrag bleibt liegen" (Spur hat keine Freigabe) sprang weiter, ohne neu zu
schreiben. Gemessen: eine Warteschlange stand nach einem Lauf des Executors
unveraendert bei 4441 B mit 59 Eintraegen, davon je Instrument dreimal
dieselbe Richtung.

Also drei Dinge zusammen:
- **Jeder** Zweig, auch der, der NICHT ausfuehrt, schreibt die Liste neu
  (`rest = eintraege[-20:]`) — sonst sammeln sich die abgelaufenen Eintraege
  genau dort, wo nichts passiert, also bei jeder gesperrten Spur dauerhaft.
- **Deckel** (z. B. die letzten 20). Eine Warteschlange, die unbegrenzt waechst,
  ist ein Protokoll; ein Protokoll gehoert ins Journal, nicht in den Postfach.
- **Leerraeumen**, wenn alles verfallen ist, sonst bleibt die Datei als
  scheinbar aktiver Stand liegen.

**Merksatz: eine Warteschlange, die niemand leert, ist kein Feature — sie ist
die Behauptung, es sei nichts passiert.** Genau das war an der Stelle nicht
sichtbar, wo es am meisten auffaellt: bei der gesperrten Spur, die regelmaessig
arbeitet und nie handelt.

**Merkstaende setzen, wenn eine Wache neu auf eine Spur mit Historie zeigt:**
eine frische Merkdatei hat Zaehler 0 und meldet damit JEDEN alten
Journal-Eintrag als „ERSTER EINSTIEG" — die Wache spielt die ganze Historie
nach. Vor dem ersten Lauf die Zaehler aus dem Journal setzen.

## Reihenfolge im Dauerlauf, wenn beides getrennt laeuft

Ein Zyklus macht: offene Positionen pruefen (Stop/Ziel, immer), Signale lesen,
Signalwechsel in die Queue legen, **keine** eigene Order. Die Ausfuehrung
gehoert in den Executor. Wer beides im selben Lauf laesst, hat die Trennung
gebaut und dann aufgehoben.

## Was NICHT gilt

- **Nicht** das Gatter in die Signalberechnung haengen. Es unterdrueckt dann
  Kandidaten, die spaeter ohnehin an Guthaben, Platz oder Sperrfrist
  scheitern - und beschreibt das Buch, statt den Auftrag zu verweigern.
- **Nicht** die nautilus-Arme einbauen. Sie erzeugen keine eigenen Signale,
  sie lesen Einstiege aus dem Journal der kopier-Spur; ihr Richtungswechsel
  kommt von dort.
- **Nicht** das Flag setzen und es fuer erledigt halten, wenn die Spur einen
  eigenen `handeln.py` hat. Belegen: Gatter sitzt, Testsuite der Spur
  gruen, Vorschau fehlerfrei.

## Papierbetrieb traegt das Gatter auch

xperp bleibt auf Papier (Entscheidung Max) und traegt das Gatter trotzdem:
sonst waere das Papierbuch genau die Messgrundlage, die nicht mehr gilt,
waehrend die Live-Buecher nach der neuen Regel laufen. Ein Vergleich zwischen
einer nach der neuen Regel gefahrenen Live-Spur und einer alten
Papier-Zahl fuehrt zu keinem Ergebnis.
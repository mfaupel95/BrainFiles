# Buch, Journal und Freigabe im Betrieb einer Spur

Vier Regeln, die jede Spur im Betrieb betreffen — jede ist aus einem konkreten
Fehler entstanden, der still blieb, bis jemand nachgerechnet hat.

## 1. Ein Buch fuer Papier und Live heisst: zwei Schreiber

Laeuft eine Spur mit geschlossenem Freigabefenster im Papier und mit offenem
Fenster live, fuellt SIE DASSELBE Buch. Der Papierzyklus legt Positionen ohne
echte Order an; der naechste Live-Zyklus liest sie als seine eigenen.

Folgen, alle messbar: die Plaetze sind belegt (kein Neukauf), und jeder
Ausstiegsversuch laeuft in einen Fehler, weil am Handelsplatz nichts zu
verkaufen ist. Von Hand bereinigen hilft nur bis zum naechsten Papierzyklus.

Zwei Bausteine zusammen sind die Loesung, keiner allein:

- **Aufraeumen beim Start jedes Live-Laufs**, VOR dem Ausstiegspruefen:
  Positionen ohne echte Order-ID werden zum Marktkurs als PAPIER-Verkauf
  ausgebucht (eigener Journal-Grund, damit die Bereinigung in der Historie
  erkennbar bleibt). Positionen MIT Order bleiben unangetastet. Ohne Kurs
  bleibt die Position liegen — kein stiller Verlust. Idempotent halten.
- **Ein Modus-Waechter je Position** im Live-Ausstiegspfad
  (`if p.get("modus") != "live": continue`). Wer nur den Pfad bereinigt,
  uebernimmt Altbestaende, die niemand bereinigt hat.

Beleg: das Buch hat danach genau die Positionen mit Order-ID, und der naechste
Live-Zyklus kauft wieder.

## 2. Journalzeilen: Buchung ist nicht Zeile

Beim Lesen fremder Spurenjournale nie die letzte Zeile als "Aktivitaet"
nehmen. Zwei Fallen:

- **Quote-Sammler schreiben im Takt**: `zyklus`-Zeilen mit Bid/Ask (Muster der
  Nautilus-Arme) und `quotes`-Zeilen sind Betriebsnotiz, kein Handel. Eine Spur
  sieht damit "frisch" aus, obwohl sie seit Wochen nicht handelt.
- **Die Schemata unterscheiden sich.** Die meisten Spuren schreiben eine
  `aktion`-Spalte (`kauf`/`verkauf`/`eroeffnen`/`schliessen`); manche (ORB-Spur
  und ihre Verwandten) schreiben `einstieg`/`ausgang` OHNE `aktion`. Ein Leser,
  der nur auf `aktion` prueft, meldet fuer diese Spur "hat nie gehandelt",
  obwohl Zeilen im Buch stehen.

Regel fuer Leser: `aktion` der bekannten Menge hat Vorrang; fehlt die Spalte
oder ist sie leer, gilt eine Zeile mit Inhalt in `einstieg`/`ausgang`/`preis`/
`einsatz`/`menge` als Buchung. `zyklus`, `quotes`, `funding`, `rollover`
bleiben in beiden Schemata Notiz.

## 3. Der eigene Sperr-Text ist die Schnittstelle zur Freigabe

Der Dauerlauf entscheidet ueber eine Freigabe-Anfrage (und ueber die
automatische Freigabe) anhand der `--vorschau`-Zeile der Spur: er verlangt
GENAU EINEN Grund, und in diesem Grund muss das Wort **Freigabefenster**
vorkommen.

Daraus folgt:

- Eine Spur, die in der `--vorschau` **keinen** Grund nennt ("gesperrt durch:
  nichts"), wird NIE von selbst scharf geschaltet — sie wird nicht einmal
  gefragt. Eine vollstaendig bereite Spur braucht deshalb eine eigene Zeile, die
  das fehlende Fenster als Blocker nennt.
- Nennt die Vorschau **zwei** Gruende (z. B. Guthaben UND Fenster), wird nicht
  gefragt: erst muss der andere Blocker weg sein.
- Spuren ohne Live-Pfad nennen einen Grund, der das Wort "Freigabefenster"
  NICHT enthaelt, damit keine Anfrage entsteht.
- Der Sperr-Text darf das Wort also nicht zufaellig enthalten und nicht
  zufaellig vermissen — er ist keine Meldung, sondern eine Schnittstelle.
- Konsequenz fuer den Nutzer-Hinweis: wer einen Blocker beseitigt (Guthaben
  auffuellen), schaltet damit je nach Lage auch das automatische Scharfschalten
  scharf. Immer BEIDES nennen: was jetzt geht und was daraus folgt.

## 4. Stille Spuren gehoeren namentlich in den Bericht

Eine Zeile "N Spuren still: ..." nennt acht Namen und sagt nicht, welche Spur
seit einer Stunde und welche seit drei Wochen nichts tut — genau der
Unterschied zwischen "ruhig" und "kaputt".

- Pro stiller Spur eine Zeile mit dem Alter der letzten **Buchung** (Regel 2),
  nicht der letzten Zeile, plus dem `handel_erlaubt` der Wache.
- Drei Faelle getrennt benennen: "letzte Buchung vor N Tag(en)", "kein
  Journal" (Spur hat nie gebucht), "Journal traegt nur Kurse" (Zeilen da,
  aber kein Handel).
- Ein geteilter Schluessel muss ausgeschrieben werden: laufen zwei Arme unter
  demselben Schluessel (Spot/Futures derselben Boerse), erscheint der Name
  sonst zweimal identisch in der Liste.
- Der Wachen-Schalter steckt nicht immer dort, wo man ihn erwartet: das
  Lagebild kann `wachen` leer lassen und die Datei woanders tragen — beide Orte
  lesen, sonst bleibt die Spalte stumm.

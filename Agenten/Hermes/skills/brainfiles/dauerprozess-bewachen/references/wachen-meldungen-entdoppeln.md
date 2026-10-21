# Wachen-Meldungen entdoppeln: nach Klasse, nicht nach Text

Eine Wache soll dieselbe Feststellung nicht wiederholen. Der naheliegende Weg —
den Meldungstext merken und nur bei Aenderung senden — versagt genau dann, wenn
der Text einen MESSWERT traegt.

## Die Regel

- **Schluessel = KLASSE der Feststellung, Zahlen nur im Text.** Traegt die Meldung
einen gerechneten Wert (Notional, Kurs, Alter in Minuten, Kontostand), ist sie bei
  jedem Tick "neu" und die Wache feuert dauerhaft.
- **Klassifizieren an EINER Stelle**: eine Funktion `ist_<klasse>(text)`, die
  Regel und Text zusammenhaelt. Zwei Stellen, die dieselbe Klasse erkennen, laufen
  auseinander, sobald ein Aufrufer den Text anders formatiert.

## Erwartete Zustaende als normal einordnen

Manche Meldungen sind kein Defekt, sondern der Betrieb:
Ablehnung durch einen Positions- oder Nominaldeckel, Wartezeit eines
Freigabefensters, "kein Signal" einer Strategie.

- Sie werden GEZAEHLT und hoechstens **einmal pro Tag in einer Zeile** genannt.
- Gemeldet wird nur, was FEHLT oder KAPUTT ist: Position ohne Schutz, Prozess tot,
  Order ohne Fill, Mengendrift, fehlende Datei.
- Warum das nicht Kosmetik ist: ein Tagesbudget fuer Meldungen wird von der
  Rauschklasse zuerst verbraucht. Sind die sechs erlaubten Meldungen um 10 Uhr
  durch Deckel-Ablehnungen weg, schweigt die Wache fuer den Rest des Tages — auch
  als die Position wirklich nackt war. Laerm ist hier ein Sicherheitsverlust, keine
  Meinungsfrage.

## Merkdatei nach einem Neustart des ueberwachten Laufs zuruecksetzen

- Zaehler (`orders_seen`, `rejected_seen`) beschreiben einen konkreten Lauf. Nach
  einem Neustart vergleicht die Wache sonst den NEUEN Lauf mit dem alten Stand:
  die erste echte Order des neuen Laufs liegt unter dem alten Zaehler und wird
  verschluckt.
- Das Tagesbudget (`meldungen`) ebenfalls zuruecksetzen — sonst ist der neue Lauf
  fuer den Rest des Tages stumm.
- Die Merkdatei gehoert nach `Agenten/Hermes/cache/`, nicht in einen Unterordner
  der Wachen-Skripte.

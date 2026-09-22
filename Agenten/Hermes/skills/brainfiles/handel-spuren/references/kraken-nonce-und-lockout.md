# Kraken: Invalid nonce und Temporary lockout

Stand 20.09.2026. Reihenfolge der Pruefung, damit nicht stundenlang die
falsche Ursache gejagt wird.

## Erst den Kontostatus, dann den nonce

`EAPI:Invalid nonce` und `EGeneral:Temporary lockout` sehen im Log
aehnlich aus, haben aber nichts miteinander zu tun. Eine Serie
fehlgeschlagener Privataufrufe fuehrt zur **Sperre des Schluessels**.
Danach wird JEDER nonce abgelehnt - auch ein korrekter.

Deshalb: bei wiederholten nonce-Fehlern zuerst pruefen, ob ueberhaupt
noch etwas durchgeht. Ist die Antwort `Temporary lockout`, ist jede
weitere Sonde schaedlich (sie verlaengert die Sperre) und jede Messung
wertlos (sie misst die Sperre, nicht den nonce).

## Nicht sondieren, sondern warten

Sweeps ueber Zeitfenster (`srv-600s` bis `srv+10000s`) beweisen nichts,
solange die Sperre steht, und jeder Treffer wuerde den serverseitigen
nonce-Peak weiter hochtreiben. Richtig ist eine Wache, die **genau
einen** Abruf pro Stunde macht und nur den Uebergang meldet
(`Agenten/Hermes/scripts/kraken-lockout-wache.py`).

## nonce-Regeln, die bleiben

- Ein Schluessel, mehrere Programme: nur mit **gemeinsamem** persistentem
  nonce-Zaehler (`Agenten/Handel/kraken/nonce_pool.py`, O_EXCL-Sperrdatei).
  Zwei Prozesse mit eigener Wallclock ueberholen sich sonst gegenseitig.
- Monotone Wallclock ist die bewaehrte Basis. Ein "Drift-Abzug" gegen die
  Kraken-Serverzeit klingt richtig, senkt den nonce aber unter den bereits
  gespeicherten Peak - danach geht gar nichts mehr.
- Alte Prozesse halten ihren Code im Speicher. Ein nonce-Fix wirkt erst,
  wenn ALLE Sender neu gestartet sind (Dauerlaeufe, MCP-Server, Gateway).

## Nach dem Ende der Sperre: erst messen, dann urteilen

Die Sperre laeuft von selbst ab (Minuten bis Stunden), **ohne dass am Code
etwas geaendert wird**. Der erste erfolgreiche Leseaufruf danach ist deshalb
der Beweis, dass nonce-Pool und Schluessel in Ordnung waren - nicht der Beweis,
dass eine Reparatur gewirkt hat.

- Solange die Sperre steht, ist "der nonce-Code ist kaputt" **unbewiesen**:
die Sperre lehnt jeden nonce ab. Eine neue Schluessel-Empfehlung ist eine
  Absicherung, kein belegter Befund - im Bericht so benennen.
- Nach dem Ende der Sperre den **ersten Leseaufruf** als Beleg nehmen
  (`guthaben()` liefert eine Zahl statt einer Ausnahme).
- **Die Sperre war ein versteckter Blocker der Spuren.** Ein Guthaben-Tor
  ("nur X frei, noetig Y") kann waehrend der Sperre gar nicht anders antworten.
  Nach dem Ende der Sperre `handeln.py --vorschau` erneut laufen lassen: faellt
  "Live waere gesperrt durch: nichts", ist die Spur ohne Code-Aenderung frei -
  und der naechste Zyklus handelt. Nie einen Blocker aus der Sperrzeit
  weitererzaehlen.
- Eine Wache auf einen solchen Zustand ist nach dessen Ende entbehrlich; sie
  abzuraeumen ist Teil des Abschlusses. Der Merker, dass mehr als EIN Abruf je
  Stunde die Sperre verlaengert, bleibt gueltig.

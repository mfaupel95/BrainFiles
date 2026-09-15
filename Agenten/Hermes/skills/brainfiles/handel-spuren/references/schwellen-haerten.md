# Schwellen und Wachen einer Spur haerten

Das Verfahren, mit dem die Schutzwerte einer Spur (Drawdown-Ratsche,
Kill-Switch, Positionsgrenzen) vertrauenswuerdig werden. Die PITFALLS dazu
stehen in SKILL.md; hier steht die REIHENFOLGE.

Ausloeser: eine Spur soll schaerfer abgesichert werden, ein Wert "wirkt nicht",
oder eine Spur soll live gehen.

## 1. Zuerst die Risikoskala der Spur feststellen

Nicht den Kapitalrahmen lesen, sondern: **was verliert die Spur, wenn JEDE
offene Position gleichzeitig den Stop trifft?** Das ist das BUCHRISIKO, die
einzige Groesse, in der ein Gewinnruecklauf spuruebergreifend vergleichbar ist.

Zwei Zahlen, beide noetig:

- Risiko je Position
- Hoechstzahl Positionen

Die Schluesselnamen unterscheiden sich je Spur (`risiko_je_position_usd`,
`risiko_je_anlauf_usd`, `risiko_pro_trade_usd`, `risiko_je_position_eur`, …).
Deshalb traegt `Handel/ratschen.py` eine Liste `BUCHRISIKO_PAARE` — wer eine
neue Schreibweise einfaerbt, traegt sie DORT ein, sonst meldet das Pruefskript
weiter "nicht herleitbar".

Nennt eine Spur nur eine der beiden Zahlen, fehlt die andere. Beide Luecken
sind im Bestand vorgekommen und haben je eine andere Antwort:

### Fehlende Positionszahl -> strukturelle Tatsache aus dem Code

Nicht raten, sondern nachsehen, wie viele Positionen die Spur ueberhaupt halten
KANN. Steht die Position als einzelnes Dict im Zustand (`z["position"]`,
Zuweisung statt `append`, geprueft mit `if not z.get("position")`), dann ist 1
die Wahrheit — kein neuer Deckel, sondern eine Beschreibung. Im `_`-Kommentar
genau so benennen und dazuschreiben, dass die Handelslogik den Schluessel NICHT
liest und den Platz bauartbedingt nicht ueberschreiten kann. Wer dort je mehr
eintraegt, muss die Spur erst auf eine Positionsliste umbauen.

### Fehlendes Risiko je Position -> Hoechstfall herleiten

Ist die Spur **nicht** risikonormiert (sie kauft fix einen Nominalbetrag),
steckt ihr Risiko im Stop: `Nominal x pflicht_stop_prozent_max / 100`. Der
tatsaechliche Wert schwankt je nach Stop; fuer eine SCHUTZschwelle ist der
HOECHSTE Fall der richtige. Ein Mittelwert liesse die Ratsche zu spaet ausloesen
— die Schutzgrenze muss im schlimmsten Fall noch greifen, nicht im mittleren.

## 2. Herleiten statt waehlen

Ein Schutzbetrag, den jemand ausgesucht hat, kann von der Regel ablaufen, der
er folgen soll. Ein hergeleiteter kann das nicht. Also: herleiten und den
hergeleiteten Wert AUSDRUECKLICH hinschreiben — das ist kein Widerspruch,
sondern die Kombination, die zaehlt:

- Der ausdrueckliche Betrag hat Vorrang, damit er sich nicht von selbst
  verschiebt, wenn jemand an Risikozahlen dreht.
- Das Pruefskript rechnet nach, dass er noch der Regel entspricht.

Drift wird damit sichtbar statt still.

## 3. Kein Wert ohne Herkunft im `_`-Kommentar

Jeder nicht offensichtliche Betrag in einer `wachen.json` bekommt ein
`_`-Praefix-Kommentarfeld, das die Rechnung nennt (Operanden, Ergebnis, und was
sich aendert, wenn jemand daran dreht). Sagt ein Wert nur "15 %", ist er
unpruefbar; sagt er "1.0 x Buchrisiko = 6.0 x 4 = 24.00", kann ihn jeder
nachrechnen.

## 4. Warnen statt ausloesen

Ein Fehlwert darf den Handel NICHT drosseln — er muss nur sichtbar sein:

- Fehlt jede Schwelle, bleibt der Groessenfaktor 1.0 (nicht 0.5!). Eine
  stillschweigende Ersatzschwelle sieht aus wie Schutz und ist keiner.
- Eine Schwelle von 0 oder darunter ist keine Linie, die man ueberschreiten
  kann; sie wird wie KEINE Schwelle behandelt.
- Die Anzeige nennt den Zustand ("keine Ratsche konfiguriert"), statt ihn zu
  verschweigen.

## 5. Erreichbarkeit richtig pruefen

Der Fehler, der hier am teuersten ist: **"unerreichbar" zu behaupten.** Ein
Drawdown-Ruecklauf ist `Hoechststand - kumulierter Stand`, und der kumulierte
Stand darf ins MINUS laufen — der Ruecklauf waechst also ueber den
Hoechststand hinaus. Eine Schwelle ueber dem Hoechststand ist damit nicht
unerreichbar; sie greift nur erst, nachdem die Spur mehr verloren hat als sie je
gewonnen hatte, und schuetzt dann keinen GEWINN mehr, sondern faengt einen
Nettoverlust — dafuer ist der Kill-Switch da.

Die richtige Frage heisst deshalb: **greift die Halbierung noch, SOLANGE die
Spur im Gewinn ist?** (Feld `halbierung_im_gewinn`.) Vor jeder Aussage ueber
eine "tote" Schwelle die Rechnung zeigen: bei welchem Stand greift sie? Wie
weit muss die Spur ins Minus? Eine Behauptung ohne diese zwei Zahlen ist eine
Vermutung.

## 6. Jede Spur muss ihre Risikoskala nennen koennen

Eine Spur, die ihr Buchrisiko nicht aus eigenen Zahlen nennen kann, kann keine
hergeleitete Schutzschwelle tragen. Das ist ein Befund, kein Detail — er gehoert
an den Nutzer, mit der fehlenden Zahl benannt: "orbk hat Risiko, aber keine
Positionszahl; kraken hat Positionen, aber kein Risiko je Position."

## 7. Das Pruefskript ist der eigentliche Schutz

`Handel/pruefe_ratschen.py` ist die stehende Gegenprobe. Zwei Eigenschaften
machen es wertvoll, zwei weitere sind Pflicht:

- Es befragt jede Spur ueber ihr EIGENES `lage()` — eine nachgebaute Formel
  prueft die Formel, nicht die Spur.
- Es liest die Schwellen aus der geteilten Umsetzung (`ratschen.py`), nicht aus
  einer zweiten Kopie der Rechnung.
- Pflicht: die Wachen der Spur wirklich uebergeben. `lage({}, journal, {})`
  wirft `KeyError` — eine leere Konfiguration ist keine gueltige Konfiguration,
  und ein Fehler dort darf nicht als "greift" durchgehen.
- Pflicht: ein Fehler ist ein BEFUND, kein stiller Durchlauf. Wer beim Befragen
  scheitert, gehoert in die Problemzeile — sonst meldet das Skript
  "alle in Ordnung", waehrend es vier von fuenf Spuren gar nicht geprueft hat.

Tests, die den Betriebswert festhalten, gehoeren dazu (`tests/test_ratschen.py`):
je Spur der erwartete Betrag, plus ein Test, dass keine Spur wieder ohne
herleitbares Buchrisiko dasteht. Aendert man einen Betrag, faellt der Test — und
das ist gewollt: dann gehoert das Pruefskript mitgelesen.

## 8. Der Stand aller fuenf Spuren (15.09.2026)

Alle fuehren einen HERGELEITETEN Betrag, alle 1.0 x Buchrisiko:

| Spur | Risiko je Position | Plaetze | Buchrisiko | Schwelle | vorher |
|---|---:|---:|---:|---:|---:|
| scanner | 6.0 USD | 6 | 36.00 | 36.00 | 60.00 |
| xperp | 7.5 USD | 4 | 30.00 | 30.00 | 30.00 |
| swap | 7.5 USD | 4 | 30.00 | 30.00 | 30.00 |
| orbk | 10.0 USD | 1 | 10.00 | 10.00 | 22.50 |
| kraken | 6.0 EUR | 4 | 24.00 | 24.00 | 30.00 |

Jede Aenderung war eine VERSCHAERFUNG. Wer Zahlen senkt, muss dazusagen, dass er
strenger wird — "angepasst" klingt nach beiden Richtungen.

Ruhend und nicht geprueft: `orb`. `nautilus` hatte den Schluessel, aber kein
`groessenfaktor()` — tote Konfiguration in einem EIGENEN Repo.

## 9. Die Spalten des Pruefskripts lesen

`pruefe_ratschen.py` gibt je Spur aus: Herkunft, Schwelle, Buchrisiko, `1.0x?`,
Hoechststand und ob die Schwelle noch IM GEWINN greift.

- `ausdr.+herl.` heisst: der Betrag steht ausdruecklich da UND ist herleitbar.
  Nur `ausdruecklich` ohne Zusatz heisst: er steht da, aber niemand kann ihn
  nachrechnen — genau der Zustand, der behoben gehoert.
- `n/a` in der Spalte `1.0x?` heisst NICHT "in Ordnung", sondern "das Buchrisiko
  ist nicht herleitbar" — eine Eingabe fehlt und ist im Code nachzusehen.
- Ein neuer Schluesselname, der in `BUCHRISIKO_PAARE` fehlt, laesst die Spur
  `n/a` melden, OBWOHL die `wachen.json` stimmt. Genau das passierte mit
  `risiko_je_position_eur`: erst der Eintrag in der Paarliste holte kraken aus
  dem `n/a`.

## 10. Ein Befund ist erst ein Befund, wenn die Fundstelle gezeigt ist

Zwei Fehlurteile aus derselben Woche, beide teuer, weil sie nach Arbeit klangen:

- "kein Code liest X" aus einer zu engen Suche — die Import-Kette fehlte (siehe
  `sicherungen-pruefen.md`).
- Umgekehrt: `max_gesamt_risiko_usd` in omniquant wurde fuer TOT erklaert
  ("taucht in handeln.py nirgends auf"), tatsaechlich wird es als Kill-Switch
  gelesen UND `verluste_usd` wird erhoeht. Der Befund stammte aus einer
  Kartierung und war schlicht falsch.

Regel: **Schreiben und Lesen sind zwei verschiedene Fragen.** Nach einem
`search_files` auf den Schluessel jeden Treffer ansehen und trennen — wird er
GESETZT? wird er VERGLICHEN? Erst dann ein Urteil. Bei fremder Vorarbeit (auch
von Subagenten) die tragende Behauptung einzeln nachfahren, bevor sie in einen
Bericht wandert: eine Kartierung ist eine gute Landkarte, aber kein Beleg.

## Reihenfolge in Kurzform

1. Buchrisiko herleiten (beide Faktoren; fehlende aus dem Code beschaffen)
2. Betrag herleiten und ausdruecklich hinschreiben
3. `_`-Kommentar mit der Rechnung
4. Warnen statt ausloesen
5. `halbierung_im_gewinn` pruefen, nicht "erreichbar"
6. Pruefskript + Tests fahren, Fehler als Befund melden
7. Gespiegelten Stand gegenpruefen (`spiegelstand.py`), erst dann committen

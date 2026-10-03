# Sicherungen, Schwellen und Pruefwerkzeuge

Fuer alles, was eine Spur ABSICHERT statt sie zu handeln: Drawdown-Ratschen,
Kill-Switches, Deckel, Positionsgroessen-Faktoren — und fuer die Werkzeuge, mit
denen man prueft, dass diese Sicherungen ueberhaupt greifen koennen.

## Eine Sicherung, die nie greift, ist keine Sicherung

**Der Ausloeser gehoert in einen ABSOLUTEN Betrag, nicht in eine Quote von einer
fremden Groesse.** Beispiel: die Drawdown-Ratsche rechnete
`drawdown_halbierung_prozent/100 * max_gesamt_usd`. Sie misst aber den Ruecklauf
der realisierten GEWINNKURVE — der Kapitaldeckel ist eine davon unabhaengige
Groesse. Als der Deckel von 400 auf 1000 stieg, wanderte die Schwelle lautlos von
60 auf 150 USD, ohne dass jemand die Ratsche angefasst haette. Wer eine Sicherung
an einen Nenner koppelt, den ein anderer Zweck steuert, verschiebt sie bei jeder
fremden Aenderung mit.

Deshalb: absoluten Wert fuehren (`drawdown_halbierung_usd`). Der Prozentsatz
`drawdown_halbierung_prozent` ist am 15.09.2026 aus ALLEN Spuren ENTFERNT worden
und wird nirgends mehr gelesen — auch nicht als Rueckfallwert. Zwei Wege zu
derselben Zahl sind zwei Stellen, die auseinanderlaufen, und ein "Rueckfall"
waere genau die Fremdgroessen-Kopplung, die hier verboten ist.

Ein Test haelt das: die Schwelle darf den Gewinnhoechststand nicht
dauerhaft unterschreiten, ohne dass es gemeldet wird. Faellt er, gehoert das
Pruefskript mitgelesen.

## Ein Stop in PROZENT kann nicht als fester Betrag eingetragen werden

Eine Ansage wie „Stop 60“ ist eine Prozentangabe. Traegt die Spur nur
`stop_usd` — einen **festen Betrag** — kann sie nicht treu umgesetzt werden,
weil der Einsatz je Position schwankt: bei 30 USD Einsatz sind 18 USD genau 60 %,
bei 90 USD (drei Kaeufe auf denselben Token) sind dieselben 18 USD nur noch 20 %.
Die Zahl „60“ verschwindet ersatzlos, ohne dass jemand sie angefasst haette.

Gemessen: die Bilanz einer Kopier-Spur wurde von 13 Stop-Runden mit 0 Treffern
und −537 % dominiert, alle unter der alten Absolutschwelle. Der Auftrag lautete
„Stop 60 %“; `stop_usd: 18` haette ihn an der groessten Position nicht erfuellt,
ohne dass eine Meldung das gezeigt haette.

- **Traegt die Wache beide Felder, hat das PROZENT Vorrang**, der feste Betrag
  ist Rueckfall (`if stop_pct: … elif stop_usd:`). Zwei Wege zur selben Zahl sind
  die Fremdgroessen-Kopplung von oben — der Betrag darf den Vorrang nie bekommen.
- **Beim Eintragen die groesste UND die kleinste Position gegenrechnen**, nicht
  die mittlere. Der groesste Einsatz ist `max_einsatz_je_kauf_usd x
  max_kaeufe_je_token`; genau dort weicht die Prozentzahl am weitesten vom
  eingetragenen Betrag ab.
- **Ein datierter Vermerk neben dem Wert**, der die Einheit nennt („18.00 USD =
  60 % von max_einsatz_je_kauf_usd 30“) — sonst liest der naechste die Zahl und
  nimmt die Prozentangabe an.
- **Gegenprobe vor dem Setzen:** je eine Position mit kleinem und mit
  grossem Einsatz durch die Ausstiegsrechnung schicken. Feuert der Stop bei
  beiden gleich, ist die Zahl richtig uebertragen.

Sonderfall Kopier-Spuren: dort ist der Stop in USD absolut, waehrend die Kosten
(1 % Gebuehr + 5 % Slippage je Seite) im Kurs stecken. Ein Stop bei 60 % Verlust
auf den ERTRAG feuert deshalb schon bei rund 59 % **Kursverlust**. Beide Zahlen
nennen, sonst meint der Leser „60 %“ und der Code rechnet 48 %.

## 'Zu locker' ist nicht 'abgeschaltet' — die Kurve darf ins Minus

Der wichtigste Denkfehler an dieser Stelle, weil er einen ganzen
Sicherungskonzept-Fehlschluss erzeugt:

`drawdown()` rechnet `hoch - kum`. `kum` startet bei 0 und kann NEGATIV werden.
Der Ruecklauf ist damit nach unten **nicht** durch den Hoechststand begrenzt —
eine Schwelle ueber dem Hoechststand ist NICHT unerreichbar.

Konkret: Hoechststand 140.24 USD, Schwelle 150 USD. Das greift, sobald die Spur
bei **-9.76 USD** steht — also erst, nachdem sie mehr verloren hat, als sie je
ewonnen hatte. Die richtige Beschreibung ist:

> Die Halbierung greift erst nach Verlust ueber den Nullpunkt und schuetzt damit
> keinen Gewinn mehr, sondern faengt nur noch einen Nettoverlust — dafuer ist der
> Kill-Switch da.

NICHT: 'unerreichbar' / 'abgeschaltet' / 'kann nie ausloesen'. Der Unterschied
entscheidet, ob die Korrektur eine Zahl aendert oder ein Sicherungskonzept, und
er entscheidet darueber, ob man einen Test auf eine Regel baut, die es nicht gibt.

Konsequenz fuer die Benennung: `halbierung_erreichbar` war falsch und wurde zu
`halbierung_im_gewinn`; die Anzeige 'NICHT AUSLOESBAR' wurde zu 'greift erst nach
Verlust ueber den Nullpunkt'. Ein Flag-Name, der die falsche Aussage weitertraegt,
ueberlebt jede spaetere Korrektur des Textes.

Die Grenze haengt NUR am Hoechststand, nie am aktuellen Ruecklauf. Sonst steht die
Warnung neben 'Faktor 0.50' und widerspricht sich selbst.

## Ein Kill-Switch kann GEWINNENDE Positionen schliessen

Der Kill-Switch feuert auf den KUMULIERTEN Ruecklauf vom realisierten
Hoechststand, nicht auf die aktuelle Position. Deshalb kann er Positionen
schliessen, die gerade IM PLUS stehen: er schuetzt den realisierten Gewinn, nicht
den aktuellen Stand. Belegt (xperp, 21./25.09.2026): alle fuenf
kill_switch-Ausstiege waren +0,4 % bis +2,4 % — der Kill realisierte Gewinne,
weil der Ruecklauf vom Peak den Deckel erreicht hatte.

Bei der Diagnose 'warum hat der Kill gefeuert' also die KUMULIERTE
Drawdown-Kurve (FIFO-gepaart, `hoch - kum`) ansehen, nicht die einzelne
Position. Ein Kill, der Gewinner schliesst, ist kein Fehler, sondern ein zu
aggressiver Schutz — der Deckel ist dann die Stellschraube, nicht der Code. Ein
hoher Deckel (weit ueber dem je erreichten Ruecklauf) entschaerft ihn de facto.

## Sicherungen sichtbar machen

Eine Sicherung, die man in der Ausgabe nicht sieht, kann man nicht pruefen. Der
Status gehoert in dieselbe Anzeige wie der Rest:

```
  2 Ruecklauf      28.43 USD von Hoechststand 140.24  -> Faktor 1.00
    Halbierung ab  60.00 USD
```

Zwei Regeln dabei: die Anzeige darf beim Nachrechnen nicht abstuerzen (alte
Zustandsdatei) — also `.get()` mit Vorgabe statt `[...]`; und die Warnzeile muss
den echten Mangel benennen, nicht den vermuteten.

## Vier Nenner fuer dieselbe Zahl

Alle Spuren fuehren `drawdown_halbierung_prozent: 15.0`, aber mit verschiedenen
Nennern: `max_gesamt_usd`, `max_margin_gesamt_usd`, `kill_switch_gesamt_usd`,
`max_gesamt_eur`. Dieselbe Zahl bedeutet je Spur einen anderen Betrag (und `orb`
rechnet auf `kill_switch_gesamt_eur`). Je Spur fuer sich kann das richtig sein —
bei einer Spur entsprach die Schwelle exakt einem vollen Buch-Stop-Auslauf
(`risiko_je_anlauf_usd 7.5 x max_offene_anlaeufe 4 = 30 USD`, und genau 15 Prozent
von `max_margin_gesamt_usd` 200). Vor dem Bewerten also immer erst den Nenner der
jeweiligen Spur feststellen, bevor die Zahl beurteilt wird. Eine Spur mit kleinem
Gewinnhoechststand meldet 'greift erst im Minus' allein aus Jugend — das ist kein
Defekt.

Erst messen, DANN bewerten: `pruefe_ratschen.py` befragt jede Spur ueber ihr
eigenes `lage()`, gibt Schwelle, Hoechststand, Ruecklauf und Faktor aus und nennt
zum Schluss, welche Spuren erst im Minus greifen.

## Ein Pruefwerkzeug befragt das ECHTE Gegenueber

Ein Skript, das die Formel nachbaut, prueft die Formel — nicht die Spur. Wer
wissen will, ob eine Sicherung im Betrieb wirkt, ruft die Funktion der Spur auf,
die auch im Dauerlauf laeuft.

Zwei Pflichten, sonst ist das Werkzeug schlimmer als keines, weil sein 'alles in
Ordnung' geglaubt wird:

1. **Die Erfolgszeile nur drucken, wenn NULL Fehler auftraten.** Eine
   Zusammenfassung, die nur EINEN Fehlermodus zaehlt, meldet sonst Erfolg,
   waehrend jeder Fall mit einer Ausnahme abgebrochen ist. Fehler und Befunde in
   getrennten Listen fuehren und beide ausgeben.
2. **Je Fall melden, was NICHT geprueft werden konnte**, mit Grund.

Vor dem ersten echten Lauf gegenpruefen, dass das Werkzeug auch ROT bekommt:
Wert verstellen, Fehlschlag zeigen, zuruecksetzen. Ein Pruefwerkzeug, das nie rot
war, ist ungeprueft.

## Keine Negativ-Aussage aus einer abgeschnittenen Suche

'Kein Skript liest X' ist eine harte Behauptung und braucht einen vollstaendigen
Trefferzaehler, nicht das Ende einer Liste. Drei Fallen:

- `grep -rn ... | head -20` schneidet genau die Datei ab, die den Treffer traegt,
  der die Aussage widerlegt.
- Ein Filter wie `grep -v '^.*_'` wirft jede JSON-Zeile weg, weil Schluesselnamen
  Unterstriche enthalten — die Suche sieht dann leer aus und ist es nicht.
- Eine Spur liest ihre Werte oft nicht selbst, sondern erbt sie. `swap/handeln.py`
  enthaelt den String der Ratsche nirgends; es importiert `wachen_xperp` und
  reicht `s['groessenfaktor']` weiter. Eine Suche im Spurordner findet sie nie.

Reihenfolge: Treffer ZAEHLEN (`grep -c`), dann lesen, dann die Import-Kette
mitgehen, dann erst schlussfolgern.

## Ein Limit kann von einem anderen Limit verdeckt werden

Bei risiko-normiertem Sizing gibt es mehrere Deckel gleichzeitig (je Position,
Gesamtkapital, Anzahl Plaetze, Risiko je Position). Ein erhoehtes Limit kann
WIRKUNGSLOS sein, weil ein anderes bindet: 1000 USD Gesamtdeckel auf ein Buch,
dessen groesstmoegliches Volumen `max_offene_positionen x risiko /
pflicht_stop_prozent_min` = 6 x 120 = 720 USD ist, bindet nie. Vor jeder
Limit-Aenderung die Obergrenze der JEWEILS anderen Limits ausrechnen und nennen,
welches tatsaechlich greift.

Ein Deckel kann umgekehrt eine Normierung halbieren: `nominal = risiko / stop_pct`
wirkt nur, soweit der Positionsdeckel es laesst — enge Stops laufen in den Deckel
und behalten ein zu kleines Risiko, weite werden sauber normiert. Nach dem Einbau
die Spannweite MESSEN statt die Vereinheitlichung anzunehmen.

Abgeleitete Werte gehoeren HERGELEITET, nicht gegriffen: der Positionsdeckel ist
`risiko_je_position_usd / (pflicht_stop_prozent_min/100)` und nicht die naechste
runde Zahl daneben. Ein Test, der die HERLEITUNG prueft (`Deckel >=
risiko / stop_min`) statt den Wert, faellt bei der naechsten Aenderung der
Risikozahl mit der noetigen Zahl in der Meldung.

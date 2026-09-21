# Bericht: mehrere Buch-Spuren als EIN Block (Holer-Aggregation)

Mehrere Papierbuecher, die dieselbe Signalquelle teilen (Spiegel + Schattenbuecher
+ Kopier-Spuren), gehoeren im Bericht als EINE Familie zusammen, je Buch eine
schlanke Zeile statt jeder Position. So baut man den Aggregations-Holer richtig.

## Der saubere Aufbau (familie-Holer)

- **Positionen aller Buecher bleiben in `positionen`** (konkateniert), auch wenn
der Render sie nicht aufzieht. Der Schnappschuss, die "N offene Position"-Summe
und der Stille-`rang` lesen `positionen` — ein positionen-freier Block verlccre
Taeglicher Diff und die Gesamtsumme still.
- Je Buch eine Zusammenfassung in einem SEPARATEN Feld (`familie`: name, offen,
bilanz). Die Zeile zeigt, was zaehlt: offen, Runden/Ausstiege, Ergebnis nach
Kosten und **Trefferquote** (die steht in `auswertung.kernzeile`, z.B.
`Treffer 258/1012`). Keine zweite Formel: die `bilanz` jedes Buchs kommt aus
`lage._bilanz`/`kernzeile` — derselben, die der Bericht sonst zeigt.
- Im Render (`tagesbericht._block`) frueh eine Familie-Verzweigung schalten
(`if s.get("familie") is not None`) und VOR der generischen
Positionenschleife per `return` beenden. `rang()` bleibt aktiv, weil
`positionen` wahr belegt ist.

## Falle 1: `zu_lage` verwerft eigene Felder still

`lage.zu_lage(roh, schluessel)` normalisiert jede spur_*-Rueckgabe auf eine
FESTE dict — Felder, die nicht in dieser Form stehen, werden **stillschweigend
geloescht**. Auch der Familie-Zweig in `_block` findet ein handgesetztes
`familie`-Feld nie, wenn `erhebe()` ueber `zu_lage` laeuft: der Block faellt
dann in die generische Positionen-Liste zurueck, ohne Fehler.
Fix: das Render-Feld (und seinen Zaehler) in `zu_lage` ausdruecklich
**durchreichen**: `"familie": roh.get("familie")`.

## Falle 2: Test durch den ECHTEN Pfad, sonst maskiert er den Fehler

Ein Unit-Test, der einen handgebauten spur-dict direkt an `_block` schickt,
ist grund gruen und verdeckt die `zu_lage`-Falle (der Test lief nicht durch die
Normalisierung). Der Render-Test muss `roh` -> `lage.zu_lage(roh, None)` ->
`_block` laufen UND `assertEqual(spur["familie"], roh["familie"])` verlangen —
erst das beweist, dass das Feld den echten Pfad ueberlebt.

## Falle 3: kein `ordner` mit SPUREN-Ordnernamen

`_schluessel_von(roh)` leitet den Schnappschuss-Schluessel aus dem
`ordner`-Basenamen her, wenn der in `auswertung_alle.SPUREN` steht. Ein
Aggregations-Holer, der `ordner=spiegel` setzt, kollidiert damit im
Schnappschuss mit dem Hauptbuch. Den Aggregat-Holer **ohne `ordner`** bauen
(Schluessel None → der Bericht schluesselt ueber den Namen); `zu_lage` braucht
fuer ihn nur `name/waehrung/positionen/w/bilanz`, und `pruefmodul=None` haelt
die fremde Wachenrechnung fern.

## HOLER-Zaehltests koennen schon rot sein, wenn eine Fremdsitzung anfasst

ein `test_holer_sind_vollzaehlig`-Zaehler bricht, sobald die andere Sitzung
Holer hinzufuegt ohne den Zaehler mitzuziehen. Beim Umbau die IST-Zahl per
`len(lage.HOLER)` messen, nicht aus dem Kommentar glauben; fremde aenderungen
sieht man erst im diff.

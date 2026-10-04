# Ziel-Geometrie und Hebel — die zwei Rechnungen, die jede neue Spur braucht

Zwei Fragen kommen bei jeder Spur, deren Ziel kein Vielfaches des Stops ist
(„Marktpunkt", Zone, Wand, Niveaus): **Ist der Zielabstand gross genug gegen die
Gebuehr?** Und **Was aendert der Hebel?** Beide sind eine Rechnung, keine
Gefuehlsache — und beide beantworten sich aus dem Journal der Spur selbst.

## 1. Zielabstands-Boden: die Gebuehr ist eine Untergrenze, keine Nuance

**Regel.** Kein Einstieg, dessen Abstand zum Ziel kleiner ist als die
Rundengebuehr. Steht als `min_ziel_abstand_pct` in der Wachen, gespiegelt in
beide Richtungen der `signal()`.

**Warum.** Eine Regel mit beidseitigem Abstand ohne UNTEREN Rand liest sich wie
„long unter der Wand, short darueber" und bedeutet in der Praxis „long wenn der
Kurs 0,015 % darunter steht". Das ist kein Signal, das ist ein Handgriff neben
der Gebuehr.

**Belegt an iv_wand** (OKX-Spot 0,10 % je Seite = 0,20 % je Runde). Das Journal
vom 02.10.2026, 10 Runden:

| Zielabstand | Runden | brutto | Gebuehr | netto |
|---|---|---|---|---|
| 0,015 – 0,051 % | 6 | +0,649 % | 1,20 % | **−0,551 %** |
| >= 0,43 % | 4 | +5,160 % | 0,80 % | **+4,360 %** |

Die Trefferquote war 9 von 9 — und trotzdem war die Mehrheit der Runden
Verlust. Eine hohe Trefferquote ist bei kleinem Zielabstand **kein** Vorteil:
sie sagt nur, dass der Kurs die Linie oft beruehrt, nicht dass das etwas
verdient wurde. Das ist die Umkehrung der verbreiteten Lesart.

**Der Boden ist die Gebuehr, nicht die Vorsicht.** 0,30 % ist die Zahl aus dieser
Rechnung, nicht eine runde Huerde. Bei einer anderen Boerse oder einem anderen
Zieltyp wird er neu gerechnet, nicht uebernommen.

**Der Boden macht die Regel nicht schaerfer im Sinne „seltener"**, sondern im
Sinne „nicht gegen die Gebuehr handeln" — die Anzahl Runden sinkt, die
Erwartung steigt. Beides gehoert in die Antwort, sonst liest es sich wie eine
Verschlechterung.

**Gegenprobe im echten Lauf** (die staerkste, weil sie nicht am Test klebt):
`--vorschau` muss an einem Fall, den die alte Regel verkauft haette, **kein**
Signal nennen. Bei iv_wand: Kurs 86032, Wand 86000, Abstand 0,037 % — alt
`short` mit 0,037 % Zielabstand, neu kein Signal.

**Zielrichtung.** Ein Ziel, das aus Abstand zur Zone gesetzt wird, muss auf
der RICHTIGEN Seite liegen: long von unten → Ziel knapp UNTER der Zone, short
von oben → knapp UEBER. Ohne diese Unterscheidung liegt das Short-Ziel hinter
dem Einstieg und `spur_buch.einstieg` lehnt es als Rechenfehler ab — die Spur
handelt dann gar nichts, ohne dass jemand den Grund sieht.

## 1a. Eine Quelle, die BEIDSEITS des Kurses liegen kann, ist kein Zielpunkt

Die Regel oben gilt fuer Zonen mit fester Seite. Sie laeuft ins Leere, sobald
die Quelle selbst **auf beiden Seiten** des Kurses liegen kann — eine
Liquidationswand, ein Liquidity-Pool, ein Niveauband. Dann gibt es keine
Konstante "die richtige Seite", sondern eine **Bedingung**: das Ziel muss in
Handelsrichtung liegen, und wenn der Rohwert das nicht erfuellt, wird er durch
ein Distanzziel (R) ersetzt — nie durch einen anderen Markt.

**Das Symptom ist eine vertauschte Bilanz, keine schlechte Trefferquote.** Bei
einer Liquidationswand: Ziel-Ausstiege im Mittel leicht negativ, Stop-Ausstiege
positiv, Gesamtsumme negativ bei ueber 50 % Treffern. Wer nur die Quote liest,
haelt die Geometrie fuer in Ordnung; wer auf die Zeile `ziel` schaut, sieht das
Ziel auf der falschen Seite des Einstiegs.

**Regel.** Beim Bau eines Zielpunkts aus einem Rohwert zuerst fragen: *kann
dieser Rohwert unter UND ueber dem Kurs liegen?* Wenn ja, wird er gegen die
Handelsrichtung geprueft, nicht ungeprueft uebernommen:

```python
wandpreis, menge, seite = treffer          # seite = liquidierter Bestand
long_ = (seite == "short")                 # liquidierte Shorts = Kaufdruck
if long_:
    return wandpreis if wandpreis > spot else spot * (1 + r / 100.0)
return wandpreis if wandpreis < spot else spot * (1 - r / 100.0)
```

Der Test dazu kreuzt **jede Kombination** aus Rohwert ueber/unter dem Kurs und
long/short — siehe `references/test-friert-stand-ein.md`, „Gegenprobe beim
Umbau“. Der Wandpreis wird weiterhin genommen, wenn er passt; nur die Haelfte
der Faelde, in denen er nicht passt, bekommt statt eines unerreichbaren Ziels
ein erreichbares.

## 1b. Ein Buendelpreis ist ein Rasterpunkt, nicht der Rohpreis

Wenn die Quelle in Preisb Buendel einsortiert, ist der zurueckgegebene Preis
die **Bandmitte**, nicht der beobachtete Einzelwert: aus einer Liquidation bei
86000 wird bei einem Raster von 0,25 % und Spot 85000 ein Ziel von 86062,50.
Das ist Absicht — die Buendelung braucht ein Raster — und es heisst: ein Test,
der auf den Rohwert pruft, meldet einen Fehler, den es nicht gibt. Der Test holt
den Preis ueber dieselbe Funktion, die der Lauf benutzt, und vergleicht das
Ergebnis damit.

## 2. Ein Marktpunkt ist ein Streifen, keine Linie

Gemessen an iv_wand: Ziel 86000, tatsaechliche Verkaeufe bei 86777, 86043,
86024, 86025. Der Kurs reisst durch die Linie, weil an einem runden Strike ein
**Preisstreifen** steht (Marktabsicherungen, Limits), nicht ein Punkt.

**Regel.** Das Ziel um `ziel_vor_wand_pct` VOR die Zone legen, richtungsabhaengig
nach der Seite. Bei BTC-Strikes im 1000er-Raster sind das 1,16 % Kursabstand,
0,15 % liegt bequem IN diesem Streifen. Der Wert ist eine **zoneneigene**
Groesse — bei einer anderen Zone gilt ein anderer Wert, er gehoert darum in die
Wachen und nicht in den Code.

**Was man sich davon verspricht.** Nicht mehr Trefferquote (die war schon hoch),
sondern: der Rest der Position laeuft weiter und der Stop bleibt unberuehrt,
falls die Zone nicht haelt. Das ist eine Behauptung, keine Messung — sie steht
als Vermerk in der Wachen, bis das Journal etwas sagt.

## 3. Hebel: bei risikonormierter Groesse eine Kapitalersparnis ohne Nutzen

**Die Rechnung.** Groesse risikonormiert, Stop `s` Prozent vom Kurs:

```
Nominal  N = Risikobetrag / s        <-- unabhaengig vom Hebel
Margin   M = N / h
Verlust am Stop = N * s = Risikobetrag     (fix)
Gewinn  am Ziel = N * Zielabstand          (fix)
```

Gemessen an iv_wand (Risiko 5 USD, Stop 4 %, Zielabstand 1,3 %):

| Hebel | Nominal | Margin | Gewinn am Ziel |
|---|---|---|---|
| 1 | 125,00 | 125,00 | 1,62 |
| 3 | 125,00 | 41,67 | 1,62 |
| 10 | 125,00 | 12,50 | 1,62 |

Der Hebel veraendert **weder Gewinn noch Verlust** — er senkt nur die
Kapitalbindung auf 1/h. Das ist echt, aber es ist nur dann etwas wert, wenn es
eine ZWEITE Verwendung fuer das freie Kapital gibt.

**Daraus die Regel:** Hebel lohnt sich nur bei (a) mehreren Positionen, die
sonst nicht gleichzeitig offen waeren, oder (b) einem Einsatz, der am
Guthaben scheitert. Eine Spur mit `max_offene_positionen: 1` hat keinen
Nutzen — das freie Kapital kann nirgends hin. **Die Frage „geht das mit Hebel?"
ist bei einer Ein-Platz-Spur also mit der Rechnung zu beantworten, nicht mit
einem Arm.** Die Rechnung gehoert als Vermerk in die Wachen, damit die Frage
nicht wieder gestellt wird.

**Die Grenze nach oben ist die Liquidationsdistanz.** Der Stop muss vor der
Liquidation liegen:

```
Liquidationsabstand = 100 % / h    muss  >  stop_pct sein
```

Bei 4 % Stop ist das **bei Hebel 25 genau aufgezehrt**, ab 25 liegt der Stop
ausserhalb. Dann liquidiert die Boerse, das Buch protokolliert einen anderen
Ausstieg — und die Diskrepanz faellt erst auf, wenn die Buecher verglichen
werden. Jede Hebel-Arm bekommt deshalb diese Pruefung als Test.

Merksatz: **ein Hebel, der nur das freie Kapital schont, ist bei einer Spur mit
einem Platz eine kapitalfreie Rechnung — kein Handelsargument.**

## 4. Ein Test auf einen festen Wert ist ein Stand, keine Regel

Beim Einbau des Schiebetors wurde ein bestehender Test rot: er pruefte
`p["ziel"] == 72000.0`. Die Regel war richtig, der Test haengte an einem
konkreten Wert.

**Regel.** Ein Buchtest liest den Erwartungswert aus **derselben Wachen, die der
Lauf benutzt**, und rechnet die Erwartung unabhaengig nach. Damit ueberlebt er
jede Parameteraenderung und beweist trotzdem die Funktion. Ein Test, der eine
Zahl festhaelt, meldet Aenderung, nicht Fehler — siehe
`references/test-friert-stand-ein.md`.

**Vollstaendigkeit einer Testwache.** Ein Test, der eine Buchung provoziert,
braucht ALLE Wachenfelder, die der Einstieg liest. Ein fehlendes
`max_pro_trade_usd` laesst die Buchung gar nicht erst versuchen — der Test
faellt dann mit `KeyError` aus und nicht mit der Aussage, die er treffen sollte.

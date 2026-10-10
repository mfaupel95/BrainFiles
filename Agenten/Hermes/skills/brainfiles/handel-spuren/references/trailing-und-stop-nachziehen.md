# Trailing-Stop und Stop-Nachziehen — die Gewinnschwelle fehlt leicht

Gehoert zu `handel-spuren`. Betrifft jede Spur, deren Buch ueber das
gemeinsame Buchmodul laeuft und in deren Wachen `trailing_stop_prozent` steht:
der Boersen-Stop wird im Zyklus **nachgezogen**, nicht im Buch neu gerechnet.

## Die Regel

**Ein nachgezogener Stop darf nie unter den Einstieg plus Rundenkosten
wandern.** Ohne diese Schwelle verwandelt das Nachziehen den weiten
Notausstieg in einen garantierten Verlust.

## Der Mechanismus, an dem es scheitert

Die uebliche Fassung lautet:

```python
hoch = max(hoechstkurs, kurs)
neu  = hoch * (1.0 - pct)
if neu > p["stop"]:        # "nur nach oben"
    stop_nachziehen(...)
```

`nur nach oben` vergleicht gegen den **alten Stop**, nicht gegen den
**Einstieg**. Solange der Hoechstkurs unter dem Einstieg liegt, ist `neu`
trotzdem groesser als der weite Pflicht-Stop — und liegt zugleich unter dem
Einstieg. Beispiel ohne Schwelle: Einstieg 100, Hoechstkurs 99, Trailing 3 %
-> Stop 96,03. Der Pflicht-Stop stand bei 86,50; aus 13,5 % Erholungsluft
werden 3,97 % garantierter Verlust, und zwar **bevor** die Position je im
Gewinn war.

Richtig ist eine Schwelle vor dem Nachziehen:

```python
schwelle = p["einstieg"] * (1.0 + 2.0 * float(w.get("gebuehr_taker") or 0.0))
if pct > 0.0 and p.get("seite") == "long" and hoch > schwelle:
    ...
```

Darunter bleibt der Pflicht-Stop stehen. Die Kosten gehoeren in die Schwelle,
weil ein Ausstieg genau auf dem Einstieg nach zwei Gebuehrenseiten ein Verlust
ist.

## Trailing und Notausstieg gehoeren nebeneinander geprueft

Ein Trailing-Prozentsatz, der **enger** ist als der Pflicht-Stop, verwandelt
den weiten Notausstieg still in einen engen — die Spur handelt dann eine
andere Geometrie als die, mit der sie gemessen wurde. Vor dem Setzen beide
Zahlen aus der Wachen nebeneinander legen: `stop_prozent` und
`trailing_stop_prozent`. Bei Hebel zusaetzlich umrechnen: der Prozentsatz
wirkt auf den Nennwert, auf die Margin ist er mit dem Hebel multipliziert
(3 % bei Hebel 7 sind rund 21 % der Margin).

## Diagnose: Boersen-Stop weicht vom Buch-Stop ab

Drei Zahlen und ein Zeitstempel beantworten die Frage, ohne zu raten:

1. **Einstieg** aus der Journalzeile der Eroeffnung.
2. **Buch-Stop** aus der Position in der `zustand*.json`.
3. **Boersen-Stop** aus den offenen Auftraegen der Boerse
   (`stopPrice`, `reduceOnly`), nie aus dem Buch.
4. **Zeitpunkt der letzten Aenderung** des Auftrags. Liegt er deutlich nach
   der Eroeffnung, wurde der Stop **nachgezogen** — dann ist es keine
   Fehlbuchung, sondern eine laufende Regel.

Teilt man den Boersen-Stop durch den Hoechstkurs, kommt der Prozentsatz der
Regel heraus; damit ist die Fundstelle identifiziert, bevor man Code anfasst.

## Besitz klaeren, bevor eine Wachen-Zahl geaendert wird

`trailing_stop_prozent` steht je Spur, wirkt aber durch das **gemeinsame**
Buchmodul: jede Spur, die ihr Buch darueber fuehrt, erbt das Verhalten. Eine
abweichende Stop-Lage an der Boerse ist deshalb erst dann einer Spur
zugeordnet, wenn Instrument **und Menge** in genau einer Buchdatei stehen —
und die Risikostufen-Kopien (`zustand.mittel.json`, `zustand.hoch.json`)
gehoeren mit in die Suche. Eine Spur mit leerem Buch kann den Auftrag nicht
gesetzt haben, auch wenn ihre Wachen den passenden Prozentsatz tragen.

## Pitfalls

- **Scheitert das Nachziehen, muss der ALTE Stop stehen bleiben.** Nie
  stornieren und dann neu setzen: bricht es zwischen beiden Schritten ab,
  steht die Position ungeschuetzt an der Boerse. Ein Fehlschlag beim
  Nachziehen ist der harmlose Fall und wird nur gemeldet.
- **Ein Stop, der nur im Buch steht, ist kein Schutz.** Nach jedem Setzen und
  Nachziehen gegen die Boerse gegenpruefen; der Vergleich zaehlt die
  **Menge**, nicht die Existenz eines Treffers.
- **Der Hoechstkurs gehoert in die Position, nicht in den Zyklus.** Wird er
  bei jedem Lauf aus dem aktuellen Kurs neu gebildet, folgt der Stop dem Kurs
  auch nach unten, sobald eine Zwischenerholung den Speicher ueberschreibt.
- **Trailing nur fuer die Richtung bauen, die die Spur eroeffnet.** Eine
  spiegelbildliche Short-Fassung, die nie laeuft, ist toter Code; eine
  fehlende, waehrend die Spur short eroeffnet, ist ein ungeschuetzter Short.

## Nachweis

Ein Test, der die Schwelle prueft, muss **rot werden, wenn man sie
entfernt** — sonst prueft er nur das Nachziehen. Zwei Faelle genuegen:
Hoechstkurs unter dem Einstieg (es darf **kein** Nachziehen geschehen) und
Hoechstkurs deutlich darueber (der Stop wandert, und zwar ueber den Einstieg
plus Kosten). Dazu der Gegenbeweis am laufenden System: Buch-Stop,
Boersen-Stop und Einstieg nach einem echten Zyklus nebeneinander ausgeben.

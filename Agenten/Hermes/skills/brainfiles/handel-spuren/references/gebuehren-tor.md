# Das Gebuehren-Tor: eine Spur wird erst live, wenn die Zahl es traegt

Ausloeser: „Gebuehren-tor", „Auswertung und Freigabe", „ab wann darf eine Spur
live?", „welche Spur hat ueberhaupt Edge?", „die beste Spur freigeben".

## Was es ist — und was nicht

`freigabe.erfuellt` bleibt der von Hand gesetzte Haken von Max. Das Tor ist eine
**zusaetzliche** Sperre in derselben Kette, und es **rechnet**. Es setzt
nichts, es verweigert.

Der Unterschied ist der ganze Punkt. Ein Werkzeug, das Freigaben **vergibt**, ist
eine Behauptung: es behauptet, die Bedingung sei erfuellt, und niemand kann sie
pruefen. Ein Werkzeug, das **verweigert**, kann nur zu streng liegen — und das
sieht man sofort, in dem Moment, in dem eine Spur durchgeht, die man selbst
freigeben wollte.

## Die vier Bedingungen

1. **`n >= min_runden`** (Vorgabe 8). Unter acht Runden ist jede Zahl eine
   Behauptung. Der scanner hat 161 Runden und trotzdem keinen Edge — eine Spur
   mit 16 Runden hat noch gar keinerlei.
2. **`n_basis >= min_runden`.** Runden MIT Basislinie. Sonst steht da kein
   Edge, sondern ein Rundendurchschnitt, und der sieht aus wie eine Kennzahl.
3. **`mean_excess − gebuehr_der_eigenen_boerse > 0`.** Der Excess ist die
   Grundlinie schon abgezogen: Rundenergebnis minus „dasselbe Instrument
   einfach halten". Die Gebuehr kommt aus der `wachen.json`; `gebuehr_taker` ist
   der Anteil **JE SEITE**, eine Runde ist Kauf+Verkauf und kostet das
   Doppelte (`* 2 * 100` fuer Prozent). Der Faktor liegt zwischen Einheit und
   Zahl, und ohne ihn erklaert sich jede Spur selbst fuer tragfaehig.
4. **KEIN Befund im Audit.** Das ist die Bedingung, an der das Tor sonst
   wertlos waere.

## Bedingung 4 ist die wichtigste

Eine Spur mit einem **Befund** im Audit ist nicht gemessen, sondern
**beanstandet**.

Gemessen am 03.10.2026: der scanner haette die ersten drei Bedingungen mit
**+8,52 % Excess** klar bestanden — die groesste Zahl im Haus. Sein Audit traegt
vier Befunde, darunter „87 von 161 Runden auf EIN Instrument“ und
„Einstiegspreis je (Instrument, Tag) IDENTISCH — Preis uebernommen statt
geholt“. Ohne Bedingung 4 haette das Tor genau die Zahl abgesegnet, an der sich
das Haus am selben Tag die eigene Empfehlung zurückgenommen hat.

**Merksatz: eine schoene Zahl mit einem Befund daneben ist keine Freigabe,
sondern ein Befund.** Wer eine Zahl gegen ein Tor stellt, stellt auch die
Beanstandung dagegen.

## Was das Tor mit einer Spur macht, die es NICHT kennt

Nichts. Keine Auditrundlage heisst **unbewiesen**, nicht *abgelehnt*. Ein
Torschutz, der wegen seiner eigenen Unkenntnis schweigt, waere ein anderer
Fehler — und genauso still. Die Unbekannten werden gemeldet, nicht gesperrt.

## Die Zahlen kommen aus EINEM Lauf

`spur_audit.py --json` (liest nur) liefert je Spur `n`, `basislinie_n`,
`n_excess`, `mean_excess`, `befunde`. Das Tor merkt sie in
`Agenten/Handel/cache/freigabe-tor.json` **mit Zeitstempel** und rechnet nicht
je Spur neu: sonst hinge es an einem Abruf, der beim Nachladen der Kerzen anders
ausfaellt als der Lauf von heute frueh, und die Bedingung waere von einem
Zeitpunkt ab, nicht von den Runden abhaengig.

Ein Tor ohne frischen Lauf ist nicht frisch. `ALTER_MAX_S` (6 h) passt zum
Audit-Takt; darueber hinaus ist der Stand veraltet und das Tor verweigert.

## Fail-closed, und zwar an JEDER Stelle

Das Tor kommt in den Weg, der ausserhalb des Dauerlaufs ordert (der
`signal-executor`), und **vor** der Order. Ein `ImportError` oder ein
Lesefehler bedeutet: **keine Order**. Ein Torschutz, der bei seinem eigenen
Ausfall durchlaesst, ist kein Torschutz — das ist dieselbe Regel wie beim
Freigabefenster, und beide gehoeren an denselben Weg.

## Der Test prueft die Regel, und eine Bedingung braucht ihre Gegenprobe

Je Bedingung ein Test mit **Kopien der Wachen** (die echte Spur bleibt
unberuehrt): `trigger_modus` entfernt -> ZU; `gebuehr_taker` auf einen Wert, der
den Excess uebersteigt -> ZU; dieselbe Spur ohne Befund-Bedingung gerechnet ->
`netto > 0`, damit die Bedingung als wirksam belegt ist.

**Merksatz: eine Bedingung, deren Weglassen nichts aendert, ist keine
Bedingung.** Die Gegenprobe rechnet die Spur OHNE die Bedingung und zeigt, dass
sie durchgewaere.

## Was das Tor NICHT leistet

- Es vergibt nichts und setzt keinen Haken.
- Es beweist keine Zukunft. Eine Spur mit +1,15 % auf 16 Runden hat einen
  positiven *gemessenen* Excess und eine **duenne** Stichprobe — das Tor sagt
  beides, und es sagt nicht „sicher“.
- Es ersetzt nicht das Freigabefenster und nicht `handel_erlaubt`.

## Ein Soll, das man zuruecknimmt

Sagt Max „freigabe erlaubt“ und ist die Spur nachweislich unprofitabel, dann ist
das seine Entscheidung — und sie wird ausgefuehrt. Aber eine Aenderung, die auf
einer zurueckgenommenen Zahl beruhte, gehoert **zurueckgenommen und benannt**,
nicht stillschweigend stehen gelassen: Vermerk mit Datum in der `wachen.json`,
der Grund ist die Messung, nicht eine neue Bewertung. Eine Kostensenkung oder
Budget-Erhoehung ohne Ruecknahme-Bedingung zaehlt spaeter Runden, fuer die die
Freigabe gar nicht mehr gilt.

## Aufruf

```
scanner/.venv/Scripts/python.exe freigabe_tor.py --messen        # Audit einmal fahren
scanner/.venv/Scripts/python.exe freigabe_tor.py                 # Tabelle aller Spuren
scanner/.venv/Scripts/python.exe freigabe_tor.py --pruefe <spur> # mit Grund
```

`--pruefe` gibt die Sperrgruende woertlich aus — sie gehoeren in die
Vorschauzeile der Spur, sonst findet der Dauerlauf nichts, wonach er fragen
kann.
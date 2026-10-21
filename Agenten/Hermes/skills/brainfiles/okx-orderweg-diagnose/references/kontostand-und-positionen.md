# Kontostand und Positionen lesen — Feldformen statt Feldnamen

Fuer die Frage „was steht gerade offen“ (nicht „was hat der Bot bestellt“).
Rein lesend, dieselbe Schiene wie die Beleg-Rezepte in
`okx-fehler-und-nachweis.md`.

Fertiges Werkzeug: `Agenten/Handel/okx_positionen_live.py` aus dem Handel-Ordner

```bash
MAXHIRN_ROUTINE=1 scanner/.venv/Scripts/python.exe okx_positionen_live.py
MAXHIRN_ROUTINE=1 scanner/.venv/Scripts/python.exe okx_positionen_live.py --json
```

## Kontostand: die Summenzeile traegt nicht die Einzelwerte

`GET /api/v5/account/balance` fuehrt auf Kontoebene **nur** `totalEq`. Die zwei
Zahlen, die eine Frage beantworten, sind dort leer bzw. `null`:

```
totalEq   "1703.48"   <- Kontoebene, gefuellt
availEq   ""          <- Kontoebene, LEER
stgyEq    null        <- Kontoebene, NULL
```

Beide stehen je Waehrung in `details[]`:

```python
for d in konto["details"]:
    eq        = float(d["eq"] or 0)        # gesamt
    availEq   = float(d["availEq"] or 0)   # frei
    stgyEq    = float(d["stgyEq"] or 0)    # in Staking gebunden
    frozenBal = float(d["frozenBal"] or 0) # an Margin/Orders gebunden
```

Ein Parser auf der Kontoebene meldete **0.00 fuer ein Konto mit 949 USDC** —
und „0.00“ sieht wie „leeres Konto“ aus, nicht wie ein Fehler. Das ist bei einer
Boerse die gefaehrlichste Fehlform: sie beschreibt „nichts“ statt „falsch
gelesen“. **Bei einer Antwort mit Listen- und Objektebene braucht man die
LISTE, sobald man Einzelwerte will.** Das Summenfeld ist ein Kontrollwert.

`frozenBal` heisst bei OKX NICHT „eingefroren“, sondern die an Margin, offene
Orders und Algo-Orders gebundene Summe. Die Rechnung geht auf:

```
eq = availEq + stgyEq + gebunden
```

**`okx.guthaben(ccy)` liefert einen FLOAT (`availBal`), kein Dict.** Es
beantwortet „wie viel ist frei“. Wer darauf einen Adapter fuer `eq`,
`stgyEq` oder `details` setzt, baut still ein falsches Objekt. **Die
Rueckgabeart einer Fremdbibliothek messen (`type()` + Auszug der Rohantwort),
bevor ein Adapter darauf aufsetzt.**

## Positionen: `instType` nimmt kein SPOT

`GET /api/v5/account/positions` akzeptiert **nur** `FUTURES`, `SWAP`,
`MARGIN`. `SPOT` gibt `OKX 51000: Parameter instType error` — Spot-Bestaende
sind KEINE Positionen, sie stehen in `/account/balance`. Ein Aufruf mit SPOT
wird gar nicht gestellt, statt den Fachfehler als Befund zu melden: **eine
Antwort, die man selbst provoziert hat, gehoert nicht in den Befund.**

Je Position (alles als STRING; `uplRatio`/`mgnRatio` als DECIMAL):

| Feld | Bedeutung |
|---|---|
| `pos` | Richtung und Menge, **signed** (short = negativ) |
| `avgPx` / `markPx` / `liqPx` | Einstieg / Marktkurs / Liquidationsmarke |
| `lever`, `mgnMode` | Hebel, `isolated` oder `cross` |
| `upl`, `uplRatio` | unbezahlter Gewinn absolut und in Prozent |
| `margin`, `notionalUsd` | gebundene Margin, Nennwert |
| `mgnRatio` | **Marginanteil am Positionskapital** — NICHT die Luft |

## Zwei Rechnungen, die man nicht verwechselt

**Luft bis zur Liquidation** muss auf BEIDEN Seiten positiv sein — Long hat
`liqPx` unter `markPx`, Short darueber:

```python
luft = (liqPx / markPx - 1.0) * -richtung * 100.0   # richtung = +1 long / -1 short
```

**`mgnRatio` ist keine zweite Luft.** Als Gegenrechnung etikettiert liefert es
82–93 % neben echten 8–17 % — das sieht wie ein Datenfehler aus und ist eine
falsche Beschriftung. Wenn zwei Spalten derselben Zeile systematisch um eine
feste Groesse abweichen, ist die Beschriftung der Verdächtige, nicht der Wert.

## Schutz decken?

`/api/v5/trade/orders-algo-pending` je `ordType` lesen — `conditional`, `oco`,
`trigger`, `move_order_stop` — nicht nur `attachAlgoOrds`. Je Stop zaehlt
`sz`, nicht die Existenz: ein Stop auf 22 Stueck bei einer Position von 34
deckt zwei Drittel. Als Schutz zaehlt nur `reduceOnly` auf der **gegenlaufenden**
Seite.

## Zwei Messungen statt einer

Positionen aendern sich waehrend des eigenen Laufs. **Zweimal lesen, wenn der
Bericht eine Zahl traegt** — aendert sich Menge, Liquidationsmarke oder
Notional zwischen den Laeufen, ist das ein eigener Befund (Bot, Nachkauf,
fremde Sitzung) und gehoert in die Antwort, nicht still in die Tabelle.

## Eine bereits gedeckte Position ist keine Aufgabe

Der Auftrag „setz Take-Profit in Stufen“ heisst **nicht** „setz zusaetzlich
Stufen“. Geprueft lag ein vollstaendiger OCO (Stop *und* Ziel auf der vollen
Menge); drei zusaetzliche Stufen haetten beim ersten Treffer **doppelt
verkauft**, weil ihre Mengen sich mit der Zielmenge des OCO ueberschneiden.

Ist die Position vollstaendig gedeckt, ist die Handlung **„nichts“** — und die
Antwort benennt die Luecke in einer *anderen* Position, statt eine zweite
Schutzebene zu bauen.

**Vor jeder Handlung neu lesen.** Zwischen Analyse und Order aendert sich das
Konto: Mengen wachsen, Stops werden nachgesetzt, OCO-Auftraege wechseln. Wer auf
einer Tabelle von vor einer Minute handelt, setzt auf eine bereits gesicherte
Position. Messung und Order gehoeren in **einen** Lauf, nicht in zwei
Werkzeugaufrufe.

## Gestufter Take-Profit: Menge zuerst, Preis danach

Die Summe der Teilmengen muss **exakt** die Position ergeben. Ein Restbetrag ist
entweder eine Order, die die Boerse ablehnt, oder eine Teilmenge, die
ungeschuetzt bleibt, weil der Stop auf den vollen Bestand zeigt.

- **Rest auf die FRUEHEN Stufen**, nicht auf die letzte: ein Rest auf der letzten
  Stufe bleibt bis zum letzten Treffer ohne Schutz.
- **Stop ZUERST**, dann die Stufen. Eine TP-Stufe ohne Stop ist eine Position,
  die beim naechsten Neustart des Algo-Bestands nackt dasteht.
- **Eigener Orderweg statt eines allgemeinen Helfers.** Ein fuer Spot
  geschriebener Helfer ist fest auf `tdMode: cash` und `side: sell`
  verdrahtet und lehnt auf einem Perpetual ab. `tdMode` folgt der Position
  (`cross`/`isolated`), die Seite folgt der Seite der Position.
- **Marktausloesung, nicht Limitpreis** (`slOrdPx: -1` / `tpOrdPx: -1`): ein
  Limitpreis verpasst genau den Momentum-Move, der ihn ausgeloest hat.
- **Gleichverteilte Stufen** zwischen Einstand und Ziel, jede `1/n`. Eine
  risikogewichtete Staffelung (fruehere Stufen naeher am Einstag) loest bei einem
  0,03-USD-Instrument nichts — die Gebuehr je Seite frisst den ersten Abstand.
- **Im Bericht die fuenf Zahlen**: Triggerpreis, Abstand in Prozent, Menge,
  Erloes je Stufe, Summe. Wer eine Order freigibt, will den Rechenweg sehen.

## Die Schutzhoehe zaehlt, nicht die Deckung

Eine Luecke von 3.805 von 11.388 Stuecken (67 % geschuetzt) sah nach der einen
Aufgabe aus. Gemessen an der **Schutzhoehe** war sie eine Falle:

| | |
|---|---|
| Stop 0,053 gegen **Einstand** 0,054448 | −2,66 % |
| Stop 0,053 gegen **Kurs** 0,05915 | **−10,40 %** |
| Ziel 0,06 gegen **Kurs** 0,05915 | **+1,44 %** |

Der Markt war 8,6 % ueber den Einstand gestiegen, der Stop nicht mitgezogen. Er
schuetzte den Rücksetzer, nicht mehr den Einstieg — und das Ziel war nur noch
1,4 % entfernt. Die Luecke mit den Altpreisen zu fuellen haette die Position
**formal** gedeckt und sie beim naechsten Ausbruch restlos verkauft.

**Regel: eine Schutzhoehe wird gegen den aktuellen Kurs gemessen, nicht gegen
den Einstand.** Vor jeder Nachsicherung am bestehenden Order drei Zahlen
drucken: Hoehe gegen Einstand, Hoehe gegen Kurs, Ziel gegen Kurs. Ist das Ziel
naeher als der Abstand zum Stop, ist das nicht eine Aufgabe, sondern zwei —
und die Reihenfolge ist: Stop hoeher ziehen, dann Luecke fuellen.

**Die Preise des bestehenden Orders uebernehmen, nicht neu rechnen.** Sie sind
der Beleg, dass die Position so gestellt wurde; ein neu gerechneter Preis waere
eine zweite Wahrheit neben der ersten.

**Die Luecke mit EINEM OCO fuellen, nicht mit einem Stop plus getrennten
Ziel-Orders.** Zwei bedingte Orders koennen sich in der Menge ueberschneiden,
wenn zuerst das Ziel feuert. `POST /api/v5/trade/order-algo` mit
`ordType: oco` und **beiden** Preisen in einem Koerper garantiert, dass je
Stueck hoechstens einmal ausgeloest wird.

## Zwei Helferfallen, die beide still ausfallen

**Eine Hilfsfunktion darf eine Aufrufform haben, nicht zwei.** Nach einem
Signaturumbau (`zahl(wert)` → `zahl(container, feldname)`) trugen 17 Aufrufe
noch die alte Form: der *Wert* landete als *Feldname* in einer Suche, das
Ergebnis war `0.0` statt der echten Zahl. Das Gelbe: ein `TypeError` faellt auf,
dieser Weg nicht. Verwandte Form: eine Funktion, die einen formatierten String
zurueckgibt (`"%.10g"`), liefert im naechsten Aufruf ein `str` — die
Formatierung gehoert in die Ausgabe, nicht in die Rechnung.

**Eine Bedingung, die nichts bewirkt, liest sich wie eine Entscheidung.** Ein
`if a and b: pass / elif b:` im Block, der eigentlich verzweigen sollte, fuehrt
zu einem `None`, das zwei Aufrufe spaeter als `TypeError: 'NoneType' object is
not iterable` auffaellt — die Ursache liegt aber im toten Zweig. Jeder Block,
der eine Tabelle nur unter einer Bedingung zeigt, braucht **eine** `if` mit
beiden Zweigen; ein `pass`-Zweig ist eine Behauptung ohne Wirkung.

**Ein Kontrollwert, der zwei Nullen vergleicht, ist keine Kontrolle.** Summiere
die `details[]` und vergleiche sie mit `totalEq`. Bei 0 gegen 0 ist das gruen,
ohne dass irgendetwas geprueft wurde — die Pruefung **bestaetigt** den Fehler,
statt ihn zu finden. Eine Kontrolle muss an einem **nicht-trivialen** Wert
haengen.

**Ein Block-Ersetzungsskript kann die alte Definition stehen lassen.** In
Python gewinnt die *spaetere*. Der Bericht zeigte exakt den toten Code, dessen
Lesefehler verschluckt als „keine Positionen“ erschienen — ein Befund ueber
nichts, erzeugt von einem Programm. Nach jedem Austausch
`count("def <name>(") == 1` pruefen und `compile()` **vor** dem Schreiben
laufen lassen.

## Die Abrechnungswaehrung steht im KONTO, nicht im Instrument

Drei Stellen fuehren eine Waehrung, und nur eine davon gilt fuer Geldbetraege:

| Quelle | Beispiel | gilt fuer |
|---|---|---|
| Symbol | `SOL-USD_UM_XPERP-310404` → `USD` | Namensgebung |
| Instrument `/public/instruments` → `settleCcy` | `USD` | NICHT die Equity-Waehrung |
| Konto `/account/config` → `settleCcy` | `USDC` | Kontostand, Margin, Equity |

Wer die Equity (oder das Guthaben-Tor) aus der Symbol-Quote rechnet, sucht im
Kontostand eine Waehrung, die es dort nicht gibt: der Bestand ist 0, die Equity
faellt auf den unrealisierten PnL zusammen, und ein Drawdown-Limit
`(peak - equity) / peak` schiesst in Millionenprozent, sobald der PnL einmal
positiv und danach negativ war. Folge: **jeder** Auftrag wird vom eigenen Guard
abgelehnt, waehrend der Status gesund aussieht (`state: running`,
`orders_placed` > 0).

Diagnose in drei Zeilen:

1. Die Ablehnung nennt den GUARD, nicht die Boerse → die Zahl stammt aus eigenem Code.
2. Die Prozentzahl aendert sich mit dem PnL, aber nicht mit dem Kontostand → falsche Bezugsgroesse.
3. `/account/config` lesen: `settleCcy` ist die Waehrung, in der abgerechnet wird.

**Regel: jede Equity-/Margin-Rechnung nimmt die Kontowaehrung.** Reihenfolge:
Quote des Symbols → Kontowaehrung → Instrument-Waehrung, und die erste Waehrung
MIT BESTAND gewinnt; sonst bleibt es bei der Quote (fail open zur alten Regel,
nie fail closed auf eine Null).

**Testfalle dazu:** ein Drawdown-Guard steigt bei `peak <= 0` frueh aus. Ein Test,
der nur prueft "Auftrag wird nicht abgelehnt", ist deshalb auch mit falscher
Waehrung gruen (Equity 0 → Guard steigt aus, bevor er rechnet). Der Fall braucht
einen POSITIVEN Peak VOR dem Verlust (erst +0,05 uPnL, dann -0,50) — erst dann
wird der Test rot, wenn die Waehrung fehlt.

## `liqPx: "0"` ist ein Preis, kein fehlender Wert

OKX meldet bei einer Position ohne Liquidationsmarke (1x isolated) `liqPx: "0"`
— "es kann keine Liquidation geben", nicht "unbekannt". Ein Parser, der jeden
Wert `<= 0` in `None` uebersetzt, macht daraus "nicht lesbar", und eine
fail-closed-Regel (`Liquidationspreis oder Markpreis fehlt bei offener Position`)
verweigert dann **jedes Nachlegen** — die zweite Stufe eines Plans ist
unerreichbar, obwohl der Markpreis vorliegt.

**Regel: bei Preisfeldern LEER (`""`, unbekannt, fail closed) von `0` (Aussage
der Boerse) unterscheiden.** Die Distanz zu 0 ist 100 %, die Sperre greift also
nicht — das ist die richtige Aussage fuer eine Position, die nicht liquidiert
werden kann. Gegenprobe: eine echte Liquidationsmarke 2 % unter dem Mark muss
weiter gesperrt bleiben.

## Merksatz

> Ein Befund ueber null ist nie ein Befund ueber "nichts".
> „an der falschen Stelle gelesen“ — und das sieht aus wie eine Tatsache ueber
> die Welt, nicht wie ein Fehler im Programm.
>
> Und die Gegenhistorie gilt genauso: ein Auftrag, eine Position zu sichern,
> ist manchmal die richtige Antwort **„sie ist bereits gesichert, hier ist die
> Luecke woanders“**. Ein Werkzeug, das ansetzt, weil ein Auftrag das sagte,
> baut die zweite Schutzebene — und die verkauft doppelt.
# OKX-Futures: offene Position lesen und absichern

Gegenstueck zu `references/boersen-aufrufe.md` (Kraken-Spot/Margin). Hier geht
es um `*_UM_XPERP`-Perpetuals: Hebel, isolierte und cross-Marge, Liquidations-
preis, bedingte OCO-Orders. Der SKILL-Abschnitt zum nachtraeglichen Absichern
ist Kraken-geformt; das hier sind die Felder und Rechenwege fuer OKX.

Werkzeuge: `Agenten/Handel/okx_positionen_live.py` (rein lesend: Kontostand je
Waehrung + offene Positionen mit Einstieg, Marke, Liquidation, UPL und den
Stops mit ihrer Menge) und `Agenten/Handel/okx_tp_stufen.py` (Stop +
gestufter Take-Profit fuer EINE Position, Trockenlauf als Vorgabe,
`--anwenden` schreibt).

## Lesen: welche Abfrage welche Frage beantwortet

- **Positionen:** `/api/v5/account/positions?instType=FUTURES`, signiert.
  Gueltige `instType` sind **FUTURES, SWAP, MARGIN — SPOT steht nicht dabei**
  und wird mit `51000 Parameter instType error` abgewiesen. SPOT-Bestaende
  kommen aus `/api/v5/account/balance`, und sie sind keine Positionen im Sinne
  dieses Werkzeugs: sie haben keine Liquidationsmarke und keinen Hebel.
- **Offene bedingte Orders:** `/api/v5/trade/orders-algo-pending` mit
  `ordType=conditional` UND mit `ordType=oco` — beide lesen und zusammenfuehren.
  Je Position liefern beide Abfragen, was wirklich haengt; nur eine davon zu
  lesen heisst, die Haelfte des Schutzes nicht zu sehen.
- **Kontostand:** `/api/v5/account/balance`, signiert.

### Die Falle: die Kontostand-Zahlen stehen auf zwei Ebenen

`totalEq` steht auf Kontoebene. `availEq` ist dort ein **leerer String** und
`stgyEq` ist **`null`**. Beide Zahlen stehen je Waehrung in `details` als
`eq` / `availEq` / `cashBal` / `stgyEq` / `frozenBal`. Ein Parser, der die
Kontoebene liest, meldet **0.00 fuer ein Konto mit ueber 900 USDC** — das
sieht wie ein leeres Konto aus und nicht wie ein Fehler, und eine Kontrollzeile
`abs(summe - totalEq) < 0.01` **bestaetigt** diesen Fehler, weil sie zwei
Nullen vergleicht.

Drei Grössen beantworten drei verschiedene Fragen und gehoeren getrennt
genannt: `availEq` = frei (was eine neue Order kaufen kann), `stgyEq` = in
Staking gebunden (frei nach Max' Freigabe, aber nicht automatisch),
`frozenBal` = an Margin, offene Orders und Algo-Orders gebunden. `frozenBal`
heisst bei OKX nicht "eingefroren".

Die Kontrollzahl braucht einen Wert, der **nicht** Null sein kann — sonst
gruent sie bei Nullen immer. Beste Gegenprobe: Summe der `details`-Zeilen gegen
`totalEq`, und wenn das um eine runde Summe danebenliegt, ist die Liste
gekuerzt (das ist dann der Befund, nicht die kleinere Zahl).

## Die Felder einer Position

`pos` (signed, long > 0), `avgPx` (Einstand), `markPx`, `liqPx` (Liquidations-
marke), `upl` / `uplRatio` (Dezimal, x100 fuer Prozent), `margin`, `imr`,
`mgnRatio` (Dezimal), `lever`, `mgnMode` (`isolated`/`cross` = `tdMode`),
`notionalUsd`.

**`mgnRatio` ist KEINE zweite Liquidationsdistanz.** Es ist der Marginanteil am
Positionskapital (bei Hebel 10 rund 10 %). Als zweite Luft etikettiert ergab
das 82-93 % neben den echten 8-17 % und liess jede Position um 70-80 Punkte
"abweichen" — das sieht wie ein Datenfehler aus und ist eine falsche
Beschriftung zweier verschiedener Fragen.

### Die Liquidationsdistanz richtig rechnen

`(liqPx / markPx - 1) * -richtung * 100`, mit `richtung = +1` long, `-1`
short. Das `-richtung` ist der Punkt: long hat `liq` unter `mark`, short dar-
ueber, und die **LUFT** ist auf beiden Seiten positiv. `(liq/mark - 1) *
richtung` liefert bei long negative Prozent, was als "keine Luft" liest.
**Kein `abs()`** — ein negativer Wert bedeutet, dass der Kurs die Liquidations-
marke ueberschritten hat, und genau das ist der Befund.

## Absichern: OCO ist EIN Order, nicht zwei

`POST /api/v5/trade/order-algo` mit `ordType: "oco"` und BEIDEN Preisen in
einem Koerper:

```
{"instId": …, "tdMode": "isolated", "side": "sell", "ordType": "oco",
 "sz": "3805", "slTriggerPx": "0.053", "slOrdPx": "-1",
 "tpTriggerPx": "0.06",  "tpOrdPx": "-1"}
```

- `tdMode` aus `mgnMode` der Position (`cross` -> `cross`, sonst `isolated`).
- `side` GEGEN die Position: long -> `sell`, short -> `buy`.
- `slOrdPx: -1` / `tpOrdPx: -1` = Marktausloesung. Bei einem TP **bewusst kein
  Limitkurs**: bei einem Momentum-Ausbruch verpasst der Limitpreis genau den
  Move, der ihn ausgeloest hat.
- Warum OCO statt zwei bedingter Orders: bei zwei getrennten Orders kann das
  Ziel feuern, teilweise schliessen und der Stop auf die ALT-Menge weiterlaufen.

**`okx.stop_setzen` ist fuer diesen Zweck nicht verwendbar** — es ist fest auf
`tdMode: "cash"` und `side: "sell"` verdrahtet (Scanner-Spot-Benutzung). Ein
`tdMode: cash` auf einem Perpetual wird abgewiesen, und ein stillschweigend
falsch gesetzter Schutz ist schlimmer als keiner. Fuer XPERP den Koerper selbst
bauen.

## Die Luecke: Summe der Stueckzahlen, nicht der groesste Einzelwert

"Geschuetzt" ist die **Summe** aller Stop-Mengen auf der richtigen Seite. Damit
werden drei Fehler sichtbar, die ein Einzelwert verdeckt:

- **Luecke** — Position groesser als die Summe (Nachkauf ohne Stopnachzug):
  die Nachkaufmenge ist ungeschuetzt. Das ist der haeufigste Befund.
- **Ueberdeckung** — Summe groesser als die Position (zwei Stops ueber
  geteilte Mengen, deren Grundlage aelter ist). Schuetzt formal, aber beim
  naechsten Nachkauf trifft ein Stop eine fremde Position.
- **Nullmenge** — ein Order mit `sz: 0` schuetzt nichts, existiert aber und
  ist nicht im Bild, wenn man nur "hat ein Stop" fragt. Als Waise melden.

## VOR dem Ausfuehren: ist der Preis ueberhaupt noch der richtige?

Das ist die Regel, die beim Aufstocken am meisten ausmacht.

Ein bestehender OCO traegt **Preise, die zum Zeitpunkt seiner Setzung
gerechnet waren**. Ist der Markt seitdem gelaufen, liegen Stop und Ziel nicht
mehr dort, wo sie relativ zum Einstand wirken. Deshalb **vor** dem Aufstocken
jeden Preis des vorhandenen Orders gegen den **aktuellen Kurs** rechnen, nicht
gegen den Einstand:

| Preis | vom Einstand | vom aktuellen Kurs |
|---|---|---|
| Stop 0.053 bei Einstand 0.0544, Kurs 0.0591 | −2,66 % | **−10,4 %** |
| Ziel 0.06 bei Einstand 0.0544, Kurs 0.0591 | +10,20 % | **+1,4 %** |

Am Beispiel: die Position war nach einem Nachkauf um 8,6 % ueber den Einstand
gestiegen, der Stop war nicht mitgezogen. Er schuetzte damit den **Ruecksetzer**,
nicht mehr den Einstieg — und das Ziel war nur noch 1,4 % entfernt, der
Take-Profit also faktisch schon erreicht. Die Luecke zu schliessen haette die
Menge formal dicht gemacht und den naechsten Kursmove zum Gesamtausgang
gemacht: die volle Menge zum alten Stop statt zum Ziel.

Also vor dem Aufstocken melden: Abstand jedes vorhandenen Preises zum
**Kurs** (nicht nur zum Einstand), und wenn Stop oder Ziel nicht mehr das
leisten, was ihr Name sagt, ist das eine **Entscheidung des Nutzers** — Stop
nachziehen, Ziel anpassen oder bewusst schliessen. Der Auftrag "Luecke
schliessen" deckt das nicht ab.

Faustregel fuer den Aufstock-Preis: den Preis des **bestehenden Orders**
uebernehmen ist der Beleg, dass die Position vom Haus gesetzt wurde. Ein neu
gerechneter Preis waere eine zweite Wahrheit neben der ersten.

## Reihenfolge

1. Stop **vor** den TP-Stufen. Eine TP-Stufe ohne Stop ist eine Position, die
   beim naechsten Neustart des Algo-Bestands nackt dasteht.
2. Trockenlauf, dann `--anwenden`, dann **nachlesen** (`bestaetigte(inst)` neu
   ziehen) — die Antwort auf den POST ist nicht der Beleg, das ist der
   Bestand danach.
3. Beim Aufstocken **eine** OCO-Order ueber die Luecke, nicht Stop und Ziel
   getrennt.
4. Einen Nullposten und jeden Posten, dessen Menge nicht zur Position passt,
   im Bericht benennen — er wird nicht automatisch mitgeraeumt.

## Fallen beim Rechnen

- **Mengen muessen Ganzzahlen sein und exakt aufsummieren.** Ein Rest von
  0,0001 Stuecken ist eine Order, die die Boerse ablehnt; ein Rest, den man
  auf die letzte Stufe legt, bleibt bis zum letzten Take-Profit ungeschuetzt.
  Den Rest auf die fruehen Stufen verteilen und mit `assert sum == menge`
  gegenpruefen.
- **Eine Hilfsfunktion darf EINE Aufrufform haben.** Ein `zahl(zeile,
  feldname)` und ein `zahl(wert)` nebeneinander wurden beim Umbau verwechselt und
  lieferten still 0.0 fuer jede Zahl des Kontostands. Formatiert wird in der
  Ausgabe, nicht in der Rechnung — sonst kommt der Trigger als `str` zurueck
  und bricht die naechste Rechnung mit `TypeError: must be real number`.
- **`str`-Preise aus der API sind Leer-/Null-Faelle, keine Nullen.** `""`,
  `None`, `"-"` werden zu "unbekannt"; wer sie als 0.00 liest, rechnet weiter
  und nennt das Ergebnis gemessen.
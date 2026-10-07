## Bestehende Positionen nachtraeglich absichern (Spot wie Margin)

Auftrag "Kraken positionen mit stop loss 7,5% ausstatten" / "Sui Zec und near
ebenfalls absichern". Geht es um Positionen, die SCHON offen sind, ist das ein
Handgriff am Konto - nicht der Stop, den die Spur beim Einstieg selbst setzt.
Die exakten Aufrufe und Felder stehen in `references/boersen-aufrufe.md`;
**OKX-Futures (XPERP, Hebel, isoliert/cross, OCO) in
`references/okx-futures-positionen.md`** - dort auch die Fallgriffe, an denen
ein Bestandsbericht ein leeres Konto meldet (die Kontostand-Zahlen stehen je
Waehrung in `details`, nicht auf Kontoebene) und wie man die Liquidationsluft
richtig rechnet.

1. **Ort klaeren, nicht raten.** Drei Stellen: Spot (`BalanceEx`),
   MARGIN-Positionen (`OpenPositions`), Futures-Brieftasche. Wer nur das
   Guthaben liest, schliesst falsch "hat er nicht" - SUI/ZEC/NEAR lagen als
   6x `SUIEUR`, 1x `NEAREUR`, 1x `XZECZUSD` in `OpenPositions`.
2. **Einstieg je Position:** Margin `cost / vol`, Spot aus dem Buch. Ohne
   Einstieg keinen Stop setzen.
3. **Stop = Einstieg minus Prozent** - und NIE ueber dem Markt. Ein Stop ueber
   dem Kurs ist ein sofortiger Verkauf, keine Absicherung: ueberspringen, melden.
4. **Menge = min(Position, verfuegbar)**, abgerundet auf `lot_decimals`. Das
   Buch fuehrt BRUTTO, die Brieftasche NETTO (Gebuehr ging vom Zufluss ab).
   Bei Margin genau die Menge der Position - mehr dreht den Rest short.
5. **Preis runden** auf `pair_decimals` (`preis_gerundet(paar, preis, "auf")`);
   ein roher Rechenwert wird abgelehnt.
6. **Margin-Stop MUSS verknuepft sein:** `close[ordertxid]` der Position. Ohne
   die Verknuepfung bleibt nach einem Handverkauf ein nackter Verkaufsstop
   stehen, der einen SHORT aufmacht.
7. **Reihenfolge:** Kraken reserviert die Menge eines Stop-Loss, ein zweiter
   Stop auf dieselbe Menge scheitert mit `EOrder:Insufficient funds` - also
   stornieren -> setzen, und bei Setzfehler den ALTEN Stop sofort zurueck.
8. **Am Konto nachsehen**, nicht im Buch: `OpenOrders` je Position ein
   `stop-loss`, `QueryOrders` mit `descr.close` = "close position @ stop loss"
   und dem Flag `c` in `oflags`. Frisch gesetzte Stops erscheinen verzoegert.
9. **Buch folgt der Boerse** (`zustand.json`: stop/stop_txid/menge), dann
   spiegeln und `spiegelstand.py` byte-gleich.
10. **Loecher melden:** uebersprungene Positionen (Staub, Stop nicht unter dem
    Markt) und Bestaende ohne Stop gehoeren in die Antwort - sonst sieht
    "8 Stops gesetzt" nach "alles geschuetzt" aus.
11. **Der Auftrag kann buchstabengetreu falsch sein - und das ist der
    Auftrag.** „MON zuerst absichern" traegt, wenn MON zwischen Auftrag und
    Ausfuehrung schon einen OCO bekommen hat; „Luecke schliessen" traegt nicht,
    wenn der Stop am Einstands-Niveau haengt und der Markt 9 % darueber steht.
    **Deshalb vor dem Setzen den Ist-Zustand frisch lesen** und beide Wege
    benennen: der beauftragte und der, der die Absicht wirklich trifft, mit den
    Zahlen, die dafuer sprechen. Dann ist die Entscheidung beim Menschen -
    ein Werkzeug darf sie nicht selbst treffen, und ein Live-Handgriff wird
    nicht "vorsorglich" ausgefuehrt, weil er plausibel klingt. Der Auftrag
    deckt auch nicht, was daneben liegt: fehlende TP-Deckung, Waisenposten
    mit Nullmenge, Stop auf halber Position gehoeren in den Bericht, nicht in
    die stille Erledigung.

Werkzeuge: `kraken/margin_stops.py` (Margin; Vorschau Standard, `--anwenden`),
`kraken/spot_stops.py` (ALLE SPOT-Bestaende ab einem Mindestwert, Bezug ist der
AKTUELLE Kurs statt eines Einstiegs - fuer Bestaende, die von Hand gekauft
wurden; `--ab-eur 50 --prozent 7.5`, Vorschau Standard, `--anwenden`, idempotent
weil nur der freie Teil (Betrag minus `hold_trade`) geordert wird),
`kraken/waisen_stops.py` (findet Schutz-Orders, deren Position es NICHT mehr
   gibt; Vorschau Standard, `--stornieren`. **Merksatz: beim Schliessen einer
   Margin-Position loescht Kraken den zugehoerigen Stop-Loss NICHT** - der Stop
   bleibt offen, sieht in der Oberflaeche wie eine offene Position aus, ein
   Schliessversuch scheitert ohne Bestand/Position, und beim Ausloesen eroeffnet
   ein Margin-SELL-Stop einen SHORT. Also nach jedem Schliessen nachsehen. Der Cron `waisen-wache`
   (30 min, no_agent, Telegram) meldet solche Waisen von selbst und storniert
   NIE),
`mosaic/kraken_stops_7_5.py` (Spot mit Buch-Einstieg; `--anwenden`, danach
`--nur-buch`),
`kraken.stop_setzen(..., leverage=, close_txid=)`, `okx.stop_setzen` /
`okx.stop_stornieren(algo_id, inst)` (inst ist PFLICHT). Nach einem `--anwenden`
NICHT noch einmal anwenden - ein zweiter Lauf storniert den frischen Stop; erst
`--nur-buch`.

## OKX-Handpositionen: keine Boersen-Stop-Kennung, Ausstieg gehoert Max

Eine von Max von Hand an der OKX-Boerse eroeffnete Position wird von der Spur
als Fremdposition uebernommen (Journal-grund `fremdposition_uebernommen`,
Positionsfeld `herkunft = boerse_handgriff`). Zwei Eigenschaften, beide
gemessen:

- **Keine Boersen-Stop-Kennung.** Die OKX-Position wurde nicht ueber den
  Orderweg der Spur mit Stop eroeffnet; stopdeckung und stops_nachziehen
  koennen deshalb weder Stop noch Trailing an der Boerse verankern (Journal-
  Vermerk im 15-Minuten-Takt: "trailing nicht ausgefuehrt: keine Boersen-
  Stop-Kennung"). Das ist der erwartete Zustand einer Handposition, kein
  defekter Waechter - der erste Stop-Ausstieg danach (grund=stop im Journal)
  ist der Haus-Stop der Spur, der den Kursabfall deckt.
- **Die Spur schliesst sie nicht automatisch.** Regel (Auftrag Max):
  `pruefe_ausstiege` und `flach_stellen` (Kill/Kill-Switch/Notaus)
  ueberspringen Positionen mit `herkunft == "boerse_handgriff"`; sie bleiben
  im Buch (Funding, Journal, Bilanz), den Ausstieg macht Max selbst. Dieselbe
  Regel gehoert an JEDEN Weg, der einen Ausstieg entscheidet (Ausstiegspruefung
  UND Notaus), und braucht je Weg eine Gegenprobe - eine normale Position muss
  weiter automatisch geschlossen werden, sonst ist die Ausnahme zur Regel
  geworden.

Zeitkorrelation bei der Rekonstruktion eines Vorfalls: Max nennt Ortszeiten
(CEST), das Journal schreibt UTC. "um 18:30 eroeffnet, direkt danach verkauft"
war hier ein Stop um 16:31:59 UTC (= 18:31:59 CEST) auf eine Position, die
schon seit dem Morgen im Buch lief; der 15-Minuten-Vermerk "trailing nicht
ausgefuehrt" ist die Uhrquelle, nicht der Vorfall selbst.

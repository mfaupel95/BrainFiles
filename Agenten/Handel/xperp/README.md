# XPERP-Bot

Handelsvorbereitung für die **XPERP-Kontrakte** von OKX — gehebelte
Perpetuals auf Krypto, Aktien und Rohstoffe. Rechnet Signal, Positionsgröße,
Stop und Ziel und **legt die fertigen Befehle vor. Ausgelöst wird von Hand.**

Stand: 2026-09-01. Entstanden aus der Frage nach einem Bot für „REUSD XPERP
long 5x Hebel".

## Was hier erlaubt ist — Spur 2

Bis zum 01.09.2026 galt pauschal „nur Spot, nur Long, kein Hebel". Seitdem
kennt `Wissen/Handelsregeln.md` zwei Spuren, und dieser Ordner ist **Spur 2**:

> **Hebel ist nicht mehr grundsätzlich verboten. Verboten bleibt, ihn von
> selbst zu nehmen.**

Eine gültige Anweisung nennt **alle vier Angaben** — Kontrakt (voller
`instId`), Richtung, Hebel als Zahl, Einsatz und Stop. Fehlt eine, wird sie
**nicht sinngemäß ergänzt**, sondern erfragt.

**Eine Rangliste aus `auswahl.py` ist ein Vorschlag, keine Anweisung.** Der Bot
eröffnet nichts aus einer Rangliste heraus und leitet keine Richtung aus dem
Trend ab.

### Die Prüfpflicht ersetzt das Verbot

An die Stelle des Verbots treten **vier Zahlen vor jeder gehebelten Order**.
`bot.py` legt sie ungefragt vor (`pruefpflicht()`):

| # | Zahl | woher |
|---|---|---|
| 1 | Liquidationsabstand gegen größten 7-Tage-Rücklauf | `hebel_deckel()` |
| 2 | Funding über die Haltedauer, mit Vorzeichen | OKX, live |
| 3 | Gebühren je Runde gegen erwarteten Gewinn | 0,05 % je Ausführung |
| 4 | **Nötige gegen beobachtete Trefferquote** | `noetige_quote()` gegen `trefferquote()` |

Zahl 4 ist die unbequeme. Sie kommt aus [[Handelsbots]]: Dort lagen nötige und
erreichte Quote über 12 Monate **immer ein bis zwei Prozentpunkte
auseinander** — übrig blieben die Gebühren. Hebel vergrößert diesen Abstand
mit, nicht nur den Gewinn.

**Widerspruchspflicht, kein Vetorecht.** Sagen die Zahlen, dass eine Anweisung
falsch gedacht ist, steht das einmal in der Ausgabe, mit Gegenvorschlag.
Bestätigt Max, wird wie angewiesen gerechnet — nicht stillschweigend kleiner.

Das Absenden der scharfen Order tut die Claude-Sitzung selbst nicht; sie
rechnet, wählt aus und legt bis zur Bestätigung fertig vor.

## Das Instrument heißt anders, als es aussieht

„REUSD XPERP" gibt es nicht zu finden. Der Kontrakt heißt
**`RE-USD_UM_XPERP-310620`** — der Bindestrich gehört zum Namen, und gelesen
ergibt „RE-USD" eben „REUSD". Drei Fallen dabei:

- **XPERP liegen unter `instType=FUTURES`**, nicht `SWAP`. Wer bei den Swaps
  sucht, findet keinen einzigen.
- Sie tragen ein **Ablaufdatum weit in der Zukunft** (RE: 2031) und heißen
  trotzdem Perpetual.
- `instCategory` trennt die Familien: **1 = Krypto (111), 3 = Aktien (46),
  4 = Rohstoffe (4)**.

`okxf.instrument()` nimmt alle drei Schreibweisen an — `RE`, `REUSD` und den
vollen `instId`.

**Auch gewöhnliche Perpetuals.** Endet die Eingabe auf `-SWAP`
(`bot.py trend --wert CHIP-USDT-SWAP …`), holt `okxf.instrument()` den normalen
SWAP-Kontrakt statt eines XPERP. Grund: CHIP als XPERP war 14 Tage alt und
setzte 1 Mio USD/Tag um, `CHIP-USDT-SWAP` 134 Tage und 24 Mio — gleicher Hebel,
gleiche `ctVal`. `--historie auto` zieht dann die tiefe Reihe desselben
Kontrakts (mehr als die 300 Signal-Kerzen).

## Die tragende Regel: Der Hebel ist Ergebnis, nicht Eingabe

Das ist der Unterschied zu einem Bot, dem man „5x" vorgibt:

```
Stop-Abstand   = 1,5 x ATR          (aus der gemessenen Schwankung)
Positionswert  = Risikobetrag / Stop-Abstand
Margin         = Positionswert / Hebel
```

Der Hebel fällt hinten heraus und wird nur noch **gedeckelt** — durch
`max_hebel` aus `wachen.json` und durch den Rücklauf der letzten sieben Tage.

**Hebel je Familie (seit 08.10.2026, Auftrag Max):** `familien.<name>.max_hebel`
ersetzt `max_hebel` für diese Familie, `familien.<name>.stop_max_pct` begrenzt
die Stopweite in % des Kurses. Gesetzt ist beides für `rohstoff` (XAU, XAG, CL,
BZ): **10x, Stop höchstens 4 %**. Der Rücklauf-Deckel bleibt davor — ein Rohstoff,
dessen letzte sieben Tage 10x nicht getragen hätten, fällt aus der Rangliste.
Bei 10x liegt die Liquidation grob bei 9–9,5 % gegen die Position, 4 % Stop
halten klaren Abstand; ein Wochenend-Gap kann ihn trotzdem überspringen. Das
Risiko je Anlauf bleibt gleich (Positionswert = Risiko / Stopabstand), nur die
gebundene Margin halbiert sich gegenüber 5x. Code: `wachen_xperp.hebel_grenze`,
`stop_max_pct`, `fuer_familie`; dieselbe Regel gilt in `../swap/`.
`Handel/README.md` hat diese Regel schon aus dem Titelvergleich gezogen: *Die
Hebelhöhe gehört an die gemessene Volatilität gekoppelt, nicht an eine
Kurserwartung.*

Warum das nicht Kosmetik ist: Bei RE ist ATR(14) **2,90 % je 4h-Kerze**. Ein
fester Stop bei −2 % liegt damit *innerhalb* des normalen Zappelns und wird
getroffen, ohne dass der Markt etwas getan hat. Bei SOL mit 1,82 % ATR wäre
derselbe Stop halbwegs brauchbar. Ein Prozentwert, der für beide gilt, gibt es
nicht.

## Dateien

| Datei | Zweck |
|---|---|
| `wachen.json` | **Eine Wahrheit für alle Grenzen.** Wird nur gelesen. |
| `okxf.py` | OKX-Zugang für Futures. Öffentliche Kerzen ohne Schlüssel; signierte Orders nur, wenn ein Mensch sie aufruft. |
| `indikatoren.py` | ATR, EMA, RSI, SuperTrend, Efficiency Ratio, Saisonalität, Volumen-Drift. Reine Rechnung, kein Netz. |
| `cvd.py` | CVD-4h-Divergenz je Kontrakt: Taker-Volumen von OKX in 4h-Eimern, Divergenz gegen den Preis. Ein Abruf, kein Orderpfad. |
| `auswahl.py` | Rangliste aller Krypto-XPERP für Long, Short und Grid. |
| `bot.py` | Lage, Trend-Anlauf, Grid. Legt Befehle vor. |
| `historie.py` | Tiefe Kerzenreihe für zu junge Kontrakte — zieht den `<Basis>-USDT-SWAP`, damit Hebel-Deckel, Trefferquote und Saisonalität auf Monaten statt Tagen stehen. |

Kein eigenes `.venv` — läuft mit dem des Marktscanners (`../scanner/.venv`,
nur Standardbibliothek).

## Aufrufe

```powershell
cd Agenten\Handel\xperp

..\scanner\.venv\Scripts\python.exe auswahl.py                 # alle drei Ranglisten
..\scanner\.venv\Scripts\python.exe auswahl.py --wert RE       # ein Wert im Detail
..\scanner\.venv\Scripts\python.exe bot.py lage  --wert SOL    # Signal und Tore
..\scanner\.venv\Scripts\python.exe bot.py trend --wert SOL    # ein Anlauf mit TP/SL
..\scanner\.venv\Scripts\python.exe bot.py grid  --wert SOL    # Raster mit TP/SL je Stufe

..\scanner\.venv\Scripts\python.exe bot.py trend --wert CHIP --historie auto
..\scanner\.venv\Scripts\python.exe historie.py CHIP           # Vergleich jung <-> tief
```

### `--historie` — wenn der Kontrakt zu jung ist

Ein frisch gelisteter XPERP trägt die Kennzahlen nicht, die vor einer
gehebelten Order zählen. `CHIP-USD_UM_XPERP-310822` war am 01.09.2026 **14 Tage
alt**; auf diesem Fenster meldete der Bot einen viel zu hohen Hebel-Deckel.
Nachgemessen am 13.09.2026 auf Tageskerzen (`historie.py CHIP`): der junge
Kontrakt (26 Tage) meldet **4,3×** und 48 % Trefferquote (Long), die tiefe
Reihe `CHIP-USDT-SWAP` (145 Tage) **2,2×** und **29 % gegen 34 % nötig — trägt
nicht**. Genau die Falle aus [[Handelsbots]]: „Kurze Fenster täuschen
zuverlässig", hier nach oben, weil der XPERP sein ganzes Leben auf einem
lokalen Tief begann.

`--historie auto` zieht den `<Basis>-USDT-SWAP` und rechnet Hebel-Deckel (auf
den **Tageskerzen** des SWAP) und Trefferquote darauf. Das **Signal** (SuperTrend, EMA, RSI, ATR jetzt) bleibt
am gehandelten Kontrakt — es beschreibt den Kurs, den man wirklich kauft.
Rechtfertigung: gleicher Index, ATR% deckungsgleich (CHIP: 4,6 % XPERP gegen
4,4 % SWAP). `--historie selbst` erzwingt den Kontrakt, `--historie <instId>`
nennt die Reihe ausdrücklich.

### `--hebel` und `--einsatz` — die Anweisung nach Spur 2

Ohne diese Schalter bleibt der Hebel **Ergebnis, nicht Eingabe** — er fällt aus
dem Stop-Abstand und wird auf den Deckel begrenzt. Eine gültige Anweisung nach
[[Handelsregeln]] Spur 2 nennt ihn aber als Zahl, samt Einsatz. Dafür:

- `--hebel N` — setzt den Hebel fest. Liegt `N` über dem Deckel, rechnet der
  Bot **wie angewiesen** und schreibt in die Prüfpflicht `ZU HOCH` mit der
  Liquidationsrechnung dazu — nicht stillschweigend kleiner (Widerspruchs­pflicht,
  kein Vetorecht).
- `--einsatz USD` — Margin. Bei `trend` je Anlauf statt `max_margin_je_anlauf_usd`,
  bei `grid` die Gesamtmargin statt `max_margin_gesamt_usd`.

```powershell
..\scanner\.venv\Scripts\python.exe bot.py trend --wert CHIP --historie auto --hebel 2
..\scanner\.venv\Scripts\python.exe bot.py grid  --wert CHIP --historie auto --hebel 3 --einsatz 80
```

Fest bleibt auch mit Anweisung: der Pflicht-Stop je Position, der Kill-Switch
beim Grid, und dass die Claude-Sitzung die scharfe Order nicht selbst absendet.

## Saisonalität im Signal — hoch gewichtet, auf Anweisung

Am 01.09.2026 angeordnet: Der TradingView-Indikator [xGhozt Prophecies: A
Forecast on the Future](https://de.tradingview.com/script/HtBJgdne-xGhozt-Prophecies-A-Forecast-on-the-Future/)
soll in die Chart-Analyse und **hoch gewichtet** werden.

Der Indikator ist **Closed-Source** — der Pine-Code ist nicht einsehbar, es gibt
keine API. Nachgebaut ist deshalb nur sein Prinzip: **Kalenderstatistik**. Er
nimmt die nächste, noch nicht existierende Kerze, liest ihren Wochentag und ihre
Tagesphase (UTC) und misst an allen früheren Kerzen desselben Rasters, wie oft
sie über ihrem Eröffnungskurs schlossen und wie groß die mittlere
Kerzenrendite war. Das rechnet `indikatoren.saisonalitaet()` aus der
Kerzenreihe, die der Bot ohnehin zieht.

**Wie es ins Signal greift** (`indikatoren.lage()`):

| Lage | Folge |
|---|---|
| Saisonalität stimmt mit SuperTrend+EMA überein | Signal bleibt, Grund trägt „+ Saisonalität bestätigt" |
| SuperTrend und EMA widersprechen sich (Signal `kein`) | **Saisonalität setzt die Richtung** |
| Saisonalität steht gegen SuperTrend+EMA | **Saisonalität überstimmt** — Signal kippt |

`richtung` wird nur gesetzt, wenn die Wochentags-Aggregation **≥ 6
Beobachtungen** hat *und* Auf-Quote (≥ 58 % / ≤ 42 %) und mittlere Rendite
dasselbe Vorzeichen zeigen. Sonst bleibt sie neutral und rührt das Signal
nicht an. RSI kann ein saisonal gesetztes Signal danach weiter als überkauft
blocken.

**Die Einschränkung steht in der Ausgabe, nicht nur hier.** Bei 300×4h-Kerzen
sind das rund **sieben Kerzen je Wochentag** (50 Tage Historie). Das ist
Rückblick auf einem dünnen Fenster, kein Backtest — genau das Muster, vor dem
[[Handelsbots]] warnt („Kurze Fenster täuschen zuverlässig"). `bot.py lage`
druckt `n` bei jeder Zeile mit, und wenn die Saisonalität das Signal dreht,
nennt der Grund-Text die Stichprobe. Das ist bewusst laut: der Faktor weicht
von der sonstigen Regel ab, dass `lage()` die Bausteine **nicht** verrechnet.

**Seit 16.09.2026 rechnet sie auf der tiefen Reihe, wenn `--historie` gesetzt ist**
(T-018). Die Saisonalität ist *Statistik* wie Hebel-Deckel und Trefferquote, nicht
Kursstruktur — und auf ~50 Tagen Kontrakthistorie hat sie zu wenige Beobachtungen.
Nachgemessen an `LINK-USD_UM_XPERP-310829` (20 Tage alt) am 16.09.2026: **n = 16**
aus dem Kontrakt gegen **n = 172** aus `LINK-USDT-SWAP` (1200 Kerzen, 200 Tage). Die
Ausgabe nennt die Basis jetzt ausdrücklich (`Basis: tiefe Reihe, 1200 Kerzen -
Statistik, nicht der Kontrakt`); die Warnung „n=… ist dünn" entfällt genau dann.
Übernommen wird sie nur, wenn die tiefe Reihe **gleichzeitig endet**
(`indikatoren._gleichzeitig`): `saisonalitaet()` liest Wochentag und Tagesphase der
*nächsten* Kerze aus dem Ende der Reihe — eine verschobene Reihe würde das Raster
still verschieben. Dafür steht der Signal-Merge in `indikatoren.signal_bauen()` an
einer Stelle. Sechs Tests halten es: `test_saisonalitaet_tief.py` (ohne Netz).

## CVD-4h-Divergenz im Signal — hoch gewichtet, auf Anweisung

Am 13.09.2026 als **dritte** hoch gewichtete Komponente gebaut. Anlass:
buildix.trade führt die **CVD-4h-Divergenz** als Signal-Label (STRONG BUY
„Akkumulation am Tief" / STRONG SELL „Verteilung am Hoch"). Nachgebaut in
`cvd.py` aus dem OKX-Taker-Volumen je Kontrakt (`okxf.taker_volumen`, 4h-Eimer,
100 Eimer Tiefe).

| Lage | Folge im SIGNAL |
|---|---|
| CVD-Richtung = aktuelles Signal | Signal bleibt, Grund „+ CVD-4h-Divergenz … bestätigt" |
| Aktuelles Signal neutral | CVD **setzt** die Richtung |
| CVD widerspricht | CVD **überstimmt** — sie läuft als letzte Komponente |

Zwölf 4h-Eimer (48 h) werden halbiert. Bärisch: jüngere Hälfte teurer, CVD-
Steigung negativ, Kurs im oberen Fensterbereich. Bullisch: gespiegelt. Zwei
Tore: die Preisbewegung muss ≥ 15 % der Fensterspanne ausmachen, die
CVD-Steigung ≥ 10 % der mittleren Eimer-Bewegung (`MIN_CVD_ANTEIL`, an 1287
Fenstern kalibriert — danach werden 8,9 % davon zum Signal). Danach bleibt die
RSI-Wache scharf.

**Warum nicht das rohe Tape:** `/market/history-trades` liefert 100 Trades je
Anfrage, das sind bei BTC-USDT-SWAP 28 Sekunden (13.09.2026 gemessen); 4 h
wären rund 4000 Anfragen je Wert. Der Taker-Volumen-Endpunkt ist derselbe
Inhalt, von der Börse aggregiert — und er liegt **nur auf `www.okx.com`**: auf
`my.okx.com` (dem Wert von `OKX_BASE` hier) und auf `eea.okx.com` kommt eine
leere Liste ohne Fehler. Dafür gibt es `okxf.rubik_basis()` mit dem Override
`OKX_BASE_RUBIK`.

`bot.py lage` zeigt die Zeile `CVD-4h …`; dreht sie das Signal, nennt der
Grund-Text Richtung, Preisbewegung, CVD-Anteil und Eimerzahl. Rangfolge aller
Bausteine, Herkunft der Zahlen und die Messungen: [[CVD-4h-Divergenz-Signal]].

## Warum drei Ranglisten und nicht eine

Long, Short und Grid brauchen **gegensätzliche** Eigenschaften. Ein Wert, der
für das eine gut ist, ist für das andere schlecht. Die entscheidende Kennzahl
für Grid ist die **Kaufman Efficiency Ratio** — Nettobewegung geteilt durch
zurückgelegten Weg:

| ER | Bedeutung | taugt für |
|---|---|---|
| nahe 1 | jeder Schritt geht in dieselbe Richtung | Trend |
| nahe 0 | viel Weg, kein Fortschritt | Grid |

Das ist messbar; „sieht seitwärts aus" ist es nicht.

## Der Hebel-Deckel

Zu jedem Wert wird der größte Rücklauf der letzten sieben Tage gemessen —
auf **Tageskerzen** (`auswahl.mae_tage`), nicht auf dem 4H-Fenster — und
daraus der Hebel gerechnet, der ihn überlebt hätte:

```
Hebel_max = 1 / (größter Rücklauf + Wartungsmarge)
```

Das ist **Rückblick und keine Zusage** — aber ein Hebel, der schon die letzte
Woche nicht überstanden hätte, braucht über die nächste nicht diskutiert zu
werden.

## Warum ein Grid mit viel Hebel nicht geht

`Handel/README.md` hat das für den Sparplan schon gemessen (Grid mit Hebel 3
im Seitwärtsjahr: **−94,4 %**). Der Grund in einem Satz:

> Ein Grid braucht Tiefe zum Nachkaufen, ein Hebel verbietet Tiefe.

`bot.py grid` rechnet das nach, statt es zu wiederholen. Die oberste Stufe hat
den weitesten Weg bis zum Boden des Rasters; überlebt sie ihn nicht, sterben
die oberen Stufen, bevor die unteren kaufen:

```
Hebel_max = 1 / (Spannentiefe + Wartungsmarge + Puffer)
```

Bei 11 % Spanne sind das 6,9× — bei 17 % nur noch 4,8×. Der Bot senkt den
Hebel selbständig auf den kleineren der beiden Deckel und sagt, warum.

**Jede Stufe ist eine eigene isolierte Position mit eigenem Ziel und einem
gemeinsamen Stop unter dem Raster.** Dadurch wird sie *ausgestoppt* statt
liquidiert — der Verlust ist der gerechnete Betrag, nicht die ganze Margin.
Liegt der Stop trotzdem hinter der Liquidation, meldet der Bot das je Stufe.

## Die Tore

Ein Wert wird nur ohne Warnung vorgeschlagen, wenn alle drei offen sind:

| Tor | Standard | warum |
|---|---|---|
| `min_historie_tage` | 21 | Unter drei Wochen existiert die 14-Tage-Kennzahl nicht. |
| `min_umsatz_24h_usd` | 3 Mio | Das XPERP-Universum ist dünn — siehe unten. |
| `max_hebel` gegen Hebel-Deckel | 5 | Was den letzten Rücklauf nicht überlebt hätte. |

`vola_tor_pa` (1,20) stammt aus `../scanner/wachen.json` und ist in
`auswahl.py` als `!vola` sichtbar.

## Gemessen am 01.09.2026

**Das Universum ist dünn.** Außer BTC (170 Mio) und ETH erreicht kaum ein
XPERP nennenswerten Tagesumsatz. RE liegt bei **0,9 Mio USD**, ARB bei 3,4
Mio. Bei 50 USD je Anlauf ist das tragbar, aber es ist der Grund, warum
`min_umsatz_24h_usd` überhaupt existiert.

**Von 103 Krypto-XPERP sind nur 77 bewertbar** (21 Tage Mindesthistorie), und
von diesen überlebt die Mehrheit keine 5×.

Die Bewertungen am 01.09.2026 (korrigierte Messung — Hebel-Deckel auf
**Tageskerzen**, über 200 Tage statt 300×4h = 50 Tage):

| Wert | Vola p.a. | ER | Hebel-Deckel | Umsatz 24h | Grid | Long |
|---|---|---|---|---|---|---|
| **SOL** | 48 % | 0,10 | 3,6× | 21,8 Mio | 82 | 83 |
| **HYPE** | 77 % | 0,04 | 4,1× | 13,7 Mio | 85 | **92** |
| **ZEC** | 95 % | 0,15 | 1,7× | 12,1 Mio | 86 | 91 |

**Damit besteht keiner der drei das Hebel-Tor (≥ 5) mehr.** Die frühere Fassung
dieser Tabelle nannte SOL 10,0×, HYPE 6,4× und ZEC 5,8× und leitete daraus ab,
alle drei hätten „alle Tore bestanden“ — beides ist zurückgenommen.

**Falle — der Messfehler dahinter:** Der Deckel wurde aus **300 4H-Kerzen**
abgeleitet, das sind nur **50 Tage**; SOLs Rücklauf vom 31.05.2026 lag
außerhalb dieses Fensters (9,5 % statt 27,9 %, Deckel 10× statt 3,5×). Seit
dem 13.09.2026 rechnet `bot.hebel_deckel()` auf **Tageskerzen**
(`auswahl.mae_tage`). Wer den Deckel nachrechnet, muss auf Tageskerzen
rechnen — nicht auf dem 300-Kerzen-Fenster des gehandelten Kontrakts, sonst
kommt wieder eine zu optimistische Zahl heraus.

**RE selbst besteht zwei Tore nicht:** Vola 173 %, Umsatz 0,9 Mio,
Hebel-Deckel **2,5×** long und 1,2× short. Die Grid-These stimmt allerdings —
ER 0,22 bei 69 % zurückgelegtem Weg in sieben Tagen ist echtes Gezappel. Nur
der Hebel trägt nicht.

**Für Short gab es keinen brauchbaren Kandidaten.** Jeder Wert mit echtem
Abwärtstrend fiel entweder durch das Vola-Tor (GRVT 192 %, NES 135 %), durch
den Hebel-Deckel (JTO 3,8×) oder durch die Liquidität (POL 0,5 Mio). Das ist
ein Befund, kein fehlendes Feature.

## Zwei Fehler beim Bauen — beide standen im ersten Wurf

Sie stehen als Kommentar im Code, weil sie beim nächsten Mal genauso passieren:

- **`volCcy24h` enthält `ctVal` bereits.** Wer nochmal multipliziert, meldet
  BONK mit 167 Billionen USD Tagesumsatz und stellt die ganze
  Liquiditätsrangliste auf den Kopf.
- **Eine fehlende Kennzahl als `0,0 %` zu drucken ist gefährlicher als eine
  Lücke.** DASH und POL standen oben in der Grid-Liste, weil ihre nicht
  existierende 14-Tage-Rendite als „+0.0 %" erschien und wie perfekte
  Seitwärtsbewegung aussah. Beide waren erst acht Tage alt.

## Die Falle bei Zahl 4: eine hohe Trefferquote misst manchmal nichts

Beim Grid auf SOL meldete die Prüfpflicht **99,6 % beobachtete Trefferquote**
gegen 86,4 % nötige — sieht nach klarem Vorsprung aus. Die Zahl dahinter:
**237 Ziele gegen einen einzigen Stop.**

Das Verlustereignis ist damit nicht gemessen, sondern nicht vorgekommen. Eine
Quote aus einem Gegenbeispiel ist keine Schätzung. Genau dieses Muster —
enges Ziel, weiter Stop, hohe Quote — beschreibt [[Handelsbots]]: Der eine
Stop kostet mehr, als die vielen Treffer eingebracht haben. Bei 2,01 % Ziel
gegen 12,15 % Stop braucht es **sieben Treffer, um einen Stop zu bezahlen.**

`bot.py` warnt deshalb, sobald die seltenere der beiden Seiten unter zehn
Ereignissen liegt. Beim Trend-Anlauf auf SOL (113 Ziel / 153 Stop) tut es das
nicht — dort sind beide Seiten besetzt.

## Grenzen

- **Der Bot löst nichts aus.** Er rechnet, wählt aus und legt bis zur
  Bestätigung fertig vor; abgesendet wird von Max oder von einem dafür
  gebauten Skript.
- **Kein Backtest.** Der Bot rechnet die *jetzige* Lage. Ob die Mechanik über
  ein Jahr trägt, ist damit nicht beantwortet — und bei XPERP auch nicht
  beantwortbar: Die ältesten Kontrakte laufen seit Mai 2026.
- **Die Grundlinie steht in [[Handelsbots]]:** Über lange Zeiträume lag jede
  getestete mechanische Krypto-Strategie nahe null, leicht darunter. Die
  Gebühren fressen den Vorteil. Dieser Bot sucht ein gutes Verhältnis, keinen
  großen Wurf, und er kann trotzdem Geld verlieren.
- **Funding fehlt in der Rechnung.** Bei RE gemessen: +0,0031 % je Periode,
  Long zahlt. Über Tage summiert sich das gegen eine gehaltene Position.
- **4h-Kerzen lösen nicht auf**, ob Hoch oder Tief zuerst kam. Ein Stop und
  ein Ziel in derselben Kerze werden als Stop gewertet — vorsichtig gerechnet.

Verwandt: [[Handelsbots]], [[Marktscanner]], [[Handelsregeln]],
`../README.md` (DCA-Simulator und Grid ohne Hebel).

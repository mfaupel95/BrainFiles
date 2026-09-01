# XPERP-Bot

Handelsvorbereitung für die **XPERP-Kontrakte** von OKX — gehebelte
Perpetuals auf Krypto, Aktien und Rohstoffe. Rechnet Signal, Positionsgröße,
Stop und Ziel und **legt die fertigen Befehle vor. Ausgelöst wird von Hand.**

Stand: 2026-09-01. Entstanden aus der Frage nach einem Bot für „REUSD XPERP
long 5x Hebel".

## Was hier erlaubt ist — Spur 2

Bis zum 01.09.2026 galt pauschal „nur Spot, nur Long, kein Hebel". Seitdem
kennt `Wissen/Schutzregeln.md` zwei Spuren, und dieser Ordner ist **Spur 2**:

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

## Die tragende Regel: Der Hebel ist Ergebnis, nicht Eingabe

Das ist der Unterschied zu einem Bot, dem man „5x" vorgibt:

```
Stop-Abstand   = 1,5 x ATR          (aus der gemessenen Schwankung)
Positionswert  = Risikobetrag / Stop-Abstand
Margin         = Positionswert / Hebel
```

Der Hebel fällt hinten heraus und wird nur noch **gedeckelt** — durch
`max_hebel` aus `wachen.json` und durch den Rücklauf der letzten sieben Tage.
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
| `indikatoren.py` | ATR, EMA, RSI, SuperTrend, Efficiency Ratio. Reine Rechnung, kein Netz. |
| `auswahl.py` | Rangliste aller Krypto-XPERP für Long, Short und Grid. |
| `bot.py` | Lage, Trend-Anlauf, Grid. Legt Befehle vor. |
| `historie.py` | Tiefe Kerzenreihe für zu junge Kontrakte — zieht den `<Basis>-USDT-SWAP`, damit Hebel-Deckel und Trefferquote auf Monaten statt Tagen stehen. |

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
alt**; auf diesem Fenster meldete der Bot Hebel-Deckel 4,8× und Trefferquote
67 %. Auf der realen Historie des `CHIP-USDT-SWAP` (**133 Tage**, seit dem
Listing 21.04.2026) sind es **2,2×** und **28 % gegen 34 % nötig — trägt
nicht**. Genau die Falle aus [[Handelsbots]]: „Kurze Fenster täuschen
zuverlässig", hier nach oben, weil der XPERP sein ganzes Leben auf einem
lokalen Tief begann.

`--historie auto` zieht den `<Basis>-USDT-SWAP` und rechnet Hebel-Deckel und
Trefferquote darauf. Das **Signal** (SuperTrend, EMA, RSI, ATR jetzt) bleibt
am gehandelten Kontrakt — es beschreibt den Kurs, den man wirklich kauft.
Rechtfertigung: gleicher Index, ATR% deckungsgleich (CHIP: 4,6 % XPERP gegen
4,4 % SWAP). `--historie selbst` erzwingt den Kontrakt, `--historie <instId>`
nennt die Reihe ausdrücklich.

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

Zu jedem Wert wird der größte Rücklauf der letzten sieben Tage gemessen und
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

Die Werte, die am 01.09.2026 **alle** Tore bestanden:

| Wert | Vola p.a. | ER | Hebel-Deckel | Umsatz 24h | Grid | Long |
|---|---|---|---|---|---|---|
| **SOL** | 48 % | 0,10 | **10,0×** | 21,8 Mio | 82 | 83 |
| **HYPE** | 77 % | 0,04 | 6,4× | 13,7 Mio | 85 | **92** |
| **ZEC** | 95 % | 0,15 | 5,8× | 12,1 Mio | 86 | 91 |

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

Verwandt: [[Handelsbots]], [[Marktscanner]], [[Schutzregeln]],
`../README.md` (DCA-Simulator und Grid ohne Hebel).

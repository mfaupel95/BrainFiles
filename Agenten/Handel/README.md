# DCA-Simulator

Rechnet Sparplan-Strategien auf historischen Kursen durch — mit und ohne Hebel.
**Das Werkzeug rechnet. Es handelt nicht und ist mit keinem Broker verbunden.**

Stand: 2026-08-10

## Was es beantwortet

- Was wäre aus einem festen Betrag je Monat geworden?
- Was ändert Hebel daran — und was kostet er?
- **Wie viele Tranchen wären unterwegs liquidiert worden?** Das ist bei gehebeltem
  DCA die entscheidende Größe, nicht der Einstiegspreis.
- Wie stark hängt das Ergebnis vom Startzeitpunkt ab?

## Aufrufe

```powershell
.venv\Scripts\python.exe dca.py                      # PLTR, 200 EUR/Monat, ohne Hebel
.venv\Scripts\python.exe dca.py --vergleich          # Hebel 1/2/3/5 nebeneinander
.venv\Scripts\python.exe dca.py --hebel 3 --details  # jede Tranche einzeln
.venv\Scripts\python.exe dca.py --rollierend 18      # jeder Startmonat, 18 Monate Haltedauer
```

Weitere Schalter: `--ticker`, `--betrag`, `--intervall woche|monat|quartal`,
`--start`, `--ende`, `--zins`, `--modus isoliert|cross`, `--neu` (Kurse neu abrufen).

Die Ausgabe ist standardmäßig knapp. `--details` nur, wenn die einzelnen Tranchen
wirklich gebraucht werden.

## Die Modellannahmen

Sie stehen als Konstanten oben in `dca.py` und **gehören an den echten Broker
angepasst**, sobald das Instrument feststeht:

| Größe | Standard | Bedeutung |
|---|---|---|
| `WARTUNGSMARGE` | 0,5 % | Anteil des Positionswerts, der als Sicherheit stehen bleiben muss |
| `FINANZIERUNG_PA` | 6,0 % | Jahreszins auf das geliehene Kapital |

Drei Entscheidungen, die das Ergebnis spürbar beeinflussen:

- **Liquidation wird am Tagestief geprüft, nicht am Schlusskurs.** Ein Broker
  schließt zwangsweise, sobald der Kurs die Schwelle berührt; ob er sich bis zum
  Abend erholt, ist dann egal. Am Schlusskurs zu prüfen würde die Strategie
  systematisch schönrechnen.
- **`isoliert` gegen `cross`.** Isoliert stirbt jede Tranche einzeln; bei cross
  trifft es alle gleichzeitig, dafür stützen sich die Positionen gegenseitig.
- **Nach einer Liquidation läuft der Plan weiter.** Das entspricht einem echten
  Sparplan — und es ist der Grund, warum manche Läufe trotz vieler Liquidationen
  gut aussehen: Das Geld *nach* dem Absturz hat den Aufschwung mitgenommen.

Nicht modelliert: Spread, Ordergebühren, Steuern, Slippage, Dividenden,
Wechselkurs EUR/USD. Alle wirken gegen die Strategie — die Ergebnisse sind also
eher zu gut als zu schlecht.

## Grenzen des Backtests — bitte lesen

**PLTR hat nur sechs Jahre Historie, und die war außergewöhnlich.** Der Kurs ist
seit dem IPO (September 2020) etwa um das Siebzehnfache gestiegen. Jeder Backtest
auf diesem Titel misst zu einem großen Teil genau das.

Was die rollierende Auswertung zeigt (Stand 10.08.2026, 200 EUR/Monat, isolierte Margin):

| Haltedauer | Hebel | Median | Schlechtestes | Fenster im Minus | mit Liquidation |
|---|---|---|---|---|---|
| 36 Monate | 1 | +354 % | +15 % | 0 von 36 | — |
| 36 Monate | 3 | +1045 % | +10 % | 0 von 36 | 30 von 36 |
| 18 Monate | 1 | +70 % | −54 % | 17 von 54 | — |
| 18 Monate | 3 | +183 % | −95 % | 17 von 54 | 30 von 54 |

Zwei Lehren daraus:

1. **Die Haltedauer entscheidet mehr als der Hebel.** Bei 36 Monaten war kein
   einziges Fenster negativ, bei 18 Monaten fast ein Drittel. Das ist kein
   Qualitätsmerkmal der Strategie, sondern eine Eigenschaft dieses Kursverlaufs.
2. **Liquidationen sind der Normalfall, nicht die Ausnahme.** Bei Hebel 3 traf es
   in 83 % der Dreijahresfenster mindestens eine Tranche. Dass die Endrendite
   trotzdem hoch aussieht, liegt am Nachkaufen zu Tiefstkursen — das setzt voraus,
   dass genug Geld nachfließt und der Titel sich erholt.

Ein Gegenbeispiel aus demselben Datensatz: Derselbe Plan mit Hebel 3, gestartet im
Januar 2021 und im Januar 2023 beendet, endet bei **−92,7 %** — 19 von 24 Tranchen
liquidiert. Dieselbe Strategie, dasselbe Papier, anderes Fenster.

36 rollierende Fenster aus einer einzigen Kursgeschichte sind **keine 36
unabhängigen Beobachtungen**. Wer die Aussagekraft erhöhen will, testet dieselbe
Mechanik auf mehreren Titeln und über längere Zeiträume (`--ticker`).

## Der Titelvergleich (`vergleich.py`)

```powershell
.venv\Scripts\python.exe vergleich.py --ab-pltr --dauer 18   # gemeinsamer Zeitraum
.venv\Scripts\python.exe vergleich.py --hebel 3 --dauer 18   # volle Historie je Titel
```

Die acht Titel sind **Testfälle, keine Empfehlungsliste**. Entscheidend sind die
der Gruppe „gescheitert" (PTON, ZM) und „abgestiegen" (INTC): Wer nur AAPL, NVDA
und TSLA testet, testet ausschließlich Überlebende und bekommt garantiert ein zu
gutes Ergebnis (Survivorship Bias).

Ergebnis über die volle Historie, Hebel 3, 18 Monate Haltedauer, isolierte Margin:

| Titel | Rolle | Fenster | Median | Schlechtestes | im Minus | mit Liquidation |
|---|---|---|---|---|---|---|
| PLTR | Ausgangsfall | 54 | +183 % | −95 % | 31 % | 56 % |
| NVDA | überlebt | 314 | +71 % | −100 % | 27 % | 70 % |
| AAPL | überlebt | 531 | +46 % | −100 % | 34 % | 56 % |
| TSLA | überlebt | 177 | +33 % | −100 % | 37 % | 81 % |
| SPY | breiter Markt | 386 | +26 % | −97 % | 21 % | **15 %** |
| INTC | abgestiegen | 540 | +16 % | −97 % | 41 % | 51 % |
| ZM | gescheitert | 71 | −5 % | −96 % | 54 % | 59 % |
| PTON | gescheitert | 66 | −52 % | −100 % | 64 % | **100 %** |

Drei Befunde:

1. **Hebel verstärkt die Richtung, er erzeugt keine.** Bei den Überlebenden hebt
   er den Median, bei den Gescheiterten drückt er ihn tiefer. PTON: −27 % ohne
   Hebel, −64 % mit Hebel 3 (gemeinsamer Zeitraum).
2. **Mit Hebel 3 hatte jeder einzelne Titel mindestens ein Fenster nahe
   Totalverlust** — auch AAPL, auch SPY. Das ist keine Eigenschaft schlechter
   Titel, sondern des Hebels.
3. **Die Liquidationsrate hängt an der Volatilität, nicht an der Rendite.** TSLA
   ist langfristig deutlich gestiegen und hatte trotzdem in 81 % der Fenster
   Liquidationen; SPY in 15 %. Im gemeinsamen Zeitraum ist TSLA der lehrreichste
   Fall: Median +15 % ohne Hebel, aber **±0 % mit Hebel 3 bei 100 %
   Liquidationsrate** — die Schwankung hat den gesamten Gewinn aufgezehrt.

Für die Konstruktion eines Agenten folgt daraus: **Die Hebelhöhe gehört an die
gemessene Volatilität gekoppelt, nicht an eine Kurserwartung.** Volatilität lässt
sich aus der Vergangenheit schätzen, die künftige Rendite nicht.

## Dateien

- `dca.py` — Simulator und Kommandozeile
- `vergleich.py` — dieselbe Mechanik über mehrere Titel
- `kursdaten.py` — Abruf über yfinance, lokaler Cache unter `daten/`
- `daten/*.csv` — zwischengespeicherte Kurse (12 h gültig, danach neuer Abruf)
- `.venv/` — eigene Python-Umgebung, an ihren Pfad gebunden

Der Cache ist Absicht: yfinance ist eine inoffizielle Schnittstelle und kann ohne
Vorwarnung ausfallen. Liegen die Daten lokal, läuft die Simulation weiter und sagt
dazu, wie alt der Stand ist.

## Handelbarkeit über OKX (Stand 10.08.2026)

Geprüft mit `onchainos token search` nach erfolgreichem Wallet-Login (Apple).

**Entscheidend: Es sind durchweg Spot-Token, keine Futures.** Tokenisierte Aktien
(xStocks von Backed, „on"-Varianten von Ondo) bilden den Kurs 1:1 ab — **Hebel ist
darüber nicht möglich**. Ein gehebelter DCA auf eine Aktie lässt sich mit den
installierten OKX-Skills nicht umsetzen; die CLI kennt `swap`, `defi` und
`strategy` (Limit-Orders), aber keine Perpetuals oder Futures.

Liquidität der jeweils besten Variante:

| Titel | Bestes Token | Kette | Liquidität | Holder |
|---|---|---|---|---|
| BTC | nativ | — | Börsenliquidität | — |
| NVDA | NVDAon | Ethereum | 5.238.832 USD | 4.255 |
| NVDA | NVDAx | Solana | 3.188.586 USD | 63.430 |
| MSFT | MSFTon | Ethereum | 828.547 USD | 843 |
| MSFT | MSFTx | Solana | 162.870 USD | 4.904 |
| PLTR | PLTRx | Solana | 120.913 USD | 1.222 |
| PLTR | PLTRon | Ethereum | **178 USD** | 288 |
| IREN | IRENon | beide | **keine Angabe** | 112 / 90 |

Daraus folgt für die Instrumentenwahl:

- **NVDA ist on-chain um Größenordnungen besser handelbar als PLTR** — Faktor 25
  bis 40 bei der Liquidität.
- **PLTRon auf Ethereum ist mit 178 USD Pool-Liquidität praktisch nicht
  handelbar.** Gleicher Name, gleicher Preis, unbrauchbar. Vor jedem Kauf die
  konkrete Contract-Adresse prüfen, nicht das Symbol.
- **IREN existiert on-chain nur pro forma.**
- Zusätzliche Risiken gegenüber der echten Aktie: Emittentenrisiko (Backed,
  Ondo), Slippage bei dünnen Pools, kein Stimmrecht, steuerliche Einordnung
  offen.

## Coins statt tokenisierter Aktien (Stand 10.08.2026)

**Kein Hebel über die installierten Skills** — weder auf Aktien noch auf Krypto.
`strategy` kann nur preisgetriggerte Limit-Orders, `defi` nur Earn/Lending/Pools.
Es gibt kein Perpetual- oder Futures-Kommando. Der realistische Bauplan für einen
Agenten ist damit: **Spot-DCA über `swap`, ausgelöst per `strategy create-limit`.**

Marktlage zum Messzeitpunkt — die Zahlen unten sind dadurch geprägt:

| | BTC | ETH | SOL | ADA | AVAX | LUNC |
|---|---|---|---|---|---|---|
| vom Allzeithoch | −49 % | −61 % | −71 % | −93 % | −95 % | −100 % |

DCA ohne Hebel, 18 Monate Haltedauer, volle Historie:

| Titel | Fenster | Median | Schlechtestes | im Minus |
|---|---|---|---|---|
| BTC-USD | 126 | **+59 %** | −52 % | **18 %** |
| SOL-USD | 59 | +27 % | −75 % | 41 % |
| ETH-USD | 88 | +14 % | −50 % | 39 % |
| SPY (Referenz) | 386 | +11 % | −39 % | 18 % |
| DOGE-USD | 88 | +10 % | −50 % | 40 % |
| XRP-USD | 88 | +8 % | −48 % | 42 % |
| ADA-USD | 88 | +7 % | −63 % | 45 % |
| AVAX-USD | 55 | **−21 %** | −56 % | 62 % |
| LUNC-USD | 68 | **−21 %** | −95 % | 60 % |

- **BTC ist der einzige Coin, der die SPY-Referenz klar schlägt** — höherer Median
  bei gleicher Verlustquote (18 %).
- **Alle übrigen Coins liegen in 39–62 % der Fenster im Minus**, zwei bis drei Mal
  so oft wie SPY. Zwei sind im Median negativ.
- Der Abstand BTC zu Rest ist größer als der Abstand BTC zu SPY.

### Warum diese Tabelle zu gut aussieht

**Survivorship Bias, und bei Krypto ist er dominant.** Getestet werden kann nur,
was noch Kursdaten liefert. Tausende Coins aus den Zyklen 2017 und 2021 sind
verschwunden — samt Kurshistorie. Wer 2021 breit in Altcoins gespart hat, hat mit
hoher Wahrscheinlichkeit Positionen gehalten, die es in dieser Tabelle gar nicht
mehr gibt. LUNC ist nur enthalten, weil der Restwert als „Classic" weiterläuft;
ein echter Totalausfall verschwindet aus dem Datensatz und damit aus jeder
Statistik.

**Gegenläufig wirkt der Endzeitpunkt:** Ein Backtest, der im Bärenmarkt endet,
zeigt schlechtere Zahlen als einer, der am Allzeithoch endet. Die Aktien-Tabellen
weiter oben enden nahe Höchstständen, diese hier tief darunter. Beide Tabellen
sind deshalb **nicht direkt miteinander vergleichbar** — dafür ist die SPY-Zeile
da, sie steht in beiden.

## Swap-Kosten (gemessen 10.08.2026)

Mit `onchainos swap quote` gemessen, USDC → WBTC, nicht geschätzt:

| Kette | Betrag | Impact | Router-Fee | Fee % | Gas-Einheiten |
|---|---|---|---|---|---|
| Ethereum | 100 | 0,02 % | 1,52 USD | 1,52 % | 1.308.000 |
| Ethereum | 200 | 0,01 % | 1,79 USD | 0,89 % | 1.536.000 |
| Ethereum | 1000 | 0,00 % | 0,92 USD | 0,09 % | 790.108 |
| Solana | 200 | 0,06 % | 0,00 USD | 0,00 % | 285.300 |

`estimateGasFee` sind **Gas-Einheiten, nicht Dollar**. 1,5 Mio Einheiten auf
Ethereum sind bei 10 Gwei und ETH ≈ 1.868 USD rund 28 USD; auf Solana kosten
285.300 Lamports etwa 2 Cent.

Eingerechnet in `dca.py --kette solana|ethereum`. Wirkung auf einen
BTC-Sparplan über die volle Historie:

| Plan | Solana | Ethereum |
|---|---|---|
| 200 USD je Monat | 20 USD = **0,1 %** | 4.291 USD = **14,9 %** |
| 50 USD je Woche | 31 USD = **0,1 %** | 17.696 USD = **56,9 %** |

**Kette und Intervall entscheiden mehr als die Titelwahl.** Ein wöchentlicher
DCA auf Ethereum verliert über die Hälfte des eingesetzten Kapitals an Gas,
bevor irgendeine Kursbewegung stattgefunden hat. Für kleine Tranchen ist
Ethereum unbrauchbar.

## Der Agent (`agent.py`)

```powershell
.venv\Scripts\python.exe agent.py init --kette solana --betrag 200 --intervall monat
.venv\Scripts\python.exe agent.py status
.venv\Scripts\python.exe agent.py vorbereiten
.venv\Scripts\python.exe agent.py erledigt --menge 0.00313098
```

**Mehrere Pläne parallel.** `plan.json` hält eine Liste; jeder Plan hat einen
Kurznamen und eigene Token, Beträge, Intervalle und Grenzen. Angesprochen wird
er mit `--plan <name>`, wobei ein eindeutiges Präfix genügt (`--plan btc-e`).
Bei mehrdeutigem Präfix bricht der Aufruf ab und listet die Kandidaten — damit
nicht versehentlich der falsche Sparplan angefasst wird. Bei nur einem Plan darf
`--plan` entfallen.

| Befehl | Wirkung |
|---|---|
| `init --name X` | Plan anlegen, inklusive Sicherheitsscan des Zieltokens |
| `status` | alle Pläne mit Tranchen, Kostenbasis, Fälligkeit, offenen Orders |
| `vorbereiten --plan X` | Quote holen, Kosten prüfen, Befehl vorlegen |
| `erledigt --plan X --menge N` | ausgeführte Tranche eintragen |
| `check` | still prüfen, was fällig ist (für Routinen) |
| `abgleich` | Buchführung gegen echten Wallet-Bestand |
| `pruefen` | Sicherheitsscan der Zieltoken |
| `backtest --plan X` | genau diesen Plan auf historischen Kursen rechnen |
| `entfernen --plan X` | Plan löschen (mit Historie nur per `--trotzdem`) |

`vorbereiten` holt eine echte Quote, rechnet die Gesamtkosten aus, prüft sie
gegen die Grenze und **legt den Befehl vor, ohne ihn auszuführen**.

Eine ältere `plan.json` mit nur einem Plan wird beim ersten Aufruf automatisch
umgestellt; die alte Fassung bleibt als `plan.json.v1` liegen, weil eine
Kaufhistorie sich nicht rekonstruieren lässt.

Drei eingebaute Sicherungen:

- **Contract-Adressen sind fest hinterlegt, Symbole werden nicht aufgelöst.** Zu
  jedem bekannten Symbol existieren Nachbauten mit gleichem Namen und fast
  gleichem Preis, aber ohne Liquidität — auf Solana gibt es ein zweites „WBTC"
  mit 55.206 USD statt 664 Mio, bei PLTR eine Variante mit 178 USD Pool.
- **Kostengrenze** (Standard 1 % der Tranche). Ein negativer Preis-Impact wird
  dabei nicht gutgeschrieben, sonst könnte eine Kursdelle die Grenze aushebeln.
- **Honeypot-Flag** aus der Quote führt zum Abbruch.

**Der Agent löst nichts aus.** Kein Swap, keine Order, keine Signatur — er gibt
den Befehl aus, ausgeführt wird er von Hand. Das ist bewusst so und ändert sich
nicht.

### Limit-Order statt Marktkauf

```powershell
.venv\Scripts\python.exe agent.py vorbereiten --limit --abschlag 5
```

Setzt den Trigger 5 % unter den aktuellen Kurs; ausgeführt wird erst, wenn der
Kurs dorthin fällt — die Tranche kann also auch liegenbleiben. Das ist der
Unterschied zum reinen DCA und gehört bewusst entschieden.

**Slippage: 0,5 % statt der CLI-Vorgabe von 15 %.** Der Standardwert von
`strategy create-limit` ist für einen Sparplan viel zu weit; 0,5 % passt zu den
gemessenen Impact-Werten (0,04–0,06 % auf Solana) und lässt Luft bis zur
Ausführung. MEV-Schutz wird eingeschaltet.

### Abgleich, Sicherheitsscan, offene Orders

```powershell
.venv\Scripts\python.exe agent.py abgleich   # Plan gegen echten Wallet-Bestand
.venv\Scripts\python.exe agent.py pruefen    # Sicherheitsscan des Zieltokens
```

`abgleich` vergleicht die Buchführung in `plan.json` mit `wallet balance`. Der
Plan weiß nur, was eingetragen wurde — wer eine Order platziert und `erledigt`
vergisst, lässt beide auseinanderlaufen. `status` zeigt zusätzlich offene
Limit-Orders: eine platzierte, aber noch nicht ausgelöste Order bindet Kapital,
ohne im Bestand aufzutauchen.

Der Sicherheitsscan läuft automatisch bei `init` und übersetzt die Flags in
Klartext.

### Der Plan im Backtest

```powershell
.venv\Scripts\python.exe agent.py backtest --plan cbbtc --dauer 18
```

Rechnet **genau den konfigurierten Plan** durch — mit seinem Betrag, seinem
Intervall und den gemessenen Swap-Kosten seiner Kette. Das verbindet die
Buchführung mit dem Simulator, statt beide getrennt zu bedienen.

Der Backtest rechnet auf dem **Basiswert** (cbBTC → BTC-USD, SOL → SOL-USD). Ein
Wrapper folgt dem Kurs, trägt aber zusätzlich das Risiko seines Verwahrers — das
steckt in keiner Kursreihe und wird deshalb separat über `pruefen` gemeldet.

### Nativ oder gewrappt — ein echter Zielkonflikt

Gemessen am 10.08.2026, 18 Monate Haltedauer, Solana-Kosten eingerechnet:

| | cbBTC (gewrappt) | SOL (nativ) |
|---|---|---|
| Risikostufe im Scan | **MEDIUM** | **LOW** |
| Befunde | nachprägbar, Rechte nicht abgegeben, **einfrierbar** | nur „Quellcode nicht offen" |
| Verwahrer | Coinbase | keiner — natives Asset |
| Median (18 Mon.) | **+59 %** | +22 % |
| Schlechtestes | **−52 %** | −77 % |
| Fenster im Minus | **18 %** | 41 % |

**Die bessere Kursstatistik und das geringere Verwahrrisiko liegen bei
verschiedenen Token.** BTC ist in jeder Kursdimension ruhiger, kommt on-chain
aber nur als Nachbildung mit Verwahrer. SOL ist das native Asset ohne Bridge und
ohne Einfrierrecht, dafür deutlich schwankungsanfälliger. Diese Abwägung lässt
sich nicht wegrechnen.

### Welches BTC auf Solana?

Es gibt kein natives Bitcoin auf Solana — nur Nachbildungen, und die tragen ein
Risiko, das der Bitcoin-Kurs nicht abbildet. Beide geprüften Varianten sind
`riskLevel: MEDIUM`, aber **aus unterschiedlichen Gründen**:

| | WBTC | cbBTC |
|---|---|---|
| Vollständiger Name | Wrapped BTC (**Wormhole**) | Coinbase Wrapped BTC |
| Liquidität | 664.124.947 USD | 21.659.723 USD |
| Holder | — | 85.610 |
| Verwahrung | Bridge (Wormhole, 2022 gehackt) | Coinbase, reguliert |
| `isMintable` | ja | ja |
| `isNotRenounced` | ja | ja |
| `isHasFrozenAuth` | nein | **ja** — Guthaben einfrierbar |

Keine der beiden ist „sicher". WBTC hat deutlich mehr Liquidität, cbBTC einen
regulierten Verwahrer, der dafür einfrieren kann. Beide sind über
`agent.py init --token WBTC|cbBTC` wählbar.

### Als Routine

```powershell
.venv\Scripts\python.exe agent.py check
```

Schweigt, wenn nichts ansteht — eine Routine, die täglich „nichts zu tun" meldet,
wird nach einer Woche ignoriert. Einplanung über die Windows-Aufgabenplanung,
nicht über `/schedule`: Letzteres legt Cloud-Agenten an, die weder auf
`plan.json` noch auf die lokale `onchainos`-Anmeldung zugreifen können. Der
Befehl steht in [Wissen/Routinen.md](../Wissen/Routinen.md).

## Grid — kaufen unten, verkaufen oben

Ein Grid legt zwischen zwei Grenzen N Preisstufen. Fällt der Kurs auf eine
Stufe, wird gekauft; steigt er auf die nächsthöhere, wird genau diese Position
verkauft. Der Gewinn eines Zyklus ist der Stufenabstand minus Kosten.

```powershell
.venv\Scripts\python.exe grid.py --ticker BTC-USD --spanne-auto --stufen 10 --kapital 2000 --start 2024-08-01
.venv\Scripts\python.exe grid.py --ticker BTC-USD --spanne-auto --raster   # Stufenzahl vergleichen
```

### Befund 1: Mehr Stufen sind nicht besser

BTC, 2.000 USD, Spanne 49.121–126.198, ab 08/2024, Solana-Kosten:

| Stufen | Zyklen | Kosten | Ergebnis | vs. Halten |
|---|---|---|---|---|
| 5 | 5 | 5 USD | **+399 USD (+20 %)** | +447 |
| 10 | 22 | 8 USD | +200 USD (+10 %) | +247 |
| 20 | 106 | 19 USD | +179 USD (+9 %) | +226 |
| 40 | 479 | 50 USD | +167 USD (+8 %) | +214 |
| 80 | 1.454 | 105 USD | **−53 USD (−3 %)** | −6 |

Jede zusätzliche Stufe erzeugt Trades, aber keinen zusätzlichen Ertrag. Ab einer
gewissen Dichte frisst die Gebühr den Stufengewinn — bei 80 Stufen kippt das
Ergebnis ins Minus. **Wenige, breite Stufen schlagen viele enge.**

`grid-init` warnt automatisch, wenn der Stufengewinn nicht klar über den Kosten
eines vollständigen Zyklus (Kauf *und* Verkauf) liegt.

### Befund 2: Im Trend verliert das Grid

Derselbe Aufbau, BTC 01/2023–01/2025 (starker Aufwärtstrend):

| | Ergebnis |
|---|---|
| Grid, 10 Stufen | +718 USD (+35,9 %) |
| Buy-and-Hold | **+9.352 USD (+467,6 %)** |
| Differenz | **−8.634 USD** |

Das Grid verkauft auf dem Weg nach oben und steigt nicht wieder ein. **Grids
gewinnen in Seitwärtsmärkten und verlieren in Trends** — nach oben durch
entgangenen Gewinn, nach unten durch immer weiteres Zukaufen. Verlässt der Kurs
die Spanne nach unten, sitzt das gesamte Kapital fest und es passiert nichts
mehr.

Deshalb steht in jeder Ausgabe der Vergleich zu Buy-and-Hold. Ein Grid, das
schlechter ist als schlicht halten, hat seinen Zweck verfehlt.

### Grid im Agenten

```powershell
.venv\Scripts\python.exe agent.py grid-init --name btc-grid --token cbBTC ^
    --unten 50000 --oben 80000 --stufen 8 --kapital 2000
.venv\Scripts\python.exe agent.py grid-orders --plan btc-grid
```

`grid-orders` ermittelt den aktuellen Kurs und legt **alle Kaufstufen darunter**
als fertige `strategy create-limit`-Befehle vor, jeweils mit Verkaufsziel. Die
Stufen sind geometrisch verteilt (gleicher prozentualer Abstand) — bei
Kryptokursen sinnvoller als gleiche absolute Abstände.

Verkaufs-Orders erscheinen bewusst nicht im ersten Wurf: Vor dem Kauf gibt es
nichts zu verkaufen. Wird eine Kauf-Order ausgeführt, gehört die zugehörige
Verkaufs-Order auf die nächsthöhere Stufe (`--direction sell`).

**Der Agent platziert nichts.** Er legt die Befehle vor. Einmal platziert,
arbeitet das Raster allerdings selbständig — die Orders lösen ohne weitere
Rückfrage aus, wenn ihr Trigger erreicht wird. Das ist der Punkt, an dem aus
einer vorbereiteten Liste ein laufender Bot wird, und er gehört bewusst
entschieden.

Grid- und DCA-Pläne liegen gemeinsam in `plan.json` und lassen sich mischen;
`check` und die Routine betreffen nur DCA-Pläne, weil ein Grid keine Fälligkeit
kennt.

## Grid mit Hebel — die Konstruktion trägt nicht

```powershell
.venv\Scripts\python.exe grid.py --spanne-auto --start 2024-08-01 --stufen 10 --hebel 3
.venv\Scripts\python.exe grid.py --spanne-auto --start 2025-08-01 --hebel 3 --stress 40
```

Die Idee war, kleine gehebelte Positionen durch ein Grid abzusichern. Gerechnet
mit `dca.Tranche` (dieselbe Liquidationsmechanik wie beim DCA), Liquidation am
Tagestief, Gebühr auf die Positionsgröße, Finanzierung auf das geliehene
Kapital.

**Seitwärtsjahr 08/2024–08/2025** — genau das Umfeld, in dem ein Grid gewinnt:

| Hebel | Ergebnis | Liquidationen |
|---|---|---|
| 1 | **+200 USD (+10,0 %)** | – |
| 2 | −628 USD (−31,4 %) | 4 Stufen, 888 USD Margin |
| 3 | −1.889 USD (−94,4 %) | 10 Stufen, 2.218 USD Margin |

**Abwärtsjahr 08/2025–08/2026** (BTC −44 %), 8 Stufen:

| | Ergebnis |
|---|---|
| Hebel 1 | −176 USD (−8,8 %) |
| Hebel 3 | −1.718 USD (−85,9 %), 6 von 8 Stufen liquidiert |
| Buy-and-Hold | −874 USD (−43,7 %) |

Mit zusätzlichem Stress von −40 %: −1.807 USD (−90,3 %), 7 Stufen liquidiert.

### Warum das kein Parameterproblem ist

Bei Hebel 3 greift die Liquidation rund **3,6 Gitterstufen** unter jedem
Einstieg (`stufen_bis_liquidation()` rechnet das aus dem Stufenabstand aus). Ein
Gitter von 8 Stufen Tiefe kann damit nie durchlaufen werden: Die unteren Stufen
sind nicht erreichbar, ohne dass die oberen vorher sterben.

**Ein Grid braucht Tiefe zum Nachkaufen, ein Hebel verbietet Tiefe.** Die beiden
Anforderungen widersprechen sich direkt — deshalb verliert die Kombination auch
im Seitwärtsmarkt, wo das ungehebelte Grid gewinnt. Ein Grid ist keine
Absicherung; es erhöht das Engagement, während der Kurs fällt.

### Ein Modellierungsfehler, der dabei auffiel

Der erste Lauf meldete 283 Liquidationen bei 8 Stufen und −4.058 % auf das
Kapital. Ursache: Nach einer Liquidation wurde die Stufe frei, der Kurs stand
weiterhin darunter, also wurde sofort neu gekauft — mit unbegrenzt
nachgeschossener Margin. `simuliere()` führt jetzt ein Kapitalkonto (`frei`):
Käufe reduzieren es, Verkäufe geben Margin plus Gewinn zurück, liquidierte
Margin ist weg. Ist das Kapital aufgebraucht, endet der Handel. Die ungehebelten
Ergebnisse sind davon unberührt (Kontrolllauf: −176 USD vorher wie nachher).

## Reinvestition — was sich wie oft anlegen lässt

```powershell
.venv\Scripts\python.exe reinvest.py --kapital 500,5000,50000 --kette solana
.venv\Scripts\python.exe reinvest.py --kette ethereum
```

Ertragsquellen am 10.08.2026 über `onchainos defi search` (Solana):

| Quelle | Art | APY | TVL |
|---|---|---|---|
| Kamino Main Pool | Lending | 6,83 % | 94,3 Mio |
| Jupiter | Single Earn | 5,08 % | 430,6 Mio |
| Kamino | Single Earn | 4,64 % | 19,9 Mio |
| Orca V3 | DEX-Pool | 27,6–35,9 % | 2,7–26,3 Mio |
| Raydium V3 | DEX-Pool | 23,0 % | 6,1 Mio |

**Mindestertrag, ab dem eine Reinvestition sich rechnet** — das ist die Zahl,
die über die Frequenz entscheidet:

| | Solana | Ethereum |
|---|---|---|
| Kosten je Vorgang | 0,02 USD + 0,06 % | 28,00 USD + 0,90 % |
| Schwelle bei 6,83 % APY | **0,30 USD** | **472,18 USD** |
| erreichbar bei 500 USD Kapital | 116× im Jahr | **nie** |
| erreichbar bei 50.000 USD | 11.560× | 7× |

Auf Ethereum lohnt sich Reinvestieren unterhalb von 50.000 USD Kapital
überhaupt nicht — der Ertrag erreicht die Gebührenschwelle nie.

**Mehr Frequenz ist nicht besser.** Endwert nach drei Jahren, Kamino, Solana:

| Kapital | gar nicht | jährlich | monatlich | täglich |
|---|---|---|---|---|
| 500 | 602 | 609 | **612** | 589 |
| 5.000 | 6.024 | 6.095 | **6.132** | 6.112 |
| 50.000 | 60.245 | 60.954 | 61.326 | **61.337** |

Bei 500 USD ist tägliches Reinvestieren *schlechter* als monatliches: 365 × 0,02
USD Fixkosten schlagen den Zinseszinsvorteil. Das Optimum wandert mit dem
Kapital nach oben.

### Was in diesen Zahlen nicht steckt

- **Impermanent Loss** bei allen DEX-Pools — die 23–36 % APY sind Brutto vor IL,
  und die höchsten Raten hängen an den kleinsten TVLs (2,7 Mio bei Orca).
- **Protokollrisiko** bei Lending und Earn.
- **Grid-Zyklen sind keine vergleichbare Quelle.** 69 Zyklen pro Jahr klingen
  nach häufigem Ertrag, entstanden aber in einem Zeitraum, in dem das Grid
  insgesamt 161 USD *verlor*. Häufige Zyklen bedeuten häufige Umsätze, nicht
  Gewinn.

## Was noch fehlt

Der Simulator ist bewusst instrumentenneutral gebaut. Für den nächsten Ausbau
— Signale, wann die nächste Tranche fällig ist, und Order-Vorbereitung — muss
feststehen, **womit** tatsächlich gehandelt wird: CFD, US-Option oder Aktie ohne
Hebel. Davon hängen Margin-Mechanik, Gebührenmodell und die Frage ab, ob es
überhaupt eine API gibt.

**Ausgelöst werden Orders in keinem Fall vom Programm.** Es bereitet vor und legt
mit allen Werten vor; der letzte Schritt bleibt beim Menschen.

## Freigabefenster (`freigabe.py`)

Gebaut am 02.09.2026 für T-028. Es erfüllt Punkt 3 aus
`Wissen/Schutzregeln.md`: scharf geschaltet wird von Hand, in einem Fenster,
das die Werte zeigt, sie anpassbar macht und ein Feld zum Bestätigen hat.

**Es führt nichts aus — es gibt frei.** Keine Order, kein OKX, kein Kraken. Es
nimmt Aufträge entgegen, lässt sie im Rahmen der Wachen verändern und gibt die
bestätigten zurück. Ausgeführt werden sie vom Automaten, der `wachen.json`
liest. So bleibt die Ausführung dort, wo die Grenzen sind.

```
python freigabe.py --spur hebel --beispiel
python freigabe.py --spur spot --auftrag auftrag.json --aus frei.json
```

Exit-Code 0 = bestätigt, 1 = abgelehnt. Fenster schließen und Escape zählen
als Ablehnung; Ablehnen verwirft auch, was in derselben Runde schon bestätigt
wurde.

### Was das Fenster nicht zulässt

| Regel | Wie sie im Code steht |
|---|---|
| Kein Wert über eine Grenze | Die **Obergrenze jedes Reglers ist der Wachen-Wert** — nicht erst die Prüfung danach |
| Hebeldeckel senkbar, nie hebbar | Regler geht 1 bis `max_hebel`, der Hebel selbst fällt aus der Stopweite |
| Kein Prozent-Stop | Spur 2 rechnet die Stopweite in ATR, `stop_atr_faktor` ist die Untergrenze |
| `wachen.json` bleibt unberührt | Die Datei wird nur gelesen |

Reißt eine Grenze, ist der Bestätigen-Knopf **gesperrt** und die Zeile steht mit
Ist gegen Soll in der Tabelle. Halten alle Grenzen, aber `freigabe.erfuellt`
oder `handel_erlaubt` stehen auf `false`, gibt das Fenster den Auftrag als
**Papier** frei und sagt das auf dem Knopf — Live wird nie stillschweigend zu
Papier.

### Angebunden an `handeln.py --live`

Seit dem 02.09.2026 ruft `scanner/handeln.py` das Fenster vor jedem Einstieg
auf — aber nur im `--live`-Pfad und erst, wenn alle bisherigen Sperren offen
sind. Dazu kam eine **siebte Sperre**: ohne Sitzung am Bildschirm kein Live.

Zwei Entscheidungen, die den Ausschlag geben:

**Ausstiege laufen nie durch das Fenster.** Ein Stop muss auch dann greifen,
wenn niemand davorsitzt. Bestätigt wird nur, was Geld *bindet*.

**Die Uhr ist der eigentliche Schutz, nicht die Sitzungserkennung.** Am
02.09.2026 gemessen: `sys.stdin.isatty()` meldet in der Git-Bash unter Windows
auch dann ein Terminal, wenn stdin umgeleitet wurde — als alleinige Sperre
taugt es nicht. Deshalb lehnt das Fenster nach `FREIGABE_ZEITLIMIT_S` (120 s)
ohne Bedienung von selbst ab. Geht es je versehentlich in einer geplanten
Aufgabe auf, blockiert es sie nicht, sondern sagt Nein. Jede Bedienung setzt
die Uhr zurück — wer davorsitzt, hat alle Zeit.

Als zweite Hürde setzen die Wrapper in `../Routinen/` jetzt
`MAXHIRN_ROUTINE=1`. Das ist die ausdrückliche Ansage „hier sitzt niemand" und
schlägt die Erkennung. Die Tagesroutine läuft ohnehin mit `--papier`.

Fällt das Fenster aus — Tk fehlt, Anzeige weg, Abbruch — wird **nicht
gehandelt**. Ein Fehler beim Bestätigen darf nie zu einem ungefragten Kauf
werden.

`xperp/bot.py` ist noch nicht angebunden; er legt Befehle ohnehin nur vor.

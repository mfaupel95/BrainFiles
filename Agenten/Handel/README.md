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
- `hausspur_regeln.py` — 17 Haus-Spuren als eine Signal-Schnittstelle für die
  Freqtrade-Strategie `freqtrade/user_data/strategies/HausSpur.py` (seit
  10.10.2026, Bots in `freqtrade/bots.json`, Urteile über `bots.py backtest`)
- `leitstand_freqtrade.py` — Leitstand-Reiter FreqTrade (Strg+8): alle Bots,
  Zustand, Runden, Backtest-Urteil; nur lesend über `freqtrade_bridge.py`

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

## Journal außer Haus (`spiegelstand.py`) — Bedingung 4

Jede Spur im Dauerlauf kopiert `handelsjournal.csv` und `zustand.json` nach
jedem Zyklus zusätzlich nach `journal_zweitziel` aus ihrer `wachen.json`
(`Q:\Handel_Journal\<spur>`; der Marktscanner direkt in `Q:\Handel_Journal`).
Die Kopie entsteht **nach** dem Schreiben von Herzschlag und Journal: ein
hängendes Zweitlaufwerk darf den Zyklus verzögern, nicht den Herzschlag
verschlucken. Ein fehlendes Ziel ist kein Fehler des Laufs (Rückgabecode bleibt
0) — sichtbar wird es stattdessen im Zustand der Spur
(`journal_zweitziel_ok` / `_info`, geschrieben nur beim Wechsel) und in
`handeln.py --wachen`.

`spiegelstand.py` ist die eine Rechnung dafür, lesend und ohne Netz:

    scanner/.venv/Scripts/python.exe spiegelstand.py

Es vergleicht je Spur **byte-genau** (wie `cmp`) und zeigt Ziel, Journalzeilen,
Alter des Herzschlags und den Vermerk. Rückgabecode 0 = jede Spur im Dauerlauf
ist byte-gleich, 1 = mindestens eine Abweichung. Spuren mit `wachen.json`, die
nicht in `dauerlauf.SPUREN` stehen (kraken mit eigenem Zeitfenster, `orb` als
Altbestand), werden mitgeprüft und gekennzeichnet, aber nicht als Fehler
gezählt.

**Zwei Fälle, die wie ein Fehler aussehen und keiner sind** (16.09.2026):
Ein Testlauf der Spuren schreibt in die echten Spurenordner; die Kopie auf `Q:`
folgt erst im nächsten Zyklus, also meldet der Vergleich bis dahin
`ABWEICHUNG`. Und `macd_mtf` stand wochenlang auf „abweichend", weil sein
Journal beim Umbau der Skalierung umbenannt wurde (`handelsjournal.falsch-
skaliert-20260915.csv`) und die alte Kopie auf `Q:` liegen blieb; sie wurde
gegen den lokalen Altstand byte-geprüft und entfernt — seitdem sind beide
Seiten ohne Journal, und das zählt als gleich.

Zwei Verbraucher hängen daran: der **Tagesbericht** zeigt den Stand als eigene
Zeile (`spiegelstand.kurz()`, im Fehlerfall hervorgehoben), und die
**Systemprüfung** ruft dasselbe Modul morgens als Block 11 auf. Eine
überschriebene oder fehlende Kopie fällt damit spätestens am nächsten Morgen
auf, statt still zu bleiben.

## Risikostufen (`risikostufe.py`) — derselbe Handel, größere Beträge

Ein Messwerkzeug, kein Gewinnhebel: dieselben Wachen, dieselben Regeln, nur ein
Faktor auf die Beträge (1 / 2 / 4 für `niedrig` / `mittel` / `hoch`). Zweck ist
**mehr Beobachtungen je Zeiteinheit** — bei 20-EUR-Einsätzen dauert jede
Statistik Monate.

    scanner/.venv/Scripts/python.exe dauerlauf.py --risiko mittel   # zweiter Lauf
    Routinen\handel-dauerlauf.ps1 -Risiko mittel                    # als Wächter

Jede Spur liest `HANDEL_RISIKO` aus ihrer Umgebung, skaliert beim Laden ihre
Wachen (`skaliere`) und schreibt Zustand und Journal mit Suffix
(`zustand.mittel.json`, `handelsjournal.mittel.csv`). Der Basislauf bleibt
unberührt, und **ohne die Variable ändert sich nichts**.

Drei Regeln machen eine Stufe ungefährlich: sie geht **nie live** (die Spuren
verweigern `--live`, der Dauerlauf übergibt nur `--papier`), sie sendet und
empfängt **kein Telegram** (zwei Läufe an einem Bot nehmen sich die Nachrichten
weg), und der **Spiegel** läuft nur in der Basis (gleicher Einsatz in jeder
Stufe, sonst zwei Schreiber auf denselben Dateien).

Was skaliert wird — und was nie (Marktdaten, Messwerte, Kontoschwellen) —, steht
in `MaxHirn/Wissen/Handelsregeln.md`; geprüft wird über jede Spur in
`tests/test_risikostufe.py`, die Stufe selbst mit `spiegelstand.py --risiko
mittel` (Bedingung 4) und `auswertung_alle.py --risiko mittel`.

Sichtbar wird die Stufe an drei Stellen: die **Handelszentrale** hat einen
Umschalter Basis/mittel/hoch in der Kopfzeile (Startwert `--risiko mittel`), der
**Tagesbericht** traegt eine Zeile je laufender Stufe, und `handeln.py --wachen`
zeigt die skalierten Grenzen. Ohne Stufe aendert sich an allen dreien nichts.

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
`Wissen/Handelsregeln.md`: scharf geschaltet wird von Hand, in einem Fenster,
das die Werte zeigt, sie anpassbar macht und ein Feld zum Bestätigen hat.

**Es führt nichts aus — es gibt frei.** Keine Order, kein OKX, kein Kraken. Es
nimmt Aufträge entgegen, lässt sie im Rahmen der Wachen verändern und gibt die
bestätigten zurück. Ausgeführt werden sie vom Automaten, der `wachen.json`
liest. So bleibt die Ausführung dort, wo die Grenzen sind.

```
python freigabe.py --spur hebel --beispiel
python freigabe.py --spur spot --auftrag auftrag.json --aus frei.json
python freigabe.py --spur kraken --beispiel --nur-pruefen   # rechnet nur, kein Fenster
```

Exit-Code 0 = bestätigt, 1 = abgelehnt. Fenster schließen und Escape zählen
als Ablehnung; Ablehnen verwirft auch, was in derselben Runde schon bestätigt
wurde.

Bedienung per Tastatur: **Enter** bestätigt, **Entf** und **Escape** lehnen
ab. Invoke auf einen gesperrten Knopf tut nichts — ein Auftrag, der eine
Grenze reißt, lässt sich also auch per Enter nicht durchdrücken.

### Prüflauf ohne Fenster (`--nur-pruefen`)

Rechnet den Auftrag und gibt jede Wachen-Zeile aus (Ist, Soll, hält/REISST)
— **ohne Fenster und ohne Bestätigung**. Der Lauf bestätigt nichts und gibt
nichts frei; er ist zum Nachprüfen aus einer Routine gedacht und für den Test
dieses Moduls. Exit-Code 0 = alles hält, 1 = eine Grenze reißt oder der
Zustand (Freigabe, `handel_erlaubt`) steht noch offen.

### Protokoll (`freigabe_journal.jsonl`)

Jede Entscheidung wird angehängt: Bestätigung **und** Ablehnung, mit Grund
(`Zeitlimit` / `abgebrochen`), Spur, Instrument, Modus (live/papier) und den
Werten. Vorher hinterließ ein abgelehntes Fenster keine Spur. Die Datei ist
reines Protokoll: sie wird nur geschrieben, nie gelesen und entscheidet
nichts. Ein Schreibfehler wird verschluckt — er darf ein Freigeben nie
verhindern.

### Bestand und Zeitfenster in der Anzeige

Der Ergebnisblock zeigt zusätzlich den **Bestand vor dem Auftrag** (gebunden,
offene Positionen) und den Stand des **Handy-Fensters**
(`freigabefenster.py`) für diese Spur. Best effort: fehlt das Modul, steht
dort `n/a` — das Fenster scheitert nie daran.

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
sind. Dazu kam eine **siebte Sperre**: eine Freigabe von Hand muss vorliegen.

Seit dem 11.09.2026 hat diese siebte Sperre zwei Fassungen — dieselbe Aufteilung
wie in `xperp/handeln.py`:

* **Sitzung am Bildschirm** (`sys.stdin.isatty()`, und `MAXHIRN_ROUTINE` nicht
  gesetzt): vor jedem Einstieg geht das Bestätigungsfenster aus `freigabe.py`
  auf, je Vorschlag einzeln.
* **Kein Bildschirm, aber offenes Zeitfenster** (`freigabefenster.py`): die
  Freigabe am Handy per `/ja` tritt an die Stelle des Fensters. Ohne sie bliebe
  der Dauerbetrieb dauerhaft auf Papier — siehe den Befund unten.

Beide Wege werden **unmittelbar vor dem Einstieg noch einmal** geprüft: zwischen
der Sperrenprüfung und dem Kauf liegen Netzabfragen, und `/stop` kann in dieser
Zeit greifen. Ist das Fenster dann zu, unterbleibt der Einstieg.

Die Begründung der Sperre nennt immer das Wort *Freigabefenster*. Daran hängt
`dauerlauf.nur_fenster_fehlt`: nur wenn **allein** die Freigabe noch fehlt,
fragt der Dauerlauf überhaupt am Handy nach. Eine Zeile, die anders heißt,
führt dazu, dass nie gefragt wird — und ein `/ja` folgenlos bleibt.

Zwei Entscheidungen, die den Ausschlag geben:

**Ausstiege laufen nie durch das Fenster.** Ein Stop muss auch dann greifen,
wenn niemand davorsitzt. Bestätigt wird nur, was Geld *bindet*.

**Eine stillgelegte Spur sperrt das Fenster.** Seit 12.09.2026 liest
`freigabe.py` das Feld `stillgelegt` aus der `wachen.json` der Spur
(`freigabe.stillgelegt()`) und führt es als eigene Zeile in der Wachen-Tabelle:
`Stillgelegt  true  kein Live  REISST`. Betrifft heute Spur 3 (Kraken). Der
Knopf ist **gesperrt** und heißt „Stillgelegt"; der Hinweis sagt, dass hier
nichts freigegeben wird — weder live noch als Papier, weil `kraken/handeln.py`
stillgelegte Spuren ohnehin verweigert.

Warum gesperrt und nicht Papier: Ein bestätigter Papierauftrag wäre eine Zusage,
die niemand einlöst. „Werte anpassen" wäre ebenfalls falsch — es gibt nichts
anzupassen, die Spur ist abgeschaltet. Gelesen wird das Feld, nicht eine Liste
im Code: Beim Wiederanschalten setzt du `stillgelegt` in `wachen.json` zurück,
im Fenster ist nichts nachzuziehen. Nachweis: `tests/test_freigabe_papier.py`
(inkl. Gegenprobe, dass eine aktive Spur weiter `live` gibt) und
`freigabe.py --spur kraken --beispiel --nur-pruefen` →
`stillgelegt: hier wird nichts freigegeben`.

**Der Ausstiegsgrund wird nach Schwere benannt, nicht nach Nähe.** Seit
12.09.2026 prüft `pruefe_ausstiege` erst die Liquidationsschwelle, dann den
Stop, dann das Ziel — in `xperp/handeln.py` und in `swap/handeln.py` gleich.
Die Schwelle liegt immer hinter dem Stop; stünde der Stop zuerst, stünde bei
einem Totalverlust „stop" im Journal und die Liquidationszeile wäre toter
Code. Am Geld ändert die Reihenfolge nichts: gerechnet wird mit dem echten
Kurs, geschlossen wird unabhängig vom Grund. Nachweis: `xperp/test_ausstieg.py`
(9 Tests, Long und Short, inklusive Kurs genau auf der Schwelle; der Order-Pfad
ist im Test durch einen Werfer ersetzt und wird nie erreicht).

### Wie oft gefragt wird (seit 12.09.2026)

Die Frage ans Handy ist eine Bitte, kein Dauerzustand. `neue_anfrage_erlaubt()`
in `freigabefenster.py` hält zwei Wiedervorlage-Fristen ein:

* **2 Stunden** nach einer unbeantworteten Anfrage. Die Antwortfrist selbst
  bleibt bei 30 Minuten, gefragt wird aber frühestens nach zwei Stunden erneut —
  vorher stand hier den ganzen Abend im Halbstundentakt dieselbe Frage.
* **12 Stunden** nach einer Ablehnung. Ein `/nein` um 21:06 wurde am 12.09.2026
  um 21:18 wortgleich erneut gestellt; eine gerade abgelehnte Frage wird
  weggewischt, und mit ihr die nächste, auf die es ankommt. Ein `/stop` wirkt
  genauso, ein beendeter Lauf (`Dauerlauf beendet`) nicht — nach einem Neustart
  darf wieder gefragt werden.

Grundlage ist der eigene Zustand in `freigabe_fenster.json`
(`anfrage_gestellt`, `zuletzt_geschlossen`, `schliess_grund`), keine zweite
Merkdatei. **Das ist keine Sperre:** kein Pfad wird geschlossen, keine Grenze
angehoben, keine Freigabe verweigert — es wird nur nicht gefragt. Wer es sich
anders überlegt, schaltet am Bildschirm scharf (`freigabe.py`) oder antwortet
auf die nächste Anfrage.

Nachweis: `tests/test_telegram_freigabe.py`, Klassen `WiedervorlageTest` und
`WiedervorlageImLaufTest` (die zweite prüft, dass die Frist im Dauerlauf
ankommt, nicht nur in der Hilfsfunktion).

### Befund 10.09.2026, behoben am 11.09.2026 — das Handy-Fenster erreichte
den Live-Pfad nicht

`freigabefenster.py` (das Zeitfenster für `/ja` und `/nein`) war nur in
`dauerlauf.py` verdrahtet, nicht in `scanner/handeln.py`. Zwei Fehler wirkten
zusammen, beide auf der **sicheren** Seite — es wurde nie etwas live gehandelt:

1. **Es wurde nie gefragt.** `dauerlauf.nur_fenster_fehlt` liest die
   Sperren-Zeile aus `handeln.py --vorschau`. Der alte Rumpf druckte diese
   Zeile aber nur im `--live`-Zweig, den die Vorschau nie betritt. Ohne Zeile
   keine Anfrage, ohne Anfrage kein `/ja`, ohne `/ja` nie ein Fenster.
2. **Ein `/ja` wäre folgenlos geblieben.** Die siebte Sperre verlangte eine
   Sitzung am Bildschirm; aus einer geplanten Aufgabe heraus ist `sys.stdin`
   keine Konsole. Der Dauerlauf startete die Spur bei offenem Fenster korrekt
   mit `--live`, `handeln.py` fiel aber sofort auf Papier zurück.

Behoben in `scanner/handeln.py`: die Sperrenprüfung ist jetzt die Funktion
`sperren_live()` (wie in `xperp/handeln.py`), sie nennt ihre Gründe auch unter
`--vorschau`, und `zeitfenster_offen()` tritt neben `sitzung_da()`. Nachgeprüft
am 11.09.2026 mit `scanner/tests/test_handeln_sperren.py` (8 Tests) und einem
Lauf `--live` mit stillgelegtem Order-Pfad: ohne Fenster eine Sperre, mit
Fenster `[]`, Einstiegszweig mit `live=True` erreicht, acht Zeilen im
Freigabeprotokoll, `wachen.json` und `zustand.json` unverändert.

Was das **nicht** ändert: `xperp` (Spur 2) hatte den Weg schon; geblieben sind
die 24-Stunden-Obergrenze eines Fensters, `/stop`, die Sperre bei `EV < 0` und
das Verwerfen eines offenen Fensters, wenn der Dauerlauf endet.

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
## Prognose (`prognose.py`)

Angelegt am 11.09.2026 auf Max' Anweisung: bei sehr günstigen
Einstiegsgelegenheiten über **alle** Märkte hinweg scannen und melden.

Der Unterschied zum Marktscanner ist der Blickwinkel. `scanner/scan.py` sieht
elf Werte an und liefert die Rangliste, aus der gekauft wird. `prognose.py`
sieht den ganzen Markt — alle Spot-Paare in USDT und USDC über einem
Mindestumsatz — und sucht Lagen mit klarem Verhältnis von Chance zu Risiko, in
**beiden Richtungen**:

- **LONG** — Rücksetzer in einem intakten Aufwärtstrend, Ziel ist das
  60-Tage-Hoch.
- **SHORT** — das Spiegelbild: Erholung in einem Abwärtstrend, Ziel ist das
  60-Tage-Tief.

Die Richtung steht als erste Spalte in jeder Tabelle und im Klartext in der
Meldung (`LONG`/`SHORT`). Was die Tore nicht passiert, wird nicht gemeldet; ein
Tag ohne Meldung ist ein Ergebnis, kein Ausfall.

**Es handelt nicht.** Kein Orderaufruf, keine Position, kein Zustand. Die
Grenzen aus `wachen.json` gelten für Prognose nicht, weil sie keine Order
stellt. Sie ist ein Beobachter.

```
python prognose.py                  # ganzer Markt, Bericht + Meldung
python prognose.py --kurz           # nur die Tabellen
python prognose.py --alle           # auch zeigen, was durchgefallen ist
python prognose.py --ohne-meldung   # Bericht schreiben, nichts senden
python prognose.py --werte 60       # nur die 60 umsatzstärksten Märkte
```

Exit-Code 0 = mindestens ein Treffer, 1 = keiner. Berichte nach
`prognose_berichte/JJJJ-MM-TT.json` und `neuester.json`.

### Die Tore (`prognose.json`) — kalibriert, nicht geschätzt

Alle Tore müssen gleichzeitig halten. Wo es die Grenze schon gibt, steht
derselbe Wert wie in `scanner/wachen.json` — eine zweite Wahrheit wäre eine
zweite Meinung zum selben Geld.

| Tor | LONG | SHORT | Warum |
|---|---|---|---|
| Score | ≥ 60 | ≥ 45 | long-kalibrierte Skala — siehe unten |
| RSI(14) | ≤ 55 | ≥ 45 | nicht überhitzt / nicht überverkauft |
| Abstand | zum Hoch −25 % bis −4 % | zum Tief +4 % bis +25 % | Rücksetzer / Erholung, kein gebrochener Trend |
| Volatilität p.a. | ≤ 1,2 | ≤ 1,2 | wie `max_volatilitaet_pa` in wachen.json |
| Trend | Preis über SMA100 | Preis unter SMA100 | in die Richtung des längeren Trends |
| Volumen (5 Tage zu 30 Tagen) | ≥ 0,5 | ≥ 0,5 | sonst ist der Markt eingeschlafen |
| Chance/Risiko | ≥ 1,5 | ≥ 1,5 | gegen das Hoch bzw. das Tief der 60 Tage |
| Stop | 5 % bis 12 % | 5 % bis 12 % | wie `pflicht_stop_prozent_min/max` |

**Die Short-Seite hat eine eigene Score-Schwelle, und das ist der Punkt.** Die
Bewertung in `bewertung.py` ist auf die Long-Frage kalibriert; gemessen am
13.09.2026 über 31 Märkte (1D) liegt sie auf der Short-Seite strukturell
tiefer:

| Richtung | Median | q75 | Maximum |
|---|---|---|---|
| LONG | 57,5 | 64,7 | 71,4 |
| SHORT | 34,9 | 39,1 | 53,3 |

Mit derselben Zahl 60 wäre das Short-Tor über dem Tagesmaximum gelegen — es
wäre nie aufgegangen, und die Short-Seite hätte nichts gemeldet, ohne dass es
auffällt. 45 ist auf der Short-Verteilung das obere Quartil (q75 39,1), also
derselbe Rang statt derselben Zahl. Wer `mindest_score: 60` ändert, muss neu
messen.

`bewertung.bewerten(kerzen, richtung=)` spiegelt die Chance-Bausteine (Preis
unter den SMAs, Abwärtsrendite, Erholung vom Tief); Gewichte und Rechenweg
bleiben dieselben — es entsteht keine zweite Formel. Der Aufruf ohne Richtung
bleibt `long`, der Marktscanner ist damit unberührt.

**Die Short-Seite kam am 13.09.2026 dazu, weil eine Prognose ohne Richtung die
halbe Antwort schuldig bleibt.** Erster Lauf mit identischer Score-Schwelle:
31 Märkte, 6 LONG, **0 SHORT** — obwohl WLFI-USDT alle übrigen Tore offen hatte
und nur am Score scheiterte. Messung siehe oben, eigene Schwelle, danach:
7 günstig, 6 LONG / 1 SHORT (WLFI-USDT, Erholung 18,6 %, C/R 1,79).

**Die erste Fassung fand nichts — über 41 Märkte an einem normalen Tag.** Zwei
Fehler, beide im Aufbau:

1. Das Ziel war auf `mindest_cr` *hochgezogen* worden. Damit war das
   Chance/Risiko-Tor immer erfüllt und filterte nichts. Jetzt ist das Ziel das
   beobachtete 60-Tage-Hoch; ob es sich lohnt, sagt der C/R-Wert.
2. Das Volumentor stand auf `volumen_bestaetigung` aus `bewertung.py` — eine
   Kennzahl, die *Volumenausweitung* verlangt, also eine Breakout-Eigenschaft.
   Ein Rücksetzer hat aber fallendes Volumen. Jetzt zählt das Verhältnis der
   letzten 5 Tage zum 30-Tage-Schnitt direkt, und geprüft wird nur, dass der
   Markt nicht eingeschlafen ist.

Nach der Kalibrierung blieben am 11.09.2026 zwei Werte übrig: LINK-USDT
(Score 63,1 · RSI 50,7 · −15,0 % vom Hoch · C/R 2,86) und BNB-USDT
(75,1 · 53,9 · −8,4 % · C/R 1,61). Nachweis: `tests/test_prognose.py`.

### Was Prognose nicht ist

Keine Empfehlung. Der Name ist Max', die Sache ist eine Auswahl. Sie ersetzt
keinen Einstieg über die Freigabe: Wer kaufen will, schaltet die Spur über das
Freigabefenster scharf, und dort gelten die Grenzen aus `wachen.json`.

## NautilusTrader-Node (`nautilus/`, Paper)

Ein OKX-Demo-Node auf NautilusTrader 1.231.0 — die fünfte Spur, aber eine ohne
Orderpfad: ein **Quoten-Feed**. `wachen.json` darin führt `handel_erlaubt: false`.

**Stand 12.09.2026: vom flüchtigen Ort in den versionierten geholt.** Der Node
lag unter `Werkstatt/nautilus-trader/`. Die Werkstatt ist ein Junction auf
`O:\Werkstatt`, dort räumt `datensortierung.ps1` auf, und der Ordner war in
keiner Sicherung — ein Aufräumlauf hätte die Arbeit gelöscht. Jetzt liegt er
unter `Agenten/Handel/nautilus/` und damit in `sichern.ps1`/`zweitkopie.ps1`.

Die Sicherungen nehmen `.git`- und `.venv`-Ordner generell aus
(`/XD .venv … .git` in `sichern.ps1`); die Umgebung ist aus
`requirements`/`pip freeze` nachbaubar. Die sechs Commits des eigenen `.git`
liegen seit 12.09.2026 ausser Haus im privaten GitHub-Repo `mfaupel95/nautilus`
(Remote `origin`, Zweig `master`); diese Datei und `README-live-node.md`
tragen die Vorgeschichte trotzdem weiter.

**Das Quotenproblem ist geklärt** (ausführlich in `nautilus/README-live-node.md`):
Der Data-Client meldet sich mit Schlüssel zusätzlich am privaten
business-Websocket an; scheitert das, verbindet der ganze Data-Client nicht.
Zweitens hält ein scheiternder Order-Client den Node 60 Sekunden beim Start auf,
sodass keine Strategie startet. Auslöser war die IP-Whitelist des OKX-Schlüssels:
Der Rechner geht über NordVPN ins Netz, die Ausgangs-IP wechselt.

Reparatur: **Der Data-Client bekommt keine Zugangsdaten mehr** (Quoten sind
öffentlich), und der **Order-Client ist opt-in** — im GUI ein Häkchen. Nachweis:
`test_gui_quote_pfad.py` holt 41 Quote-Ticks in 22 Sekunden über den echten
GUI-Pfad; der Test ist die Regressionssicherung.

Offen bleibt der **Orderpfad**: Dafür muss die aktuelle IP im OKX-Portal
freigegeben sein, und der DEMO-Schlüssel braucht die Trade-Berechtigung (er ist
laut `demo_order_test.py` nur `read_only`).
## Gitter-Spur (`gitter/`) — dasselbe Grid, im laufenden Betrieb

Seit 14.09.2026 liegt das Grid auch als Spur im Dauerlauf: `gitter/handeln.py`
fuehrt ein Papierbuch auf OKX-Spot (`BTC-USDT`), Stufen aus
`Handel/grid.py:stufen_bauen` — eine Rechnung, zwei Aufrufer. Der Backtest
desselben Gitters steht in `nautilus/backtest_grid.py` (siehe
`nautilus/README-live-node.md`), die Messung an der Vergangenheit; hier laeuft
es auf laufenden Kursen.

```powershell
scanner/.venv/Scripts/python.exe gitter/handeln.py --wachen    # Grenzen
scanner/.venv/Scripts/python.exe gitter/handeln.py --vorschau  # schreibt nichts
scanner/.venv/Scripts/python.exe gitter/handeln.py --papier    # ein Zyklus
scanner/.venv/Scripts/python.exe gitter/auswertung.py          # Bilanz
cd gitter; ../scanner/.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py"
```

**Die Grenzen entstehen EINMAL** aus dem ersten gesehenen Kurs (+/-20 %, 12
Stufen, Schritt 3,755 %) und werden danach nie verschoben — ein Gitter, das
seiner Spanne nachzieht, waere eine andere Strategie. Preise und Mengen werden
auf das Raster der Boerse gerundet (`tickSz`/`lotSz` aus dem Instrument), damit
das Papierbuch dieselben Zahlen benutzt, die eine echte Order haette.

**Die Kerzen-Regel** (jede Zahl dieser Spur haengt daran): je abgeschlossener
Stunde zuerst die Kaeufe (Tief beruehrt die Stufe), dann die Verkaeufe (Hoch
beruehrt die Stufe hoeher) — aber nur fuer Lose, die schon VOR dieser Kerze
lagen; am Ende der Kerze wird neu armiert (freie Stufen unter dem Schlusskurs).
Die laufende Stunde wird verworfen. Damit erfindet der Durchlauf keinen Zyklus,
der in derselben Stunde begonnen und beendet worden waere; der Backtest rechnet
genauso (Order aus Kerze N wirkt ab Kerze N+1).

**Nachgezogen wird seit der letzten Kerze**, nicht nur die neueste: ein
ausgefallener Zyklus (oder ein Neustart) verliert nichts, solange die Luecke ins
Fenster passt (300 Kerzen = 12,5 Tage). Deshalb greift hier **Bedingung 3 nicht**
— ein Gitter hat keine Order am Markt, die unbewacht waere; es muss nichts
flachgestellt werden. Bedingung 4 laeuft: Journal und Zustand gehen nach jedem
Zyklus nach `Q:\Handel_Journal\gitter`, byte-genau geprueft von
`spiegelstand.py`.

Kosten auf beiden Seiten (0,1 % Gebuehr + 0,05 % Slippage je Seite = 0,3 % je
Runde) gegen 3,755 % Stufenabstand. Kill-Switch bei 200 USD (20 % des
Einsatzes): ab dort keine neuen Stufen, belegte Stufen verkaufen weiter.
`--live` verweigert mit einem Grund ohne das Wort Freigabefenster
(`handel_erlaubt=false`) — der Dauerlauf fragt deshalb keine Freigabe an.

Die belegten Stufen stehen als Positionen im Zustand (`inst`, `seite`,
`einstieg`, `menge`, `nominal`, `ziel`) — abgeleitet aus den Losen, nie von Hand
gefuellt; `ziel` ist die naechste Stufe, einen Stop gibt es nicht. Der
Tagesbericht zeigt darum "Verkauf in x %" statt eines Stop-Abstands.

## Handelszentrale (`handelszentrale.py`) — alle acht Spuren in einem Fenster

Seit 13.09.2026 gibt es die gemeinsame Ansicht ueber den ganzen Handel-Ordner:
dieselben vier Dinge, die die omnitrade-Oberflaeche (`omnitrade-ui`: Chart,
Orderbuch, Positionen, Konsole) fuer EINE Engine zeigt — hier Spuren, offene
Positionen, Kurschart und Konsole ueber ALLE Spuren (`xperp`, `scanner`,
`swap`, `spiegel`, `orbk`, `omniquant`, `nautilus`, `gitter`).

Aufruf aus diesem Ordner, mit dem Vorgabe-Interpreter der Spuren:

    scanner/.venv/Scripts/python.exe handelszentrale.py
    scanner/.venv/Scripts/python.exe handelszentrale.py --pruefen

`--pruefen` gibt ohne Fenster genau das aus, was das Fenster zeigen wuerde:
Spurzeilen, offene Positionen samt Kursweg und die letzten Buchungen. Das ist
der Nachweis, wenn kein Bildschirm da ist.

**Rein lesend.** Gelesen werden je Spur `zustand.json`, `wachen.json` und
`handelsjournal.csv`, dazu `dauerlauf.log`, `dauerlauf.pid` und
`freigabe_fenster.json`. Kurse und Kerzen holt die GUI in Hintergrund-Threads
(OKX ueber `scanner/okx`, Kraken ueber `kraken/kraken.py`, Token-Kurse ueber
`spiegel/lesen.py`) — das Netz blockiert die Oberflaeche nie, Refresh alle 15
Sekunden. Geschrieben wird NICHTS; der Dauerlauf bleibt der einzige Schreiber.
`tests/test_handelszentrale_rein_lesend.py` verbietet Schreibzugriffe per
AST-Pruefung und vergleicht Groesse/mtime aller Spurdateien vor und nach einem
vollen Leselauf.

**Welche Spuren erscheinen, entscheidet `dauerlauf.SPUREN`** — die Liste wird
importiert, nicht abgeschrieben. Eine zweite Spurliste in der GUI waere eine
zweite Wahrheit, die beim naechsten neuen Spurordner still auseinanderlaeuft.
Aus demselben Grund liefert `--pruefen` die Spurliste mit aus.

**Die Zustandsformen der Spuren sind verschieden**, und die Tabelle muss alle
kennen (sie werden gelesen, nicht erfunden):

| Feld | Varianten |
|---|---|
| Positionen | `positionen` (Liste) oder `position` (Einzelwert, ORB) |
| Richtung | `seite` oder `richtung` (ORB); fehlt sie ganz, gilt long |
| Einstieg | `einstieg` oder `preis_einstieg` (Spiegel) |
| Grenzen | `stop`/`ziel` oder `stop_preis`/`ziel_preis` (Spiegel) |
| Einsatz | `nominal`, `usd`, `einsatz_usd`, `eur` oder `menge × einstieg` |
| Name | `inst` oder `paar` oder `symbol (kette)` |

`tests/test_handelszentrale_bindung.py` haelt das fest: je Spur ein Fall in
ihrer echten Schreibweise, dazu eine Formpruefung gegen die echten Dateien —
die GUI darf keine Position verlieren, die in `zustand.json` steht. Genau
dieser Fehler waere sonst unsichtbar: der ORB-Zustand fuehrt seine eine
Position unter `position` und nennt die Richtung `richtung`; ohne diesen Griff
haette die zentrale Tabelle fuer diese Spur dauerhaft „0 Positionen“ gezeigt.

**Zwei Rechnungen sind richtungsbewusst** (wie `tagesbericht.zeile_position`):
G/V aus Kurs/Einstieg und der Abstand zum Stop. Bei short liegt der Stop
ueber dem Kurs — ohne Richtungsfaktor saehe jede gesunde short-Position aus wie
ein gerissener Stop. Negativ heisst: der Kurs hat den Stop durchlaufen.

**Der Kursweg haengt an der SPUR, nicht am Instrument:** `orbk` handelt auf
Kraken und fuehrt als `inst` nur den Schluessel `ETH_USD` — den Kraken-Paarnamen
traegt der Instrumentenblock in `wachen.json`. Die Spiegel-Spur hat keine
Boersenkerzen; dort steht der Grund in der Chartflaeche statt eines leeren
Bildes.

**Drei Befunde vom 13.09.2026**, die im Code als Kommentar stehen:

1. **Das Dauerlauf-Log traegt lokale Zeit ohne Jahr** (`13.09. 18:25:44`).
   Gegen UTC gerechnet stand in der Kopfzeile „letzter Zyklus vor -120 min“,
   waehrend der Dienst lief. Der Vergleich laeuft jetzt in derselben Zone; ein
   Eintrag, der mehr als einen Tag in der Zukunft liegt, gehoert zum Vorjahr.
   Ohne `strptime('%d.%m. ...')` — das Format ohne Jahr warnt seit Python 3.13.
2. **Nicht jedes Journal hat eine Uhrzeit.** Die ORB-Spur schreibt
   `2026-09-13`. Ein starres `zeit[11:16]` las dort eine leere Spalte; die
   Konsole zeigt fuer diese Form `13.09.`.
3. **Der eigene Modulname darf keinem Spurmodul gleichen.** Diese Datei hiess
   zuerst `gui.py` — genau wie `omniquant/gui.py`. Mit `Handel/` auf `sys.path`
   fing sie deren `import gui` ab, und fuenf Omniquant-Tests brachen mit
   `module 'gui' has no attribute 'fuss_texte'`. Sie waren nicht kaputt, sie
   liefen gegen das falsche Fenster. `NamensfalleTest` haelt den Handel-Kopf
   jetzt frei von doppelten Modulnamen.

**Tests des Fensters** (43 der 122 Tests in `Handel/tests`):

    scanner/.venv/Scripts/python.exe -m unittest discover -s tests -p "test_handelszentrale*.py"

Darunter ein echter Fensteraufbau (`FensterAufbauTest`): ein tk-Mock verdeckt
genau die zwei Fehler, die nur beim echten Start auftreten (fehlendes
`from tkinter import ttk`, ein `root` in einer Builder-Methode, die nur
`self.root` kennt). Deshalb wird das Fenster wirklich gebaut, einmal gezeichnet
und wieder geschlossen.

## Handelsagenten und Auswertungs-Aufgaben (Kopien, 11.10.2026)

Lesekopien zur Pruefung (Originale: `~/.claude/agents/handels-*.md` und `~/.claude/scheduled-tasks/*/SKILL.md`):
`agenten/` = Handelskette scanner -> pruefer -> disponent, `aufgaben/` = die zwei Omnitrade-Auswertungen mit Telegram-Meldung.
Vor Aenderungen immer das Original anpassen; diese Kopien dann nachziehen.

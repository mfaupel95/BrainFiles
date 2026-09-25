---
name: okx-bots-bewachen
description: "Use when OKX-Bots bewacht, gestoppt, dimensioniert werden."
version: 0.1.0
author: Hermes
license: MIT
category: brainfiles
platforms: [windows]
metadata:
  hermes:
    tags: [OKX, Handel, Bots, DCA, Grid, Waechter]
    related_skills: [handel-spuren, okx-trading-schleifen, dauerprozess-bewachen, okx-orderweg-diagnose]
---

# Boersenseitige OKX-Bots: bewachen, stoppen, dimensionieren

Gilt fuer Bots, die BEI OKX laufen (`/api/v5/tradingBot/...`): Future-DCA,
Future-Grid, Spot-DCA, Recurring. Das sind NICHT die Haus-Spuren — hier fuehrt die
Boerse Leiter und Position, der Agent liest und greift hoechstens ein.
Werkzeug: `Agenten/Handel/okx_bot_waechter/` (`waechter.py` Bericht, `analyse.py`
Dimensionierung, `vorschlag.py` neuer Plan, `bauen.py` anlegen, `anpassen.py`
einen LAUFENDEN Bot umstellen).

## When to Use

- „Bot laeuft aus seiner letzten Kaufgrenze“, „wie tief kauft der noch nach“
- „neuen DCA/Grid aufsetzen“, „Nachkauf-Barrieren besser einrichten“
- ein laufender Bot soll gestoppt oder geaendert werden
- „warum war dieser Bot so erfolgreich“, „was ist das Schema dahinter“ —
  geschlossene Bots auswerten (eigener Abschnitt unten)

## Die Kernregel: Leiter in ATR-Einheiten, nicht in Prozent

Eine DCA-Leiter ist nur so gut wie ihre TIEFE. Der gemessene Regelfehler:
Leitern 4-8 % tief bei Instrumenten mit 8-13 % Tagesrange — nach ein bis zwei
Tagen ist die Munition weg, danach kauft der Bot nicht mehr nach und die Position
laeuft ohne Stop in die Liquidation. Deshalb fuer jeden NEUEN Bot:

- **Tiefe** = `max(3 x ATR14(Tag), groesster Rueckgang in 90/180/365 Tagen, 10 %)`,
  gedeckelt bei 60 %. Ohne Kerzen gilt der feste Rueckfallwert — und der Plan
  sagt, dass er geraten ist.
- **Abstand je Stufe** = 0,15-0,5 x ATR, **nie unter 2,5 %** (darunter verbraucht
  die Leiter sich an Rauschen) und nie ueber 5 %.
- **Hebel** so, dass die Liquidation mindestens 5 % UNTER dem Planboden liegt.
- **Barriere**: der Planboden soll unter dem 90-Tage-Tief liegen — liegt er
  darueber, wird das GEMELDET, nicht verschwiegen.
- **Ein Stop gehoert dazu**: die tiefste Stufe ist der Stop (DCA `slPct`), beim
  Grid eine Preis-Schwelle (`slTriggerPx`). Die Schwelle wird GERECHNET, nicht
  auf die Netzkante gelegt: `Kurs - 1,5 x ATR14(Tag)`, nach oben begrenzt auf
  `0,99 x minPx` (ein Stop IM Band toetet das Gitter bei normalem Lauf) und nach
  unten begrenzt auf `1,15 x liqPx` (naeher an der Liquidation schuetzt nichts
  mehr). Bei einem Instrument mit 8-9 % Tagesrange liegt die untere Netzkante
  oft nur ~0,5 ATR entfernt - ein Stop dort feuert am Rauschen, nicht am
  Bruch. Am lebenden Beispiel gerechnet: Kurs 1552, ATR 132, Bandboden 1480,
  Liquidation 1111 -> Stop 1354.

**Engpass ist die STUFENZAHL, nicht die Tiefe.** 12 Stufen bei 2,5 % Abstand
decken nur 30 % — fuer 3 x ATR braucht es oft 20 und mehr Stufen. Die Analyse
nennt die noetige Zahl als Warnung; wer sie still auf 12 kappt, baut wieder eine
zu flache Leiter.

## Geschlossene Bots auswerten: ein Grid ist ein gehebelter Long

Wer fragt „warum war dieser Bot so erfolgreich“, will das SCHEMA, nicht die
Kennzahl. Der Bericht des Waechters enthaelt nur LAUFENDE Bots — geschlossene
kommen ueber die Historie (Endpunkte und Feldnamen: `references/okx-bot-api.md`).

Ein Grid-Bot ist kein marktneutrales Geschaeft: innerhalb des Bandes handelt er
(Netzgewinn), ausserhalb liegt die Position voll und macht die Richtungsbewegung
mit Hebel mit. Zwei Wege zum Gewinn, **ein** Weg zum grossen Verlust.

- `totalPnl = gridProfit + floatProfit`. Die Gebuehren NICHT ein zweites Mal
  abziehen — `fee`/`fundingFee` sind Ausweisposten und in den beiden Summanden
  bereits enthalten.
- Die **Marktrichtung waehrend der Lebensdauer** trennt Gewinner von Verlierern;
  Hebel, Netzzahl und Bandbreite trennen NICHT. Ohne diese Messung ist jede
  Aussage ueber „gute Parameter“ geraten.
- Die Laufzeit ist kurz (Groessenordnung ein Tag): ein „erfolgreicher“ Bot ist
  meist ein Lauf, der IM PLUS gestoppt wurde, nicht ein Netz, das lange geerntet
  hat. Nachsehen, WER gestoppt hat (`triggerParams[-1].triggerType`, `manual`
  oder `auto`) — das entscheidet, ob es die Mechanik war oder ein Griff.
- Zwei Vorzeige-Bots koennen ZWEI verschiedene Mechanismen sein (Richtungstreffer
  mit Hebel gegen echte Oszillation im Band). Jeden einzeln nachrechnen, nicht
  aus einem den anderen erklaeren.
- Der groesste Einzelverlust einer Serie ist regelmaessig ein Bot OHNE Stop, der
  lief, waehrend der Markt gegen die Position ging — `slTriggerPx` je Bot LESEN,
  auch bei geschlossenen.

Reihenfolge je Auswertung: (1) Historie und Detailantwort je Kennung holen,
(2) Kursbewegung waehrend der Lebensdauer aus 1H-Kerzen ueber
`market/history-candles` seitenweise rueckwaerts, (3) je Bot Seite, Laufzeit,
Netzgewinn, Richtungsgewinn, Stop und die Bewegung in Richtung der Position
nebeneinander stellen, (4) ERST DANN gruppieren (mit/gegen die Richtung) und
Mittel vergleichen, (5) Ergebnis als Wiki-Seite und offene Punkte nach
`Archiv/TASKS.md`.

## Ablauf

1. **Ist-Lage messen** (rein lesend): `waechter.py` gibt je Bot den Zustand
   OK/KNAPP/AUSGELAUFEN/NOTFALL/WARNUNG — nur fuer LAUFENDE Bots. Die **letzte kaufbare Grenze zweimal**
   bestimmen — tiefste Kauforder aus `dca/orders?algoId=...` UND die Planrechnung
   `initPx x (1 - maxSafetyOrds x pxSteps)`. Weichen beide ab, ist die Orderliste
   die Wahrheit. Munition = `maxSafetyOrds - fillSafetyOrds`.
2. **Je Bot die drei Zahlen nennen** (Grenze, Kurs, Munition) plus Abstand zur
   Liquidation und den eigenen G/V — „OK“ ohne Zahlen ist kein Befund.
3. **Dimensionieren**: `analyse.py` (mit `--woche` fuer den uebergeordneten Trend),
   dann `vorschlag.py --art dca --inst <instId> --budget <n> --tiefe auto`.
   Ein Grid-Vorschlag kann am OKX-Mindestinvestment scheitern — das ist eine
   Eigenschaft des Instruments, kein Defekt.
4. **Stoppen, umstellen oder bauen nur hinter zwei Toren** (siehe unten).
   Laufende SPOT-DCA sind umstellbar, laufende CONTRACT-DCA NICHT (eigener
   Abschnitt unten), neue bekommen die Regel aus Schritt 3 von Anfang an. Ob gestoppt, umgestellt oder ausgesessen
   wird, entscheidet der Nutzer — die Messung liefert nur die Zahlen dafuer.
5. **Wache als Hermes-Cron** (`no_agent`, leere Ausgabe = nichts senden), nur
   Standardbibliothek, Fachmodule per Pfad laden (`dauerprozess-bewachen`).
   Gemeldet wird jede LAGEAENDERUNG, derselbe Zustand hoechstens alle 6 h.
6. **Dokumentieren und sichern**: README-Abschnitt mit der Regel, Wiki-Seite,
   `.gitignore`-Freigabe fuer den Ordner (Zustands- und Protokolldateien bleiben
   draussen), `git check-ignore -v` als Gegenprobe, Commit nur eigene Pfade.

## Zwei Tore fuer jede echte Handlung

Ein Werkzeug, das echte Positionen bewegt, ist ein Werkzeug — kein Schalter:

- **Tor 1** in `wachen.json` (`stop_erlaubt`, `bauen_erlaubt`, ...), **Tor 2** das
  CLI-Flag `--anwenden`. Standard ist der Trockenlauf, der genau sagt, was er
  taete (`GESPERRT: <grund>`), und nichts tut. Beide Tore zu ist der Auslieferungs-
  zustand.
- **Je Objekt ausnehmbar**: `bots: {"<algoId>": {"scharf": false, "vermerk":
  "<Grund>"}}`. Eine Entscheidung des Nutzers („nicht stoppen, weil der
  Wochenchart aufwaerts ist“) MUSS als datierter Vermerk dort stehen — sonst
  kippt sie um, sobald spaeter jemand das globale Tor oeffnet.
- **Jede Handlung wird protokolliert** (JSONL je Handlung) und mit einer Zeile je
  Bot quittiert; der Bericht bleibt rein lesend.
- **Verweigern statt beschoenigen**: Boden ueber dem Kurs, Einsatz unter dem
  Mindestinvestment, unbekanntes Instrument — jeweils Sperre mit Begruendung,
  nie eine stillschweigend korrigierte Zahl.
- **Nie aus einem Zeitplan eingreifen.** Ein Cron darf melden, nicht stoppen; das
  gilt auch fuer den eigenen Waechter.

## Laufende Bots umstellen - nur SPOT-DCA nehmen einen Amend an

**Erst die Bot-Art aus der Detailantwort lesen, dann handeln.**
`POST /api/v5/tradingBot/dca/amend-order-algo` heisst in der OKX-Doku woertlich
„Amend **spot** dca basic param". Eine laufende CONTRACT-DCA
(`algoOrdType: contract_dca`, alle unsere Future-Bots) wird mit
`OKX 51291: The bot doesn't exist or has already stopped` abgewiesen — fuer jede
Kennung, mit vollstaendigem Koerper aus dem Ist-Zustand und mit korrektem
Schluessel. Die Meldung nennt den Bot, gemeint ist die BOT-ART: sie ist kein
Hinweis auf einen falschen Koerper, ein falsches Feld oder einen toten Bot.
Folge: `anpassen.py --sl-pct/--nur-schutz` kann an einer laufendenContract-DCA
nichts aendern, das Tor `anpassen_erlaubt` bleibt fuer sie wirkungslos.

Was an einer laufenden CONTRACT-DCA erreichbar ist:

- `dca/margin/add` — Liquidation nach unten druecken,
- `dca/orders/manual-buy` — von Hand in den laufenden Zyklus kaufen,
- `dca/stop` (`stopType 1` schliesst die Positionen am Markt) — das EINZIGE
  Schutzmittel einer laufenden Contract-DCA; Tor ist `stop_erlaubt`.

**Ein Stop auf die POSITION ersetzt den Bot-Stop nicht.** Fuer diese Bots
liefert `/api/v5/account/positions` **null Eintraege** (auch mit
`instType=FUTURES`/`SWAP`); mit dem Bot-Instrument gefragt kommt eine Zeile mit
`pos=0`. Die Marge liegt im Bot, nicht im Konto — es gibt keine Position, die
eine bedingte `reduceOnly`-Order absichern koennte (Werkzeug und Befund:
`okx_bot_waechter/positions_schutz.py`).

### Fuer die SPOT-DCA, bei der der Amend greift

Der Amend schreibt die ganze Leiter plus Stop und Ziel neu; die Werte gelten
sofort UND fuer den naechsten Zyklus (die Parameter haengen am Bot, nicht am
Zyklus).

- **Nichts erfinden.** Der Koerper verlangt ALLE Felder — jedes aus dem
  Ist-Zustand nehmen, `tpPct` notfalls aus `tpPx / avgPx` herleiten (nicht mit
  einem runden Wert annehmen). Ohne ausdrueckliche Wahl (`--stufen`, `--schritt`,
  `--sl-pct`, `--nur-schutz`) sendet `--anwenden` gar nichts; Tor ist
  `anpassen_erlaubt`.
- **`slPct` ist ein ANTEIL des Einstands**, nicht ein Preis:
  `slPct = 1 - stop / avgPx` (0.1254 = 12,54 % unter `avgPx`). Den Stop-Preis
  zuerst rechnen, dann umrechnen — nicht umgekehrt. Hausregel fuer den Preis:
  5 % UNTER die tiefste Kaufstufe (die Leiter muss fuellen koennen), bei schon
  ausgelaufener Leiter (Kurs unter dem Boden) 1,5 % unter den Kurs als
  Reissleine, in jedem Fall mindestens 2 % ueber `liqPx`; liegt der Stop danach
  ueber dem Kurs, ist er sofort faellig und gehoert so benannt.
- **Zwei Grenzen mitnennen, sonst ist die Umstellung Kosmetik**: (a) neue Stufen
  brauchen FREIES Guthaben — Bedarf (`zusaetzliche Stufen x safetyOrdAmt`) gegen
  den freien Bestand stellen und beides nennen, (b) bei einer voll gefuellten
  Position ist die LIQUIDATION die Wand, nicht die Leiter: liegt der Planboden
  unter `liqPx`, erreicht der Bot die tiefsten Stufen nie.
- **Die Wand rechnen statt schaetzen**: `Abstand(Einstand -> Liquidation) =
  Margin/Notional + Rest`; Margin und Notional kommen aus dem Bot, der Abstand
  aus `liqPx` — der Rest ist damit GEMESSEN, daraus folgt der Margin-Bedarf
  `(Zielabstand - Abstand) x Notional`. Erst diese Zahl macht die Antwort
  vollstaendig: „Leiter tiefer legen“ kostet bei einer gefuellten Position Geld.
- Was ein Amend nicht kann: die bereits gefuellte Position aendern.

## Einem laufenden GRID einen Stop setzen (`grid_schutz.py`)

Ein Grid kennt kein `slPct` - es kennt eine PREIS-Schwelle. `anpassen.py` deckt
nur DCA ab; fuer Grids gibt es `okx_bot_waechter/grid_schutz.py` (Trockenlauf
ohne `--anwenden`, `--preis` fuer eine Handentscheidung, `--nur <algoId>`).

- **Der Endpunkt ist `/api/v5/tradingBot/grid/amend-order-algo`** - das
  naheliegende `/grid/amend-algo` antwortet `HTTP 404 Not Found`. Koerper:
  `{algoId, instId, slTriggerPx, slOrdPx: "-1"}` (`-1` = Ausstieg am Markt).
  Vorher mit einer erfundenen `algoId` proben: `OKX 51291: The bot doesn't exist
  or has already stopped` beweist Endpunkt, Signatur und Host, ohne etwas zu
  beruehren.
- **Der Schutz-Stop ist der GEGENWEG einer Leiteraenderung** und haengt deshalb
  nicht an `anpassen_erlaubt`: er senkt das Risiko. Umgekehrt gilt weiter, dass
  ein Amend die bereits gefuellte Position NICHT aendert - Band und Netzzahl
  bleiben, nur die Schwelle kommt dazu.
- **Nach dem Amend LESEN, nicht glauben:** `sCode: "0"` und danach
  `grid_details()` nachziehen (`slTriggerPx` gefuellt, `state: running`,
  `minPx`/`maxPx`/`gridNum` unveraendert). `slOrdPx` erscheint in der
  Detailantwort als `None`, obwohl der Ausstieg greift - nicht als Fehler lesen.
- **Die Entscheidung datiert in `wachen.json`** (`bots.<algoId>.vermerk`), sonst
  kippt sie beim naechsten Griff. Ein Stop, den niemand mehr erklaeren kann,
  wird beim naechsten Aufraeumen entfernt.

## Pitfalls

- **GET-Parameter gehoeren in den PFAD.** Der gemeinsame `_roh`-Helfer der
  okx-Module schickt `body` als Request-Body (fuer POST) — bei GET landet nichts
  davon in der Abfrage. Endpunkte und Felder: `references/okx-bot-api.md`.
- **`/public/instruments` verlangt `instType`** („Parameter instType can not be
  empty“). Aus der Kennung ableiten (`<Basis>-USD_UM_XPERP-<n>` -> `SWAP`), nicht
  raten.
- **Verschiedene Formen je Endpunkt**: `grid/stop-order-algo` nimmt eine LISTE,
  `dca/stop` ein OBJEKT, `stopType 1` schliesst die Positionen am Markt.
- **Kontraktkerzen sind fuer den uebergeordneten Trend zu kurz** (7-26
  Wochenkerzen bei jungen XPERP-Kontrakten). Den Trend am SPOT-Paar messen
  (`UNI-USDT`), sonst ist jede Trendaussage geraten.
- **Nicht annehmen, dass ein Stop existiert.** Bei OKX-DCA ist „kein Stop“ der
  Normalfall: `slPx`/`slTriggerPx` je Bot LESEN und fehlend melden.
- **Bot-Kennung und Positions-Kennung sind nicht dieselbe Zeichenkette.** Der
  Bot traegt eine Lieferkennung (`LTC-USD_UM_XPERP-310404`), die Position nicht
  (`LTC-USD_UM_XPERP`). `/account/positions?instId=<ohne Suffix>` antwortet
  `OKX 51001: Instrument ID ... doesn't exist` — das ist ein Suchfehler, kein
  fehlendes Instrument; mit dem Bot-Namen kommt eine Zeile (ggf. `pos=0`).
- **Hebel und Stufen sind gekoppelt** (`liqPx`). Ein zu hoher Hebel macht die
  letzte Stufe unerreichbar, weil die Liquidation davor liegt.
- **Ein Kurs unter dem Planboden heisst nicht „fertig“**, sondern „der Bot kann
  nicht mehr nachkaufen“ — genau die Lage, die den Stop ersetzt.
- **Schreibwege gefahrlos pruefen, VOR dem ersten echten Aufruf.** Einen
  POST-Endpunkt mit einer Kennung aufrufen, die es nicht gibt (`algoId "1"`):
  ein Fachfehler („The bot doesn't exist or has already stopped“) beweist
  Endpunkt, Signatur und Host, ohne ein Objekt zu beruehren; ein GET auf
  denselben Pfad antwortet „Operation not supported“ (falscher Weg). Als
  widerlegt gilt: „unbekannter Endpunkt“ haette anders geantwortet.
- **Der Residualterm heisst nicht Wartungsrate.** In `Abstand = Margin/Notional +
  Rest` steckt mehr als die Wartungsrate (einrealisierte Gewinne, die als Puffer
  auf der Position liegen) — als Rest MESSEN und so benennen. Ist er gross, liegt
  mehr Margin auf der Position als die Leiterbetraege hergeben; das gehoert in
  den Bericht, weil es die Rechnung sonst verschoenert.
- **Kerzenzeilen sind LISTEN** `[ts, o, h, l, c, v]`, keine Dicts. Ein
  Dict-Fixture im Test faellt als `KeyError: 2` aus, obwohl der Code richtig ist —
  erst pruefen, in welcher Form der Datenzugriff die Kerzen liefert.
- **Tests ohne Netz**: `main()` laedt seine eigene Konfiguration, ein im Test
  uebergebenes Dict wird ignoriert — den LADER patchen (`lade_wachen`).
  Attrappen als MODULkonstanten anlegen (ein Klassenattribut, das eine Klasse im
  eigenen Koerper benutzt, ist ein NameError) und einen Modulwaechter einbauen,
  der Dateiliste und Groessen des echten Ordners vor/nach vergleicht.
- **Ein leeres Feld ist keine Null.** In der LISTEN-Antwort der Historie stehen
  `floatProfit`, `runPx` und `tradeNum` leer, in der DETAILANTWORT derselben
  Kennung gefuellt. Wer das leere Feld als 0,00 liest, rechnet einen Anteil von
  0 % aus und begruendet damit die falsche These. Vor jeder Aussage „X ist null“
  die Detailantwort ziehen.
- **`algoId` und `algoOrdType` gehoeren zusammen.** `dca/position-details` auf
  eine Grid-Kennung antwortet `OKX 50016: algoId and algoOrdType don't match` —
  der billigste Weg, eine unbekannte Kennung einer Bot-Art zuzuordnen, statt zu
  raten.
- **1H-Kerzen reichen nur rund zwoelf Tage zurueck** (`market/candles`) und
  liefern fuer aeltere Bots still das FALSCHE Fenster. Fuer die Lebensdauer
  eines Bots `market/history-candles` seitenweise rueckwaerts blaettern
  (`after=<ts_ms>&limit=100`, bis der aelteste Punkt unter dem Start liegt) —
  und niemals still auf „die letzten n Kerzen“ zurueckfallen, das liefert
  plausible Zahlen zum falschen Zeitraum.

## Verification

```bash
cd Agenten/Handel/okx_bot_waechter
MAXHIRN_ROUTINE=1 ../scanner/.venv/Scripts/python.exe waechter.py            # Bericht
MAXHIRN_ROUTINE=1 ../scanner/.venv/Scripts/python.exe analyse.py --woche    # Trend + Regel
MAXHIRN_ROUTINE=1 ../scanner/.venv/Scripts/python.exe vorschlag.py --art dca \
  --inst UNI-USD_UM_XPERP-310718 --budget 100 --tiefe auto
cd tests && MAXHIRN_ROUTINE=1 ../../scanner/.venv/Scripts/python.exe -m unittest discover -s . -t .
```

Fertig ist eine Aenderung erst, wenn (a) die Testsuite gruen ist, (b) der
Trockenlauf des Werkzeugs genau das sagt, was der Handlauf taete, (c) ein frisch
angelegter Cron per Job-Satz (`last_run_at`, `last_status`) UND Ausgabedatei
belegt ist — und (d) die gehandelten Objekte unveraendert sind (kein Bot
gestoppt, keine Order), wenn keine Freigabe erteilt wurde.

## Abgrenzung

- Haus-Spuren und ihre Buecher: `handel-spuren`
- Rein lesende OKX-Berichts-/Wachen-Crons: `okx-trading-schleifen`
- Fehlercodes einer Order deuten: `okx-orderweg-diagnose`
- Cron-Bauart und Watchdog-Muster: `dauerprozess-bewachen`

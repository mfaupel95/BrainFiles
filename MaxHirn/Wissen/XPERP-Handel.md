---
id: 20260901-xperp-handel
title: 'XPERP-Handel auf OKX'
tags: [handel]
created: 2026-09-01
updated: 2026-09-08
related: [20260901-saisonalitaet-signal, 20260902-handelsregeln, 20260908-volumen-drift-signal]
summary: 'Wo die gehebelten OKX-Perpetuals liegen, welche Werte 5x tragen, warum der Hebel aus dem Stop fällt statt umgekehrt — und seit 03.09.2026 die 45 Aktien und 4 Rohstoffe samt Ruhekerzen-Filter.'
---

# XPERP-Handel auf OKX

Was beim Bau des Bots unter `Agenten/Handel/xperp/` herauskam. Der Anlass war
die Frage nach „REUSD XPERP long 5x Hebel"; die Hälfte der Arbeit war,
herauszufinden, **was dieses Instrument überhaupt ist**.

**Warum:** Die Instrumentensuche hat allein eine halbe Stunde gekostet, weil
der Name in keiner Suche auftaucht. Und die Hebelrechnung dreht die übliche
Reihenfolge um — ohne diese Notiz wird beim nächsten Bot wieder ein
Prozent-Stop gesetzt, der bei 2,9 % ATR reines Rauschen ist.

**Stand:** 2026-09-01

## Das Instrument findet man nur, wenn man den Bindestrich kennt

„REUSD" existiert nicht. Der Kontrakt heißt **`RE-USD_UM_XPERP-310620`** —
gelesen ergibt „RE-USD" eben „REUSD". Drei Fallen auf einmal:

| Falle | Wirkung |
|---|---|
| XPERP liegen unter **`instType=FUTURES`**, nicht `SWAP` | Wer bei den Swaps sucht, findet null Treffer |
| Sie tragen ein **Ablaufdatum** (RE: 2031) | Heißen trotzdem Perpetual |
| `instCategory` trennt die Familien | **1 = Krypto (111), 3 = Aktien (46), 4 = Rohstoffe (4)** |

`okxf.instrument()` nimmt deshalb `RE`, `REUSD` und den vollen `instId`.

## Aktien und Rohstoffe lagen die ganze Zeit hinter demselben Schlüssel

**Ergänzt am 03.09.2026.** Die Zeile über `instCategory` stand seit dem
01.09.2026 in dieser Notiz — als Randbemerkung. Sie war der ganze Zugang: Am
03.09.2026 fragte Max nach Aktien und Futures und vermutete sie bei Kraken,
weil dort die Gebühren höher sind und sich kurze Runden nicht lohnen. Die
Messung drehte das um:

| | Kraken Spot | OKX-XPERP |
|---|---|---|
| Aktien im Angebot | **keine** — 1440 Paare, kein AAPL/TSLA/SPY | **45** |
| Rohstoffe | keine | 4 (XAU, XAG, CL, BZ) |
| Gebühr je Runde | 0,80 % | 0,10 % |

Aktien auf Kraken gäbe es nur über Kraken Futures — andere Plattform, anderer
Schlüssel, andere Signatur. Auf OKX kostete es einen Parameter: `okxf`
kannte die Familien längst, `auswahl.py` stand nur fest auf `KRYPTO`.

**Ein Tor, das an Krypto gemessen wurde, misst bei einer Aktie das Falsche.**
Deshalb je Familie eigene Werte in `xperp/wachen.json`:

| | Krypto | Aktie | Rohstoff |
|---|---|---|---|
| Vola-Tor p.a. | 120 % | 90 % | 60 % |
| Umsatz-Bezug | 3 Mio | 1 Mio | 1 Mio |

Der gesenkte Umsatz-Bezug ist keine Aufweichung, sondern eine Korrektur am
Maßstab: **Der Umsatz war hier nie das Risiko, der Spread ist es.** Gemessen
am 03.09.2026 — SPY 0,001 %, MSTR 0,036 %, NVDA 0,066 %, also rund ein Zehntel
des Krypto-Werts bei 0,3–2,8 Mio Umsatz. Eine Position von 250 USD steht damit
gegen 0,025 % des Tagesumsatzes.

Der Ertrag steht in einer Spalte, die im Krypto-Universum fast leer bleibt —
dem **Hebel-Deckel**: MSTR 6,8x, CRCL 6,2x, NVDA 8,4x, XAU 9,7x, während fast
jeder Krypto-Wert unter 5x liegt und den Marker `!hebel<5` trägt. Alle vier
Rohstoffe bestanden am 03.09.2026 jedes Tor ohne einen einzigen Warnmarker.

### Sie laufen 24/7, ihre Basiswerte nicht

Die Falle dieser Familien, und sie ist nicht offensichtlich. Gemessen über 500
Stundenkerzen, mittlere Spanne je Stunde:

| Wert | Mo–Fr | Sa–So | Faktor |
|---|---|---|---|
| NVDA | 0,45 % | 0,07 % | **0,16** |
| SPY | 0,09 % | 0,02 % | 0,23 |
| Gold | 0,39 % | 0,08 % | 0,21 |
| WTI | 0,62 % | 0,22 % | 0,36 |
| BTC | 0,70 % | 0,38 % | 0,54 |

**144 von 500 Stunden sind bei Aktien praktisch Stillstand.** Fließen sie in
die ATR ein, wird der Pflicht-Stop zu eng und greift Montag früh, ohne dass
der Markt etwas getan hat — derselbe Fehler wie beim Prozent-Stop oben, nur
eine Ebene tiefer.

`auswahl.py` lässt deshalb Kerzen aus ATR und Vola heraus, deren True Range
unter einem Viertel der Median-Spanne liegt (`ruhe_anteil`). **Kein
Feiertagskalender**, und der Filter regelt sich selbst — gemessen an
4H-Kerzen:

| SOL | BTC | CL | MSTR | SPY | NVDA | XAU |
|---|---|---|---|---|---|---|
| 0 % | 4 % | 6 % | 8 % | 13 % | 14 % | 16 % |

SOL mit 0 % ist der Beweis, dass er bei echtem 24/7 nichts tut. Nebenbefund:
Er markiert auch tote Krypto-Werte — RAVE kam mit 39 % Ruhekerzen und
0,0 Mio Umsatz.

**Was er nicht löst:** Der XPERP driftet am Wochenende kaum, der Basiswert
öffnet Montag trotzdem dort, wo die Nachrichten ihn hinstellen. Ein Stop, der
Sonntag sicher aussieht, liegt Montag hinter dem Gap — bei Hebel ist das der
Liquidationsfall. Dagegen hilft kein Filter, nur Zurückhaltung: ab
`freitag_stopp_utc` keine neuen Anläufe dieser Familien, und `wochenend_faktor`
gegen den Rahmen.

## Der Hebel ist Ergebnis, nicht Eingabe

Die tragende Regel, die den Bot von einem „5x-Bot" unterscheidet:

```
Stop-Abstand   = 1,5 x ATR
Positionswert  = Risikobetrag / Stop-Abstand
Margin         = Positionswert / Hebel
```

Der Hebel fällt hinten heraus und wird nur noch **gedeckelt**. Das ist
dieselbe Regel, die in `Handel/README.md` schon aus dem Titelvergleich kam:
Die Hebelhöhe gehört an die gemessene Volatilität gekoppelt, nicht an eine
Kurserwartung.

**Warum ein Prozent-Stop nicht geht:** RE hat **2,90 % ATR je 4h-Kerze**, SOL
**1,82 %**. Ein fester Stop bei −2 % liegt bei RE *innerhalb* des normalen
Zappelns und wird getroffen, ohne dass der Markt etwas getan hat. Denselben
Wert für beide zu nehmen, ist bei einem 5×-Hebel der Unterschied zwischen
„mehrere Anläufe" und „mehrere Totalverluste".

### Der Hebel-Deckel

```
Hebel_max = 1 / (größter 7-Tage-Rücklauf + Wartungsmarge)
```

Rückblick, keine Zusage — aber ein Hebel, der die letzte Woche nicht
überstanden hätte, braucht über die nächste nicht diskutiert zu werden.
Gerechnet von `bot.hebel_deckel()`, gemeldet in jeder Rangliste.

### Beim Grid kommt ein zweiter Deckel dazu

```
Hebel_max = 1 / (Spannentiefe + Wartungsmarge + Puffer)
```

Bei 11 % Rastertiefe sind das 6,9×, bei 17 % nur noch 4,8×. Der Grund steht
in `Handel/README.md`: *Ein Grid braucht Tiefe zum Nachkaufen, ein Hebel
verbietet Tiefe.* Die oberste Stufe hat den weitesten Weg zum Rasterboden;
überlebt sie ihn nicht, sterben die oberen Stufen, bevor die unteren kaufen.

## Gemessen am 01.09.2026

Erzeugt mit `Agenten/Handel/xperp/auswahl.py` (4h-Kerzen, 103 Krypto-XPERP,
davon 77 mit ≥ 21 Tagen Historie bewertbar).

**Das Universum ist dünn.** Außer BTC (170 Mio) erreicht kaum ein XPERP
nennenswerten Tagesumsatz — RE liegt bei **0,9 Mio USD**.

Werte, die nach der **korrigierten** Messung (200 Tageskerzen) durch die
Tore kommen (Vola < 120 %, Umsatz ≥ 3 Mio, Hebel-Deckel ≥ 5):

| Wert | Vola p.a. | ER | Hebel-Deckel | Umsatz 24h |
|---|---|---|---|---|
| **SOL** | 48 % | 0,10 | 3,6× | 21,8 Mio |
| **HYPE** | 77 % | 0,04 | 4,1× | 13,7 Mio |
| **ZEC** | 95 % | 0,15 | 1,7× | 12,1 Mio |

**Damit besteht keiner der drei das Hebel-Tor (≥ 5) mehr.** Die frühere Fassung
dieser Tabelle nannte SOL 10,0×, HYPE 6,4× und ZEC 5,8× und leitete daraus ab,
alle drei hätten „alle Tore bestanden" — beides ist zurückgenommen.

**Falle für die nächste Sitzung — der Messfehler, der das verursacht hat:**
`auswahl.py` leitete den Deckel aus **300 4H-Kerzen** ab. Das sind nur
**50 Tage**, und SOLs Rücklauf vom 31.05.2026 lag außerhalb dieses Fensters.
Der Code ist behoben — `mae_tage()` rechnet jetzt auf **300 Tageskerzen**
(committet), die Notiz war es nicht. Wer den Deckel nachrechnet, muss auf
**Tageskerzen** rechnen, nicht auf dem 300-Kerzen-Fenster des gehandelten
Kontrakts; sonst kommt wieder eine zu kleine Zahl heraus.

**RE selbst fällt durch zwei Tore:** Vola 173 %, Umsatz 0,9 Mio, Hebel-Deckel
**2,5×** long und 1,2× short. Die Grid-Eignung stimmt allerdings — ER 0,22 bei
69 % zurückgelegtem Weg in sieben Tagen ist echtes Gezappel. Nur der Hebel
trägt nicht.

**Für Short gab es keinen brauchbaren Kandidaten.** Jeder Wert mit echtem
Abwärtstrend fiel durch das Vola-Tor (GRVT 192 %, NES 135 %), den Hebel-Deckel
(JTO 3,8×) oder die Liquidität (POL 0,5 Mio). Das ist ein Befund, kein
fehlendes Werkzeug.

### Saisonalität greift ins Signal — hoch gewichtet, auf Anweisung

Seit 01.09.2026 rechnet `indikatoren.saisonalitaet()` eine Kalenderstatistik
(Nachbau des Closed-Source-Indikators „xGhozt Prophecies") und darf in
`lage()` die Richtung setzen oder gegen SuperTrend+EMA kippen. Die Stichprobe
ist dünn (~7 Kerzen je Wochentag auf 50 Tagen), deshalb nennt jede Ausgabe
`n`. Eigene Notiz mit Begründung: [[Saisonalitaet-Signal]].

### Volumen-Drift-Momentum greift ins Signal — hoch gewichtet, mit Vorrang

Seit 08.09.2026 rechnet `indikatoren.volumen_drift()` eine volumengewichtete,
ATR-normierte Preisdrift mit Mehrfach-Zeitebenen-Bestätigung (Nachbau des
Prinzips von „Swift Algo X", TradingView, Invite-Only) und darf in `lage()`
ebenfalls die Richtung setzen oder kippen — geprüft nach der Saisonalität und
bei Widerspruch zu ihr vorrangig. Eigenständige TradingView-Fassung unter
`Werkstatt/Ausgabe/2026-09-08_Volumen-Drift-Momentum.pine`. Eigene Notiz mit
Begründung und Vorrangregel: [[Volumen-Drift-Signal]].

### Die Kennzahl für Grid-Eignung heißt Efficiency Ratio

Kaufman: **Nettobewegung / zurückgelegter Weg**, über 7 Tage. Nahe 1 =
sauberer Trend, nahe 0 = Gezappel. Das ist messbar; „sieht seitwärts aus" ist
es nicht — und der Augenschein täuscht: RE *sah* seitwärts aus und lief in
sieben Tagen −13 %.

## Die gefährlichste Zahl ist eine hohe Trefferquote

Die Prüfpflicht (`bot.pruefpflicht()`) meldete für das SOL-Grid **99,6 %
beobachtete gegen 86,4 % nötige Trefferquote**. Sieht nach klarem Vorsprung
aus. Dahinter: **237 Ziele gegen einen einzigen Stop.**

Das Verlustereignis ist damit nicht gemessen, sondern nicht vorgekommen. Genau
das Muster beschreibt [[Handelsbots]]: enges Ziel, weiter Stop, hohe Quote —
und der eine Stop kostet mehr, als die vielen Treffer einbrachten. Bei 2,01 %
Ziel gegen 12,15 % Stop braucht es **sieben Treffer, um einen Stop zu
bezahlen.**

`bot.py` warnt deshalb, sobald die **seltenere** der beiden Seiten unter zehn
Ereignissen liegt. Beim Trend-Anlauf auf SOL (113 Ziel / 153 Stop) schweigt
er, dort sind beide Seiten besetzt.

**Regel daraus:** Eine Trefferquote ohne die Zahl der Gegenereignisse ist
keine Zahl. Immer beide Seiten mitangeben.

## Zwei Fehler, die im ersten Wurf drinstanden

- **`volCcy24h` enthält `ctVal` bereits.** Wer nochmal mit `ctVal`
  multipliziert, meldet BONK mit 167 Billionen USD Tagesumsatz und stellt die
  ganze Liquiditätsrangliste auf den Kopf. USD-Umsatz = `volCcy24h × Kurs`.
- **Eine fehlende Kennzahl als `0,0 %` zu drucken ist gefährlicher als eine
  Lücke.** DASH und POL standen oben in der Grid-Rangliste, weil ihre nicht
  existierende 14-Tage-Rendite als „+0,0 %" erschien und wie perfekte
  Seitwärtsbewegung aussah. Beide waren erst **acht Tage** alt. Fehlende Werte
  als `n/a` ausgeben, und eine Mindesthistorie erzwingen.

Dazu die beiden schon bekannten aus [[Handelsbots]], die weiter gelten: OKX
antwortet ohne User-Agent mit HTTP 403, und `ctVal`/`lotSz` bestimmen die
Position, nicht der Wunschbetrag.

## Nachrechnen

```powershell
cd Agenten\Handel\xperp
..\scanner\.venv\Scripts\python.exe auswahl.py               # alle drei Ranglisten
..\scanner\.venv\Scripts\python.exe auswahl.py --wert RE     # ein Wert im Detail
..\scanner\.venv\Scripts\python.exe bot.py lage  --wert SOL
..\scanner\.venv\Scripts\python.exe bot.py trend --wert SOL  # mit Prüfpflicht
..\scanner\.venv\Scripts\python.exe bot.py grid  --wert SOL
```

Die Grenzen stehen in `xperp/wachen.json` — die Datei, die [[Schutzregeln]]
T-017 für Spur 2 verlangt hat.

## Grenze

**Seit dem Abend des 01.09.2026 ist Hebel nicht mehr an eine Einzelanweisung
gebunden** — Max hat die Regel in [[Schutzregeln]] auf „automatisch erlaubt,
solange `wachen.json` eingehalten wird" umgestellt. Zwei Wege führen deshalb
in eine Position:

- **automatisch:** `bot.py` im Rahmen von `xperp/wachen.json`, ohne Rückfrage
  je Order. Die vier Zahlen der Prüfpflicht gehören dann ins Handelsjournal,
  nicht in den Chat.
- **auf Anweisung:** Max nennt Kontrakt, Richtung, Hebel, Einsatz und Stop
  ([[Schutzregeln]], Spur 2). Eine Rangliste aus `auswahl.py` bleibt auf diesem
  Weg ein Vorschlag, keine Anweisung.

`handel_erlaubt` steht auf `false` — **Papierbetrieb**. Den Live-Pfad selbst
gibt es seit dem 03.09.2026 (`xperp/handeln.py` mit Journal, Zustand, Ein- und
Ausstiegen; zusätzliche Grenzen in `xperp/wachen_xperp.py`), er schließt T-019:
bis dahin lief die Regel der Umsetzung voraus. Auf `true` erst, wenn der
Papierlauf die vier Werte aus `wachen.json` (`_freigabe`) erfüllt,
`journal_zweitziel` gesetzt ist und die OKX-Schlüssel stehen — und selbst dann
handelt ein Lauf nur scharf, wenn ein Freigabefenster offen ist. Der Schalter
wird von Hand auf `true` gelegt, nie aus einer Routine; zurück auf `false` darf
auch `wachen_xperp.py` (nur diese Richtung).

Verwandt: [[Handelsbots]], [[Marktscanner]], [[Schutzregeln]], [[Verbindungen]]

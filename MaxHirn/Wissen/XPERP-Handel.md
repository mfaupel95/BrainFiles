---
id: 20260901-xperp-handel
title: 'XPERP-Handel auf OKX'
tags: [handel]
created: 2026-09-01
updated: 2026-09-01
related: []
summary: 'Wo die gehebelten OKX-Perpetuals liegen, welche Werte 5x tragen und warum der Hebel aus dem Stop fällt statt umgekehrt.'
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

Werte, die **alle** Tore bestanden (Vola < 120 %, Umsatz ≥ 3 Mio,
Hebel-Deckel ≥ 5):

| Wert | Vola p.a. | ER | Hebel-Deckel | Umsatz 24h |
|---|---|---|---|---|
| **SOL** | 48 % | 0,10 | **10,0×** | 21,8 Mio |
| **HYPE** | 77 % | 0,04 | 6,4× | 13,7 Mio |
| **ZEC** | 95 % | 0,15 | 5,8× | 12,1 Mio |

**RE selbst fällt durch zwei Tore:** Vola 173 %, Umsatz 0,9 Mio, Hebel-Deckel
**2,5×** long und 1,2× short. Die Grid-Eignung stimmt allerdings — ER 0,22 bei
69 % zurückgelegtem Weg in sieben Tagen ist echtes Gezappel. Nur der Hebel
trägt nicht.

**Für Short gab es keinen brauchbaren Kandidaten.** Jeder Wert mit echtem
Abwärtstrend fiel durch das Vola-Tor (GRVT 192 %, NES 135 %), den Hebel-Deckel
(JTO 3,8×) oder die Liquidität (POL 0,5 Mio). Das ist ein Befund, kein
fehlendes Werkzeug.

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

Gehandelt wird gehebelt **nur auf ausdrückliche Anweisung** mit Kontrakt,
Richtung, Hebel, Einsatz und Stop ([[Schutzregeln]], Spur 2). Eine Rangliste
aus `auswahl.py` ist ein Vorschlag, keine Anweisung. Der Bot rechnet und legt
vor; abgesendet wird von Max.

Verwandt: [[Handelsbots]], [[Marktscanner]], [[Schutzregeln]], [[Verbindungen]]

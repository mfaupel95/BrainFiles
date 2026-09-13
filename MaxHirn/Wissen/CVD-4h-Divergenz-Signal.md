---
id: 20260913-cvd-divergenz-signal
title: 'CVD-4h-Divergenz im XPERP/SWAP-Signal'
tags: [handel]
created: 2026-09-13
updated: 2026-09-13
related:
  - id: 20260908-volumen-drift-signal
  - id: 20260913-buildix-santiment
  - id: 20260901-saisonalitaet-signal
  - id: 20260902-analyse-quellen
summary: 'Dritter hoch gewichteter Baustein im XPERP/SWAP-Signal: CVD (kumulierte Differenz aggressiver Kaeufe und Verkaeufe) aus dem OKX-Taker-Volumen in 4h-Eimern, als Divergenz gegen den Preis. Zeigt, woher die Zahlen kommen, warum das rohe Trade-Tape dafuer nicht traegt, wie die Rangfolge der drei hoch gewichteten Bausteine jetzt lautet und wie die Schwellen an der eigenen Verteilung kalibriert sind.'
---

# CVD-4h-Divergenz im XPERP/SWAP-Signal

Am 13.09.2026 gebaut, im Anschluss an die Ernte von [[Buildix-Santiment-Handelswissen]]:
buildix.trade fuehrt als Signal-Label genau diese Groesse (**CVD-4h-Divergenz**
→ STRONG BUY „accumulation near lows" / STRONG SELL „distribution near highs").
Sie ist aus Boersendaten nachbaubar, ohne den kostenpflichtigen Zugang.

- **Code:** `Agenten/Handel/xperp/cvd.py` (neu), Abruf in `okxf.taker_volumen()`,
  einghaengt in `indikatoren.lage()`, sichtbar in `bot.py lage`.
- **Tests:** `Agenten/Handel/xperp/test_cvd.py` (22 Faelle, kein Netzzugriff).

## Was gerechnet wird

CVD ist die laufende Summe aus aggressivem Kauf- minus Verkaufsvolumen, hier in
4h-Eimern. **Divergenz** heisst: der Preis macht ein Extrem, das Delta bestaetigt
es nicht (Rally ohne CVD = schwach; Verkauf ohne CVD = Boden). Das Fenster sind
**12 Eimer = 48 h**, halbiert:

| Groesse | Rechnung |
|---|---|
| `d_preis` | Mittel der juengeren Fensterhaelfte minus Mittel der aelteren |
| `d_cvd` | mittlere **Steigung** der juengsten Haelfte (nicht der Mittelwert des Standes) |
| `lage_im_bereich` | wo der letzte Schlusskurs im Fensterbereich steht (0 = Tief, 1 = Hoch) |

Daraus: `d_preis > 0` und `d_cvd < 0` und oberes Ende → **-1** (Verteilung am
Hoch); `d_preis < 0` und `d_cvd > 0` und unteres Ende → **+1** (Akkumulation am
Tief); sonst 0. Zwei zusaetzliche Tore: die Preisbewegung muss mindestens 15 %
der Fensterspanne betragen (30 % fuer `stark`), und die CVD-Steigung mindestens
10 % der mittleren Eimer-Bewegung — sonst ist es Rauschen, siehe unten.

**Der Mittelwert des CVD-Standes waere falsch.** Ein steil gestiegener und dann
leicht gefallener CVD hat immer noch einen hoeheren Mittelwert als die aeltere
Haelfte; eine Verteilung saehe dann wie Bestaetigung aus. Beim ersten Testlauf
ist genau das passiert (Fall `test_baerische_divergenz_preis_hoch_cvd_runter`
fiel zunaechst durch) — gemessen wird deshalb die Steigung.

## Woher die Zahlen kommen (und wo nicht)

`okxf.taker_volumen(inst, "4H")` — OKX fuehrt das Taker-Volumen je Kontrakt
unter `/api/v5/rubik/stat/taker-volume-contract`. Ein Abruf, 100 Eimer (4h-Eimer
= rund 16 Tage Tiefe), Rueckgabe `[ts, Verkaufsvolumen, Kaufvolumen]`,
Einheit Kontrakte wie in den Kerzen.

**Das rohe Trade-Tape traegt 4 Stunden nicht.** Am 13.09.2026 gemessen:
`/api/v5/market/history-trades` liefert 100 Trades je Anfrage, und 100 Trades
sind bei BTC-USDT-SWAP **28 Sekunden** (CHIP 15 s, WLFI 118 s). Vier Stunden
waeren rund **4000 Anfragen je Wert** — bei etwa 40 Anfragen je 2 s eine Stunde
fuer ein Instrument. Der Taker-Volumen-Endpunkt ist derselbe Inhalt, von der
Boerse aggregiert.

**Host-Falle (wichtig fuer alles unter `/rubik/` mit `instId`).** Der Endpunkt
liefert Daten **nur auf `www.okx.com`**. Auf `my.okx.com` — dem Wert, auf den
`OKX_BASE` dieser Maschine zeigt — und auf `eea.okx.com` kommt **`code=0` mit
leerer Liste** zurueck: kein Fehler, nur nichts. Alle anderen geprueften
Marktendpunkte (Kerzen, Ticker, Funding, Instrumente, `long-short-account-ratio`)
antworten auf diesen Hosts korrekt; die Falle trifft genau diesen Endpunkt.
Konsequenz im Code: `okxf.RUBIK_BASIS` / `okxf.rubik_basis()` (Override
`OKX_BASE_RUBIK`), unabhaengig vom kontogebundenen `OKX_BASE`, und der Grund
einer leeren Antwort nennt den benutzten Host — „leer" ohne Hostangabe laesst
sich nicht deuten.

## Rangfolge: jetzt drei hoch gewichtete Bausteine

[[Volumen-Drift-Signal]] verlangt ausdruecklich, dass beim dritten hoch
gewichteten Baustein die Reihenfolge laut ausgesprochen wird. Sie lautet:

1. **SuperTrend + EMA** setzen die Grundrichtung (RSI blockt nur Nachlaufen).
2. **Saisonalitaet** ([[Saisonalitaet-Signal]]) — kann setzen und kippen.
3. **Volumen-Drift** — hat Vorrang vor der Saisonalitaet.
4. **CVD-4h-Divergenz** — laeuft als letzte und hat damit das letzte Wort.
5. Danach die RSI-Wache: sie kann ein long-Signal weiter zu „kein" machen.

Die Pruefreihenfolge im Code **ist** die Rangfolge; es gibt keine zweite
Vorrangregel. Die RSI-Wache ueberschreibt den Grundtext (vorhandenes Verhalten,
unveraendert gelassen).

## Kalibrierung der Tore (13.09.2026)

Ein Tor, das nie aufgeht, ist kein Filter, sondern ein Fehler — und eines, das
immer aufgeht, ist keiner. Gemessen ueber 15 USDT-Perpetuals und **1287
Fenster** zu je 12 4h-Eimern:

- 142 Fenster zeigten eine Divergenz (11,0 %).
- Verteilung von `|CVD-Anteil|` in diesen 142: min 0,002 · p10 0,037 ·
  p25 0,142 · Median 0,333 · p75 0,623 · max 1,202.
- Das untere Fuenftel (27 Fenster unter 0,10) ist das Rauschband; die Schwelle
  `MIN_CVD_ANTEIL = 0.10` schneidet es weg.
- Danach: **115 Fenster = 8,9 %** aller Fenster als Signal (long 2,4 %,
  short 6,5 %). Vor der Schwelle waren es 11,0 %.

Ein live gefundenes Beispiel (13.09.2026, AVAX-USDT-SWAP): Preis -1,24 % im
Fenster, CVD-Steigung +4 % — das lag **unter** der Schwelle und ist deshalb
korrekt neutral, obwohl das Vorzeichen passte. Genau dafuer ist die Schwelle da.

## Ausfallverhalten

Ein neuer Datenabruf im Signalpfad darf das Signal nicht umbringen: `lage()`
laeuft in jedem Zyklus jeder Spur.

- **429 / `50011 Too Many Requests`**: Rubik drosselt strenger als der
  Marktdatenpfad, und `OKXFehler` wird von `_mit_wiederholung` nicht wiederholt.
  `cvd_4h()` versucht es einmal erneut (1,2 s Pause) und faellt dann auf neutral
  zurueck.
- **Leere Antwort / Netzfehler**: neutrale Lage mit Grund und Host.
- **Kein Instrument im Aufruf** (`lage(k)` ohne `inst=`): die Komponente faellt
  aus, alles andere rechnet unveraendert. Aeltere Aufrufer bleiben damit gueltig.
- **Test-Naht**: `indikatoren.cvd_quelle` (Modulvariable) und der Parameter
  `cvd_lage=` in `lage()`. Beide Wege sind getestet, keiner geht ins Netz.

## Nachrechnen

```powershell
cd Agenten\Handel\xperp
..\.venv\Scripts\python.exe test_cvd.py                 # 22 Faelle
..\.venv\Scripts\python.exe bot.py lage --wert AVAX-USDT-SWAP
```

Die Zeile „CVD-4h ..." zeigt Eimerzahl, Preisbewegung, CVD-Anteil und Richtung;
bei gesetzter Richtung folgt die Zeile mit Hoch/Tief und — falls zutreffend —
„STARK". Die Kalibrierprobe (Verteilung und Oeffnungsrate) liegt als
Wegwerfskript unter `Agenten/Hermes/cache/cvd_kalibrierung.py`.

## Was hier NICHT gebaut ist

- **VPIN** (Flow Toxicity, fixe Volumen-Buckets) — aus denselben Daten
  nachbaubar, noch offen.
- **OBI/OFI** — brauchen Orderbuch-Snapshots ueber den Websocket inklusive
  Speicherung, nicht aus dem Tape.
- **Kyle's Lambda, Absorption, Markout** — eigene Rechnungen, nicht Teil dieser
  Komponente.
- **Smart-Money-Delta** — braucht Wallet-Kohorten (bei Buildix Hyperliquid-
  On-Chain); aus Boersendaten nicht nachbaubar.

Verwandt: [[Volumen-Drift-Signal]], [[Buildix-Santiment-Handelswissen]], [[Saisonalitaet-Signal]], [[Analyse-Quellen]]

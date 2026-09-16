---
id: 20260901-saisonalitaet-signal
title: 'Saisonalität im XPERP-Signal'
tags: [handel]
created: 2026-09-01
updated: 2026-09-16
related: [20260901-xperp-handel, 20260830-handelsbots, 20260902-handelsregeln, 20260908-volumen-drift-signal]
summary: 'Warum der Closed-Source-Indikator xGhozt Prophecies als Kalenderstatistik nachgebaut ist, hoch gewichtet ins Signal greift und trotzdem seine duenne Stichprobe nennt.'
---

# Saisonalität im XPERP-Signal

Am 01.09.2026 hat Max angeordnet, den TradingView-Indikator
**[xGhozt Prophecies: A Forecast on the Future](https://de.tradingview.com/script/HtBJgdne-xGhozt-Prophecies-A-Forecast-on-the-Future/)**
in die Chart-Analyse des XPERP-Bots aufzunehmen und **hoch zu gewichten**.
Umgesetzt in `Agenten/Handel/xperp/indikatoren.py` (`saisonalitaet()`, greift in
`lage()` ein) und sichtbar in `bot.py lage`.

**Warum:** Der Auftrag stand gegen zwei bestehende Bauentscheidungen, und
dieser Widerspruch ist der Grund für die Notiz — sonst wird er beim nächsten
Umbau übersehen:

1. **Der Indikator ist Closed-Source.** Der Pine-Code ist nicht einsehbar, es
   gibt keine API. Kopiert werden konnte nichts — nur sein Prinzip nachgebaut:
   Kalenderstatistik nach Wochentag und Tagesphase (UTC). Für die nächste,
   noch nicht existierende Kerze wird gemessen, wie oft frühere Kerzen
   desselben Rasters über ihrem Eröffnungskurs schlossen und wie groß die
   mittlere Kerzenrendite war.
2. **`lage()` verrechnet seine Bausteine bewusst nicht.** SuperTrend, EMA und
   RSI bleiben getrennt, „eine Summe würde verdecken, welcher davon
   widerspricht". Die Saisonalität ist die erste Ausnahme: sie *darf* das
   Signal setzen und gegen SuperTrend+EMA kippen.

## Wie es wirkt

| Lage | Folge im SIGNAL |
|---|---|
| Saisonalität = SuperTrend+EMA | Signal bleibt, Grund: „+ Saisonalität bestätigt" |
| SuperTrend/EMA widersprechen sich | Saisonalität **setzt** die Richtung |
| Saisonalität gegen SuperTrend+EMA | Saisonalität **überstimmt** — Signal kippt |

`richtung` wird nur ≠ 0, wenn die Wochentags-Aggregation **≥ 6 Beobachtungen**
hat *und* Auf-Quote (≥ 58 % long / ≤ 42 % short) und mittlere Rendite dasselbe
Vorzeichen zeigen. RSI kann ein saisonal gesetztes Long danach weiter als
überkauft blocken.

## Die Einschränkung, laut in der Ausgabe

Bei 300×4h-Kerzen sind das **rund sieben Kerzen je Wochentag** (~50 Tage
Historie). Das ist Rückblick auf einem dünnen Fenster, kein Backtest — dasselbe
Muster, vor dem [[Handelsbots]] warnt („Kurze Fenster täuschen zuverlässig").
Deshalb druckt `bot.py lage` bei jeder Saisonalitäts-Zeile `n` mit, und wenn
der Faktor das Signal dreht, nennt der Grund-Text die Stichprobe. **Vor dem
Vertrauen in eine gekippte Richtung: `n` lesen.**

## Seit 16.09.2026: die Statistik kommt aus der tiefen Reihe (T-018)

Die Saisonalität ist **Statistik**, nicht Kursstruktur - wie Hebel-Deckel und
Trefferquote. Auf ~50 Tagen Kontrakthistorie (300 4h-Kerzen) trägt der
Wochentag nur rund sieben Beobachtungen. Deshalb rechnet `bot.py` sie seit dem
16.09.2026 auf der tiefen Reihe, wenn `--historie` gesetzt ist.

Nachgemessen an `LINK-USD_UM_XPERP-310829` (20 Tage alt) am 16.09.2026:

| Reihe | Kerzen | Beobachtungen für den Wochentag |
|---|---|---|
| Kontrakt | 300 | n = 16 |
| `LINK-USDT-SWAP` | 1200 | n = 172 |

Die Ausgabe nennt die Basis jetzt ausdrücklich (`Basis: tiefe Reihe, 1200
Kerzen - Statistik, nicht der Kontrakt`); die Warnung „n=... ist dünn" entfällt
genau dann. Übernommen wird die Reihe nur, wenn sie **gleichzeitig endet**
(`indikatoren._gleichzeitig`): `saisonalitaet()` liest Wochentag und Tagesphase
der *nächsten* Kerze aus dem Ende der Reihe, eine verschobene oder alte Reihe
würde das Raster still verschieben. Dafür steht der Signal-Merge in
`indikatoren.signal_bauen()` an einer Stelle statt zweimal im Quelltext.

Das **Kurs-Signal** (SuperTrend, EMA, RSI, ATR jetzt) bleibt weiter am
gehandelten Kontrakt - getauscht wird nur die Statistik, wie bei
[[XPERP-Handel]] unter `--historie` beschrieben. Sechs Tests halten es:
`xperp/test_saisonalitaet_tief.py` (ohne Netz).

## Nachrechnen

```powershell
cd Agenten\Handel\xperp
..\scanner\.venv\Scripts\python.exe bot.py lage --wert SOL
```

Die Zeile „Saisonalität <Wochentag> <hh>:00 UTC" zeigt Richtung, Auf-Quote,
`n` und mittlere Kerzenrendite; eine zweite Zeile die feinere Aggregation
Wochentag+Phase, sobald sie ≥ 3 Treffer hat.

Seit 08.09.2026 gibt es einen zweiten hoch gewichteten Baustein,
[[Volumen-Drift-Signal]] — dort steht auch die Vorrangregel für den Fall,
dass beide sich widersprechen.

Verwandt: [[XPERP-Handel]], [[Handelsbots]], [[Volumen-Drift-Signal]], [[Schutzregeln]]

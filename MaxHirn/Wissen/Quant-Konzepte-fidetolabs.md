---
id: 20261021-quant-konzepte
title: 'Quant-Konzepte aus den fidetolabs-Reels'
tags: [handel, methoden]
created: 2026-10-21
updated: 2026-10-21
related: [20261021-handelsuniversum, 20261021-signature-plot, 20260902-handelsregeln]
summary: 'Sechs Methoden aus Captions der Reels von fidetolabs.math (Marchenko-Pastur, Fractional Differencing, Triple Barrier, Signature Plot, CUSUM, Breeden-Litzenberger): was sie tun, was die Captions weglassen, und wo sie zu unseren Spuren passen.'
---

# Quant-Konzepte aus den fidetolabs-Reels

Die sechs Reels von `fidetolabs.math` ließen sich über Instagram nicht abrufen.
Max hat die Captions eingefügt. Die Notiz hält fest, was die Konzepte tun und
was sie nicht sind. **Keines davon ist eine vollständige Handelsstrategie**: Es
fehlen Einstieg, Ausstieg und Positionsgröße.

**Warum:** Die Reels werden als Strategien verkauft, sind aber Bausteine für
Datenaufbereitung, Labeling und Risikomodelle. Wer sie als Strategie übernimmt,
übernimmt die Lücke gleich mit.

| # | Konzept | Was es tut | Passt zu uns? |
|---|---|---|---|
| 1 | **Marchenko-Pastur** | Obergrenze für Zufallskorrelationen in einer Korrelationsmatrix (Eigenwerte oberhalb der Grenze gelten als Signal) | Nur bei Portfolios mit mehreren Assets, derzeit kein Anwendungsfall |
| 2 | **Fractional Differencing** | Preisreihe teilweise differenzieren, bis sie stationär ist, das Langfristgedächtnis bleibt erhalten. Differenzierungsgrad d per ADF-Test wählen. | Als Feature-Bau für Modelle denkbar |
| 3 | **Triple Barrier** | Gewinnziel, Verlustgrenze und Zeitlimit. Die Barriere, die zuerst fällt, bestimmt das Label. | Gut für die Auswertung von Backtests: vermeidet Look-ahead. Barrieren müssen festgelegt werden. |
| 4 | **Signature Plot** | Volatilität gegen Abtastintervall. Feines Sampling kann Bid-Ask-Rauschen aufblasen. | Ja, zur Wahl des Sampling-Intervalls. Ergebnis in [[Signature-Plot-XBTEUR]]. |
| 5 | **CUSUM-Filter** | Ereignis erst auslösen, wenn die kumulierte Kursbewegung eine Schwelle überschreitet (h = 4σ im Reel). | Ja, als Auslöser statt fester Zeitschritte |
| 6 | **Breeden-Litzenberger** | Risikoneutrale Verteilung aus Butterfly-Spreads der Optionskette | Nur mit Optionsdaten, die wir nicht haben |

## Einzelne Befunde

- **Signature Plot:** Die Zahlen im Reel (37,9 % bei Sekundensampling gegen
  16,0 % bei 79 Sekunden, Faktor 2,4) sind innerlich konsistent. Ob sie stimmen,
  ist nicht prüfbar, weil Sekundendaten fehlen. Auf XBTEUR über 60 Stunden zeigt
  sich kein Rauschaufschlag zwischen 5 und 60 Minuten.
- **CUSUM:** h = 4σ = 4,56 % entspricht σ ≈ 1,14 %. Die Angaben „33 Sessions
  Wartezeit“ und „18 Events“ gelten für einen Datensatz, den wir nicht kennen.
- **Breeden-Litzenberger:** Die Näherung „1 Cent = 1 % Wahrscheinlichkeit“ gilt
  nur für eine Auszahlung von 1 ohne Abzinsung und ohne Dividenden. Die Beispielwerte
  (0,9 ¢ bei Strike 100, 4,3 ¢ bei 110) stammen aus dem Reel.

## Empfehlung

Wenn überhaupt eines davon in den Betrieb kommt, dann in dieser Reihenfolge:
Signature Plot (Sampling-Wahl), Triple Barrier (faire Backtest-Auswertung), CUSUM
(Ereignisauslöser). Vor einer Übernahme müssen die Konzepte auf einem Universum
laufen, das dem Betrieb entspricht ([[Handelsuniversum]]).

---
id: 20260830-handelsbots
title: 'Handelsbots auf OKX'
tags: [handel]
created: 2026-08-24
updated: 2026-09-02
related: [20260902-handelsregeln, 20260830-schutzregeln]
summary: 'Gemessene Ergebnisse der OKX-DCA-Bots und welche Stellschraube tatsächlich wirkt.'
---

# Handelsbots auf OKX

Gemessene Erkenntnisse zu den DCA-Bots (Martingale) auf OKX, entstanden aus der
Auswertung des BTC-Bots vom 24.08.2026. Der Kern: **Die Stellschraube ist
`slPct`, nicht `pxStepsMult`** — und über 12 Monate gerechnet lag jede getestete
Einstellung dicht an der Nulllinie, leicht darunter.

**Warum:** Die Auswertung kostete rund eine Stunde Rechenzeit und einen
Jahres-Download. Ohne diese Notiz beginnt sie beim nächsten Bot von vorn — und
die beiden nicht offensichtlichen Punkte (fester Stop-Loss, HTTP 403) würden
erneut Zeit kosten.

**Stand:** 2026-08-24

## Der Stop-Loss hängt am Einstieg, nicht am Schnitt

Das ist der Punkt, der die ganze Bewertung dreht. Beobachtet am laufenden Bot:
Der Durchschnittspreis fiel durch vier Nachkäufe von 79.917 auf 79.558, `slPx`
blieb unverändert bei **77.519,5** — exakt 3 % unter dem *Einstiegspreis*.

Daraus folgt: Nachkaufstufen unterhalb dieser festen Schwelle werden nie
erreicht. Das dafür reservierte Geld liegt tot.

| `pxStepsMult` | Leiterende | nutzbare Stufen | einsetzbares Kapital |
|---|---|---|---|
| **0,94** | 77.657 | **8 von 8** | **119 von 119 $** |
| 1,00 | 77.147 | 6 von 8 | 90 von 119 $ |
| 1,10 | 75.983 | 5 von 8 | 77 von 119 $ |
| 1,20 | 74.292 | 4 von 8 | 65 von 119 $ |

Ein Multiplikator unter 1 ist hier also **richtig**, nicht falsch: Er hält die
Leiter im erreichbaren Bereich. Die verbreitete Faustregel „Multiplikator über
1, damit die Leiter tiefere Rutsche übersteht" gilt nur bei einem Stop-Loss, der
mit dem Schnitt mitwandert. Bei OKX tut er das nicht.

## Die Trefferquote deckt das Verhältnis von Gewinn zu Verlust nicht

Rückrechnung über 8.800 Stundenkerzen (23.08.2025–24.08.2026), Einstieg alle
2 Stunden, Haltedauer maximal 3 Tage, Gebühren 0,05 % je Ausführung:

| Variante | Ziel erreicht | Ø Gewinn | Ø Verlust | nötige Quote | je Runde |
|---|---|---|---|---|---|
| Ist-Zustand | 78,4 % | 1,78 $ | 7,45 $ | 80,7 % | −0,22 $ |
| Mult 1,05 | 77,7 % | 1,73 $ | 7,20 $ | 80,6 % | −0,26 $ |
| ohne Preis-Trigger | 89,2 % | 2,07 $ | 19,98 $ | 90,6 % | −0,38 $ |
| Stop-Loss 6 % | 96,8 % | 2,26 $ | 56,34 $ | 96,1 % | −0,23 $ |
| Trigger erst bei −3 % | 89,2 % | 2,07 $ | 17,79 $ | 89,6 % | **−0,15 $** |

Das Muster ist das eigentliche Ergebnis: **Egal wie die Parameter stehen, nötige
und erreichte Trefferquote liegen ein bis zwei Prozentpunkte auseinander.** Ein
weiterer Stop-Loss senkt die Stopp-Häufigkeit, macht jeden Stopp aber
entsprechend teurer. Die Struktur gleicht sich selbst aus; übrig bleiben die
Gebühren, und die gehen gegen einen.

## Kurze Zeiträume täuschen zuverlässig

Dieselbe Rechnung über die **letzten 30 Tage** ergab für den Ist-Zustand
**+0,63 $ je Runde** statt −0,22 $. In diesem Fenster stieg BTC von 62.268 auf
80.000 (+28,5 %). Ein Long-Martingale sieht in jedem Aufwärtsmonat gut aus.

**Regel daraus:** Einen Bot nie über weniger als ein Jahr bewerten, und den
Kursverlauf des Testfensters immer mit angeben.

## Fallen beim Nachrechnen

- **OKX antwortet ohne User-Agent mit HTTP 403.** `curl` setzt einen, Pythons
  `urllib` nicht. Kostete hier einen Durchlauf, der in einer Endlosschleife
  hing, weil die Ausnahmebehandlung stumpf weiterprobierte. Immer
  `{"User-Agent": "Mozilla/5.0"}` mitgeben und Fehlversuche zählen.
- **Stundenkerzen lösen nicht auf**, ob Hoch oder Tief zuerst kam. Beide
  Reihenfolgen durchrechnen und die Spanne angeben (hier: −0,22 bis −0,39 $).
- **Funding-Gebühren fehlen** in der Rückrechnung. Der echte Bot zahlte
  −0,031 $ in 36 Minuten auf 570 $ Position; über drei Tage frisst das rund
  einen halben Durchschnittsgewinn.
- **`investmentAmt` ist das reservierte Gesamtkapital**, nicht das eingesetzte.
  Beim BTC-Bot 119,49 $ bei nur 28 $ Ersteinsatz.
- **Das Modell traf die Ausführung nicht genau:** nach vier Nachkäufen 570 $
  Nominal statt der berechneten 651 $, vermutlich Rundung auf ganze Kontrakte
  (`ctVal` 0,0001 BTC).

## Nicht verwechseln: zwei Bedeutungen von „DCA“

In `Handel/` liegen beide, sie haben nur den Namen gemeinsam:

| Datei | Was | Datenquelle |
|---|---|---|
| `dca.py`, `vergleich.py` | **Sparplan** — feste Summe, festes Intervall, wahlweise gehebelt | yfinance (Aktien) |
| `dca_auswertung.py` | **Martingale-Bot** — Nachkaufleiter, Take-Profit, Stop-Loss je Runde | OKX (Krypto) |

`vergleich.py` macht für den Sparplan denselben Punkt, den oben der
Jahreszeitraum macht: Ein Backtest auf einem einzigen günstigen Fall misst
vor allem diesen Fall.

## Nachrechnen

```
cd Handel
python dca_auswertung.py --details          # 12 Monate
python dca_auswertung.py --tage 30          # kurzes Fenster zum Vergleich
```

Die Bot-Werte stehen in `KONFIG` oben im Skript und lassen sich alle aus
`dca_get_order_details` ablesen. Verwandt: [[Verbindungen]] (OKX Agent Trade
Kit als MCP-Server), [[Marktlage-August-2026]], [[Projekte]].

## Grenze

**Überholt seit 01.09.2026.** Bis dahin galt: Das Auslösen von Geldbewegungen
— starten, stoppen, anpassen, schließen — bleibt bei Max; gelesen, gerechnet und
vorbereitet wird vollständig, der letzte Klick nicht. Seither ist automatischer
Handel im Rahmen der beiden `wachen.json` die Regel. Was heute gilt, steht in
[[Handelsregeln]]. Unverändert davon: Eine Claude-Sitzung sendet die scharfe
Order nicht selbst — auch auf Kraken nicht, wo seit 02.09.2026 zwar eine
bewachte dritte Spur handelt, die schreibenden MCP-Werkzeuge aber gesperrt
bleiben.

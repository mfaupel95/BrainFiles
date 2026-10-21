---
id: 20260830-handelsbots
title: 'Handelsbots auf OKX'
tags: [handel]
created: 2026-08-24
updated: 2026-10-11
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

## Haus-Spuren als Freqtrade-Bots (seit 10.10.2026)

17 Haus-Spuren laufen zusätzlich zu den drei Moon-Dev-Bots als
Freqtrade-Dry-Run-Bots: 11 × `klassik_*`, `macd_mtf`, `squeeze`, `wavetrend`,
`supertrend`, `trendwende_btc`, `orb` (Ports 8084–8100, Liste in
`Agenten/Handel/freqtrade/bots.json`). Grundlage ist **eine** Strategie
`HausSpur`, die die Regel nicht nachbaut, sondern über
`Agenten/Handel/hausspur_regeln.py` aus dem Haus importiert. `Agenten/` hängt
dafür nur lesend unter `/agenten` im Container. Gerechnet wird je Kerze auf
demselben Fenster wie im Haus (`kerzen_anzahl`), Futures, Hebel 1.

- **Bot ergänzen:** Spur in `ALLE` von `hausspur_regeln.py`, Eintrag in
  `bots.json`; der Test `Manifest` in `freqtrade/tests/test_bots_hausspur.py`
  prüft Zeitrahmen und Paare gegen die `wachen.json`.
- **Urteil:** `python bots.py backtest <bot>` schreibt Runden, Netto % und
  Rücklauf nach `freqtrade/urteile.json`. Der Leitstand-Reiter **FreqTrade**
  (Strg+8) zeigt es neben jedem Bot. Viele Bots heißt nicht viel Kante: erster
  Probelauf `klassik-ema`, 4h, 21 Monate: 227 Runden, −30,5 %. Das Ziel läuft
  über `custom_roi`, damit der Backtest zum Zielpreis schließt wie das Haus;
  mit `custom_exit` waren es geschönte −25,7 % (Ziel erst zum Kerzenschluss).
- **Container sieht nur** `Agenten/Handel` und `Agenten/Bus` (read-only); alle
  Handel-Ordner, die keine Spur braucht, sind per tmpfs überdeckt — dort liegen
  fremde Zugänge.
- **Schnellere Strategien (Phase B)** ersetzen eine Spur erst, wenn
  `freqtrade/gleichheit.py` auf derselben Kerzenreihe keine Abweichung zum
  Adapter meldet. Erste B-Fassung: `HausSpurKlassikDonchianTrend` (seit
  11.10.2026). Knackpunkt war die Haus-EMA: Sie wird je Kerze im 400er-Fenster
  neu gerechnet, gestartet mit dem SMA der ersten n Kerzen. Eine durchgehende
  EMA weicht davon ab.

### Walk-Forward `klassik-donchian-trend` (11.10.2026): Haus-Wachen bleiben

Optimiert wurden Einstiegs- und Ausstiegskanal, EMA-Länge, EMA-Steigung und
Stop, mit `python freqtrade/walkforward.py` und der Strategie
`HausSpurDonchianTrendOpt`. Gerechnet in 3 rollenden Falten: je 8 Monate
lernen, dann 4–5 Monate prüfen, 300 Epochen, Sharpe auf Tagesbasis. Daten:
4h-Futures BTC/ETH/SOL.

| Falte | Vorgabe gelernt | Optimiert gelernt | Vorgabe geprüft | Optimiert geprüft |
|---|---|---|---|---|
| 01–09/25 → 09–12/25 | +28,2 % | +44,8 % | +1,4 % (8) | +4,4 % (7) |
| 05–12/25 → 01–04/26 | +25,7 % | +42,9 % | −8,3 % (16) | −9,9 % (15) |
| 09/25–04/26 → 05–10/26 | −7,0 % | +8,6 % | +8,2 % (34) | +3,4 % (41) |
| **Summe Prüfzeiten** | | | **+1,36 % (58)** | **−2,15 % (63)** |

In der Lernzeit liegt die Optimierung 15–17 Punkte vorn, in der ungesehenen
Prüfzeit 3,5 Punkte hinten. Die Siegerwerte springen von Falte zu Falte:
EMA 168/273/139, Ausstiegskanal 16/5/29. Das ist Überanpassung, also bleiben
die Haus-Wachen. Stabil blieben nur zwei Werte: Einstiegskanal 29–35 statt 20
und Stop 2,8–3,5 % statt 5 %. Das ist ein Hinweis, kein Beleg; die
Prüffenster haben nur 7–41 Runden.

**Regel daraus:** Ein Hyperopt-Gewinn zählt erst, wenn er in der späteren
Prüfzeit gegen die Vorgabe besteht. Der Gewinn in der Lernzeit allein sagt
nichts.

Fallen beim Hyperopt mit `HausSpur`:

- **Hyperopt-Worker fanden `Handel/freqtrade` statt des echten Pakets**
  (`ImportError __version__`). Seit 11.10. nimmt `bot_start` den echten
  Paketordner in `sys.path` auf.
- **`hyperopt-show --best` schreibt selbst die Parameterdatei**
  `strategies/<Strategie>.json`, und jeder spätere Backtest liest sie still mit.
  `walkforward.py` legt sie nur für die Sieger-Backtests an und löscht sie
  danach. Mit `--strategy` liest `hyperopt-show` keine Epochen und schweigt.
- **Parameterabhängige Spalten gehören nach `populate_entry_trend`.**
  `populate_indicators` läuft beim Hyperopt nur einmal je Lauf, nicht je
  Epoche.

Auslösung auf Kerzenschluss (Schalter `hausspur.ausloesung: "schluss"`,
seit 11.10.): Bei `squeeze` war sie schlechter, −27,6 % gegen −4,5 % mit
Auslösung schon beim Docht. Die Vorgabe bleibt deshalb „docht“.

Spec und Plan: `Werkstatt/spec-freqtrade-hausspuren-2026-10-10.md`,
`Werkstatt/plan-freqtrade-hausspuren-2026-10-10.md`.

## Grenze

**Überholt seit 01.09.2026.** Bis dahin galt: Das Auslösen von Geldbewegungen
— starten, stoppen, anpassen, schließen — bleibt bei Max; gelesen, gerechnet und
vorbereitet wird vollständig, der letzte Klick nicht. Seither ist automatischer
Handel im Rahmen der beiden `wachen.json` die Regel. Was heute gilt, steht in
[[Handelsregeln]]. Unverändert davon: Eine Claude-Sitzung sendet die scharfe
Order nicht selbst — auch auf Kraken nicht, wo seit 02.09.2026 zwar eine
bewachte dritte Spur handelt, die schreibenden MCP-Werkzeuge aber gesperrt
bleiben.

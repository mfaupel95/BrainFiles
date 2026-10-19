---
id: 20260921-archiv-trading-skills
title: 'Archiv-Trading-Skills und Fremdstrategien im Lauf'
tags: [handel]
created: 2026-09-21
updated: 2026-09-21
related: [20260902-handelsregeln, 20260830-handelsbots, 20260831-marktscanner]
summary: 'Was von den ausgemusterten Handels-Skills lauffaehig ist, was nicht, und was eine gefahrene Fremdstrategie gemessen liefert.'
---

# Archiv-Trading-Skills und Fremdstrategien im Lauf

Auftrag am 21.09.2026: Handels- und Trading-Skills aus dem Archiv holen,
durchsehen und **laufen lassen**, um zu sehen, ob ein Mehrwert herauskommt.
Ergebnis vorab: **der Mehrwert liegt nicht in den Skills, sondern in den
Fremd-Repos unter `Werkstatt/` samt ihren Kursdaten.** Das Archiv enthaelt
beschreibendes Material, das teils auf nicht installierte Werkzeuge zeigt.

## 1. Was im Archiv unter Trading laeuft

Die ausgemusterten Skills liegen unter `Agenten/Hermes/skills/.archive/` und
sind **lesbar, ohne in die Bibliothek geladen zu werden** — ein Archiv-Skill
kostet null Tokens je Anfrage, solange er dort bleibt. Zurueckholen per
`hermes curator restore <name>`, Liste per `hermes curator list-archived`.

| Skill | Trading-Bezug | Laeuft es? |
|---|---|---|
| `geld` | Fristen + Kraken-Guthaben nebeneinander | **Ja** — rein ueber Kraken-MCP, keine Installation. Am 21.09.2026 zurueckgeholt |
| `marktbriefing` | Makro-/Sektor-/Movers-Boards | **Nein** — ruft `traderhub` auf, und das Werkzeug ist auf dem Rechner **nicht installiert**. Die Monatsnotize [[Marktlage-September-2026]] haengt an derselben Luecke |
| `financial-services` (67 Skills) | DCF-, 3-Statement-, Comps-, Earnings-, KYC-Modelle | Technisch ja (`validate_dcf.py`), praktisch nein: Eigenkapital-/Investmentbanking-Welt, braucht Excel- und LSEG-Anbindung. **Bewusst im Archiv gelassen** — 67 Skills waeren dauerhafte Last ohne Bezug zu Krypto/OKX/Kraken |
| `product-price-monitor`, `competitor-news-monitor`, `blogwatcher` | Preis-/News-Wachen | Generisch, brauchen je einen eigenen Dienst; fuer den Handel kein Zugewinn |
| `vergleich`, `research`, `arxiv` | Datei-/Literaturarbeit | Kein Trading |

## 2. Die gefahrene Fremdstrategie (Original-Code, lokale Daten)

Strategie: `Bollinger-Squeeze + Keltner-Kanal (TTM-Squeeze) + ADX > 25`,
Ausbruch long/short, Ziel 5 %, Stop 3 % — Original aus
`Werkstatt/Harvard-Algorithmic-Trading-with-AI/backtest/bb_squeeze_adx.py`.
Unveraendert uebernommen, nur Datenquelle und Gebuehr parametrisiert.
Lauffaehig im venv `Werkstatt/moon-dev-ai-agents/.venv` (pandas, talib,
backtesting.py).

| Daten | Zeitraum | Kerzen | Gebuehr/Seite | Rendite | Trades | Treffer | Erwartung je Trade |
|---|---|---|---|---|---|---|---|
| BTC 1h (Repodaten) | 2015-07 → 2024-05 | 77.375 | 0,20 % | **−59,98 %** | 840 | 41,5 % | −0,151 % |
| BTC 1h (Repodaten) | dito | 77.375 | 0,05 % | +158,47 % | 901 | 41,0 % | +0,102 % |
| BTC 6h (Repodaten) | dito | 12.903 | 0,05 % | +44,42 % | 217 | 41,9 % | +0,178 % |
| ETH 1d (Repodaten) | 2016-05 → 2024-07 | 2.976 | 0,05 % | −2,85 % | 56 | 39,3 % | −0,055 % |
| SOL 1d (Repodaten) | 2021-06 → 2024-07 | 1.122 | 0,05 % | −10,20 % | 16 | 31,2 % | −0,671 % |
| **BTC 1h (Hausdaten, frisch)** | 2025-08 → 2026-08 | 8.800 | 0,05 % | **−14,00 %** | 57 | 35,1 % | **−0,364 %** |
| BTC 1h (Hausdaten, frisch) | dito | 8.800 | 0,20 % | −23,61 % | 56 | 35,7 % | −0,615 % |

**Lesart.** Ueber neun Jahre war der Vorteil je Runde so klein, dass ihn die
Gebuehr allein entschied: 0,20 % je Seite dreht das Ergebnis von +158 % auf
−60 %. Umgerechnet ist der **Kosten-Wendepunkt dieser Strategie ≈ 0,10 % je
Runde** (Kauf + Verkauf). Auf den frischen Hausdaten ist sie auch ohne
Gebuehrdruck negativ. Als Signalgeber ist sie damit unbrauchbar.

## 3. Gegenprobe mit dem eigenen Massstab

`Agenten/Handel/kosten_wendepunkt.py` liefert denselben Massstab fuer die
Haus-Spuren (f_max = Gebuehr je Runde, bei der die eigene Trefferquote nur die
Nullinie trifft), Lauf vom 21.09.2026:

| Buch | Runden | f_max je Runde |
|---|---|---|
| scanner/mittel | 225 | +12,92 % |
| scanner | 122 | +9,98 % |
| xperp | 15 | +2,54 % |
| swap | 3 | +1,13 % |
| orbk | 8 | +0,07 % |
| **Harvard-Fremdstrategie** | 840–901 | **≈ +0,10 %** |

Die Fremdstrategie steht damit auf dem Niveau der schwaechsten eigenen Spur
(orbk, das an der Kraken-Gebuehrfreiheit haengt) und rund **100-mal schlechter**
als der Scanner. Das ist kein Argument gegen fremde Strategien, sondern der
Beleg, dass der Kostenmassstab vor der Uebernahme gehoert — genau wie bei
[[Handelsbots]].

## 4. Wo der echte Mehrwert liegt

1. **Die Kursdaten der Fremd-Repos.** `Werkstatt/Harvard-…/backtest/data/`
   traegt `BTC-1h-1000wks-data.csv` (77.375 Stundenkerzen ab 2015), dazu BTC-6h,
   ETH-1d, SOL-1d sowie BTC-15m/1d. Rund **neun Jahre Historie lokal**, ohne
   Netzzugriff — bislang von keiner eigenen Spur genutzt.
2. **Vier fertige Backtest-Umgebungen mit eigenem venv** unter `Werkstatt/`:
   `freqtrade` (2026.9-dev, ccxt 4.5.78, lauffaehig; `user_data/data` ist
   **leer**, es fehlt der Daten-Download), `FinRL`, `RLTrader`,
   `intelligent-trading-bot`.
3. **Ein wiederverwendbares Pruefmuster:** Fremdstrategie mit Original-Code auf
   lokalen Kerzen fahren, Gebuehr zweifach (0,05 % und 0,20 %), Ergebnis gegen
   `kosten_wendepunkt.py` halten. Erst danach ueber Parameter reden.

Nachrechnen (Skript liegt versioniert neben dem Handel):
`Agenten/Handel/backtest_archiv_strategie.py`,
Aufruf mit `Werkstatt/moon-dev-ai-agents/.venv/Scripts/python.exe`.

## 5. Was nicht angefasst wurde

- `financial-services` (67 Skills) bleibt im Archiv, `marktbriefing` ebenso
  (`traderhub` fehlt weiter) — beide ohne Bibliothekslast lesbar.
- Keine laufende Spur, kein `wachen.json`, kein Dauerlauf beruehrt; es wurden
  nur Daten gelesen und ein befristeter Backtest gefahren.
- `Werkstatt/Harvard-…` ist unveraendert (Original-Code nur kopiert,
  Mac-Pfad nicht editiert).
- Kein Modell, kein Schluessel, kein Guthaben bewegt.

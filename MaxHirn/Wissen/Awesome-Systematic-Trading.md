---
id: 20260917-awesome-systematic-trading
title: "awesome-systematic-trading: kuratierte Referenzliste fuer systematisches Trading"
tags: [handel, struktur, ki-agenten]
created: 2026-09-17
updated: 2026-09-17
related: [20260916-repo-bots, 20260921-prognose-backtest]
summary: "Fork von paperswithbacktest/awesome-systematic-trading - reine Markdown-Sammlung (kein Code): 136 Backtesting-/Live-Trading-Bibliotheken, echte Sharpe/t-Stat-Kennzahlen zu Strategien aus 4.843 replizierten Papers, 55 Buecher. Referenz fuer eigene Handelsspuren, nichts zu installieren."
---

# awesome-systematic-trading

Fork [mfaupel95/awesome-systematic-trading](https://github.com/mfaupel95/awesome-systematic-trading)
von [paperswithbacktest/awesome-systematic-trading](https://github.com/paperswithbacktest/awesome-systematic-trading)
(0 Sterne beim Original selbst wenig bekannt, aber Traeger-Firma
paperswithbacktest.com hat 4.843 Strategie-Papers real repliziert und die
Kennzahlen offengelegt). Klon: `Werkstatt/Repos/awesome-systematic-trading`
(depth 1, `origin`=Fork, `upstream`=Original). Bot-Profil
`awesome-systematic-trading` (getrimmter Skillstand wie santiment/openmontage).

## Was es ist

**Kein Code-Repository** - README.md (+ ja/zh-Uebersetzung) mit 25 Abschnitten,
kuratiert und ueber `static/strategies` + ein Backend bei paperswithbacktest.com
gepflegt (dormant/archived-Markierungen werden automatisch aktualisiert).
Es gibt nichts zu installieren; der Nutzen ist reines Referenzmaterial.

## Fuer den Handelsstack relevant

### Einordnung der eigenen Spuren als Baustein-Frameworks

Die Liste unter „Backtesting and Live Trading" nennt genau die Kategorie
Werkzeug, die die eigenen Spuren (scanner/xperp/orbk/gitter/...) haendisch
nachbauen: `nautilus_trader` (bereits als eigenes Repo im Bestand,
`Agenten/Handel/nautilus`), `vectorbt` (Numba-beschleunigtes Vektor-Backtesting
- fuer `gitter/backtest_gitter.py` und `verbesserer/` interessant, falls die
eigene Brute-Force-Parametersuche zu langsam wird), `Freqtrade` (Python-Bot mit
eingebauter Telegram-Steuerung und ML-Strategieoptimierung - deckt sich mit dem
Haus-Muster Bot + Telegram, aber als fertiges Framework).

### Belegte Kennzahlen statt geschaetzter Sharpe-Ratios

Der Abschnitt „Strategies" listet **8 replizierte Krypto-Strategien** mit
echtem Sharpe/t-Stat/Volatility/Testjahren (Median ueber alle 4.843 Papers:
Sharpe 0.37, 48 % ueber t=1.96, 34 Jahre Testfenster, Beta zum S&P 500 +0.17).
Zwei Faelle mit direktem Bezug zu laufenden Spuren:

- **Multi-Timeframe-Trend auf Bitcoin**: Sharpe 3.39, t-Stat 16.2, 23 Jahre
  getestet - strukturell verwandt mit `mosaic` (4H/30M/5M Top-Down) und
  `macd_mtf`. Hoher Sharpe bei langer Historie ist ein Signal, das eigene
  Multi-Timeframe-Konzept nicht leichtfertig aufzugeben.
- **Seasonality/Trend-following/Mean-reversion in Bitcoin**: Sharpe 1.11,
  16 Jahre - deckt sich mit der xperp-Saisonalitaet aus T-018 (Commit
  `2f3a01a`, 15.09.2026).

Die Methode („Median braucht `(1.96/Sharpe)^2` Jahre zum Beweis") ist eine
gute Elle fuer die eigene Overfitting-Sperre im Verbesserer (`>= 20 OOS-Runden`
ist deutlich strenger als naiv, aber die Faustregel bestaetigt: bei den
kleinen Sharpe-Werten, die die eigenen Spuren bisher zeigen, sind viele Jahre
Testfenster noetig, bevor man von echtem Edge statt Rauschen sprechen darf).

### Kein Handlungsbedarf jetzt

Reines Nachschlagewerk - kein Anschluss an `dauerlauf.SPUREN`,
`auswertung_alle.py`, `spiegelstand.py`. Wird bei Bedarf konsultiert (neue
Spur-Idee, Bibliotheksauswahl fuer eine Optimierung), nicht automatisiert
eingebunden.

## Aufruf

```
cd Werkstatt/Repos/awesome-systematic-trading
```

Kein Setup, keine `.venv`, keine Schluessel - nur lesen.

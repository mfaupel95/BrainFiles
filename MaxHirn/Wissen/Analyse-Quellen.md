---
id: 20260902-analyse-quellen
title: 'Analyse-Quellen'
tags: [handel]
created: 2026-09-02
updated: 2026-09-08
related:
  - id: 20260830-marktlage-august-2026
  - id: 20260902-xrp-analyse-sta
  - id: 20260905-btc-analyse-sta
  - id: 20260901-saisonalitaet-signal
  - id: 20260908-volumen-drift-signal
  - id: 20260913-buildix-santiment
summary: 'Wiederkehrende externe Analyse-Quellen (YouTube-Kanäle, Indikatoren) mit fester Einstufung — damit die Quellenbewertung nicht in jeder Einzelnotiz neu geschrieben wird.'
---

# Analyse-Quellen

Externe Quellen, die mehr als einmal in eine Auswertung eingegangen sind. Die
Einstufung hier gilt, bis eine neue Auswertung sie ändert. Einzelnotizen
verweisen per `[[…]]` hierher, statt die Bewertung zu wiederholen.

## STA Solutions / Alexander Schulz

- **Was:** YouTube-Kanal mit Chart- und Marktanalysen. Geschäftsmodell:
  kostenpflichtige Kursanalysen (`schulz-technical-analysis.com`),
  Ledger-Provisionslink. Die Videos liefern bewusst die Richtung, nicht die
  Umsetzung.
- **Methodik:** »ITW«-Ansatz (Elliott-Wave-nah), fünfteilige Impulse +
  korrektive Wellen, dazu MACD / RSI / »messbare Marktstimmung« über mehrere
  Zeiteinheiten.
- **Einstufung:** *brauchbar als Hypothesen- und Marken-Lieferant, unbrauchbar
  als Handlungsgrundlage.* Selten ein falsifizierbares Kriterium (Kursziel,
  Zeithorizont, Invalidierungsmarke); Formulierungen sind meist mit jedem
  Verlauf vereinbar.
- **Titel ignorieren:** A/B-getestete Klickköder, regelmäßig reißerischer als
  der Inhalt und teils gegenläufig zur eigenen Aussage im Video. Dieselbe
  Video-ID lief schon unter zwei Titeln gleichzeitig.
- **Auto-Transkript:** schreibt den Namen oft falsch (»SCR Solutions«, »Alexer
  Schulz«).
- **Ausgewertet in:** [[Marktlage-August-2026]] (Makro, 11.08.2026),
  [[XRP-Analyse-STA-September-2026]] (XRP, 02.09.2026),
  [[BTC-Analyse-STA-September-2026]] (BTC, 05.09.2026).

## xGhozt Prophecies: A Forecast on the Future

- **Was:** TradingView-Indikator, Closed-Source (Pine nicht einsehbar, keine
  API). Liefert eine Saisonalitäts-/Kalenderstatistik nach Wochentag und
  Tagesphase.
- **Nutzung im eigenen System:** Prinzip nachgebaut in
  `Agenten/Handel/xperp/indikatoren.py`, hoch gewichtet ins XPERP-Signal — darf
  dort SuperTrend+EMA überstimmen.
- **Einstufung:** dünne Stichprobe (~7 Kerzen je Wochentag bei 300×4h). Rückblick
  auf schmalem Fenster, kein Backtest. Vor dem Vertrauen in eine gekippte
  Richtung immer `n` lesen.
- **Ausgewertet in:** [[Saisonalitaet-Signal]].

## Swift Algo X

- **Was:** TradingView-Indikator, Invite-Only/Closed-Source (Autor
  swiftalgo). Kombiniert laut Eigenbeschreibung eine Volumen-Drift-Momentum-
  Engine, einen 144er-Parameter-Optimizer und ein 8-Timeframe-Trend-
  Dashboard.
- **Nutzung im eigenen System:** Zwei der drei Bausteine im Prinzip
  nachgebaut (Volumen-Drift-Momentum + vereinfachte Mehrfach-Zeitebenen-
  Bestätigung) in `Agenten/Handel/xperp/indikatoren.py`
  (`volumen_drift()`), hoch gewichtet ins XPERP-Signal mit Vorrang vor der
  Saisonalität. Zusätzlich eigenständige TradingView-Fassung unter
  `Werkstatt/Ausgabe/2026-09-08_Volumen-Drift-Momentum.pine`. Der Parameter-
  Optimizer (Meta-Werkzeug, kein Signal) wurde bewusst weggelassen.
- **Einstufung:** kein Pine-Code einsehbar, nur die auf der Seite
  beschriebene Methodik nachgebaut, nichts kopiert.
- **Ausgewertet in:** [[Volumen-Drift-Signal]].

## Aufnahmekriterium

Eine Quelle kommt hierher, wenn sie **zum zweiten Mal** in eine Auswertung
eingeht — nicht beim ersten Video. Rohquellen (Transkripte) liegen in
`Werkstatt/Projekte/Invest/Quellen/`, Register dort in `Quellen/INDEX.md`.

Verwandt: [[Marktlage-August-2026]], [[XRP-Analyse-STA-September-2026]], [[Saisonalitaet-Signal]]

---
id: 20261007-spur-bewertung
title: Spur-Bewertung
tags: [handel, verbesserer, strategie]
created: 2026-10-07
updated: 2026-10-07
related: [20261006-verbesserer-architektur, 20261007-verbesserer-ausloeser, 20261007-papier-experiment-zyklus]
summary: Metriken und Schwellwerte, nach denen der Verbesserer entscheidet, ob eine Spur schlecht, ineffizient oder verbesserungswürdig ist.
---

# Spur-Bewertung

> Summary: Metriken und Schwellwerte, nach denen der Verbesserer entscheidet, ob eine Spur schlecht, ineffizient oder verbesserungswürdig ist.

## Kontext
Bevor der Verbesserer Parameteranpassungen vorschlägt, muss er wissen, ob die Spur überhaupt
schlecht läuft. Ohne Bewertungslogik wird blind optimiert.

## Details

### Primärmetriken (immer prüfen)

| Metrik | Schlecht wenn | Quelle |
|---|---|---|
| Gewinnrate (Win Rate) | < 45 % über ≥ 30 Trades | Journal |
| Profit-Faktor | < 1,2 | Journal |
| Maximaler Drawdown | > 15 % des Startkapitals | Journal |
| Durchschn. Haltezeit vs. Zeitrahmen | < 1,5× Kerzenbreite | Journal |

### Effizienzmetriken (optional, zeigen wo Potenzial liegt)

| Metrik | Problem wenn | Bedeutung |
|---|---|---|
| Signalfrequenz | < 1 Signal / 3 Tage | Spur ist zu selektiv, kaum Kapitalnutzung |
| Slippage-Quote | > 0,3 % ⌀ pro Trade | Einstiegszeitpunkt zu ungenau |
| Stop-Auslöse-Rate | > 60 % der Verlust-Trades | Stop zu eng oder falscher Platzierung |
| Korrelation mit Benchmark | > 0,85 | Spur fügt keinen Mehrwert gegenüber Buy&Hold |

### Bewertungsintervall
- **Mindestbasis:** 30 abgeschlossene Trades oder 14 Tage — weniger ist statistisch nicht belastbar
- **Kurzauswertung:** nach starkem Ereignis (Momentum, Drawdown-Alarm) auch früher möglich

### Ausgabe
Der Verbesserer gibt pro Spur eine von drei Einschätzungen zurück:
- `OK` — Spur läuft, keine Aktion
- `BEOBACHTEN` — ein Metrik-Warnsignal, nächste Auswertung vorgezogen
- `VERBESSERN` — mindestens zwei Primärmetriken im roten Bereich → Experiment starten

## Related
- [Verbesserer-Architektur](verbesserer-architektur.md) — Kontext: wo Bewertung im Gesamtzyklus liegt.
- [Verbesserer-Auslöser](verbesserer-ausloeser.md) — Weiterführend: wann die Bewertung ausgeführt wird.
- [Papier-Experiment-Zyklus](papier-experiment-zyklus.md) — Folgeschritt: was nach `VERBESSERN` passiert.

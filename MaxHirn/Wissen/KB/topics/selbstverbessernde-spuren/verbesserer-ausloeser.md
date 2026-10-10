---
id: 20261007-verbesserer-ausloeser
title: Verbesserer-Auslöser
tags: [handel, verbesserer, implementierung]
created: 2026-10-07
updated: 2026-10-07
related: [20261006-verbesserer-architektur, 20261007-spur-bewertung, 20261007-papier-experiment-zyklus]
summary: Wann der Verbesserer aktiv wird — zeitgesteuert alle paar Tage oder ereignisgesteuert bei starkem Momentum.
---

# Verbesserer-Auslöser

> Summary: Wann der Verbesserer aktiv wird — zeitgesteuert alle paar Tage oder ereignisgesteuert bei starkem Momentum.

## Kontext
Der Verbesserer soll weder zu träge (Probleme bleiben zu lange) noch zu nervös
(ständige Parameteranpassung destabilisiert die Spur) reagieren. Zwei Auslöser-Typen
decken beide Richtungen ab.

## Details

### Typ 1: Zeitgesteuert (Regelauslöser)

- **Intervall:** alle 3–7 Tage, konfigurierbar per Wache
- **Ablauf:** Routine prüft um feste Uhrzeit, ob seit letztem Lauf genügend neue Trades im Journal liegen (Mindestbasis: 30 Trades oder 14 Tage)
- **Umsetzung:** Cron-Eintrag in `Agenten/Routinen/`, Ergebnis landet als Eintrag im Journal

### Typ 2: Ereignisgesteuert (Momentum-Auslöser)

Ausgelöst, wenn eine der folgenden Bedingungen innerhalb von 24 h eintritt:

| Ereignis | Schwellwert |
|---|---|
| Kursveränderung des Instruments | > ±8 % in 4 h |
| Drawdown der Spur | > 10 % des aktuellen Kapitals |
| 3 Stop-Auslösungen in Folge | innerhalb von 12 h |
| Funding Rate (Perpetuals) | > 0,1 % pro 8 h |

- Momentum-Auslöser startet nur die **Kurzauswertung** (nicht den vollen Experiment-Zyklus)
- Schlägt die Kurzauswertung `VERBESSERN` vor, wird der volle Zyklus manuell bestätigt

### Schutzregel: Abkühlphase
Nach jeder Parameteranpassung gilt eine **Abkühlphase von 48 h**: kein weiterer
Auslöser — auch kein Momentum-Auslöser — wird in dieser Zeit ausgeführt. Verhindert
Über-Optimierung durch aufeinanderfolgende Marktereignisse.

### Konfigurationsort
- Zeitgesteuert: Wachen-Datei der Spur (`wachen.json` / xperp-Wache)
- Momentum-Schwellwerte: `verbesserer/config.yaml` (noch anzulegen)

## Related
- [Spur-Bewertung](spur-bewertung.md) — Voraussetzung: was bei einem Auslöser bewertet wird.
- [Papier-Experiment-Zyklus](papier-experiment-zyklus.md) — Folgeschritt: was nach positivem Auslöser passiert.
- [Verbesserer-Architektur](verbesserer-architektur.md) — Überblick: Gesamtzyklus.

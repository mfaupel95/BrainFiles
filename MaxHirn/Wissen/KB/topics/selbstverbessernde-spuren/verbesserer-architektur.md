---
id: 20261006-verbesserer-architektur
title: Verbesserer-Architektur
tags: [handel, verbesserer, architektur]
created: 2026-10-06
updated: 2026-10-07
related: [20261006-spur-typen, 20261006-llm-als-signal, 20261007-spur-bewertung, 20261007-verbesserer-ausloeser, 20261007-papier-experiment-zyklus]
summary: Aufbau und Ablauf des Verbesserer-Moduls: wöchentliche Vorschlags-Schleife, Bewertung, Übernahme.
---

# Verbesserer-Architektur

> Summary: Aufbau und Ablauf des Verbesserer-Moduls: wöchentliche Vorschlags-Schleife, Bewertung, Übernahme.

## Kontext
Das Modul `Agenten/Handel/verbesserer/` automatisiert die Weiterentwicklung der Handels-Spuren. Stufe 1 adressiert Spur 1 (Kraken); Stufe 1.5 ist spec-abgenommen, Plan ausstehend.

## Details

### Zyklus
1. **Auswertung** — Spur läuft eine Woche; Performance-Metriken werden gesammelt.
2. **Vorschlag** — Verbesserer analysiert die Metriken und schlägt Parameteranpassungen vor.
3. **Bewertung** — Vorschläge werden auf Backtest-Basis oder Papier-Test bewertet.
4. **Übernahme** — Akzeptierte Vorschläge landen in der Wachen-Datei der Spur.

### Kodierung
- Einstiegspunkt: `Agenten/Handel/verbesserer/`
- Spec und Plan: `Werkstatt/` (Übergabe-Dateien)
- Wachen-Datei: `Agenten/Handel/mosaic/wachen.json` (Spur 1) / `Agenten/Handel/xperp/` (Spur 2)

## Related
- [Spurtypen und Implementierung](../strategien-implementierung/spur-typen.md) — Kontext: welche Spuren verbessert werden.
- [LLM als Signalgeber](../llm-signalgeber/llm-als-signal.md) — Erweiterung: LLM kann Vorschlags-Schritt übernehmen.
- [Spur-Bewertung](spur-bewertung.md) — Details: Metriken und Schwellwerte für die Bewertungs-Phase.
- [Verbesserer-Auslöser](verbesserer-ausloeser.md) — Details: wann der Zyklus startet.
- [Papier-Experiment-Zyklus](papier-experiment-zyklus.md) — Details: wie Vorschläge getestet und übernommen werden.

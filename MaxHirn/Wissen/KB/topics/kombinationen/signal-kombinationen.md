---
id: 20261006-signal-kombinationen
title: Signalkombinationen
tags: [handel, kombination, strategie]
created: 2026-10-06
updated: 2026-10-06
related: [20261006-llm-als-signal, 20261006-spur-typen]
summary: Muster für die Verbindung mehrerer Signalquellen zu einem Handelsentscheid.
---

# Signalkombinationen

> Summary: Muster für die Verbindung mehrerer Signalquellen zu einem Handelsentscheid.

## Kontext
Kein einzelnes Signal ist zuverlässig genug. Die Kombination mehrerer unkorrelierter Quellen erhöht die Trefferquote und reduziert Falschsignale.

## Details

### Kombinationsmuster

**1. Voting (Mehrheitsentscheid)**
- N Signale stimmen ab: Long, Short oder Neutral
- Handel nur bei Mehrheit (z.B. ≥ 2 von 3 stimmen zu)
- Vorteil: robust, leicht zu debuggen

**2. Gewichtetes Scoring**
- Jedem Signal ein Gewicht (historische Trefferquote)
- Score-Summe über Schwellwert → Handeln
- Vorteil: lernt aus Vergangenheit; passt zum Verbesserer-Zyklus

**3. Filter + Trigger**
- Ein Signal ist Trigger (löst den Trade aus), ein anderes ist Filter (verhindert Trades gegen den Trend)
- Beispiel: LLM-Signal als Trigger, gleitender Durchschnitt als Trendfilter
- Vorteil: weniger Trades, höhere Qualität

**4. Kaskade**
- Erst grober Zeitrahmen (1h-Chart), dann feiner (5m-Chart) bestätigt
- Handeln nur wenn beide Ebenen übereinstimmen
- Vorteil: vermeidet Counter-Trend-Trades auf kleinen Zeitrahmen

### Datenfluss im Code
1. Jede Signalquelle gibt `{"signal": ..., "confidence": ...}` zurück
2. Kombinator (`kombinierer.py` o.ä.) sammelt alle Quellen
3. Ausgabe: einheitliches Signal an `handeln.py`

## Related
- [LLM als Signalgeber](../llm-signalgeber/llm-als-signal.md) — LLM als eine der kombinierten Quellen.
- [Spurtypen und Implementierung](../strategien-implementierung/spur-typen.md) — wo Kombinationen in den Spuren eingebaut werden.

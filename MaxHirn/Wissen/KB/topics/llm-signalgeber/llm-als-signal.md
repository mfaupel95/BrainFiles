---
id: 20261006-llm-als-signal
title: LLM als Signalgeber
tags: [handel, llm, strategie]
created: 2026-10-06
updated: 2026-10-07
related: [20261006-verbesserer-architektur, 20261006-signal-kombinationen, 20261007-prompt-design-ohlcv]
summary: Konzept: wie ein LLM Kursdaten interpretiert und daraus Handelssignale erzeugt.
---

# LLM als Signalgeber

> Summary: Konzept: wie ein LLM Kursdaten interpretiert und daraus Handelssignale erzeugt.

## Kontext
Klassische regelbasierte Signale (Moving Average, RSI, Breakout) lassen sich durch ein LLM ergänzen oder ersetzen: das Modell liest Kursdaten und gibt eine Richtungsentscheidung zurück.

## Details

### Eingaben
- OHLCV-Daten als Text oder JSON (Kerzenreihe der letzten N Bars)
- Optional: Orderbuch-Snapshot, Funding Rate, offene Positionen
- Optional: Nachrichtenschlagzeilen / Sentiment

### Ausgabe
- Strukturiertes JSON: `{"signal": "long"|"short"|"neutral", "confidence": 0–1, "reasoning": "..."}`
- Reasoning-Feld ist auswertbar für den Verbesserer (erklärt, warum der Vorschlag gemacht wurde)

### Modellwahl
- Lokale Modelle (Modelle/-Verzeichnis) für niedrige Latenz und Datenschutz
- Cloud-Modelle (Claude API) für komplexere Kontextfenster

### Risiken
- Halluzination: Modell kann plausible, aber falsche Muster konstruieren → Konfidenz-Schwellwert nötig
- Latenz: API-Aufruf kann Einstiegszeitpunkt verschieben → Vorab-Berechnung oder asynchron

## Related
- [Verbesserer-Architektur](../selbstverbessernde-spuren/verbesserer-architektur.md) — Anwendung: LLM im Vorschlags-Schritt des Verbesserers.
- [Signalkombinationen](../kombinationen/signal-kombinationen.md) — Weiterführend: LLM-Signal mit regelbasierten Signalen kombinieren.
- [Prompt-Design für OHLCV-Input](prompt-design-ohlcv.md) — Details: wie Kursdaten serialisiert und eingerahmt werden.

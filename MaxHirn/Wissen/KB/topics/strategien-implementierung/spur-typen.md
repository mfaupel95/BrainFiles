---
id: 20261006-spur-typen
title: Spurtypen und Implementierung
tags: [handel, architektur, implementierung]
created: 2026-10-06
updated: 2026-10-06
related: [20261006-verbesserer-architektur, 20261006-signal-kombinationen]
summary: Überblick der aktiven Spuren (Spur 1 Kraken, Spur 2 OKX-Perpetuals) und ihrer Code-Strukturen.
---

# Spurtypen und Implementierung

> Summary: Überblick der aktiven Spuren (Spur 1 Kraken, Spur 2 OKX-Perpetuals) und ihrer Code-Strukturen.

## Kontext
Das Handelssystem arbeitet mit mehreren unabhängigen Spuren, die unterschiedliche Börsen und Instrumenttypen bedienen.

## Details

### Spur 1 — Kraken (Spot/Futures)
- **Einstiegspunkt:** `Agenten/Handel/scanner/handeln.py`
- **Wachen:** `Agenten/Handel/mosaic/wachen.json`
- **Start:** `omnitrade.cmd start`
- **Verbesserer:** aktiv (Stufe 1, wöchentlicher Zyklus)

### Spur 2 — OKX-Perpetuals (xperp)
- **Einstiegspunkt:** `Agenten/Handel/xperp/handeln.py`
- **Modi:** `--vorschau | --papier | --live | --wachen`
- **Kernlogik:** `Agenten/Handel/xperp/bot.py`
- **Trailing-Stop:** `Agenten/Handel/trailing.py`, verdrahtet in `xperp/handeln.py`
- **Tests:** `Agenten/Handel/xperp/tests/` (unittest)

### Gemeinsame Infrastruktur
- **Leitstand:** `Agenten/Handel/leitstand_backtests.py` — Backtesting-Übersicht
- **Replay:** `Agenten/Handel/replay.py` — Kursdaten-Replay für Tests
- **OKX-Historie:** `Agenten/Handel/historie_okx.py`
- **Tracking:** `Agenten/Handel/tracking.py`

## Related
- [Verbesserer-Architektur](../selbstverbessernde-spuren/verbesserer-architektur.md) — Verbesserer operiert auf diesen Spuren.
- [Signalkombinationen](../kombinationen/signal-kombinationen.md) — Wie Signale innerhalb einer Spur kombiniert werden.

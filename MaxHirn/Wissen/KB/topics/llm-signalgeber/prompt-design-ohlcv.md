---
id: 20261007-prompt-design-ohlcv
title: Prompt-Design für OHLCV-Input
tags: [llm, handel, implementierung]
created: 2026-10-07
updated: 2026-10-07
related: [20261006-llm-als-signal, 20261006-signal-kombinationen]
summary: Wie OHLCV-Kerzen in einen LLM-Prompt überführt werden und welche Strukturen zuverlässige Signale liefern.
---

# Prompt-Design für OHLCV-Input

> Summary: Wie OHLCV-Kerzen in einen LLM-Prompt überführt werden und welche Strukturen zuverlässige Signale liefern.

## Kontext
Das Modell sieht keine Charts — es liest Text. Wie die Kursdaten serialisiert und
eingerahmt werden, bestimmt, ob das Modell ein nützliches Signal oder Rauschen zurückgibt.

## Details

### Datenformat

**Kompaktes CSV (bevorzugt für kleine Kontextfenster)**
```
time,open,high,low,close,volume
2026-10-06T22:00,62100,62450,61900,62300,18.4
2026-10-06T22:05,62300,62510,62200,62410,12.1
...
```
- Zeitstempel als ISO-8601 (UTC), Preis in der Kurswährung, Volumen in Basiswährung
- Keine zusätzlichen Indikatoren im CSV — das Modell berechnet sie implizit oder du übergibst sie separat

**Umfang:** 20–50 Kerzen reichen für kurzfristige Signale; mehr als 200 erhöhen Latenz
ohne messbare Qualitätssteigerung (empirisch: ab ~100 Kerzen sinkt die Konsistenz)

### Prompt-Struktur

```
[System]
Du bist ein quantitativer Handelsassistent. Analysiere die OHLCV-Daten und gib
eine Handelsentscheidung im vorgegebenen JSON-Format zurück. Sei konservativ:
im Zweifel neutral.

[User]
Zeitrahmen: 5-Minuten-Kerzen, Instrument: BTC/USDT
Aktuelle Position: keine

OHLCV:
<CSV-Block>

Antworte ausschließlich mit:
{"signal": "long"|"short"|"neutral", "confidence": 0.0–1.0, "reasoning": "<1 Satz>"}
```

### Wichtige Prompt-Regeln
- **JSON-Only erzwingen:** Kein Freitext außerhalb des JSON — sonst muss geparst werden
- **Kontext mitgeben:** Position, Zeitrahmen, Instrument — das Modell hat keine Zustandsspeicherung
- **Reasoning verlangen:** Der Satz im `reasoning`-Feld ist auswertbar für den Verbesserer
- **Temperatur 0:** Bei API-Aufruf `temperature=0` setzen für reproduzierbare Ausgaben

### Ergänzende Inputs (optional, nach Nutzen)
| Input | Wann sinnvoll |
|---|---|
| RSI / MACD als Extra-Zeile | Wenn das Modell lokale Modelle < 7B sind |
| Funding Rate | Nur bei Perpetuals (Spur 2) |
| Orderbook-Imbalance | Scalping auf 1m-Zeitrahmen |
| Letzter Trade der Spur | Verhindert Flip-Flop-Signale |

### Häufige Fehler
- **Zu viele Kerzen:** Kontext wird geflutet, Modell fokussiert auf frühe Daten
- **Kein JSON-Schema:** Modell antwortet prosaisch → `json.loads()` wirft Exception
- **Preis ohne Kontext:** Absolute Preiszahlen ohne Zeitstempel sind für das Modell sinnlos
- **Fehlende Einheit:** `volume: 18.4` ist mehrdeutig — immer BTC oder USDT spezifizieren

## Related
- [LLM als Signalgeber](llm-als-signal.md) — Überblick: Eingaben, Ausgaben, Modellwahl.
- [Signalkombinationen](../kombinationen/signal-kombinationen.md) — Weiterführend: wie dieses Signal mit anderen kombiniert wird.

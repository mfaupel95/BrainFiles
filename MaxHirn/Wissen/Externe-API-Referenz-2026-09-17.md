---
id: 20260917-externe-api-referenz
title: 'Externe API-Referenz (public-apis-Liste) — Handel-relevante Fundstellen'
tags: [handel, ki-agenten]
created: 2026-09-17
updated: 2026-09-17
related:
  - id: 20260902-analyse-quellen
summary: 'Am 17.09.2026 angehängte public-apis/public-apis-README (600+ öffentliche APIs, Kategorie-Übersicht) als Nachschlagewerk erfasst; Standouts mit Bezug zu bestehenden Handelsspuren herausgefiltert statt die ganze Liste zu duplizieren.'
---

# Externe API-Referenz — public-apis-Liste

Max hat am 17.09.2026 das README des GitHub-Repos
[public-apis/public-apis](https://github.com/public-apis/public-apis)
angehängt — eine von der Community kuratierte Liste öffentlicher APIs über
alle Fachgebiete (Tiere bis Wetter). Die Liste selbst wird **nicht kopiert**
(sie ändert sich laufend, Original bleibt die Quelle); diese Notiz hält nur
fest, wo sie zu finden ist und welche Einträge mit Bezug zu laufenden
Handelsspuren auffielen.

## Fundstellen mit Bezug zu bestehenden Spuren

| API | Auth | Bezug |
|---|---|---|
| [DefiLlama](https://defillama.com/docs/api) | keine | TVL, Coin-Preise, Volumen, Yields — offen, könnte `moondev_marktlage`/`moondev_listingarb` um DeFi-Breite ergänzen |
| [Hyperliquid Market Data](https://rapidapi.com/theliminalguy/api/hyperliquid-market-data-oi-funding-open-interest) | `apiKey` | OI/Funding/cross-venue predicted rates — `moondev_funding` liest Funding heute direkt über die Bot-Funktion `nice_funcs_hl.get_funding_rates()`, diese API wäre ein zweiter, unabhängiger Datenweg zur Gegenprobe |
| [PumpFunData](https://pumpfundata.com/docs) | `apiKey` | Historische Pump.fun/PumpSwap-Swaps als stündliche Parquet-Dateien — `kopier` verfolgt aktuell die Top-10 der Pump.fun-PnL-Rangliste live; diese API liefert die Historie dazu für Backtests |
| [Mempool](https://mempool.space/api) | keine | Bitcoin-Mempool/Gebühren — bisher ungenutzt, für keine Spur zwingend, aber kostenlos und stabil |
| [Messari](https://messari.io/api) | keine | Breite Krypto-Metadaten, Alternative/Ergänzung zu CoinGecko (das `moondev_*` bereits nutzt) |
| [FRED](https://fred.stlouisfed.org/docs/api/fred/) | `apiKey` | US-Makrodaten — passt zu `Wissen/Marktbriefing.md`/Marktlage-Notizen, keine Handelsspur direkt |

Keine dieser APIs ist verdrahtet. OKX/Kraken/CoinGecko decken den laufenden
Bedarf; die Liste ist reiner Vormerk für den Fall, dass eine Spur einen
zweiten Datenweg zur Gegenprobe braucht (Muster: Bedingung, dass ein
Signal aus zwei unabhängigen Quellen bestätigt wird, bevor es gewichtet
wird — wie bereits bei CVD/Saisonalität/Volumen-Drift im XPERP-Signal).

## Sonstiges aus dem Anhang

Zwei weitere angehängte READMEs am selben Tag (`README-3.md` =
moon-dev-ai-agents, `README-4.md` = dieses public-apis) — moon-dev-ai-agents
ist bereits vollständig in [[Moon-Dev-Agenten]] erfasst (46 Agenten,
4 laufende Spuren, Sperrgründe A–D), keine neue Information daraus.

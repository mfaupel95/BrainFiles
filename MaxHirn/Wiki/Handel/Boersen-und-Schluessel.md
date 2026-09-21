---
id: 20260921-boersen-und-schluessel
title: 'Handel — Boersen und Schluessel'
tags: [handel, zugaenge]
created: 2026-09-21
updated: 2026-09-21
related: ['[[Handel/Gates-und-Freigabe]]', '[[Wissen/Zugaenge]]']
summary: 'Welcher Schluesselsatz zu welcher Boerse und welcher Spur gehoert, was die OKX-Fehlercodes bedeuten — ohne jeden Schluesselwert.'
---

# Boersen und Schluessel

**Hier stehen keine Werte und keine Wertteile.** Werte liegen ausschliesslich in
`Wissen/Zugaenge.md` (Stufe 0: nie lesen, nie ausgeben, nie protokollieren) bzw. in den
Windows-Benutzervariablen.

## OKX

- Max' Konto ist **EEA**: `OKX_BASE=https://eea.okx.com`. NICHT `www.okx.com`, NICHT
  `my.okx.com` (= Portal-Host).
- **Je Spur ein anderer Variablensatz** — die falsche Variable zu aendern wirkt nicht:
  `xperp` und `mosaic` lesen `OKX_API_KEY` / `OKX_SECRET` / `OKX_PASSPHRASE`;
  `scanner` liest `OKX_LIVE_API_KEY` / `…_SECRET` / `…_PASSPHRASE`.
  Die okx-Module lesen die Werte mit Registry-Rueckfall (der MCP-Client reicht
  Benutzervariablen **nicht** an Serverprozesse durch).
- `OKX_SIMULATED=1` erzwingt den Papier-/Demo-Modus — fuer echtes Live muss die Variable weg.
- **Margin ist USDC, nicht USDT.** Gemessen: `/api/v5/account/positions?instType=FUTURES`
  zeigt `mgnMode=isolated, ccy=USDC`; eine Abfrage mit `ccy=USDT` liefert eine **leere** Liste
  — auf dem Konto gibt es gar kein USDT (USDC ~1001 eq / ~255 frei, EURC 15,99, Kleinstreste).
  `xperp/okxf.guthaben_usdt()` lieferte deshalb 0.0 und gibt bei leerem USDT jetzt das freie
  USDC zurueck. **Wer eine Finanzierungsaussage trifft, prueft die Margin-Waehrung der
  POSITION, nicht den Namen der Waehrung im Kopf.**

### Fehlercode 50101

`APIKey does not match current environment` = der Schluessel gehoert zu einem anderen Host
oder einer anderen Umgebung: EEA vs. global, Demo-Key, oder fehlende IP-Whitelist.
**Pruefen mit einem signierten LESEaufruf (`guthaben`, `offene_orders`) gegen den
Registry-Host** — nie gegen einen geratenen Host. Stand 21.09.2026 lieferte der xperp-Satz
50101; echte Orderfaehigkeit ist damit ungeklaert, obwohl das Konto den Handel zulaesst.

## Kraken

- Zugang ueber `Agenten/Handel/kraken/kraken.py`; Variablen `KRAKEN_*`. Ordern mit
  `echt=True` moeglich, `validate=True` rechnet nur durch (Trockenlauf).
- Kraken-Pro-Abo: Kauf+Verkauf bis 10.000 EUR Monatsvolumen gebuehrenfrei → `gebuehr_taker: 0`
  in `kraken/wachen.json`. Siehe [[Handel/Kosten-und-Bedingungen]] fuer das Risiko daran.
- **Zweite Boerse fuer dieselbe Spur** (Muster, 21.09.2026): `mosaic/kraken_spot.py` stellt
  dieselben Funktionsnamen bereit wie `okx_spot.py` und ruft dahinter `kraken/kraken.py`;
  `handeln.venue_binden(w)` waehlt das Modul ueber das Feld `boerse` (Standard okx) und bindet
  die Test-Seams neu — **VOR** der ersten Sperrenpruefung. Paarabildung EINMAL in
  `kraken_spot.PAARE` (BTC-USDC→XXBTZEUR, ETH-USDC→XETHZEUR, SOL-USDC→SOLEUR); unbekanntes
  Paar = `ValueError` (nie still ersatzweise handeln). Die wachen-Instrumente bleiben in
  OKX-Namen, damit Kerzen und Papierzweig unberuehrt bleiben.

## Deribit

`iv_waelle` liest die oeffentlichen Deribit-Endpunkte (Daten, kein Schluessel). Gebuehr in
der eigenen `wachen.json` auf 0,05 % — bewusst NICHT 0.

## OKX-Optionsdaten (oeffentlich, ohne Schluessel)

- `/api/v5/public/open-interest?instType=OPTION&uly=BTC-USD` — `oi`/`oiCcy`/`oiUsd` JE OPTION
  in EINEM Aufruf.
- `/api/v5/public/opt-summary?uly=BTC-USD` — `markVol` (= IV) je Option.
- **Nicht verfuegbar:** OI ueber Rubik (`/rubik/stat/option/open-interest-volume-strike` →
  `expTime`-Fehler in jedem probierten Format) und OI in `opt-summary`.
- Strike/Verfall/Art stehen in der `instId` (`BTC-USD-260925-79000-C`). OKX-Verfall ist
  **08:00 UTC**. Spot ueber `okx.letzter_kurs(inst)` — die Funktion heisst NICHT `okx.kurs()`.
- `/api/v5/market/candles` gibt oeffentlich nur **1440 Stundenkerzen** (60 Tage), egal was man
  anfordert.

## Kraken-Flotte (nicht verwechseln)

`kraken` (Spot-Spur, EUR) · `nautilus_kraken` / `nautilus_kraken_futures` (Papier-Arme,
nautilus-venv) · `moondev_marktlage.live_kraken.py` (abgetrennter Live-Zweig, nicht verdrahtet)
· `kraken_agent` aus `Werkstatt/Repos/moon-dev-ai-agents` (Fremd-Bot, eigener Treiber
`MaxHirn-MoonDev-Dauerlauf`).
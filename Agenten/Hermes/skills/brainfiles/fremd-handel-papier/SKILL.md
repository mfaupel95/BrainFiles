---
name: fremd-handel-papier
description: "Use when Fremd-Handelswerkzeuge (kraken-cli, OKX Agent Trade Kit) im Papier-/Demo-Modus genutzt werden."
version: 0.1.0
author: Hermes
license: MIT
category: brainfiles
platforms: [windows]
metadata:
  hermes:
    tags: [Handel, Papier, Demo, Kraken, OKX, MCP]
    related_skills: [fremdrepos-signal, handel-spuren, okx-live-anbinden, okx-trading-schleifen, mcp-sync]
---

# Fremd-Handelswerkzeuge: nur Papier und Demo

Zwei Forks unter `Werkstatt/` sind als MCP an Hermes angeschlossen. Beide
handeln hier **nie echt**: Papier (Kraken) und Demo (OKX). Echtes Geld bewegt
weiterhin nur die Kette aus `okx-live-anbinden` und den Wachen in `Agenten/Handel/`.

## When to Use

- „teste das auf Papier", „Papierhandel", „Demo-Order", „probier die Strategie an der Boerse"
- ein Signal aus einer Fremd-Spur soll gegen echte Kurse ohne Risiko laufen
- Markt-/Orderbuchdaten brauchen ein zweites, unabhaengiges Werkzeug

## Prerequisites

- **kraken-papier** (MCP, an): `Werkstatt/kraken-cli/target/release/kraken.exe mcp`.
  Standarddienste Markt, Konto lesen, Papier. Futures-Papierkonto 10 000 USD
  initialisiert (`kraken futures paper init`). Neu bauen: `cargo build --release`.
- **okx-agentkit** (MCP, **an, schreibend, nur DEMO**): Starter
  `Agenten/MCP-Server/okx-agentkit/start-demo.cmd` bildet `OKX_DEMO_API_*` im Kindprozess
  auf die erwarteten Namen ab (Live-Schluessel greift nie; `--demo --site eea`).
  **Nur Spot** (z. B. `BTC-USDC`): Swap/Perps sind im EWR-Demo gesperrt (Fehler 50124).
  Ablauf fuer eine Demo-Order: Signal -> `Agenten/Handel/fremd_demo.py` `plane()` rechnet
  Menge (quote_ccy), Stop und Limits und lehnt short/Papier/Tor-zu ab; erst dann
  `spot_place_order` mit genau diesen `args`. Nach dem Fill Position im Demo-Buch halten;
  `flat` = Verkaufsorder plus offenen Stop stornieren (`spot_cancel_algo_order`, mit `instId`).
  **Ausfuehrungsschritt (Hermes):** 1) `python Agenten/Handel/fremd_signale/demo_plan.py --vormerken`
  (Tor zu = nichts). 2) Je JSON-Zeile mit `ok:true` genau `plan.tool` mit `plan.args` aufrufen,
  nie abgeaendert. 3) Antwort `sCode` != 0 oder nicht gefuellt -> `demo_plan.py --verwerfen <instrument>`.
  4) Bei `aktion: schliessen` nach dem Verkauf offene Stops per `spot_get_algo_orders` suchen,
  mit `spot_cancel_algo_order` (`instId`, `algoId`) stornieren und `--verwerfen <instrument>`.
  5) Ergebnis (Fill-Preis, Menge, Stop) in den Topic Handel melden. Nie `mode=live`, nie Swap.
  Neu bauen: `pnpm install --frozen-lockfile && pnpm build` im Repo.

## How to Run

Werkzeuge erscheinen als `kraken_*` bzw. `okx_*`. Reihenfolge fuer einen Test:

1. Markt lesen (`kraken_ticker`, `kraken_ohlc`).
2. Papier-Order setzen, Stop **immer** mit (Hausregel Stop-Pflicht).
3. Ergebnis ins Journal der Spur, nicht in eine Parallelablage.

CLI-Gegenprobe ohne MCP: `kraken futures paper status -o json`.

## Pitfalls

- **Nie** `-s all` oder `--allow-dangerous` bei kraken, **nie** `--live` bei OKX.
- Das Profil `okx-prod` in `~/.okx/config.toml` ist Live; `default_profile` nicht
  anfassen, sonst springt der Live-Pfad der Spuren um.
- Keys nie ausgeben, nur Vorhandensein und Laenge.
- Papier ist kein Beweis fuer Live: Slippage und Gebuehren sind simuliert.
- **Vor dem Live-Schalten eines per-Block/per-Tick On-Chain-Bots die Gas-Oekonomie messen, nicht schaetzen.** Blockrate zweimal `eth_blockNumber` im Abstand von 10 s (Monad: ~3,4 Bloecke/s = 12 240/h), Gas/Block aus Limit x Basis-Fee, dann Burn-Rate = Gas/Block x Bloecke/h gegen die Wallet-Balance stellen. Ein Wallet kann weniger wert sein als zwei Stunden Gas (691 MON = ~17 $ gegen ~437 MON/h = ~10,80 $/h) — Live-Schalten ist dann wirtschaftlich sinnlos, egal ob die Strategie gewinnt. Der README-Beispielwert des Bots (0,0357 MON/Block) mal der echten Blockrate ist die Zahl, die entscheidet. Details: `references/monad-kuru.md`.

## Verification

- `Agenten/mcp-sync-check.ps1` zeigt `OK kraken-papier` (und `okx-agentkit` nach dem Einschalten).
- `kraken futures paper status -o json` antwortet ohne `error`.

## Delegierung
Telegram-Topic **Handel** ist mit dem Skill `fremdrepos-signal` verdrahtet (Signal-Schema, Stale-Verwurf, Gate). Bot-Profile: `kraken-cli` (MCP `kraken-native`, an) und `agent-trade-kit` (MCP `okx-agentkit`, Demo, schreibend). Dieser Skill ist die Werkzeug-Seite, `fremdrepos-signal` der Vertrag; das Schema nicht hier duplizieren.

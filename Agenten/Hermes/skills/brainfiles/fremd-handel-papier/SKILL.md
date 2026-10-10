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

Zwei Forks unter `Werkstatt/Repos/` sind als MCP an Hermes angeschlossen. Beide
handeln hier **nie echt**: Papier (Kraken) und Demo (OKX). Echtes Geld bewegt
weiterhin nur die Kette aus `okx-live-anbinden` und den Wachen in `Agenten/Handel/`.

## When to Use

- „teste das auf Papier", „Papierhandel", „Demo-Order", „probier die Strategie an der Boerse"
- ein Signal aus einer Fremd-Spur soll gegen echte Kurse ohne Risiko laufen
- Markt-/Orderbuchdaten brauchen ein zweites, unabhaengiges Werkzeug

## Prerequisites

- **kraken-papier** (MCP, an): `Werkstatt/Repos/kraken-cli/target/release/kraken.exe mcp`.
  Standarddienste Markt, Konto lesen, Papier. Futures-Papierkonto 10 000 USD
  initialisiert (`kraken futures paper init`). Neu bauen: `cargo build --release`.
- **okx-agentkit** (MCP, **aus**): `Werkstatt/Repos/agent-trade-kit/packages/mcp/dist/index.js`
  mit `--demo --profile demo`. Einschalten erst, wenn in `~/.okx/config.toml` ein
  Profil `demo` (`demo = true`, Demo-API-Key) existiert; dann in Manifest und
  `Hermes/config.yaml` `enabled: true`, `mcp-sync-check.ps1` laufen lassen.
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

## Verification

- `Agenten/mcp-sync-check.ps1` zeigt `OK kraken-papier` (und `okx-agentkit` nach dem Einschalten).
- `kraken futures paper status -o json` antwortet ohne `error`.

## Delegierung
Telegram-Topic **Handel** ist mit dem Skill `fremdrepos-signal` verdrahtet (Signal-Schema, Stale-Verwurf, Gate). Bot-Profile: `kraken-cli` (MCP `kraken-native`, an) und `agent-trade-kit` (MCP `okx-agentkit`, aus bis Demo-Profil). Dieser Skill ist die Werkzeug-Seite, `fremdrepos-signal` der Vertrag; das Schema nicht hier duplizieren.

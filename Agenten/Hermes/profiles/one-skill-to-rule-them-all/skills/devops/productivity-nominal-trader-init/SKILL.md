---
name: productivity-nominal-trader-init
description: "Use for installs/configs/reviews of crypto trading agents."
version: 0.1.0
author: Hermes Agent
license: MIT
platform: [windows]
---

# productivity-nominal-trader-init

Use when setting up a crypto trading engine/agent (e.g. Nautilus) as a separate automation with Paper-first and Live only on explicit command.

## Procedure
1) Verify install state (import + version).
2) Set user gates: Paper-only first; Live blocked until explicit go-live.
3) Build exact exchange mapping from user-provided instrument IDs; never guess symbol formats.
4) Create minimal configs that match the engine’s typed schema; keep configs secrets-free.
5) Validate configs by starting in “feed-only” mode (no orders / paper only).
6) Apply strategy as a second step, using the user’s risk-rule parameters (e.g. Hebel-Deckel, stop ATR, grid steps).
7) Verify with read-only logs/status; if you hit schema errors like “unknown field”, inspect the engine’s config types and fix the specific key, not randomness.
8) Verify every on-chain address in trading/exclude/never-trade lists before trusting them. Solana: POST `getAccountInfo` (encoding jsonParsed) to `https://api.mainnet-beta.solana.com` — result `value: null` means the account does not exist.

## Pitfalls
- Typed-schema errors: treat them as a config contract mismatch; don’t iterate by trial-and-error.
- Instrument IDs: case/spacing matters; validate each symbol.
- Exclude/never-trade lists are safety gates: a swapped or mistyped token address silently un-excludes the real asset (and gates a non-token instead) while the list still looks populated. Verify each address on-chain; `getAccountInfo` → `null` means the protection is gone, and a config diff that touches such a list is a safety review, not a cosmetic one.
- Paper vs execution: never assume “paper” means “no orders”; confirm the engine’s execution mode.


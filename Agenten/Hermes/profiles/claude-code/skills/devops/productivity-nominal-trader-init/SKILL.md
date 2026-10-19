---
name: productivity-nominal-trader-init
description: "Use for installs/configs of crypto trading agents."
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

## Pitfalls
- Typed-schema errors: treat them as a config contract mismatch; don’t iterate by trial-and-error.
- Instrument IDs: case/spacing matters; validate each symbol.
- Paper vs execution: never assume “paper” means “no orders”; confirm the engine’s execution mode.
- A limit that looks wrong is usually deliberate — read the config’s own justification before “harmonizing”. Caps are often not the quantity they appear to be: a `max_*_usd` can be the NOMINAL value of the smallest tradable contract (large on purpose), and an elevated per-position risk can be an explicit user decision. Read the note/comment keys next to the value (`_…_vermerk`, `#`, adjacent docstring) and leave documented values alone; harmonizing them to a felt average breaks a working setup. Same discipline for anything derived from contract size — take it from the exchange’s own instrument list, never from a similar-looking value.
- Verify running state with the platform’s process/task APIs, not a POSIX shell. On Windows a `ps aux` under MSYS shows no native processes at all, so “nothing is running” is an unfounded claim; query the process list (with command line and parent PID) and the scheduler/task state, and treat a lock file as a lock, not as health.


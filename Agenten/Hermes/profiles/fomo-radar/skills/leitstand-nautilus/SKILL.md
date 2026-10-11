---
name: leitstand-nautilus
description: "Use when working on Leitstand Nautilus/Prozesse tabs."
author: Hermes Agent
version: 1.0.0
---

# Leitstand Nautilus & Prozesse

The Leitstand (`leitstand.py`) is a Tkinter notebook with 8 tabs. It never trades live — it only observes and starts/stops child processes. This skill covers the Nautilus tab, the Prozesse tab, and how to bind the trading repos in `Agenten/Handel/`.

## When to Use

Load when modifying `leitstand_nautilus.py`, `leitstand_prozesse.py`, or adding new trading repos as tabs. The repos all live under `C:\Users\faupe\Documents\BrainFiles\Agenten\Handel\`.

## Repo Map (Agenten/Handel/)

| Repo | Type | Entry point | Leitstand |
|------|------|-------------|----------|
| `nautilus/` | OKX DEMO Node (Tkinter GUI) | `nautilus_gui.py` → `NautilusFrame` | ✅ Nautilus tab |
| `nautilus_kraken/` | Kraken Paper Node (Spot/Futures) | `run_kraken_paper_node.py` | ✅ Prozesse tab |
| `nautilus_emacross/` | EMA-Cross Strategy (Kraken) | `handeln.py` | ❌ |
| `nautilus_rc5/` | Kraken Order Test | `kraken_order_test_rc5.py` | ❌ |
| `omnitrade/` | Rust Handelsagent (OKX DEMO) | `omnitrade_lauf.py` / `omnitrade.cmd` | ✅ Prozesse tab |
| `omnitrade_futures/` | Omnitrade + Kraken Futures x7 | `handeln.py` | ❌ |
| `omniquant/` | GUI for Papierspur | `gui.py` | ✅ Omniquant tab |
| `freqtrade/` | Freqtrade Bots | `freqtrade_bridge.py` | ✅ FreqTrade tab |
| `xperp/` | XPerp Trading | `handeln.py` | ❌ |
| `orb/` | ORB Trading | `handeln.py` | ❌ |
| `orbk/` | ORB Trading (Kraken) | `handeln.py` | ❌ |
| `kraken/` | Kraken Trading | `handeln.py` | ❌ |
| `robinhood_radar/` | Robinhood Radar (Paper) | `handeln.py` | ❌ |

## Nautilus Tab Architecture

`NautilusReiter` (in `leitstand_nautilus.py`) is a thin wrapper:
1. Calls `nautilus_gui_laden()` — imports `nautilus_gui` module from `Agenten/Handel/nautilus/`
2. If import fails: shows explanation text instead of crashing (the Leitstand must survive a missing wheel)
3. If success: embeds `modul.NautilusFrame(self)` as the tab content

`NautilusFrame` is a `ttk.Frame` — no window management (title/geometry/minsize/protocol belong to the host).

## Prozesse Tab Architecture

`ProzessReiter` (in `leitstand_prozesse.py`) manages OS-level child processes:
- Each process: `laeuft()`, `starten()`, `stoppen()` + `read_only` flag
- Processes survive Leitstand close (`CREATE_NEW_CONSOLE`)
- PID files: `*.pid` (first field = PID, second = timestamp)
- Quote-only nodes strip API keys from child env

## Adding a New Repo to Prozesse

1. Add a class with `laeuft()`, `starten()`, `stoppen()` to `leitstand_prozesse.py`
2. Add it to the `PROZESSE` list
3. The UI auto-builds `_ProzessZeile` for each entry

## Adding a New Repo as Tab

1. Create `leitstand_<name>.py` with a `ttk.Frame` subclass
2. Add to `REITER` list in `leitstand.py`
3. Add to `TAKT_SICHTBAR` if it needs periodic refresh
4. Add keyboard shortcut if needed (Ctrl+1..8)

## Always-on Rules

- **Fail soft**: a missing venv, missing nautilus_trader, or missing keys must NEVER crash the Leitstand
- **No live trading**: the Leitstand is observation-only. Child processes decide their own trading mode
- **No secrets in code**: API keys come from env vars, never hardcoded
- **Read-only by default**: new repos start observation-only until explicitly wired to a trading path
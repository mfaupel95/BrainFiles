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
8) Before the go-live flip, confirm WHICH copy of the repo the running process uses and that only ONE bot will touch the account.
9) After the flip, verify the first order on-chain (tx receipt status + gasUsed), not just the log line.

## Pitfalls
- Typed-schema errors: treat them as a config contract mismatch; don’t iterate by trial-and-error.
- Instrument IDs: case/spacing matters; validate each symbol.
- Paper vs execution: never assume “paper” means “no orders”; confirm the engine’s execution mode.
- Multiple repo copies: a parallel session can clone the same repo into a second path (e.g. `O:\Werkstatt 2\...`) with its own branch, and the running bot may use THAT copy while you edit the one you think is live. Before going live, identify the active copy by the mtime of its state/events file (the one still being written) and the running process's cwd/branch — never assume the copy you edited is the one that runs. Two bots on one account = double orders.
- Live with a mock/deterministic model is an ORDER-PATH TEST, not a real strategy. A `MODEL=mock` stand-in (momentum + noise) proves the order path works but makes no real decisions. Say so plainly before flipping live; real strategy needs the real model + its API key.
- Gas budget after margin deposit: a large startup margin deposit (e.g. 600 MON into Kuru) can leave the wallet nearly empty of gas. Check the wallet balance AFTER the deposit math, not before — a too-generous deposit starves the bot of gas within ~2 h. The top-up itself then fails at the next start with `INSUFFICIENT_FUNDS` (the bot wants to deposit the difference to MARGIN_MON but the wallet can't cover it). Fix: set MARGIN_MON BELOW the current on-chain margin so no top-up deposit is needed — the bot only deposits, never withdraws, so a margin already above the target starts clean. Same logic applies to the QUOTE asset: a too-high MARGIN_USDC target only deposits "what is there", which is no substitute for funding the wallet with the quote token.
- Funding: check the wallet holds the QUOTE asset too, not just the gas token. A 0.01 WETH order at ~2423 needs ~24 USDC of margin; if the wallet has only MON (gas), the bot is permanently "cap or funds on both sides" and NEVER posts. The MARGIN_USDC top-up deposits "what is there" and silently leaves the bot unfunded — compare against the trade size × ask before flipping live.
- The real running cost is GAS, not the model API. A model call is ~0.00003 USD (a few hundred tokens × a per-MILLION-token price); gas on a fast chain is ~1-2 USD/h. Do not misread per-MILLION-token pricing as per-thousand — that is a factor-300 error that makes the model look like the cost driver when it is noise. Size the budget on gas, and treat the model fee as negligible.
- Gas-heavy chains (Monad ~3.4 blocks/s): posting a post-only order every block burns the wallet fast (~0.035 MON/order ≈ 437 MON/h). Add a gas saver: only post when the mid moved >= N bps since the last post OR after N blocks, keeping the resting order untouched in between; always post when nothing is resting. Measure the real gas price (base fee × gas limit) before sizing the budget.
- Measure the real order rate from the LIVE window of the events log, not the bot's startup estimate. The startup "~N per hour" line is worst-case (every block); the actual rate with a gas saver is far lower. Count tx-orders in the events file filtered to the last ~2 h — the full history is polluted by dry-run sim orders and gives a meaningless average. See references/model-api-and-gas-costs.md for the recipe.
- A "multi-market support" commit is only real if the ASSET plumbing changed, not just the labels. Parametrizing MARKET_LABEL/BASE_SYMBOL for the prompt while the margin code still reads the FIRST market's base token hardcoded (e.g. `ZERO_ADDRESS` = native MON) produces silent reverts on the second market: the bot reads the old market's margin, believes it has funds, posts, and the chain rejects every order. The base margin must come from `MarketParams.baseAssetAddress`, the base deposit must branch native (value transfer) vs ERC20 (approve + token deposit), and any USD conversion of gas must use the GAS token's price, not the market mid (on WETH-USDC the mid is ~2423 while gas is paid in MON ~0.024 — a ~100000x pnl overstatement). See references/multi-market-switching.md.
- Watch the live log for `REVERTED` lines in the first minutes after a market switch: each revert costs gas, every block can add another. Stop the bot immediately, fix the margin/allowance plumbing, verify with a read-only book state, then restart. A dry-run "reads the WETH book and posts simulated orders" proves NOTHING about the live path — simulation never exercises margin/allowance/deposit because nothing is sent.
- A live order that is never filled is not always a bug: a post-only order needs taker flow on the other side. Check the book imbalance and the trade-print count before concluding the bot is broken — a one-sided book (e.g. 97% bids) means your resting buys queue behind everyone else and no sell comes. The fix is a more liquid market, not more code.
- A venue can be too thin for post-only market-making as a whole, not just one market. If the bot posts thousands of orders with ZERO fills across BOTH the native and the liquid-adjacent market (e.g. Kuru MON-USDC AND WETH-USDC both 0 fills in 6 h at ~4550 orders), the venue lacks taker flow — no parameter (order size, tick inside, market choice) fixes it. PAUSE the bot rather than keep burning gas (~1-2 USD/h) on a strategy the venue cannot fill. The next step is a venue with real orderbook volume (Hyperliquid, a CEX), not another thin DEX.
- On a thin-margin market, the margin check must count the RESTING + INFLIGHT size on the side, not just the new order. A bot that posts a second order while the first is still resting exceeds the account (Kuru reverts with `InsufficientBalance` 0xf4d678b8) when order value is a large fraction of margin (WETH: 0.01 ~24 USD vs 50 USDC margin) — a bug that never surfaced on the native market where orders were ~4.8 USD against 600 margin. `allowed()` should sum `restingMon(side) + size` against the margin, and the bot should hold instead of reverting. See references/multi-market-switching.md.


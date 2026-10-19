# Multi-market switching: what must actually change

A bot built and tested on one market (e.g. Kuru MON-USDC) does not run on a second market (WETH-USDC, cbBTC-USDC, XAUt0-USDC) by changing env labels alone. A commit that "parametrizes market/base names for the model prompt" is a prompt-only change; the execution path keeps the first market's assumptions until verified otherwise.

## The three places that hard-code the first market
1. **Base margin read**: `marginBalance(ZERO_ADDRESS)` reads the native token balance in the margin account. On MON-USDC that IS the base asset; on WETH-USDC the base is an ERC20, so this reads the wrong basket (worse: it reads the OLD market's leftover MON and makes the bot believe it has base funds).
2. **Base margin deposit**: native `value=amount` transfer vs ERC20 `approve` + token `deposit`. WETH needs the approve path; a native-value deposit with an ERC20 address encodes a zero-amount transfer.
3. **USD conversion of gas**: `gasUsd = gasMon * book.mid` is only correct when the base token of the traded market IS the gas token (mid of MON-USDC ≈ MON price in USD). On WETH-USDC the mid is ~2423 — a ~100000x overstatement of pnl.

## The fix pattern (verified on Kuru, Monad)
- Read base margin from `this.params.baseAssetAddress` (Kuru `MarketParams` exposes `baseAssetAddress`/`baseAssetDecimals`), never a constant.
- Deposit base: `base === ZERO_ADDRESS ? native : erc20` (approve the margin account first for ERC20, like the quote token already does).
- Gas-in-USD: keep an explicit `monPriceUsd`-style config value (env override, default the gas token's USD price) instead of deriving it from the traded market's mid.
- Note: `MarketParams.baseAssetAddress` is `ZERO_ADDRESS` for the native-token market (MON) and the token address for WETH — so the SAME code path serves both if it branches on that check.

## Pre-switch checklist
1. Fetch `getMarketParams` for the new market on-chain and print base/quote addresses + decimals + minSize — verify with a probe, do not trust a commit message.
2. Verify the margin account is the right one for the new market (Kuru: all four USDC markets settle against the same MarginAccount — confirm per-deployment, it is a documented fact, not a given).
3. Check the wallet holds the QUOTE asset too: a 0.01 WETH order at 2423 needs ~24 USDC of margin, and if the wallet only holds the gas token the bot is permanently "cap or funds on both sides". Depositing "what is there" (a partial top-up) is not a substitute for funding the correct asset.
4. Start, then watch the first N blocks of the LIVE log for `REVERTED` lines. Every revert costs gas. Simulated/dry-run orders prove nothing about margin/allowance/deposit.

## Symptom map
| Symptom | Cause |
|---|---|
| Every post `REVERTED` shortly after switch | Base margin read wrong token (old market's balance) OR ERC20 without allowance OR order on wrong margin account |
| `NO QUOTE (cap or funds on both sides)` forever | Wallet lacks the quote asset (USDC) or the base asset for the reducing side — funding, not code |
| pnl jumps by orders of magnitude after switch | `gasUsd` still uses `book.mid` while gas is paid in a different token |

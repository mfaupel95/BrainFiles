# Model API cost vs gas cost — measuring the real running cost of a live bot

## The rule
On a fast chain the gas is the cost driver, not the model API. Size the budget on gas; treat the model fee as noise.

## Model API cost (Jev / TypeSafe AI)
- The `@ai-sdk/typesafe-ai` SDK reads the key from the env var `TYPESAFE_AI_API_KEY` (check `node_modules/@ai-sdk/typesafe-ai/dist/*.js` for `environmentVariableName`).
- A `billing_error` ("Your organization has no available TypeSafe API credits") means the KEY IS VALID but the org has no credits — a user-side action (load credits at console.typesafe.ai/settings/billing), not a code problem. The key may already be set in the repo `.env` and Windows user env; verify existence/length, never print the value.
- Cost per decision: `inputTokens / 1e6 * jevUsdPerMTok`. With a ~665-token state and 0.042 USD/Mtok that is ~0.00003 USD — negligible. **Pricing is per MILLION tokens**; misreading it as per-thousand is a factor-300 error.
- Test the key with the repo's exact call shape (`experimental_evaluate({ model, state, questions, maxRetries: 0 })`), not a hand-rolled format — the SDK rejects a wrong `state`/`questions` shape with "must be a JSON-compatible string, object, or array" before it ever reaches the API.

## Gas cost — measure the real rate, not the startup estimate
The bot's startup line "~N MON per hour" is worst-case (posting every block). With a gas saver the real rate is far lower. Measure it:

1. Read the events log (`data/events.jsonl`), one JSON object per line.
2. Filter to the LIVE window only: `e.ts >= Date.now() - 2*3600e3`. The full history is polluted by dry-run sim orders (`quote.status === "sim"`) and gives a meaningless average.
3. Count real orders: `e.quote?.txHash` (live sends carry a tx hash; sim orders do not).
4. `rate = txCount / windowMinutes * 60` → tx/h. Multiply by gas-per-tx (gasUsed × effective gas price) for MON/h.

## Margin top-up failure (INSUFFICIENT_FUNDS at start)
The bot tops the margin account up to `MARGIN_MON` at startup and only ever deposits, never withdraws. If the wallet is nearly empty of gas, the top-up itself fails with `INSUFFICIENT_FUNDS` ("insufficient funds for intrinsic transaction cost") and the bot dies before the first block.

Fix: set `MARGIN_MON` BELOW the current on-chain margin so no top-up is needed — a margin already above the target starts clean. Check the wallet balance AFTER the deposit math, not before.

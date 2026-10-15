# Hyperliquid Market-Making — Projektplan

**Status:** Angelegt 15.10.2026 · Entscheidung Max: "hyperliquid als neues projekt"
**Ziel:** Den Jev-Entscheidungskern (aus Werkstatt/jev-trader) auf Hyperliquid (Perps) portieren, wo echtes Orderbook-Volumen existiert — im Gegensatz zu Kuru (Monad), das zu wenig Taker-Flow für post-only Market-Making hat.

## Ausgangslage (belegt)

- **Kuru/jev-trader:** 0 Fills in 6 h bei 4.550 Orders (MON UND WETH-USDC). Technisch einwandfrei (0 Reverts, Autostart, Morgen-Check), aber der Markt trägt post-only Market-Making nicht. Bot pausiert (Aufgabe `MaxHirn-Jev-Trader` deaktiviert).
- **Monad-DEX-Landschaft:** $39,9 Mio/24h gesamt, Großteil AMM (Uniswap). Orderbook-DEXs (Kuru, Clober, Crystal, o1) alle zu dünn. Clober = eigener Umbau (Segmented Segment Tree), gleiche Illiquiditäts-Gefahr → verworfen.
- **Hyperliquid:** Perps-L1 mit massivem Orderbook-Volumen, offizielles Python-SDK (`hyperliquid-python-sdk`, 1,9k Stars, v0.24.0, MIT), WebSocket-API + JSON-RPC.

## Was bleibt / was wechselt

| Baustein | Kuru (heute) | Hyperliquid |
|---|---|---|
| Orderweg | on-chain Contract | REST/WebSocket API |
| SDK | `@kuru-labs/kuru-sdk` (TS) | `hyperliquid-python-sdk` (Python) |
| Markt | Spot (MON/WETH-USDC) | Perps (BTC/ETH/SOL-PERP) |
| Margin | MarginAccount | Wallet-USDC, Hebel |
| Order | post-only limit | limit + post-only, tif |

**Bleibt unverändert (der Wert):** Jev-Entscheidungskern — `model.ts` (JevModel, QUESTIONS), `decision-pipeline.ts` (decouple decide() vom Block-Takt), `trader.ts`-Logik (Gas-Saver, Position-Cap, Resting-Margin-Deckel). Alles marktunabhängig.

**Wechselt:** Nur der Orderweg (`market.ts` → Hyperliquid-Client) + Perps-Semantik (Hebel, Funding, Liquidation).

## Nächste Schritte (Reihenfolge)

1. **Hyperliquid-API erkunden** — REST `exchange/placeOrder`, WebSocket-Subscriptions (book, trades, userFills), Info-Endpoint (meta, l2Book). Beleg: lesender Aufruf gegen Testnet. **ERLEDIGT 15.10.2026:** Testnet erreichbar (allMids, l2Book BTC, meta). Orderweg = REST POST /exchange, Signatur ed25519, TIF Alo = post-only. Book-Struktur `levels`=[[bids],[asks]] (px/sz/n) — anders als Kuru, Reader muss umgebaut werden.
2. **Orderweg-Client bauen** — **ENTSCHEIDUNG: TS-Client direkt gegen die REST-API** (kein Python-SDK). Gründe: jev-trader ist TS/bun (eine Sprache), API simpel (2 Endpoints), ed25519 in bun eingebaut, Jev-Kern bleibt byte-identisch. Nur `market.ts` wird ersetzt. **ERLEDIGT 15.10.2026:** `src/market-hl.ts` gebaut (Drop-in fuer die Kuru-Market-Schnittstelle, `@nktkas/hyperliquid` uebernimmt ed25519-Signatur), `ENGINE=hyperliquid`-Schalter in config + index.ts, Hyperliquid-Takt 300ms. Dry-Run belegt: liest echtes BTC-PERP-Buch, postet sim-Orders, Jev-Modell aktiv. Commit `ad951b0`.
3. **Perps-Anpassung** — Hebel, Funding-Kosten in die Kostenrechnung, Liquidation-Schutz (Stop), Position-Cap in USD.
4. **Papier/Testnet zuerst** — Hyperliquid hat ein Testnet. Paper-first, Live nur auf expliziten Befehl (Hausregel).
5. **Autostart + Wache** — nach dem Muster des jev-trader (Wrapper, Aufgabe, Morgen-Check).

## Offene Entscheidungen (Max)

- **TS-Client vs. Python-Neubau** (nach API-Erkundung)
- **Welche Perps-Märkte** (BTC/ETH/SOL-PERP?)
- **Kapital** (USDC auf Hyperliquid, Live-Freigabe)
- **Hebel-Deckel** (Hausregel: dynamisch, nicht statisch)

## Referenzen

- Hyperliquid SDK: https://github.com/hyperliquid-dex/hyperliquid-python-sdk
- Hyperliquid Docs: https://hyperliquid.gitbook.io/hyperliquid-docs
- jev-trader (Quelle des Kerns): Werkstatt/jev-trader

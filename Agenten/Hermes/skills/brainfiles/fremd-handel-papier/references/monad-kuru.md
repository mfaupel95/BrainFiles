# Monad / Kuru (jev-trader) — Domain-Fakten

Fuer den Monad-Marktmacher `Werkstatt/jev-trader` (Kuru, MON-USDC).

## Chain-Fakten (gemessen am oeffentlichen RPC `https://rpc.monad.xyz`)

- **Chain-ID 143** (`eth_chainId` = `0x8f`). Nicht 10143 — die oft genannte Zahl ist falsch; immer am RPC verifizieren.
- **Blockrate ~3,4 Bloecke/s** = ~12 240/h (34 Bloecke in 10 s gemessen). Der Bot-Code rechnet selbst mit 12 000/h.
- **Gas wird auf dem LIMIT abgebucht**, nicht auf gasUsed — ein zu hohes Limit kostet den vollen Betrag, egal ob die Order landet.
- Basis-Fee-Floor 100 gwei + 2 gwei Priority (EIP-1559 type-2). `eth_gasPrice` liefert ~102 gwei.
- Gas/Block bei 350k Limit x 102 gwei = **0,0357 MON** → **~437 MON/h** ≈ **10,80 $/h** bei MON=0,0247.

## Kuru (MON-USDC Marktmacher)

- Markt `0x065C9d28E428A0db40191a54d33d5b7c71a9C394`, MarginAccount `0x2A68ba1833cDf93fa9Da1EEbd7F46242aD8E90c5`.
- Limit-Orders ziehen aus dem **Margin-Konto**, nicht der Wallet. Beim Start deposited der Bot bis `MARGIN_MON`/`MARGIN_USDC` (600/20).
- Mindestorder 200 MON, Tick 0,000001.
- Post-only Limit-Order, einen Tick inside the touch, ersetzt die vorige (cancel + place in einem `batchUpdate`).
- **Gas-Sparmodus (implementiert):** `src/postpolicy.ts` `shouldPost()` postet nur, wenn der Mid seit dem letzten Post >= `POST_MOVE_BPS` (Default 5) bps gewandert ist ODER `POST_REFRESH_BLOCKS` (Default 20) Bloecke vergangen sind; dazwischen bleibt die ruhende Order stehen (kein cancel, kein send). Immer posten, wenn nichts ruht. `BlockEvent.skipReason` unterscheidet `no-move` von `cap`. Gemessen im Dry-Run: 25 Bloecke -> 2 Orders (vorher 25), ~12x weniger Gas. Test: `scripts/test-postpolicy.ts`.
- `DRY_RUN=true` oder fehlender `PRIVATE_KEY` = Simulation (echtes Buch, simulierte Fills).
- Repo liegt unter `Werkstatt/jev-trader` (nicht `Werkstatt/Repos/`); privater Backup-Bare unter `O:/privkopie-cache/jev-trader-privat.git`.

## Hyperliquid-Engine (seit Port)

Der Bot laesst sich ueber `ENGINE=hyperliquid` in `.env` vom Kuru-On-Chain-Marktmacher auf Hyperliquid-Perps umschalten. Dann greifen:

- `HL_TESTNET=true|false`, `HL_COIN=BTC` (oder ETH/SOL/...), `HL_LEVERAGE=0` (0 = nicht setzen), `HL_LIQ_PUFFER_BPS=100` (Liquidation-Stop-Puffer vor dem Liq-Preis).
- SDK `@nktkas/hyperliquid`: `InfoClient({transport: new HttpTransport({isTestnet})})`, `ExchangeClient({transport, wallet})`.
- `info.clearinghouseState({user})` = Konto (accountValue, totalMarginUsed, assetPositions). `assetPositions[].position` traegt `szi` (signierte Groesse, >0 long), `entryPx`, `liquidationPx` (kann null sein), `positionValue`, `unrealizedPnl`, `leverage.value`.
- `info.l2Book({coin})` = Book mit `levels=[[bids],[asks]]` (px/sz/n) — NICHT `bids`/`asks` als eigene Felder. `info.meta()` = Universe (maxLeverage, szDecimals je Coin).
- `info.userRole({user})` = `"missing"` wenn das Wallet noch nie auf HL eingezahlt hat.
- **Liquidation-Stop (implementiert):** bei offener Position setzt `liquidationSchutz()` einen reduce-only Market-Stop (`t:{trigger:{isMarket:true, triggerPx, tpsl:"sl"}}`, `r:true`) hinter dem Liq-Preis (long: liq*(1-puffer), short: liq*(1+puffer)); einmal je Position, ersetzt wenn liqPx sich bewegt. `openOrders`-Eintraege tragen `isPositionTpsl`.
- **Funding:** `info.fundingHistory({coin, startTime})` summiert die 24h-Funding-Zahlungen in `fundingUsd` (negativ = wir zahlten). Funding fliesst real in den Kontostand (margin.usdc sinkt), nicht in eine pnl-Zeile.
- **Testnet-Faucet (`app.hyperliquid-testnet.xyz/drip`) braucht $5+ Mainnet-Deposit** auf demselben Wallet. Ohne Mainnet-Historie kein Testnet-USDC. Bridge laeuft ueber Arbitrum — MON auf Monad ist keine Quelle.

## Wallet-Onboarding fuer Max (MetaMask/Rabby)

Max ist nicht sattelfest in EVM-Wallet-Tooling — klick-fuer-klick fuehren, exakte Feldwerte nennen.

1. **Frischen Key erzeugen** (nie den Bot-Key aus der .env in eine Browser-Wallet importieren): `Wallet.createRandom()` + Gegenprobe `new Wallet(privateKey).address === address`, sonst Abbruch. Key nur in eine nicht versionierte Scratch-Datei, nie in den Chat.
2. **MetaMask zwingt beim Erststart zu "Create a new wallet"** (Seed-Phrase) — erst durchklicken, dann Avatar -> "Import account" -> privaten Key einfuegen. Die Seed-Phrase ist das leere Standard-Wallet, der importierte Key ein separates Konto.
3. **Monad-Netzwerk manuell hinzufuegen** (MetaMask zeigt es nicht von selbst): Network name `Monad`, RPC `https://rpc.monad.xyz`, Chain ID `10143`, Symbol `MON`, Explorer `https://explorer.monad.xyz`.
4. **WalletConnect-`wc:`-Links kann der Agent NICHT ausfuehren** — sie brauchen eine Wallet-App mit dem privaten Key. Sie sind fuer Max zum Oeffnen in seiner Wallet-App; der Agent bereitet nur vor (Key, Netzwerk, Guthaben).

## Wallet-Guthaben pruefen (ethers v5)

Das Repo nutzt ethers 5.8. Die v5-API weicht von v6 ab:

- `new ethers.providers.JsonRpcProvider(url)` — nicht `new ethers.JsonRpcProvider(url)`.
- `new ethers.Contract(addr, abi, provider)` — nicht `new ethers.utils.Contract(...)`.
- `ethers.utils.Interface` — nicht `ethers.Interface`.
- `ethers.BigNumber.from(raw)` — nicht `new ethers.BigNumber(raw)`.
- Fuer Tuple-Rueckgaben (z. B. `getMarketParams`) die ABI mit `components` bauen; ein flaches `returns (address,...)` parst falsch.
- USDC auf Monad: `0xf817257fed379853cDe0fa4F97AB987181B1E5Ea` (6 Dezimalen).

Vor dem Scharfschalten: Blockrate messen, Gas/Block x Bloecke/h gegen die Wallet-Balance stellen (siehe SKILL.md-Pitfall). Ohne Gas-Sparmodus reicht ein 691-MON-Konto ~1,6 h (437 MON/h) — nicht tragfaehig. Mit dem Sparmodus (nur bei Bewegung/Refresh posten) sinkt die Last auf ~22 MON/h worst case (nur Refresh alle 20 Bloecke) bis ~55 MON/h realistisch (alle ~8 Bloecke) — das Konto reicht dann ~13-32 h. Vor dem Scharfschalten die echte Post-Rate im Dry-Run messen (wie oft postet er wirklich), nicht die worst-case-Zahl glauben.

## Prozess-Diagnose

Der Bot laeuft als `bun run src/index.ts`. PID-Datei (`Agenten/Hermes/cache/jev-trader.pid`) kann eine tote PID tragen — immer den echten Prozess pruefen:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'bun' -and $_.CommandLine -match 'src/index.ts' }
```

Nur `Name -match 'bun'` matcht auch Hermes-eigene bun-Server. Der Wrapper `Agenten/Routinen/jev-trader-start.ps1` prueft genau dieses Muster vor dem Start (Einzelinstanz). Log: `Agenten/Routinen/logs/jev-trader.out.log`. Geplante Aufgabe `MaxHirn-Jev-Trader` (Logon + 15 Min, IgnoreNew) kann deaktiviert sein — `Enable-ScheduledTask` reaktiviert sie.

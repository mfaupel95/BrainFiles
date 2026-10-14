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

## Live-Freigabe-Gate

Vor dem Scharfschalten: Blockrate messen, Gas/Block x Bloecke/h gegen die Wallet-Balance stellen (siehe SKILL.md-Pitfall). Ohne Gas-Sparmodus reicht ein 691-MON-Konto ~1,6 h (437 MON/h) — nicht tragfaehig. Mit dem Sparmodus (nur bei Bewegung/Refresh posten) sinkt die Last auf ~22 MON/h worst case (nur Refresh alle 20 Bloecke) bis ~55 MON/h realistisch (alle ~8 Bloecke) — das Konto reicht dann ~13-32 h. Vor dem Scharfschalten die echte Post-Rate im Dry-Run messen (wie oft postet er wirklich), nicht die worst-case-Zahl glauben.

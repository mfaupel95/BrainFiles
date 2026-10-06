# Depotbestand gegen Spuren-Bücher abgleichen

## Wann

Der Auftrag lautet: "Depotbestände bei OKX und Kraken mit Büchern gegenprüfen und möglichst damit handeln bzw. frei machen für Swap oder Future". Das ist KEIN Live-Schalter — es ist ein Abgleich, der zeigt, was frei ist und was gesperrt bleibt.

## Die drei Abgleich-Werkzeuge

Alle drei sind **rein lesend** (bis auf `--anwenden` beim Kraken-Abgleich):

1. **Kraken Buch gegen Boerse** (`kraken/abgleich.py`): liest `zustand.json` + `handelsjournal.csv` der Spur und gegen Kraken `BalanceEx` + `OpenPositions` + `OpenOrders`. Befunde: `geist` (Buch hat Position, Boerse nicht), `waise` (Schutzauftrag ohne Bestand), `teils` (Teilverkauf). Vorschau ist Standard, `--anwenden` bucht Geister mit echtem Boersenerloes aus.

2. **OKX Positionen live** (`okx_positionen_live.py`): liest `/api/v5/account/balance` (je Waehrung: eq, availEq, stgyEq, frozenBal) und `/api/v5/account/positions` (FUTURES, SWAP, MARGIN — NICHT SPOT). Zeigt Kontostand, offene Positionen mit Einstieg/Liquidation/UPL und Schutz-Orders mit Deckung.

3. **OKX Waisen** (`okx_waisen.py`): liest `/api/v5/trade/orders-algo-pending?ordType=conditional` und prueft jede Schutz-Order gegen Bestand (Spot) oder Position (Perp). Befunde: `OK`, `WAISE` (kein Bestand/Position), `UEBERDECKT` (Menge > Bestand).

## Die Reihenfolge

1. **Kraken abgleichen** (`kraken/abgleich.py`) — zeigt Geister/Waisen/Teils
2. **OKX abgleichen** (`okx_positionen_live.py`) — zeigt Kontostand + Positionen
3. **OKX Waisen** (`okx_waisen.py`) — zeigt Schutz-Orders ohne Deckung
4. **Spuren-Bücher lesen** (`zustand.json` je Spur) — zeigt Positionen, die die Spur fuehrt
5. **Vorschau fahren** (`<spur>/handeln.py --vorschau`) — zeigt, was die Spur mit den freien Mitteln machen würde

## Die Freigabe-Regel

**`freigabe.erfuellt` wird NIE vom Agenten gesetzt.** Es ist der von Hand gesetzte Haken in `wachen.json`. Der Agent kann:
- Den Abgleich fahren und die Befunde zeigen
- Die technischen Sperren heben (Herzschlag aktualisieren, venv reparieren)
- Die Vorschau fahren und sagen, was die Spur tun würde

Aber der Haken `freigabe.erfuellt=true` und `handel_erlaubt=true` kommt NUR von Max.

## Die Sperrgruende

| Grund | Ursache | Wer heilt |
|-------|---------|-----------|
| `freigabe.erfuellt=false` | Haken nicht gesetzt | Max |
| `handel_erlaubt=false` | Schalter nicht umgelegt | Max |
| `Herzschlag alt` | Dauerlauf laeuft nicht oder Zyklus ist alt | Dauerlauf neu starten |
| `kein Freigabefenster` | Zeitfenster nicht offen | Freigabefenster oeffnen |
| `ModuleNotFoundError` | venv kaputt | venv reparieren |
| `Guthaben nicht ausreichend` | Zu wenig freies Guthaben | Max (Guthaben transferieren) |

## Die Boerzen-Trennung

- **OKX EEA**: Spot in USDC (kein USDT!), Perp als `_UM_XPERP`-Kontrakte, Margin in USDC
- **Kraken**: Spot in EUR/USDC/EURC, Futures als `PF_`-Kontrakte, Margin im flex-Konto

Eine Spur kann nicht einfach von OKX nach Kraken wechseln — die Waehrung und das Produkt sind anders. Der Abgleich zeigt, was auf welcher Boerse frei ist.

## Das Wichtigste

**Ein Abgleich ist keine Freigabe.** Er zeigt, was frei ist und was gesperrt bleibt. Die Freigabe kommt von Max, nicht vom Werkzeug.
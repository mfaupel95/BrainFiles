# Kraken-MCP

Zweiter selbst gebauter MCP-Server (nach `archiv/`). Bindet Max' Kraken-Pro-Konto
über die REST-API an.

Angelegt am 14.08.2026.

## Zugangsdaten

Ausschließlich über zwei **Windows-Benutzer-Umgebungsvariablen**:

| Variable | Inhalt bei Kraken |
|---|---|
| `KRAKEN_API_KEY` | „API Key" |
| `KRAKEN_API_SECRET` | „Private Key" (base64) |

Sie stehen **nicht** im Vault, nicht in `claude_desktop_config.json` und in
keiner Ausgabe dieses Servers — auch nicht gekürzt. `kraken_status` meldet nur,
*ob* sie gesetzt sind und ob Kraken sie akzeptiert.

Nach dem Setzen muss **Claude neu gestartet** werden: Ein laufender Prozess
erbt neu angelegte Umgebungsvariablen nicht.

## Rechte am Kraken-Schlüssel

Nötig: *Query Funds*, *Query Open Orders & Trades*, *Query Closed Orders &
Trades*, *Query Ledger Entries*, *Create & Modify Orders*.

**Nicht setzen: „Withdraw Funds".** Das ist das einzige Recht, mit dem sich
Guthaben von Kraken wegbewegen lässt. Dieser Server implementiert bewusst kein
Auszahlungs-Werkzeug — selbst wenn das Recht gesetzt wäre, gäbe es hier keinen
Weg dorthin.

## Werkzeuge

**Ohne Schlüssel (öffentlich):**

| Werkzeug | Zweck |
|---|---|
| `kraken_kurs` | Letzter Kurs, Geld/Brief, Hoch/Tief, Volumen |
| `kraken_paare_suchen` | Kraken-Paarnamen finden (Kraken nutzt `XXBTZEUR`, nicht `BTCEUR`) |
| `kraken_candles` | OHLC-Kerzen, 1 min bis 15 Tage |

**Mit Schlüssel (lesend):**

| Werkzeug | Braucht |
|---|---|
| `kraken_status` | — (prüft nur die Anbindung) |
| `kraken_guthaben` | Query Funds |
| `kraken_offene_orders` | Query Open Orders & Trades |
| `kraken_geschlossene_orders` | Query Closed Orders & Trades |
| `kraken_trades` | Query Closed Orders & Trades |
| `kraken_ledger` | Query Ledger Entries |

**Mit Schlüssel (schreibend):**

| Werkzeug | Verhalten |
|---|---|
| `kraken_order_aufgeben` | **Standard: nur Prüfung.** Kraken rechnet die Order komplett durch und meldet Fehler, legt sie aber nicht ins Buch. Erst `echt_ausfuehren=True` platziert wirklich — diesen Schritt macht Max. |
| `kraken_order_stornieren` | Storniert eine oder alle offenen Orders. Bewegt kein Geld. |

## Testen

```
.venv\Scripts\python.exe kraken_mcp.py
npx -y @modelcontextprotocol/inspector .venv\Scripts\python.exe kraken_mcp.py
```

Ohne gesetzte Umgebungsvariablen starten die öffentlichen Werkzeuge trotzdem —
nur die privaten melden dann, dass die Variablen fehlen.

## Fallstricke

- **`Invalid key`** heißt meist nicht „falscher Schlüssel", sondern dass der
  base64-kodierte Secret vor dem HMAC nicht dekodiert wurde. Ist im Code
  berücksichtigt; bei eigenen Änderungen daran denken.
- **`EGeneral:Permission denied`** heißt: dem Schlüssel fehlt ein Recht — der
  Schlüssel selbst ist in Ordnung.
- **Nonce muss streng steigen.** Der Server nimmt Mikrosekunden. Wird derselbe
  Schlüssel gleichzeitig von einem anderen Programm benutzt, kann es trotzdem
  zu `Invalid nonce` kommen; dann einen eigenen Schlüssel je Programm anlegen.

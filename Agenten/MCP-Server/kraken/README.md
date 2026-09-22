# Kraken-MCP

Zweiter selbst gebauter MCP-Server (nach `archiv/`). Bindet Max' Kraken-Pro-Konto
über die REST-API an.

Angelegt am 14.08.2026.

## Zugangsdaten

Ausschließlich über zwei **Windows-Benutzer-Umgebungsvariablen**:

| Variable | Inhalt bei Kraken |
|---|---|
| `KRAKEN_SPOT_API_KEY` | „API Key" — **dieses Paar liest der Server** |
| `KRAKEN_SPOT_API_SECRET` | „Private Key" (base64) |

**Achtung, gemessen am 22.09.2026:** in der Benutzerumgebung liegen zwei Paare.
`KRAKEN_API_KEY`/`KRAKEN_API_SECRET` existiert ebenfalls, wird von Kraken aber
mit `EAPI:Invalid key` abgelehnt — es ist ein anderer (toter) Zugang. Wer ein
neues Werkzeug anschließt, muss prüfen, **welchen Namen** es liest: die
kraken-cli liest die generischen Namen und scheitert damit, bis man ihr die
SPOT-Variablen gibt (`Agenten/Werkzeuge/kraken.ps1` tut das).

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
| `kraken_order_aufgeben` | **Nur Prüfung, niemals echt** (seit 22.09.2026). Kraken rechnet die Order komplett durch und meldet Fehler, legt sie aber nicht ins Buch. `echt_ausfuehren=True` wird abgelehnt und verweist auf `kraken_order_mit_beleg`. |
| `kraken_order_mit_beleg` | **Der einzige Weg zu einer echten Order.** Führt nur aus, was eine Handels-Spur mit einem Freigabe-Beleg versehen hat (`Agenten/Handel/freigabebeleg.py`): Beleg-Kennung, Spur, Seite, Paar, Höchstmenge und Höchstpreis müssen passen, der Beleg muss frisch und unverbraucht sein. Standard ist auch hier nur die Prüfung (`echt_ausfuehren=False`); echt ausführen verbraucht den Beleg. Dieses Werkzeug stellt **keine** Belege aus. |
| `kraken_beleg_uebersicht` | Rein lesend: welche Belege gelten jetzt. |
| `kraken_order_stornieren` | Storniert **eine** Order (kürzt nur Risiko). `"all"` wird abgelehnt — ein Sammelstorno kann den Schutz-Stop einer offenen Position mitnehmen. |

**Warum das Tor:** ein MCP-Werkzeug ist aus jeder Sitzung aufrufbar (Chat, Bot,
A2A-Nachricht), die Sperrenkette der Spuren (Freigabefenster, Herzschlag, Stop,
Kill-Switch, Deckel) hängt aber am Skript. Der Beleg verbindet beides: die
Entscheidung bleibt bei der Spur, der MCP ist nur die Hand. Siehe
`Wissen/Handelsregeln.md`.

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

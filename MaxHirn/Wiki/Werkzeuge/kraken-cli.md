---
titel: Kraken CLI (kraken-cli) im Haus
aktualisiert: 2026-09-22
tags: [werkzeug, handel, kraken]
---

# Kraken CLI — was es ist und wie es hier läuft

> **Falle zuerst:** Die CLI signiert mit **Nanosekunden**-Nonces. Seit dem
> ersten Aufruf muss die Hausseite dasselbe tun, sonst antwortet Kraken jeder
> Abfrage `EAPI:Invalid nonce`. Gemessen, behoben und begründet in
> [../Lektionen/Boersen-und-Schluessel.md](../Lektionen/Boersen-und-Schluessel.md).

`krakenfx/kraken-cli` ist die **offizielle CLI von Kraken** (Rust, ein
Einzelprogramm, Apache/MIT, v0.4.1 am 22.09.2026). Sie ist nicht nur ein
Lesewerkzeug: sie kann handeln, Papier handeln, aufzeichnen und einen eigenen
**MCP-Server** starten.

- Klon: `Werkstatt/kraken-cli` (Fork `mfaupel95/kraken-cli`,
  `upstream` = `krakenfx/kraken-cli`)
- Programm: `Werkstatt/kraken-cli/target/release/kraken.exe`
- Aufruf bei uns: `Agenten/Werkzeuge/kraken.ps1 <Befehl> -o json`

## Windows: selbst gebaut, kein WSL

Kraken liefert **keine Windows-Binärdateien** (nur macOS/Linux; die Anleitung
sagt „Windows: use WSL"). Auf diesem Rechner war Rust 1.97.1 vorhanden, der
Bau lief durch:

```powershell
cd Werkstatt\kraken-cli
cargo build --release --bin kraken      # ~15 min beim ersten Mal, dann inkrementell
```

Ergebnis: `kraken 0.4.1`, 50 MB. Öffentliche Abfragen (Ticker, Kerzen,
Orderbuch) funktionieren sofort, ohne Schlüssel.

## Die Falle, die wie ein falscher Schlüssel aussah

`kraken auth test` und `balance` scheiterten mit
`{"error":"auth","message":"Authentication failed: EAPI:Invalid key"}` —
obwohl **derselbe** Rechnersatz im Haus nachweislich funktioniert.

Ursache: es gibt **zwei** Paare in der Benutzerumgebung.

| Variablen | Wer liest sie | Zustand |
|---|---|---|
| `KRAKEN_SPOT_API_KEY` / `KRAKEN_SPOT_API_SECRET` | `Handel/kraken/kraken.py` (unsere Spuren) | **gültig** |
| `KRAKEN_API_KEY` / `KRAKEN_API_SECRET` | die kraken-cli | von Kraken **abgelehnt** |

`KRAKEN_API_KEY` ist also belegt, aber ungültig — ein falscher **Name**, kein
falscher Schlüssel. Der Wrapper `Agenten/Werkzeuge/kraken.ps1` setzt deshalb die
generischen Namen aus den SPOT-Variablen; danach meldet `balance` EUR 189,151
und dieselben Bestände wie `kraken.guthaben('ZEUR')`.

**Merksatz:** Wenn eine Börse „Invalid key" sagt, obwohl eine andere Anwendung
mit demselben Rechner denselben Zugang nutzt — zuerst prüfen, **welchen
Variablennamen** die neue Anwendung liest.

## Papiermodus (ohne Schlüssel, mit Livekursen)

```powershell
.\kraken.ps1 workspace create sandbox --capital 10000 --mode paper --fee-rate 0.006 -o json
$env:KRAKEN_WORKSPACE='sandbox'
.\kraken.ps1 paper buy BTCUSD 0.01 -o json
.\kraken.ps1 workspace status -o json
```

Kauf zum echten Marktkurs, Gebühr einstellbar — mit `--fee-rate 0.006` rechnet
sie mit **unserem gemessenen Kraken-Satz** (0,6 % je Seite). Damit lässt sich
eine Kraken-Strategie in Minuten gegen die echten Kurse spielen, ohne einen
Schlüssel und ohne unser Buch.

## Was die CLI darf — und was nicht

| Weg | Erlaubnis |
|---|---|
| `ticker`, `ohlc`, `orderbook`, `assets` (öffentlich) | frei |
| `balance`, `open-orders`, `trades-history`, `ledger` | frei (nur lesen) |
| `paper`, `futures paper`, `workspace`, `record`, `session` | frei (lokale Simulation/Aufzeichnung) |
| `order buy/sell/cancel` **echt** | **nicht aus einer Sitzung** — siehe unten |

Der Handel bleibt am Skript-Weg: die Spuren entscheiden unter ihren Wachen.
Für den Sonderfall „ein Agent soll die beschlossene Order ausführen" gibt es
den **Freigabe-Beleg** (`Agenten/Handel/freigabebeleg.py`): eine Spur stellt ihn
nur bei offenem Freigabefenster aus, das Kraken-MCP-Werkzeug
`kraken_order_mit_beleg` führt damit aus — und nur einmal.

Der eingebaute MCP der CLI (`kraken mcp -s market,account,paper`) ist eine
Alternative mit eigener Abstufung (`--allow-dangerous` schaltet die
Bestätigung ab); **bewusst nicht eingebunden**, weil zwei Wege mit demselben
Schlüssel zwei Meinungen darüber erzeugen, was erlaubt ist.

## Nützlich für die Spuren

- `record`/`session`/`replay`: Marktdaten auf Band legen und später abspielen
  (DuckDB/JSONL) — eine saubere Datenquelle für Backtests ohne Rate-Limit
- `paper`: Kostenmodell mit echter Gebühr, Livekurs und Slippage
- `agents/tool-catalog.json` im Klon: 174 Befehle mit Schemas und
  `dangerous`-Kennzeichnung; `skills/` enthält fertige Workflow-Anleitungen

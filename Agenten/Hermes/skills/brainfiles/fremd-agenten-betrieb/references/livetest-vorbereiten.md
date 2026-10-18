# Live-Test eines laufenden Fremd-Traders vorbereiten

Zweck: einen fremden Trading-Bot (Fork, eigenes Repo) fuer einen ECHTEN Lauf auf
einer Testnet-Boerse vorbereiten — ohne den laufenden Trockenlauf zu beruehren
und ohne automatisch live zu gehen. Reihenfolge ist Pflicht; jeder Schritt hat
einen Beleg.

## 1. Auswerten (vor jedem Eingriff)

- **Laufzeit-Schnittstelle zuerst:** `curl -s http://127.0.0.1:<PORT>/` liefert
  `engine`, `dryRun`, `wallet`, `totals`, `latest` — das ist der Betriebszustand.
  Kosmetische `.env`-Felder (`MARKET_LABEL`, `MARKET`, `BASE_SYMBOL`) gehoeren
  oft einem FRUEHEREN Markt; das Engine-Feld entscheidet, welcher Weg laeuft.
- **Prozess:** PID-Datei + CommandLine-Match (Interpreter-Name + Startdatei,
  z. B. `bun` + `src/index.ts`), Task-State ueber `schtasks -query -fo list`
  (aus git-bash mit EINFACHEM Bindestrich, `//query` laeuft in einen
  Option-Fehler und ein grep darueber meldet faelschlich „Aufgabe fehlt").
- **Fehler-Logs:** wiederholte Entscheidungs-Fehler je Block
  (`decide() ... billing_error`, `no credits`) = das Modell ist stumm, der
  Prozess lebt. Sonst haelt man einen haengenden Bot fuer gesund.
- **Guthaben read-only:** Probe-Skript leitet die Wallet-Adresse aus der Config
  ab (Key bleibt im Prozess) und ruft den oeffentlichen Balance-Endpoint. Ausgabe
  NUR Adresse + Zahl. In Bun-/TS-Repos liegt die Probe als `.ts` — in `.mjs`
  faellt der TS-Non-Null-Operator beim Parsen um.

## 2. Isolierter Arbeitsbaum

```
git -C <repo> worktree add --detach <pfad>
cp <repo>/.env <pfad>/.env.live      # Live-Variante, nur hier patchen
```

- Live-Variante: Testnet-Flag AN, `DRY_RUN=false`, kleine Groesse (ein
  Rundungs-Schritt unter der alten Live-Groesse; Sizing in Coin-Einheiten
  pruefen — der Fremd-Code rechnet oft `send(..., tradeSize, ...)` direkt),
  eigener Port, Hebel klein.
- Trocken-Variante: `DRY_RUN=true`, `MODEL=mock` (oder offline) — gleicher
  Code-Pfad bis zum Orderweg, aber kein Wallet, keine echte Order.
- Die `.env` des LAUFENDEN Bots nie anfassen: der Task startet ihn sonst beim
  naechsten Mal mit den neuen Werten.
- Worktree braucht eigenen `bun install` (node_modules ist nicht im Git).

## 3. Trockenlauf im Worktree (Beleg)

```
timeout 90 bun --env-file=.env.trocken run src/index.ts > test.log 2>&1
```

Erwartung: Logkopf nennt Engine + Testnet + `DRY RUN` + Port; im Buch erscheinen
`(sim)`-Orders mit der NEUEN Groesse; `data/events.jsonl` entsteht ISOLIERT im
Worktree (der laufende Bot schreibt weiter in seinen eigenen Ordner). Snapshot
per Curl auf dem eigenen Port bestaetigt dasselbe. Danach beenden.

## 4. Start nur ueber ein Skript mit Sicherheitskette

Grundlage: ein Wrapper in `Agenten/Routinen/<name>-livetest-start.ps1`.
Jeder Punkt bricht VOR dem Start ab (Ausgabe + Exit 1, NICHTS gestartet):

1. Venue-/Testnet-Flag der Env == 'true' — dieser Weg geht NIE aufs Mainnet.
2. `DRY_RUN` == 'false' — sonst waere es nur die Trocken-Kopie.
3. Engine-Wert wie erwartet.
4. Wallet-Guthaben (Probe aus Schritt 1) > 0 — sonst Hinweis auf den Faucet.
5. Einzelinstanz per CommandLine-Match (Interpreter + Worktree-Pfad).

Danach: `.env.live` per `Move-Item` zu `.env` (Bun laedt sie automatisch aus dem
CWD), Start via `Start-Process -WorkingDirectory <worktree>`, getrennte
Out-/Err-Logs, PID-Datei unter `Agenten/Hermes/cache/`.

**Test der Kette ist Pflicht:** einmal absichtlich scheitern lassen (leeres
Wallet) — Ausgabe „ABBRUCH: Wallet <adresse> hat 0 ...", Exit 1, kein Prozess,
keine verschobene `.env`. Eine Kette, die nie abgebrochen ist, ist nicht
eingerichtet.

## 5. Blocker gehoeren dem Nutzer

- Guthaben auf dem Testnet-Konto laden (Faucet = Handarbeit im Browser).
- Modell-Credits: bei `billing_error` laeuft der Live-Test nur mit
  `MODEL=mock` — das beweist den Orderweg, NICHT die Strategie.
- Der Start selbst erfolgt erst auf ausdrueckliches Wort.
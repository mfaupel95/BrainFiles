---
id: 20260930-omnitrade-spur
title: 'omnitrade-Spur — der Rust-Lauf entscheidet, Kraken ordert'
tags: [handel, betrieb, spur]
created: 2026-09-30
updated: 2026-09-30
related: [20260929-omnitrade, 20260902-handelsregeln]
summary: 'Weg B: Agenten/Handel/omnitrade spiegelt die Position der Rust-Laeufe und fuehrt sie ueber den Haus-Kraken-Weg aus. Zwei Zeugen statt state=running, Zustand statt Orderliste, echter Verkaufspreis.'
---

# omnitrade-Spur — der Rust-Lauf entscheidet, Kraken ordert

Stand 30.09.2026, Commit `6197ac9`. Die Spur liegt in
`Agenten/Handel/omnitrade` (Papier, `handel_erlaubt=false`).

## Der Auftrag und die Luecke

Max hat am 30.09.2026 angeordnet: **„nur noch omnitrade auf kraken handel
erlaubt"**. Die Sperrseite war schnell umgesetzt — `kraken` und
`moondev_marktlage` auf `handel_erlaubt=false`, `mosaic` auf `boersen: ["okx"]`,
alle vier Kraken-Spuren aus `dauerlauf.AUTO_FREIGABE`. Die Freigabeseite fehlte:
`omnitrade-exchange/src/` kennt nur `binance` und `okx`, und
`omnitrade-cli/src/commands/live.rs:33` weist jedes andere `--exchange` ab.
**Danach handelte niemand mehr auf Kraken** (T-206).

## Weg B (Entscheidung Max)

**omnitrade bleibt der Entscheider, der bewaehrte Haus-Orderweg fuehrt aus.**
Kein Kraken-Adapter in Rust: das waere ein zweiter Kraken-Schluessel und ein
zweiter Nonce-Zaehler neben dem Haus-Pool (`kraken/.kraken_nonce`), und die
Preisregeln je Paar (`pair_decimals`), die Stop-Logik und der Freigabebeleg
muessten in Rust nachgebaut werden — alles schon da in
`mosaic/kraken_spot.py` → `kraken/kraken.py`.

Die Spur nutzt damit den **gemeinsamen Kern** (`spur_buch.zyklus`) samt
Sperrenkette; `boerse: kraken`, `kraken_quote: USDC`, `guthaben_waehrung: USDC`,
`mindest_guthaben: 60`. Die Quote wird in `boersen_binden(w)` **vor der ersten
Sperrenpruefung** gesetzt — mit der Vorgabe EUR findet die Paar-Tabelle ein
USDC-Paar nicht, und sie faellt ausdruecklich nicht auf eine andere Waehrung
zurueck (eine Order im falschen Markt waere die Folge).

## Die drei Entscheidungen, die den Aufbau tragen

1. **Zustand statt Orderliste.** `recent_orders` ist ein Ringpuffer mit
   hoechstens 20 Eintraegen (`MAX_ORDERS` in `omnitrade-cli/src/status.rs`).
   Wer daraus Ereignisse nachzaehlt, verliert bei einem Ausfall alles
   dazwischen. Gespiegelt wird `net_quantity`: hat der Lauf eine Position, hat
   die Spur sie auch.
2. **Zwei Zeugen statt `state: running`.** Nach einem harten Ende bleibt die
   Statusdatei mit einer **toten PID** auf `running` stehen — am 30.09.2026 lag
   `live_adx_macd_BTCUSDC.json` so zwei Stunden im Statusordner, waehrend
   `omnitrade_start.py liste` „steht, PID lebt nicht" meldete. Ein Einstieg
   verlangt deshalb Statusdatei frisch UND lebende PID (`lesen.lauf` →
   `omnitrade_lauf.pid_lebt`). Der Ausstieg greift auch bei `stopped` (die CLI
   verkauft beim Beenden), **nie** bei `starting`/`error`: ein Abbruch ist kein
   Handelssignal.
3. **Der echte Verkaufspreis, nicht `last_close`.** Der Ausstieg des
   Rust-Laufs ist eine echte Order mit echtem Preis; er steht in
   `recent_orders`. Wer `last_close` bucht, schreibt einen Kurs ins Journal,
   den es nie gab. `quelle()` nimmt den Verkaufspreis genau dann, wenn der
   Lauf **nicht** offen ist — fuer eine offene Position bleibt `last_close` die
   Bewertungsgrundlage.

## Grenzen

| Wert | Zahl | Warum |
|---|---|---|
| Notausstieg | 8 % | die Ausstiegslinie ist der Rust-Lauf, nicht die Spur |
| Ziel | 10R (80 %) | absichtlich weit — ein Ziel, das die Strategie ueberholt, bucht Runden, die omnitrade nie genommen haette |
| Ratsche | 15.00 | 1.0x Buchrisiko (5 USD x 3 Plaetze) |
| Kill | 45.00 | 3x Buchrisiko |
| Gebuehr | 0,6 %/Seite | Kraken-Taker, gemessen an zwei echten Fuellungen am 22.09.2026 |
| Live | 1 Platz, 50 USD | kleinster sinnvoller Anfang |

## Nachweis (30.09.2026)

* 31 Tests gruen (`tests/test_omnitrade.py`): Attrappen-Statusordner, Prozessabfrage
  als Seam, Buch-Zyklus in einem Temp-Spurenordner — Einstieg, Halten, Ausstieg
  mit Grund `omnitrade flat`, Leiche mit toter PID, gar keine Daten.
* `--vorschau` mit `MAXHIRN_ROUTINE=1` nennt vier Sperrgruende:
  `handel_erlaubt=false`; `freigabe.erfuellt=false`; kein Freigabefenster;
  `nur 25.08 USDC frei, noetig 60.00`.
* Erster Papierzyklus schreibt `zustand.json` und spiegelt nach
  `Q:\Handel_Journal\omnitrade`; `spiegelstand.py` meldet **38/38 byte-gleich**.
* `pruefe_ratschen.py` fuehrt omnitrade mit 15.00 = 1.0x Buchrisiko;
  `test_lage` 12/12 (jede Spur aus `dauerlauf.SPUREN` hat einen Holer).

## Offen

* **Scharf schalten** braucht die Freigabekette (Handelsregeln Punkt 1–5) und
  Max' Endabnahme. Bindend waere das Guthaben: das Kraken-Konto traegt rund
  25 USDC gegen ein Tor von 60 (T-115).
* Die acht `klassik_*`-Spuren (30.09.2026) melden im Bus-Test
  `test_dauerlauf_subprocess_skripte_haben_bus` „automatisch gestartet, aber
  ohne Bus-Anbindung": ihr Spurname steht in `klassik_regeln.spur_main`, nicht
  woertlich in der gestarteten Datei. Vorbestehend, nicht von dieser Spur.

Verwandt: [[20260929-omnitrade]] (der Rust-Lauf selbst), [[Handelsregeln]],
`references/zweite-boerse.md` im Skill `handel-spuren`.
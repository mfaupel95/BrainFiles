---
id: 20260921-spuren-uebersicht
title: 'Handel — Spuren-Uebersicht'
tags: [handel]
created: 2026-09-21
updated: 2026-09-22
related: ['[[Handel/Gates-und-Freigabe]]', '[[Handel/Kosten-und-Bedingungen]]', '[[Wissen/Handelsregeln]]']
summary: 'Die 39 Spuren des Dauerlaufs, welchen Orderweg sie haben und wer heute wirklich handeln darf oder kann.'
---

# Spuren-Uebersicht

Quelle dieser Seite: `Agenten/Handel/dauerlauf.py` (`SPUREN`, `NUR_BASIS`, `AUTO_FREIGABE`)
und die `wachen.json` jeder Spur. Stand 30.09.2026 (39 Spuren).

## Der Dauerlauf

Ein einziger Schreiber auf allen Spuren: `Handel/dauerlauf.py` (Takt 15 min, `TAKT_MAX_MINUTEN`
ist eine harte Obergrenze wegen des eigenen Herzschlags). Geplante Aufgaben:
`MaxHirn-Handel-Dauerlauf` (Basis), `...-Mittel-Waechter` (Stufe mittel) und seit
24.09.2026 `...-Hoch-Waechter` (Stufe hoch), je mit `IgnoreNew`. Wache:
`MaxHirn-Handel-Dauerlauf-Waechter` (30 min) startet einen toten Lauf neu.

**Risikostufen:** `dauerlauf.py --risiko mittel|hoch` fahren dieselben Spuren mit groesseren
Betraegen in eigenen Dateien, **nie live**, ohne Telegram und ohne Befehle. Je Stufe eine
eigene Sperrdatei, ein eigenes Log und ein eigener Waechter-Task:

| Stufe | Sperre | Log | Waechter-Task |
|---|---|---|---|
| Basis | `dauerlauf.pid` | `dauerlauf.log` | `MaxHirn-Handel-Dauerlauf-Waechter` |
| mittel | `dauerlauf.mittel.pid` | `dauerlauf.mittel.log` | `...-Mittel-Waechter` |
| hoch | `dauerlauf.hoch.pid` | `dauerlauf.hoch.log` | `...-Hoch-Waechter` |

**Den Stand einer Stufe LESEN** (statt zu schaetzen): `tagesbericht.py --risiko mittel`
(oder `hoch`) baut den Bericht aus `zustand.mittel.json` und
`handelsjournal.mittel.csv`; `--risiko alle` gibt Basis, mittel und hoch untereinander
aus (die XPERP-Rangliste wird dabei EINMAL geholt, nicht je Stufe). Ohne Angabe bleibt
es beim Basisbericht - der nennt die Stufen nur in seiner Summenzeile.

Die Stufe wirkt ueber `HANDEL_RISIKO` (genau wie beim Dauerlauf), und `lage._buch()`
haengt das Suffix an `zustand*` und `handelsjournal*` - **nicht** an `wachen.json`: die
Wachen werden beim Laden skaliert (`risikostufe.skaliere`), die Datei behaelt ihren
Namen. Mit Suffix gelesen waere die Wachenlage eines Stufenberichts leer und damit jede
Sperre darin falsch. Bis 25.09.2026 kündigte der Bericht die Stufe nur AN und las
trotzdem die Basisdateien - ein Kopf "Faktor 4" ueber den Zahlen der Basis. Wer eine
weitere Datei eines Buchs anfasst (Zustand, Journal), geht durch `_buch`.

Stand 24.09.2026: alle drei laufen. `hoch` wurde an diesem Tag gestartet (Wrapper
`Routinen/handel-dauerlauf.ps1 -Risiko hoch`), sein Waechter ist ein Klon des Mittel-Waechters
mit `-Risiko hoch`. `NUR_BASIS` enthaelt die Spuren, die nur der Basislauf fuehrt (derzeit leer).

## 39 Spuren im Dauerlauf

| Gruppe | Spuren |
|---|---|
| Kern | `xperp`, `scanner`, `swap`, `kraken` |
| Preisaktion/Indikatoren (eigene Signale) | `mosaic`, `orbk`, `orb`, `gitter`, `squeeze`, `wavetrend`, `macd_mtf`, `supertrend`, `trendwende_btc`, `liq_wand` |
| Copy-Trade-Feed | `kopier`, `kopier1zu1` |
| Nautilus-Arme (BTC-Proxy) | `nautilus`, `nautilus_kraken`, `nautilus_kraken_futures` |
| Bot-Signale (MoonDev-Nachbau) | `moondev_funding`, `moondev_listingarb`, `moondev_topmovers`, `moondev_marktlage`, `moondev_sniper`, `moondev_signalwelle` |
| Optionszonen | `iv_wand`, `iv_waelle` |
| Sprachmodell-Spuren | `moondev_whale`, `moondev_liquidation`, `moondev_sentiment` |
| Klassik (Pine-Regeln, 4H, OKX-Perp, Papier) | `klassik_sma`, `klassik_ema`, `klassik_macd`, `klassik_bollinger`, `klassik_donchian`, `klassik_rsi`, `klassik_rsi2`, `klassik_donchian_trend`, `klassik_sr_breaks`, `klassik_pmax`, `klassik_supertrend` |
| Zeitreihen-Experiment | `omniquant` |
| Fremd-Lauf gespiegelt (Rust) | `omnitrade` (Position der Laeufe in `Werkstatt/omnitrade`, Live-Zweig Kraken/USDC) |
| **aus** seit 21.09.2026 | `spiegel`, `spiegel_knapp`, `spiegel_weit` (Buecher bleiben als Vergleichsgrundlage, wachsen nicht) |

Die `klassik_*`-Spuren (30.09.2026, `klassik_sr_breaks` und `klassik_pmax` 02.10.2026) setzen die Pine-Strategien dieses Ordners als Papierbuch um
(BTC/ETH/SOL, 4H, Long und Short, 5 USD Risiko, 3 Plaetze, Ratsche 15 USD, `--live` verweigert). Gemeinsamer
Kern: `Agenten/Handel/klassik_regeln.py`. Zwei sind neu erdacht: `klassik_rsi2` (Connors RSI(2) mit SMA200-Filter)
und `klassik_donchian_trend` (Donchian nur in Richtung der EMA200); `klassik_sr_breaks` bildet die
LuxAlgo-Vorlage `sr-breaks.pine` ab (Pivot-Resistance/-Support 15/15, Break mit Volumen-OSZ > 20,
Bull/Bear-Wick ohne Volumenfilter, Ausstieg beim Gegensignal); `klassik_pmax` den PMax Explorer
(`pmax-explorer.pine`, EMA10 auf hl2 plus ATR-Baender, acht MA-Typen waehlbar); `klassik_supertrend`
den Supertrend Explorer (`supertrend-explorer.pine`, Band auf hl2, Signale auf dem Linienwechsel). Lehre: Die Pine-Donchian-Vorlage
rechnet den Kanal inklusive laufender Kerze und kann nie ausloesen; der Kanal liegt hier VOR der Kerze.

`moondev_signalwelle` (22.09.2026) ist das ehrliche Gegenstueck zu einem VIP-Signal-Kanal aus
Max' Screenshot: 1h-Momentum (3-15 %) plus Tagesvolumen >= 20 Mio USD, Long, deterministisch,
**kein Hebel und kein Live-Zweig** (`--live` verweigert). Buch ueber `spur_buch.py`,
3 Plaetze, Ratsche 15 USD. Kein Kanal-Copytrading, sondern eine nachrechenbare Regel.

## Wer hat einen echten Orderweg im CODE?

Gemessen mit `Agenten/Handel/spuren_stand.py` (21.09.2026): **7 von 29** tragen Ordercode im
Modul. Davon **fuenf mit scharfem Weg**: `xperp` (OKX Perps/`okxf`), `scanner` (OKX Spot/`okx`),
`swap` (OKX), `mosaic` (waehlbar: OKX Spot **oder** Kraken Spot — Feld `boerse: kraken`),
`kraken` (Kraken Spot, EUR). Zwei Sonderfaelle ohne scharfen Weg:

- `nautilus` — `grid_strategie.py` faehrt eine echte NautilusTrader-Strategie, aber im
  **OKX-DEMO-Node** (Container `nautilus-demo`); kein echtes Geld.
- `moondev_marktlage` — abgetrennter Live-Zweig `live_kraken.py` (Kraken-Spot XBT/USD,
  long-only, 10-30 EUR, eigenes Buch `handelsjournal.live.csv`), laut eigenem Vermerk
  **nicht** ueber `--live` verdrahtet, `handel_erlaubt=false`.

Die uebrigen 22 verweigern `--live` mit einem Grund; dort ist `handel_erlaubt` wirkungslos
oder nicht gesetzt.

## `handel_erlaubt` und `freigabe.erfuellt` heute (Dateistand 22.09.2026)

`handel_erlaubt = true` **und** `freigabe.erfuellt = true`: `xperp`, `scanner`, `swap`,
`mosaic`, `kraken`*(siehe unten)*, `moondev_listingarb`, `moondev_topmovers`,
`trendwende_btc`, `liq_wand`.
**`kraken` ist seit 22.09.2026 Papier** (Auftrag Max „Kraken papier"): `freigabe.erfuellt`
bleibt true, `handel_erlaubt` steht auf **false**. Das Konto ist seit demselben Tag wieder
frei (189 EUR, `EGeneral:Temporary lockout` vorbei) und das Fenster stand offen — mit
`handel_erlaubt=false` laeuft die Spur trotzdem Papier, und weil jetzt ein ZWEITER
Sperrgrund genannt wird, oeffnet `AUTO_FREIGABE` kein Fenster mehr. Im Buch steht keine
einzige `live`-Zeile.
**Der Schalter allein handelt nicht** — es zaehlt die Sperrenkette (siehe [[Handel/Gates-und-Freigabe]]).

## Was aus einem live-Lauf wirklich kommt

`AUTO_FREIGABE` (gemessen 22.09.2026) steht auf `("xperp", "scanner", "mosaic", "swap",
"moondev_listingarb", "moondev_topmovers", "kraken", "trendwende_btc", "liq_wand")` mit 12
Stunden Laufzeit. Die MoonDev-Spuren darin haben **keinen** Live-Pfad — die Freigabe ist dort
gegenstandslos, weil `--live` ohnehin verweigert. `kraken` bekommt kein Fenster mehr, weil mit
`handel_erlaubt=false` ein zweiter Sperrgrund genannt wird (`nur_fenster_fehlt` verlangt GENAU
EINEN Grund). Wer die Liste aendert, prueft das gegen die Spalte „Orderweg im Code".

## Wie man den Stand ERFRAGT (statt zu schaetzen)

- `Agenten/Handel/spuren_stand.py` — Tabelle aller Spuren.
- `Agenten/Handel/sperrgruende.py` — Sperrgruende aus der eigenen Vorschau, markiert „nur
  das Fenster fehlt".
- `handeln.py --wachen` je Spur — die wirksamen Grenzen.
- `handeln.py --vorschau` mit `MAXHIRN_ROUTINE=1` — so ruft der Dauerlauf die Spur; die Zeile
  `Live waere gesperrt durch: …` ist die einzige Wahrheit ueber den Modus.
- `Agenten/Handel/spiegelstand.py` — Bedingung 4 (Spiegel byte-gleich), zuletzt 30/30.
- `Agenten/Handel/auswertung_alle.py` — Kennzahlen je Spur auf echten Runden.
- SkillsBot-Befehle: `/lage`, `/live`, `/spuren`, `/spur NAME`, `/bericht`, `/geschlossen`.

## robinhood_radar — Papier auf bewerteten Wallets (Robinhood Chain)

Angelegt 22.09.2026 (Auftrag „Radar -papierspur und -bot"). Quelle ist die SQLite
`fomo_agent.db` des Fremd-Repos `Werkstatt/Repos/fomo-robinhood-radar` — **nur lesend**
(`lesen.py` oeffnet mit `mode=ro` und lehnt jede Anweisung ab, die nicht mit `SELECT`/`WITH`/
`PRAGMA` beginnt).

Regel: mindestens **zwei verschiedene bewertete Wallets** (Score ≥ 60, Status ≠ `dropped`)
kaufen denselben Token innerhalb von sechs Stunden; Verkaufsdruck derselben Kohorte blockiert
das Signal. Nur long — Robinhood Chain hat in diesem Haus **keinen Orderweg**, `--live`
verweigert mit Grund.

- Einstiegspreis = Preis des juengsten beobachteten Kaufs (`usd_value / token_amount`)
  **+2 % Nachlauf**, plus 1 % Gebuehr je Seite. Eine Kopie ohne Kursbewegung ergibt ein Minus —
  das ist Absicht, keine Ungenauigkeit.
- **Ein** neuer Einstieg je Zyklus, staerkster Kandidat zuerst (sonst fuellt der erste Zyklus
  mit Daten das ganze Buch und die Auswertung kann den Rang nicht tragen). Stop/Ziel (25 %,
  2,0 R) sind **gesetzt, nicht gemessen**.
- Sammeln tut der Cron `radar-sammler` (20 Minuten, `Agenten/Hermes/scripts/radar-sammeln.py`),
  nicht die Spur — damit ist die Spur offline testbar, `FOMO_RADAR_DB` ist die Naht.
- Papier: `handel_erlaubt=false`, `freigabe.erfuellt=false`; Ratsche 15,00 = 1,0x Buchrisiko
  (Risiko 5 USD × 3 Plaetze).

**Nachtrag 22.09.2026:** `pruefe_ratschen.py` fuehrte `trendwende_btc`, `liq_wand` und
`robinhood_radar` nicht — die Liste war seit dem 21.09. hinter den Spuren her. Jetzt alle drei
drin, alle „1.0x? ja".

**Nachtrag 03.10.2026 — drei Spuren liefen, ohne dass das Haus ihre Zahlen kannte.**
`liq_wand`, `trendwende_btc` und `nautilus_emacross` standen in `dauerlauf.SPUREN`,
hatten `wachen.json`, einen funktionierenden Zyklus — und fehlten in
`auswertung_alle.SPUREN`. Gemessen: `liq_wand` hatte **32 geschlossene Runden im Journal
und 0 in jeder Auswertung**. Kein Tagesbericht, keine Strategiekennzahl, kein
Kosten-Wendepunkt, keine Freigabe-Aussage. Alle drei tragen `kauf`/`verkauf` mit
`einsatz_usd` — dieselbe Form wie `squeeze`/`wavetrend`, also derselbe Rechenweg
(`runden_indikator`). Nachgetragen, Ergebnis liq_wand: 32 Runden, 66 % Treffer,
−10,83 USD brutto / −14,07 USD netto; Kosten-Wendepunkt −0,30 % je Runde.

**Und dieselbe Luecke bei den Ratschen:** `squeeze`, `wavetrend`, `macd_mtf`,
`supertrend` (alle 20,00 = 1,0 × Buchrisiko 5 USD × 4 Plätze) und
`nautilus_emacross` (100,00) führten eine Drawdown-Ratsche, die
`pruefe_ratschen.py` nie nachfragte. Nachgetragen; `nautilus_emacross` meldet jetzt
„n/a“ — die Wache setzt 100,00 **ohne Risiko-Feld**, der Betrag ist damit nicht
herleitbar (als Lücke benannt, nicht stillschweigend übergangen).

**Warum das so lange unbemerkt blieb:** die beiden Listen (`auswertung_alle.SPUREN`,
`pruefe_ratschen.SPUREN`) wurden von Hand nachgezogen, und kein Test verglich sie mit
`dauerlauf.SPUREN`. Es gibt jetzt `Agenten/Handel/tests/test_verdrahtung.py` — es
prüft die **Regel** (jede Spur mit Journal hat einen Rechenweg; jede gesetzte Ratsche
wird geprüft; jeder geprüfte Betrag trifft 1,0 × Buchrisiko), nicht eine feste
Zahl, und hat zwei Gegenproben: nimmt man `liq_wand` aus der Auswertungsliste oder
`squeeze` aus der Prüfliste, wird derselbe Test rot.

**Bewusst NICHT verdrahtet:** `kopier`, `kopier1zu1`, `spiegel`, `omniquant`, `gitter`
haben eine eigene `auswertung.py` und erscheinen im Tagesbericht mit voller Bilanz
(kopier: 111 Ausstiege, −793,81 USD). Ihr Journal trägt `token`/`symbol` statt `inst`;
ein Weg in `auswertung_alle` ergab **107 Runden mit falscher Paarung** (Einsteig PATE,
Ausstieg leeres Symbol) — gemessen, nicht vermutet. `gitter` führt `max_verlust_usd`
(Kill) statt einer Drawdown-Ratsche und hat keine `lage()`.

## Pläne und Befunde (verschoben 2026-10-06)

Alle Pläne liegen in `MaxHirn/Wiki/Handel/plans/`:

- [[2026-09-18-spiegel-kopier-filter-design]]
- [[2026-09-19-quant-migration-design]]
- [[2026-09-24-backtest-fundament-design]]
- [[2026-09-26-moondev-backtest-design]]
- [[2026-09-29-leitstand-design]]
- [[2026-10-01-prognose-merkmale-design]]
- [[2026-09-18-filter-studie]]
- [[2026-09-18-v1-ausstiegsgeometrie]]
- [[2026-09-19-daten-auffrischen]]
- [[2026-09-19-python-zu-rust-migration]]
- [[2026-09-19-quant-migration-plan]]
- [[2026-09-24-backtest-fundament]]
- [[2026-09-26-moondev-backtest]]
- [[2026-09-29-leitstand-plan]]
- [[2026-10-01-omniquant-kraken-live-plan]]
- [[PLAN-auswertung-datengrundlage-2026-09-17]]
- [[PLAN-berichtsschicht-2026-09-18]]

Befunde in `MaxHirn/Wiki/Handel/Befunde/`:
- [[BEFUND-hygiene-2026-09-17]]
- [[CODE_REVIEW_AND_FIXES_INDEX]]
- [[CODE_REVIEW_FIXES]]
- [[ENTWURF-auswertung-berichte-2026-09-17]]
- [[FIXES_APPLIED_SUMMARY]]
- [[HANDOFF_FOR_NEXT_DEVELOPER]]
- [[VALIDATION_REPORT]]

Spur-Pläne in `MaxHirn/Wiki/Handel/Spuren/`:
- [[MOSAIC-LIVE-PLAN-OKX]] (mosaic)
- [[KRAKEN-LIVE-PLAN]] (moondev_marktlage)
- [[NOTIZ]] (iv_waelle)
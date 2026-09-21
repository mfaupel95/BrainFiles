---
id: 20260921-spuren-uebersicht
title: 'Handel — Spuren-Uebersicht'
tags: [handel]
created: 2026-09-21
updated: 2026-09-21
related: ['[[Handel/Gates-und-Freigabe]]', '[[Handel/Kosten-und-Bedingungen]]', '[[Wissen/Handelsregeln]]']
summary: 'Die 29 Spuren des Dauerlaufs, welchen Orderweg sie haben und wer heute wirklich handeln darf oder kann.'
---

# Spuren-Uebersicht

Quelle dieser Seite: `Agenten/Handel/dauerlauf.py` (`SPUREN`, `NUR_BASIS`, `AUTO_FREIGABE`)
und die `wachen.json` jeder Spur. Stand 21.09.2026.

## Der Dauerlauf

Ein einziger Schreiber auf allen Spuren: `Handel/dauerlauf.py` (Takt 15 min, `TAKT_MAX_MINUTEN`
ist eine harte Obergrenze wegen des eigenen Herzschlags). Geplante Aufgaben:
`MaxHirn-Handel-Dauerlauf` (Basis) und `...-Mittel-Waechter` (Risikostufe mittel), je mit
`IgnoreNew`. Wache: `MaxHirn-Handel-Dauerlauf-Waechter` (30 min) startet einen toten Lauf neu.

**Risikostufen:** `dauerlauf.py --risiko mittel|hoch` fahren dieselben Spuren mit groesseren
Betraegen in eigenen Dateien (`zustand.mittel.json`, `dauerlauf.mittel.log`), **nie live**,
ohne Telegram und ohne Befehle. `NUR_BASIS` enthaelt die Spuren, die nur der Basislauf fuehrt
(derzeit leer).

## 29 Spuren im Dauerlauf

| Gruppe | Spuren |
|---|---|
| Kern | `xperp`, `scanner`, `swap`, `kraken` |
| Preisaktion/Indikatoren (eigene Signale) | `mosaic`, `orbk`, `orb`, `gitter`, `squeeze`, `wavetrend`, `macd_mtf`, `supertrend` |
| Copy-Trade-Feed | `kopier`, `kopier1zu1` |
| Nautilus-Arme (BTC-Proxy) | `nautilus`, `nautilus_kraken`, `nautilus_kraken_futures` |
| Bot-Signale (MoonDev-Nachbau) | `moondev_funding`, `moondev_listingarb`, `moondev_topmovers`, `moondev_marktlage`, `moondev_sniper`, `moondev_signalwelle` |
| Optionszonen | `iv_wand`, `iv_waelle` |
| Sprachmodell-Spuren | `moondev_whale`, `moondev_liquidation`, `moondev_sentiment` |
| Zeitreihen-Experiment | `omniquant` |
| **aus** seit 21.09.2026 | `spiegel`, `spiegel_knapp`, `spiegel_weit` (Buecher bleiben als Vergleichsgrundlage, wachsen nicht) |

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

## `handel_erlaubt` und `freigabe.erfuellt` heute (Dateistand)

`handel_erlaubt = true` **und** `freigabe.erfuellt = true`: `xperp`, `scanner`, `swap`,
`mosaic`, `moondev_listingarb`, `moondev_topmovers`.
`freigabe.erfuellt = true` ohne Schalter: `kraken` (traegt `stillgelegt`); alle uebrigen
Spuren: beides false/nicht gesetzt.
**Der Schalter allein handelt nicht** — es zaehlt die Sperrenkette (siehe [[Handel/Gates-und-Freigabe]]).

Fenster zum Messzeitpunkt offen: `xperp` bis 08:33, `scanner` bis 04:02, `swap` bis 01:02,
`mosaic` bis 09:09, `moondev_listingarb`/`-topmovers` bis 07:54. `kraken` zu.

## Was aus einem live-Lauf wirklich kommt

`AUTO_FREIGABE` steht heute auf `("xperp", "scanner", "mosaic", "swap", "moondev_listingarb",
"moondev_topmovers", "kraken")` mit 12 Stunden Laufzeit. Die MoonDev-Spuren darin haben
**keinen** Live-Pfad — die Freigabe ist dort gegenstandslos, weil `--live` ohnehin verweigert.
Wer die Liste aendert, prueft das gegen die Spalte „Orderweg im Code".

## Wie man den Stand ERFRAGT (statt zu schaetzen)

- `Agenten/Handel/spuren_stand.py` — Tabelle aller Spuren.
- `Agenten/Handel/sperrgruende.py` — Sperrgruende aus der eigenen Vorschau, markiert „nur
  das Fenster fehlt".
- `handeln.py --wachen` je Spur — die wirksamen Grenzen.
- `Agenten/Handel/spiegelstand.py` — Bedingung 4 (Spiegel byte-gleich), zuletzt 27/27.
- `Agenten/Handel/auswertung_alle.py` — Kennzahlen je Spur auf echten Runden.
- SkillsBot-Befehle: `/lage`, `/live`, `/spuren`, `/spur NAME`, `/bericht`, `/geschlossen`.
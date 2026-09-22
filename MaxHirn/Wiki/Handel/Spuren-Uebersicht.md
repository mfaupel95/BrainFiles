---
id: 20260921-spuren-uebersicht
title: 'Handel — Spuren-Uebersicht'
tags: [handel]
created: 2026-09-21
updated: 2026-09-22
related: ['[[Handel/Gates-und-Freigabe]]', '[[Handel/Kosten-und-Bedingungen]]', '[[Wissen/Handelsregeln]]']
summary: 'Die 31 Spuren des Dauerlaufs, welchen Orderweg sie haben und wer heute wirklich handeln darf oder kann.'
---

# Spuren-Uebersicht

Quelle dieser Seite: `Agenten/Handel/dauerlauf.py` (`SPUREN`, `NUR_BASIS`, `AUTO_FREIGABE`)
und die `wachen.json` jeder Spur. Stand 22.09.2026 (31 Spuren).

## Der Dauerlauf

Ein einziger Schreiber auf allen Spuren: `Handel/dauerlauf.py` (Takt 15 min, `TAKT_MAX_MINUTEN`
ist eine harte Obergrenze wegen des eigenen Herzschlags). Geplante Aufgaben:
`MaxHirn-Handel-Dauerlauf` (Basis) und `...-Mittel-Waechter` (Risikostufe mittel), je mit
`IgnoreNew`. Wache: `MaxHirn-Handel-Dauerlauf-Waechter` (30 min) startet einen toten Lauf neu.

**Risikostufen:** `dauerlauf.py --risiko mittel|hoch` fahren dieselben Spuren mit groesseren
Betraegen in eigenen Dateien (`zustand.mittel.json`, `dauerlauf.mittel.log`), **nie live**,
ohne Telegram und ohne Befehle. `NUR_BASIS` enthaelt die Spuren, die nur der Basislauf fuehrt
(derzeit leer).

## 31 Spuren im Dauerlauf

| Gruppe | Spuren |
|---|---|
| Kern | `xperp`, `scanner`, `swap`, `kraken` |
| Preisaktion/Indikatoren (eigene Signale) | `mosaic`, `orbk`, `orb`, `gitter`, `squeeze`, `wavetrend`, `macd_mtf`, `supertrend`, `trendwende_btc`, `liq_wand` |
| Copy-Trade-Feed | `kopier`, `kopier1zu1` |
| Nautilus-Arme (BTC-Proxy) | `nautilus`, `nautilus_kraken`, `nautilus_kraken_futures` |
| Bot-Signale (MoonDev-Nachbau) | `moondev_funding`, `moondev_listingarb`, `moondev_topmovers`, `moondev_marktlage`, `moondev_sniper`, `moondev_signalwelle` |
| Optionszonen | `iv_wand`, `iv_waelle` |
| Sprachmodell-Spuren | `moondev_whale`, `moondev_liquidation`, `moondev_sentiment` |
| Zeitreihen-Experiment | `omniquant` |
| **aus** seit 21.09.2026 | `spiegel`, `spiegel_knapp`, `spiegel_weit` (Buecher bleiben als Vergleichsgrundlage, wachsen nicht) |

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
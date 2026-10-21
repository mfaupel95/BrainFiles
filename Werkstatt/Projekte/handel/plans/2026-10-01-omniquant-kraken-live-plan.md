# Omniquant live auf Kraken Futures — Plan (01.10.2026, gebaut)

Auftrag Max: „Omniquant Handel Freigabe auf kraken live", nachgemeldet
**„aber mit perp und hebel x6"**.

Damit ist die Zielboerse **Kraken Futures** (Dienst
`https://futures.kraken.com/derivatives/api/v3`, PF_-Märkte), nicht der
Spot-Markt. Dieser Plan ist die Hausregel aus
`handel-spuren/references/live-schalten.md`: ein neuer echter Geldpfad wird
geplant, dann gebaut. **Gebaut ist er jetzt — scharf ist nichts.**

## 1. Was gebaut ist

| Datei | Aufgabe |
|---|---|
| `omniquant/kraken_perp.py` | Instrument-Abbildung (OKX-Name → PF_-Symbol), Sizing (`Nennwert = Einsatz × Hebel`), Hebel-Sperre, Durchreichen an den Haus-Orderweg |
| `omniquant/live_perp.py` | Sperrenkette, Einstieg (Marktkauf + Schutz-Stop), Live-Ausstiege, Fehlerzeilen |
| `omniquant/handeln.py` | sechs chirurgische Ersetzungen: Import, `sperren_live` delegiert, `sperren_zeile` (immer gedruckt), Live-Grenzen in `--wachen`, Papier-Ausstiege fassen `modus=live` nie an, live-bewusste Ein-/Ausstiege |
| `omniquant/wachen.json` | `boerse`, `hebel 6`, `live_einsatz_usd 50`, `live_max_offene_positionen 1`, `live_max_gesamt_usd 50`, `mindest_guthaben_usd 35`, `freigabe`-Block |
| `omniquant/tests/test_live_perp.py` | 20 Tests + Modulwächter |

Der Orderweg selbst ist **nicht neu gebaut**: Signatur, Nonce, flex-Konto und
Kontraktgröße liegen in `nautilus_kraken/kraken_futures.py` und waren dort schon
live bewiesen.

## 2. Fähigkeit der Zielboerse — GEMESSEN am 01.10.2026

`GET /derivatives/api/v3/instruments`, 300 Märkte:

| Omniquant führt | PF_-Markt | tradeable |
|---|---|---|
| STRK-USDT | `PF_STRKUSD` | ✓ |
| DOGE-USDT | `PF_DOGEUSD` | ✓ (nicht XDG wie im Spot) |
| XRP-USDC | `PF_XRPUSD` | ✓ |
| W-USDT | `PF_WUSD` | ✓ |
| FIL-USDT | `PF_FILUSD` | ✓ |
| ETC-USDT | `PF_ETCUSD` | ✓ |
| WLD-USDT | `PF_WLDUSD` | ✓ |
| ZEC-USDC | `PF_ZECUSD` | ✓ |
| ORDI-USDT | `PF_ORDIUSD` | ✓ |
| **MAGIC-USDT** | **kein Markt** | ✗ |

**9 von 10 handelbar.** Nur MAGIC-USDT bleibt Papier; `kraken_perp.paar_fuer`
wirft dafür einen lauten `ValueError` (nie still ersatzweise handeln).
Nebenbefund fürs Protokoll: im **Spot** wären es nur 8 von 10 gewesen (dort
fehlen ORDI und MAGIC), und DOGE heißt dort XDG statt DOGE.

**Ein Kontrakt ist die kleinste Order und bei jedem PF_-Markt genau 1 Einheit
der Basiswährung** (gemessen 25.09.2026: 1 Kontrakt PF_NEARUSD bei 4,5517 USD
belegte 0,4548 USD Marge). `contractSize: 1` im Instrumentenrecord sagt dazu
nichts.

## 3. Was „Hebel ×6" hier heißt

Kraken Futures kennt **keinen Hebel-Schalter je Order** — der Einschuss ist der
Margenplan des Marktes (EEA retail 10 %). „Hebel 6" ist deshalb eine
**Sizing-Regel**: `Nennwert = Einsatz × 6`, und die Börse fordert davon nur ihre
10 % an. Der Rest des Einsatzes bleibt freie Margin.

Bei 50 USD Einsatz je Position ergibt das 300 USD Nennwert ≈ 30 USD Einschuss:

```
DOGE-USDT  PF_DOGEUSD  kontrakte=3133  nennwert=299.95  einschuss=30.00  hebel_ist=6.00
XRP-USDC   PF_XRPUSD   kontrakte=199   nennwert=299.93  einschuss=29.99  hebel_ist=6.00
STRK-USDT  PF_STRKUSD  kontrakte=6846  nennwert=299.99  einschuss=30.00  hebel_ist=6.00
...
ZEC-USDC   PF_ZECUSD   kontrakte=1     nennwert=1436.99 einschuss=143.70 hebel_ist=28.74
```

**ZEC fällt heraus.** 1 Kontrakt kostet 1436,99 USD Nennwert — bei 50 USD Einsatz
also Hebel **28,7**, nicht 6. Das Aufrunden auf ganze Kontrakte darf den Hebel
nicht sprengen, deshalb sperrt `hebel_grund()` solche Fälle (Toleranz 25 %)
statt sie zu buchen. Ohne diese Sperre wäre ZEC die größte Position im Buch
gewesen, und am Hebel hätte es niemand gesehen.

**Risiko je Position:** ein Stop von x % kostet bei Hebel 6 rund 6x % des
Einsatzes. Der Hebel erhöht den Verlust je Position, nicht die Trefferchance.

## 4. Der Kontostand ist der Blocker (gemessen)

Das Kraken-Futures-**flex-Konto** (multiCollateral; `cash.balances` steht dort
immer auf 0 — wer nur cash liest, sieht 0 USD):

```
balanceValue        85.09     EUR  5.8614  -> available 1.1589
collateralValue     84.69     USDC 78.4357 -> available 1.3184
initialMargin       83.38  <- von drei offenen nautilus-Positionen belegt
availableMargin      1.31  <- frei
pnl                +12.63
```

Drei Positionen laufen dort bereits (nautilus_kraken_futures: SUI, HBAR, HYPE,
zusammen +12,63 USD im Plus) und binden **83,38 USD** als Einschuss auf ~799 USD
Nennwert — rund 9,6x, also praktisch die volle Ausnutzung.

**Frei sind 1,31 USD.** Stufe 1 braucht 30 USD Einschuss. Das Guthaben-Tor der
Spur steht deshalb zu — mit einer klaren Zahl, nicht mit einem Gefühl. Nach der
Hausregel ist das **kein Grund, nicht zu bauen, nur ein Grund, nicht scharf zu
schalten**.

## 5. Stufen und Beträge (Entscheidung Max)

- **Stufe 1 — ein Platz, 50 USD Einsatz (300 USD Nennwert, ~30 USD Einschuss).**
  `live_einsatz_usd 50`, `live_max_offene_positionen 1`, `live_max_gesamt_usd 50`,
  `mindest_guthaben_usd 35`. **Gesetzt.** Belegt wird sie durch einen echten
  Kauf, einen börsenseitigen Stop, eine Journalzeile `live` — und danach den
  Abgleich Buch ↔ Börse.
- **Stufe 2 — drei Plätze (150 USD Einsatz, ~90 USD Einschuss).** Erst wenn
  Stufe 1 sauber gebucht **und ausgebucht** ist.
- **Stufe 3 — Papierrahmen (10 × 50 USD).** Braucht ~300 USD freie Margin;
  heute nicht vorhanden.

**Vor Stufe 1 muss freie Margin her.** Wege, alle eine Entscheidung von Max:
(a) eine der drei nautilus-Positionen schließen, (b) Guthaben ins flex-Konto
legen, (c) `mindest_guthaben_usd` senken — was nur kleinere Positionen erlaubt,
nicht mehr Plätze.

## 6. Nachweis-Kette (vor jedem Scharfstellen)

1. ✅ Paar-Verfügbarkeit gegen `/instruments` — 9 von 10, MAGIC nicht.
2. ✅ Sizing gegen echte Kurse — 300 USD Nennwert je Position bei Hebel 6.
3. ✅ Hebel-Sperre — ZEC wird abgewiesen statt gebucht.
4. ✅ Sperrenkette — die Vorschau nennt JEDEN Grund einzeln.
5. ✅ Tests — 89 grün, kein Test erreicht `markt_kauf`, Modulwächter an.
6. ⬜ Freie Margin ≥ 35 USD.
7. ⬜ `handel_erlaubt` **und** `freigabe.erfuellt` — **beide Haken, und den
   Haken setzt Max.** Danach nennt die Vorschau nur noch Fenster und Guthaben;
   sobald nur das Fenster bleibt, öffnet der Dauerlauf die Anfrage selbst.

## 7. Offene Entscheidungen

1. **Welcher Weg schafft freie Margin** (nautilus-Position schließen / Guthaben
   legen / kleinerer Einsatz)? Empfehlung: Guthaben — die drei laufenden
   Positionen sind im Plus und tragen ihre eigene Strategie.
2. **Sollen die zehn Papierpositionen beim ersten Live-Lauf ausgebucht werden?**
   Nein — `pruefe_ausstiege` lässt `modus=live` stehen, Papierpositionen ohne
   `modus` werden weiter Papier gebucht. Es entsteht kein „Verlusttag" im
   Journal.
3. **ORDI und MAGIC**: ORDI ist auf Futures handelbar, MAGIC bleibt Papier.
   Einverstanden?

## 8. Was dieser Plan NICHT tut

Er schaltet nichts scharf. `handel_erlaubt` steht auf `false`,
`freigabe.erfuellt` auf `false`, omniquant steht **nicht** in
`dauerlauf.AUTO_FREIGABE`. Die Vorschau nennt vier Gründe, nicht einen — die
Auto-Freigabe fragt also nicht.

## 9. Nachtrag: ein Test hat ins echte Journal geschrieben

Beim ersten Lauf der neuen Tests hat `PapierLaesstLiveStehenTest` die Funktion
`pruefe_ausstiege` direkt gerufen; die schließt die Papierposition und
journalisiert sie. Vier Zeilen landeten im **echten** `handelsjournal.csv`
(01.10. 06:10–06:12 UTC, STRK zu Preis 1.0). Der Modulwächter in
`tests/test_live_perp.py` hat es gefangen, die Zeilen sind entfernt (Sicherung
`handelsjournal.csv.bak-20261001-081341`, 45 → 41 Zeilen), und die Testklasse
setzt jetzt `SCHREIBEN=False`. Das ist genau die Falle vom 16.09.2026 — ein
Test, der eine journalisierende Funktion direkt prüft, schreibt nach außen.
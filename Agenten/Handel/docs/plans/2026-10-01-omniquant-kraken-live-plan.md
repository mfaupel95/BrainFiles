# Omniquant auf Kraken live — Plan (01.10.2026)

Auftrag Max: „Omniquant Handel Freigabe auf kraken live".

Dieser Plan ist die Hausregel aus `handel-spuren/references/live-schalten.md`:
**ein neuer echter Geldpfad wird geplant, dann gebaut.** Er wird nicht eingebaut,
bevor Max ihn freigibt — und ein „ja" auf diesen Plan ist die Freigabe zum
BAUEN, nicht die Live-Freigabe (die bleibt der Haken `freigabe.erfuellt` plus
Freigabefenster).

## 1. Was heute da ist (gemessen, nicht erinnert)

- `omniquant/handeln.py` hat **keinen Orderpfad**. Docstring: „Kein Orderpfad.
  Kein Broker-Aufruf, keine Position am Markt. `--live` verweigert mit genau
  einem Grund, in dem das Wort Freigabefenster NICHT vorkommt."
- `wachen.json`: `handel_erlaubt: false`, **kein `freigabe`-Block**,
  `waehrung: "USD"`, `gebuehr_pct: 0.1`, `slippage_pct: 0.15`.
- Buch: 10 Papierpositionen (STRK, DOGE, XRP, ORDI, MAGIC, W, FIL, ETC, WLD, ZEC).
- Signalquelle: `prognose_berichte/neuester.weit.json` (`prognose_fassung: weit`).
- Grenzen: `max_einsatz_je_position_usd 50`, `max_offen 10`, `max_neu_je_zyklus 5`,
  `max_gesamt_risiko_usd 500`, `max_halte_dauer_tage 14`, Herzschlag 180.

## 2. Faehigkeit der Zielboerse — GEMESSEN am 01.10.2026

`GET /0/public/AssetPairs`, 1455 Paare, Feld `wsname`/`quote`/`status`:

| Omniquant führt | Kraken-Paar (EUR) | ordermin | costmin | pair_decimals |
|---|---|---|---|---|
| STRK-USDT | `STRKEUR` | 200 | 0.45 | 5 |
| DOGE-USDT | `XDGEUR` | 50 | 0.45 | 7 |
| XRP-USDC | `XXRPZEUR` | 1.65 | 0.45 | 5 |
| W-USDT | `WEUR` | 500 | 0.45 | 5 |
| FIL-USDT | `FILEUR` | 7 | 0.45 | 3 |
| ETC-USDT | `XETCZEUR` | 0.7 | 0.45 | 3 |
| WLD-USDT | `WLDEUR` | 11 | 0.45 | 4 |
| ZEC-USDC | `XZECZEUR` | 0.01 | 0.45 | 3 |
| **ORDI-USDT** | **kein Paar** | — | — | — |
| **MAGIC-USDT** | **kein Paar** | — | — | — |

**Ergebnis: 8 von 10 handelbar, 2 nicht.** ORDI und MAGIC bleiben Papier —
nach der Hausregel „nur die vertraeglichen bekommen den echten Orderweg".
DOGE heisst bei Kraken **XDG**, nicht DOGE.

**Quote ist EUR, nicht USD.** Alle acht gibt es in EUR; USDC nur fuer XRP und
XDG, EURC fuer keinen. Das Kraken-Konto traegt 53,81 EUR und 25,08 USDC —
EUR ist damit die einzige Waehrung, in der mehr als eine Position moeglich ist.
Nebenbefund: `kraken_paare.py` fuehrt keines dieser acht Paare — die Tabelle
muss dort ergaenzt werden, sonst greift die EINE Paar-Quelle nicht.

## 3. Was gebaut werden muss

1. `omniquant/kraken_spot.py` — Order-Modul nach dem Muster
   `mosaic/kraken_spot.py`, ruft dahinter `kraken/kraken.py`:
   `PAARE` (die acht aus Abschnitt 2), `paar_fuer(inst)` mit **lautem Fehler**
   bei Unbekanntem (ORDI/MAGIC/unbekannt — nie still ersatzweise handeln),
   `letzter_kurs`, `menge_fuer`, `guthaben_waehrung("EUR")`, `markt_kauf`,
   `markt_verkauf`, `stop_setzen`, `gefuellte_menge`, `schluessel_vorhanden`,
   `demo_modus`.
2. `omniquant/handeln.py` — **abgetrennter** Live-Zweig im eigenen Ordner
   (nicht `spur_buch.py` anfassen, das traegt neun Bot-Spuren):
   - `SPUR = "omniquant"`, eigener Fensterschluessel.
   - `zeitfenster_offen()` **ueber den PFAD** laden (`spec_from_file_location`),
     nicht per blankem `import freigabefenster` — sonst meldet der
     best-effort-`except` „kein Zeitfenster", obwohl das Fenster offen ist.
   - Sperrtext mit **beiden** Wegen zu Punkt 3 (Bildschirm ODER Zeitfenster);
     `sitzung_da()` allein ist im Dauerlauf immer False (`MAXHIRN_ROUTINE=1`).
   - `sperren_zeile()` auch im `--vorschau`-Weg drucken — sonst liest
     `dauerlauf.nur_fenster_fehlt()` nichts und die Auto-Freigabe fragt nie.
   - Schutz-Stop **direkt nach dem Kauf**; eine nackte Live-Position ist kein
     Handel, sondern ein offenes Risiko.
   - Positionen tragen `modus`; Papierpositionen werden im Live-Lauf **nie**
     geordert (sonst verkauft der erste Zyklus, was es nicht gibt).
   - Jede Fehlerstelle im Live-Pfad schreibt eine Journalzeile
     (`aktion="fehler"`, `grund=<Meldung>`), damit ein ausbleibender Einstieg
     eine beantwortbare Frage ist statt stumm.
   - Jeder Ausgang schreibt Zustand und spiegelt (auch der abbrechende) —
     sonst bleibt das Herzschlag-Tor fuer immer zu (Deadlock).
3. `wachen.json`: `boerse: "kraken"`, `kraken_quote: "EUR"`, `freigabe`-Block,
   `live_einsatz_eur`, `live_max_offene_positionen`, `live_max_gesamt_eur`,
   `mindest_guthaben_eur`. Der Live-Einsatz traegt den **Waehrungsnamen**.
4. Verdrahtung: `freigabe.py` (`WACHEN`, `SPOTARTIG`, `BETRAGSFELD`, `TITEL`,
   `RECHNER`), `dauerlauf.AUTO_FREIGABE`, `spuren_stand`, `sperrgruende`,
   `.gitignore`-Freigabe je neuer Datei.
5. Tests: Paar-Abbildung (unbekannt = Fehler), Sperrenkette mit Attrappen,
   Papier-Position wird im Live-Lauf nicht geordert, Vorschau schreibt nicht.
   **Keine Suite darf `--live` fahren, sobald die Spur freigegeben ist.**

## 4. Stufen und Betraege (Entscheidung Max)

Frei sind heute **53,81 EUR** (Kraken) — nicht 500 USD wie der Papierrahmen.

- **Stufe 1 — ein Platz, 50 EUR.** `live_einsatz_eur 50`,
  `live_max_offene_positionen 1`, `live_max_gesamt_eur 50`,
  `mindest_guthaben_eur 55`. Belegt: ein echter Kauf, ein boersenseitiger Stop,
  eine Journalzeile `live`. Danach Bilanz gegen die Boerse.
- **Stufe 2 — drei Plaetze, 3 x 40 EUR** (120 EUR), erst wenn Stufe 1 sauber
  gebucht und ausgebuht ist.
- **Stufe 3 — Papierrahmen (10 x 50 USD).** Setzt voraus, dass Kraken-Guthaben
  in EUR in dieser Groessenordnung liegt — heute nicht der Fall.

**Waehrungs-Entscheidung noetig:** Omniquant fuehrt sein Buch in **USD**,
Kraken-Paare rechnen in **EUR**. Zwei Wege: (a) Buch auf EUR umstellen (dann
sind die zehn Papierpositionen in USD nicht mehr vergleichbar), oder (b) Buch
bleibt USD, der Live-Zweig rechnet je Position zum Tageskurs um. Empfehlung:
**(a) fuer den Live-Zweig ein eigenes Buch in EUR** — zwei Waehrungen in einer
Zahl sind spaeter nicht mehr auseinanderzuhalten.

## 5. Nachweis-Kette (vor jedem Scharfstellen abzuarbeiten)

1. Kerzen und Paar-Info je Instrument gegen Kraken (die acht aus Abschnitt 2).
2. Guthaben: `guthaben_waehrung("EUR")` gegen den echten Kontostand.
3. Order **ohne echte Ausfuehrung** pruefen — `kraken._add_order(..., echt=False)`
   rechnet nur durch; Preis auf `pair_decimals` gerundet (ein roher Rechenwert
   wird abgelehnt, `EOrder:Invalid price`).
4. `handeln.py --live` mit `MAXHIRN_ROUTINE=1`: die Kette nennt genau die
   offenen Gruende, ohne eine Order zu stellen.
5. `--vorschau` nennt GENAU EINEN Grund und darin das Wort „Freigabefenster" —
   erst dann oeffnet der Dauerlauf die Anfrage.
6. Erst danach `freigabe.erfuellt` und `handel_erlaubt` — **beide** Haken, und
   den Haken setzt Max.

## 6. Offene Entscheidungen

1. **Stufe 1 mit 50 EUR freigeben?** (Empfehlung: ja, ein Platz.)
2. **Buch in EUR oder USD?** (Empfehlung: eigener EUR-Zweig.)
3. **ORDI und MAGIC bleiben Papier** — einverstanden?
4. Sollen die zehn bestehenden Papierpositionen beim ersten Live-Lauf als
   Altlast ausgebucht werden (`bueche_papier_altlasten_aus`, Journal-Grund
   `buchbereinigung`)? Das ist gewollt, sieht aber im Journal wie ein
   Verlusttag aus — vorher sagen.

## 7. Was dieser Plan NICHT tut

Er schaltet nichts scharf. `handel_erlaubt` bleibt `false`, `freigabe.erfuellt`
existiert noch nicht, `AUTO_FREIGABE` nennt omniquant nicht. Der Bau der Stufen
2 und 3 ist nicht Teil der Freigabe zu Stufe 1.
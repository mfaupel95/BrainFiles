# robinhood_radar — Papierbuch auf bewerteten Wallets (Robinhood Chain)

**Auftrag Max 22.09.2026:** „Radar -papierspur und -bot".

## Was gemessen wird

Der FOMO-Robinhood-Radar (`Werkstatt/Repos/fomo-robinhood-radar`, Fremd-Repo,
Fork `mfaupel95`) liest die On-Chain-Aktivität von Tradern auf **Robinhood
Chain (Chain-ID 4663)** und bewertet die Wallets mit einem Sprachmodell
(Score 0–100). Diese Spur kopiert **nicht die Rangliste** — das wäre
Zuchtauswahl nach dem Ergebnis — sondern das **Geschehen**:

> Kauft eine Kohorte von mindestens zwei **verschiedenen** bewerteten Wallets
> (Score ≥ 60, Status ≠ `dropped`) denselben Token innerhalb von sechs
> Stunden, ist das ein Signal.

Zusätzlich blockiert der **Verkaufsdruck derselben Kohorte**: Hat sie im
selben Fenster mehr verkauft als gekauft, entfällt das Signal (sonst kauft
die Spur in einen Abverkauf hinein). Nur **long** — auf dieser Kette gibt es
für uns keinen Leerverkauf.

## Der Weg der Daten

    Radar-CLI  →  fomo_agent.db (SQLite)  →  robinhood_radar/lesen.py  →  Buch

* **Der Radar sammelt**, diese Spur liest. `lesen.py` öffnet die Datenbank
  mit `mode=ro` und lehnt jede Anweisung ab, die nicht mit `SELECT`/`WITH`/
  `PRAGMA` beginnt.
* **Kein `subprocess`, kein Netz** im Zyklus: die Spur ist offline testbar,
  die Datenquelle ist über `FOMO_RADAR_DB` als Naht austauschbar.
* Frisch gehalten wird die Datenbank vom Hermes-Cron **`radar-sammler`**
  (Skript `Agenten/Hermes/scripts/radar-sammeln.py`), nicht von der Spur.

## Der laufende Kurs (T-299)

Die Spur bucht den Einstiegspreis aus der eigenen Sammlung; einen **laufenden
Kurs** liefert die Radar-Datenbank seit dem 02.10.2026: der Sammler
(`radar-sammeln.py`) ruft jetzt auch `enrich-tokens` auf, und der bepreist
die gehaltenen Token über **GeckoTerminal** — den einzigen Kursgeber für
Robinhood Chain 4663 (DexScreener indexiert die Kette nicht). Preise stehen
in `tokens.price_usd`/`price_at` und werden je `price_max_age_s` (2 h) für
gehaltene Token erneuert. Tote Token ohne aktiven Pool (keine der drei
offenen Positionen hat einen) bekommen von keiner Quelle einen Live-Kurs.

## Kosten, ehrlich gerechnet

Einstiegspreis ist der Preis des **jüngsten beobachteten Kaufs**
(`usd_value / token_amount`, on-chain belegt) mit **+2 % Nachlauf** — der
Radar sammelt im Takt, die eigene Buchung liegt hinter dem Vorbild. Dazu
**1 % Gebühr je Seite** (`gebuehr_taker`). Eine Kopie ohne Kursbewegung ergibt
damit ein Minus; das ist Absicht, keine Ungenauigkeit.

**Gemessen am 01.10.2026** mit `handeln.py --messen` (rein lesend über die
eigene Sammlung, Rohwerte in `daten/messung.json`): 3529 Füllungen, davon
1979 Käufe mit einer nächsten Beobachtung. Nachlauf-Median **+1,76 %**
(p25 −2,63 %, p75 +9,10 %, Schnitt +10,21 %). Im **Signalfall** — nur die
Käufe, die unsere Regel genommen hätte (Kohorte ≥ 2 bewertete Wallets) —
n=19: Median **+2,87 %**, Schnitt +9,89 %, kleinster +0,14 %. Der gesetzte
Aufschlag von 2,0 % liegt damit **am Median, nicht darüber**. Abstand Signal →
nächste Beobachtung: Median 86 s.

Die **Gebühr selbst ist in diesen Daten nicht messbar** — sie steckt im
Poolpreis, die Sammlung führt kein Gebührenfeld. Sie bleibt eine Annahme und
ist als solche in `wachen.json` benannt. Neu messen, wenn die Sammlung
deutlich größer ist oder die Spur live gehen soll.

## Aufruf

```bash
cd Agenten/Handel/robinhood_radar
<Handel>/scanner/.venv/Scripts/python.exe handeln.py --vorschau   # nichts schreiben
<Handel>/scanner/.venv/Scripts/python.exe handeln.py --papier     # Papierzyklus
<Handel>/scanner/.venv/Scripts/python.exe handeln.py --wachen     # Grenzen zeigen
<Handel>/scanner/.venv/Scripts/python.exe handeln.py --messen     # Nachlauf messen
```

`--live` verweigert mit Grund: **es gibt keinen Orderweg.** Robinhood Chain
ist in diesem Haus nicht angebunden, und ein Live-Weg bräuchte zuerst
Sperrenkette, Freigabekette und einen echten Handelsplatz.

## Stand und was offen ist

* Angelegt 22.09.2026, im Dauerlauf (`dauerlauf.SPUREN`), Buch über
  `Handel/spur_buch.py`, Spiegelung nach `Q:\Handel_Journal\robinhood_radar`.
* **`handel_erlaubt: false`, `freigabe.erfuellt: false`** — Papier. Der Haken
  wird von Hand gesetzt, nie vom Agenten.
* **Gesetzt, nicht gemessen:** `stop_prozent 25 %` und
  `ziel_r_vielfaches 2,0`. Für Memecoins auf einer jungen Kette liegt noch
  keine eigene Stichprobe vor; nach 50 Runden gegen die Messung stellen
  (Handelsregeln Bedingung 1).
* Nur **ein** neuer Einstieg je Zyklus (`max_neue_je_zyklus`), der stärkste
  Kandidat zuerst — sonst füllt der erste Zyklus mit Daten das ganze Buch,
  und die Auswertung kann nicht zeigen, welcher Rang trägt.

Tests (offline, keine echten Dateien):

```bash
cd Agenten/Handel/robinhood_radar/tests
<Handel>/scanner/.venv/Scripts/python.exe -m unittest test_robinhood_radar
```
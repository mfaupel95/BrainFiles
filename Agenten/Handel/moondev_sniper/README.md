# moondev_sniper

Papierbuch-Spur auf den **neuen Solana-Token-Launches** von Pump.fun. Der
Vorbild-Agent `sniper_agent` aus `Werkstatt/Repos/moon-dev-ai-agents` scannt
neue Launches und zeigt sie an - er faellt **kein eigenes Urteil**
(Anzeige-Scanner mit Animation und Sound). Seine Datenquelle ist der tote
Eigen-Server des Autors (`api.moondev.com`), deshalb holt diese Spur denselben
Inhalt ueber die oeffentliche Pump.fun-API.

## Quelle

- `frontend-api-v3.pump.fun/coins?sort=created_timestamp&order=DESC` - die
  neuesten Launches mit Alter, Marktwert und Liquiditaet (kein Schluessel).
- `swap-api.pump.fun/v2/coins/<mint>/trades?limit=1` - der letzte gehandelte
  Preis je Token (kein Schluessel).

Das ist **nicht der Bot selbst** (er haengt an `api.moondev.com`, das tot
ist), sondern derselbe Dateninhalt oeffentlich. Implementierung:
`Handel/moondev_daten.py` (nur Standardbibliothek, `urllib`).

> Preis-Bemerkung: Der Marktwert laesst sich nicht in einen Preis rechnen
> (die `total_supply` stimmt nicht mit der gehandelten Menge eines Paars
> ueberein - Faktor 10^6 Diskrepanz, gemessen 19.09.). Genommen wird der
> letzte Swap-Preis (`priceUsd`).

## Regel

Ein neuer Launch wird **long** gekauft, wenn er:

1. jung ist (Alter <= `max_alter_minuten`, Vorgabe 60 Minuten),
2. nicht gebannt oder nsfw ist,
3. seinen Marktwert im Band `marktkap_band_usd` hat (Vorgabe 200 ... 100 000
   USD - nicht tot, nicht schon ausgewachsen),
4. einen echten Preis hat.

Stop und Ziel nach Haus-Muster (`risiko_je_position_usd` -> Nominal,
`stop_prozent`, `ziel_r_vielfaches`). Kein Sprachmodell, kein Wallet.

## Buch

`Handel/spur_buch.py` (Zustand, Journal, Q:-Spiegel = Bedingung 4, Ratsche,
Stop/Ziel). Positionsliste im Zustand, `kauf`/`verkauf` im Journal,
ausgewertet ueber `auswertung_alle.BOT_SPUREN`.

## Grenzen

- **Kein Live-Zweig.** Die Fremd-Agenten handeln mit echten Schluesseln und
  einer Wallet; ein `--live` verweigert.
- **Kein Sprachmodell.** Die Richtung ist eine Haus-Regel, nachrechenbar.
- **Risiko-Vorfilter aktiv** (`risikovorfilter: true`, Regeln des Moon-Dev
  `risk_agent`): kein NEUER Einstieg nach gerissener Verlustgrenze oder
  erreichtem Gewinnziel im 12-h-Fenster. Schliesst keine Position.
- **Slippage ist real.** Der Preis kommt vom letzten Swap-Trade. Bei frischen
  Launches mit duenner Liquiditaet kann der Kurs zwischen zwei Zyklen durch
  den Stop rutschen - der 8-%-Stop wird dann mit deutlich groesserem Verlust
  ausgefuehrt (gemessen 19.09.2026: -37.59 USD bei 62.50 Nominal). Das ist
  kein Bug, sondern die ehrliche Abbildung der Memecoin-Realitaet.
- **Rate-Limit.** swap-api.pump.fun deckelt hart (HTTP 429). Nur die
  `max_offene_positionen` juengsten Kandidaten bekommen einen Preis, nicht
  alle 40 - sonst reisst der Deckel und die Spur liefert nichts.

## Aufruf

```
python handeln.py --vorschau | --papier | --wachen
```

## Tests

Aus `moondev_sniper/tests`:

```
python -m unittest test_moondev_sniper
```

Tests laufen ohne Netz (Quelle durch Lambda ersetzt) und schreiben nie in den
echten Spurenordner (SCHREIBEN=False + Modulwaechter).
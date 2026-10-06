# OKX-LIVE-PLAN — mosaic (erster echter OKX-Geldpfad im System)

> Stand: 2026-09-19, von Hermes nach Rücksprache mit Max geschrieben.
> **Dies ist ein PLAN zur Prüfung, kein genehmigter Umbau.** Nichts hierin
> ist gebaut. `handel_erlaubt` bleibt `false`, bis Max einen weiteren Schritt
> freigibt. Jeder Bau-Schritt braucht eine eigene Bestätigung mit
> Betragshöhe. Ein „ja“ auf diesen Plan ist NICHT die Live-Freigabe.

> **STAND 2026-09-19 (Stufe A gebaut, nichts scharf):** Der abgetrennte
> OKX-Spot-Orderweg ist gebaut (Commit `be62611` + Folge-Commit):
> `mosaic/okx_spot.py`, Live-Zweig in `mosaic/handeln.py` (Sperrenkette,
> Freigabefenster, Notaus), Freigabefenster-Eintrag in `freigabe.py`,
> Live-Grenzen 10/5/200 + `freigabe`-Block in `wachen.json`, Tests 25/25 grün.
> `--live` ist gesperrt und zeigt die offenen Sperren namentlich (gemessen):
>   1. `handel_erlaubt=false`
>   2. `freigabe.erfuellt=false` (Bedingung 1 — 1 Papierrunde, braucht 50)
>   3. `OKX_DEMO/OKX_SIMULATED` gesetzt (Demo-Konto)
>   4. OKX-Keys passen nicht zur Basis: `50101 APIKey does not match current
>      environment` — vermutlich EEA-Portal-Key, braucht `OKX_BASE=
>      https://eea.okx.com`.
> Keine echte Order ist bisher ausgeführt worden und keine geht, solange eine
> dieser Sperren offen ist.

## 1. Was wir bauen wollen

Mosaic bekommt einen **eigenen, abgetrennten Live-Zweig** in seinem
`handeln.py`, der mit echtem Geld an der Börse OKX handelt. Papier läuft
parallel unverändert weiter (der Dauerlauf startet mosaic weiter `--papier`).

- Echte Orders gehen **ausschließlich** über diesen neuen Live-Zweig.
- `handel_erlaubt=false` ist die zentrale Sperre; erst wenn Max über die
  Freigabekette (Bildschirmfenster `freigabe.py` oder `/ja_mosaic`) UND
  `handel_erlaubt=true` bestätigt, kann eine echte Order entstehen — und
  selbst dann wirken die Sperren der Kette.

Beleg Ist-Stand (2026-09-19):
- `mosaic/wachen.json`: `handel_erlaubt: false`, kein `freigabe`-Block.
- `mosaic/handeln.py`: `--live` bricht ab mit „`--live verweigert: Papier-Spur,
  keine Orders moeglich`" — es gibt heute **keinen** Live-Orderpfad.
- 1 geschlossene Papierrunde (+10,82 %), 4 offene Papier-Positionen.

## 2. Die ehrliche technische Wahrheit zuerst

Mosaic ist eine **Long-only-Preisaktions-Strategie** (4H-Bias → 30M-Nachfragezone
→ 5M-Structure-Shift, „Top-down long"). Die Signale sind Long, kein Short. Das
passt zu OKX-Spot, der nur kaufen/verkaufen kann, was man hält.

| | OKX Spot (Ziel) |
|---|---|
| Order | `POST /api/v5/trade/order`, `side=buy/sell`, `instId=BTC-USDT` |
| Short | — (nur verkaufen, was man hält) |
| Hebel | kein Hebel, kein Margin, kein Futures |
| Risiko | Verlust = Position (betragsteil) |
| Schlüssel | braucht `Trade`-Recht UND IP-Whitelist für Orders |
| Guthaben | USDT |
| Instrumente | `BTC-USDT`, `ETH-USDT`, `SOL-USDT` — **alle drei als Spot geführt** (geprüft 2026-09-19 via öffentliche Instrumenten-API) |

**Konkret was heute fehlt:**
1. **Kein OKX-Orderweg** im System. Die moondev-/Bot-Spuren rechnen über
   `spur_buch.py`, das ausdrücklich „Kein Live-Zweig" ist — Mosaic braucht
   seinen **eigenen** abgetrennten Order-Zweig (nach dem Kraken-Muster in
   `kraken/handeln.py`, nur mit OKX-Signatur statt Kraken-Signatur). Der
   gemeinsame Buchkern wird dabei **nicht** live-fähig gemacht.
2. **Key-Berechtigung fehlt.** Die hinterlegten OKX-Schlüssel sind nach
   Systemstand `read_only` und die IP-Whitelist für Orders ist offen. Eine
   echte Order würde OKX mit `51004`/Whitelist-Fehler ablehnen. Das korrigiert
   Max im OKX-Dashboard selbst (Portal-Aktion, gehört nicht in einen Agenten).
3. **Kein `freigabe`-Block** in wachen.json — die Freigabekriterien
   (`papierlauf_min_runden`, `netto_positiv`, `groesster_ruecklauf`) sind für
   Mosaic gar nicht eingerichtet. Aktuell **1** Papierrunde — unter jeder
   sinnvollen Mindestzahl (Hausreferenz: xperp 50, scanner 8+).

## 3. Empfehlung (eine, begründet): in drei Stufen

### Stufe A — Long echt, kleinst möglich (empfohlener erster Schritt)
- Eigener Live-Zweig in `mosaic/handeln.py` nach dem Vorbild
  `kraken/handeln.py` (Sperrenkette, `journal_zweitziel` auf Q:,
  Herzschlag 45 min).
- Eigene OKX-Order-Anbindung (HMAC-SHA256-Signatur, `POST /api/v5/trade/order`),
  Spot, ohne Hebel.
- Signal long → echte `buy` auf das jeweilige Instrument, kleinstmöglicher
  Betrag (Vorschlag 10 USDT pro Trade), 1 offene Position, Gesamtdeckel klein.
- Vor jedem Trade: Stop-Loss als Börsen-Order (`/api/v5/trade/order-algo`),
  überlebt Neustart; Ziel als Limit.
- Konto-Vorbedingung prüfen: `guthaben("USDT")` > Betrag, Key darf Ordern
  (nicht read_only), IP-Whitelist steht.

### Stufe B — Freigabekriterien für Mosaic einrichten
- `freigabe`-Block in wachen.json ergänzen (Mindest-Papierrunden, netto
  positiv, Rücklauf-Grenze) und den Papierlauf bis dahin weiterlaufen lassen.
- Erst wenn Bedingung 1 erfüllt ist, spielt die Freigabekette überhaupt eine
  Rolle.

### Stufe C — Auswertung, die beide Welten kennt
- `auswertung_alle.py` (bzw. der Mosaic-Holer) weist echte Live-Runden
  getrennt von Papier-Runden aus, damit eine Freigabe nie aus einem
  Live/Papier-Mix zählt.

## 4. Warum Stufe A zuerst

1. **Erster echter OKX-Geldpfad.** Alles bisher ist OKX-Papier; echte
   OKX-Order-Signatur und -Beträge sind unerprobt. Ein Hebel-/Futures-Weg
   wäre überproportional riskant.
2. Mosaic ist strukturell **Long-only-Spot** — Stufe A ist genau die Strategie,
   ohne einen zweiten Risiko-Stack (Margin, Liquidationsrisiko) einzuführen.
3. Stufe A beantwortet die Grundfragen (funktioniert die OKX-Signatur, läuft
   Stop/Ziel echt, stimmen die Beträge) mit kleinstmöglichem Risiko. Danach
   kann der Papierlauf die Freigabekriterien füllen.

## 5. Sicherheitsdesign (für jede Stufe)

- **Sperrenkette** nach `kraken/handeln.py`:
  1. `handel_erlaubt == true` (wachen.json)
  2. OKX-Key/Secret gesetzt (aus der Spur-`.env`)
  3. `--live` ausdrücklich auf der Kommandozeile
  4. `freigabe.erfuellt == true` (Bedingung 1, noch gar nicht definiert)
  5. Herzschlag frisch (45 min)
  6. rollierender Erwartungswert nicht negativ (Bedingung 5)
  7. `journal_zweitziel` gesetzt und erreichbar (Bedingung 4, Q:)
  8. mindestens `mindest_guthaben_usdt` frei
  9. Freigabefenster-Sitzung aktiv
- Fehlt eine Sperre: **Papier** handeln und MIT GRUND sagen, welche Sperre zu war.
- Kein Short, kein Hebel. Stop-Loss als Börsen-Order (Order-Algo), keine
  skript-bewachte Position.
- Maximalbetrag pro Trade klein (Stufe A: 10 USDT), `max_offene_positionen` 1,
  Gesamtdeckel klein.
- Live wird **nie aus einem Chat-/A2A-Befehl scharf** — nur die Freigabekette.
  Ein „ja“ auf den Plan ist NICHT die Freigabe.

## 6. Nachweis-Kette (was „gefechtsbereit" heißt, konkret)

Stufe A ist erst dann „gefechtsbereit", wenn ALL das echte Ergebnisse sind:
1. `okx.kerzen("BTC-USDT", …)` liefert echte OKX-Kerzen (4H/30M/5M).
2. Instrumenten-Status: `BTC-USDT`/`ETH-USDT`/`SOL-USDT` sind `live`, nicht
   pre-open (Spot-Sortiment, geprüft).
3. `guthaben("USDT")` läuft (leer meldet nur: Key vorhanden, kein Guthaben-Fehler).
4. Order-Signatur-Vorprüfung: eine validierte Order ohne echte Ausführung
   (OKX-Dry-Run, `POST` mit `tdMode=cash`-Prüfung oder gecaptem Betrag) wird
   angenommen — **ohne** eine echte Order zu erzeugen.
5. `mosaic/handeln.py --vorschau` rechnet Long sauber.
6. `--live` mit gesperrter Kette sagt, welche Sperre zu war (nichts passiert).
7. Erste echte Order (Kleinstbetrag) nur NACH explizitem Befehl, mit vorher
   gezeigter Betragshöhe, Stop, Ziel.

## 7. Was ich NICHT mache (weder jetzt noch in Stufe A)

- Kein Margin-/Futures-/Short-Code.
- Kein Ändern des gemeinsamen Buchkerns `spur_buch.py` live-fähig (würde auf
  alle OKX-Bot-Spuren drucken; Mosaic bekommt seinen eigenen Zweig).
- Kein Live-Scharfschalten aus irgendeiner Nachricht heraus.
- Keine echten OKX-Order ohne vorher gezeigten Betrag, Stop, Ziel.
- Kein Berühren der Freigabedatei in einen Zustand `true`.
- Kein Lesen/Ausgeben von `Wissen/OKX_API.env` — das Key-Recht stellt Max im
  OKX-Dashboard selbst um.

## 8. Entscheidungspunkte für dich (= warte auf deine Antwort)

1. **Freigabe Stufe A bauen?** Dann baue ich den abgetrennten OKX-Live-Zweig
   (Long, BTC/ETH/SOL-USDT, Kleinstbetrag, Sperrenkette + Tests). Papier läuft
   weiter. Kein Schalter geht an.
2. **Betragshöhe Stufe A** (Vorschlag: 10 USDT pro Trade, 1 offene Position,
   Gesamtdeckel 30 USDT). Sag eine Höhe oder bestätige.
3. **OKX-Key-Berechtigung** (Max im Dashboard): Key auf `Trade` stellen UND
   die IP-Whitelist füllen. Erst dann kann eine spätere echte Order überhaupt
   ankommen.
4. Stufe B (Freigabekriterien + Papierlauf bis 50 Runden) läuft parallel zum
   Bau — die echte Freischaltung kommt erst, wenn Bedingung 1 erfüllt ist.

## Wechsel auf USDC (21.09.2026)

Max: "Auf okx usdc nehmen!". Die Spur handelte gegen USDT-Paare, waehrend im
OKX-Konto gar kein USDT lag - das Guthaben-Tor ("mindest_guthaben_usdt 30")
war damit dauerhaft zu, obwohl 255 USDC frei lagen. Jetzt:

- `instrumente`: BTC-USDC / ETH-USDC / SOL-USDC (dieselben Maerkte, andere
  Quote-Waehrung; die Kerzen kommen aus demselben oeffentlichen Endpunkt),
- `mindest_guthaben_usdc` 30.00 ersetzt `mindest_guthaben_usdt`,
- `okx_spot.guthaben_waehrung(ccy)` mit Standard USDC; `guthaben_usdt()` bleibt
  als Altname erhalten.

Wirkung: das Guthaben-Tor ist offen (Vorschau: "Live waere gesperrt durch:
nichts"), die Freigabekette bleibt unveraendert - ohne offenes Fenster laeuft
die Spur Papier.

## Beobachtung im Live-Betrieb (21.09.2026)

Max: "Einsatz erstmal so lassen und beobachten." Die Grenzen bleiben damit
bei 10 USDC je Position, 5 Plaetzen und 200 gesamt. Die Beobachtung
uebernimmt der Hermes-Cron `mosaic-live-wache` (alle 10 Minuten, no_agent,
Skript `Agenten/Hermes/scripts/mosaic-live-wache.py`):

- meldet jede NEUE Live-Zeile im Journal (also den ersten echten Einstieg -
  er ist zugleich der Beweis, dass der Schluesselsatz ordern darf),
- meldet den Fensterwechsel (live -> Papier, Papier -> live),
- schweigt, wenn nichts passiert (leere Ausgabe = keine Nachricht),
- fuehrt seinen Stand in `Agenten/Hermes/cache/mosaic-live-wache.json`.

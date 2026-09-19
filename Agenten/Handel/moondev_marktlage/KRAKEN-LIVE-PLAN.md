# KRAKEN-LIVE-PLAN — moondev_marktlage (erster echter Geldpfad im System)

> Stand: 2026-09-19, von Hermes nach Rü cksprache mit Max geschrieben.
> **Dies ist ein PLAN zur Prüfung, kein genehmigter Umbau.** Nichts hierin
> ist gebaut. `handel_erlaubt` bleibt überall `false`, bis Max einen
> weiteren Schritt freigibt. Jeder Bau-Schritt braucht eine eigene
> Bestätigung mit Betragshöhe.

## 1. Was wir bauen wollen

marktlage bekommt einen **eigenen, abgetrennten Live-Zweig** in seinem
`handeln.py`, der mit echtem Geld an der Börse Kraken handelt. Papier läuft
parallel unverändert weiter (der Dauerlauf startet marktlage weiter `--papier`).

- Echte Orders gehen **ausschließlich** über diesen neuen Live-Zweig.
- `handel_erlaubt=false` ist die zentrale Sperre; erst wenn Max über die
  Freigabekette (Bildschirmfenster `freigabe.py` oder `/ja_moondev_marktlage`)
  UND `handel_erlaubt=true` bestätigt, kann eine echte Order entstehen —
  und selbst dann wirken 9 unabhängige Sperren.

## 2. Die ehrliche technische Wahrheit zuerst (gelesen im Code 2026-09-19)

Die vorhandene Anbindung `Agenten/Handel/kraken/kraken.py` kann **nur
Spot**: `markt_kauf`/`markt_verkauf` (buy/sell), `stop_setzen` als
Stop-Loss, kein Hebel, **kein Short**. Sie ist der vorbildliche Weg für
Long.

Der Wunsch **„Long UND Short mit Hebel“** ist auf diesem Weg NICHT
machbar. Short mit Hebel ist **Kraken-Margin-Trading** — ein anderer
mechanischer Pfad:

| | Spot (vorhanden) | Margin (fehlt) |
|---|---|---|
| Order | buy / sell | AddOrder mit `leverage` (z. B. `leverage:b:3`) |
| Short | — (nur verkaufen, was man hält) | Leerverkauf von geliehenem Kapital |
| Absicherung | Stop-Loss-Order | positionsabhängige Margin-Absicherung (`MarginOrder` / Stop in Einheiten), Liquidationsrisiko |
| Risiko | Verlust = Position | Verlust kann Kontostand übersteigen (Nachschusspflicht) |
| Schlüssel | Reicht der Spot-Key? | Braucht **eigenen Margin-Schlüssel** mit Margin-Recht; der vorhandene Key ist für Spot konfiguriert |
| Guthaben | ZEUR | Margin-Guthaben + freigegebenes Margin-Kontingent |
| API | private/AddOrder (vorhanden) | Margin-spezifische Endpunkte, teils andere Signatur |

**Konsequenz für den Plan:** Short mit Hebel ist ein **eigenes Teilprojekt**
mit deutlich höherem Risiko und eigener Freischaltung (Margin-Schlüssel,
Kontingent, Margin-API). Es gehört NICHT in den ersten Schritt.

## 3. Empfehlung (eine, begründet): in drei Stufen

### Stufe A — Long echt, kleinst möglich (empfohlener erster Schritt)
- Eigener Live-Zweig in `moondev_marktlage/handeln.py` nach dem Vorbild
  `kraken/handeln.py` (9-Fach-Sperrenkette, `journal_zweitziel` auf Q:,
  Herzschlag 45 min).
- Nutzt die vorhandene `kraken.py`-Anbindung (Spot, kein neuer Schlüssel,
  keine Margin).
- Signal: marktlage long → echte `markt_kauf` auf `XBT/USD`
  (kleinstmöglicher Betrag, z. B. 10 EUR, erst nach Freigabe).
- short-Signal: wird **ignoriert** bzw. schließt nur eine evtl. offene
  Long-Position (kein Leerverkauf). So bleibt Stufe A ohne Hebel-Risiko.
- Konto-Vorbedingung prüfen: `kraken.guthaben("ZEUR")` > Betrag, Key darf
  Ordern (nicht read_only), IP-Whitelist für Orders.

### Stufe B — Short echt über Kraken-Margin (eigenes Teilprojekt)
- Neuer Pfad, neuer Schlüssel (Margin-Recht + freigegebenes Kontingent),
  Margin-API-Anbindung, `leverage`-Begrenzung hart auf 2:1, Absicherung
  hart. Das ist ein **separater Plan** mit eigenem Freigabe-Datum.

### Stufe C — Auswertung, die beide Welten kennt
- `auswertung_trading.py` erweitern, damit echte Runden (Live-Journal)
  von Papier-Runden getrennt ausgewiesen werden — damit Bedingung 1
  (50 Runden netto positiv) nie aus einem Mix aus Live/Papier zählt.

## 4. Warum Stufe A zuerst (nicht sofort Long+Short)

1. **Erster Geldpfad des Systems.** Alles bisher ist Papier. Ein fehlerbehafteter
   erster Live-Schritt mit Hebel wäre unverhältnismäßig riskant.
2. **Short-Hebel ist strukturell anders** (Margin-Schlüssel, Kontingent,
   Nachschusspflicht) — in einem Schritt bauen hieße zwei neue Risiken auf
   einmal.
3. **Stufe A beantwortet die Grundfrage** (funktioniert die Freigabekette mit
   echtem Geld, läuft Stop/Ziel, stimmen die Beträge) mit dem
   kleinstmöglichen Risiko. Danach kann Stufe B auf belegtem Boden stehen.
4. Die Haus-Kraken-Spur ist selbst „nur Long“ (Zeile 3 in ihrem handeln.py)
   — Stufe A folgt dem bewährten Hausmuster.

## 5. Sicherheitsdesign (für jede Stufe)

- **9-Fach-Sperrenkette** wie `kraken/handeln.py` Zeile 16:
  1. `handel_erlaubt == true` (in wachen.json)
  2. `KRAKEN_API_KEY`/`SECRET` gesetzt
  3. `--live` ausdrücklich auf der Kommandozeile
  4. `freigabe.erfuellt == true` (Bedingung 1: 50 Runden netto positiv)
  5. Herzschlag frisch (45 min)
  6. rollierender Erwartungswert nicht negativ (Bedingung 5)
  7. `journal_zweitziel` gesetzt und erreichbar (Bedingung 4, Q:)
  8. mindestens `mindest_guthaben_eur` frei
  9. Freigabefenster-Sitzung aktiv
- Fehlt eine Sperre: **Papier** handeln und MIT GRUND sagen, welche Sperre zu war.
- **Kein Short in Stufe A**, kein Hebel. Stop-Loss als Boersen-Order
  (überlebt Neustart), keine skript-bewachte Position.
- Maximalbetrag pro Trade klein (Stufe A: 10 EUR), `max_offene_positionen`
  klein (1), Gesamtdeckel klein.
- Live wird **nie aus einem Chat-/A2A-befehl scharf** — nur die
  Freigabekette. Ein „ja“ auf einen Plan ist NICHT die Freigabe.

## 6. Nachweis-Kette (was „gefechtsbereit“ heißt, konkret)

Stufe A ist erst dann „gefechtsbereit“, wenn ALL das echte Ergebnisse sind:

1. `kraken.kerzen("XBTUSD", 1440, 10)` liefert echte Kraken-Spot-Kerzen.
2. `kraken.paar_info("XBTUSD")` nennt Stellen, Mindestmenge, Mindestwert.
3. `kraken.guthaben("ZEUR")` läuft (gerade/leer meldet nur: Key vorhanden,
   kein Guthaben-Fehler).
4. Order-Signatur funktioniert: ein `marktwert_validieren`-Lauf (validate,
   `echt=False`) auf ein Kleinstpaar wird von Kraken angenommen (txid leer
   aber kein Fehler) — **ohne** eine echte Order zu erzeugen.
5. `moondev_marktlage/handeln.py --vorschau` rechnet Long long sauber.
6. `--live` mit gesperrter Kette sagt, welche Sperre zu war (nichts passiert).
7. Erste echte Order (Kleinstbetrag) nur NACH deinem expliziten Befehl, mit
   vorher gezeigter Betragshöhe, Stop, Ziel.

## 7. Was ich NICHT mache (weder jetzt noch in Stufe A)

- Kein Margin-/Short-Code in Stufe A.
- Kein Ändern des gemeinsamen Buchkerns `spur_buch.py` live-fähig für
  alle 9 Spuren (zu breit für den ersten Geldpfad).
- Kein Live-Scharfschalten aus irgendeiner Nachricht heraus.
- Keine echten Kraken-Order ohne vorher gezeigten Betrag, Stop, Ziel.
- Kein Berühren der Freigabedatei(n) in einen Zustand `true`.

## 8. Entscheidungspunkte für dich (= warte auf deine Antwort)

1. **Freigabe Stufe A bauen?** Dann baue ich den abgetrennten Live-Zweig
   (Long, XBT/USD, Kleinstbetrag) mit Sperrenkette + Tests. Papier läuft
   weiter. Kein Schalter geht an.
2. **Betragshöhe Stufe A** (Vorschlag: 10 EUR pro Trade, 1 offene Position,
   Gesamtdeckel 30 EUR). Sag eine Höhe oder bestätige.
3. Stufe B (Margin-Short) bleibt im Plan vermerkt, wird aber **nicht**
   gebaut, bis A auf echtem Kraken-Spot steht und du eine separate
   Freigabe für den Margin-Schlüssel + Kontingent gibst.
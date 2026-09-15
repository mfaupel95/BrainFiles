# Risikostufen: derselbe Handel, andere Buchgroesse

Gehoert zu den Handelsspuren (`Agenten/Handel`). Zweck: mehr Beobachtungen je
Zeiteinheit, ohne eine Strategie zu aendern. Bei kleinen Einsaetzen dauert jede
Statistik Monate; mit dem Faktor sieht man denselben Fehler schneller. Ein
Messwerkzeug, kein Gewinnhebel.

## Bauform

- `Agenten/Handel/risikostufe.py` ist die EINE Umsetzung. Der Dauerlauf setzt je
  Stufe `HANDEL_RISIKO=niedrig|mittel|hoch` (Faktor 1 / 2 / 4) in die
  Prozessumgebung der Kindprozesse.
- **Ohne die Variable aendert sich nichts.** Das ist die Bedingung, unter der eine
  solche Umstellung in laufenden Handelscode darf: Basis = Faktor 1.0, kein
  Suffix, identisches Verhalten.
- Zustand und Journal MUESSEN je Stufe getrennt liegen
  (`zustand.mittel.json`, `handelsjournal.mittel.csv`, ueber `datei()`): zwei
  Laeufe auf derselben Datei ueberschreiben sich die Positionen. `journal_zweitziel`
  bleibt dagegen unveraendert — `spiegele_journal` kopiert unter dem QUELLnamen
  nach Q:, die Kopien heissen also von selbst `zustand.mittel.json`. Kein eigener
  Zielordner noetig.
- Ein unbekannter Wert zaehlt als Basis. Ein Tippfehler („mitel") darf nicht still
  die vierfache Position handeln.
- `datei()`/`datei_fuer()` erhalten den Pfadtyp: aus `str` kommt `str`, aus
  `Path` kommt `Path`. `scanner/handeln.py` ruft `.read_text()` auf dem Ergebnis
  auf — ein zurueckgegebener str waere dort ein Attributfehler im Zyklus.

## Was skaliert wird - und was nie

Positivliste, KEIN Namensmuster. Die naheliegende Regel „alles mit `_usd`" ist
falsch: an den echten Wachen gemessen trifft sie Felder, die keine Einsaetze sind.

| nicht skalieren | warum |
|---|---|
| `marketcap_band_usd` | Marktgroesse eines Tokens, kein Einsatz |
| `groesster_ruecklauf_papierlauf_*` | eine MESSUNG; skaliert waere sie eine Behauptung ueber die Vergangenheit |
| `mindest_guthaben_*`, `mindest_marge_frei_*` | Kontoschwellen der Boerse |
| `umsatz_bezug_usd`, `punkt_wert_usd` | Handelsvolumen, Vertragsgroesse |
| Felder mit fuehrendem `_` | dokumentierter Vorwert |

Skaliert werden die Begrenzer der Buchgroesse: `risiko_je_position_*`,
`risiko_pro_trade_*`, `risiko_je_anlauf_*`, `max_pro_trade_*`, `max_gesamt_*`,
`max_margin_*`, `max_einsatz_*`, `einsatz_usd`, `max_verlust_usd`, `stop_usd`.

**Mit skalieren MUSS die Ratsche** (`drawdown_halbierung_usd`) **und der
Kill-Schalter** (`kill_switch_gesamt_*`): beide sind in Buchrisiko ausgedrueckt
(1,0x, siehe `ratschen.py`). Blieben sie stehen, loeste die doppelte Position die
Halbierung nach dem ersten Verlust aus - die Stufe waere gesperrt und lieferte
keine Daten.

## Drei Regeln, die eine Stufe erst ungefaehrlich machen

1. **Nie live.** `risikostufe.live_erlaubt()` ist nur in der Basis true, und der
   Dauerlauf uebergibt auch bei offenem Freigabefenster `--papier`. Grund: das
   Buch der Stufe ist getrennt - live gehandeltes Geld stuende in keiner
   Auswertung, und derselbe Handel mit vierfachem Einsatz bringt keinen
   zusaetzlichen Erkenntnisgewinn.
2. **Kein Telegram.** Kein Senden, kein Abholen von Befehlen, keine
   Freigabe-Anfrage, kein Schliessen der Fenster beim Beenden. Zwei Dauerlaeufe
   an einem Bot nehmen sich die Nachrichten weg (Telegram: 409), und ein `/ja`
   waere nicht mehr zuzuordnen.
3. **Spiegel nur in der Basis.** Er hat in jeder Stufe denselben Einsatz
   (Vorgabe Max), ein zweites Buch waere dieselbe Beobachtung noch einmal - und
   zwei Laeufe schrieben in dieselben Dateien. `dauerlauf.NUR_BASIS` ueberspringt
   ihn, `spiegel.py` bricht in einer Stufe mit Klartext ab.

## Anschliessen je Spur (so ist es gebaut)

Es gibt keine zentrale Stelle: jede Spur bildet ihre Dateinamen selbst. Je Spur
sind es drei Eingriffe, alle nach demselben Muster:

1. `risikostufe` ueber den PFAD laden (wie `ratschen.py`) - die Spuren haben ihren
   eigenen Ordner als `sys.path[0]`, ein `import` auf `Handel/` scheitert.
2. Die Wachen nach dem Laden durch `skaliere(...)` schicken. **Die Wachen-Funktion
   ist der richtige Ort**, nicht `lauf()`: nur so kann ein Test dieselbe Funktion
   befragen, die der Betrieb benutzt.
3. `ZUSTAND`/`JOURNAL`/`ABLEHNUNGEN` (und `nautilus`: `KOPIER_*`) ueber `datei(...)`
   benennen.

| Spur | Wachen aus | Dateien in |
|---|---|---|
| xperp | `bot.wachen()` | `handeln.py` |
| scanner, kraken | `scan.wachen()` | `handeln.py` |
| swap | `handeln.wachen()` | `handeln.py` |
| orbk | `handeln._wachen()` | `handeln.py` |
| kopier, kopier1zu1, nautilus, omniquant, gitter, squeeze, supertrend, wavetrend, macd_mtf, mosaic | `lade_wachen()` | `handeln.py`/`kopier.py` |
| spiegel | — (nur Basis) | — |

Werkzeuge, die eine FREMDE Stufe ansehen, nehmen `datei_fuer(pfad, stufe)` statt
der Umgebungsvariable: `spiegelstand.py` und `auswertung_alle.py` haben ein
`--risiko`, die `auswertung.py` in kopier/kopier1zu1/omniquant/gitter folgen der
Umgebungsvariable (dort wie die Spur selbst starten).

Betrieb:

- `dauerlauf.py --risiko mittel`: eigene Logdatei (`dauerlauf.mittel.log`) und
  eigene PID-Datei (`dauerlauf.mittel.pid`), sonst haetten sich zwei Laeufe
  gegenseitig „laeuft schon" gemeldet.
- `Routinen/handel-dauerlauf.ps1 -Risiko mittel`: Waechter-Aufruf der Stufe.
  Eine zweite geplante Aufgabe muss Max anlegen - der Wrapper startet nichts von
  selbst.

## Pruefen

`Agenten/Handel/tests/test_risikostufe.py` faehrt ueber JEDE Spur: sie wird per
`importlib` geladen (wie im Betrieb) und dann gefragt, ob ihre Dateikonstanten den
Suffix tragen und ihre Wachen-Funktion die Betraege verdoppelt - in beiden
Richtungen. Dazu die Gegenprobe, dass der Spiegel die Basisnamen behaelt.

Nach jeder Aenderung an den Stufen:

    cd Agenten/Handel/tests && python -m unittest test_risikostufe
    cd Agenten/Handel && python spiegelstand.py          # Basis muss byte-gleich sein
    cd Agenten/Handel && python spiegelstand.py --risiko mittel

Der zweite Aufruf ist der eigentliche Nachweis: eine Stufe darf die Q:-Kopien der
Basis NICHT anfassen. Faellt dort eine Abweichung an, die es im Basislauf nicht
gibt, schreibt eine Stufe in Basispfade.

Abgrenzung: `journal-spiegelung` (Kopie nach Q:), `dauerprozess-bewachen` (eine
Stufe ist ein eigener Dauerprozess mit eigener PID-Datei und eigener Wache).

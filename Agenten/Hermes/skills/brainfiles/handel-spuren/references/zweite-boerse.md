# Eine Spur an eine zweite Boerse haengen (mosaic -> Kraken, 21.09.2026)

Muster fuer: "Spur X soll statt/zusaetzlich auf Boerse Y handeln", ohne die
Strategie anzufassen. Umgesetzt in `Agenten/Handel/mosaic`, uebertragbar auf
jede Spur, deren Live-Weg ueber gebundene Funktionsnamen laeuft.

## Der Aufbau in vier Teilen

1. **Ein Boersenmodul mit DERSELBEN Oberflaeche.** `mosaic/kraken_spot.py` stellt
   genau die Namen bereit, die `handeln.py` erwartet (`markt_kauf`,
   `markt_verkauf`, `algo_stop_setzen`, `algo_stornieren`, `gefuellte_menge`,
   `guthaben_waehrung`, `letzter_kurs`, `menge_fuer`, `schluessel_vorhanden`,
   `demo_modus`) und ruft dahinter `kraken/kraken.py`. Die Boersenlogik wird NICHT
   kopiert - nur ihre Namen und Signaturen.
   Das Modul ueber den **Pfad** laden (`importlib.util.spec_from_file_location`),
   nie ueber `sys.path`: ein Eintrag auf `Handel/kraken/` kann gleichnamige
   Module verdecken (dieselbe Falle wie bei `ratschen.py`).

2. **Eine Binde-Funktion statt eines Imports.** `venue_binden(w)` in
   `handeln.py` liest `boerse` aus der `wachen.json` und setzt die Modulglobals
   (`op_kauf`, `live_kurs_quelle`, ...) neu. Aufruf **vor der ersten
   Sperrenpruefung**, damit Schluessel-, Demo- und Guthaben-Tor die richtige
   Boerse fragen. Ohne Feld bleibt alles wie vorher (Standard `okx`) - ein
   fehlendes Feld darf keine Spur umschalten.

3. **Paar-Abbildung an EINER Stelle - und laut scheitern.**
   `kraken_spot.PAARE = {"BTC-USDC": "XXBTZEUR", ...}`. Die Instrumente in der
   `wachen.json` bleiben in den alten Namen (Kerzenquelle, Papierzweig und Buch
   bleiben unberuehrt); nur die Order wird uebersetzt. Ein unbekanntes Paar wirft
   `ValueError` - eine stille Ersatzwahl schickt die Order in den falschen Markt.

4. **Die Sperrenkette boersenunabhaengig machen.** `live_sperren` fragte hart
   `okx_spot.schluessel_vorhanden()`, `okx_spot.demo_modus()` und das Guthaben
   ohne Waehrung. Jetzt: `VENUE.schluessel_vorhanden()`,
   `VENUE.demo_modus()`, `op_guthaben(GUTHABEN_WAEHRUNG)` und der Mindestbetrag
   aus `mindest_guthaben` (Rueckfall `mindest_guthaben_usdc`/`_eur`). Die
   **Kontowaehrung gehoert in die wachen.json** (hier EUR), sonst prueft die Spur
   60 USDC statt 60 EUR.

## Fallen, die dabei aufgefallen sind

- **Duplikate JSON-Schluessel beim Einfuegen.** Ein eingefuegtes
  `"guthaben_waehrung": "EUR"` direkt hinter `handel_erlaubt` war wirkungslos,
  weil weiter unten schon `"guthaben_waehrung": "USDC"` stand - **der letzte
  Schluessel gewinnt**, und die Pruefung zeigte USDC. Nach dem Einfuegen gegen
  das GELESENE JSON pruefen, nicht gegen den eingefuegten Text.
- **`.format()` und `%` nicht mischen.** Aus dem Nachbarmodul kopiert:
  `"%.{0}f ... {1}".format(stellen) % (menge, ...)` laeuft in einen
  `IndexError`. Vorlage einmal mit `.format()` fuellen, kein `%` dahinter.
- **Testvergleich ueber Modulnamen, nicht Objektidentitaet.** Der Test laedt die
  Datei unter eigenem Namen, `handeln.py` importiert sie als `kraken_spot` -
  dasselbe Modul, zwei Objekte. `assertIs` scheitert dann, obwohl alles stimmt.
- **Ordern mit `echt=True` gehoert in die duenne Schicht.** `kraken.py` kann
  `validate=true` (nur durchrechnen). Das Adaptermodul setzt `echt=True` hart -
  es wird ausschliesslich aus dem Live-Zweig gerufen, der vorher die ganze
  Sperrenkette passiert. Der Papierzweig laeuft ueber einen eigenen Pfad und
  beruehrt das Modul nie.

## Pruefen

```
cd Agenten/Handel/mosaic
../scanner/.venv/Scripts/python.exe handeln.py --vorschau
```
Die Zeile `Live waere gesperrt durch: ...` nennt bei gesetzter `boerse: kraken`
die Sperren der KRAKEN-Seite (Guthaben in EUR). Genau ein Grund, und dieser
Grund heisst "Freigabefenster" -> die Auto-Freigabe oeffnet selbst; jeder andere
Grund (z. B. Guthaben) ist eine Sache fuer Max, kein Dateischalter.

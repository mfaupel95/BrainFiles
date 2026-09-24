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

## Mehrere Boersen gleichzeitig: eine Liste mit Vorrang

Soll dieselbe Spur BEIDE Boersen nutzen ("gerne auf okx und kraken"), ist das
KEINE zweite Spur, sondern das Feld `boersen: ["kraken", "okx"]` in der
`wachen.json` - die Reihenfolge ist der Vorrang.

- **Die erste EINSATZBEREITE gewinnt**, nicht die erste der Liste: Schluessel
  vorhanden, kein Demo-Modus, Mindestguthaben frei. Ist keine bereit, bleibt es
  bei der ersten der Liste - so nennt die Sperrenkette EINEN Grund, und die
  Auto-Freigabe (die genau einen Freigabefenster-Grund verlangt) bleibt scharf.
- **Das Guthaben wird in der Waehrung DIESER Boerse geprueft**
  (`guthaben_waehrung_je_boerse`: Kraken EUR, OKX USDC). Ein einzelnes
  `guthaben_waehrung: "EUR"` fragt OKX nach EUR und sperrt es dauerhaft. Der
  Mindestbetrag darf je Boerse gesetzt werden, sonst gilt einer in beiden
  Waehrungen. **Margin-Guthaben ist kein Spot-Guthaben:** `availEq` in USDC aus
  der Kontoansicht kann voll aussehen, waehrend fuer einen Spot-Kauf fast nichts
  frei ist - die Boerse fragt man mit der Waehrung des Kaufpfads.
- **Einzelboerse bleibt eine signierte Abfrage aermer:** die
  Bereitschaftspruefung nur bei mehr als einer Boerse laufen lassen, sonst wird
  jeder Zyklus teurer, ohne dass sich etwas entscheiden kann.
- **Jede Position traegt ihr `boerse`-Feld** (beim Einstieg stempeln), und der
  Ausstieg bindet die Boerse der POSITION (`venue_fuer_position(p, w)`) - nicht
  die gerade gewaehlte. Ohne das verkauft eine Kraken-Position ueber den OKX-Weg
  ins Leere. Positionen ohne Feld laufen weiter ueber die gebundene Boerse
  (Altdaten); ein unbekannter Name ist ein `ValueError`, kein stiller Rueckfall.
- **Nach dem Umbinden zurueckbinden**, wenn gewechselt wurde (Flag ueber die
  Schleife, `venue_binden(w)` am Ende) - sonst haengen die anschliessenden
  Einstiege und die Seams an der falschen Boerse.
- **Test-Naht fuer das Guthaben** (`_guthaben_roh(name, ccy)`): eine
  Bereitschaftspruefung, die direkt ins Boersenmodul greift, macht JEDEN Test zu
  einem echten Netzaufruf und laesst die Suite mit fremden Fehlern rot werden.
  In Tests das Modul-Dict (`BOERSEN`) durch Attrappen mit denselben Funktionsnamen
  ersetzen und die Seams (`op_*`) am Ende der Testklasse neu binden - sonst zeigt
  die naechste Testdatei auf die Attrappen.

## Kurs-Waehrungs-Mismatch: quelle() liefert USD, Boerse braucht EUR

`spur_buch.einstieg()` rechnet Stop und Ziel aus dem `kurs`-Wert, der aus
`quelle()` kommt — bei CoinGecko-basierten Spuren ist das der USD-Preis.
Kraken setzt den Stop als EUR-Betrag. Ergebnis: ein Stop bei 158 USD wird als
158 EUR gesetzt, waehrend der Markt bei 497 EUR steht. Entweder sofort gerissen
(Stop ueber dem Preis) oder viel zu nah (Stop deutlich unter dem Preis in
anderer Waehrung).

**Fix (in `spur_buch.py`):** Im Live-Einstieg den Boersen-Kurs holen (`weg.letzter_kurs(vinst)`)
und Stop, Ziel und Menge auf Basis dieses Kurses neu berechnen. Schlaegt der Abruf
fehl, Einstieg uebergehen (niemals mit falschem Kurs ordern):

```python
try:
    kurs_live = float(weg.letzter_kurs(vinst))
    if kurs_live > 0:
        kurs = kurs_live  # Stop/Ziel/Menge neu rechnen
except Exception as e:
    print("Boersen-Kurs nicht abrufbar (%s) - Einstieg uebersprungen" % e,
          file=sys.stderr)
    return None
```

Testmuster (`test_spur_buch_orderweg.py`):
- Attrappe mit `letzter_kurs = lambda self, inst: 200.0` (deutlich != quelle-Kurs 100)
- Assert auf `p["einstieg"] == 200.0`, `p["stop"] == 200*0.93`, `p["ziel"] == 200*1.14`
- Attrappe mit `letzter_kurs` der `RuntimeError` wirft → `einstieg()` gibt `None`

**Dieselbe Waehrungsfalle in der ANZEIGE.** Ein Berichts-Holer fuer die
Papier-Spuren holte die Kurse fuer ALLE Positionen von OKX (USDC) - eine
Kraken-Position in EUR stand damit mit **+11 %** im Bericht, waehrend sie real
**-2 %** lag. Ein Prozentwert aus fremder Waehrung ist kein Rundungsfehler, er
dreht das Vorzeichen und laesst ein Ziel "erreicht" erscheinen, das weit weg ist.

- Der Kurs gehoert zur **Boerse der Position** (`p["boerse"]`, sonst die erste
  Boerse der Spur). Kraken-Kurse ueber das Adaptermodul holen
  (`kraken_spot.letzter_kurs` uebersetzt die OKX-Namen auf Kraken-Paare), per
  `importlib`-Pfad geladen - kein `sys.path`-Eintrag, der gleichnamige Module
  verdecken kann. Pro Position die passende Quelle waehlen, nicht einmal fuer alle.
- **Ein "Papier"-Etikett im Bericht darf nicht fest verdrahtet sein.** Ein
  gemeinsamer Holer fuer viele Papier-Spuren setzte das Papier-Merkmal hart; die
  eine Spur mit Live-Zweig stand damit als "kein Live-Zweig (Papierpfad)" im
  Bericht, obwohl sie live handelte. Die Faehigkeit ist ein PARAMETER des Holers
  (Standard Papier), der angezeigte Modus kommt aus `handel_erlaubt` +
  `freigabe.erfuellt` + Boersenliste, und Live-Positionen bekommen "(live)" in den
  Namen. Merksatz: **wer eine Anzeige baut, die eine Faehigkeit behauptet, muss
  sie aus der Konfiguration lesen - nicht aus einer Konstante.**

Die Paar-Abbildung (`venue_inst(inst, w)`) erzeugt aus `XMR` bei `boerse: kraken`
den String `XMR-EUR`. Dieser String muss in `kraken_spot.PAARE` stehen; fehlt er,
wirft `paar_fuer()` `ValueError` — der Einstieg wird lautlos uebersprungen
(Exception in spur_buch faengt das ab). Vor dem Anbinden einer neuen Spur an Kraken
die Paare live validieren: `GET /0/public/AssetPairs` und die EUR-Paarnamen je Signal
in die `PAARE`-Dict eintragen.



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

## Jede Boerse hat Preisregeln — der Orderpreis muss gerundet raus

Ein Stop-/Trigger-/Limitpreis kommt aus einer Rechnung (`Einstieg * (1 - stop_pct)`)
und hat damit zu viele Stellen. Beide Boersen lehnen ihn dann ab, ohne Teilausfuehrung —
der Notausstieg fehlt komplett und die Spur verkauft die gerade gekaufte Position
sofort zurueck (Spesen ohne Handel). Die erlaubte Stellenzahl steht **je Paar bzw.
je Instrument in der API**, nie in einer Konstanten:

| Boerse | Feld | Beispiele |
|---|---|---|
| Kraken | `AssetPairs[paar].pair_decimals` | SOLEUR/XETHZEUR 2, XXBTZEUR 1, AKEEUR 8, KASEUR 5 |
| OKX | `instruments[instId].tickSz` | SOL-USDC 0.01, BTC-USDC 0.1, XRP-USDC 0.0001 |

Muster: eine Funktion `preis_gerundet(paar, preis, richtung="auf")` **je
Boersenmodul** (`kraken.preis_gerundet`, `okx_spot.preis_gerundet`), aufgerufen in
der Stop-Funktion selbst — nicht beim Aufrufer. So sind alle Spuren mitgemeint:
`kraken.stop_setzen` wird von `kraken/handeln.py`,
`moondev_marktlage/live_kraken.py` und `mosaic/kraken_spot.py` gerufen.

- **Richtung `auf` (ceil) fuer den Long-Stop:** der Ausstieg liegt dann nie TIEFER
  als gerechnet, das Risiko wird also nicht groesser als die Wache erlaubt. `ab`
  (floor) ist die Gegenrichtung fuer den Short-Stop.
- **Fertig formatierten String zurueckgeben**, nicht `float`: `str(float)` schreibt
  kleine Werte als `1e-08`, was ebenfalls abgelehnt wird.
- **`round(x, 6)` vor `ceil`/`floor`:** `128.995 * 100` ist binaer
  `12899.499999999998` und kippt die Rundung sonst.
- **Test-Doubles ohne Preisregel-Feld nicht raten lassen:** liefert `paar_info()`
  kein `preis_stellen` (handgeschriebene Attrappen in aelteren Tests), den rohen
  Wert weitergeben statt eine Stellenzahl zu erfinden. Neue Tests fuellen das Feld.
- **Probe ohne Geld:** die Order mit `validate=true` (Kraken `AddOrder`) bzw. gegen
  den `order-algo`-Pruefweg senden — sie nimmt den gerundeten Preis an und den
  rohen nicht. Das ist der Beleg vor dem Commit, ohne Orderrisiko.
- **Unbekannter Paarname wirft laut** (`EQuery:Unknown asset pair`). Vor dem
  Anschliessen die echten Paarnamen aus der `watchlist`/Instrumentenliste gegen
  `AssetPairs` pruefen; OKX ist bei zu vielen Stellen nachsichtig (live
  angenommene Stops mit 5 Stellen), Kraken nicht.

## Pruefen

```
cd Agenten/Handel/mosaic
../scanner/.venv/Scripts/python.exe handeln.py --vorschau
```
Die Zeile `Live waere gesperrt durch: ...` nennt bei gesetzter `boerse: kraken`
die Sperren der KRAKEN-Seite (Guthaben in EUR). Genau ein Grund, und dieser
Grund heisst "Freigabefenster" -> die Auto-Freigabe oeffnet selbst; jeder andere
Grund (z. B. Guthaben) ist eine Sache fuer Max, kein Dateischalter.

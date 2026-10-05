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
  Boerse der Spur). **Margin-Guthaben ist kein Spot-Guthaben:** `availEq` in USDC aus
  der Kontoansicht kann voll aussehen, waehrend fuer einen Spot-Kauf fast nichts
  frei ist - die Boerse fragt man mit der Waehrung des Kaufpfads. Bei OKX stehen
  die drei Zahlen nebeneinander und erzaehlen die Geschichte: `eq` (Gesamt),
  `frozenBal` (reserviert) und `availEq = availBal = cashBal` (wirklich frei).
  Gemessen: `eq 730,42` / `frozenBal 730,42` / `frei 0,0021` - die Stop-Orders der
  eigenen offenen Positionen reservieren das Guthaben, und die Sperre SCHWANKT
  mit ihnen (kurz zuvor waren 227,39 frei). Vor dem Satz "das Geld ist da" also
  `frozenBal` lesen und den Grund benennen, sonst verspricht man einen Einsatz,
  den die Boerse ablehnt.
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

**Bei Signalen aus einer Liste (CoinGecko/Ranglisten) reicht eine feste
Paar-Tabelle NICHT — die Spur muss VOR dem Einstieg pruefen, ob es das Paar
tatsaechlich gibt.** Ein `spur_buch`-Spur bildet jedes Signal blind auf
`<SYM>-<Waehrung>` ab; welcher Symbolname aus den Daten kommt, weiss die Config
nicht. Gemessen beim Wechsel einer Feed-Spur auf OKX: von drei Signalen desselben
Tages hatte nur EINES ueberhaupt ein OKX-Paar, und das nur als `-USDT` statt
`-USDC` — zwei von drei Einstiegen waeren auf ein Paar gegangen, das die Boerse
nicht kennt (`ValueError`, lautlos uebersprungen, ohne dass jemand den Grund
sieht). Muster:

1. In `quelle()` die handelbare Instrumentenliste EINMAL je Zyklus holen
   (oeffentlich, kein Schluessel: OKX `/api/v5/public/instruments?instType=SPOT`)
   und je Coin ein Feld `okx_usdc: bool` setzen; ein Fehler beim Abruf ist ein
   `fehler`-Eintrag, kein stilles Weiterlaufen.
2. In `signal()` ein Tor: falscher Weg (`boerse: okx`) und Paar fehlt -> `None`,
   mit einem Kommentar, WARUM (der Orderweg wuerde sonst ins Leere schicken).
   Bei der anderen Boerse bleibt das Tor aus.
3. Eine Test-Naht fuer die Instrumentenliste (`instrumente_override`) und Tests
   fuer alle drei Faelle: Paar da, Paar fehlt, andere Boerse.

Merksatz: **eine feste Paar-Tabelle ist eine Behauptung ueber die Datenquelle,
keine Pruefung.** Wo die Symbole aus einer API kommen, gehoert die Pruefung in
den Zyklus.



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

## Einen HEGEBELTEN Weg an eine SPUR haengen (derselbe Aufbau, andere Produktklasse)

Der Aufbau oben haengt einen zweiten Boersenweg mit DERSELBEN Oberflaeche an
eine Spur - beide Beispiele dort sind SPOT. Kommt die Anweisung "mit 6x Hebel",
ist das kein Parametersatz, sondern eine **andere Produktklasse**: der
bestehende Weg kann es strukturell nicht, und das steht in seinem eigenen
Modulkopf. `tdMode` ist dort fest `"cash"`, die Menge ist eine Basiseinheit,
eine `hebel_setzen`-Funktion existiert nicht. Ein Schalter auf
`handel_erlaubt` in diesem Zustand liefert **ungehebelten** Spot - nicht das,
was bestellt wurde. Diese Behauptung gehoert VOR der Zusage am Code geprueft
(`hasattr(okx_spot, "hebel_setzen")` und `'"tdMode": "cash"' im Quelltext), nicht
begruendet.

**Vier Stellen unterscheiden einen gehebelten Weg vom Spotweg. Jede davon war
schon ein Fehler, bevor sie benannt war.**

1. **`menge_fuer(inst, betrag, kurs)` bedeutet auf dem einen Weg MARGIN, auf dem
   anderen NOMINALWERT.** Derselbe Funktionsname, zwei Bedeutungen: 100 USD
   heissen im Spot 100 USD Bestand, im Futures 100 USD Nennwert. Ohne
   Umrechnung kauft der gehebelte Weg eine 1x-Wette mit dem Margin-Betrag eines
   6x-Kontrakts - und niemand sieht es am Journal, weil die Zahl plausibel
   aussieht. Die Umrechnung gehoert an EINER Stelle und wird als Vorrang
   bestimmt, nicht am Aufrufer: `NOMINAL_STATT_MARGINAL = {"okx_perp"}` neben der
   Boersentabelle, und `live_menge_fuer(inst, nominal, kurs)` an der einen
   Aufrufstelle. **Der gebundene Wert im Buch bleibt die Margin, der
   Nominalwert geht nur an die Mengenrechnung** - sonst bookt die Spur das
   Sechsfache ihres eigenen Deckels.
2. **`stop_vor_liq()` ist eine eigene Pruefung, die es bei Spot nicht gibt, und
   sie laeuft VOR dem Kauf.** Ein Long verliert, wenn der Kurs faellt: er
   trifft zuerst den naeher am Einstieg liegenden Stop, erst danach die
   Liquidationsmarke. Also muss `liq < stop < einstieg` gelten (Short
   spiegelbildlich). Die Ungleichung ist leicht verkehrt herum zu lesen, und
   **eine verkehrte Fassung lehnt jeden regulaeren Stop ab** - sie faellt nicht
   durch, weil sie "vorsichtig" wirkt. Zwei Preise werden verweigert statt
   geraten: ein Stop auf/ueber dem Kurs (verkauft sofort) und einer jenseits der
   Marke (kaeme nie). Die Grenze ist eine Rechnung und gehoert in den Vermerk:
   bei 6x liegt die Marke rund 16 % entfernt, ein 5-%-Stop kommt vorher, erst
   jenseits von etwa 20x nicht mehr.
3. **Die Kontowaehrung steht in `details`, nicht auf der obersten Ebene.**
   `/api/v5/account/balance?ccy=USDC` liefert oben `availEq=''` und erst in
   `details[0]` die Zahlen. Wer die oberen Felder liest, bekommt `0.00` - das
   sieht wie ein leeres Konto aus und sperrt die Spur an einem Guthaben-Tor,
   das offen ist. Derselbe Stoff, dreimal im Haus falsch gelesen; der Test
   haelt genau diese Antwortform fest (`availEq` oben leer, `details[0]`
   gefuellt).
4. **Ein Vertragstest auf die vollstaendige Funktionsliste findet, was Lesen
   nicht findet.** Die Binde-Funktion setzt jede Seam ueber einen NAMEN -
   `live_kurs_quelle = modul.letzter_kurs` -, und ein fehlender Name crasht erst
   beim ersten Kursabruf im Live-Zweig, also nach dem Freigabefenster. Ein
   Test der die Namen beider Wege gegeneinander haelt (`hatattr` je Name,
   plus die Negativ-Aussage: der Spotweg darf `hebel_setzen` NICHT haben,
   sonst ist der ganze Aufbau ueberfluessig) findet es vor dem ersten Order.

**Den Hebel als Parameter an den Kauf geben, nie als Wert in der Wache, den
irgendein Aufrufer als Nominal missversteht.** `markt_kauf(inst, menge, hebel)`
setzt ihn ueber `set-leverage` VOR der Order; der Aufrufer uebergibt ihn aus
der Wache ueber eine Deckel-Funktion mit hartem Maximum. Ein Kauf auf einem
Kontrakt mit fremdem Hebel ist eine Wette, die niemand bestellt hat.

**Der gehebelte Weg leiht die Signatur, statt eine zweite zu bauen.** Schluessel,
Signatur und Takt kommen ueber den Pfad aus dem Modul der Nachbarspur
(`xperp/okxf.py`). Zwei Signaturen im Haus sind zwei Fehlerquellen fuer ein
Problem, das es nur einmal gibt. Was der gehebelte Weg selbst beitraegt: die
Produktklasse (`tdMode=isolated`, Kontrakte statt Basiseinheiten, `ctVal`
aus dem Instrumentenrecord), die Instrument-Aufloesung und die beiden
Pruefungen oben.

**Die Marktdeckung ist je Produktklasse verschieden und muss gemessen werden.**
OKX fuehrt **null USDC-SWAP-Maerkte** (gemessen ueber die volle
Instrumentenliste) - nur `BTC-USDT-SWAP` und die `_UM_XPERP`-Futures. Ein Weg,
der auf eine Waehrung gebaut wurde, die es fuer dieses Produkt nicht gibt,
sieht aus wie ein Konfigurationsfehler und ist einer. Der Kontrakt nennt seinen
`ctVal` (0.0001 BTC / 0.001 ETH / 0.01 SOL) - das ist die Kontraktgroesse, und
ohne sie kommt der Faktor Zehntausend zu gross heraus. **Ein unbekannter
Basiswert ist ein Fehler, kein Rueckfall auf ein anderes Instrument**: still das
falsche zu handeln waere der teuerste Fehler der ganzen Datei. Und `posSide`
gehoert nur mit, wenn das Konto nicht im Net-Modus steht - `posMode` vorher
lesen, sonst wird jede Order abgelehnt.

**Der Auftrag "Hebel xN" aendert die Substanzfrage nicht.** Ein Hebel macht
dieselbe Stichprobe riskanter, nicht besser: er vergroessert den Verlust JE
Position und senkt die Liquidationsmarke, die Trefferquote bleibt dieselbe. Wenn
die Spur vorher keinen Edge zeigte, ist der Hebel eine Ausgabe, keine
Verbesserung - das gehoert in den Bericht, sonst liest "live mit 6x" wie ein
Vorteil.

## Ein zweiter Dienst sieht aus wie eine zweite Boerse

Dieselbe Firma, anderes Produkt: **Kraken Futures ist ein eigener Dienst**, nicht
die Spot-API mit anderem Host. Wer ihn nach dem Muster oben anhaengt, muss die
vier Angaben aus der Doku holen, BEVOR eine Zeile Code entsteht - sie sind alle
vier anders als beim Spotweg:

| Angabe | Spot | Futures |
|---|---|---|
| Basis | `api.kraken.com/0` | `futures.kraken.com/derivatives/api/v3` |
| Kopf | `API-Key`/`API-Sign` | `APIKey`/`Nonce`/`Authent` |
| Signatur | HMAC-SHA512 ueber Pfad+Nonce+POST-Daten | `base64(HMAC-SHA512(base64decode(secret), SHA256(postData + nonce + "<pfad>")))` |
| Schluessel | `KRAKEN_SPOT_API_KEY`/`_SECRET` | `KRAKEN_FUTURE_API_KEY`/`_SECRET` |

Die Namen sind FAST gleich und trotzdem verschieden: unser Modul liest die
**Einzahl** (`KRAKEN_FUTURE_API_KEY`), die offizielle kraken-cli die **Mehrzahl**
(`KRAKEN_FUTURES_API_KEY`). Gemessen 25.09.2026: nur die Einzahl ist gesetzt.
Ein `Invalid key` eines fremden Werkzeugs ist deshalb zuerst ein Namensverdacht.

- **Signaturpfad und Aufrufpfad sind zwei verschiedene Dinge.** Der signierte Pfad
  traegt das Basis-Praefix NICHT (`/api/v3/accounts`, nicht
  `/derivatives/api/v3/accounts`) - mit dem vollen Pfad antwortet der Dienst
  `Authentication error`, obwohl der Schluessel lebt. Der Praefix gehoert als
  eigener Aufrufpfad in die URL.
- **Ein Koerper am lesenden Aufruf macht ihn zum POST.** Ein GET mit `data=b""`
  wird als POST gesendet und laeuft in `HTTP 404 NOT_FOUND` - das liest sich wie
  ein Rechteproblem und schickt die Fehlersuche auf die falsche Spur. Deshalb das
  Verfahren EXPLIZIT machen: jeder Aufruf traegt ein `post=False` und setzt `data`
  nur beim Senden (`post=True` an den Order- und Storno-Stellen), statt es aus
  "es gibt Werte" abzuleiten. Test: bei einem Leseaufruf muss `request.data`
  `None` sein; beim Orderaufruf `get_method() == "POST"`.
- **Die Order nimmt KONTRAKTE, und die Kontraktgroesse steht NICHT im Instrumentenrecord.**
  `contractSize` ist bei allen `PF_`-Maerkten `1` und sagt nichts ueber den Nennwert -
  die Regel steht unten unter "Wie gross ist ein Kontrakt WIRKLICH": **1 Kontrakt = 1
  Einheit der BASISwaehrung** (`base`, Einschuss 10 % fuer ein EEA-Konto). Nicht
  `menge * kurs` rechnen: aus 0,0001 BTC werden so "8 Kontrakte", also 8 BTC -
  eine Order, die nie durchgeht. Der Preis wird auf `tickSize` gerundet (dieselbe
  `preis_gerundet`-Regel wie oben, nur aus dem anderen Feld).
- **Ausstieg und Schutz-Stop brauchen `reduceOnly`** (Stop als `orderType: stp`
  mit `stopPrice`): ohne das Kennzeichen eroeffnet ein "Verkauf" auf der
  Gegenseite eine neue Position. Eine Ausstiegsorder ist nie eine Eroeffnung.
- **Besichert wird aus dem CASH-Konto dieses Dienstes.** Ein Coin-Bestand im
  Futures-Wallet (`fi_<coin>usd`) finanziert keine Order; ohne freies USD ist jede
  Order abgelehnt. Die Sperrenkette fragt die Waehrung DIESES Kontos und nennt den
  echten Grund ("kein freies USD im Futures-Konto") - nicht "Schluessel fehlt".
- **Ein Programm meldet `Invalid key`, waehrend unser eigenes Konto arbeitet:** es
  liest den ANDEREN Variablennamen. Beide Paare existieren gleichzeitig in der
  Umgebung; erst die Namen vergleichen, dann den Schluessel verdaechtigen.
- **Produktweiche statt zweiter Datei:** `KRAKEN_PRODUKT=futures` laesst das
  bestehende Adaptermodul (`kraken_rest`) den Futures-Weg laden und laesst die
  Spot-Datei unveraendert - die Spur schaltet ueber ihre Umgebung, nicht ueber
  kopierten Code. Ein eigener Launcher setzt die Variable (plus eigene Wachen-,
  Zustands- und Journalsuffixe), damit beide Produkte nicht ein Buch teilen.
- **Ein Bestand von 0 in der Kontowaehrung heisst gebaut, aber nicht fahrbar.**
  Weg bauen, live LESEND belegen (Salden, Instrumentenliste, ein Storno ohne
  Wirkung), den echten Sperrgrund in die Vorschau schreiben und die Entscheidung
  zur Einzahlung Max ueberlassen - kein Geld umschichten, kein Transfer auf
  Verdacht. Und: eine Kontoleiche in der Vorschau (mehrere Sperrgruende) haelt die
  Auto-Freigabe fern, weil sie genau einen Freigabefenster-Grund verlangt - das ist
  hier richtig, nicht ein Fehler.
- **Die Test-Attrappe muss je PFAD antworten und das Verfahren mitpruefen.** Ein
  Fake-Transport, der fuer jede Anfrage dieselbe Antwort liefert, laesst den
  Methodenfehler (GET/POST) durch: die Order erscheint erfolgreich, die Auswertung
  der Antwort faellt spaeter um. Pro Pfad eine Antwort hinterlegen (Senden ->
  Erfolgsantwort mit Orderkennung, Lesen -> Datenliste) und zusaetzlich die
  HTTP-Methode und `data` asserten.
- **Die "Probe ohne Geld" aus dem Spotweg gibt es hier nicht** - der Mini-Round-Trip
  ist der Ersatz, sobald Saldo UND Mindestgroesse geklaert sind. Vorher `handelbar()`
  fragen (Mindestmarge des Instruments gegen freies Guthaben); passt der kleinste
  Satz ins Konto, dann: Vorschau als Standard, `--anwenden` fuehrt aus, Kauf `mkt`,
  Fuellung ueber `/fills` abwarten, Verkauf `mkt` + `reduceOnly`, danach Positionen
  und Orders LEER zeigen. Notausstieg: scheitert der Verkauf, sofort einen
  Schutz-Stop 1,5 % unter dem Einstieg setzen und laut melden - eine offene Position
  ohne Stop waere das eigentliche Risiko. Kosten und Messaufloesung vorher nennen
  (Nennwert x Gebuehr, Equity-Aufloesung 0,0001 USD); bei einem Nennwert von wenigen
  USD ist die Gebuehr damit NICHT belastbar bestimmbar, das gehoert in den Bericht.
  Erst nach dem Ja von Max handeln, und nie mehr als den kleinsten Satz.

## Pruefen

```
cd Agenten/Handel/mosaic
../scanner/.venv/Scripts/python.exe handeln.py --vorschau
```
Die Zeile `Live waere gesperrt durch: ...` nennt bei gesetzter `boerse: kraken`
die Sperren der KRAKEN-Seite (Guthaben in EUR). Genau ein Grund, und dieser
Grund heisst "Freigabefenster" -> die Auto-Freigabe oeffnet selbst; jeder andere
Grund (z. B. Guthaben) ist eine Sache fuer Max, kein Dateischalter.

## Wie gross ist ein Kontrakt WIRKLICH (gemessen 25.09.2026, EEA-Konto)

`contractSize` im Instrumentenrecord ist bei ALLEN `PF_`-Maerkten `1` und sagt
ueber die Groesse NICHTS. Die Wahrheit kommt aus zwei Messungen:

1. **1 Kontrakt ist EINE Einheit der BASISWaehrung** (Feld `base`). Beleg:
   1 Kontrakt `PF_NEARUSD` wurde bei 4,5517 USD gefuellt und belegte 0,4548 USD
   Marge - das sind 10 % von 4,5517, also der Nennwert EINES NEAR. Waere 1
   Kontrakt = 1 USD Nennwert, waeren es 0,10 USD gewesen.
2. **Einschuss 10 %** fuer ein Europa-/EEA-Konto (`marginSchedules.europa.retail`,
   `initialMargin` 0.1). Der alte Plan `retailMarginLevels` zeigt 1 % - er gilt
   NICHT fuer dieses Konto. Die Ableitung steht als `einschuss()` im Modul und
   rechnet den gemessenen Fall nach (0,4553 gegen 0,4548 gemessen).

Folgen, die man vorher nicht sieht:

| Markt | 1 Kontrakt | Einschuss (10 %) | Mit 141,59 USD? |
|---|---|---|---|
| `PF_XBTUSD` | 1 BTC (~84.500 USD) | ~8.450 USD | nein |
| `PF_ETHUSD` | 1 ETH (~2.688 USD) | ~269 USD | nein |
| `PF_SOLUSD` | 1 SOL (~117 USD) | ~11,75 USD | ja |
| `PF_NEARUSD` | 1 NEAR (~4,55 USD) | ~0,46 USD | ja (bewiesen) |

- **Der kleinste Handel ist damit 1 Basis-Einheit, nicht 1 USD.** Ein
  Kopiersignal in BTC (0,0001 BTC) laesst sich auf einem Kraken-Futures-Konto
  dieser Groesse NICHT abbilden - die Begruendung gehoert in die Sperrenkette,
  nicht in einen stillen Rundungsfehler. `handelbar()` nennt genau diesen Grund.
- **`insufficientAvailableFunds` ist keine Kennungs- oder Rechtefrage.** Es heisst:
  die Mindestmarge des Instruments ist groesser als das freie Guthaben (bei
  `PF_XBTUSD` um den Faktor 60). Gegenprobe in zwei Zeilen: dasselbe Konto, dasselbe
  Kommando mit `PF_NEARUSD` wird angenommen.
- **Ein `CONTRACT_ACCESS_FORBIDDEN` (HTTP 403, code 95) ist eine Produktsperre des
  Kontos, kein Schluesselproblem.** Gemessen: `PI_XBTUSD` (inverse) ist fuer dieses
  EEA-Konto gesperrt, `PF_XBTUSD` (flexible futures) nicht.
- **Manche Endpunkte sind mit dem Handelsschluessel nicht lesbar:** `/fills` und
  `/accountlogcsv` antworten `authenticationError` bzw. HTTP 401 - die
  Gebuehrenmessung ueber das Journal faellt damit aus. Ersatz: die Kontoequity
  unmittelbar vor und nach der Ausfuehrung lesen (`collateralValue` im `flex`-Konto);
  die Differenz ist Gebuehr + Spread (Aufloesung 0,0001 USD - bei 4,55 USD Nennwert
  ist das grob, fuer eine belastbare Gebuehr braucht es ein groesseres Instrument).
- **Werkzeug:** `Agenten/Handel/nautilus_kraken/futures_probe.py` - echter
  Mini-Round-Trip mit Vorschau, `--symbol`, `--kontrakte`, Notausstieg per Stop
  falls der Verkauf scheitert. Es bucht in kein Buch und oeffnet kein Fenster.

## Eine Spur auf Kraken Futures umstellen: erst Marktdeckung, dann Sizing

Auftrag "Spur X live auf Kraken, aber mit perp und hebel xN". Zwei Pruefungen
gehoeren VOR die erste Zeile Code, beide oeffentlich und ohne Schluessel.

**1. Marktdeckung messen - die PF_-Maerkte sind NICHT die Spot-Paare.**
`GET https://futures.kraken.com/derivatives/api/v3/instruments` (rund 300
Maerkte), dann je Instrument der Spur pruefen, ob ein `PF_<BASE>USD` mit
`tradeable: true` existiert. Gemessen an einer Zehn-Instrumenten-Spur: neun
hatten einen PF_-Markt, nur eines nicht - im SPOT waren es nur acht gewesen.
Zwei Namen fallen auseinander: **DOGE heisst auf Futures `PF_DOGEUSD`, im Spot
`XDG`**, und ein Instrument ohne Spot-Paar kann auf Futures trotzdem
existieren. Die Deckung ist je Boerse EIGEN; "das gibt es bei Kraken nicht"
nie aus der Spot-Tabelle schliessen. Was fehlt, bekommt einen eigenen,
amentlich benannten Sperrgrund (`KEIN_MARKT`-Menge + `ValueError`), damit der
Grund im Bericht steht und nicht als "unbekannt" verschwindet.

**2. "Hebel xN" ist eine SIZING-Regel, kein Orderparameter.** Kraken Futures
kennt keinen Hebel je Order - der Einschuss ist der Margenplan des Marktes
(EEA retail 10 %, siehe oben). Die Vorgabe "Hebel 6" heisst deshalb
`nennwert = einsatz * hebel`, `kontrakte = nennwert / kurs`; die Boerse fordert
davon nur ihre 10 % an, der Rest des Einsatzes bleibt freie Margin. Das gehoert
so in den Bericht, sonst liest "Hebel 6" wie eine sechsfache Besicherung. Und:
**ein Stop von x % kostet bei Hebel 6 rund 6x % des Einsatzes** - der Hebel
erhoeht den Verlust JE POSITION, nicht die Trefferchance.
**UND der Stop muss zwischen Einstieg und Liquidationsmarke liegen, sonst kommt
er nie** - dieselbe Regel wie beim gehebelten OKX-Weg weiter oben
(`stop_vor_liq`, `liq < stop < einstieg`). Das ist beim Kraken-Weg bisher NICHT
abgesichert, nur beim OKX-Weg: wer beide Wege nutzt, zieht die Pruefung hier nach.
Der Rechenweg ist derselbe (Liquidationsmarke aus Hebel und Wartungsmarge), und
die Grenze ist bei Kraken eher enger, weil dort ein Kontrakt die Einheit der
Bstwaehrung ist und der Hebel das Vielfache der Margin ausmacht.

**3. Die Mindestmenge kann den Hebel sprengen - dann wird GESPERRT, nicht
aufgerundet.** 1 Kontrakt ist die kleinste Order und 1 Einheit der
Basiswaehrung; bei einem teuren Instrument ist schon DER groesser als das
Hebel-Budget. Gemessen: 1 Kontrakt eines ~1437-USD-Instruments ergibt bei
50 USD Einsatz **Hebel 28,7 statt 6**. Ohne Sperre waere das die groesste
Position im Buch gewesen, und am Hebel haette es niemand gesehen.

```python
HEBEL_TOLERANZ = 1.25          # der Kurs laeuft zwischen Sizing und Fuellung

def hebel_grund(inst, einsatz, kurs, w):
    k = kontrakte_fuer(inst, einsatz, kurs, w)
    ist = nennwert_usd(inst, k, kurs) / einsatz
    if ist > hebel(w) * HEBEL_TOLERANZ:
        return ("1 Kontrakt %s ist %.2f USD Nennwert (Hebel %.1f bei %.2f USD "
                "Einsatz) - bei Hebel %g nicht abbildbar" % (...))
    return None
```

Der Hebel gehoert in die `wachen.json` und wird zur AUFRUFZEIT gelesen - eine
Konstante im Modul waere eine zweite Wahrheit.

**4. Das Guthaben-Tor der neuen Boerse ist die freie MARGIN, nicht der Saldo.**
Ein multiCollateral-Konto (`flex`) traegt `availableMargin` und laesst
`cash.balances` auf 0 stehen; dasselbe Konto kann 85 USD tragen und davon 83 als
Einschuss fuer fremde Positionen gebunden haben. Vor jeder Zusage
`availableMargin` UND `initialMargin` lesen und BEIDE Zahlen nennen - "das Konto
hat 85 USD" ist ohne die zweite Zahl eine halbe Wahrheit.

**5. Das Tor auf den Betrag stellen, den Max wirklich bewegt.** Ein
`mindest_guthaben` von 35 USD bei einem beauftragten Transfer von 30 USD ist
wirkungslos: der Saldo landet bei 31,31 und die Sperre bleibt stehen. Vor dem
Setzen nachrechnen (`frei_neu = frei_alt + transfer` gegen `mindest_guthaben`),
sonst baut man einen Automaten, der auf ein Guthaben wartet, das schon da ist.
Und die Folge aussprechen: **ein aufgeladenes Guthaben IST die Live-Freigabe** -
faellt der letzte Nicht-Fenster-Grund weg, oeffnet die Auto-Freigabe das Fenster
selbst.

## Der Instrumenten-Weg wird ABGELEITET, nicht gepflegt — und nicht von selbst scharf

Die `KEIN_MARKT`-Menge aus dem Abschnitt oben ist der Notaus fuer die Maerkte,
die es nicht gibt. Sie ist aber nicht die Antwort auf die Frage, wie ein
Instrument, das der Signalgeber BRINGT und das in keiner Tabelle steht, auf den
Zielmarkt kommt. Drei Regeln dafuer, jede aus einem echten Ausfall:

1. **Namen werden aus der echten Marktliste GELEITET, nicht nachgetragen.** Die
   Regel ist einfach (`PF_<BASIS>USD`, mit Ausnahmen wie `BTC -> XBT`) und wird
   JEDES Mal gegen die Boerse geprueft (ein Name ohne Markt dort bleibt ein
   lauter Fehler und wird nie in einen anderen Markt umgelenkt). Eine
   handgepflegte Tabelle kann nicht mit einem Bericht Schritt halten, der ueber
   zweihundert Instrumente rotiert: gemessen passten elf von etwa zweihundert,
   und die zwei Kandidaten des Tages wurden abgewiesen, obwohl der Zielmarkt
   sie fuehrt.
   **Die geprueften Tabelleneintraege sind trotzdem kein Ersatz fuer die
   Ableitung.** Sie beantworten nur "welches Symbol", und sie decken genau die
   Faelle ab, in denen die Regel falsch liegt - dort, wo die Basis am Zielmarkt
   anders heisst als an der Quelle. Beide Wege braucht es: die Regel fuer die
   Regelmaessigen, die geprueften Eintraege fuer die Ausnahmen. Ein Eintrag
   umgeht dabei weder die Marktliste noch das Ableitungs-Tor, er beantwortet
   nur die Namensfrage mit einer gemessenen statt einer abgeleiteten Antwort.
   **Gegenprobe jeder geprueften Tabelle gegen die echte Marktliste** (jeder
   Eintrag muss dort stehen), nicht nur gegen die eigene Datei - sonst altert
   die Tabelle lautlos, und ein veralteter Eintrag sieht aus wie ein Markt, den
   die Boerse nicht fuehrt.
2. **Die Ableitung ist ein eigener Schalter, der von Hand kommt.** Sie gibt Geld
   fuer ein Instrument aus, das der Nutzer nie gesehen hat — genau da gehoert
   sein Ja hin, also `live_pf_ableitung: false` als Vorgabe plus Vermerk. Der
   gepruefte Kern (die von Hand bestaetigten Namen) laeuft, die Ableitung erst
   nach Freigabe. Ohne diese Trennung ist die Regel eine stille Erweiterung
   des Live-Buchs.
3. **Ein Lader, den niemand aufruft, sieht aus wie ein kaputter Aufrufer.** Wenn
   die Marktliste absichtlich nur BEIM LADEN gefuellt wird (kein Netzzugriff auf
   dem heissen Pfad), muss der Lader einmal je Lauf gerufen werden — sonst
   verweigert der Aufrufer JEDEN Einstieg mit einer Meldung ueber die
   Instrumentliste, und man sucht den Fehler im falschen Modul. Die
   Fremdarbeit dabei uebernehmen, nicht ueberschreiben: die Ableitung war richtig,
   nur unverkettet. Das echte Journal ist der Zeuge (N Fehlerzeilen je
   Zyklus, alle im Live-Modus, alle mit derselben Begruendung).

**Der Notausstieg darf nicht von dem Schritt abhaengen, der scheitern kann.**
Ein Mini-Round-Trip kauft, wartet auf die Fuellung und verkauft. Schlaegt das
Warten auf die Fuellung fehl, bricht der Lauf ab — und der Verkauf, also der
einzige Schutz, liegt im selben Zweig. Gemessen: Kauf angenommen und gefuellt,
die Fill-Abfrage mit `authenticationError` abgewiesen, die Position blieb OHNE
Stop offen. Zwei Regeln: den Notaus unabhaengig vom Fuell-Nachweis ausfuehren
(er ist ein eigener Schritt, nicht die Fortsetzung), und **nach jedem Probe-Lauf
Positionen UND offene Orders lesen** — der Ruecklauf auf „0 Kontrakte" ist der
Nachweis, nicht die Rueckmeldung des Werkzeugs. Gehoert der Endpunkt generell
nicht zum Handelsschluessel (gemessen: `/fills` ja, `/accounts` nein), dann ist
die Fill-Bestaetigung zu streichen und durch Position plus Order zu ersetzen.

## Zwei Einsatz-Konventionen im Haus — die Formel des Helfers ist die Wahrheit

Es gibt Spuren, deren Sizing-Helfer rechnet `int(Einsatz // Kurs)` — dort ist
`live_max_pro_trade_usd` der **NOMINAL** der Position, und die Margin kommt
erst aus dem Margenplan des Marktes. Andere rechnen `Nennwert = Einsatz x
Hebel` — dort ist dasselbe Feld die **Margin**. Beide stehen im Haus, und wer
das falsche liest, baut entweder eine zu kleine Position (Tor verweigert mit
„Einsatz kleiner als ein Kontrakt") oder eine um den Faktor Hebel zu grosse.

**Vor dem Setzen die Formel des Helfers lesen, nicht die Konvention annehmen.**
Der Nachweis ist ein Aufruf des Helfers mit dem neuen Wert und dem echten
Kurs — er muss die beabsichtigte Kontraktzahl liefern, sonst ist der Wert
falsch (nicht „die Boerse lehnt ab“). Bei einem Instrument ohne Bruchstuecke ist
der Nominalwert auch das, was die Obergrenze bestimmt: ein Wert knapp ueber dem
Kurs ergibt genau einen Kontrakt und verweigert bei einem Kurssprung nach oben
laut, statt auf eine kleinere Groesse auszuweichen.

## Die Kante gehoert zum INSTRUMENT, nicht zur Strategie

Bevor eine gemessene Strategie auf einer neuen Boerse gebaut wird: **die Strategie
auf dem Instrument messen, das die Boerse ueberhaupt handeln kann** — nicht das
Instrument aus einem vorhandenen Weg erben. Gemessen am selben Skript, gleicher
Takt, gleicher Fenster, gleiche Gebuehr: 42 Runden bei 28,6 % Treffer mit einem
Ergebnis nahe null gegen 44 Runden bei 29,6 % mit einem um zwei Groessenordnungen
besseren Ergebnis. Die Trefferquote unterscheidet die beiden nicht — sie zu
vergleichen haette die Entscheidung vertauscht.

Faellt der Weg aus, wird das Instrument gewechselt, NICHT die Strategie
abgeschwaecht. Vorher die Kerzendaten des neuen Instruments gegensehen (erste,
letzte, min, max) — ein Skalierungsfehler in der Reihe sieht aus wie ein
Strategieergebnis und ist die billigste Gegenprobe.

## Kraken gegen USDC: die Paare gibt es, die Waehrung ist die Huerde

Kraken fuehrt USDC-Quotepaare — dieselben Instrumente, die der Haus-Spot handelt
(`XBTUSDC`, `ETHUSDC`, `SOLUSDC`, `XRPUSDC`, dazu ADA/LINK/AVAX/DOT/LTC/BNB, gut
vier Dutzend). Mindestmengen: BTC 0,00005 / ETH 0,001 / SOL 0,06 / XRP 1,65.
Pruefen laesst sich das oeffentlich und ohne Schluessel:
`GET /0/public/AssetPairs`, dann auf `quote == "USDC"` filtern — **die
Waehrungsspalte ist die Wahrheit, nicht der Paarname.**

Die Haus-Spuren sind auf EUR-Paare verdrahtet: `PAARE` in
`mosaic/kraken_spot.py`, `PAAR` in `moondev_marktlage/live_kraken.py`, `paar` in
`nautilus_kraken/wachen.json`, `waehrung`/`guthaben_waehrung` in
`kraken/wachen.json`. Die Umstellung ist je Spur EINE Tabelle — aber sie ist ein
**Buchvorgang, kein Schalter** (ein Waehrungswechsel ist derselbe Fall wie der
Instrumentenwechsel weiter unten: offene Positionen mit EUR-Einstiegen werden
vom ersten Zyklus gegen USDC-Kurse gerechnet und alle flachgestellt).

- **Erst den ORDERWEG zaehlen, dann die Boerse waehlen.** Einen Kraken-Orderweg
  haben `kraken`, `mosaic`, `moondev_marktlage`, `nautilus_kraken` (und
  `moondev_listingarb` als vorhandener Pfad); `nautilus_kraken_futures` ist
  USD-Margin, kein USDC-Spot; Spuren ohne Orderaufruf sind nicht "auf Kraken
  schaltbar", sondern gar nicht handelbar — eine Spur, die Kraken nur fuer
  Kerzen liest (`orbk`), hat damit keinen Orderweg.
- **Vorbedingung ist Guthaben in der Quotewaehrung**, nicht Code: ein Konto kann
  EUR halten und 0,01 USDC. Kraken-Codes lesen (`kraken._roh_privat('Balance')`):
  Fiat traegt ein `Z`-Praefix (`ZEUR`, `ZUSD`), Krypto nicht (`USDC`, `XXBT`,
  `XETH`, `SOL`).
- **Falle bei der Kontolesung:** die Balance alphabetisch ausgeben und mit `head`
  abschneiden schneidet genau `ZEUR`/`ZUSD` ab (sie stehen am ENDE) — daraus wird
  schnell der Fehlschluss "kein Fiat auf dem Konto". `head`/`tail` nie als
  Beweismittel fuer eine Kontolesung; gezielt filtern (`guthaben('ZEUR')`) oder
  die Ausgabe vollstaendig zeigen.
- **Waehrungsrisiko nennen:** ein EUR-Konto, das USDC-Paare handelt, traegt
  zusaetzlich EUR/USD. Fuer dieselbe Bewegung in EUR ist das kein
  Genauigkeitsgewinn, sondern ein neues Risiko — die Umstellung nur bauen, wenn
  die Rechnung in USDC gewollt ist. EURC ist der Euro-Stablecoin: EURC-quotierte
  Paare sind dieselbe Waehrungsfamilie wie EUR (kein neues EUR/USD-Risiko),
  USDC-quotierte tragen es. Deshalb lassen sich EURC-Paare frei ergaenzen,
  waehrend USDC-Paare strukturell gesperrt bleiben, bis USDC-Guthaben da ist.

## Eine Spur von EINER Quotewaehrung auf MEHRERE generalisieren (EUR -> EUR/EURC/USDC)

Eine Spur, die hart auf eine Quotewaehrung verdrahtet ist (Watchlist nur
EUR-Paare, Guthaben-Tor `guthaben("ZEUR")`, alle Betragsfelder `_eur`), kann
zusätzlich EURC-/USDC-Paare handeln, ohne die Strategie anzufassen. Das Muster
ist ein BUCHVORGANG wie der Instrumentenwechsel weiter unten, aber die
Generalisierung selbst ist Code:

1. **Die Quotewaehrung je Paar aus der API ableiten, nicht aus dem Namen.**
   `AssetPairs[paar].quote` ist die Wahrheit (`ZEUR`/`EURC`/`USDC`), der
   Paarname nicht. Ein Filter auf `quote == "EURC"`/`"USDC"` findet die Paare;
   ein Filter auf `ZEURC`/`ZUSDC` (mit Z-Praefix) findet NICHTS, weil
   Stablecoins kein Z tragen — nur Fiat hat es.
2. **Das Guthaben-Tor fragt die Quotewaehrung des jeweiligen Paares**, nicht
   eine hart gesetzte. Eine Spur, die immer `guthaben("ZEUR")` liest, sieht
   fuer ein EURC-Paar 0 und sperrt es dauerhaft, obwohl EURC frei liegt. Das
   Tor wird waehrungsbewusst: `guthaben(quotewaehrung(paar))` gegen den
   Mindestbetrag in DIESER Waehrung.
3. **Das Buch bleibt in der Waehrung der Spur** (EUR); die Quotewaehrung ist
   eine Eigenschaft des ORDERWEGS je Paar, nicht des Buchs. Betragsfelder
   (`max_pro_trade_eur`) bleiben die Nominale; nur das Tor und die Anzeige
   werden waehrungsbewusst.
4. **EURC-Paare in die Watchlist aufnehmen, USDC-Paare auch — aber USDC bleibt
   gesperrt, bis USDC-Guthaben da ist.** Das Guthaben-Tor in der Paarwaehrung
   ist eine Versicherung, kein Ertrag: es haelt die Spur von einem Kauf fern,
   den die Boerse ablehnt, und es ist kein Grund, die Faehigkeit nicht zu
   bauen — nur ein Grund, sie spaeter scharf zu schalten.
5. **Vor dem Bauen die Konto-Waehrungsbestaende lesen** (`kraken._roh_privat('Balance')`),
   nicht raten: welches Kapital liegt frei (EURC kann mehr sein als EUR), und
   welche Waehrung die Spur damit tatsaechlich nutzen kann. Die Prioritaet der
   Spuren richtet sich danach, welche das vorhandene Kapital nutzen kann.

## omnitrade ist KEINE Spur — und omniquant hat keinen Orderweg

`omnitrade` ist kein Ordner unter `Agenten/Handel`: es ist ein rein lesender
Rust-Lauf (`Werkstatt/omnitrade`, Statusdatei `status/live.json`, gelesen von
`omnitrade_bridge.py`/`omnitrade_lauf.py`). Es bewegt kein Kapital und hat
keinen Orderweg im Haus. `omniquant` ist eine Papier-Spur auf dem
Prognose-Bericht (`--live` verweigert, kein Broker-Aufruf). Sagt Max
"omnitrade/omniquant bauen", heisst das: einen LIVE-ORDERWEG anbinden — nicht
"die Spur ist schon da, nur verdrahten". Vor dem Bauen pruefen, ob die Spur
ueberhaupt einen Orderaufruf im Code hat (`spuren_stand.py` Spalte
"Order-Code"), sonst baut man an einer Spur, die gar nicht handeln kann.

### Der gebaute Weg: den FREMDREN Lauf spiegeln, nicht nachbauen (30.09.2026)

Umgesetzt in `Agenten/Handel/omnitrade` (Weg B der Entscheidung von Max, nach
Auftrag "nur noch omnitrade auf kraken handel erlaubt"). Vier Regeln, die den
Aufbau tragen und auf JEDE Spur uebertragbar sind, die einen fremden Lauf
liest:

1. **Den ZUSTAND spiegeln, nicht die Orderliste.** Ein Statusdokument, das
   `recent_orders` als Ringpuffer fuehrt (dort `MAX_ORDERS = 20`), verliert bei
   einem Ausfall alles dazwischen — wer daraus Ereignisse nachzaehlt, verpasst
   sie still. `net_quantity > 0` sagt dagegen zu jedem Zeitpunkt, ob der Lauf
   eine Position haelt.
2. **`state: running` ist kein Beweis — zwei Zeugen.** Nach einem harten Ende
   bleibt die Statusdatei mit einer TOTEN PID auf `running` stehen (gemessen:
   `live_adx_macd_BTCUSDC.json` lag zwei Stunden so im Statusordner, waehrend
   `omnitrade_start.py liste` "PID lebt nicht" meldete). Einstieg nur bei
   frischer Datei UND lebender PID (`omnitrade_lauf.pid_lebt`); der Ausstieg
   greift auch bei `stopped` (die CLI verkauft beim Beenden), **nie** bei
   `starting`/`error` — ein Abbruch ist kein Handelssignal.
   **`omnitrade_start.py` schreibt JE LAUF eine eigene Statusdatei
   (`live_<strategie>_<symbol>.json`); `status/live.json` ist nur der
   Standard-Anker der ANZEIGE** (`omnitrade_bridge.pfad()` =
   `OMNITRADE_STATUS` oder `live.json`). Ein Wrapper, der ohne Argument den
   Stand zeigt, kann damit auf eine TOTE Alt-Datei zeigen (gemessen:
   `live.json` mit PID 55888 — Prozess laengst weg — meldete „veraltet",
   waehrend `live_adx_macd_BTCUSDC.json` mit PID 61280 frisch lief).
   „veraltet" an der Anzeige ist kein Beleg, dass kein Lauf laeuft: erst
   `tasklist`/`pid_lebt` nach omnitrade-cli.exe fragen und ALLE `live*.json`
   im Statusordner lesen (die Spur `lesen.py` macht das automatisch), dann
   urteilen. Der Anzeige-Anker laesst sich ueber `OMNITRADE_STATUS` auf den
   lebenden Lauf richten.
3. **Den echten Orderpreis buchen, nicht den letzten Kerzenschluss.** Ein
   Fremdlauf steigt mit einer echten Order aus; ihr Preis steht in
   `recent_orders`. `last_close` als Verkaufskurs ins Journal zu schreiben,
   erfindet einen Kurs. Regel in `quelle()`: Verkaufspreis genau dann, wenn der
   Lauf NICHT offen ist; `last_close` bleibt die Bewertung der offenen Position.
4. **Der Fremdlauf ist die Ausstiegslinie, der Stop ist der Notaus.** Der Stop
   wird WEIT gesetzt (hier 8 %) und das Ziel praktisch unerreichbar (10R) —
   sonst bucht die Spur Runden, die der fremde Lauf nie genommen haette. Der
   Ausstieg kommt ueber `spur_buch.zyklus(..., zusatz_ausstieg=...)` mit einem
   eigenen Grund (`omnitrade flat`).

Dazu die zwei Fallen des Anschlusses: **die Quotewaehrung vor der ersten
Sperrenpruefung setzen** (`boersen_binden(w)` → `weg.setze_quote(w["kraken_quote"])`),
sonst findet die Paar-Tabelle ein USDC-Paar nicht — sie faellt ausdruecklich
nicht auf eine andere Waehrung zurueck, damit keine Order im falschen Markt
landet. Und: **`spur_buch.zyklus` steigt bei leeren Daten VOR `pruefe_ausstiege`
aus** — liefert `quelle()` nur laufende Laeufe, kann ein beendeter Lauf die
Position nie schliessen. Deshalb kommen ALLE lesbaren Laeufe ins `daten`-Dict
und `signal()` prueft `laeuft` UND `offen`.

## Einen WAEHRUNGSWECHSEL der Signalquelle planen (USDT -> USDC)

"Nur noch USDC" klingt nach einer Zeile in der Konfiguration und ist ein
Fünf-Stellen-Vorgang. Die Signalquelle, der Orderweg, die Anzeige, die
Auswertung und die Schattenarme tragen die Quote jeweils an eigener Stelle —
wer nur die Quelle umstellt, verliert Kandidaten, ohne dass irgendwo ein Fehler
erscheint. **Vor dem Umstellen alle fünf Stellen messen, dann in dieser
Reihenfolge arbeiten:**

| Stelle | Was dort die Quote traegt | Folge, wenn sie stehen bleibt |
|---|---|---|
| Konfiguration der Signalquelle (`maerkte` in der Berichts-Config, je Fassung) | welche Paare der Lauf ueberhaupt sieht | Kandidaten bleiben auf der alten Quote |
| Instrumenten-Aufloesung des Orderwegs (Paar-Tabelle + Ableitung) | `Inst-QUOTE` → Markt-Symbol | Einstieg wird mit „gibt es am Zielmarkt nicht" abgewiesen |
| GUI der Spur | fest verdrahteter Berichtspfad, Spaltenueberschrift „Wert USD" | zeigt den falschen Bericht oder die falsche Waehrung |
| Berichts-Holer (`lage.py`) | `waehrung`, `papierfest` als Konstante | zeigt „kein Live-Zweig" fuer eine live handelnde Spur |
| Schattenarm-Config | `handel_erlaubt`, Vermerk „kein Orderpfad" | Widerspruch zum Hauptarm, den niemand aufloest |

**Die Marktbreite der neuen Quote zuerst messen — sie ist die eigentliche
Entscheidung, nicht die Schreibweise.** Gesichert oeffentlich, ohne Schluessel:
der volle Ticker-Satz, dann auf die Quote filtern und gegen den Mindestumsatz
zaehlen. Der Wechsel einer breiten auf eine schmale Quote kostet Dutzende
Kandidaten: gemessen USDT+USDC 49 Paare ueber dem Filter gegen USDC allein 6
(bei 298 USDC-Paaren insgesamt). Steht die Antwort auf wenige Märkte, gehört
DIE Zahl in den Vermerk der Config-Datei — sonst haelt später jemand die kleine
Zahl fuer einen Fehler und stellt die Quote zurueck.

**Umgekehrt gilt derselbe Massstab: eine Filterwegnahme, die mehr Kandidaten
zeigt, ist erst dann eine Verbesserung.** Die Breitenmessung beantwortet "wie
viele Kandidaten sehen wir"; die Frage, die ueber die Konfiguration entscheidet,
ist "wie viele davon erfuellen die Tore und sind an der Zielboerse orderbar".
Beide Zahlen sind richtig und fuehren zu entgegengesetzten Entscheidungen.

Deshalb bei jeder Filteraenderung die **Differenzmenge gegen die Tore fahren**,
nicht nur zaehlen. Zwei Klassen, die dabei regelmaessig herausfallen und getrennt
zu benennen sind:

- **Fiat-Quote-Paare** (EUR, BRL, TRY, ...) stehen in derselben Tickerliste wie
  die Krypto-Paare und fallen an Toren durch, die aus dem Wechselkurs folgen —
  das Ziel liegt strukturell nah am 60-Tage-Hoch, also ist der Chance-Risiko-
  Quotient kleiner als der Stop. Sie sind als Signal wertlos, egal wie gross ihr
  Umsatz ist. Ohne diese Trennung liest man die Breite als Kandidatengewinn.
- **Kandidaten ohne Markt an der Zielboerse** sind als Signal vollwertig (der
  Kurs stimmt) und als Position wertlos. Beide in einer Zahl zu mischen meldet
  eine Breite, die es nicht gibt.

Gemessen (Filterwegnahme gegen die echte Ticker- und Instrumentenliste): die
Differenzmenge war vollstaendig Fiat, und ohne Fiat blieben exakt so viele
Kandidaten uebrig wie mit dem Filter. Die Erweiterung wurde daraufhin aktiv
zurueckgenommen — mit Begruendung und Messung im Vermerk der geaenderten
Config-Datei, nicht nur in der Antwort.

**Was neben einer Filterwegnahme wirklich 0 Treffer verursacht, ist fast nie
der Filter.** Ein Lauf ueber 50 bis 60 Maerkte mit 0 Treffern liegt am Tor, das
gegen die aktuelle Marktlage rechnet (typisch Chance-Risiko gegen das
60-Tage-Hoch, wenn der Markt ueberall dort steht). Das ist eine Marktlage und
keine Konfiguration; **an ihr aendert kein Filter etwas.** Deshalb bei 0
Treffern zuerst die Tore gegen die vorhandenen Kandidaten fahren und den
geschlossenen Tor nennen, bevor eine Konfigurationsaenderung vorgeschlagen wird.

**Ein fehlender Konfigurationsschluessel ist ein Filter, kein Fehler.** Wird ein
Schluessel entfernt, um eine Vorgabe zu loeschen, muss der **Aufrufer** den
Schluessel mit `.get()` lesen — sonst bricht der Lauf mit `KeyError` ab, und
der Abbruch sieht nach einem Fehler in der Konfiguration aus statt nach dem
Absicht. Gehoert der Wert in eine Meldung (etwa "ueber welche Maerkte"), tritt
an seine Stelle ein lesbarer Ersatz ("alle Quotes").

**Der Orderweg muss die Basis-ABWEICHUNG können, sonst ist die Umstellung eine
Verschlimmbesserung.** Die Regel `PF_<BASIS>USD` ist fast, aber nicht ganz
richtig: gemessen gibt es `PF_XBTUSD` statt `PF_BTCUSD`, `PF_CTSIUSD` statt
`PF_CTUSD` und gar kein `PF_XMSTRUSD`. Eine Ableitung, die das nicht abbildet,
erzeugt ein Symbol, das es nicht gibt — und das faellt als „am Zielmarkt nicht
handelbar" durch, also als *unbelegter Markt*, nicht als *fehlende Abbildung*.
Deshalb: **die Basis-Ausnahmen als gemessene Abbildung in die Aufloesung, und
alles, was die Boerse nicht fuehrt, namentlich sperren** (`KEIN_MARKT` + Fehler mit
dem Namen), nie still auf einen anderen Markt umlenken.

**Eine offene Position auf der alten Quote laesst man stehen.** Der Wechsel der
Signalquelle fasst sie nicht an; sie wird nur im Buch weiter unter ihrem alten
Namen gefuehrt (inklusive Zielmarkt-Symbol). Wer sie vorher schliesst, nimmt
dem Nutzer eine Position weg, ohne zu fragen — die Aufgabe war die
Signalquelle, nicht das Buch.

**Anzeige und Berichts-Holer lesen die Konfiguration, nie eine Konstante.**
Faellt die Anzeige auf den fest verdrahteten Berichtspfad zurueck, zeigt sie
einen anderen Report als den, den die Spur handelt, und der Bildschirm
widerspricht dem Journal, ohne dass jemand den Widerspruch bemerkt. Der Pfad
gehoert aus der Wachen-Datei gelesen (Fassungsfeld), die Waehrungsangabe aus der
Order-Boerse, und die Live-Faehigkeit als Parameter des Holers statt als
festes Etikett.

**Schattenarme nicht als Kopien der Hauptarm-Datei behandeln.** Beide teilen das
Wissen („diese Spur hat keinen Orderweg"), aber sie werden zu verschiedenen
Zeiten angefasst. Ein `handel_erlaubt: false` plus ein Vermerk, der die
Faehigkeit des Hauptarms verneint, ist nach dem Bau des Orderwegs FALSCH —
mit Datumsvermerk berichtigen, nicht stillschweigend.

## Instrumentenwechsel mit offenem Buch

Ein Instrumentenwechsel ist kein Konfigurationswert, sondern ein BUCHVORGANG.
Die Strategie bewertet JEDE Position mit dem Kurs des EINEN konfigurierten
Symbols: nach einem Wechsel liegen Positionen mit Einstiegen um 81.500 im Buch,
waehrend der Kurs jetzt 117 ist - der erste Zyklus liest das als gerissenen Stop
und bucht alle Positionen aus. Das ist ein Buchhaltungsunfall, kein Handel, und
er faellt nur auf, wenn man das Buch vorher ansieht.

Reihenfolge (Papier, kein Geld):

1. Kurs des ALTEN Instruments holen (`letzter_kurs(alt)`) - geschlossen wird zum
   echten Kurs, nicht zu einem erfundenen.
2. Jede offene Position mit den Funktionen der STRATEGIE selbst schliessen
   (`verkaeuflich(menge, kurs, w)` fuer den Erloes, `grund=symbolwechsel`) und
   als Journalzeile schreiben. Keine eigene G/V-Formel bauen - sie waere eine
   zweite Wahrheit neben der Strategie und driftet beim naechsten Umbau.
3. Zustand mit leerem `positionen` schreiben.
4. Spiegeln (Bedingung 4): der Wechsel ist ein Zustandswechsel wie jeder andere.
5. ERST JETZT `symbol`/`paar` in der `wachen.json` tauschen.
6. Gegenprobe ueber den Zustand, nicht ueber die Absicht: `letzte_quote` muss den
   Kurs des NEUEN Instruments tragen (117 statt 84.000), und die Vorschau mit
   `MAXHIRN_ROUTINE=1` muss den neuen Namen in der "Waere"-Zeile nennen.

Welches Instrument in Frage kommt, entscheidet die MINDESTMENGE gegen das freie
Guthaben (`handelbar()`/`einschuss()`), nicht das Nominal des Signals: auf einem
Markt mit ganzen Kontrakten ist der kleinste Handel ueberall der groesste Posten
der Rechnung.

**Und was nicht passieren darf: stilles Aufrunden.** Ein Sendeweg, der eine zu
kleine Menge auf die Mindestgroesse rundet (`max(1, round(menge))`), macht aus
einem gedachten 1-USD-Einsatz eine Position von 118 USD - die Wache hat eine
andere Zahl erlaubt, als die Boerse fuellt. Die Kette sperrt das ausdruecklich und
nennt die Zahl ("Einsatz 1.00 kleiner als 1 Kontrakt PF_SOLUSD (11.75 USD
Einschuss) - Mindestgroesse der Boerse").

## Eine Boerse wieder ENTZIEHEN ("nur noch <Programm> darf auf <Boerse> handeln")

Der Rueckweg zum Abschnitt oben. Drei Schalter, und sie greifen zu
verschiedenen Zeitpunkten:

| Schalter | Wirkung | greift |
|---|---|---|
| `handel_erlaubt: false` (+ `freigabe.erfuellt: false`) in der `wachen.json` | die Spur sperrt sich selbst | sofort, ohne Neustart |
| Boersenliste (`boersen: ["okx"]`) | die Spur handelt weiter, aber auf der anderen Boerse | sofort |
| `dauerlauf.AUTO_FREIGABE` | kein selbsttaetiges Freigabefenster mehr | erst nach einem Neustart des Dauerlaufs |

- **Nur der erste Schalter ist die Sperre, die zaehlt.** Eine Spur, die aus
  `AUTO_FREIGABE` faellt, aber `handel_erlaubt: true` behaelt, handelt weiter,
  sobald jemand das Fenster von Hand oeffnet. Umgekehrt ist die Auto-Freigabe
  ohnehin wirkungslos, sobald die Sperrliste MEHRERE Gruende nennt:
  `dauerlauf.nur_fenster_fehlt` verlangt GENAU EINEN, und er muss
  "Freigabefenster" heissen. Nach dem Entzug ist die Sperrliste der Spur
  ohnehin mehrgruendig - deshalb wirkt der Entzug auch ohne Neustart.
- **Eine Sperre ist kein Umzug - vorher pruefen, ob der Nachfolger die Boerse
  ueberhaupt kennt.** Belegt: ein Fremdprogramm, das die Boerse uebernehmen
  sollte, kennt nur `binance` und `okx`, und sein Live-Befehl weist jedes andere
  `--exchange` mit einer festen Liste ab. Nach dem Abschalten handelte NIEMAND
  mehr dort. Die Anweisung war als Sperre umgesetzt, nicht als Umzug - genau das
  gehoert in den Bericht, sonst liest Max "umgestellt" und erwartet Orders.
- **Erst die OFFENEN Positionen absichern, dann die Spur abschalten.** Eine
  entzogene Spur hoert auf, ihren Teil zu tun; die Positionen an der Boerse
  bleiben stehen. Wer abschaltet, ohne vorher zu pruefen, dass die
  Boersen-Stops liegen, schaltet den Waechter ab, der die Position ohnehin
  nicht mehr bewacht haette.
- **Die Pruefung ist NICHT "steht eine Kennung im Buch".**
  `boersen_stop_fehlt: false` heisst nur "beim Einstieg wurde ein Stop
  bestellt". Eine Order kann an der Boerse spaeter `canceled` sein, waehrend das
  Buch unveraendert aussieht - belegt: drei Stops ueber rund 258 EUR standen auf
  `canceled`, das Buch meldete weiter Schutz. Die Wahrheit kommt aus
  `order_details(txid)` -> `status == "open"` (Kraken) bzw. der Liste der
  offenen Algo-Orders (OKX); das Haus-Werkzeug dafuer ist
  `kraken/spot_stops.py` (Vorschau Standard, `--anwenden`), es liest Bestand UND
  Orders gegeneinander. **Ein Stop, den niemand nachprueft, ist eine Annahme,
  kein Schutz** - der scanner hat diesen Abgleich seit dem 28.09. im Live-Zyklus
  (`scanner/boersenstops.py`), die uebrigen Boersen-Spuren nicht.
- **Ein Bestand von 0 bei gefuellter Position ist ein Geist, kein Rundungsrest.**
  Dieselbe Lesung deckt die Gegenrichtung auf: eine Position im Buch, deren Coin
  an der Boerse 0 steht (Geist), und einen offenen Stop, zu dem es keinen
  Bestand gibt (Waise). Beides ausbuchen bzw. stornieren, BEVOR die Spur
  abgeschaltet wird - danach hat niemand mehr einen Grund, in ihr Buch zu sehen.
- **Handwerkzeuge bleiben scharf.** `kraken/spot_stops.py`,
  `kraken/waisen_stops.py`, `kraken/margin_stops.py`,
  `mosaic/stops_nachziehen.py` und das MCP-Werkzeug mit Beleg ordnen weiterhin -
  sie sind Handwerkzeug, kein Automat, und werden bewusst NICHT gesperrt. Die
  Sperre gilt den SPUREN. Das gehoert in den Bericht, sonst liest "die Boerse ist
  gesperrt" wie eine Kontosperre.
- **Nachweis der Wirkung, nicht der Absicht:** je Spur `handeln.py --vorschau`
  mit `MAXHIRN_ROUTINE=1` - die entzogene Boerse darf in der Zeile
  "Live waere gesperrt durch:" nicht mehr auftauchen, die abgeschaltete Spur
  muss `handel_erlaubt=false` nennen. Danach `spiegelstand.py`.
- **Vor dem Umschalten AUF eine Boerse erst nachsehen, ob sie gerade entzogen
  wurde.** `dauerlauf.AUTO_FREIGABE` traegt die datierten Vermerke des Entzugs
  („nur noch <Programm> auf <Boerse> handel erlaubt"). Eine Spur auf diese Boerse
  umzustellen ist dann kein Konfigurationswert, sondern ein Widerspruch zu einer
  stehenden Entscheidung von Max — und der faellt nicht auf, weil die Spur
  technisch sauber arbeitet. **Und die Liste ist dabei selbst oft unvollstaendig:**
  eine Spur, die auf der ANDEREN Boerse steht, bleibt zu Recht in
  `AUTO_FREIGABE` — aus „die Spur steht noch drin" folgt also NICHT „diese Boerse
  ist erlaubt". Reihenfolge: die Vermerke lesen -> die Boerse DIESER Spur pruefen
  -> erst dann umstellen. Eine versehentliche Umstellung nimmt man wortlos
  zurueck und belegt die Ruecknahme mit `git diff --numstat` (0/0 heisst wirklich
  identisch mit `HEAD`).
- **Der entzogene Weg bleibt im Code.** Die Sperre ist ein Wachen-Schalter, kein
  Rueckbau: die Orderfunktionen, Tests und das Buch bleiben, damit die Spur ohne
  Neubau wieder scharf gestellt werden kann. Wer den Code entfernt, muss ihn
  spaeter neu schreiben - und die Testsuite verliert dabei ihren Gegenstand.

Zwei Beispiele fuer die Nutzbarkeit dieser Unterscheidung: **eine Waehrung, die
es fuer die Produktklasse nicht gibt, sieht aus wie ein Konfigurationsfehler
und ist einer** (gemessen: null USDC-SWAP-Maerkte bei OKX, waehrend die Spur auf
USDC laeuft) - und **ein Gebuehrensatz aus der anderen Produktklasse** (Spot gegen
Futures) verschiebt das Vorzeichen einer Rundenauswertung.
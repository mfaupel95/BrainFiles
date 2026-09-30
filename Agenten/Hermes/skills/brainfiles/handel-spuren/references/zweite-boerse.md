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
  die Rechnung in USDC gewollt ist.

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
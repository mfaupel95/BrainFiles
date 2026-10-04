# Gebuehren belegen statt annehmen

Wann: eine Spur soll beurteilt werden (f_max, netto, Freigabe), zwei Spuren tragen
fuer dieselbe Boerse verschiedene Saetze, oder eine Spur meldet im Bericht
"BRUTTO und UNBEKANNT".

Kernsatz: Eine Gebuehr wird an einer ECHTEN Fuellung UND am Kontotarif gemessen -
nie an einer Tarifseite, nie aus dem Gedaechtnis, nie von einer anderen Boerse.

## Die zwei Zeugen (OKX, rein lesend, ohne Order)

* **Tarif des Kontos**: `GET /api/v5/account/trade-fee?instType=SPOT` (bzw.
  `FUTURES`) -> `level`, `maker`, `taker` als Bruchteil je Seite. OHNE `instId`
  funktioniert es; MIT `instId` antwortet OKX bei XPERP-Kontrakten
  `50016 instId and instType don't match`.
* **Echte Fuellung**: `GET /api/v5/trade/fills?instType=SPOT&limit=20` ->
  `fee`, `feeCcy`, `fillPx`, `fillSz`. Der Satz ist
  `|fee| / (fillSz * ctVal * ctMult * fillPx)`; `ctVal`/`ctMult` kommen aus
  `/api/v5/public/instruments` - **ein XPERP-Kontrakt ist NICHT 1 USD**
  (gemessen: ZEC 0,01 / ADA 10 / VVV 0,1). Ohne die Kontraktgroesse rechnet man
  den Satz um Faktor 100 falsch.
* Aufruf im Haus: `scanner/okx.py` (`_roh(pfad, signiert=True)`; GET-Parameter
  gehoeren in den PFAD). `OKX_SIMULATED` darf NICHT gesetzt sein - sonst misst
  man das Papierkonto, und dessen Tarif sagt nichts ueber echtes Geld.
* **Kraken**: Fuellung plus `/0/private/TradeVolume` (der Haus-Client hat dafuer
  keinen eigenen Aufruf; die Messung vom 22.09.2026 steht in
  `kraken/wachen.json` unter `_gebuehren_abo_widerlegt`). Futures: eigener
  Dienst `futures.kraken.com` - gemessen 25.09.2026: 0,04-0,05 % je Seite.

## Messwerte 01.10.2026 (eigenes OKX-Konto, EEA)

| Markt | taker je Seite | Zeugen |
|---|---|---|
| OKX Spot | **0,10 %** (`gebuehr_taker: 0.001`) | Tarif `Lv1 taker=-0.001` UND Fuellung `HYPE-USDC` 0,002772544 auf 2,77254 USDC |
| OKX Futures/XPERP | **0,05 %** (`gebuehr_taker: 0.0005`) | Tarif `taker=-0.0005` UND Fuellungen ZEC-/ADA-`USD_UM_XPERP` je 0,0500 % |
| Kraken Spot | 0,60 % (`0.006`) | Fuellung + `TradeVolume` (22.09.2026) |
| Kraken Futures | 0,04-0,05 % (`gebuehr_pct: 0.05`) | Round-Trip 0,0029 USD auf 4,55 USD (25.09.2026) |

Vorher rechnete das Haus OKX-**Spot** mit 0,05 % - dem halben Satz, weil der
Futures-Satz fuer beide Maerkte benutzt wurde. Jede Netto-Zahl war damit um
0,1 Prozentpunkte je Runde zu freundlich, auch bei `scanner` (der einzigen Spur
mit belegtem Vorteil).

## Einheiten - der haeufigste Fehler

* `gebuehr_taker` = **Bruch je Seite** (`0.001` = 0,10 %). `replay.gebuehr_fuer()`
  gibt daraus Prozent je Seite (`* 100`); die Auswertung rechnet
  `kosten = einsatz * 2 * gebuehr`; `kosten_wendepunkt.urteil()` vergleicht mit
  `f_max` in **Prozent je Runde** (bis 30.09.2026 wurde der Bruch mit
  Prozentzeichen gedruckt - Faktor 100 zu klein).
* `gebuehr_pct` = **Prozent je Seite** (`0.1` = 0,10 %) - eigene Arme
  (`gitter`, `omniquant`, `kopier`, `kopier1zu1`, `nautilus*`). Zwei Felder, zwei
  Einheiten: wer eines setzt und das andere liest, aendert nichts.
* **Die Auswertung liest NUR `gebuehr_taker`, und ein fehlendes Feld ergibt 0.0 -
  nicht "unbekannt".** `auswertung_alle.gebuehr_fuer()` gibt bei fehlendem
  `gebuehr_taker` exakt `0.0` zurueck; die Spur erscheint damit als KOSTENLOS,
  nicht als unbestimmt. Ein Arm, der nur `gebuehr_pct` traegt, wird also nicht
  auffallen, sondern schoen rechnen - das ist der gefaehrlichere Fall als eine
  leere Anzeige. Beide Felder setzen (so geschehen bei `nautilus`,
  `nautilus_kraken_futures` und `omniquant`). Gegenprobe: `gebuehr_taker`
  entfernen und die Auswertung laufen lassen - sie muss dabei 0.0 melden.
* Der Futures-Arm `nautilus_kraken_futures` faehrt aus dem Ordner
  `nautilus_kraken`, seine Wachen heissen `wachen.futures.json`; ohne
  `auswertung_alle.WACHEN_SUFFIX` liest der Bericht die Spot-Wachen.

## Die Boerse der SPUR, nicht des Ordners

Spot und Perp kosten bei derselben Boerse verschieden viel. Die Zuordnung steht
in `replay.SPUR_BOERSE` und ist nur ein RUECKFALL - der eigene Wert in der
`wachen.json` hat Vorrang. Genau deshalb blieben zwei falsche Zuordnungen lange
unsichtbar: `gitter` stand als Perp (handelt aber BTC-USDT auf dem OKX-Spot),
`orb` stand als Spot (handelt `BTC-USDT-SWAP`). Beim Eintragen die eigene
`wachen.json` lesen, nicht den Ordner- oder Spurnamen deuten.

## Werkzeug

    cd Agenten/Handel
    .venv/Scripts/python.exe gebuehren_setzen.py              # Vorschau
    .venv/Scripts/python.exe gebuehren_setzen.py --anwenden   # mit .bak-JJJJMMTT
    .venv/Scripts/python.exe gebuehren_setzen.py --messen     # Kontosaetze abfragen

Nach dem Setzen: `auswertung_alle.py` laufen lassen und pruefen, dass nur noch
Spuren mit WIRKLICH unbekanntem Markt "BRUTTO und UNBEKANNT" melden.

## Nicht raten

Ist der Markt einer Spur nicht belegt (kein Instrument in der `wachen.json`,
Code nennt keinen), bleibt die Spur OHNE Gebuehrenfeld - "BRUTTO und UNBEKANNT"
ist dann die ehrliche Anzeige (`moondev_sniper`: pump.fun-Token, offen). Saetze
aus einem anderen Markt (Solana-Onchain 1 % bei `kopier`, Robinhood Chain 1 % bei
`robinhood_radar`) sind Modellannahmen und brauchen eine Entscheidung, keine
Messung.
## Drei Regeln, die aus dem Festziehen vom 01.10.2026 kommen

1. **Wert ohne Quelle ist nicht nachpruefbar.** Neben `gebuehr_taker` gehoert
   `_gebuehr_quelle` mit Messweg und Datum. Aeltere Wachen fuehren die Quelle unter
   `_gebuehren` bzw. `_gebuehren_abo_widerlegt` - auch das zaehlt, aber ein Wert
   ohne JEDE Notiz ist ein Fund (elf Wachen waren so).
2. **Der Markt bestimmt den Satz, nicht die Bequemlichkeit.** OKX-Spot 0.001,
   OKX-Perp 0.0005, Kraken-Spot 0.006 (je Seite, Bruch). Ein Test, der feste Werte
   je Spur einfriert, wird bei der naechsten Messung rot, obwohl der Code stimmt -
   pruefe die REGEL (Markt -> Satz) plus 'Quelle vorhanden'.
3. **Die Gebuehr folgt der ORDER-Boerse, nicht dem Kursweg.** Wichtiger noch: dass
   eine Wache zwei Boersen nennt, ist **kein Widerspruch**, sondern der
   Normalfall. Kurs und Order kommen selten aus derselben Quelle - eine Spur
   kann ihren Marktkurs ueber `okx.letzter_kurs` nehmen und auf Kraken Futures
   bestellen (gemessen: `omniquant`). Der Satz gehoert immer zur BOERSE, bei der
   die Order liegt; der Kursweg sagt nichts darueber. Wer hier zwei Saetze
   gegeneinanderstellt und den teureren nimmt, doppelt die Gebuehr einer
   gemessenen Buchung.
   **Der echte Widerspruch ist ein anderer Fall:** die Wache behauptet einen
   Satz, der zur gemessenen Fuellung dieser Orderboerse passt. Dann gilt die
   Messung, und die Behauptung wird korrigiert - nicht umgekehrt.
   **Gegenprobe:** bei jeder Gebuehr-Aenderung den Kursweg und die Orderboerse
   getrennt benennen. Folgen beide aus einem Feld, ist es geraten.

## Ein Boersenwechsel muss den Satz mitnehmen (gemessen 04.10.2026)

Der Satz gehoert zur **aktuellen** Orderboerse. Wechselt eine Spur die Boerse,
wandert das Feld von allein nicht mit — der Satz bleibt auf dem alten Wert
stehen und jede Auswertung rechnet weiter mit ihm.

Gemessen: nach einem Auftrag, der einer Spur eine Boerse entzog (ihre
Boersenliste verlor den Eintrag, es blieb eine andere), trug die Wache weiter
den Satz der **entfernten** Boerse — 1,2 % je Runde statt der gemessenen 0,2 %
(6-fach). Der Satz war seit Wochen falsch, ohne dass ein Test rot wurde: die
bestehende Pruefung verglich **Wert gegen Einheit**, nicht **Wert gegen
Boesenfeld**.

Zwei Regeln daraus:

1. **Der Satz wird aus dem Zustand abgeleitet, nicht aus der Historie.** Die
   aktive Boerse steht in der Vorragliste (`boersen[0]`), sonst im Einzel-Feld —
   nie in einem Vermerk und nie im gemessenen Wert von gestern.
2. **Die Ableitung liest Felder, nie das serialisierte Objekt.** Eine Regel der
   Form „ist das ein Perp?" wird aus den Feldern beantwortet, die den **Markt**
   bezeichnen (Instrument-Listen, Markttyp-Feld). Sie darf **nicht** das ganze
   Objekt nach einem Schluesselwort durchsuchen: die Notizfelder erwaehnen
   haeufig genau das falsche Wort („als PERP gefuehrt"), und dann verlangt der
   Abgleich von jeder Spot-Spur den Perp-Satz. Ausserdem: eine Einheit fuehrt
   ihr Instrument je nach Alter in einer **Einzelfeld**-Variante — beide
   Feldnamen pruefen, sonst gilt eine echte Perp-Spur als Spot.

**Gegenprobe des Werkzeugs:** eine Wache mit einem NOTIZ-Feld, das den
Gegensatz nennt, muss trotzdem den Satz des Markt-Felds bekommen. Und: die
Zuordnung **Spur -&gt; Markt** in Tests und Auswertungen wandert mit der
Boerse — ein Test, der eine Spur noch der alten Boerse zurechnet, ist eine
**kaputte Pruefung**, kein Befund (siehe `references/test-friert-stand-ein.md`).

## Der Satz der Boerse wird aus EINEM Ort gepflegt

Geaendert wird der Satz nie direkt in der Wache, sondern ueber die Regeltabelle
des Setzwerkzeugs — sonst zieht der naechste Lauf den Wert zurueck. Das
Setzwerkzeug traegt darum je Zeile eine Quelle mit Messweg und Datum; eine
Zeile ohne Boerse-Feld ist eine Modellannahme und wird nicht beurteilt.

Wer eine neue Boerse oder einen neuen Markt in einer Wache eintragt, muss sie
in der Satztabelle **mit** ihrem Satz aufnehmen. Ein Test, der die Liste der
bekannten Boersennamen im TestModul festhaelt, schlaegt dann an - richtig, aber
als Befund zu behandeln: der neue Name gehoert in die Liste, nicht in eine
Sonderbehandlung.

## Werkzeug-Fallen beim Setzen

- **Notiz da, Wert fehlt** ist ein eigener Fall: wer nur die Notiz auffrischt, setzt den
  Wert nie - und eine anschliessende Pruefung `float(d.get(feld))` faellt mit einem
  irrefuehrenden `TypeError: ... not NoneType` um. Erst `is None` pruefen, dann rechnen,
  und die Meldung muss Feld, Ist-Wert und Erwartung nennen.
- **Neuer Schluessel hinter dem bisher letzten** erzeugt ungueltiges JSON
  ('Illegal trailing comma before end of object'). In echten Wachen faellt das nicht auf,
  solange dort noch ein Schluessel folgt - im Test mit einer MINIMALEN Datei sofort.
  Nach jedem Einfuegen daher das Komma des letzten Schluessels entfernen.
- **`--anwenden` ueberschrieb eine Notiz, auch wenn der WERT richtig ist**
  (behoben, Regel unten). Er schrieb die Quelle aus dem eigenen Katalog, sobald
  eine Aenderung anstand - und nahm dabei eine zwischenzeitlich VERBESSERTE
  Notiz (mit gemessener Rueckrechnung) auf den aelteren Text zurueck.
  **Ein Schreibwerkzeug, das neben dem WERT auch eine BEGRUENDUNG pflegt, muss
  die beiden Fragen getrennt entscheiden:** ein FALSCHER Wert wird immer
  ersetzt, eine Notiz nur dann, wenn die vorhandene keinen staerkeren Beleg
  traegt. Erkennungsregel fuer den Beleg: ein Belegwort (GEMESSEN / GEKLAERT /
  BELEGT / NACHLAUF) UND ein Datum `dd.mm.yyyy`, das die neue Notiz nicht
  traegt. Die Regel bleibt absichtlich eng und einseitig - sonst entscheidet
  weiter der Katalog, damit kein Aufruf den Anspruch der Wachen still anhebt.
  **Und `vorschau()` wertet dieselben Regeln aus wie `anwenden()`:** eine
  Vorschau, die etwas anderes ankündigt als das Schreiben tut, ist schlimmer
  als keine Vorschau. Als Test reicht der Kern: richtigem Wert + besserer Notiz
  muss die Datei BYTE-GLEICH bleiben.
- **Die Erfolgsmeldung nannte einen RELATIVEN Pfad** (behoben) - und war damit
  von einem Testartefakt am Text nicht unterscheidbar. Ein Werkzeugtest legt
  `spur/wachen.json` in einem Tempordner an; seine Meldung las sich wie ein
  Schreibzugriff auf eine echte Wache (`gebuehr_taker: 0.001 -> 0.002`).
  **Bevor daraus eine Fehlersuche wird:** existiert der genannte Pfad im Repo?
  Ist `git diff --numstat` auf ihn leer? Hat die Datei eine mtime von weniger
  als zehn Minuten? Alles dreimal NEIN heisst Testartefakt. Grundregel fuer
  JEDE Meldung ueber einen Schreibvorgang - Erfolgszeile, Vorschau UND
  Fehlertext: sie nennt den **absoluten** Pfad, sonst traegt sie die Aussage
  nicht. Im Test ueber `os.path.commonpath` vergleichen, nicht per `startswith`
  auf einen String - gemischte Trennzeichen (`C:\…\spur/wachen.json`) lassen
  `startswith` scheitern, obwohl der Pfad stimmt.
- **Ein Testlauf meldet auch Module, die es nicht gibt.** `python -m unittest
  test_foo` auf einen falsch getippten Namen endet mit `FAILED (errors=1)` und
  sieht damit aus wie ein Fehlschlag des Hauses - es ist ein ImportError. Also
  `errors=1` IMMER mit `ls tests/test_*.py` gegenpruefen, bevor daraus ein
  Befund wird. **Und unittest schreibt sein Ergebnis nach `stderr`, nicht nach
  `stdout`:** ein Filter auf `r.stdout` liefert eine leere Liste und sieht aus,
  als haette der Lauf gar nichts getan.
- **`addCleanup(setattr, mod, name, mod.name)` sichert den BEREITS ERSETZTEN
  Wert** - der Ersatz lebt weiter und vergiftet jeden folgenden Test in der
  Datei (gemessen: drei Fehlschlaege, von denen keiner mit dem getesteten
  Verhalten zu tun hatte). `self.alt = gs.f` VOR dem Setzen merken und dieses im
  Cleanup zuruecksetzen.
- **Eine erweiterte Signatur trifft jeden handgebauten Double.** Wird
  `_feld_setzen(..., notiz_behalten=None)` um einen Parameter erweitert, bricht
  ein `lambda roh, feld, wert, quelle: ...` aus einem frueheren Test sofort ab -
  der Fehler zeigt sich als `TypeError ... got an unexpected keyword
  argument`, nicht als ein Fehlschlag der Pruefung. Alle Doubles mitziehen und
  den Bruch als SOLCHEN benennen, sonst repariert man den Test statt des Codes.
- **Ein fehlender Import faellt nur im ECHTEN Lauf auf.** `re` fehlte, nachdem
  eine neue Hilfsfunktion eingebaut worden war: die Tests riefen die Funktion
  mit einfachen Attributen auf und fuehrten den Ausdruck nie aus. Nach jeder
  neuen Regex oder jedem neuen Modul im Werkzeug den ECHTEN Aufruf fahren
  (`vorschau()`, im Trockenlauf) - ein gruener Testlauf sagt darueber nichts.

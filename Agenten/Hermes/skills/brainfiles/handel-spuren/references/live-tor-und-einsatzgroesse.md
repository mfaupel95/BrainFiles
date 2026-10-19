# Live-Tor und Einsatzgroesse

Zwei Regeln, die jede Spur mit echtem Orderweg braucht. Beide sind in
`moondev_marktlage` (`live_kraken.py`) und `mosaic` (`handeln.py`) umgesetzt —
Namensmuster: `einsatz_gedeckelt(eur, w)` bzw. `betrag_gedeckelt(betrag, w)`.

## 1. Ein Tor liest den Zustand des Zweigs, der SCHREIBT

Der Herzschlag ist das Alter des letzten ZYKLUS, nicht des Papierbuchs. Eine
Sperre, die nur `zustand.json` liest, waehrend die Spur live laeuft (und der
Papierzweig deshalb seit dem Umschalten nichts mehr schreibt), friert ein: nach
`herzschlag_max_minuten` sperrt sich die Spur SELBST — „Live waere gesperrt
durch: Herzschlag alt".

Doppelt schlimm mit Auto-Freigabe: `nur_fenster_fehlt` verlangt GENAU EINEN Grund,
und „Herzschlag alt" ist genau einer. Der Dauerlauf oeffnet also im 30-Min-Takt
Fenster fuer einen Lauf, der gar nicht handeln kann — der Ausfall sieht aus wie
Betrieb, es entstehen keine Fehlerzeilen, nur Stille.

Regel: den FRISCHESTEN der beiden Staende lesen (`zustand.json` UND
`zustand.live.json`). Nur Papier zaehlt weiter, damit eine Spur, die noch nie live
lief, sich scharf machen kann; nur Live waere ein Kreislauf (Papierzweig
aktualisiert nicht mehr, das Tor bliebe zu).

Gegenprobe nach dem Fix: `<spur>/handeln.py --vorschau` mit `MAXHIRN_ROUTINE=1`
muss „Live waere gesperrt durch: nichts" melden (bzw. nur echte Gruende nennen).

Merksatz: **Bei jeder neuen Sperre fragen — welcher Zweig schreibt die Datei, die
ich hier lese?** Ein Tor, das aus dem Zustand des falschen Zweigs liest, ist ein
Selbstsperrer.

## 2. Erst den Einsatz DECKELN, dann das Freigabefenster zeigen

Ein Einsatz ueber dem freien Guthaben ist eine von der Boerse ABGELEHNTE Order:
kein Handel, aber eine Journalzeile „kauf fehlgeschlagen", die wie ein Defekt
aussieht. Der Deckel gehoert deshalb VOR `hole_freigabe`/`freigabe_protokoll`,
damit das Fenster den Betrag zeigt, der wirklich ausgefuehrt wird.

Form: `gedeckelt = frei * (1 - gebuehr_taker - 0.002)`, danach runden.
Rueckfall-Regeln, die in den Tests festgehalten sind:

| Fall | Verhalten |
|---|---|
| Betrag passt ins freie Guthaben | unveraendert, kein Hinweis |
| Betrag zu gross | auf den Deckel zurueck, Hinweiszeile ins Log |
| Guthaben nicht lesbar (Ausnahme) | Betrag UNVERAENDERT lassen — die Sperrenkette hat denselben Abruf schon gemeldet, hier nichts erfinden oder still abschalten |
| kein Guthaben (0) | melden, nicht handeln |
| gedeckelter Betrag unter der Mindestmenge des Paares | die Mengenpruefung lehnt ab — ein eigener Mindestbetrag ist nicht noetig. Auf einem Markt mit GANZEN KONTRAKTEN rundet der Sendeweg dagegen still nach oben (min. 1 Kontrakt): dann sperrt die Kette ausdruecklich, siehe 5 |

Der Gebuehrensatz steht als Zahl in der `wachen.json` (`gebuehr_taker`), nicht im
Code. **Jede Spur mit Live-Pfad braucht diese Deckelung** — sonst waechst nur die
Fehlerzeile mit dem Limit.

Testmuster: die Deckelfunktion direkt pruefen (Seam `op_guthaben` der Spur
patchen, danach `addCleanup` zurueck) UND eine Quelltext-Pruefung, dass der
Deckel-Aufruf VOR dem Kaufaufruf steht (`quelle.index(...)` Vergleiche) — sonst
kann der Deckel an einer Stelle stehen, die nie erreicht wird.

## 3. Nach jeder Grenz-Erhoehung nachrechnen, WELCHES Limit danach bindet

Die Kette von der engsten zur weitesten Grenze: **je Trade (oder Risiko je
Position) → Anzahl Plaetze → Gesamtdeckel → freies Guthaben.**

- Ein hoeheres Je-Trade-Limit kann wirkungslos bleiben (Plaetze x Betrag liegt
  weiter unter dem Gesamtdeckel) oder den Gesamtdeckel ploetzlich binden.
- Umgekehrt bindet darunter oft allein das Guthaben — dann ist die Zahl am Papier
  richtig und live trotzdem nicht erreichbar.
- Im Bericht die Kette mit den ECHTEN Zahlen nennen, sonst ist die Aenderung nur
  eine Zahl. Und dazu genau eine Empfehlung: „die Grenzen sind nicht der Engpass,
  mehr Einsatz verlangt Guthaben" — nichts stillschweigend umschichten (Max
  schichtet kein Kapital um, wenn der Bestand passt).
- **Ein Guthaben-Tor ist die UNTERGRENZE, kein Puffer.** `mindest_guthaben*` wird
  mit dem KLEINSTEN Einsatz begruendet (Mindest-Einsatz + kleiner Puffer), nie mit
  einem alten Beispielbetrag. Die Schwelle sagt nur: „darf ich ueberhaupt starten?" —
  nicht, ob der GEPLANTE Einsatz (Definition nach Risikorechnung, dann live_max_*)
  auf das freie Guthaben passt. Solange die geplante Order groesser ist als das
  freie Guthaben *minus* Gebuehr/Puffer, ist ein niedriges `mindest_guthaben` trotzdem
  keine Kaufkraft — und ein hohes waere unnoetig. Symptom: viele Zyklen ohne Einstieg,
  das Tor nennt nur „nur X frei, noetig Y", aber eine Order des geplanten Betrags waere
  an der Boerse gescheitert (**insufficient balance**), erst NACH dem Kaufversuch.
  Gegenprobe: den gedeckelten Betrag (nach `liberal * (1 - geb - 0,002)`) mit dem
  Mindestbetrag des Instruments vergleichen, nicht den risikonormale.

## 4. Fehlendes Geld gehoert in die Sperrliste — mit Boerse und Waehrung

Ein Guthaben-Tor, das nur den Betrag nennt, ist zweideutig, sobald eine Spur
mehrere Boersen kennt: „nur 0.71 EUR frei, noetig 60.00" liest sich wie die
Boerse, die in der ANDEREN Waehrung notiert — und die Fehlersuche beginnt beim
falschen Konto.

- **Boerse UND Waehrung nennen** (`kraken: nur 0.71 EUR frei, noetig 60.00`) und
  bei mehreren Boersen die uebrigen Gruende daneben stellen
  (`- dazu okx: nur 0.15 USDC frei, noetig 60.00`). Sonst sieht eine geprueft-leere
  Boerse wie eine uebersprungene aus.
- **Fehlende freie Margin gehoert in dieselbe Sperrliste wie die Bedingungen**
  (Muster `swap`: `nur 0.15 USDC frei, noetig 50.00 (max_margin_je_anlauf_usd)`).
  Steht die Pruefung nur unmittelbar vor der Order, oeffnet AUTO_FREIGABE weiter
  Fenster fuer einen Lauf, der nicht handeln kann, und der Versuch endet als
  Orderfehler (`51008`) statt als lesbarer Grund. Heute bindet das Guthaben fast
  immer zuerst: die Konten sind bis auf Cent in laufenden Positionen besichert.
- **Eine gescheiterte Guthaben-Abfrage sperrt NICHT.** `None` zurueckgeben und den
  Grund weglassen — ein Netzfehler darf eine scharfe Spur nicht stilllegen.
- **Der Geldgrund darf das Wort „Freigabefenster" nicht tragen.**
  `nur_fenster_fehlt` liest GENAU EINEN Grund mit diesem Wort als Fenster-Bitte;
  ein Geldgrund daneben ist richtig (zwei Gruende = keine Bitte), ein Geldgrund
  MIT dem Wort waere eine falsche Bitte.

**Testfalle beim Einbau:** eine neue signierte Guthaben-Abfrage in der
Sperrfunktion trifft JEDEN bestehenden Test, der diese Funktion aufruft — ohne
Attrappe laeuft dort eine echte Kontoabfrage. Die Naht (`okxf.guthaben_usdc`,
`handeln._guthaben_roh`) im `setUp` der betroffenen Testklassen ergaenzen und im
`tearDown` zuruecknehmen, dazu ein Testfall je Zweig: Geld fehlt / Geld reicht /
Abfrage scheitert.

## 5. Ein Einsatz-Limit traegt den Waehrungsnamen der SPUR

Die Live-Grenzen heissen `live_einsatz_<waehrung>` und
`live_max_risiko_gesamt_<waehrung>` (EUR fuer die Spot-Spuren, USD fuer die
Futures-Spur). Liest die Ableitung nur EINEN Namen, ist das kein Fehler, sondern
ein stiller Rueckfall: die Spur rechnet mit dem PAPIER-Einsatz weiter, waehrend
`--wachen` den Live-Einsatz anzeigt - die Anzeige zeigt eine Grenze, die nicht
wirkt.

Belegt: `live_wachen()` las nur `live_einsatz_eur`. Bei einem Papier-Einsatz von
50 und einem Kontrakt zu 117 USD rundete der Sendeweg auf EIN Kontrakt = 118 USD,
also das 2,4-fache des gedachten Einsatzes - und nichts meldete es.

Regel: den Namen aus dem Waehrungsfeld der Spur bauen
(`betrag_feld(w, "live_einsatz")`) und, solange beide Schreibweisen im Bestand
sind, beide lesen - je Spur gewinnt genau einer. Und der Einsatz gehoert zuerst
gegen die MINDESTMENGE des Instruments geprueft: liegt er darunter, ist die
Sperre die richtige Antwort, nicht das Aufrunden.

Testmuster: je einen Fall fuer die EUR-Spur und die USD-Spur, dazu die
Zusicherung, dass die Papierwerte unberuehrt bleiben (die Funktion gibt eine KOPIE
zurueck, der Aufrufer schreibt `w` nicht in die Datei).

## 6. Die Sperrzeile muss es GEBEN — auch im gemeinsamen Kern

`dauerlauf.nur_fenster_fehlt()` liest die Ausgabe von `<spur>/handeln.py
--vorschau` und sucht GENAU EINE Zeile `Live waere gesperrt durch: …`. Fehlt die
Zeile ganz, gibt die Funktion `None` zurueck — und die Auto-Freigabe beantragt NIE
ein Fenster. Die Spur ist dann scharf, steht in `AUTO_FREIGABE`, traegt
`freigabe.erfuellt: true` — und handelt trotzdem nie.

Genau das war bei den Buch-Spuren der Fall: der gemeinsame Kern
`spur_buch.zyklus()` druckte bei `--vorschau` nur „Vorschau: keine Dateien
geschrieben." Es gab keinen `vorschau`-Zweig, der die Sperrenkette ueberhaupt
abfragte. Betroffen waren ALLE Spuren, die ihr Buch ueber `spur_buch` fuehren
(`moondev_listingarb`, `moondev_topmovers`, `trendwende_btc`, `liq_wand`,
`iv_wand`, `moondev_funding`) — und der Fehler sieht nirgends wie ein Fehler aus,
sondern wie eine Spur ohne Signal.

Regel: **Ein gemeinsamer Kern, der mehrere Spuren bedient, muss die Sperrzeile in
JEDEM Modus drucken, den ein Aufrufer parst** — auch in `--vorschau`, auch wenn
die Sperrenkette danach nur im Live-Zweig gebraucht wird. Muster:

```python
elif modus == "vorschau":
    gruende = sperren_live(w, s, spur_name)
    print("Live waere gesperrt durch: " + ("; ".join(gruende) if gruende else "nichts"))
```

Nachweis vor dem Commit, je Buch-Spur eine Zeile:

```
for s in moondev_listingarb moondev_topmovers trendwende_btc liq_wand iv_wand; do
  echo -n "$s: "
  MAXHIRN_ROUTINE=1 python $s/handeln.py --vorschau 2>&1 | grep -m1 "gesperrt durch"
done
```

Zweiter Teil derselben Pruefung: nennt die Zeile **mehrere** Gruende, ist die
Auto-Freigabe ebenfalls still — `nur_fenster_fehlt` verlangt genau einen, und der
muss „Freigabefenster" heissen. Ein Guthaben-Grund daneben ist RICHTIG (die Order
waere abgelehnt) und darf nicht wegoptimiert werden; der Bericht nennt ihn als
das, was Max entscheiden muss.

### Die Werkzeug-Schicht: „keine Sperrzeile" kann auch „keine Ausgabe" heissen

Ein spurenuebergreifendes Werkzeug, das jede Spur als Kindprozess aufruft, kann
an derselben Stelle scheitern wie der Kern — nur eine Ebene tiefer. Dort, wo der
Kern die Zeile nicht druckt, liefert ein **falscher Interpreter** gar keine
Ausgabe: der Aufruf bricht mit `ModuleNotFoundError` ab, und das Werkzeug meldet
das als „keine Sperrzeile". Beides sieht gleich aus und hat verschiedene Ursachen.

Gemessen: neun Spuren ohne Zeile, verteilt auf genau drei Ursachen —

| Ursache | Befund | Ort des Fixes |
|---|---|---|
| `if g: print(...)` in der Spur | Zeile fehlt, OBWOHL die Spur sie im Code hat; `nur_fenster_fehlt` liest `None` | Spur: immer drucken, leere Liste als `nichts` |
| `--vorschau`-Zweig kehrt vor der Sperrenabfrage zurueck | Zeile fehlt im Code | Spur: Zeile in den Vorschau-Zweig |
| Kindprozess mit fest verdrahtetem Interpreter | Lauf stuerzt ab, es kam nie eine Zeile | **Werkzeug**: je Spur ihr eigener venv |

Die dritte Ursache ist die teuerste, weil sie sich als „diese Spur ist blind"
liest statt als Werkzeugfehler. Ein Werkzeug, das Spuren startet, waehlt den
Interpreter aus derselben Quelle wie der Dauerlauf (Reihenfolge: die Spur
selbst, dann eine Nachbarspur, dann der Haus-venv) — Spuren mit eigenem venv
(Nautilus-Arme: `nautilus_trader` liegt nur dort) brechen sonst ab.

**Die Messung kommt VOR dem Umbau.** Erst das Werkzeug ueber die ganze Flotte
laufen lassen und die Ausgabe als Liste lesen: welche Spuren melden
`keine Sperrzeile`, welche melden `nichts`, welche nennen genau einen Grund. Die
Zeile „Keine Spur haengt allein am Fenster" ist die eigentliche Erkenntnis — sie
sagt, dass die Auto-Freigabe NICHT der Hebel ist. Der Hebel sind dann die zwei
Schalter: setzen die Spuren `handel_erlaubt` **und** `freigabe.erfuellt`, bleibt
ueberall nur das Fenster uebrig, und die Auto-Freigabe macht den Rest. Wer
stattdessen an der Auto-Freigabe selbst dreht, baut an der falschen Stelle.

Gegenprobe ist nicht „Zeile da", sondern die **Wirkung**: nach dem Fix muss eine
mit Haaken versorgte Spur „kein offenes Freigabefenster" als EINZIGEN Grund
nennen — dann weiss man auch, dass der Dauerlauf dort anfragt.

Merksatz: **eine Sperre, die niemand ausspricht, ist keine — und ein Werkzeug,
das abstuerzt, sagt auch nichts.**

## 7. Eine Waehrung je BUCH — die Quote kommt aus der API, nicht aus dem Code

Eine Spot-Spur, die auf EUR festgelegt war (Watchlist in EUR, Tor gegen `ZEUR`),
kann Kapital in anderen Quotewaehrungen desselben Kontos nicht erreichen.
Generalisiert wird in DREI Teilen, und alle drei gehoeren dazu:

1. **Die Quote JE PAAR aus der Boersen-API** (`AssetPairs`-Feld `quote`,
   Rueckfall `wsname` "BASIS/QUOTE"). Kein Uebersetzungsschluessel im Code — der
   waere die naechste feste Annahme. Ein unbekanntes Paar ist ein FEHLER
   (`QuoteUnbekannt`) und faellt als Kandidat raus, statt auf EUR
   zurueckzufallen: wer die Quote raet, handelt im falschen Markt.
2. **Das Guthaben-Tor in der Waehrung des Paares.** Die Quote eines Paares ist
   NICHT immer der Name des Postens im Kontostand: an 1455 Kraken-Paaren
   gemessen traegt Fiat dort ein "Z" (`ZEUR`, `ZCHF`), Stablecoins nicht
   (`EURC`, `USDC`). Also nicht uebersetzen, sondern gegen den ABGERUFENEN
   Kontostand aufloesen — und in EINEM Aufruf alle Waehrungen holen, weil zwei
   Aufrufe zwei Staende liefern koennen.
3. **Ein Buch fuehrt EINE Waehrung.** Einsatz, Erloes, Ruecklauf und die
   Drawdown-Ratsche summieren Betraege; eine Summe aus EUR und USDC ist keine
   Zahl. Steht das Buch, gilt seine Waehrung; ist es leer, entscheidet ein
   Vorrang aus der Konfiguration. Wer mischen will, braucht zuerst einen
   Umrechnungskurs je Position — das ist ein eigener Bau.

Der Vorrang darf NICHT das Guthaben befragen, wenn der Lauf Papier ist: ein
**Papierlauf haengt nie am Kontostand**. Sonst stellt ein Netzausfall oder ein
fehlender Schluessel ihn still, und in der Rangliste sieht das aus wie "kein
Signal". Muster `ziel_waehrung(z, w, lage, live)`: Buch schlaegt Vorrang, live
nimmt die gedeckte Waehrung, Papier nimmt die Konfiguration. Und die Geldsperre
bindet nur, wenn die Lage wirklich gelesen wurde
(`if waehrung in lage and lage[waehrung][0] < eur`).

Zwei Nebenwirkungen, die man beim Umbau mitnimmt:

- **Dasselbe Instrument in zwei Waehrungen ist EIN Instrument.** `XXBTZEUR`
  (Basis `XXBT`) und `XBTEURC` (Basis `XBT`) sind beide BTC; die Basis kommt aus
  `wsname`, weil nur dort normalisiert steht. Sonst steht dasselbe Instrument
  zweimal im Buch, und die Abklingzeit nach einem Stop greift nur in einer
  Waehrung — ein Stop in `SOLEUR` muss auch `SOLUSDC` sperren.
- **Der Guthaben-Grund bleibt EINER, auch wenn drei Waehrungen zu duenn sind.**
  `nur_fenster_fehlt` verlangt genau einen Grund und der darf das Wort
  "Freigabefenster" nicht tragen (Abschnitt 4). Drei Waehrungen duerfen deshalb
  nicht drei Gruende ergeben; der Grund nennt alle Staende in einer Zeile.

Der Feldname der Betraege bleibt der alte (`eur`), weil die Auswertungen ihn
lesen; die Waehrung steht zusaetzlich an der Position und im Journal hinter dem
Grund (`score 65.0 | USDC`). **Und die LESER ziehen mit**: Tagesbericht und
Kontofenster zeigten die Waehrung fest als EUR — ein Bericht haette eine
USDC-Position als EUR ausgewiesen, das Fenster "unter 60" gewarnt, waehrend die
Spur in USDC haette handeln koennen. Eine generalisierte Spur braucht eine
generalisierte Anzeige, sonst ist die Zahl richtig und ihre Einheit falsch.

Nachweis vor dem Commit: Scan ueber die neue Watchlist ohne Fehler, `--vorschau`
nennt die Waehrung je Vorschlag und das Guthaben JE Waehrung, und der Papierlauf
laeuft mit leerer `lage` (Test: `lage={}` kauft trotzdem).

**Vor jedem Umtausch erst messen, ob er sich lohnt** (Werkzeug
`kraken/quoten_vergleich.py`). Eine andere Quotewaehrung ist kein Marktplatz,
sondern eine Waehrung; sie lohnt nur, wenn (1) sie ein Instrument erschliesst
oder (2) ihr Markt enger ist. Beides wird gemessen:

1. **Deckung.** Gibt es ein Instrument, das NUR in der anderen Quote
   erreichbar ist? Gemessen 30.09.2026: keines von 17 — alle haben ein
   EUR-Paar, EURC ist Quote auf 3 Paaren (XBT/ETH/SOL, alle auch in EUR).
   Erschliesst der Umtausch kein Instrument, faellt Grund (1) weg.
2. **Spread.** Ein Rundlauf zahlt rund EINEN Spread; der Umtausch kostet
   einmalig die Taker-Gebuehr (60 bp). Gemessen 30.09.2026: die USDC-Paare
   sind im Mittel 6,6 bp WEITER als die EUR-Paare (EURC 3,7 bp) — es gibt
   keinen Break-even, der Umtausch kostet nur.

Ein EINZELNER Spread-Abruf traegt keine Empfehlung: bei duennen Buechern
schwankte dasselbe Paar zwischen 0,7 und 4,8 bp (LINK/EUR) und zwischen 23,5
und 55,0 bp (ALGO/USDC), Minuten auseinander. Median aus mehreren Abrufen, und
je Instrument genau EIN Paar pro Waehrung (sonst steht XBT zweimal in der
Tabelle, einmal EUR, einmal EURC).

Die Erweiterung bleibt trotzdem stehen: sie ist eine **Versicherung**, keine
Ertragsquelle. Liegt das Guthaben in einer anderen Waehrung, handelt die Spur
ohne Umtausch; laege es nur in der einen und die waere leer, muesste sie erst
tauschen — im laufenden Zyklus unmoeglich.

## 8. Die Einheit einer Zahl kommt aus dem BUCH — und die Zuordnung hat EINE Lesestelle

Seit eine Spot-Spur in mehreren Quotewaehrungen handeln kann (Abschnitt 7), ist die
Waehrung keine Eigenschaft des SPURNAMENS mehr, sondern des BUCHS. Eine feste
Tabelle `spur -> Einheit` ist nur noch der Rueckfall. Wer sie direkt liest,
rechnet still die falsche Einheit.

Belegt: ein Kennzahlen-Werkzeug las die Tabelle direkt und wies die Betraege einer
Spur als EUR aus, waehrend der Tagesbericht fuer dieselben Zahlen die Waehrung aus
dem Buch holte (USDC). Dieselbe Zahl, zwei Einheiten — und keine der beiden
Ansichten sah kaputt aus.

Regeln:

- **Genau EINE Funktion loest die Einheit auf** (`einheit_fuer(spur, z=None)`),
  sie liest den Zustand der aktuellen Risikostufe (`zustand.mittel.json` usw.)
  und nimmt aus dem Buch, was dort steht. Jeder andere Leser (Bericht, Kennzahlen,
  Kontofenster) RUFT sie auf, statt die Tabelle oder den Rueckfall nachzubauen —
  eine zweite Fassung derselben Regel laeuft frueher oder spaeter auseinander.
- **Ein Altbestand ohne Feld ist EUR, nicht „unbekannt".** Positionen aus der Zeit
  vor der Erweiterung trugen kein Waehrungsfeld; damals war EUR die einzige
  Waehrung der Spur. Ein „unbekannt" macht alte Buecher unlesbar und sieht wie
  ein Datenfehler aus.
- **Ein Delegieren statt Kopieren gilt auch fuer den Leser in der Anzeige:** die
  Lage-Funktion ruft die eine Funktion auf, statt dieselbe Rueckfall-Regel noch
  einmal zu schreiben (sonst faellt bei der naechsten Waehrung nur eine der
  beiden Stellen mit).

Testmuster, zwei Formen — beide gehoeren dazu:

1. **Die Regel als Verhalten:** Position mit Waehrung -> diese; Position ohne
   Feld -> EUR; leeres/fehlendes Buch -> Rueckfall. Dazu je ein Fall fuer die
   Stufe (Suffix am Zustandspfad), weil die Aufloesung den Stufenstand liest.
2. **Ein Quelltext-Waechter gegen den zweiten Leser:** den Spurenbaum ablaufen
   (`tests/`, `.venv/`, `daten/`, `__pycache__/` ueberspringen) und verlangen,
   dass der direkte Tabellenzugriff (`"EINHEIT.get(spur"`) genau EINMAL im Baum
   vorkommt — ausserhalb des definierenden Moduls. Der erste Test haette den
   Fehler nicht gefunden (die Tabelle selbst war richtig), erst der zweite.

Merksatz: **eine richtige Zahl mit falscher Einheit ist eine falsche Zahl** — und
wer die Einheit an zwei Stellen bestimmt, hat zwei Antworten.

## 9. Bestand aufnehmen: FREI ist nicht der Kontostand

Vor jeder Antwort auf „kann da gehandelt werden" / „ist dort Geld" wird der
Bestand GEMESSEN, je Boerse in DREI Zahlen: **total / gebunden / frei.** Ein
Kontostand allein beantwortet die Frage nicht — die Tore lesen das FREIE
Guthaben, und das ist bei besicherten Konten ein Bruchteil.

| Groesse | OKX | Kraken |
|---|---|---|
| alles | `/api/v5/account/balance` (signiert), `totalEq` | `BalanceEx`, Summe je Waehrung |
| in Margin gebunden | `isoEq` (Konto) bzw. `isoEq` je Posten | `OpenPositions` (eigener Aufruf) |
| frei | `availBal` je Waehrung in `details[]` | `balance − hold_trade` je Waehrung |

- **`availBal ≈ 0` heisst GEBUNDEN, nicht „weg":** der Posten steht in einer
  Position oder hinter einem boersenseitigen Stop. Auf demselben Konto liegen
  Krypto-Bestaende mit `availBal` = voll und andere mit 0 — nur die ersten sind
  einsetzbar.
- **Eine Bequemlichkeitsfunktion fuer EINE Waehrung ist keine Auskunft.**
  `okx.guthaben_usdt()` meldet 0.0, waehrend das Konto 542 USDC traegt — USDT ist
  dort schlicht nicht die Waehrung. Wer daraus „kein Geld" schliesst, hat die
  falsche Zeile gelesen; den Bestand immer ueber die Balance-Antwort holen.
- **`BalanceEx` traegt NUR `balance` und `hold_trade`.** Es gibt dort kein Feld
  `available`; ein Parser, der eines annimmt, druckt fuer JEDE Waehrung 0.0 und
  die Ausgabe liest sich wie „alles gebunden". Frei = `balance − hold_trade`
  (`hold_trade` = in Orders reserviert).
- **Margin-Positionen sind ein ZWEITER Ort** (`OpenPositions`) und stehen NICHT
  in der Guthabenliste. Eine Antwort, die nur das Guthaben liest, verliert sie —
  und eine Position, die mit demselben Guthaben besichert ist, erklaert einen
  Teil des Unterschieds zwischen total und frei.

### Fallen beim Zaehlen der handelbaren Paare

- **`okx.alle_paare()` liefert eine LISTE VON TUPLEN** `(instId, volumen)`, keine
  Dicts — `.get()` auf einem Element bricht mit `'tuple' object has no attribute
  'get'` ab. Das Instrument ist `p[0]`.
- **Kraken-Paarnamen tragen das „Z" auf Fiat:** ETH/EUR ist `XETHZEUR` (nicht
  `XETHEUR` → `EQuery:Unknown asset pair`), ebenso `XXBTZEUR`, `XXLMZEUR`. Die
  Schreibweise kommt aus `AssetPairs` (`wsname`), nicht aus dem Muenzenamen.
- **Ein tokenisiertes Produkt hat kein Krypto-Paar** (`XPEV.EQ`, `LAPTOP`,
  `YOM` → `Unknown asset pair`). Das ist strukturell und kein Namensfehler;
  solche Posten gehoeren als „nicht handelbar" in den Bericht, nicht in die
  Paarsuche.
- Die Zahl der gelisteten Paare ist eine LISTE, keine Aussage: 1.455 Paare auf
  Kraken sind online, aber die Frage ist, welches davon die freie Waehrung des
  Kontos bedient. Paare zaehlen nur als Beleg fuer „es gibt einen Markt".

### Der schnelle Weg durch die Flotte

- **Uebersicht:** `spuren_stand.py` — eine Tabelle ueber alle Spuren (erlaubt,
  Herzschlag, Fenster, freier Orderweg, Alter des Buchs).
- **Grund je Spur:** aus dem Spurordner `MAXHIRN_ROUTINE=1 <venv>/python
  handeln.py --vorschau` unter `timeout 90`. Das ist die belastbare Quelle; die
  Zeile „Live waere gesperrt durch:" nennt Boerse, Waehrung und Sollwert.
- **`sperrgruende.py` ueber die ganze Flotte laeuft NICHT in einen Tool-Aufruf**
  (41 Spuren, ueber 180 s). Nur benutzen, wenn Minuten zur Verfuegung stehen -
  sonst die Einzelabfrage je Spur.

### Form der Antwort

Total je Boerse → davon gebunden → frei → der Schwellwert des Tores → **eine**
Empfehlung. Der Engpass ist fast nie das fehlende Geld, sondern die Aufteilung:
gebundene Stablecoins im Vergleich zu ungenutzten Krypto-Altbestaenden, die keine
Spur anfasst. Diese Posten sind der Hebel, und ob sie verkauft werden sollen, ist
eine Entscheidung von Max — nicht stillschweigend umschichten.

## 10. Umschichten: was verkaufbar ist — und der Zeuge nach dem Verkauf

Ein Auftrag „umschichten" heisst: ungenutzte Posten in die Waehrung bringen, die
das Tor liest. Sechs Schritte, in dieser Reihenfolge:

1. **Bestand messen** (Abschnitt 9), frei von gebunden trennen.
2. **Posten ausschliessen, die eine Spur haelt.** Der Kontostand ist kein freies
   Kapital: gegen die Buecher der Spuren halten — auch gegen Arme, die dasselbe
   Konto mitbenutzen (auf Kraken hielten `kraken` und `mosaic` gleichzeitig
   Posten desselben Kontos). Was eine Spur fuehrt, wird nicht verkauft.
3. **Je Kandidat drei Fragen an `AssetPairs`:** gibt es ein Paar (nach `base`
   filtern, `status=online`), ist die Menge >= `ordermin`, ist der Wert >=
   `costmin` (Kraken 0,45).
4. **`validate`-Lauf zuerst** (`markt_verkauf(paar, menge, echt=False)`): kostet
   nichts und sagt vorher, ob die Boerse die Order annimmt.
5. **Echt verkaufen.**
6. **Gegenprobe:** `--vorschau` erneut — der Geldgrund muss aus der Sperrliste
   fallen. Bleibt er stehen, war die Umschichtung zu klein.

7. **Die Wirkung am KONTO nachmessen, nicht nur an der eigenen Vorschau.**
   `--vorschau` zeigt den eigenen Sperrstand, nicht den Kontostand. Ob das Geld
   noch da ist, sagen Abschnitt 9 (Bestand) und das Journal der Spur, die
   zugriff - siehe "Wer zuerst liest, nimmt es".

### Vier Gruende, warum ein Posten nicht verkaufbar ist

1. **Unter dem Ordermin.** Eine Mengenschwelle, kein Rechteproblem — die
   Fehlermeldung der Boerse liest sich aber wie eines: `PEPEEUR` verlangt
   1.500.000 PEPE, im Konto lagen 409.009,94; `ONDOEUR` verlangt 15, es lagen
   10,74331. Solche Posten bleiben liegen, bis mehr zusammenkommt; sie gehoeren
   als „unter Ordermin" in den Bericht, nicht in einen zweiten Versuch.
2. **Gestakte Form ohne eigenes Paar.** Der PUNKT im Namen ist das Kennzeichen
   (`ADA.S`, `ATOM21.S`, `HYPE.B`); `XPEV.EQ` ist dieselbe Sorte. Kraken fuehrt
   kein Paar mit `base=ADA.S` — `AssetPairs` liefert dafuer eine LEERE Liste.
   Der Weg ist Unstaking, nicht eine Order. Eine leere Paarliste ist das
   Merkmal, nicht ein Namensfehler.
3. **Gebunden statt frei** (`availBal` bzw. `balance − hold_trade`, Abschnitt 9).

4. **Compliance-Sperre des Kontos.** Das Instrument ist gelistet, das Paar
   existiert, die Menge passt - und die Boerse lehnt trotzdem ab, weil die
   Region des Kontos es ausschliesst (OKX `51155` bei den gestakten Formen
   `BETH`/`OKSOL`, die dort nur ein USDT-Paar haben und auch das nicht handeln
   duerfen). Erkennbar NUR am Orderweg: der Instrumentenabruf listet sie als
   handelbar. Siehe `references/okx-fehlermeldungen.md`, Abschnitt 10.

### Der Kontostand ist der Zeuge, nicht die Rueckgabe

`kraken.markt_verkauf(paar, menge, echt=True)` gibt die ROHE Kraken-Antwort
zurueck, nicht das `{result: {txid: [...]}}`-Dict, das `_roh_privat` liefert. Ein
`r.get('txid')` darauf wirft `'str' object has no attribute 'get'` — und zwar
NACH dem Fuellen: fuenf Verkaeufe waren durch, der Aufrufer meldete fuenf
Fehlschlaege. Wer daraufhin erneut verkauft, verkauft zweimal.

Regel: **nach einem Verkauf nie der Rueckgabe glauben.** `kontostaende()` und
`ClosedOrders` sind die Zeugen; im Zweifel BEIDE lesen, bevor ein zweiter
Versuch laeuft. Dieselbe Disziplin wie beim Orderweg: die Antwort ist eine
Behauptung, der Kontostand ein Befund.

### Wer zuerst liest, nimmt es

Ein freigemachtes Guthaben ist keine Zuweisung. Es gibt kein Reservierungssystem:
jede Spur liest den Kontostand in ihrem eigenen Zyklus, und **die erste, die ihn
liest, nimmt ihn.** Gemessen: nach dem Freimachen von 144,70 USDC kaufte der
live laufende `scanner` (Fenster offen) im selben Zyklus zwei Positionen fuer
143,92 USDC; die Zielspur hatte danach 0,00 frei.

Drei Regeln daraus:

1. **Vor dem Umschichten wissen, WER gerade scharf ist und ein offenes Fenster
   hat.** `spuren_stand.py` zeigt "Fenster" und "frei" je Spur; wer dort live mit
   offenem Fenster steht, greift in der naechsten Viertelstunde zu. Wer Guthaben
   fuer Spur A freimacht, waehrend Spur B scharf ist, bezahlt B.
2. **Ein Guthaben-Tor ist die LETZTE Sperre vor dem Freigabefenster.** Faellt es
   weg und bleibt genau EIN Grund ("Freigabefenster nicht offen"), oeffnet
   `AUTO_FREIGABE` das Fenster selbst - das Auffuellen eines Kontos ist damit
   mittelbar ein Scharfschalten. Guthaben und Erlaubnis sind zwei Schalter, aber
   nur einer davon wird beim Umschichten umgelegt.
3. **Umgekehrt schuetzt ein ZWEITER Grund.** Kommt nach dem Umschichten ein
   weiterer Grund dazu (das Guthaben ist inzwischen anderswo gebunden), verlangt
   `nur_fenster_fehlt` GENAU EINEN und oeffnet gar kein Fenster - die Zielspur
   handelt dann nicht, obwohl sie scharf ist. Das ist kein Fehler, sondern die
   Folge davon, dass das Geld nicht mehr bei ihr liegt.

Merksatz: **der eigene Erfolg ist die Verkaufssumme, nicht die Wirkung.** Die
Wirkung steht am Konto und im Journal der Spur, die zugriff.

## 11. Grenzen HERABSETZEN: halbieren, fehlende Live-Grenzen, latente Deckel

Ein Auftrag „Einsatz runter" beruehrt je Spur andere Felder. Bevor geschrieben
wird, wird der IST-Zustand je Spur als Feldliste gemessen und der Altwert gegen
den erwarteten geprueft — ein Anker, der nicht trifft, ist ein stilles Nichts.
`spuren_stand.py` zeigt Schalter und Fenster, aber NICHT, woher eine Live-Grenze
kommt; dafuer die Felder selbst lesen.

- **Halbieren mit Vermerk, Papier unveraendert.** Live-Grenzen
  (`live_max_*`, `live_einsatz_*`) werden halbiert, die Papierwerte bleiben.
  Jede Aenderung traegt ein datiertes `_vermerk`-Feld mit Auftrag und Grund
  (Gebuehrenstruktur, fehlender Excess) — die naechste Sitzung liest daraus,
  WARUM die Zahl kleiner ist als bei der Nachbarspur.
- **Eine Spur OHNE `live_max_*` handelt live mit den PAPIERwerten.** Ein
  fehlendes Feld ist nicht „keine Grenze konfiguriert", sondern Papier-Sizing
  in echtem Geld. Vor jedem Live-Status die EXISTENZ der Felder pruefen, nicht
  ihren Wert.
- **Ein Deckel weit ueber seinem eigenen Vermerk ist eine Falle.** Ein Wert, der
  nie bindet (90000 dort, wo der `_max_pro_trade`-Vermerk 130 sagt), ist
  unsichtbar, bis ein kuenftiger Aufrufer die Sizing aus dem Deckel ableitet.
  Beim Anfassen der Grenzen den Vermerk gegen den Wert lesen.
- **Die Kette konsistent halten: je Trade → Plaetze → Gesamtdeckel → Guthaben**
  (Abschnitt 3). Ein halbiertes Je-Trade-Limit laesst die Plaetze binden — das
  ist die beabsichtigte Bremse und gehoert in den Vermerk, nicht in eine Zahl,
  die „nicht passt".
- **Abgeleitete Risikofelder nicht mitziehen.** `risiko_je_position_eur`
  beschreibt das HOECHSTRISIKO der ALTNORM (50 x 12 %); die Ratsche leitet
  daraus die Halbierungsschwelle. Wird das Je-Trade-Limit halbiert und das
  Risikofeld mitgezogen, verschiebt sich die Schwelle selbst — und die alte
  Positionsklasse verliert ihren Schutz. Bewusst stehen lassen und im Vermerk
  begruenden.
- **Nach dem Setzen nachrechnen:** `pruefe_ratschen.py` (Schwellen herleitbar,
  1.0x?) und je scharfer Spur `MAXHIRN_ROUTINE=1 <spur>/handeln.py --vorschau`
  fuer die Sperrzeile. Die Vorschau braucht Netz und laeuft in Timeouts — je
  Spur einzeln, nicht ueber die Flotte in einem Aufruf.

## 12. Die Kapitalkurve STICHTEN, wenn ein Alt-Peak den Kill bindet

Der Kill misst `ruecklauf = Hoechststand der kumulierten Kurve − aktueller
Stand` ueber ALLE Journalrunden. Ein aufgeblaehter Alt-Peak —
Handpositions-Buchungen mit margin=NOMINAL statt echter Margin, Phantomzeilen —
haelt den Kill ueber Wochen gebunden, obwohl das heutige Buch sauber ist.
Gemessen: Peak 690 USD aus Handpositions-Buchungen, der Kill feuerte und
schloss drei live GEWINNER.

Zwei Wurzelmassnahmen, keine eine:

1. **Die Zeilen korrigieren** (Werkzeug `journal_korrektur_xperp.py`,
   Trockenlauf zuerst). Faellt es auf „0 Zeilen betroffen", sind die
   Phantomzeilen schon weg — dann bleibt nur (2).
2. **Der Kurve einen Stichtag geben.** EIN Feld in der `wachen.json`
   (`kapitalkurve_ab`, ISO-Datum), gelesen in `lage()`: Runden VOR dem Stichtag
   zaehlen weiter fuer Statistik und Erwartungswert, die Kurve
   (Hoechststand/Ruecklauf/Kill) beginnt am Stichtag. So bleibt die Statistik
   ehrlich und der Kill misst das heutige Buch.

Den Deckel anzuheben (`kill_switch_gesamt_usd`) daempft nur — der Peak bleibt,
der naechste Ruecklauf feuerte erneut. **Ein Kurven-Reset ist eine Entscheidung
von Max, keine Hygiene:** die gemessenen Zahlen (Peak alt, Ruecklauf alt,
Deckel, Stand nach dem Stichtag) benennen, dann schalten.

Stehen inzwischen ZWEI Filter an derselben Stelle (z. B. ein Hand-Ergebnis-
Filter aus einer frueheren Session und der Stichtag), werden sie VERKETTET,
nicht gegeneinander ersetzt: fremden Filter behalten, den Stichtag als eigenen
Schritt DANACH setzen. Ein Filter, der den anderen verdraengt, verliert die
Wirkung des alten — und genau das faellt erst auf, wenn jemand den Kill wieder
ohne Handschutz braucht. Reihenfolge im Test festhalten: je Filter eine Zeile,
damit ein Ausfall benennt, WELCHER Schritt fehlt.

Testfalle: ein Test, der die echte `wachen.json` kopiert, **erbt den echten
Stichtag** und faelscht den Fall „kein Feld". Jeden Fall das Feld AUSDRUECKLICH
setzen (`None` = alle Runden) — eine Konfiguration, um die es geht, wird vom
Fall gesetzt, nicht geerbt. **Dieselbe Falle gilt fuer JEDES neue Feld der
Wachen:** ein Test, der die echte Datei als Vorlage nimmt, erbt jede spaetere
Erweiterung mit und prueft dann die Konfiguration, nicht die Regel. Gegenprobe:
neues Feld in den Wachen setzen und den Alt-Test rot werden sehen.

Nachweis: `lage()` vor/nach (Hoechststand, Ruecklauf, Kill-Flag) messen und die
Gegenprobe fahren — wird der Code-Pfad zurueckgenommen, muessen die
Stichtag-Tests rot werden. Die Rundenzahl der Statistik bleibt in ALLEN Faellen
gleich.

Verwandt: `references/tor-kalibrierung.md` (Schwellen und Kosten),
`references/freigabefenster-und-abbruchzeit.md` (Fenster gegen Abbruchzeit),
`references/live-schalten.md` (der erste echte Geldpfad).

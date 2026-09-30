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

Merksatz: **eine Sperre, die niemand ausspricht, ist keine.**

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

Verwandt: `references/tor-kalibrierung.md` (Schwellen und Kosten),
`references/freigabefenster-und-abbruchzeit.md` (Fenster gegen Abbruchzeit),
`references/live-schalten.md` (der erste echte Geldpfad).

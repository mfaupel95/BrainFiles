# Ein Papierbuch auf einen fremden Signal-Feed setzen

Fuer Spuren, die nicht selbst handeln, sondern nachbuchen, was ein fremder Feed
tut (Copy-Trading, Spiegelung, Signalstudie). Muster: `Agenten/Handel/spiegel/`
(OnchainOS-Feed) - Vorlage fuer jede weitere Feed-Anbindung.

## Aufbau: zwei Dateien, eine Richtung

- `lesen.py` - der **einzige** Zugang nach draussen. Ruft nur lesende
  Unterbefehle und verweigert Schreibbefehle, **bevor** ein Prozess startet:
  `SCHREIBBEFEHLE = ("swap", "cross-chain", "strategy", "payment", "wallet", …)`
  plus ein Abbruch in `ruf(args)`, wenn `args[0]` darin steht. Der Waechter
  gehoert in den Leser, nicht in den Aufrufer - dort gilt er fuer jeden Nutzer.
- `<spur>.py` - das Buch. Importiert `lesen` und ruft das CLI **nie selbst**
  (Test: der Modulquelltext enthaelt weder `subprocess` noch den CLI-Namen).
  Beim Import gegenpruefen, dass `lesen.SCHREIBBEFEHLE` existiert; fehlt der
  Waechter, startet die Spur nicht.

## Was der Feed liefern muss

| Zweck | Abfrage | Anmerkung |
|---|---|---|
| Signale (wer handelt jetzt) | `tracker activities --tracker-type smart_money\|kol --chain X --trade-type 1` | Transaktionsebene; `tradeTime` (ms) ist der Zeitstempel des Vorbilds |
| Messung (wer ist gemessen gut) | `leaderboard list --chain X --time-frame 4 --sort-by 1..5` | 50 Eintraege je Kette: PnL, Trefferquote, Trades |
| Kurs fuer offene Eintraege | `market prices --tokens "501:addr,8453:addr"` | Stapelabfrage; Paare sind `chainIndex:adresse` |
| Tiefe und Kennzahlen je Token | `token price-info --address A --chain X` | liefert `liquidity`, `marketCap`, `holders`, `volume24H` - Grundlage der Kostenmessung |
| Betrugsmerkmale vor dem Kauf | `security token-scan --tokens "501:addr" --trade-direction buy` | liefert `action`/`riskLevel` plus ~25 `is*`-Merkmale |
| Echtzeit (spaeter) | `onchainos ws start --channel kol_smartmoney-tracker-activity` | Millisekunden statt Takt; eigener Ausbau |

Ketten zuerst abfragen (`leaderboard supported-chains`, `signal chains`) und in
`wachen.json` als Liste fuehren - eine Kette ohne Daten faellt dann auf, statt
still ein leeres Buch zu erzeugen. Parameter und Felder je Befehl stehen in den
OKX-Skills (`okx-dex-market`, `okx-agentic-wallet`); hier steht nur, was das
Buch braucht.

## Die Auswahlregel

**Verfolgt wird der Feed, nicht die Rangliste.** Nur die Gewinner einer
Rangliste nachzubuchen ist Zuchtauswahl nach dem Ergebnis (Survivorship); die
Ranglistenzahlen werden daneben geschrieben, damit die Bilanz spaeter zeigt, ob
sie die *Kopierbarkeit* vorhersagen. Beides getrennt halten: `--waehlen` baut die
Verfolgungsliste (und schreibt nur diese), der Zyklus bucht. Vorher abschaetzen,
wie viele Wallets der Feed liefert - und wie viele davon ueberhaupt in einer
Rangliste stehen; die Luecke dazwischen ist selbst ein Befund.

## Kosten zweimal rechnen

Ein Nachahmer kauft spaeter und teurer, verkauft billiger und zahlt zweimal
Gebuehr:

    kaufpreis = kurs * (1 + slippage)
    menge     = (einsatz - gebuehr) / kaufpreis
    erloes    = menge * kurs * (1 - slippage) * (1 - gebuehr)

Der wichtigste Test des Buches ist: **eine Kopie ohne Kursbewegung ergibt ein
Minus.** Ein Papierbuch mit glatten Kursen ist eine Wunschrechnung. Die Annahme
gehoert gemessen, nicht gesetzt: wie das geht (Buch-Effekt und Nachlauf
getrennt, als eigener Modus, Verteilung statt Mittelwert) steht in
`references/tor-kalibrierung.md`, Regel 8.

## Tore vor jeder Buchzeile

Signalalter (aus `tradeTime`, **nicht** aus der Abfragezeit), Marktkapita-
lisierungsband, Risikostufe aus dem Scan, Hoechstzahl Kopien je Token, keine
zweite Kopie derselben Wallet auf denselben Token, freie Plaetze, Zyklusdeckel.
Ein unbekannter Wert (fehlende Marktkapitalisierung) ist ein Ablehnungsgrund,
kein Platzhalter. Die billigen Tore (Alter, Band, Duplikat) gehoeren in EINE
Funktion (`_vorpruefung(kandidat, w, z) -> (schluessel, text)`), die Buch und
Zaehlung gemeinsam benutzen - eine zweite Fassung derselben Grenze laeuft
auseinander. Schluessel = gleichbleibender Name fuer die Zaehlung, Text = was
der Mensch liest.

## Tourenplan: Gruende ausgeben reicht nicht, sie muessen daneben liegen

Die Ausgabe einer Spur sieht niemand: der Dauerlauf faengt sie ein, filtert sie
nach Stichworten und protokolliert nur "ok". Ein Ablehnungsgrund, der nur
gedruckt wird, ist beim Auswerten weg - und im Journal sehen "Tor zu streng"
und "Buch voll" identisch aus (beide erzeugen keine neue Buchzeile). Deshalb
schreibt jede Spur mit Kandidatenstrom ein **Ablehnungsprotokoll daneben**:

- **Eigene Datei, nie im Journal.** Dessen Leser zaehlen Zeilen als Buchungen
  (`bilanz()` rechnet jede Nicht-`eroeffnen`-Zeile als Runde, `buchauswertung`
  je Aktion) - eine Ablehnung waere dort eine erfundene Runde.
- **Zwei Zeilenarten.** `art=zyklus` traegt je Zyklus und Grund eine Zeile mit
  `anzahl` (Lage ueber ALLE Kandidaten, billige Tore ohne einen einzigen Abruf,
  plus die Entscheidungen der wirklich bewerteten) und garantiert damit eine
  messbare Zeitreihe; `art=signal` traegt EINEN Kandidaten mit Kennung, aber nur
  fuer die, die bis zur teuren Pruefung gekommen sind. Hunderte Kandidaten je
  Zyklus einzeln zu protokollieren ist ein Protokoll, das niemand liest und das
  mit jedem Zyklus weiter waechst. Vorher messen, wie viele Kandidaten ein
  Zyklus ueberhaupt mitbringt: eine Wegwerfprobe zaehlt sie und ihre Verteilung
  ueber die Tore, ohne Netzabrufe.
- **Jeder Kandidat in GENAU EINEM Lage-Zaehler.** Reihenfolge: erst
  Zugehoerigkeit (verfolgt die Spur dieses Wallet ueberhaupt?), dann die
  billigen Tore, dann die teure Pruefung. Ohne diese Partition steht ein
  Kandidat in zwei Zaehlern (z. B. "Wallet nicht verfolgt" UND "kaufbar"), und
  die Kontrollzeile geht nicht auf.
- **Sperre je (Transaktion, Grund).** Ein Feed-Signal steht Stunden im Fenster -
  ohne diese Sperre traegt das Protokoll denselben Kandidaten in jedem Zyklus
  erneut ein und die Zaehlung ist ein Vielfaches der Wahrheit. Aendert sich der
  Grund, ist das eine neue Zeile. Die Sperre liest den SCHLUSS der Datei (die
  Datei ist die Wahrheit, nicht der Prozess).
- **Kontrollzeile im Leser.** `kaufbar = bewertet + nicht mehr erreicht`. Die
  Kapazitaets-Zaehler (Buch voll, Zyklusdeckel) zaehlen EREIGNISSE je Zyklus,
  nicht Kandidaten - sie gehoeren nicht in die Kandidatensumme. Geht die Zeile
  nicht auf, gehoert "Achtung" in die Ausgabe, nicht eine gerundete Zahl.
- **Nachweis in vier Teilen.** (1) Tests mit synthetischen Signalen fuer Schema,
  Sperre und Partition; (2) ein Test, dass ein billiges Tor keinen Abruf kostet;
  (3) der **erste echte Zyklus** von Hand gelesen - genau dort fiel die
  Schieflage auf, die kein synthetischer Test finden konnte; (4) byte-genauer
  Vergleich mit der Kopie ausser Haus, inklusive der neuen Datei.

## Durchsatz und Frische: die zwei Engstellen, die das Journal nicht zeigt

Beim ersten Auswerten von `spiegel` (14.09.2026) lagen beide Engstellen
ausserhalb der Tore — und beide waren aus dem Journal allein nicht zu erkennen:

- **1. Der Platz.** 706 Signale je Zyklus, 5 bis 58 davon kaufbar, und das Buch
  stand dauerhaft auf 20/20. Der Zyklus bricht beim ersten Platzmangel ab und
  zaehlt den Rest als "kaufbar, aber nicht mehr erreicht" — das liest sich wie
  ein zu strenges Tor und ist Kapazitaet. **Runden je Tag = Plaetze x Umschlaege
  je Platz und Tag** (hier rund 2). Wer Daten sammeln will, hebt die Kapazitaet:
  ein eigener Wert im Papier (`max_offen_papier`), angewendet von EINER Funktion,
  die am Schalter der Spur haengt (`handel_erlaubt`/`--live`), damit live
  automatisch das geprueffte Muster faehrt. Die Notbremse im selben Anteil
  mitziehen, sonst beendet sie die Messung selbst. Fuer die Freigabe-Frage
  ("50 Runden") ist das der Unterschied zwischen eineinhalb Tagen und einem
  halben — die Praezision waechst mit der Wurzel der Rundenzahl, der Aufwand
  linear mit den Plaetzen.
- **2. Die Verfolgungsliste.** Sie ist ein Fenster auf den Feed, kein Stammbuch:
  nach zwei Tagen fehlten 154 von 206 im Feed handelnden Wallets in der Liste,
  und zwei Drittel aller Signale fielen als "Wallet nicht verfolgt" aus. Die
  Liste gehoert in den Zyklus (Neubau bei Alter > `verfolgte_max_alter_stunden`),
  nicht in eine einmalige Handarbeit — und NUR in den schreibenden Lauf: der
  Aufbau schreibt die Datei direkt und kennt den Schreibschalter nicht.

Konsequenz fuer die Messung: **eine Kapazitaets-Aenderung ist keine
Strategie-Aenderung.** Tore, Stop, Ziel, Frist, Einsatz und Kosten bleiben
unangetastet, sonst ist das Buch danach nicht mehr mit dem Vorher vergleichbar.
Die Umfangszeile gehoert in JEDEN Zyklus gedruckt (ohne ein Filterwort des
Dauerlaufs — "Kill-Switch" faellt unter `kill` und wird Spam).

## Fallen

- **Quoten-Waehrungen sind je Kette verschieden** (`SOLANA`, `ETH`, `BSC`,
  `Base`). Einsatzgroessen aus dem Feed nicht kettenuebergreifend vergleichen -
  ein Tor darauf waere ein Filter, der nur scheinbar misst.
- **Von Hand gestartete Laeufe kippen den Herzschlag.** Ein Buch mit
  Herzschlag-Wache stellt beim naechsten Start alles flach, wenn es laenger
  nicht lief. Entweder Dauerbetrieb oder die Wache an die echte Taktung
  anpassen - nie abschalten.
- **Signale sind Momentaufnahmen.** Zwischen Feed und Kursabfrage liegen
  Sekunden, und der Kurs ist dann ein anderer. Das ist keine Ungenauigkeit,
  sondern der Kostenteil, den das Buch abbilden soll - nicht wegdefinieren.
- **Die Verfolgungsliste nicht versionieren, wenn sie ein Lauf schreibt.** Sie
  wechselt bei jedem `--waehlen`; im Verlauf ist das Rauschen, das die echten
  Aenderungen zudeckt. Regeln und Wachen gehoeren in den Verlauf, das Buch
  nicht.

## Nautilus: Strategie im Node statt Quote-Sammeln (15.09.2026)

`nautilus/trailing_stop_strategie.py` haengt die bestellte Ausstiegsform
(Stop realisiert max -20 % inkl. Kosten, Trailing ab +30 % Abstand 25 %,
Frist 168 h) als echte NautilusTrader-Strategy in den OKX-DEMO-Node - OHNE
Broker-Order (Schluessel read_only). Die Muster-Entscheidungen:

- **Positionen liegen AUSSERHALB der Engine** (zustand.json): der Node lebt
  nur ~30 s je Zyklus, der Zustand ueberlebt in der Datei. Die Strategie
  bekommt offene Positionen + frische Signale uebergeben und gibt
  veraenderte Listen (positionen, buchungen) zurueck - ein Tupel aus
  sammle_quoten(), kein Framework-Cache.
- **Einstiegs-Signale aus der KOPIER-Spur:** frische eroeffnen-Buchungen im
  kopier-Journal (neuer als der letzte eigene Zyklus) werden zu
  Proxy-Positionen in BTC-USDT-SWAP zum aktuellen Mid - misst die
  AUSSTIEGSFORM auf dem liquiden Instrument, kein Markt-Urteil ueber die
  Token. Kapazitaetsfaelle (max_offene_positionen) bleiben unregistriert
  und duerfen im naechsten Zyklus wieder Kandidat sein (Test!).
- **Herzschlag-Fallback:** OKX-Feed tot (0 Quotes oder Node-Exception),
  aber kopier frisch (letzter_lauf < ein Takt) -> Herzschlag ueber die
  Kopier-Daten (feed_quelle = fallback_kopier), Rueckgabe 0; nur
  Frist-Ausstiege werden dann zum letzten Kurs gerechnet (ohne Kurse ruhen
  Stop und Trailing). Ist AUCH kopier tot -> Rueckgabe 1. Die Spur stirbt
  nur noch, wenn der ganze Dauerlauf stirbt.
- **Journal-Spalten erweitern, nicht umbauen:** preis/menge/einsatz_usd/
  wert_usd kommen zu den zyklus-Spalten; Buchungszeilen tragen sie,
  zyklus-Zeilen lassen sie leer. buchauswertung filtert Zeilen ohne
  Einsatz/Wert von selbst raus - die alte Zyklus-Zeile bleibt eine
  Zyklus-Zeile.

## Ausstiegsform umstellen: Trailing statt Ziel (15.09.2026, spiegel+kopier)

Max-Order: "20 % Verlust max, gerissenen Stop sofort schliessen, nach oben
Trailing fuer 10x/100x". Die Muster-Antwort fuer JEDE Buch-Spur:

- **Kein festes Ziel mehr.** `ziel_pct` fliegt raus; die Position bekommt
  `trail_aktiv_ab_pct` (ab wann getrail wird) und `trail_abstand_pct` (wie
  viel unter dem Peak) als SCHNAPPSCHUSS beim Buchen plus `hoechster_kurs`,
  der je Zyklus fortgeschrieben wird (`_ausstiegsgrund()` als EINE Stelle).
- **Stop auf den REALISIERTEN Verlust kalibrieren, nicht auf den Preis.**
  "Max 20 % Verlust" heisst: am Stop inklusive Slippage und Gebuehr nicht
  unter -20 % des Einsatzes. stop_pct loest `(1-sp)*(1-slip)*(1-geb) = 0,80`
  auf (spiegel 17 % bei 3/1, kopier 15 % bei 5/1) - nicht den alten Wert
  stehen lassen und hoffen. Die Rechnung gehoert in wachen.json (_ausstieg).
- **Gerissener Stop = Markt-Semantik.** Schliessen zum BEOBACHTETEN Kurs
  (erster Print unter dem Stop), nie zum Stop-Preis. OKX-Form: Stop-Market,
  kein Stop-Limit; Trailing = OKX-Trailing-Stop (Trigger/Callback). Als
  Kommentar in wachen.json dokumentieren, Orderspezifikation beim Anbinden
  gegen die API pruefen.
- **Altbestand laeuft unter seinen gebuchten Regeln aus.** Positionen ohne
  die neuen Felder nehmen den alten Zweig (stop/ziel/frist) - das Buch bleibt
  mit dem Vorher vergleichbar, keine stillen Neu-Regeln fuer alte Kopien.
  Tests: kein Ziel-Exit bei +100 % (der 10x-Fall), Trail aktiv/nicht aktiv,
  Altbestand-Zweig, Journal-Kumul ueber Faelle (No-Cap-Check zuerst).

## Zweite Feed-Spur: kopier (Pump.fun, 14.09.2026)

`Agenten/Handel/kopier/` ist die zweite Anbindung nach diesem Muster - eine
REST-API statt CLI, Positions-Spiegel statt Transaktions-Stream. Die
Lektionen aus dem Neubau:

- **Waechter als (Host, Methode)-Pfad-Whitelist.** Gibt es kein CLI mit
  Unterbefehlen, sitzt der Schreibschutz in den erlaubten URL-Pfaden:
  `_ERLAUBT = {(host, "GET"): ("/pfad/", ...)}` plus eine POST-Ausnahme fuer
  den einen lesenden Batch-Endpunkt. `posixpath.normpath` NACH dem Parsing,
  sonst unterlaeuft `/erlaubt/../swap` die Praefix-Pruefung (Test deckte es
  auf). SCHREIBBEFEHLE bleibt als Tripwire-Wortliste bestehen, weil das Buch
  den Import abbricht, wenn sie fehlt.
- **Einlauf-Regel gegen Zuchtauswahl.** Diff-Feeds sehen beim ersten Kontakt
  das GANZE aktuelle Portfolio einer Quelle. Ohne Einlauf kopiert der erste
  Zyklus die kompletten Gewinner (Survivorship pur). Regel: Eine Wallet ohne
  Eintrag in `gesehen_*` wird im ersten Zyklus still uebernommen (gezaehlt
  als eigener Lage-Eintrag), nie gekauft.
- **Registrierung endgueltig, Kapazitaet die einzige Ausnahme.** Jede
  Entscheidung (Band, zu alt, Risiko, gekauft) wird fuer (Quelle, Token)
  registriert. Nur was an Buch voll / Zyklusdeckel / Bewertungsdeckel
  scheitert, bleibt unregistriert und darf im naechsten Zyklus wieder
  Kandidat sein. Sonst traegt das Protokoll denselben Kandidaten jeden
  Zyklus neu ein (Zaehlung = Vielfaches der Wahrheit) und jede Wiederholung
  kostet einen API-Abruf.
- **Ablehnungsgruende duerfen keine Filterwoerter des Dauerlaufs tragen**
  (verkauf, stop, KILL, gesperrt, ausstieg). Eine Risikostufe "gesperrt"
  kollidiert mit der Sperren-Zeile ("gesperrt durch ...") und geht nach
  Telegram. Heisst hier "blockiert". Der Test `test_nein_zeile_ohne_filterwort`
  haelt das fest.
- **`lauf("live")` laeuft nach der Verweigerung als Papierzyklus weiter**
  (Muster spiegel). Ein Test, der "live" aufruft, muss auf den Temp-Pfaden
  stehen - sonst entsteht ein ECHTER Lauf mit echtem Netz und echtes
  Q:\\Handel_Journal\\<spur> (am 14.09.2026 passiert: 1283 Positionen
  Einlauf + Spiegelung aus einem Unit-Test heraus).
- **Marktkap-/Kettenfilter vor dem teuren Abruf.** Das Leaderboard- und
  Portfolio-API liefert auch andere Ketten (EVM etc.) und Staub-Positionen
  mit. chainId-Filter und Marktkapitalisierung sind billige Tore OHNE Abruf;
  das Signalalter braucht einen trade-Abruf und gehoert deshalb zur teuren
  Pruefung (nach dem Band, vor dem Risiko-Check).
- **spiegelstand.gleich(): beidseitig fehlende Datei = gleich.** Eine neue
  Spur hat bis zur ersten Buchung kein Journal; fehlt die Datei auf beiden
  Seiten, ist das kein Fehlalarm. Einseitig fehlend bleibt Abweichung.

## Zweite Spur auf demselben Feed: Leser und Auswahlliste teilen

Eine zweite Buch-Spur auf demselben Feed (z. B. kopier + kopier1zu1 auf
derselben Pump.fun-Rangliste) darf den Feed nicht doppelt fragen und nicht
zwei Auswahlen fuehren, sonst misst sie eine andere Strategie:

- **`lesen.py` ist genau EIN Modul, kein zweiter Klon.** Der zweite Ordner
  legt den Pfad des ersten auf `sys.path` und macht `import lesen` — der
  Waechter, die Retry-Muster, die Feld-Normalisierung bleiben an einer
  Stelle. Ein Kopieren des Lesers waere zwei Waechter, die still
  auseinanderlaufen.
- **Die Auswahlliste (verfolgte.json) gehoert der Spur, die sie pflegt.**
  Die zweite Spur liest sie NUR (`w["verfolgte_aus_kopier"] = true`) und
  ruft NIE `--waehlen` selbst — sonst schreiben zwei Spuren dieselbe Datei
  im Zyklustakt und liefern sich einen Race, in dem eine der beiden ihre
  eigene Verfolgungsliste ueberschreibt. Fehlt die Datei, meldet die Spur
  "erst waehlen lassen" und endet, statt eine leere Liste zu erzeugen.
- **Die zweite Spur BEWEIST die andere Signalform, nicht die andere
  Vorauswahl.** Wer den Feed doppelt filtert (zweite Marktkap-Schwelle,
  zweite Kettenliste), misst nicht mehr die Wirkung der Signalform — dann
  gehoeren dieselben Tore in beide Spuren.

## Trade-Ereignis vs. Portfolio-Diff

Copy-Trade-Buecher haben zwei Signalquellen — welche gewaehlt wird,
entscheidet, wann der eigene Ausstieg trifft:

- **Portfolio-Diff** (Snapshot je Zyklus): das Buch sieht ein VERSCHWUNDENES
  Token frueherstens beim naechsten Snapshot — bei 15-Minuten-Takt bis zu
  15 min nach dem Verkauf des Vorbilds. Fuer viele Feeds das Einzige, was es
  gibt (Wallet-Endpunkt liefert nur Bestand), und mit Einlauf-Regel gegen
  Zuchtauswahl gut belegt.
- **Trade-Ereignisse** (typ=buy/sell aus /trades-Endpunkt): jeder VERKAUF
  des Vorbilds nach dem eigenen Einstieg schliesst die Kopie zum letzten
  beobachteten Kurs — sekundengenau statt zyklus-genau. Voraussetzung: die
  API hat einen Trade-History-Endpunkt und der Zyklus schafft die Abrufe
  im Rate-Limit (naechster Abschnitt).

Beide Formen als eigene Spur nebeneinander laufen zu lassen ist eine
Messung, keine Redundanz: der Unterschied im Ergebnis ist die Wirkung des
Ausstiegs-Timings, nicht des Signals selbst.

## Kosten je Zyklus rechnen, bevor Anfragen laufen

Ein Fremd-Feed mit Rate-Limit toleriert nicht jeden Zyklus:

- **Anfragen zaehlen, nicht schaetzen.** N Wallets × M Tokens je Wallet ×
  K Endpunkte = Anfragen je Zyklus; gegen das Rate-Limit halten (Pump.fun:
  ~2 Anfragen/s bevor 429). `max_trader_je_zyklus` und ein Tokens-Deckel
  je Wallet begrenzen die Kosten hart, bevor die API sie ablehnt.
- **Vor dem teuren Abruf filtern.** Positions-Listen tragen fremde Ketten
  (EVM-Adressen auf einem Solana-only-Feed) und Meta-Eintraege (`native`
  = SOL selbst, nicht handelbar) — diese Eintraege vor dem Abruf
  aussortieren (`m.startswith("0x")`, `m == "native"`), sonst kosten sie
  Rate-Limit und liefern 404. Nicht: 429 als Fehler abhaken. Der Fehler
  ist die eigene Zyklus-Rechnung.
- **Zwischen Anfragen atmen.** Ein `time.sleep(1.0)` zwischen den Requests
  einer Wallet macht aus 429-Salven ordentliche 200er — in einem
  15-Minuten-Zyklus sind Sekunden je Wallet kein Preis. Der Schlaf steht
  in der Sammel-Schleife, nicht im Leser: dort waere er unsichtbar und
  wuerde auch Abrufe drosseln, die nicht in einem Burst laufen.
- **Rate-Limit-Fehler brechen den Zyklus NICHT ab.** Betroffene
  (Wallet, Token) fallen still aus (Warnung + `continue`); beim naechsten
  Zyklus stehen sie wieder bereit. Ein 429-Fehler ist Kapazitaet, keine
  Kaputtheit.

## Endpunkte einer Web-App finden (ohne Doku und API-Key)

Fuer die Pump.fun-Anbindung war der alte API-Host tot (Cloudflare-DNS 1016)
und der Pfad stand nirgends dokumentiert. Der Weg, der funktioniert hat:

1. **Die Webseite selbst greppen statt raten.** `curl` auf die oeffentliche
   Seite liefert oft HTTP 200, auch wenn der alte API-Host 1016 wirft; im
   HTML stehen die API-Hosts als URLs (`grep -oE 'https?://[a-zA-Z0-9.-]+'`
   sortiert und gezaehlt).
2. **Next.js-Chunks laden und den API-Client lesen.** Alle
   `src=".../_next/static/chunks/..."`-URLs aus dem HTML ziehen, den
   `?dpl=`-Query abtrennen, Chunks laden und nach `new URL("/pfad",
   t.BASIS)`-Buildern greppen - die Pfade und die Basis-Hosts stehen
   kompakt in EINEM Modul (hier: PNL_LEADERBOARD auf `/pnl-leaderboard`,`)
   und im Server-Rendering liegt sonst nichts (das HTML enthaelt keine
   API-Pfade).
3. **Die Fehlermeldung des Servers ist Doku.** Probiert man einen
   Endpunkt falsch, nennt die Validation die zulaessigen Werte (`period
   must be one of: daily, weekly, monthly`) - das ist das Feld-Schema,
   nicht die Faelle nachraten.
4. **Feldnamen live pruefen, nie aus der Erinnerung schreiben.** Dieselbe
   API nennt ein Feld je Endpunkt verschieden geschrieben (trades/batch
   liefert `priceUSD`, der v2-Trades-Endpunkt `priceUsd`). Die
   Normalisierung deckt beide ab, aber nur der echte Abruf zeigt, welcher
   Endpunkt welchen Namen nutzt.
5. **Eine SPA (Vite/React) hat keine literalen `"/api/..."`-Strings.** Die
   Pfade sind Template-Literale aus einer Basis-Konstante
   (`${G}/claw/agents/login`, daneben `G="/api"`). Ein grep nach `"/api/`
   liefert dann nichts und es sieht aus wie „die App hat keine API" - das ist
   ein Suchfehler, kein Befund. Erst die Basis suchen, dann die Templates:
   ```
   grep -oE '[A-Za-z_$]{1,3}="/[a-z]*"' bundle.js            # Basis
   grep -oE '\$\{[A-Za-z]\}/[a-zA-Z0-9/_{}$.?=&-]+' bundle.js | sed 's/^[^}]*}//' | sort -u
   grep -oE '.{120}/claw/agents/login.{250}' bundle.js         # Aufrufstelle
   ```
   Die Aufrufstelle nennt die Feldnamen der Nutzlast (`{name, email, password}`)
   - abschreiben statt raten.
6. **HTTP 200 auf `/docs`, `/openapi.json` oder `/redoc` beweist keine Doku.**
   Eine SPA liefert fuer JEDE Route ihre index.html; Status und Groesse sehen
   wie ein Treffer aus. Antwort gegen das HTML der Seite halten (erste Bytes),
   nicht dem Statuscode glauben.
7. **Ein fehlender Endpunkt ist ein Befund, kein Fehler.** Steht im Bundle kein
   Pfad fuer eine Funktion (z. B. Passwort aendern), dann gibt es sie auf dieser
   Plattform nicht - das ist die gemessene Antwort. Dann den tragfaehigen Weg
   nehmen (neuen Zugang anlegen, neue Kennung in `.env` und `Zugaenge.md`
   nachtragen, Werte nie ausgeben) statt weiter zu suchen. **Und die Kennung
   gehoert aus der Antwort ins Werkzeug, nicht in die Ausgabe:** Fehlerantworten
   spiegeln gern die gesendete Nutzlast in einem Feld `input`/`detail` zurueck -
   ein Passwort, das so in ein Protokoll kam, ist verbrannt. Rohe Antworten nie
   protokollieren, nur Status und Feldnamen; der Anlege-Weg ist ein Skript, das
   Kennung und Passwort erzeugt, schreibt und NICHTS davon druckt.

## Ein Signal-Kanal-Screenshot ist kein Feed

Zeigt der Nutzer einen Signal-Kanal (VIP-Gruppe, Push-Nachricht) und fragt
"koennen wir das auch?", ist das **keine** Feed-Anbindung: es gibt keinen
lesenden Endpunkt, der die Signale und ihre Ergebnisse fuehrt. Was sichtbar ist,
ist die Gewinnkarte - die Verlustseite fehlt, und damit fehlt der Track Record
(Survivorship).

- **Nicht nachbauen, was nicht belegbar ist.** Kein Copytrading einer Blackbox,
  keine Uebernahme fremder Hebel (10x/20x) und keine fremden Zahlen als
  Massstab. Die Karte ist kein Benchmark.
- **Die ehrliche Antwort ist eine eigene Spur mit derselben FORM:** ein
  deterministisches Muster aus oeffentlichen Kurs-/Volumendaten (z. B. schnelle
  1h-Bewegung mit Volumen-Untergrenze), ausdruecklich OHNE Hebel, mit Stop und
  Ziel aus der eigenen Geometrie, Papier, Kosten eingerechnet. Fuer solche
  Signalmuster ist `spur_buch.py` das leichte Muster (gemeinsames Buch der
  Feed-Spuren) statt der komplette Spur-Neubau.
- **Instrument zuerst pruefen.** Karten zeigen gern Aktien-Perpetuals
  (`NVDAUSDT` und Verwandte); die sind nicht an jeder Boerse handelbar, die wir
  angebunden haben. Vor jeder Zusage die Verfuegbarkeit am Zielmarkt pruefen -
  sonst verspricht man eine Spur, die es dort nicht gibt.
- **Den Unterschied im Bericht benennen:** eigener Gewinn ist erst nach genug
  Papierrunden eine Aussage; "wie im Kanal" ist keine Zielgroesse.
- Die neue Spur durchlaeuft danach die regulaere Anbindung (die fuenf Stellen
  und die `.gitignore`-Whitelist, siehe SKILL.md) - ein Sonderweg nur fuer
  Signalmuster existiert nicht.

## Fremder SAMMLER, eigene Spur (Radar-Muster)

Sammelt das Fremd-Repo die Daten selbst (Radar, Index, MCP), wird die Spur
**nicht** per `subprocess` oder Netz an den Sammler gehaengt. Stattdessen:

1. **Die Spur liest die Datenbank des Fremd-Repos** - genau ein Zugang, `mode=ro`
   und eine Whitelist der erlaubten Anweisungen (`SELECT`/`WITH`/`PRAGMA`, sonst
   Abbruch). Den Pfad als Umgebungsvariable fuehren (Naht fuer Tests).
2. **Der Sammler laeuft als eigener no_agent-Cron** (`discover`/`track` im
   Fremd-venv, leere Ausgabe = nichts senden, Watchdog-Muster).
3. Folge: die Spur ist **offline testbar** (Fixture-Datenbank, kein Netz), ein
   Sammlerausfall ist an EINER Stelle sichtbar, und die Spur kann nie in fremde
   Daten schreiben.

Zwei Merksaetze dazu:

- **Das Geschehen kopieren, nicht die Rangliste.** Wer die Bestenliste kopiert,
  zuechtet nach dem Ergebnis und misst nichts. Bei Ereignis-Feed-Spuren: die
  Handlungen einer Kohorte sind das Signal (ab zwei verschiedenen Kaeufern,
  Verkaufsdruck derselben Kohorte blockiert).
- **Einen neuen Einstieg je Zyklus** (staerkster Kandidat zuerst). Sonst fuellt
  der erste Zyklus mit Daten das ganze Buch, und die Auswertung kann nicht
  zeigen, welcher Rang traegt.
- **Die Spurliste altert.** `pruefe_ratschen.py` fuehrte die drei juengsten
  `spur_buch`-Spuren nicht, weil niemand sie nachgetragen hatte - nach jeder
  neuen Spur diese Liste mitpruefen (sie ist neben `dauerlauf.SPUREN` die
  zweite Stelle, die einen Spurnamen von Hand traegt).

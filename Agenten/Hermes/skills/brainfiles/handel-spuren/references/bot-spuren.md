# Bot-Spuren: eine geklonte Fremdquelle als Papierbuch

Ausloeser: „nimm Bot X in die Handelsspuren", „installiere die Repos und bau
Spuren daraus", „bau IHNEN eine Spur". Die Quelle liegt in einem Fremd-Repo
unter `Werkstatt/Repos/` (Repo einrichten: `repo-flotte`).

## Die Grundentscheidung zuerst

Fremd-Agenten sind **Sprachmodell-Agenten mit echtem Orderpfad** (echte
Schluessel, echte Boerse). Beides gehoert nicht in den Hausbetrieb. Eine
Bot-Spur hat deshalb genau drei Bausteine:

1. **Daten** - entweder eine ECHTE Funktion des Bots rufen, oder dieselben
   oeffentlichen Endpunkte selbst abrufen.
2. **Regel** - deterministisch im Haus, nachrechenbar. Kein LLM-Urteil.
3. **Buch** - Hausformat (Zustand, Journal, Q:-Spiegel, Ratsche, Stop/Ziel),
   **kein Live-Zweig**, `--live` verweigert mit Begruendung.

*Fertig, wenn* die Spur ohne Fremdschluessel laeuft und jede Zahl im Journal
nachrechenbar ist.

## Weg 1: die Funktion des Bots rufen (besser)

Gibt es im Repo eine wiederverwendbare Datenfunktion (nicht nur `main()`),
wird SIE gerufen - im **venv des Bots** als kurzer Unterprozess. Damit bleiben
die Fremd-Abhaengigkeiten (pandas, requests, ta-lib) dort, wo sie hingehoeren,
und das Haus-venv wird nicht angefasst. Dieselbe Bauform nutzt der Dauerlauf mit
`SPUREN[...]["python"]` fuer die nautilus-Spur.

```python
BOT = os.path.join(HANDEL, os.pardir, os.pardir, "Werkstatt", "Repos", "<repo>")
BOT_PYTHON = os.path.join(BOT, ".venv", "Scripts", "python.exe")
BOT_AUFRUF = (
    "import json, contextlib, io, sys\n"
    "sys.path.insert(0, r'{src}')\n"
    "import <modul> as n\n"
    "_puffer = io.StringIO()\n"
    "with contextlib.redirect_stdout(_puffer):\n"
    "    d = n.<funktion>(sys.argv[1])\n"
    "print(json.dumps(d))\n")
```

- **Statusausgaben des Bots unterdruecken.** Die Fremdfunktionen drucken bei
  jedem Aufruf („Fetching ..."). Der Dauerlauf liest die Ausgabe seiner Spuren
  auf Signalwoerter - fremde Zeilen darin sind nicht zuzuordnen. Das Skript
  druckt deshalb NUR JSON, der Aufrufer nimmt die letzte Zeile.
- **Fehlt das Repo oder sein venv, sagt die Spur das und bucht nichts.** Nie
  Ersatzwerte erfinden; die Meldung ist die Auskunft.

## Weg 2: dieselben Daten oeffentlich holen

Monolithen mit `main()` (und oft Pro-API) lassen sich nicht als Funktion rufen.
Dann dieselben Endpunkte ueber die oeffentliche API holen (`urllib`, nur
Standardbibliothek - kein `requests` im Haus-venv) und in der README
**ausdruecklich sagen**, dass es nicht der Bot selbst ist.

## Signal-Kanal-Screenshot: das ehrliche Gegenstueck statt Copytrading

Ausloeser: Max schickt einen Screenshot aus einem VIP-Signal-Kanal (Gewinnkarte,
hoher Hebel, ROI in Prozent) und fragt „koennen wir das auch schaffen?" —
oder kurz danach „Ja spur anlegen".

Erst die drei Punkte klar sagen, dann bauen (nicht umgekehrt):

- Ein Screenshot ist eine **Gewinnkarte, kein Track Record** — die
  Verlustsignale sieht niemand (Zuchtauswahl).
- **10–20x Hebel** auf Einzelsignale ohne sichtbare Stop-Definition ist genau
  das Risikoprofil, das die Hausregeln ausschliessen. Ein Hebel ist keine
  Strategie.
- Ein **synthetischer Aktien-/Rohstoff-Perpetual** liegt auf keiner
  angebundenen Boerse (OKX-Spot, Kraken-Spot) — nicht handelbar, egal wie gut
  das Signal war.

Das Gegenstueck ist eine Papierspur auf demselben BEOBACHTBAREN Muster (z. B.
kurzfristiger Kursimpuls plus Volumenfilter), deterministisch, mit Stop und
Ziel, ohne Hebel, ohne Live-Zweig, ueber den gemeinsamen Kern
(`spur_buch.py`) — nach ein paar Wochen Papierlauf auswertbar und nachrechenbar.
Das ist ehrlich vergleichbar, ein Kanal-Copytrading ist es nicht.

Nachweis beim Bauen: `--vorschau` gegen die echte Quelle (greift die Regel
ueberhaupt?), dann ZWEI echte Papierzyklen — der erste bucht die Positionen,
der zweite muss den Bestand halten. Ein Volumen-/Groessenfilter im Tor gehoert
in `wachen.json`, nicht in den Code.

## Der gemeinsame Kern

`Agenten/Handel/spur_buch.py` traegt das Buch fuer alle Feed-Spuren: `pfade()`
(auch die Risikostufen-Dateinamen), `zyklus()`, `einstieg()`, `pruefe_ausstiege()`,
Ratsche, Spiegelung. Was eine Spur liefert, sind nur:

```python
quelle(w)        -> (daten, kurse, fehler)      # Abruf, Fehler werden gemeldet
signal(daten, w) -> "long" | "short" | None     # die Regel
ziel(daten, w)   -> Preis | None                # optional: Ziel als MARKTPUNKT
```

- **Ziel als Marktpunkt** (`ziel_preis`): fuer Signale, deren Ziel eine Linie
  ist (Optionszone, Widerstand). Ein Ziel hinter dem Einstieg wird abgelehnt -
  es waere sofort erreicht.
- **Ein Kern, nicht drei Kopien.** Drei Spuren mit drei Kopien derselben
  Buchhaltung sind drei Stellen, an denen derselbe Fehler einzeln auftreten kann
  (G/V auf den Kurswert statt auf den Nominalwert).

## Anschluss-Checkliste (sonst bleibt die Spur unsichtbar oder rot)

1. `dauerlauf.SPUREN` - sonst faehrt sie niemand.
2. `auswertung_alle.BOT_SPUREN` (Journalform kauf/verkauf + `einsatz_usd` ->
   derselben Rechenweg wie die Indikator-Spuren).
3. `pruefe_ratschen.SPUREN` - die Ratsche wird je Spur ueber ihr eigenes Modul
   befragt.
4. `befehle.FAMILIE` - ohne Eintrag ist der Test „jede Spur hat Familie und
   Leser" rot.
5. `tagesbericht` - Holer `spur_<name>()` ueber `_spur_indikator(...)`.
6. `.gitignore` -s.u.; **nur** `wachen.json` freigeben.
7. `tests/test_risikostufe.py` - Kern-Spuren ueber einen eigenen Test (sie
   tragen ihre Dateinamen in `spur_buch.pfade`, nicht als Modulkonstanten).
8. README der Spur + ein Absatz in `Wissen/Handelsregeln.md` (Quelle, Regel,
   Grenzen, Nachweis).

## Fallen

- **gitignore: die spaetere Regel gewinnt.** Eine Freigabe
  `!Agenten/Handel/<spur>/*.json`, die NACH der Sperre
  `Agenten/Handel/*/zustand.mittel.json` steht, hebt sie wieder auf - prompt
  landen laufende Zustaende im Commit. Je Spur **nur** `wachen.json` freigeben
  (Code, README, Tests als eigene Zeilen), Zustand und Journal gesperrt lassen.
  Kontrolle: `git ls-files 'Agenten/Handel/*/zustand*.json'` muss LEER sein.
- **Ein `!` auf eine Datei greift nicht, solange ihr Ordner ignoriert ist.**
  Bei ignoriertem Elternordner muss der Ordner selbst mit freigegeben werden
  (`!dir/` **und** `!dir/*.<endung>`).
- **Ein Test schreibt ins echte Buch.** Tests, die eine journalende Funktion
  direkt pruefen (Einstieg/Ausstieg), buchen in die ECHTEN Dateien - sechzehn
  Testbuchungen stehen danach als Handelsrunden im Journal. Zweifach sichern:
  in diesen Testklassen `SCHREIBEN = False` setzen UND einen Modulwaechter
  bauen: `setUpModule()` merkt Dateiliste + Groessen des echten Spurordners,
  `tearDownModule()` vergleicht - jeder Test, der nach draussen schreibt, faellt
  sofort auf. Wachen/Zustand/Journal zusaetzlich auf einen Temp-Ordner patchen.
- **Die `sys.path`-Reihenfolge entscheidet, welches `handeln.py` geladen wird.**
  Die Spuren haben gleichnamige Module (`scanner/handeln.py`). Ein
  `for p in (SPUR, HANDEL, scanner): insert(0, p)` stellt `scanner` **vorne** -
  der Test prueft dann das falsche Modul. Die eigene Spur ZULETZT einfuegen und
  mit `assert h.__file__.startswith(SPUR)` absichern.
- **Kein Sprachmodell-Buch ohne Ansage.** Wer einen LLM-Agenten doch anschliesst
  (Ollama, Router), schreibt diese Grenze ausdruecklich in die README: das Buch
  haengt dann am Modell und ist nicht mehr nachrechenbar.

## Eine Datenfunktion fuer mehrere Spuren erweitern, statt sie zu forken

Teilen zwei Bot-Spuren denselben Datenabruf (`moondev_daten.maerkte()` fuer
24h- UND 1h-Momentum-Varianten), bekommt die bestehende Funktion ein neues
Parameter mit unveraendertem Vorgabewert (`prozentfelder="24h,7d"`) statt
einer zweiten Kopie. Sonst driften zwei Kopien derselben API-Anfrage
auseinander, sobald eine spaeter einen Fix bekommt und die andere nicht.

## CoinGecko `/coins/markets` teilt sich den Rate-Limit ueber alle Spuren

Mehrere Bot-Spuren, die `moondev_daten.maerkte()` rufen (topmovers,
marktlage, listingarb, jede neue Momentum-Variante), teilen sich denselben
oeffentlichen CoinGecko-Deckel. Wird beim Bauen/Testen einer neuen Spur
kurz hintereinander mehrfach `--vorschau`/`--papier` gegen mehrere dieser
Spuren gefahren, kommt `HTTP Error 429: Too Many Requests` - das ist kein
Bug der neuen Spur, sondern der geteilte Deckel. `quelle()` faengt das
bereits ab ("Keine Daten - Zyklus ohne Buchung beendet", kein Absturz,
keine gebuchte Position). Beim Nachweis-Lauf 20-60 s zwischen Testaufrufen
gegen verschiedene CoinGecko-Spuren lassen, statt den 429 als Fehler zu
behandeln oder einen zweiten Versuch sofort hinterherzuschicken.

## Fallen bei Mini-Preisen und Rate-Limits (moondev_sniper, 19.09.2026)

- **`%.6f` im Journal kollabiert Mini-Preise.** Bei Kursen ~1e-6 (frische
  Solana-Launches) runden Einstieg und Stop auf denselben String
  (`0.000003` == `0.000003`) - die Auswertung liest G/V = 0, obwohl die
  Position im Zustand float-Praezision hat. Der gemeinsame Kern hat dafuer
  `spur_buch.pformat()`: grosse Kurse bleiben 6 Stellen (bestehende Spuren
  unveraendert), kleine bekommen 8 bzw. 12. Wer eine Spur mit Mini-Preisen
  baut, nutzt `pformat` fuer preis/stop/ziel im Journal - nie `%.6f`.
- **Eine oeffentliche API mit hartem Rate-Limit (HTTP 429) liefert nichts,
  wenn man fuer ALLE Kandidaten einen Preis holt.** swap-api.pump.fun deckelt
  nach wenigen Abrufen; 40 Preis-Abrufe je Zyklus reissen den Deckel und die
  Spur bucht still nichts. Einstiege koennen ohnehin nur die
  `max_offene_positionen` juengsten sein (das Buch ist danach voll) - genau
  fuer die den Preis holen, plus fuer die gehaltenen Positionen (deren
  Stop/Ziel weiter laufen muss, auch wenn der Mint die Neuesten-Liste
  verlassen hat). 429 mit einem Retry+Pause behandeln statt still None.
- **Slippage ist bei duenner Liquiditaet real, kein Bug.** Der Preis kommt vom
  letzten Swap-Trade; zwischen zwei Zyklen rutscht der Kurs durch den Stop,
  und der 8-%-Stop wird mit deutlich groesserem Verlust ausgefuehrt (gemessen
  -37.59 USD bei 62.50 Nominal). Das gehoert ehrlich in die README und die
  Handelsregeln-Notiz - nicht als Fehler, sondern als Abbildung der
  Memecoin-Realitaet.
- **Ein Test-Token braucht BEIDE Felder, wenn quelle() und signal()
  verschiedene ableiten.** quelle() rechnet das Alter selbst aus
  `created_timestamp`, signal() liest das vorberechnete `alter_minuten`.
  Fehlt eines, ist der Test gruen, aber der echte Lauf bucht nie (signal()
  gibt None, weil das Feld fehlt). Das Test-Token stellt beide bereit.

## Was nach dem Anschliessen zu tun bleibt

Nicht alle Agenten eines Repos werden Spuren (fehlender Daten- oder
LLM-Schluessel, Wallet, kein Handelsbezug). Den **Rest vormerken**: eine Notiz
`Wissen/<Thema>.md`, die die uebrigen Agenten **nach der fehlenden Zutat**
gruppiert (Daten-Schluessel, LLM-Schluessel, RPC/Wallet, kein Handelsbezug) -
und je Gruppe den Weg nennt, wenn es weitergehen soll. Nicht nach Namen
auflisten: die Gruppe sagt, was zu tun waere.

## Ein Liquidationsband liegt HINTER dem Kurs, nicht davor

Fuer Spuren, deren Signal aus dem Strom der Zwangsschluesse kommt
(`moondev_liquidation`, `liq_wand`). Drei gemessene Eigenschaften der oeffentlichen
Quelle, die jede Regel davor beruecksichtigen muss:

- **Der Strom ist ein Ausschnitt, kein Bestand.** Die ~100 Eintraege eines Abrufs
deckten 1,8 bis 14,7 Minuten ab, der juengste war 0,6 bis 26 Minuten alt. Man
sieht die unmittelbare Vergangenheit, nicht "die offenen Wände".
- **Die SEITE eines Bandes ist die Richtung des letzten Laufs**, keine Eigenschaft
des Bandes: Longs sterben beim Fallen, Shorts beim Steigen. In beiden Messungen
waren 100 von 100 Liquidationen Longs (fallender Kurs) - eine Short-liquidierte
Wand gibt es nur mitten in einem Aufwaertsimpuls.
- **Ein Band entsteht dort, wo der Kurs GERADE WAR.** Das groesste Band lag 0,25 %
ueber dem Spot und bestand ganz aus liquidierten Longs: die Verkaeufe sind durch
das Band gelaufen, der Kurs ist schon darunter.

**Folge fuer die Regel: "die Wand muss VOR dem Kurs liegen" ist fast nie
erfuellbar** - die Spur meldet dann "falsche Seite" und schweigt tagelang, was wie
ein Datenausfall aussieht. Richtig ist eine **Toleranz hinter dem Kurs** als
Wachen-Feld (`hinter_dem_spot_prozent`, Startwert 0.5, `0` stellt die strenge
Fassung wieder her), waehrend die Entfernungsgrenze (`max_abstand_prozent`) den
Deckel bleibt. Der Cluster zaehlt als BESCHLEUNIGER: man geht MIT ihm, nicht gegen
ihn.

Vorgehen, bevor an der Regel gedreht wird: eine **Messsonde** bauen, die aus dem
Live-Strom dieselben Baender bildet und je Band Seite, Abstand und Signal
ausgibt (Vorbild `liq_wand/probe_seiten.py`). Erst messen, dann die Regel
begruenden - und dieselbe Sonde nach der Aenderung erneut laufen lassen, damit
aus der Behauptung ein Beleg wird. Dazu zwei Testfaelle: ein Band knapp hinter
dem Kurs ergibt ein Signal, eines deutlich dahinter nicht.

Wie bei jeder Signalquelle gilt: "die Vorschau meldet ein Signal" ist nicht "es
wird gehandelt" - mit `MAXHIRN_ROUTINE=1` nachfahren (siehe `vorschau-schreibt-nicht.md`).

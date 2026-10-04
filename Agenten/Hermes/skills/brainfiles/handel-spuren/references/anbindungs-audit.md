# Anbindungs-Audit im Handel-Ordner

Wann: „was ist nicht abgeschlossen / nicht angebunden?“, „was laeuft hier
ueberhaupt?“ - oder als Abschluss nach dem Bau einer neuen Spur. Ziel ist eine
ergebnis-first-Liste in vier Toepfen:

1. **laeuft** und ist gemeldet
2. **laeuft**, aber unsichtbar (nicht im Bus, nicht im Tagesbericht)
3. **bewusst gesperrt** (Sperre in `wachen.json`, negatives Backtest-Urteil)
4. **Altlast** - Handwerkzeug oder verwaist

am Ende **eine** Empfehlung, nicht eine Optionsliste.

## Die Verdrahtungsstellen gegeneinander halten

Nicht jede einzeln lesen, sondern die Schnittmengen bilden - der Befund ist die
Differenz:

- `dauerlauf.SPUREN` — was im 15-min-Takt laeuft
- `Bus/handel_befehle.SPUREN` — was `/status` per Telegram zeigt
- `tagesbericht.py` — `Select-String -Pattern 'def spur_'` **und** der Eintrag im
  Tupel in `baue()` (zwei Stellen, beide noetig)
- Aufgabenplanung — `Get-ScheduledTask | Where-Object { $_.TaskName -match
  'Handel|Kraken|DCA|Verbesserer' }`, dann je Aufgabe
  `(Get-ScheduledTask -TaskName $n).Actions` fuer das Skript und
  `Routinen/<skript>.ps1` fuer das, was es aufruft
- Versionierung — `git check-ignore -v <pfad>` und `git status --porcelain <ordner>`

Eine Spur kann in `dauerlauf.SPUREN` stehen und trotzdem unsichtbar sein: sie
laeuft, aber `/status` und Tagesbericht kennen sie nicht. Das ist der
haeufigste Fund bei einer frisch gebauten Spur (Ordner da, Tests gruen, Lauf
sauber - und keine der vier Melde- und Versionsstellen nachgezogen).

## Aufrufer suchen

```powershell
Select-String -Path "$r\*.ps1","$b\*.py","$h\*.py" -Pattern 'modulname'
```

- **Kein `-Recurse` ueber `Agenten`**: laeuft durch `.venv`, `OpenAlice`,
  `nautilus` und reisst die ~300-s-Grenze des Host-Werkzeugs. Explizite
  Pfadliste uebergeben.
- Wer einen Modulnamen sucht, findet Definitionsstellen mit: `def <name>`, ein
  Docstring-Beispiel und der eigene Aufruf im `__main__`-Block zaehlen **nicht**
  als Aufrufer. Nur Treffer in fremden Dateien sind Beweise.

## Befunde richtig deuten (die drei Fehlalarme)

- **„kein Aufrufer“ ist kein Defekt.** Analysemodule (`dca.py`, `grid.py`,
  `reinvest.py`, `vergleich.py`, `beobachte_live.py`, `dca_auswertung.py`) sind
  Handwerkzeuge fuer Max - im `README.md` des Handelsordners beschrieben, per
  Definition nicht getaktet. Als Topp 4 melden, nicht als Luecke.
- **Stilllegung nie aus einem Textfeld lesen.** `stillgelegt`, `handel_erlaubt`,
  `freigabe.erfuellt` sind die Wahrheit; der `_`-Kommentar daneben ist Historie
  und kann das Gegenteil erzaehlen. Vor dem Urteil `git log --oneline -5` - an
  diesem Baum arbeiten mehrere Sitzungen, und eine Spur kann zwischen zwei
  Commits wieder angeschaltet worden sein.
- **Eine Spur, die ihren Lauf verweigert und trotzdem per Aufgabe startet, ist
  kein Fehler.** Die Kraken-Spur rechnet im Papierlauf die Rangliste weiter, obwohl
  `handeln.py --papier` den Handel verweigert - so bleibt der Nachweis erhalten.
  Das ist gewollt; nicht „aufraeumen“.

## Was in den Bericht gehoert

Je Luecke die **konkrete Stelle** (Datei, Funktion/Dict) und die kleinste
Reparatur - nicht „orbk ist nicht richtig angebunden“, sondern „`spur_orbk()`
fehlt in `tagesbericht.py` plus der Eintrag im Tupel in `baue()`“. Dazu die
Trennung, die Max immer mitliest: was absichtlich **nicht** angefasst wurde
(laufender Zustand, Fremdarbeit, generierte Dateien) und was eine Entscheidung
von ihm braucht.

## Eine NEUE Spur in den Betrieb verdrahten (Reihenfolge)

Der Handelszyklus ist der kleinste Teil. Diese Stellen gehoeren alle mit, sonst
faellt es erst im Test oder gar nicht auf:

1. `dauerlauf.SPUREN` — Eintrag `{"ordner", "waehrung", "skript"}`; ohne ihn
   laeuft die Spur nie. Der Dauerlauf startet je Zyklus einen Unterprozess:
   eine NEUE Zeile wirkt ohne Neustart, eine geaenderte erst danach.
2. `lage.py` — eine `spur_<name>()`-Funktion UND der Eintrag in `HOLER`.
   `tests/test_lage.py` prueft die ZAHL (`assertEqual(len(lage.HOLER), N)`) —
   die Zahl im Test mitziehen. Sonst bricht die Suite an einer Stelle, die mit
   der neuen Spur nichts zu tun zu haben scheint.
3. `befehle.py::FAMILIE` — Anzeigename fuer `/strategien`. `test_befehle.py`
   prueft je SPUREN-Eintrag, dass FAMILIE **und** ein HOLER-Leser existieren.
4. `pruefe_ratschen.py` — ZWEI Stellen: Eintrag in der Liste
   `(spur, ordner, modulordner, modulname)` UND aus der `RUHT`-Tupel
   herausnehmen. Eine vergessene Spur wird dort stillschweigend NICHT geprueft
   („Ruhend, nicht geprueft") — das Werkzeug meldet gruen, ohne sie angesehen
   zu haben.
5. Bus: die gestartete Datei uebergibt `handel/<spur>` wortwoertlich
   (`ereignis.lauf("handel/<spur>")`), sonst meldet `test_anbindung_handel.py`
   sie als ohne Anbindung.
6. `wachen.json` der Spur: `journal_zweitziel` setzen (Bedingung 4), die
   Ratsche als AUSDRUECKLICHEN Betrag (`drawdown_halbierung_usd` — der
   Prozentwert wird nicht mehr gelesen) und `instrument_aktiv` fuellen, wenn die
   Strategie eins waehlt.
7. `.gitignore`-Freigabe je Ebene, belegt mit
   `git check-ignore -v --no-index <pfad>` — sonst ist die Spur fuer Git
   unsichtbar und wird nie versioniert.
8. Nach dem ersten echten Zyklus: `spiegelstand.py` (byte-genau gegen Q:) und
   `pruefe_ratschen.py` laufen lassen — beide lesen die Spurenliste aus
   `dauerlauf.SPUREN` und decken die neue Spur damit automatisch ab. Die
   Spurtests aus `<spur>/` mit ihrer eigenen Aufrufregel (siehe
   `spur-tests-und-auswertung.md`).

**Ein negatives eigenes Backtest-Urteil sperrt die Spur nicht, es begrenzt sie:**
angeschlossen wird sie als PAPIER (`handel_erlaubt=false`, `freigabe.erfuellt=false`,
`backtest_bestanden=false`, kein Live-Zweig im Code), das Urteil bleibt im
Wachen-Text stehen, und der Bericht nennt es — sonst sieht die Zeile im Log
(`<spur> (live) ok`) nach Fortschritt aus, obwohl gemessen nichts zu holen ist.
Wer eine Papier-Spur mit `--live` anfahert, laesst sie den Aufruf mit GENAU
EINEM Grund und OHNE das Wort „Freigabefenster" ablehnen (Muster `orbk`,
`spiegel`) — sonst stellt der Dauerlauf eine Freigabe-Anfrage fuer eine Spur,
die gar nicht live handeln kann.

## Der Bus-Anbindungstest (test_anbindung_handel.py)

- Die Pruefung ist zweistufig: eine **dynamische ast-Pruefung ueber
  `dauerlauf.SPUREN`** (jede per subprocess gestartete Datei muss
  „handel/<spur>“ wortwoertlich uebergeben) deckt NEUE Spuren automatisch ab -
  kein Eintrag, kein Testumbau noetig. Daneben existiert eine **feste
  7er-Legacy-Liste mit `len == 7`-Guard: NICHT erweitern** (der Guard bricht),
  neue Spuren brauchen dort nichts.
- Spuren, die ihr Buch ueber `Handel/spur_buch.py` fuehren, oeffnen den Bus im
  Kern (`ereignis.lauf`) - die Pruefung zaehlt das als Kern-Bindung, wenn die
  gestartete Datei ihren EIGENEN Namen uebergibt und spur_buch.py
  `ereignis.lauf` traegt. Eine solche Spur ohne eigenen Bus-Aufruf ist trotzdem
  angebunden; nicht als „ohne Anbindung“ melden, solange diese Bedingung gilt.

## Die Anbindung VERIFIZIEREN: die Boerse fragen, nicht die Datei

Die Spalten der Bestandstabelle oben sind Aussagen ueber **Dateien**. Die
Frage „kann diese Spur handeln?" ist eine Frage an die **Boerse**, und sie
beantwortet andere Dinge:

- `Handel/anbindung_pruefen.py` (rein lesend, **ordnet nichts**) fahrt je Spur
  genau den Weg, den sie im Betrieb nutzt, und fragt: Schluessel vorhanden,
  **Demo-Modus aus**, Guthaben in der **Quote der Spur**, Kurs des
  Instruments. Die Zeile, die man liest, ist damit ein Zustand und keine
  Behauptung ueber Quelltext.

**Demo-Modus ist eine eigene Spalte und wird nie aus dem Namen abgeleitet.**
Ein Demo-Schluessel sieht wie ein live aus und ist keiner - genau dieser
Fehlschluss hat den Roundtrip-Sonden-Vorgang geprägt.

**Die Quote ist Teil der Probe.** Ein Konto kann USDC und EURC fuehren und
0,00 USDT; wer das Guthaben in einer anderen Waehrung abfragt, sieht ein
leeres Konto und schliesst „die Boerse ist weg". Die Probe liest die Quote aus
der `wachen.json`.

**Das Instrument kommt aus der Spur, nie aus dem Prober.** Der erste Wurf
fragte bei jeder Kraken-Spur nach `BTC-USDT-SWAP` und meldete fuenf Spuren als
„kein Kurs" - Kraken fuehrt `BTC/EUR` bzw. `XXBTZEUR`, die Futures-Maerkte
`PF_XBTUSD`. **Eine Pruefung, die ihre eigene Vorgabe fuer einen Befund haelt,
sieht gesunde Spuren kaputt und echte Ausfaelle als normal** - schlimmer als
keine Pruefung. Das gilt fuer jedes Werkzeug, das eine Spur **beurteilt**:
`instrument`/`paar`/`symbol` aus der Wache lesen, mit boersenspezifischem
Rueckfall.

**Und das Ergebnis ist eine Behauptung ueber die SPUREN, nicht ueber die
Boerse.** „Alle zwoelf anbindungsbereit" heisst: der Weg ist da und gesund.
Es sagt **nichts** darueber, ob die Spur freigegeben ist oder freigegeben
werden sollte - das ist eine getrennte Frage mit einer getrennten Zahl
(`gebuehren-tor.md`). Beide Antworten in einem Absatz zu vermischen ist der
Fehler, den ein Freigabegespraech ausloest.

## Werkzeuge: Stand aller Spuren und Sperrgruende in einem Aufruf

Statt die Verdrahtungsstellen von Hand gegeneinander zu halten (aus
`Agenten/Handel/`, rein lesend, kein Fenster, keine Order):

- `python spuren_stand.py` — eine Tabelle ueber ALLE Spuren aus
  `dauerlauf.SPUREN`: `handel_erlaubt`, Herzschlag-Grenze, Fensterzustand,
  `freigabe.erfuellt`, gefundener Orderaufruf, Buchgroesse je Zustandsdatei,
  Alter des letzten Zyklus im Log. Beantwortet „was laeuft, was darf, woran
  haengt es" in einem Bild.
- `python sperrgruende.py` — faehrt je Spur ihre EIGENE `--vorschau` und zeigt
  die Gruende, markiert „NUR das Fenster - der Dauerlauf fragt hier nach
  Freigabe". Das ist die VORHERSAGE, ob eine Spur scharf geht (Regel in
  `live-schalten.md`: genau ein Grund, darin das Wort „Freigabefenster") — nicht
  aus Schaltern und Guthaben schliessen.

**Eine Heuristik-Spalte ist ein Hinweis, kein Befund.** Die Order-Spalte sucht
Order-Endpunkte im Spurordner (`/api/v5/trade/order`, `AddOrder`, ...) und
UEBERSIEHT Spuren, deren Orderweg in einem Boersenmodul liegt (`okxf.py`,
`kraken.py`, ein Adapter wie `kraken_spot.py`) — live-faehige Spuren standen so
als „keiner" in der Tabelle. Fuer die Wahrheit `sperren_live()` der Spur lesen
oder nach dem Aufruf greppen; nie anhand der Spalte entscheiden.

## Ein Bestandslauf ueber den GANZEN Baum meldet SCHEMA-BRUECHE als Befund

Das ist die teuerste Fehlerquelle einer Inventur: das Werkzeug liest die Felder
EINER Spurenfamilie und meldet jede andere Familie als defekt. Vier gemessene
Faelle, alle aus einem Lauf ueber 45 Spuren:

- **Feldnamen je Spurfamilie aufloesen, bevor ein Befund faellt.** Ein Stop-Audit
  ueber alle `zustand.json` las `inst`/`einstieg`/`stop` und meldete sieben
  Positionen einer Spur als „kein Einstieg" — die fuehrt `symbol`/`token`/
  `einsatz_usd` und war in Ordnung. Ein feldfehlender Wert ist zuerst ein
  **Schema-Bruch**, kein Positionsfehler: pro Familie den echten Feldnamen
  ermitteln und im Befund MITSPURIG ausweisen, welche Spur welches Schema traegt.
- **Ein Gruppierungsschluessel, den ALLE Positionen einer Spur nicht fuehren,
  ist kein Schluessel.** Dasselbe Werkzeug wollte gestapelte Positionen je
  (Instrument, Seite) zusammenfassen und las bei zwei Spuren `inst` als `None` —
  dort sind ALLE Positionen EINE Gruppe, es haette das komplette Buch zu einer
  Position verschmolzen. **Vor dem Zusammenfassen pruefen, dass der Schluessel
  bei mindestens einer Position belegt ist**; fehlt er, gehoert die Spur aus dem
  Lauf heraus, nicht in die Ausgabe.
- **`lage.HOLER` ist ein Tupel aus FUNKTIONSNAMEN** (`spur_squeeze`,
  `spur_omniquant_weit`), nicht aus Spurennamen. Eine Mitgliedschaftspruefung
  `name in lage.HOLER` meldet fuer jede Spur „FEHLT", obwohl sie drin ist.
  Richtig: je Eintrag `startswith('spur_')` und den NAMEN ANHANG pruefen.
- **Nicht jeder Testsatz des Hauses ist unittest.** `Bus/tests/
  test_anbindung_handel.py` schreibt nackte `def test_*`-Funktionen (pytest),
  keine Klassen — `unittest discover` meldet dafuer `Ran 0 tests` und
  `NO TESTS RAN`, was wie ein gruener Lauf aussieht. Der Scanner-venv hat kein
  pytest, also die Funktionen ueber `importlib.util.spec_from_file_location`
  laden und direkt aufrufen, jede Ausnahme als Fehler zaehlen. „0 Tests" ist
  nie ein Beleg.

## EINE SPUR RAUSNEHMEN — die Umkehrung, mit derselben Pflicht

„Spur X komplett raus" ist nicht `rm -rf` und nicht der Eintrag in
`dauerlauf.SPUREN`. Die Spur haengt an denselben Listen wie beim Anschliessen —
plus an zwei Stellen, die dort nicht vorkommen — und **ein an ihr
vorbeigesetztes Werkzeug crasht beim naechsten Lauf**, nicht beim Loeschen.

### Reihenfolge

1. **Sichern, dann loeschen.** Der Ordner gehoert nach
   `Werkstatt/Ausgemustert/<bereich>/<spur>-JJJJMMTT-HHMM/`; alle drei
   Risikostufen mitnehmen (`zustand.json`, `zustand.mittel.json`,
   `zustand.hoch.json` sind drei Staende derselben Spur). Ein geloeschtes
   Journal ist die Historie.
2. **Inventar ZIEHEN, nicht die Liste von oben uebernehmen.** `grep -rl` ueber
   den echten Baum mit Ausschlussliste, dann je Treffer die ZEILE lesen — nicht
   nur den Dateinamen. Fuenf Hand-listen: `dauerlauf.SPUREN`, `lage.HOLER`,
   `befehle.FAMILIE`, `auswertung_alle.SPUREN`, `pruefe_ratschen.SPUREN` —
   `RUHT` ausdruecklich mitnehmen, eine dort noch als ruhend gefuehrte Spur wird
   nie geprueft, ohne dass irgendwo etwas fehlt.
3. **Werkzeuge mit HARTKODIERTER Spurliste sind die Falle.** Ein
   Gebuehren-Werkzeug mit einer Tabelle `("<spur>/wachen.json", "feld", wert)`
   laeuft nach dem Loeschen in `FileNotFoundError` — mitten im Betrieb, nicht im
   Aufruf. Solche Werkzeuge gehoeren auf `dauerlauf.SPUREN` umgestellt, nicht
   auf eine zweite Liste, die man beim Loeschen von Hand pflegt. **Nach dem
   Loeschen JEDES Werkzeug starten, das eine Spur nennt** — im gemessenen Fall
   war der Testlauf dieser Suite der Finder, nicht das Absuchen.
4. **Tests mit festem Namen mitziehen.** Ein `SPUREN = ("spiegel", "kopier",
   …)`-Tupel und ein `assertEqual(len(HOLER), N)` sind dieselben Hand-Listen
   wie im Code. Gemessen waren neun Testdateien betroffen, davon vier mit
   Zaehl-/Namenslisten.
5. **`.gitignore`: nicht nur die Freigabe, auch die Sperre.** Die Spur hat
   sieben Zeilen (4 × `!…/*.py|md|json`, 3 × Sperre auf `zustand.json`,
   `handelsjournal.csv`, `ablehnungen.csv`). Die Freigabezeilen zeigen ins Leere,
   die Sperrezeilen bleiben als toter Text stehen — sonst greifen sie bei der
   naechsten Spur mit gleichem Namen wieder.
6. **Index leeren, dann Ordner loeschen:** `git rm -r --cached --quiet <pfad>`
   vor dem `rmtree`, sonst zeigt `git status` die Dateien als unversioniert
   statt als geloescht.

### Der Suchbefund, der den Auftrag gekostet hat

Ein Python-`os.walk` ueber `Agenten/` **ueberschreitet die 300-s-Werkzeuggrenze**
zweimal — der Ordner traegt Fremdbaeume. `grep -rl` mit Ausschlussliste
(`-E '\.venv|__pycache__|OpenAlice|Hermes/cache|Hermes/skills|hermes-agent|
node_modules|\.worktrees|\.claude|bak-…|Ausgemustert'`) laeuft durch und zeigt
zugleich, was man selbst erzeugt hat.

Der Grund sind **verwaiste `.worktrees/`-Ordner**: sie liegen im Baum, enthalten
je eine vollstaendige Kopie aller Handelsdateien (gemessen 25 Ordner x 48
Dateien) und gehoeren zu fremden, beendeten Sitzungen. Sie stoeren keine
`master`-Lektuere, vergiften aber jede repo-weite Suche und jeden Platzmesslauf.
Sie sind die erste Frage, wenn eine Suche eine Seite findet, die es gar nicht
gibt — und eine Entscheidung fuer Max, keine automatische Loeschung.

### Nachweis

`dauerlauf.SPUREN` importieren und die Spur gegen `False` pruefen, ALLE Module
laden, die die Spur ueber eine Liste nannten (`lage`, `tagesbericht`,
`befehle`, `auswertung_alle`, `gesamtbilanz`, `handelszentrale`, `replay`,
`Bus/handel_befehle`) — ein Import-Fehler ist hier ein Befund, kein
Testrauschen — und die betroffenen Tests einzeln mit dem **Exit-Code** fahren.
Eine Kette `cmd | tail -1` zeigt die letzte Zeile, nicht den Erfolg: ein
`FAILED` steht in derselben Zeile, die ein laufender Test als letztes schreibt.

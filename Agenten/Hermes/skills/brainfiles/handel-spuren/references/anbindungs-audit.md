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

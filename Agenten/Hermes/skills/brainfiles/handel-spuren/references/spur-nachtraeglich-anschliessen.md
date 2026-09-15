# Bestehende Spuren nachtraeglich in den Takt haengen

Wann: Ein Ordner unter `Agenten/Handel/` hat `handeln.py` + `wachen.json`, laeuft
aber nicht im Dauerlauf - Befund aus dem Anbindungs-Audit
(`references/anbindungs-audit.md`). Auch fuer mehrere auf einmal (15.09.2026:
vier Indikator-Spuren an einem Tag). Abgrenzung: eine Spur von NULL bauen ist der
andere Weg (`references/neue-spur-ende-zu-ende.md`, Abschnitt 3 "Verdrahten");
hier fehlt nur die Verdrahtung, der Code steht schon.

## Vorarbeit, bevor eine Zeile geaendert wird

1. **Ist die Spur fremde, frische Arbeit?** Commit-Datum und mtime lesen
   (`git log -1 --format="%h %ad %s" --date=iso -- <ordner>`). Bei Minuten bis
   Stunden: nicht umbauen, nur verdrahten - und die Tests ZUERST mit dem Aufruf
   aus dem Testkopf fahren (siehe Fallen).
2. **Was hat sie schon?** Drei Greps entscheiden den Umfang:
   - `grep -n "ereignis.lauf" <spur>/handeln.py` -> Bus-Anbindung fehlt?
   - `grep -n "spiegele_journal\|vermerke_spiegelung" <spur>/handeln.py` ->
     Spiegelung vorhanden, mit oder ohne Nachzug?
   - Kopf des `handelsjournal.csv` (oder die `journal(...)`-Aufrufe) -> welche
     Spaltennamen schreibt sie?
3. **Zielordner anlegen:** `mkdir -p Q:/Handel_Journal/<spur>`. Ohne ihn ist die
   Kopie ausser Haus still kaputt (kein Fehler des Laufs, nur ein leeres Ziel).
4. **Zustandsform merken:** Feldnamen aus `<spur>/handeln.py` ablesen
   (`z["positionen"].append({...})`), nicht raten - der Tagesbericht braucht sie.

## Die sechs Stellen (bei einer BESTEHENDEN Spur)

1. `dauerlauf.py` -> `SPUREN`: `"<spur>": {"ordner": "<spur>", "waehrung": "USD"}`.
   `"skript"` nur, wenn die Einstiegsdatei nicht `handeln.py` heisst; `"python"`
   nur bei eigenem venv (Muster nautilus).
2. `Bus/handel_befehle.py` -> `SPUREN`-Tupel (Telegram `/status`).
3. `tagesbericht.py` -> `spur_<name>()` **und** der Eintrag im Tupel in `baue()`.
   Bei N gleichartigen Spuren EINE gemeinsame Helferfunktion, nicht N Abschriften
   (Vorbild `_spur_indikator()` fuer die vier Indikator-Spuren).
4. `ereignis.lauf("handel/<spur>")` in der `handeln.py`: Wrapper um `main()` -
   `def main(): with ereignis.lauf(...): return _main()`, der bisherige Body wird
   `_main()`. Dazu `import ereignis` neben `import wachen_pruefung` (das
   Bus-Verzeichnis liegt schon auf `sys.path`). Vorher pruefen, ob Tests `main()`
   rufen: die vier Indikator-Spuren rufen `lauf()`, die Bus-Meldung stoert sie
   also nicht.
5. **Spiegelung nachziehen:**
   ```python
   ziel = w.get("journal_zweitziel")
   ok, info = wp.spiegele_journal([JOURNAL, ZUSTAND], ziel)
   if wp.vermerke_spiegelung(z, ziel, ok, info, schreibe_zustand) and ok:
       wp.spiegele_journal([ZUSTAND], ziel)
   ```
   Der Vermerk ist juenger als die Kopie: ohne den zweiten Aufruf meldet
   `spiegelstand.py` in JEDEM Zyklus "ABWEICHUNG", in dem sich der Spiegelstand
   aendert (die vier Indikator-Spuren hatten die kurze Fassung).
6. `Handel/befehle.py` -> `FAMILIE`: `"<spur>": "<Familie>"`. Die Familie ist die
   Gruppierung im Bericht (`/strategien`, `/lage`), nicht die Strategie-Klasse -
   eine neue Gattung (Beispiel: Preisaktion) bekommt eine eigene, keine
   Notzuordnung zu "Indikator".

**Die Testsuite ist die Pruefliste.**
`Agenten/Handel/tests/test_befehle.py::SpurenTest.test_jede_spur_hat_familie_und_leser`
faehrt `dauerlauf.SPUREN` ab und verlangt fuer JEDE Spur eine Familie und eine
Lesefunktion. Eine Spur, die in `dauerlauf.SPUREN` und im Tagesbericht steht,
aber in `FAMILIE` fehlt, macht die Suite rot - auch dann, wenn der Bericht sie
schon zeigt. Nach dem Anschliessen also `python -m unittest test_befehle`
mitfahren, nicht nur die Spurtests.

## Der Vertrag des Tagesberichts

`spur_<name>()` gibt ein dict zurueck; `baue()` liest daraus: `name`,
`waehrung`, `w`, `z`, `positionen`, `ordner`, `journal`, optional `stillgelegt`,
`papierfest`, `pruefmodul`.

Je Position liest `zeile_position()`: `name`, `einstieg`, `kurs`, `vh` (Bewegung
in Prozent, richtungsbewusst ueber `seite`), `wert`, `stop`, `ziel`, `seit`,
optional `hebel`.

`"pruefmodul": None` setzen, wenn die `wachen.json` der Spur **keine `freigabe`**
fuehrt: `baue()` ruft `wachenlage(s)` ausserhalb seines `try` auf - ein Fehler
dort bricht den GANZEN Bericht ab. Papierbuch-Spuren ohne fuenf Bedingungen
werden ohne Wachenblock gezeigt (Muster gitter).

## Der geteilte Leser muss beide Journal-Formen kennen

`scanner/wachen_pruefung.runden_aus_journal()` liest den Einsatz aus `usd`
(scanner, xperp, swap, kraken) **oder** `einsatz_usd` (Indikator-Spuren, spiegel,
omniquant). Symptom bei nur einer Form: `KeyError: 'usd'` - und zwar erst im
**ZWEITEN** Zyklus, weil der erste noch keine Runde hat. Ein gruener erster Lauf
beweist hier nichts. Erweitern immer additiv (erst die eine Spalte, dann die
andere), damit die alten Spuren unveraendert bleiben.

## Nachweis-Kette (in dieser Reihenfolge)

1. Tests je Spur mit dem **Aufruf aus ihrem Testkopf**: bei den Indikator-Spuren
   `cd <spur>/tests && ../../scanner/.venv/Scripts/python.exe -m unittest test_<spur>`;
   bei orbk `cd orbk && ../scanner/.venv/Scripts/python.exe -m unittest discover -s tests -t . -p "test_*.py"` (54 Tests).
2. Ein echter Papierzyklus je Spur von Hand (`handeln.py --papier`).
3. `scanner/.venv/Scripts/python.exe spiegelstand.py` -> jede Spur byte-gleich.
4. Warteschlangen-Probe VOR dem Neustart:
   `scanner/.venv/Scripts/python.exe ../Hermes/cache/dauerlauf_neustart_probe.py`
   -> 0 ungelesene Telegram-Nachrichten, fuer jede Spur `anfrage_offen=False`.
5. Neustart: alle PIDs der venv-Kette beenden, `Handel/dauerlauf.pid` loeschen,
   `Routinen/handel-dauerlauf.ps1` einmal starten (der Wrapper steigt bei
   lebender Sperre aus).
6. Der erste Zyklus muss **jede** Spur als "(papier) ok" listen (15.09.2026:
   15 Spuren in 2:26). Fehlt eine, laeuft noch der alte Code.
7. `Bus/journal/<datum>.jsonl`: je neuer Spur `handel/<spur>` mit `code: 0`.
8. `Routinen/systempruefung.ps1` -> Block 11 (Bedingung 4) und Block 12
   (Dauerlauf) gruen, "0 zu entscheiden".

## Fallen aus der Praxis

- **Eine waagerechte Zahl aus dem ZUSTAND schlaegt die `wachen.json`.** gitter:
  `wachen.json` sagt 6 Stufen, die laufende Leiter hat 12. Der Zustand ist die
  laufende Strategie - wer nur die wachen liest, bewertet eine andere.
- **Ein Suchmuster `"[a-z]+"` verliert Namen mit Unterstrich** (`macd_mtf` wird zu
  `macd`): echte Schluessel mit `[a-z_]+` bzw. `\w+` pruefen, sonst meldet eine
  Probe eine Spur als fehlend, die im Code steht.
- **CRLF in der Testausgabe:** `grep -E "^(Ran|OK)"` liefert scheinbar nichts,
  obwohl die Suite gruen ist. Immer den Exit-Code mitnehmen (`echo $?`).
- **Fehlender Duplikat-Schutz ist ein Risikofehler, kein Schoenheitsfehler.** Die
  vier Indikator-Spuren pruefen nicht, ob das Instrument schon gehalten wird -
  wavetrend hielt 2x BTC-USDT, also 10 USD Risiko in EINEM Instrument statt 5,
  entgegen seiner eigenen `_risiko_erklaerung`. Vor dem Anschliessen pruefen:
  `grep -c "gehalten" <spur>/handeln.py` (0 = fehlt).
- **Nach dem Neustart sagt die Systempruefung "erster Zyklus steht noch aus"**
  (Schonfrist-Fenster). Der Log ist die Wahrheit, nicht die Zeile.
- **Eine kranke Spur kostet den Zyklus Zeit** (600-s-Timeout je Unterprozess):
  Fehler sofort an der Logzeile der Spur ablesen, nicht am Ende des Zyklus.

## Verification

`scanner/.venv/Scripts/python.exe spiegelstand.py` meldet "N von N Spuren
byte-gleich", und im `dauerlauf.log` steht jede Spur des Takts als "(papier) ok".

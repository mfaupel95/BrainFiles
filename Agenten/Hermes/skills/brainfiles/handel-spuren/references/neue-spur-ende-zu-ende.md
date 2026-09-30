# Neue Spur von Null bis GUI — Ende-zu-Ende

Beweis der Schrittfolge: Omniquant-Papierspur, 13.09.2026 (abgebrochene
Aufgabe vom selben Tag verifiziert und in einer Sitzung komplett fertig -
Code, Verdrahtung, Tests, echter Lauf, Commit, Dauerlauf, GUI).

> Soll die Spur aus einer FREMDQUELLE entstehen (Video, Reel, Post oder Bild als
> Vorlage statt einer abgebrochenen Aufgabe), ist der Weg ein anderer und die
> Pruefregeln sind strenger: `references/strategie-aus-fremdquelle.md`.

## 0. Abgebrochene Aufgabe verifizieren — nichts annehmen
- `search_files("*<suchwort>*", BrainFiles-Wurzel)` → `total_count: 0`
  heisst: es existiert nichts; eine abgebrochene Sitzung hat oft nur
  gesucht und nichts geschrieben.
- `session_search` (Tool, per tool_search laden): Sitzung anhand von Datum/
  Uhrzeit finden; rekonstruieren, was sie WOLLTE und wo sie stoppte.
- Fruehere Leitlinien bewusst nachladen: `session_search` mit `window` um
  die alte Empfehlungs-Message (z. B. „kein externer Prognose-Feed“) — die
  Entscheidung von damals ist Vorgabe, nicht neu zu verhandeln.
- Befund explizit festhalten: „Sitzung hat NICHTS geschrieben — Aufgabe ist
  offen“ (danach richten sich alle weiteren Schritte; nichts Altes reparieren).

## 1. Vorbilder lesen, nicht erfinden
- `xperp/handeln.py`: handelnde Spur + Bus-main-Wrapper
  (`with ereignis.lauf("handel/<spur>")`, `main()` als Wrapper, Bus-Ordner
  auf `sys.path`).
- `spiegel/` + `spiegel.py`: reine Papierspur — `--vorschau` druckt die
  Sperrenzeile OHNE das Wort Freigabefenster, damit der Dauerlauf nie fragt.
- `dauerlauf.py`: SPUREN-Block (mit `"skript"`-Schluessel, wenn die
  Einstiegsdatei nicht `handeln.py` heisst) und der zyklus-Aufruf.
- `tagesbericht.py`: `spur_<name>()`-Muster (z. B. `spur_swap`, ~Z. 125-180)
  und das baue()-Tupel (~Z. 433-460).
- `Bus/handel_befehle.py`: SPUREN-Tupel + `status()` (liest feste
  Feldnamen: `positionen`, `seite`, `modus` — eigene Zustandsform an die
  Leser anpassen).
- Signalquelle REAL lesen (z. B. `prognose_berichte/neuester.json`): Felder
  und ob ein `richtung`-Feld existiert — ein altes Format liefert sonst
  still 0 Kandidaten.
- `.gitignore`: Whitelist-Muster der Nachbarspur nachziehen.

## 2. Bauen — drei Kerndateien
- `wachen.json`: harte Grenzen — Papierbuch, kein Orderpfad, keine externe
  API. Einzige Quelle von Grenzen; Laufzeitstand NICHT hierher.
- `handeln.py`: papierfest. `--live` verweigert mit einem Grund OHNE das Wort
  Freigabefenster. Test-Seams als Modulvariablen (`bericht_quelle`,
  `letzter_kurs_quelle`; None → echte Quelle). Kosten auf beiden Seiten,
  Zwangsschluss, Kill-Switch, Merkliste, die nur den HEUTIGEN Tag sperrt
  (ein Tor, das nie aufgeht, ist ein Fehler).
- `tests/test_<spur>.py`: nur ueber Seams, kein Netz, kein Orderpfad;
  `tearDown` setzt die Seams auf None zurueck. `HIER` im Testmodul =
  `dirname(dirname(abspath(__file__)))` (eine Ebene zu tief ist der
  Klassiker). JEDER Test steht auf Temp-Pfaden: alle Modul-Pfad-Variablen
  umbiegen (WACHEN/ZUSTAND/JOURNAL/VERFOLGTE/ABLEHNUNGEN) und im Wachen-
  Fixture `journal_zweitziel` auf den Temp-Ordner zeigen lassen. Besonders
  ein Test, der `lauf("live")` aufruft: der Lauf druckt die Verweigerung
  und bucht danach ALS PAPIERZYKLUS WEITER - ohne Temp-Pfade entsteht ein
  echter Lauf mit echtem Netz und echtem Q:\Ziel aus einem Unit-Test
  heraus (14.09.2026 passiert: 1283 Einlaufpositionen).

## 3. Verdrahten — jede Liste, die eine Spur nennt

> Fuer eine BESTEHENDE Spur, die nur noch angeschlossen werden muss (Code steht,
> keine Zeile neu), ist der eigene Weg kuerzer und nennt die Fallen, die der
> Neubau nicht hat: `references/spur-nachtraeglich-anschliessen.md`.

Die Listen liegen verstreut und werden von TESTS eingefordert — nicht durch
Nachsehen, sondern durch Laufen. Diese Tabelle ist die vollstaendige Fassung:

| Stelle | Was hinein gehoert | Wer es einfordert |
|---|---|---|
| `dauerlauf.SPUREN` | Ordner, `"waehrung"`, `"skript"` (falls nicht `handeln.py`), `"python"` (eigenes venv, Vorbild `nautilus`) | die Spur fehlt im `dauerlauf.log` |
| `lage.HOLER` | `spur_<name>()` ueber `_spur_indikator(...)`; `live_faehig=True`, wenn die Spur einen Live-Zweig HAT | `Handel/tests/test_lage.py::FormTest.test_holer_sind_vollzaehlig` |
| `Handel/befehle.py` → `FAMILIE` | Familienname (z. B. `"Feed-Kopie"`) — ohne ihn gruppiert der Bericht die Spur unter `"?"` | `Handel/tests/test_befehle.py::SpurenTest.test_jede_spur_hat_familie_und_leser` |
| `auswertung_alle` | `INDIKATOR_SPUREN` oder `BOT_SPUREN` — je nachdem, welche Journalform die Spur schreibt (Buch ueber `spur_buch` → `BOT_SPUREN`) | die Spur fehlt in der Auswertung |
| `pruefe_ratschen.py` | `("<spur>", "<ordner>", "scanner", "wachen_pruefung")`; der Betrag muss 1.0x Buchrisiko sein | `pruefe_ratschen.py` selbst (Zeile `1.0x?`) |
| `.gitignore` | Vier `!`-Zeilen (`*.py`, `*.md`, `wachen.json`, `tests/*.py`), dazu `zustand.json` und `handelsjournal.csv` als SPERRE | `git check-ignore -v` UND `git add --dry-run` |
| Spiegelung | `journal_zweitziel: Q:\\Handel_Journal\\<spur>` in der `wachen.json` | `spiegelstand.py` meldet byte-gleich |

- **Die Suiten sind der Pruefer, nicht das Auge.** Nach dem Verdrahten ZUERST
  `test_lage` und `test_befehle` fahren: sie nennen genau die vergessene Liste
  („jede Spur braucht eine Familie“). Der volle `Handel/tests`-Lauf kommt danach.
- **`Handel/befehle.py` ist der Ort, nicht `Bus/handel_befehle.py`.** Im
  Handel-Ordner liegen die Leser fuer `/status` und `/bericht`; Bus-Ordner und
  Handel-Ordner sind zwei Baeume, und ein Eintrag im falschen wird nie gelesen.
- **`tagesbericht` ist KEIN Pflichtschritt.** Der Bericht zieht die Spuren ueber
  `lage.HOLER`; einen eigenen `spur_<name>()` samt Baue-Tupel bekommt nur, wer
  einen eigenen Abschnitt braucht. Nicht annehmen — die neueste Nachbarspur
  nachsehen (`grep -rn "<nachbarspur>" Handel/tagesbericht.py`).
- **Eine frische Spur ohne Journal ist kein Betriebsfehler.** `auswertung_alle`
  unterscheidet „WARTET AUF DAS ERSTE SIGNAL“ (Zustand frisch) von „KEIN BUCH
  UND LAEUFT NICHT“.
- **Der Bus-Name steht WOERTLICH im Spur-Skript** (`ereignis.lauf("handel/<spur>")`),
  nicht abgeleitet: abgeleitet ist er nur so lange richtig, wie Ordner und
  Spurname gleich heissen. Spuren, die ihr Buch ueber `spur_buch` fuehren,
  oeffnen ihn dort; die Pruefung akzeptiert eine Kern-Bindung nur, wenn die
  gestartete Datei ihren EIGENEN Namen uebergibt.
- Nach dem SPUREN-Eintrag pruefen, dass `zyklus_spur` UND `nur_fenster_fehlt`
  das `python`-Feld respektieren (`d.get("python", PYTHON)`) - vergisst man
  die zweite Stelle, laeuft der Zyklus zwar, aber die Vorschau-Frage startet
  mit dem falschen Interpreter und die Spur wird nie gefragt.
- Vorher `.bak-JJJJMMTT` fuer JEDE anzufassende Datei (Stufe 1).
  Gegenprobe der Whitelist zweimal: `git check-ignore -v` (nennt die greifende
  Regel) UND `git add --dry-run <ordner>` (zeigt exakt, was in den Commit
  kaeme — Negationsregeln verwirren check-ignore).

## 4. Beweisen — Nachweis-Kette
- Alle Suiten: eigene Spur, Nachbarspuren (xperp, swap), `Handel/tests`,
  Bus-Ende-zu-Ende (`Agenten/Bus/tests/test_ende_zu_ende.py` endet mit
  „Ende-zu-Ende bestanden“).
- Echten Signal-Bericht erzeugen, wenn der vorhandene alt/formatfremd ist:
  `MAXHIRN_ROUTINE=1 scanner/.venv/Scripts/python.exe prognose.py
  --ohne-meldung` (schreibt Bericht, sendet nichts).
- ZWEI Papier-Zyklen: erster eroeffnet Einstiege, zweiter prueft den
  Ausstiegspfad (Merkliste verhindert Doppeleinstieg; Positionen bleiben).
- Bus-Journal: `grep '"wer": "handel/<spur>"' Agenten/Bus/journal/<JJJJ-MM-TT>.jsonl`
  → `start` UND `ende` mit `code: 0`.
- Filterprobe gegen die Dauerlauf-Stichwoerter (`verkauf`, `stop`, `KILL`,
  `gesperrt`, `ausstieg`): jede erwartete Meldungszeile nennt Instrument +
  Richtung, die Bestandszeile bleibt stumm (kein Spam). Reine Kopfroutinen
  (Python-Compare) reichen dafuer nicht — die Probenzeilen konkret
  durchjagen.
- Tagesbericht: Spur als papierfest, Positionen mit richtungsbewusstem
  Stop-Abstand (short liegt ueber dem Kurs — ohne Richtungsfaktor sieht
  jede gesunde short-Position wie gerissen aus).

## 5. Versionieren + Dauerlauf-Start
- Commit mit Nachweis-Liste in der Message (Testzahlen, echte Laeufe,
  Positionen), dann push. Eigenes SOFORT committen: was laenger als eine halbe
  Stunde offen im Baum liegt, zieht die Fremdarbeit-Routine unter fremdem Namen
  ein - und eine parallel laufende Sitzung kann eine Datei dabei auf einen
  aelteren Stand zuruecksetzen.
- Neustart des Dauerlaufs: das laufende venv-Paar beenden (ALLE PIDs der
  Kette, Startzeit/Eltern vorher pruefen — zwei gleiche Kommandozeilen sind
  ein Lauf). Beenden mit `Stop-Process -Id <pid> -Force` (nativ, je PID);
  `taskkill /T /F` aus einer PowerShell-Kette tut hier STILL NICHTS. Danach die
  Sperrdateien entfernen (`dauerlauf.pid`, `dauerlauf.mittel.pid`,
  `dauerlauf.hoch.pid` — der Wrapper raeumt nur eine VERWAISTE Sperre selbst auf).
- **ALLE Stufen neu starten, nicht nur die Basis.** `SPUREN` wird beim Start des
  Prozesses gelesen: Basis, mittel und hoch fahren dieselbe Liste und kennen die
  neue Spur sonst nicht. Je Stufe ein eigener Aufruf —
  `Agenten/Routinen/handel-dauerlauf.ps1`, `... -Risiko mittel`, `... -Risiko hoch`.
- **Die Wrapper blockieren laenger als ein Werkzeug-Timeout.** Drei Aufrufe
  hintereinander in EINEM Vordergrund-Aufruf reissen die Zeitgrenze; die
  ersten zwei Stufen laufen, die dritte startet nie, und der Auftrag sieht
  fertig aus. Die Stufen als Hintergrund-Aufrufe starten (oder je Stufe einen
  eigenen) und danach NACHZAEHLEN.
- Nachzaehlen ueber die Kommandozeile, nicht ueber den Programmnamen: je Stufe
  ein Paar (Startprogramm + Interpreter).

```
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -match 'dauerlauf\.py --takt' } |
  Select-Object ProcessId,@{n='risiko';e={($_.CommandLine -split '--risiko ')[1]}}
```

- Beleg im `dauerlauf.log` UND je Stufe im eigenen Log (`dauerlauf.mittel.log`,
  `dauerlauf.hoch.log`): der erste Zyklus muss JEDE Spur als „(papier) ok“
  listen — fehlt die neue Spur, lief noch der alte Code. (`grep -c "<spur>"`
  ueber alle drei Logs.)

## 6. GUI — rein lesend
- Tkinter, liest `zustand.json` + `neuester.json` + `handelsjournal.csv`;
  Kurse/Kerzen ueber `scanner/okx` in Hintergrund-Threads (Netz blockiert
  das Fenster nie), Refresh 15 s. Schreibt NICHTS — der Dauerlauf bleibt
  der einzige Schreiber.
- Chart ohne Zusatzpaket: Canvas + `okx.kerzen(inst, bar="1D", anzahl=90)`
  (aufsteigend, [ts,o,h,l,c,vol]); Einstiegs-/Stop-/Ziellinie farbig;
  Klick auf Tabellenzeile waehlt das Instrument.
- Zeile „letzte Schliessungen“: G/V aus `wert_usd`/`einsatz_usd` rechnen
  (das Journal hat KEIN gv-Feld; Einsatz leer = ueberspringen).
- Start-Fehler kennen: `from tkinter import ttk` ist noetig (`import
  tkinter as tk` reicht nicht); eine Builder-Methode hat nur `self.root` —
  ein blosses `root` ist ein NameError. Beide erscheinen erst beim ECHTEN
  Start (ein tk-Mock verdeckt sie) — nach jedem Umbau einen echten Start mit
  Fenster-Titel pruefen.
- Verifikation am FENSTER: GUI-Startprozesse sind venv-Paare; der
  PassThru-PID ist der Launcher mit leerer MainWindowTitle — den Titel auf
  dem KIND suchen. Das Screenshot-Tool kann „No windows found" melden,
  obwohl das Fenster im Bild steht: das BILD auswerten (`vision_analyze`),
  nicht die Fensterliste.
- stderr-Umleitung einer GUI nie per `Get-Content -Tail` lesen, solange der
  Prozess lebt (Datei offen → Aufruf haengt bis Timeout). Erst Leben pruefen;
  Log nur lesen, wenn der Prozess tot ist.

## Verifikation des Ganzen
Drei Belege in einem Atemzug: erster Zyklus im `dauerlauf.log` mit
„<spur> (papier) ok“, Bus-Journal `start`/`ende` mit `code: 0`, und das
GUI-Fenster mit korrektem Titel (Kind des venv-Paares).

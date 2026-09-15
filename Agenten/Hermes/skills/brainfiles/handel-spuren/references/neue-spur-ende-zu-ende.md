# Neue Spur von Null bis GUI — Ende-zu-Ende

Beweis der Schrittfolge: Omniquant-Papierspur, 13.09.2026 (abgebrochene
Aufgabe vom selben Tag verifiziert und in einer Sitzung komplett fertig -
Code, Verdrahtung, Tests, echter Lauf, Commit, Dauerlauf, GUI).

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

## 3. Verdrahten — fuenf Stellen, alle fuenf

> Fuer eine BESTEHENDE Spur, die nur noch angeschlossen werden muss (Code steht,
> keine Zeile neu), ist der eigene Weg kuerzer und nennt die Fallen, die der
> Neubau nicht hat: `references/spur-nachtraeglich-anschliessen.md`.
1. `dauerlauf.SPUREN` (mit `skript`-Schluessel, falls noetig; mit
   `"python"`-Schluessel, falls die Spur ein EIGENES venv braucht -
   Vorbild `nautilus`: nautilus_trader liegt nicht im scanner-venv)
2. `Bus/handel_befehle.SPUREN` (fuer `/status`)
3. `tagesbericht.spur_<name>()` UND der Eintrag im baue()-Tupel
4. `ereignis.lauf("handel/<spur>")` + `main()`-Wrapper im Spur-Skript
5. `.gitignore`-Whitelist (Quelldateien frei, `zustand.json`/Journal gesperrt
   — unten in der Sperrliste nachziehen; bei eigenem .git der Spur in deren
   EIGENER .gitignore)
Nach dem SPUREN-Eintrag pruefen, dass `zyklus_spur` UND `nur_fenster_fehlt`
das `python`-Feld respektieren (`d.get("python", PYTHON)`) - vergisst man
die zweite Stelle, laeuft der Zyklus zwar, aber die Vorschau-Frage startet
mit dem falschen Interpreter und die Spur wird nie gefragt.
Vorher `.bak-JJJJMMTT` fuer JEDE anzufassende Datei (Stufe 1).
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
  Positionen), dann push.
- Neustart des Dauerlaufs: das laufende venv-Paar beenden (ALLE PIDs der
  Kette, Startzeit/Eltern vorher pruefen — zwei gleiche Kommandozeilen sind
  ein Lauf), `dauerlauf.pid` entfernen (der Wrapper raeumt nur eine
  VERWAISTE Sperre selbst auf), dann EINMAL
  `Agenten/Routinen/handel-dauerlauf.ps1`.
- Beleg im `dauerlauf.log`: der erste Zyklus muss JEDE Spur als
  „(papier) ok“ listen — fehlt die neue Spur, lief noch der alte Code.

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

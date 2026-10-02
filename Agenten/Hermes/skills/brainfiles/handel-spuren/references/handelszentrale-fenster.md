# Handelszentrale: das Fenster ueber alle Spuren

Ausgelagert aus SKILL.md (02.10.2026) - dort steht nur noch der Anlass.
Gilt fuer: eine neue Spur, ein geaendertes Spurenbild, ein Fenster, das
beim Start oder in der Anzeige etwas tut, das niemand versteht.


- **Die zentrale Ansicht liest ihre Spurliste aus `dauerlauf.SPUREN`.** Eine
  zweite Liste in der GUI altert beim naechsten neuen Spurordner still.
- **Der eigene Modulname darf keinem Spurmodul gleichen.** `Handel/gui.py` hiess
  zuerst so — wie `omniquant/gui.py`. Mit `Handel/` auf `sys.path` fing der Import
  das fremde Fenster ab, fuenf Omniquant-Tests brachen mit `module 'gui' has no
  attribute 'fuss_texte'`: nicht kaputt, sondern gegen das falsche Modul gelaufen.
  Dieselbe Falle wie die zwei `auswertung.py`, nur ueber einen Ordner hinweg; ein
  Test haelt den Handel-Kopf frei von doppelten Modulnamen.
  **Wird dieser Test rot, weicht die JUENGERE Datei** - nicht die Spur: die
  Spurdatei hat mehr Aufrufer, eigene Tests und steht in Journalen, das
  Kopf-Werkzeug in zwei oder drei. Beleg: `Handel/historie.py` (Backtest-Daten)
  lag doppelt mit `xperp/historie.py` (`bot.py` und `stopwahl.py` holen sie per
  `import historie`); umbenannt wurde das Kopf-Modul zu `historie_binance.py`,
  mitgezogen in `replay.py`, `optimieren.py` und den Tests - xperp blieb
  unberuehrt. Nach dem Umbenennen gegenproben: kein Treffer mehr fuer
  `^import <alter name>` im eigenen Suchraum, und `git check-ignore -v` zeigt
  die neue Datei als NICHT ignoriert (sonst faellt die Freigabezeile der
  `historie.py` ins Leere und der Nachfolger ist in git unsichtbar).
- **Ein zentraler Leser muss ALLE Zustandsformen kennen, sonst zeigt er still
  null.** Je Spur ein Testfall in ihrer echten Schreibweise (`position` statt
  `positionen`, `richtung` statt `seite`, `preis_einstieg`/`stop_preis`,
  `symbol`+`kette` statt `inst`, `paar` statt `inst`, `usd`/`eur` statt `nominal`)
  plus eine Formpruefung gegen die echten Dateien: die Zahl der gelesenen
  Positionen muss der in `zustand.json` entsprechen. Ein falscher Feldname sieht
  nicht wie ein Fehler aus, sondern wie "0 Positionen".
  **Und zwar in der NORMALISIERTEN Form lesen:** `positionen_aus()` liefert
  `instrument` und `wert_usd`, die Rohfelder der Spur heissen `inst` und
  `nominal`. Wer `instrument_name(p)` auf das normalisierte Dict anwendet,
  bekommt eine Spalte voller Fragezeichen — kein Fehler, nur eine falsche
  Anzeige. Umgekehrt gilt: den Kursweg-Schluessel aus dem ROHEN Datensatz holen
  (`roh["inst"]`), nicht aus dem normalisierten.
- **Die Quellenzuordnung ist eine zweite Liste, die still altert.** Die
  Handelszentrale holt ihren Kursweg aus einem eigenen `QUELLE`-Dict (Spur ->
  okx/kraken/feed); fehlt die Spur darin, nimmt sie die VORGABE (okx) — die
  Anzeige behauptet eine falsche Boerse, der Chart holt Kerzen vom falschen Markt.
  Der Kursweg ist der GENERISCHE Schluessel aus `positionen_aus()` (`inst` ODER
  `paar` ODER `token`), nicht `roh["inst"]`: die Kraken-Spur schreibt `paar`, mit
  `roh["inst"]` stand dort `None` ("Quelle okx (None)", Chart ohne Kerzen, ohne
  Fehlermeldung). Beim Aufnehmen einer Spur BEIDE Stellen pruefen — `QUELLE` und
  Schluesselwahl — und danach `handelszentrale.py --pruefen` gegen die echte Datei
  laufen lassen: dort muss "Quelle <erwartet> (<paar>)" stehen.
- **Zeitstempel fremder Dateien: Zone und Form pruefen, nicht schneiden.**
  `dauerlauf.log` traegt LOKALE Zeit ohne Jahr (`13.09. 18:25:44`); gegen UTC
  gerechnet stand in der Kopfzeile "letzter Zyklus vor -120 min", waehrend der
  Dienst lief. In derselben Zone vergleichen, Jahr aus dem Bezug; ein Eintrag mehr
  als einen Tag in der Zukunft gehoert zum Vorjahr. `strptime("%d.%m.")` warnt
  seit Python 3.13 — von Hand parsen. Nicht jedes Journal hat eine Uhrzeit: die
  ORB-Spur schreibt `2026-09-13`, ein starres `zeit[11:16]` liest dort eine leere
  Spalte (Datum anzeigen, nicht "--:--"). **Und der Vergleichswert muss in
  dieselbe Zeitzonen-Welt gehoeren:** `alter_minuten()` erwartet ein aware
  `jetzt` (`datetime.now(UTC)`), weil die Spuren ihre Zeitstempel als UTC-ISO
  schreiben (`...+00:00`); ein naives `datetime.now()` laeuft in `TypeError:
  can't subtract offset-naive and offset-aware datetimes` — und zwar erst im
  Fenster, wenn der Test mit naiven Werten arbeitet.
- **Nebenlaeufigkeit deckeln: ein Kurs-Worker gleichzeitig.** Die Feed-Kurse
  (Spiegel) laufen ueber ein CLI und brauchen Sekunden; ohne Sperre stapeln sich
  die Threads im Viertelminutentakt, das Fenster lebt von Altantworten. Kurse und
  Kerzen nur ueber Queues ins Widget, nie aus dem Thread heraus.
- **Der Autostart laeuft ueber die Aufgabenplanung, nicht ueber den
  Startup-Ordner:** `Routinen/handelszentrale.ps1` (Bus-angebunden, Waechter ueber
  den Fenstertitel) + `Routinen/handelszentrale-aufgabe.ps1` (legt
  `MaxHirn-Handelszentrale` an, erhoehte PowerShell noetig). Ein von einem Skript
  gestartetes Fenster hat kein Vordergrundrecht und sieht aus wie „weg" —
  Gegenmittel ist `nach_vorn()` im Programm, nicht im Starter.
- **Ein Leseprogramm wird per AST geprueft, nicht per Stichwort.** Verboten:
  `open` mit w/a/x/+, `json.dump`, `csv.writer`, `os.remove/rename/replace`,
  `import subprocess` — dazu ein Laufzeittest, der Groesse und mtime ALLER
  Spurdateien vor und nach einem vollen Leselauf vergleicht. Gegenstueck zum
  spiegel-Test (verbietet `subprocess` im Quelltext).
- **Ein echter Fensteraufbau gehoert in die Suite.** Ein tk-Mock verdeckt genau
  die zwei Startfehler (fehlendes `from tkinter import ttk`, ein `root` in einer
  Builder-Methode, die nur `self.root` kennt): `root.withdraw()`, Fenster bauen,
  `root.update()`, Tabellenzeilen gegen die gelesenen Positionen pruefen — deckt
  beides ab, ohne Bildschirm.
- **Den Fensterinhalt beweist man aus den Widgets, nicht per Foto.** Fenster
  in-process bauen (`root.withdraw()`), `root.update()`, Inhalt lesen: Titel,
  Tabellenzeilen (`t_pos.get_children()` + `item(..., "values")`), Konsolentext,
  Fusszeile — und die Chartflaeche per `canvas.postscript()` auf
  Zeichenoperationen pruefen (Vorbild
  `Agenten/Hermes/cache/hz_fensterpruefung.py`). Kommt eine Bildschirmaufnahme
  einfarbig zurueck, ist der Desktop nicht abgreifbar: dann ist die Widget-Ausgabe
  der Nachweis, nicht das Foto. Ein Startbefehl ueber `Start-Process`/`cmd start`
  kehrt erst zurueck, wenn das Kind den Ausgabekanal schliesst — erst den
  Fenstertitel pruefen.
- **Persistierte Windows-Terminal-Layouts sind ein zweiter, unsichtbarer Starter.**
  `%LOCALAPPDATA%\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\state.json`
  speichert unter `persistedWindowLayouts` ALLE offenen Fenster mit ihrer
  Kommandozeile, sobald WT mit `firstWindowPreference: persistedWindowLayout`
  laeuft. Jedes Layout mit `python.exe gui.py` / `handelszentrale.py` und falschem
  WorkingDirectory (Repo-Wurzel statt `Agenten/Handel`) baut bei JEDEM WT-Start
  ein Fehlerfenster auf (`can't open file ...\BrainFiles\handelszentrale.py`,
  Exit 2) — ein Fenster, das 'immer wieder aufspringt', ohne Task oder Autostart.
  Am 14.09.2026: 10 von 12 gespeicherten Layouts liefen die venv-python aus der
  falschen Wurzel (eines davon `prognose.py --kurz`, das den OKX-Transportfehler
  1/6-Spam erzeugte). Gegenmittel: WT schliessen, kaputte Layouts aus
  `state.json` entfernen (nur die ohne `python.exe` behalten), WT neu starten.
  `powershell -File handelszentrale.ps1` haengt an der Konsole, weil pythonw die
  Ausgabekanaele erbt — erst den FENSTERTITEL pruefen. Einen veralteten
  GUI-Prozess (Startzeit VOR dem letzten Datei-Mtime) per `Stop-Process` beenden
  und den Wrapper laufen lassen: er startet den aktuellen Code neu und schreibt
  das fehler.log frisch.
- **Der Autostart gehoert in `Routinen/`, nicht in den Startup-Ordner.**
  `Routinen/handelszentrale.ps1` startet das Fenster bei der Anmeldung (+2 Min),
  wenn keines offen ist; `Routinen/handelszentrale-aufgabe.ps1` legt die Aufgabe
  an (erhoehte PowerShell noetig, der Wrapper laeuft auch ohne). Der Waechter
  prueft den FENSTERTITEL, keine PID-Datei — so zaehlt auch ein von Hand
  gestartetes Fenster, und ein Absturz hinterlaesst keine Sperre. Gestartet wird
  `pythonw.exe` (kein Konsolenfenster), Aufbau-Fehler nach
  `Routinen/logs/handelszentrale-fehler.log`. Regeln fuer Starter-Routinen
  (Bus-Anbindung, Abnahme ueber die Aufgabenplanung, Zeile in
  `Wissen/Routinen.md` erst wenn die Aufgabe steht): Skill `bus-integration`.
- **Eine neue Spur in den BESTEHENDEN Fenstern** (sie erscheint in der
  Handelszentrale von selbst, braucht aber einen eigenen Reiter, wenn ein
  gleichnamiger Fremdlauf schon einen hat; dazu der Startbefehl in der
  Werkzeug-Zentrale samt Logbeleg): `references/neue-spur-ende-zu-ende.md`,
  Abschnitt 7.


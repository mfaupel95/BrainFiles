# Eine Spur in GUI und UI bringen (Handelszentrale + Werkzeug-Zentrale)

Ausloeser: "pack das in die GUI/UI", "die Spur sehe ich nirgends", "mach das
sichtbar". Zwei Fenster sind gemeint - und beide haben eine eigene Liste, die
still altert.

## Handelszentrale (`Agenten/Handel/handelszentrale.py`)

* **Die Spurenliste kommt aus `dauerlauf.SPUREN`** - eine neue Spur erscheint
dort von selbst. Pruefen mit
  `./scanner/.venv/Scripts/python.exe handelszentrale.py --pruefen` (rein
  lesend, ohne Fenster): listet die Spuren und je Spur `Quelle <erwartet> (<paar>)`.
* **Es gibt Reiter je Fremdquelle** (`_baue_freqtrade`, `_baue_omnitrade`). Sie
  zeigen die FREMDAKTEN (Statusdatei, Bot-API). Traegt die Haus-Spur denselben
  Namen wie der Fremdlauf, gehoert die Spur als EIGENE, BESCHRIFTETE Sektion in
  denselben Reiter - sonst liest man eine Zahl und weiss nicht, welche der
  beiden gemeint ist.
* **Reine Funktionen zuerst, Fenster danach.** Aufbereitung ohne tk bauen
  (`omnitrade_spur_kopf(zustand, wachen, jetzt=None)`, `..._positionen(spur,
  zustand, wachen)`, `..._journal(pfad, grenze=6)`), damit sie ohne Bildschirm
  pruefbar sind. Das Fenster ruft nur noch diese Funktionen.
* **Was die Kopfzeile sagen muss:** Modus (Papier/Live), belegte Plaetze,
  Alter des letzten Zyklus, Boerse/Quote und der Live-Stand aus der wachen
  (`handel_erlaubt` + `freigabe.erfuellt`). Ein Zyklus aelter als
  `herzschlag_max_minuten` bekommt ein Warnzeichen - das ist der EINZIGE
  Zustand, der hier eine Warnung verdient. Eine Anzeige, die den Schalter
  verschweigt, liest sich wie ein handelnder Automat.
* **Die Journal-Tabelle braucht eine Modus-Spalte** (papier/live) - sie ist die
  interessante Spalte, und `journal_ereignisse()` traegt sie nicht. Eigenes
  Lesen mit `csv.DictReader` ist hier richtig.
* **`QUELLE` ist eine zweite Liste** (Spur -> okx/kraken/feed) fuer den
  Kursweg. Fehlt die Spur, nimmt die Zentrale die VORGABE (okx) und behauptet
  eine falsche Boerse. Bei `kraken` liest sie den Kursnamen aus
  `wachen["instrumente"][inst]["kraken"]` - fehlt dieser Block, ist der
  OKX-Weg in der Schreibweise der Instrumente die richtige Wahl (dokumentieren,
  nicht raten).

### Testmuster (beides noetig)

```
cd Agenten/Handel/tests && <absoluter-python> -m unittest test_handelszentrale_omnitrade -v
```

* Reine Funktionen: Kopfzeilen (Papier/scharf/alter Herzschlag/leerer Stand),
  Positionsaufbereitung, Journallesen (neueste zuerst, Modus, fehlende Datei).
* **Echter Fensteraufbau**, weil ein tk-Mock genau die zwei Startfehler verdeckt:
  `root = gui.tk.Tk()`, `root.withdraw()`, `gui.Handelszentrale(root)`,
  `root.update()`, dann die Widgets pruefen (`app.l_omni_spur.cget("text")`,
  `app.t_omni_pos`, `app.t_omni_journal`, Reiternamen ueber
  `app.reiter.tab(i, "text")`), `finally: root.destroy()`. Ohne Bildschirm
  `skipTest`.
* Die Nachbarsuiten mitlaufen lassen: `test_handelszentrale_rein_lesend`
  (AST-Pruefung: kein Schreiben), `..._bindung`, `..._freqtrade`,
  `..._als_rahmen`.

## Werkzeug-Zentrale (`Agenten/Werkzeuge/repos-zentrale`)

* **Startbefehl in `fuellen.py`**, Dict `SPUREN_START`
  (`name: ("handeln.py", HANDEL_PYTHON)`), fuer Sonderfaelle `SPUREN_START.update`.
  Der Eintrag erzeugt die Zeile in `KURATIERT` mit
  `[python, skript, "--vorschau"]` - Start ist IMMER `--vorschau`.
* Schreiben: `../../Handel/scanner/.venv/Scripts/python.exe fuellen.py --anwenden`
  (Trockenlauf ohne `--anwenden` zeigt `+ [handel] <spur> Spur START ...`).
  `--auffrischen` traegt nur Felder BESTEHENDER Eintraege nach.
* **Belegpflicht:** `test_manifest_gegenprobe.test_jeder_startbefehl_hat_einen_beleg_im_log`
  verlangt einen Loglauf in `logs/`. Erzeugen mit `fuellen.py --belege` (fuehrt
  nur Befehle OHNE Log aus) - danach erscheint `logs/<spur>-<zeit>.log`.
  Die Logs sind bewusst NICHT versioniert: der Beleg ist ein lokaler Zustand.
* Gegenprobe: `repos_zentrale.py --pruefen` muss die Spur mit
  `start: ..\scanner\.venv\Scripts\python.exe handeln.py --vorschau` zeigen;
  vorher steht dort `start: -` und `! HANDEL/<spur>: kein Eintrag im Manifest`.
* Ganze Suite: `python -m unittest discover -s tests -p "test_*.py"` (~296 Tests,
  ~2 min).

## Fenster starten und pruefen

```
cd Agenten/Handel && (scanner/.venv/Scripts/pythonw.exe handelszentrale.py &)
```

Nach ~12 s den Prozess ueber den FENSTERTITEL pruefen (nicht ueber die PID):
`Get-Process pythonw | Where-Object { $_.MainWindowTitle }`. Der Titel nennt die
Spurenzahl (`Handelszentrale - N Spuren (Papier, nur lesend)`) - **diese Zahl ist
der schnellste Gegenbeweis fuer eine falsche Zahl in der Doku.**

## Fallen

* **Der Reiter ist gebaut, aber leer:** die Sektion liest `zustand.json` der
  Spur, nicht die Fremd-Statusdatei. Beides im Reiter getrennt beschriften.
* **Ein Reiter, der einen Ausfall verschweigt:** fehlt der Spur-Zustand, muss die
  Kopfzeile "noch kein Zyklus" sagen, nicht eine Null zeigen.
* **Zahlen in Doku und Titel vergleichen** - die Doku wurde in dieser Sitzung mit
  "40 Spuren" gefuehrt, waehrend `len(dauerlauf.SPUREN)` 39 ergab. Messen, dann
  schreiben.

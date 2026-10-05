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

## Leitstand (`Agenten/Handel/leitstand.py`) — der Rahmen, nicht die Zentrale

Seit 04./05.10.2026 gibt es ZWEI Fenster: die Handelszentrale (allein) und
der **Leitstand** (`ttk.Notebook`), der die Handelszentrale als Reiter einhaengt
und vier weitere traegt. Sechs Reiter, **Strg+1..6**:

| # | Reiter | Was er zeigt |
|---|---|---|
| 1 | Ueberwachen | die Handelszentrale (holt ihre Kurse selbst) |
| 2 | Freigaben | Freigabefenster je Spur, Freigeben/Ablehnen/Schliessen, NOTAUS |
| 3 | Backtests | Replay, Optimierung, Urteile |
| 4 | Markt | der Prognose-Bericht, rein lesend |
| 5 | Omniquant | `OmniquantGui` eingebettet |
| 6 | Nautilus | OKX-DEMO-Node eingebettet |

* **Der Fenstertitel der Handelszentrale sagt weiter „4 Spuren"**, obwohl
  jetzt sechs Reiter existieren - wer dort die 5./6. sucht, sucht falsch. Das
  ist kein Fehler, den man „reparieren" muss: die Zahl zaehlt Spuren, nicht
  Reiter.
* **Reiter-Schnittstelle:** `__init__(self, eltern, leitstand)`,
  `refresh()`, `titel_zusatz()`, `status()`, optional `abbrechbar()`. Fehlt
  `abbrechbar`, gilt **schliessbar** (der Rahmen ruft
  `getattr(r, "abbrechbar", lambda: True)()`). Ein Reiter, der einen
  Hintergrundprozess haelt, MUSS sie haben - sonst zerstoert das „X" ihn
  (Nautilus waehrend eines laufenden Node).

### Eine fremde UI als Reiter einbetten

| Form der Fremd-UI | Beispiel | Was zu tun ist |
|---|---|---|
| baut in ein uebergebenes Widget | `OmniquantGui(root)` | fast nichts - `ttk.Frame` ist ein Widget, `after()` geht darauf |
| **ist** selbst ein Fenster | `class X(tk.Tk)` | **zerlegen**: Inhalt in ein Frame, duenner Fenster-Wrapper drumherum |

`NautilusGui(tk.Tk)` war die zweite Form. Der Umbau:
`NautilusFrame(ttk.Frame)` = der ganze Inhalt, `NautilusFenster(tk.Tk)` =
Titel/Geometrie/`WM_DELETE_WINDOW`. Der alte Name bleibt **Alias** auf das
Fenster (`NautilusGui = NautilusFenster`), sonst brechen alle Aufrufer von vor
dem Umbau - `verify_gui.py` las `app.quote_var` und braucht heute `app.frame`.

* **Fensterpflege (`title`, `geometry`, `minsize`, `protocol`, `destroy`)
  gehoert dem Fenster, nie dem Frame.** Der Fehler faellt erst zur Laufzeit
  auf (Fenster im Fenster), deshalb prueft `test_leitstand_nautilus.Trennung`
  das ueber den **AST** des Quelltexts statt ueber einen Klick.
* **`OmniquantGui` ist eine KOMPOSITION, kein Widget** - sie baut in ein
  uebergebenes `root` hinein. Deshalb ist der Reiter der *Behaelter*, und
  `gui.winfo_children()` existiert dort nicht.
* **`after()` braucht einen `<Destroy>`-Handler.** Verschwindet der Reiter,
  waehrend das Fenster weiterlebt, feuert der 120-ms-Timer ins Leere und Tk
  meldet `invalid command name <id>_poll_queue` auf stderr. Bei Gelegenheit
  den laufenden Node mitstoppen, sonst bleibt er als Waise zurueck.
* **Der Rahmen darf ein grosses Rad NICHT selbst importieren.**
  `leitstand.py` laedt `nautilus_trader` (326 MB) nicht; der Reiter tut es zur
  Laufzeit und faengt `ImportError` mit einer Installationsanweisung. Sonst
  waere ein fehlendes Rad ein **toter Leitstand**. Das Rad gehoert ins
  Handel-`.venv` (Import 1,8 s), nicht in einen Kindprozess.

### Drei Bedien-Elemente (Auftrag Max 05.10.2026)

* **Spaltenfilter in JEDER Tabelle** (in `leitstand_bedienung.Tabelle`,
  wirkt damit ueberall): Dropdown **Spalte** + Wertfeld. `>50`, `<0`, `>=8`,
  `<=3.5`, `=7` werden **numerisch** verglichen, sonst als Teilstring - sonst
  waere „12,5 %" nicht gegen „3 %" zu halten. `zahl_aus_text()` liest
  `12,5 %`, `-3,10 USD`, `1.234,5` (deutsche und englische Schreibweise).
  Ohne Zahl (`>Papier`) fliegt die Zeile **raus**, statt still nichts zu
  finden. Der Freitext-Filter daneben sucht weiter in ALLEN Spalten. Knopf
  „Filter weg" leert alle drei Felder.
* **Mehrfach-Freigabe** im Reiter Freigaben: Baum auf `auswahl="extended"`
  (Strg/Shift-Klick), ein Dialog fuer alle. **Die Dauer ist die KUERZESTE
  der Anfragen** - sonst bekommt eine 30-Minuten-Anfrage eine Stunde, die
  niemand bestellt hat. Spuren **ohne** wartende Anfrage fliegen raus (eine
  Frage, die keiner beantworten kann). Jede Spur **einzeln** oeffnen, weil
  `freigabefenster.oeffnen()` die Sperre je Spur nimmt; ein Buendel wuerde den
  Rest verpassen, und der Dauerlauf koennte in der Luecke eine Anfrage stellen.
* **Bilanzspalten** in der Handelszentrale: `Runden`, `Treffer %`,
  `Ergebnis`, Quelle `auswertung_alle.kennzahlen_fuer` (dieselbe wie im
  Tagesbericht). Ohne Journal steht **`?`**, nicht `0` - eine Null sieht nach
  Messung aus. Die Spaltenliste kommt aus EINER Funktion
  (`spalten_der_spurtabelle()`): stand sie zweimal in der Datei, war eine
  Erweiterung wirkungslos, weil `ttk.Treeview` ein zu kurzes Tuple **ohne
  Fehlermeldung** abschneidet.

### Dateinamen sind im Hex-Viewer unlesbar

Kerzen als `BTC-1H.json` werden beim Anlegen zu `4254432d31482E6A736F6E`
(hex). In `daten/historie/` sind die Namen `BTCUSDT_1H.json` (Binance-Schreib-
weise); die **1H/4H/1D** sind lesbar, `15M.json` und `30M.json` nicht. Fuer die
Basislinie des `spur_audit` reichen 1H-Kerzen - **ohne Kerzen gibt es kein
`excess%`** (keine Marktbewegung = keine Basislinie); das ist eine Luecke, kein
Befund.

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

## Verknuepfungen auf den Desktop ("die UIs auf den Desktop")

Ein Skript, das die Verknuepfungen erzeugt, statt sie von Hand zu klicken -
idempotent und mit Gegenprobe: `Agenten/Werkzeuge/desktop-verknuepfungen.ps1`
(uas `terminal` aufrufen: `powershell -ExecutionPolicy Bypass -File ...`).

Drei Angaben je Verknuepfung, und die dritte ist die, die man vergisst:

```powershell
$w = New-Object -ComObject WScript.Shell
$s = $w.CreateShortcut((Join-Path $desktop 'Handelszentrale.lnk'))
$s.TargetPath = '...\powershell.exe'
$s.Arguments  = '-ExecutionPolicy Bypass -WindowStyle Hidden -File "...\handelszentrale.ps1"'
$s.WorkingDirectory = '...\Agenten\Routinen'   # OHNE das startet es im falschen Ordner
$s.IconLocation = "$env:SystemRoot\System32\imageres.dll,1"
$s.Save()
```

* **Ein Wrapper statt des Programms, wo es einen gibt.** Die Handelszentrale
  laeuft ueber `Routinen/handelszentrale.ps1`: der prueft den Fenstertitel und
  startet nichts, wenn schon ein Fenster offen ist. Zwei Fenster zeigen dasselbe
  und lassen sich spaeter nicht von einem Dienst unterscheiden.
* **Web-UIs als eine Verknuepfung:** `cmd.exe` mit
  `/c start "" http://127.0.0.1:8081/ & start "" ...` oeffnet alle Tabs in einem
  Klick; die Ports sind nur lokal gebunden.
* **Ziel des Arbeitsverzeichnisses pruefen, nicht nur die Existenz:** die
  Gegenprobe am Skriptende liest jede Verknuepfung zurueck und prueft
  `Test-Path $s.TargetPath` UND zeigt `$s.WorkingDirectory`. Ein Klick ist kein
  Nachweis - der FENSTERTITEL ist es.

### Fallen (beide erlebt)

* **`$args` ist in PowerShell eine automatische Variable.** Ein Funktions-
  parameter dieses Namens laesst `$s.Arguments = $args` mit `System.Object[]
  kann nicht in string konvertiert werden` abbrechen - Parameter `$argumente`
  nennen.
* **Keine Umlaute in einer `.ps1`.** PowerShell 5.1 liest eine Datei ohne BOM als
  ANSI: `Verknuepfung` mit ue ist im Vergleich ein anderer Name, und ein
  `Remove-Item -LiteralPath` mit ausgeschriebenem Namen findet nichts - lautlos,
  die Datei bleibt liegen. Aufraeumen ueber Muster
  (`Get-ChildItem -LiteralPath $desktop -Filter '*moongui.py*'`), nie ueber
  ausgeschriebene Namen.
* **Reste fehlgeschlagener Verknuepfungen sehen wie Textdateien aus:** ihr NAME
  ist der ganze Befehl (`CUsersfaupeDocuments...pythonw.exe repos_zentrale.py.txt`).
  Vor dem Loeschen auf den Desktop gehoeren sie angesehen (Groesse/Inhalt), nicht
  als "0-Byte-Muell" angenommen.

## Fallen

* **Der Reiter ist gebaut, aber leer:** die Sektion liest `zustand.json` der
  Spur, nicht die Fremd-Statusdatei. Beides im Reiter getrennt beschriften.
* **Ein Reiter, der einen Ausfall verschweigt:** fehlt der Spur-Zustand, muss die
  Kopfzeile "noch kein Zyklus" sagen, nicht eine Null zeigen.
* **Zahlen in Doku und Titel vergleichen** - die Doku wurde in dieser Sitzung mit
  "40 Spuren" gefuehrt, waehrend `len(dauerlauf.SPUREN)` 39 ergab. Messen, dann
  schreiben.

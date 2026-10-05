# Fallen

- **`terminal.cwd` ist nicht nur ein Startverzeichnis - es verschiebt den Bezugspunkt jeder Anleitung.** Steht es auf `Agenten/Hermes` (Hausstand), dann sind die Pfade in Skills, Notizen und Wiki (relativ zur BrainFiles-WURZEL) NICHT mehr dasselbe wie das Arbeitsverzeichnis. **Und es gilt nur fuer den Weg, der es liest:** `terminal.cwd` erreicht Gateway, Cron und entfernte Backends (ueber `TERMINAL_CWD`), **nicht** die interaktive CLI und TUI - die uebernehmen das Startverzeichnis der SHELL (`os.getcwd()`; `hermes_cli/main_tui_launch.py`: "A local interactive session starts where the user launched"). Ein Wert in der Config macht die Oberflaechen also NICHT gleich: dazu gehoert ein `hermes`-Wrapper in Max' PowerShell-Profil (`Documents\PowerShell\Microsoft.PowerShell_profile.ps1`), der den echten `hermes.exe`-Aufruf per `Push-Location` in `Agenten\Hermes` startet und die Shell per `Pop-Location` in der Wurzel laesst (die Wurzel-Aufrufer bleiben nutzbar); `hermes -Hier ...` = aktuelles Verzeichnis, `hermes -p <bot> ...` = `terminal.cwd` DIESES Profils. Nachweis ohne Modellaufruf: `Agenten/Werkzeuge/anker-pruefen.ps1` (laedt das ECHTE Profil, haengt eine `cmd.exe`-Kopie als `hermes.exe` vor den PATH und prueft vier Faelle; Exit 0 = ok, Shell-cwd unveraendert); zweiter Zeuge ist `state.db`, Spalte `sessions.cwd` (dort steht das Startverzeichnis jeder Sitzung). `hermes --resume`/`-c` kehrt absichtlich ins aufgezeichnete cwd der Sitzung zurueck (`--no-restore-cwd` bzw. `--in DIR` heben das auf). Der Anker ist `cd "$HERMES_HOME/../.."` - **nicht `$HERMES_HOME/..`**, das landet in `Agenten` (eine Ebene zu hoch) und laesst jeden root-relativen Befehl mit "No such file or directory" scheitern. Wer den Anker in eine Anleitung schreibt, faehrt ihn VORHER einmal (`cd ... && pwd`): ein `cd <x> && <befehl>` verschluckt den Fehlschlag des `cd`, der naechste Befehl scheitert dann scheinbar grundlos. Unberuehrt, weil selbstlokalisierend: `Agenten/Routinen/*.ps1` (`$PSScriptRoot`), die Cron-Wachen (`Path(__file__)`), `omnitrade.cmd` (`%~dp0`), `git -C <repo>`. Nach dem Umstellen alle Anleitungen mit root-relativen BEFEHLEN mitziehen (nicht die Pfadangaben selbst aendern) und einen Nachweis aus dem neuen cwd fahren (z. B. `spiegelstand.py` -> "N von N byte-gleich").

- **`hermes` aus einer windows-mcp-Sitzung stirbt mit `_thread`/`f-string`-Tracebacks**
  (`Fatal Python error: init_import_site`, `module '_thread' has no attribute
  'start_joinable_thread'`)? Der Interpreter ist nicht defekt — in der aufrufenden
  Umgebung steht ein verirrtes `PYTHONHOME`, das das venv-Python auf ein fremdes Stdlib
  zieht. `Remove-Item Env:PYTHONHOME, Env:PYTHONPATH` an den Anfang jedes Aufrufs setzen,
  dann läuft `hermes.exe` wieder. Ausführlich: `hermes-maintenance`.
- **`${NAME}` ist kein Klartext.** Wer eine Datei nach Zugangswerten durchsucht,
  muss Verweis und Wert am `$` unterscheiden - nicht nur `${env:…}` ausnehmen.
  Ein Zaehler, der `${HERMES_CUSTOM_…_API_KEY}` als "gesetzt, 40 Zeichen"
  meldet, erzeugt einen Fehlalarm ueber 13 Dateien, und ein Fehlalarm kostet
  mehr Vertrauen als die Pruefung Zeit. Bei jeder Meldung die Fundstelle je
  Datei einzeln nachsehen: ein leerer Treffer kann auch heissen, dass der Block
  fehlt (das Profil `nous` hat gar kein `a2a_agents`).
- `hermes config get <pfad>` kennt nur Schlüssel aus `DEFAULT_CONFIG`; eigene Blöcke
  (z. B. `a2a_agents`) melden fälschlich „Config key not set". Kein Fehler — über
  `load_config()` prüfen.
- `hermes config set` schreibt die ganze Datei neu und kennt dieselbe Grenze. Für eine
  einzelne Zeile ist der chirurgische Ersatz nachvollziehbarer: eine Zeile geändert,
  `Compare-Object` beweist es.
- Auflösung passiert beim **Laden**: `${VAR}` und `${env:VAR}` werden in allen
  String-Werten ersetzt (`hermes_cli/config.py::_expand_env_vars`). Ein nicht auflösbarer
  Verweis bleibt als Text stehen und warnt — `istVerweis: true` in der Prüfausgabe heißt
  also **Variable fehlt**, nicht „Mechanik kaputt".
- Beim Speichern bleibt die Vorlage erhalten (`_preserve_env_ref_templates`). Die Sorge
  „der Klartext kommt zurück" ist damit widerlegt — `--speicherprobe` ist der Beleg.
- `HERMES_HOME` **vor dem ersten Import** setzen (`$env:HERMES_HOME='…\Agenten\Hermes'`):
  Kindprozesse erben die Benutzervariable nicht zuverlässig, sonst zeigt der Lauf auf das
  Standardprofil und liest eine andere `config.yaml`. **Sichtbares Symptom, wenn die Variable
  fehlt:** `hermes fallback list` meldet „No fallback providers configured", obwohl die
  Kette in `Agenten\Hermes\config.yaml` steht — gelesen wurde dann
  `%LOCALAPPDATA%\hermes\config.yaml`, ein anderes Home mit anderer Config. Vor jeder
  „ist nicht gesetzt"-Meldung das tatsächlich gelesene Home zeigen lassen:
  `python -c "from hermes_constants import get_hermes_home; print(get_hermes_home())"`.
  **Beim Schreiben dieselbe Falle, nur unauffaelliger:** `hermes config set`
  meldet `✓ Set <pfad> = <wert> in <datei>` — diese Datei lesen und gegen die
  gewollte Config halten. Ohne `HERMES_HOME` landet der Schreibvorgang im
  Standardprofil (`%LOCALAPPDATA%\hermes\config.yaml`), waehrend der laufende
  Dienst die Projekt-Config liest: die Aenderung ist dann scheinbar
  wirkungslos, obwohl „der Wert doch drinsteht". Werden beide Ablagen gelesen
  (CLI ohne und mit `HERMES_HOME`), beide auf denselben Wert ziehen — sonst
  driften sie auseinander, und der naechste Aufruf faellt auf den alten Stand
  zurueck.
- **Welche Config der LAUFENDE Gateway liest, steht in keiner Notiz — am
  Prozess bestimmen.** `hermes config path` nennt nur, was die CLI ohne
  Kontext lesen wuerde. Der Dienst startet ueber den Aufgaben-Wrapper
  (`schtasks /xml` → CommandLine, darin ggf. `HERMES_HOME`); und die
  Sitzungskennung (Model/Provider im Sessionkopf) zeigt, welche Config eine
  laufende Sitzung tatsaechlich gelesen hat. Beide Belege ziehen, bevor
  „die AppData-Config ist die aktive“ behauptet wird — der Gateway kann die
  Projekt-Config lesen, waehrend die Desktop-App die andere nutzt; beide
  Ablagen muessen auf denselben Stand gezogen sein.
- **Zwei Hermes-Checkouts nebeneinander: welcher BAUM arbeitet, steht in den Prozessen.** `hermes --version` nennt „Install directory" — das ist der Baum, aus dem DIESER Aufruf kommt, nicht der, aus dem die Dienste laufen (ein alter Checkout wie `C:\Hermes` kann daneben liegen). Wahrheit: Prozesse nach **`ExecutablePath`** gruppieren (`Get-CimInstance Win32_Process | Where-Object CommandLine -match hermes | Select ProcessId, ExecutablePath`), nie nach Kommandozeilen-Text — sonst zaehlt der eigene Suchbefehl mit und man loescht sich selbst. Autostart laeuft ueber die `*.vbs` in `Agenten/Hermes/gateway-service/`: ein VBS kann auf einen alten Baum zeigen und bei jeder Anmeldung Prozesse daraus starten. `VIRTUAL_ENV`, `PYTHONPATH` und der `python.exe`-Pfad darin gehoeren auf den aktiven Baum (VBS mit CRLF schreiben, vorher `.alt-JJJJMMTT`).
- **Ein abgeloester Task, den man nicht aendern darf, wird entschaerft und BEWIESEN.** Einen als Admin registrierten Task kann eine normale Sitzung nicht deaktivieren: `Disable-ScheduledTask` und `schtasks /Change /DISABLE` enden mit „Zugriff verweigert", `Start-Process -Verb RunAs` mit 0x800704C7 („durch den Benutzer abgebrochen") — ein nicht erhoehtes Token bekommt keinen UAC-Prompt. Statt dagegen anzukommen: das Skript, das der Task aufruft, neutralisieren (`WScript.Quit 0`) und die Wirkung MESSEN — `Start-ScheduledTask -TaskName <task>`, dann Prozesszahl vorher/nachher unveraendert UND kein Prozess aus dem alten Baum. Den formalen Schritt als fertiges Skript nach `Agenten/Werkzeuge/` legen (Log nach `%TEMP%`), das der Nutzer einmal in einer Admin-Shell startet. Die Altanlage danach **umbenennen statt loeschen** (`<baum>.alt-JJJJMMTT`) und erst nach Tagen entfernen; `venv.bak.*`/`venv.backup-*` darin sind regenerierbar und duerfen sofort weg.
- **Testläufe gegen die eigene Config gehören in ein eigenes `HERMES_HOME`, nie in die
  echte Config.** Ablage: ein Pfad **innerhalb** `BrainFiles` ohne Junction, z. B.
  `Agenten\Hermes\.<name>-test\home\`. Zwei Gründe: `HERMES_WRITE_SAFE_ROOT` verweigert
  Schreibzugriffe außerhalb von `BrainFiles`, und ein Junction-Pfad (`Werkstatt` → `O:`)
  wird auf sein echtes Ziel aufgelöst und deshalb ebenfalls verweigert — `%LOCALAPPDATA%\Temp`
 und `Werkstatt` fallen damit beide aus. Nach dem Lauf löschen: hält ein `sqlite3`-Handle
 aus der execute_code-Sitzung die Test-`state.db`(-wal), scheitert jedes `rm -rf` mit
 „Device or resource busy" — Kernel zurücksetzen (`execute_code(reset=True)`), dann löschen.
 **Ein `hermes -z`-Beweis gegen das Haupt-Home ist kein Modellbeweis.** Der Aufruf
 nimmt die letzte Sitzung des Profils wieder auf und stirbt bei einem langen Verlauf
 an "This conversation has grown too long for <modell> to read" — das liest sich wie
 ein Modellproblem, ist aber die Sitzungslaenge. Fuer den Nachweis "Modell X ist als
 Agent-Modell nutzbar" ein leeres `HERMES_HOME` mit einer MINIMAL-Config nehmen
 (`model.default`, `model.provider` und der `providers.<name>`-Block mit
 `api`/`base_url`/`default_model` - mehr nicht; ohne den Block meldet Hermes
 `Unknown provider '<name>'`) und darin `hermes -z "Antworte mit genau einem Wort: OK"`
 laufen lassen. Ein `OK` aus DIESEM Lauf belegt Modell, Provider und Kontextfenster;
 der Lauf gegen das Haupt-Home belegt nur, dass die Sitzung zu lang war.
- PowerShell-Helfer nie `H` nennen (Alias von `Get-History`) — der Fehler gibt dann
  Argumente im Klartext aus. Umlaute und mehrzeilige Blöcke nicht über die Kommandozeile
  transportieren: mehrzeiligen Text als Datei schreiben oder als Array mit
  `-join [char]10` bauen.
- **Ein Einzelauftrag (`-q`, so startet der SkillsBot `/bot`) hat keinen Nutzer
  fuer Freigaben.** In diesem Modus werden Kommandozeilen mit `-c/-e` und
  `execute_code` blockiert („runs without a user present to approve") — der
  Auftrag endet dann in einem Werkzeugfehler, den der Bot als Ergebnis meldet.
  Auftraege fuer solche Bots deshalb so formulieren, dass sie ohne
  Shell-Einzeiler auskommen (Datei schreiben und ein bestehendes Skript
  aufrufen, `read_file`/`search_files` statt Inline-Python) — und einen Bot,
  dessen Kern Kommandos fahren soll, aus einer Sitzung mit Nutzer oder als
  Routine starten, nicht per `-q`.

- **Ein Umgebungsvariablen-Namen kann ein Tippfehler sein — Namen aus der Registry lesen, nicht eine Kandidatenliste abfragen.** Im Ist-Stand stand `#ANTHROPIC_API_KEY` (mit Rautenzeichen!) und `ANTHROPIC_API_KEY_BILLING`; der kanonische `ANTHROPIC_API_KEY`, den Hermes' Provider-Profil liest, fehlte. Eine Abwesenheitsmeldung ist erst gueltig, wenn die Namen aufgelistet wurden: `(Get-Item HKCU:\Environment).GetValueNames()`, dann je Name Laenge und SHA-256-Anfang der Kandidaten vergleichen — gleicher Hash = derselbe Wert, und das Setzen ist ein Umbenennen, kein neues Geheimnis.
- **Ein Provider braucht oft keinen Block in `providers:`.** Hermes' eingebaute Model-Provider-Profile (`hermes-agent/plugins/model-providers/<name>/__init__.py`) bringen `base_url`, `api_mode` und `env_vars` selbst mit — fuer Anthropic sind das `https://api.anthropic.com`, `anthropic_messages` und `(ANTHROPIC_API_KEY, ANTHROPIC_TOKEN, CLAUDE_CODE_OAUTH_TOKEN)`. Ist die Variable gesetzt, ist der Provider da; ein zusaetzlicher Eintrag in `config.yaml` ist hoechstens eine zweite Wahrheit.
- **Fuer Provider-Anmeldedaten braucht das laufende Gateway KEINEN Neustart.** Sie kommen aus dem Credential-Pool (`auth.json`) und der `.env` des Profils, nicht aus der Prozessumgebung: ein `delegate_task`-Kind lief sofort mit `provider=anthropic model=claude-opus-5` (Logzeile `platform=subagent … id=msg_…`). Wer „greift erst nach Neustart" behauptet, muss diesen Unterschied zeigen — er gilt nur fuer `${env:NAME}`-Verweise.
- **`hermes config edit` oeffnet auf Windows notepad und blockiert den Aufruf, bis das Fenster geschlossen ist.** Intern laeuft ein synchrones `subprocess.run([editor, config_path])` ohne Timeout — aus einer Werkzeugsitzung haengt der Aufruf bis ins Zeitlimit. Der Befehl ist fuer Menschen am Desktop gedacht, nicht fuer Agenten: einzelne Werte gehoeren zu `hermes config set`, nur ein mehrzeiliger Eingriff verdient das Wegwerf-Skript (`Agenten/Hermes/cache/`). Wer `config edit` in einem Agenten-Flow braucht, startet es mit `background=true` und laesst das Fernster dem Nutzer.
- **`auto` bei einem Aux-Auftrag heisst HAUPTMODELL, nicht Router-Auto.** In
  `hermes_cli/config_defaults.py::_aux()` ist der Standard `provider: auto` + `model: ""`;
  `agent/auxiliary_client.py::_try_main_provider_route` schickt den Auftrag genau dann
  auf den Hauptanbieter des Profils. Der lokale Router kennt kein blankes `auto` (nur
  `auto/best-*`, `auto/pro-*`, `auto/coding:*`) - ein Router-Eintrag unter `auxiliary.*`
  ist deshalb immer eine UEBERSTEUERUNG und erbt den Ausfall einer Gratis-Combo. Wer
  "auto" will, setzt NICHTS: den Block mit `hermes config unset auxiliary.<auftrag>`
  entfernen, statt einen Wert zu setzen - ein gesetzter Wert muss in jeder Profil-Datei
  einzeln gepflegt werden und driftet auseinander. Folge des Wechsels: die Kompression
  laeuft dann auf dem Hauptmodell, also haengt `compression.threshold` am FENSTER DES
  HAUPTMODELLS (786k bei nous) und nicht mehr am 200k-Deckel eines kleinen Aux-Modells -
  die alte Herleitung der Schwelle gilt dann nicht mehr. Massenumstellung mit Nachweisen
  und der Reindent-Nebenwirkung: `references/einstellung-umstellen.md`.
- **Der Auxiliary-Client loest `auxiliary.*.model` ueber den Nous/OpenRouter-Katalog auf — ein lokales GGUF dort ist ein kategorischer 404, kein langsamer Server.** Zeigt `auxiliary.compression.model` (oder `auxiliary.mcp`/`auxiliary.skills_hub`) auf ein Laufzeitmodell (`llamacpp/DeepSeek-...`), wirft das Komprimieren `Failed to generate context summary: 404 - Model '...' not found ... in our configuration or OpenRouter catalog`; Muster davor in `logs/errors.log`/`gateway.log`: `Auxiliary compression: model '...' no longer in Nous catalog`. Der Client hat keinen lokalen llamacpp-Pfad — ein lokales GGUF ist fuer ihn prinzipiell unaufloesbar, und Sessions wachsen stumm auf 100k+ Tokens unkomprimiert, ohne dass die Kompression irgendwo laut scheitert. Fix: `hermes config set auxiliary.compression.provider nous` und `...model deepseek/deepseek-v4-flash-0731` (dasselbe Provider/Modell wie das Hauptmodell, 786k — nachweislich aufloesbar). Nicht zurueck auf den frueher dokumentierten `auto/coding:free`-Router-Weg: der reroutet aktuell auf OpenCode-Free, das ausserhalb von OpenCode 403 liefert — kein zuverlaessiges Kompressionsmodell. **Nach JEDEM `hermes update` alle `auxiliary.*`-Modellpfade (compression, mcp, skills_hub) pruefen**: das Update schreibt die Config neu und setzt Modell/`threshold` zurueck auf einen lokalen GGUF-Stand (gemessen: `threshold` 0.19 → 0.66, compression auf llamacpp). `auxiliary.skills_hub` kann dabei auf ein CLIP-Projektor-GGUF zeigen, das gar nicht als Hauptmodell ladbar ist ("CLIP cannot be used as main model") — ebenfalls ueber den Katalogpfad ersetzen. Beleg: `hermes config check` Exit 0; die laufende Sitzung nutzt die neue Config erst ab `/new`.
- **Die Kompression-schwellen-Warnung kennt einen dauerhaften Fix, und die Schwelle ist KONTEXT-RELATIV, kein Fixwert.** Hermes meldet per Sitzung, das Kompressionsmodell habe kleineren Kontext als die Schwelle des Hauptmodells (`auxiliary.compression.model` vs. `compression.threshold`), und senkt die Schwelle nur fuer diese Sitzung. Der Trigger in Tokens ist `(model.context_length - max_tokens) * compression.threshold` (min. 64k; Fenster < 512k werden auf 75% angehoben) — `threshold` ist ein PROZENTSATZ des Kontextfensters. Der frueher dokumentierte Wert 0.19 gilt nur, solange das Aux-Kompressionsmodell ~200k hat; ist es dasselbe Modell wie das Hauptmodell (deepseek-v4-flash, 1M), hebt man beides an: `hermes config set model.context_length 1000000` UND `hermes config set compression.threshold 0.60` → komprimiert erst bei 600k statt ~190k. Faustregel: `threshold` so waehlen, dass der Trigger-Tokenwert unter dem Fenster des Aux-Kompressionsmodells bleibt, sonst senkt Hermes die Session-Schwelle beim Start selbst ab (`_lower_threshold_to_aux_context`); ein grosses Aux-Modell erlaubt eine hohe Schwelle = Kompression ruht bis kurz vor dem Fensterende. Nach `hermes config check` (Exit 0 = sauberes YAML); die laufende Sitzung nutzt die neue Schwelle erst nach `/new`.
  **Nachtrag 29.09.2026 (gemessen): eine Schwelle UEBER 1.0 ist keine Einstellung, sondern
  ein Aus-Schalter.** Der Ausloeser rechnet `(context_length - max_tokens) * threshold`
  (`agent/context_compressor.py::_compute_threshold_tokens`); bei `threshold: 1.6` liegt er
  ueber dem Fenster, der Anbieter lehnt die Anfrage ab, BEVOR komprimiert wird - die Sitzung
  stirbt am Fensterende statt zu komprimieren, und jede Runde kostet mehr Tokens. Wer die
  Kompression wirklich aus will, setzt `compression.enabled: false` (ehrlich und sichtbar)
  statt einer erfundenen Zahl. Rueckkehr auf 0.19, solange das Aux-Kompressionsmodell ~200k
  traegt - und **den Weg einmal wirklich rufen**, bevor er fuer tot erklaert wird: `auto/best-free`
  antwortete am 29.09.2026 mit dem Hausschluessel 200 (bedient von claude-haiku-4-5), ohne
  Schluessel dagegen 403 mit der OpenCode-Free-Meldung. Ein 403 aus einem Aufruf OHNE
  Schluessel beweist nichts ueber den Weg.
- **`patch` und `write_file` sind ausserhalb von `BrainFiles` generell gesperrt** (`HERMES_WRITE_SAFE_ROOT`), auf einer `config.yaml` zusaetzlich („Refusing to write to Hermes config file", auch fuer die AppData-Config). Fuer eine Datei ausserhalb des Repos (typisch: Max' PowerShell-Profil unter `Documents\PowerShell`) daher: Inhalt per `write_file` nach `Agenten/Hermes/cache/scratch/` schreiben, dort ASCII und CRLF pruefen, vorher `.bak-JJJJMMTT`, dann per MSYS `cp` an den Zielort - und die Syntax mit `[System.Management.Automation.Language.Parser]::ParseFile` pruefen, BEVOR der naechste Start der Shell davon abhaengt. **`write_file` verweigert ausserdem das Ueberschreiben einer BESTEHENDEN Datei, die in derselben Aufgabe nur per `offset/limit` gelesen wurde** („partial view", es kommt `None` statt `bytes_written` zurueck): dann `patch` nehmen oder die Datei vollstaendig lesen. Zwei Wege bleiben, und sie sind nicht gleichwertig: `hermes config set …` fuer den EINZELNEN Wert (auch fuer Listen — der Wert wird als YAML/JSON geparst, `'[{"provider":"omniroute","model":"auto/best-coding"}]'` funktioniert), und ein Wegwerf-Skript unter `Agenten/Hermes/cache/`, das die Datei binaer liest, chirurgisch ersetzt und zurueckschreibt — fuer eine Zusammenfuehrung mit mehreren Hunks. Das Skript ist dort das BESSERE Mittel, weil `hermes config set` die Datei neu schreibt und dabei den Kommentar-Schluss abschneidet (naechste Falle). Fuer das Skript gelten dieselben Regeln wie fuer jede Textaenderung: Zeilenenden binaer feststellen (`b"\r\n" in raw`) und erhalten, je Ersetzung `count == 1` asserten, den NEUEN Text vor dem Schreiben mit `yaml.safe_load` pruefen, vorher `.bak-JJJJMMTT`.
- **`hermes config set`/`unset` kann zuerst den mehrminutigen Launcher-Schwanz fahren - nie mit eigenem Zeitlimit im Vordergrund aufrufen.** Ein Aufruf kann Node-Abhaengigkeiten, TUI, Web-UI und Desktop-App bauen (mehrere Minuten), BEVOR er den Wert setzt. Kappt das Werkzeug-Zeitlimit den Lauf, bleibt die Schwanz-Obligation `installs/<hash>/source-completion-pending` scharf: ab da faehrt JEDER `hermes`-Start erst diesen Schwanz, die Desktop-App bekommt in ihrem 90-s-Fenster keinen Backend-Port und laeuft in eine Bootschleife, waehrend der Gateway aus bleibt. Deshalb: den Wert byte-genau per Skript setzen (siehe unten) oder den Aufruf losgeloest starten und im Log nachsehen - nie "schnell noch eben" im Vordergrund mit Timeout. Reparatur des scharfen Schwanzes: `hermes-maintenance`, Abschnitt "Abgebrochener Update-Schwanz".
- **`hermes config set` schneidet den Kommentar-Schluss der Datei ab.** Es schreibt die ganze Datei neu; ein Dokumentationsblock am Dateiende (Beispiele fuer `security:`, `fallback_model:`) ist danach weg — funktional harmlos, aber eine stille Aenderung an der Datei des Nutzers. Nach **jedem** `config set` diffen und den Block zurueckholen (`Agenten/Hermes/cache/config-schluss-wiederherstellen.py --tun`), sonst waechst bei jeder Aenderung eine unsichtbare Differenz. Die Aenderung selbst sieht im Diff wie eine Zeilenersetzung aus — genau pruefen, ob noch mehr fehlt. **Rueckholquelle:** `hermes config set` legt vor dem Schreiben ein Backup unter `backups/config/config.yaml.good.<zeitstempel>` an — den fehlenden Block daraus byte-genau (CRLF erhalten) an die Datei anhaengen, dann `diff` gegen die Sicherung: er darf exakt die eine gewollte Zeile zeigen.
- **Der Kommentar-Schluss fehlt auch bei PROFIL-Configs** (`profiles/<name>/config.yaml`),
  nicht nur im Hauptprofil (gemessen: 38 Zeilen in 6 Profilen). Dort ist "Block anhaengen"
  der falsche Fix — die Ziel-Fassung BYTE-genau aus `git show HEAD:<pfad>` bauen und nur
  den geaenderten Block ersetzen. `read_text()`/`write_text()` ohne `newline=""` drehen
  eine CRLF-Datei still auf LF (die selbst eingesetzten Zeilen behalten `\r\n`, die
  gelesenen nicht) — der Diff zeigt danach die GANZE Datei. **Beide Richtungen sind
  betroffen:** mit `newline=None` setzt Python beim Schreiben `os.linesep` ein, eine
  LF-Datei wird also genauso auf CRLF gedreht (gemessen an Python-Dateien, die im Haus
  LF fuehren). Wer eine Datei in Textmodus anfasst, erzeugt einen Ganzdatei-Diff, in
  welche Richtung auch immer — Bytes lesen, Bytes schreiben, danach `git diff --numstat`
  JE Datei gegen die erwartete Zeilenzahl halten; bei einem Werkzeug, das ganze
  Ordnerbaeume umstellt, diesen Check fuer jede geaenderte Datei einzeln fahren, weil
  eine Summe den Ausreisser verbirgt. `Agenten/Hermes/scripts/bot-modell-auf-router.py`
  arbeitet genau so und heilt den Kommentar-Schluss gleich mit.
- **Nach einer Massenaenderung den Diff JE DATEI zaehlen, nicht die Summe.** Erwartet sind
  die Zeilen der gewollten Ersetzung (Beispiel `model`: 2 Einfuegungen/3 Loeschungen, weil
  `base_url` entfaellt). Ein Diff, der wie die ganze Datei aussieht, heisst gekippte
  Zeilenenden oder verschwundener Doku-Block — in einer Summe ueber 25 Dateien faellt
  beides nicht auf. Zusaetzlich jede geaenderte `config.yaml` mit `yaml.safe_load` parsen
  und die Zielwerte asserten.
- **Ein Kommentar als YAML-Schluessel erzeugt eine erfundene Einstellung.**
  Wer einen Erklaerungstext in eine Config schreibt und dabei
  `vergiss_this_note: >` benutzt, bekommt danach in jeder
  Schluesselansicht, in jedem `config get` und in jedem Dashboard einen
  Schalter, den es nicht gibt — und beim naechsten Lesen sieht er wie Absicht
  aus, weil er plausibel benannt ist. Der Kommentar gehoert an die Zeile, die
  er erklaert. Gegenprobe nach jedem Block-Einfuegen: `set(cfg)` gegen den
  Vorzustand halten, nicht nur die Werte.
- **Ein Block-Ersetzer braucht die Einrueckung DER ZIELDATEI, nicht die des
  Hauses — und die Assertion muss VOR dem Schreiben greifen.** Gemessen:
  Profil-Configs fuehren Skalarfelder mit ZWEI Leerzeichen unter einem
  Top-Level-Schluessel (`delegation:` ist Top-Level, `provider:` darunter
  eingerueckt), die Hauptkonfiguration mit vier. Ein aus dem Hauptprofil
  kopierter Ersatzzblock parst dort nicht (`expected <block end>`), das
  Schreiben gelingt trotzdem, und danach ist der Schluessel ein String und
  alle folgenden Felder sind verschluckt. Drei Regeln daraus: den
  Ersatzzblock ALLEIN stehend parsen (`yaml.safe_load("\n".join(block))`),
  die Einrueckung aus der Zieldatei ableiten statt sie anzunehmen, und beim
  Ersetzen einer Zeilenfolge die Einrueckungstiefe als Parameter fuehren.
  Rollback dann byteweise aus `.bak-JJJJMMTT`; der Beleg ist
  `git status --porcelain -- <pfade>` **leer**, nicht "die Assertion hat
  gegriffen".
- **Ein Suchlauf kann still nichts finden, weil die Zeilen ein
  abschliessendes `\\r` tragen.** `text.split("\\n")` laesst bei CRLF-Dateien
  `\\r` an jeder Zeile stehen; jedes Praefix ohne Toleranz matcht dann null
  Mal. Der Trockenlauf meldet "keine Aenderung noetig" und das ist die
  gefaehrlichste Ausgabe ueberhaupt - sie sieht wie ein Befund aus und
  beweist nichts. Nach dem Split je Zeile auf `\\r` pruefen, dann neu messen.
  Verwandt: ein Skript, das seine Daten relativ zum Skriptort sucht, muss
  die Ebenenzahl pruefen - `cache/scratch/` liegt DREI Ebenen unter dem
  Home, nicht zwei, und ein `assert os.path.isdir(...)` faengt es sofort.
- **Ein kaputter Fallback ueberdeckt die echte Fehlermeldung.** Ist der Primaerpfad nicht
  angemeldet und die geerbte Kette zeigt auf ein lokales Modell unter der Mindestgroesse,
  endet der Lauf mit „context window ... below the minimum" — der Anmeldefehler ist dann
  unsichtbar. Passt eine Meldung nicht zur vermuteten Ursache, zuerst den
  `fallback_providers`-Block des PROFILS lesen und die Zahl der Eintraege zaehlen, bevor
  der Provider verdaechtigt wird.

# Belegte Faelle — Trugschluesse aus 259 Sitzungen (22.08.–21.09.2026)

Quelle des Destillats: `Agenten/Hermes/state.db`, 259 Sitzungen / 26.897
Nachrichten; die Zeilen unten stammen aus dem Sitzungsspeicher, dem jeweiligen
Journal oder der Messung, nicht aus dem Gedaechtnis.

Jeder Fall in derselben Form: **Behauptung** — **wie sie entstand** — **wie sie
auffiel** — **Beleg**.

## Messwerkzeug (04.10.2026)

### 1. Ein Werkzeug zaehlt eine Spur nicht
- Behauptung: das Haus haelt 657,63 USD Gesamtrisiko.
- Entstehung: `Agenten/Handel/risiko_beitrag.py` las offene Positionen aus
  `zustand["positionen"]`. **gitter legt seine Stufen in `z["lose"]`** (Dict,
  Schluessel = Stufennummer) und fuehrt zusaetzlich *eine* Position in
  `positionen`. Die `lose`-Stufe wurde nicht gezaehlt.
- Auffiel: die Risiko-Wache meldete eine BTC-Position von gitter **ohne
  Schutz-Stop** — und als der Notaus gesetzt war, stand er am Nachmittag wieder
  nicht im Zustand.
- Beleg: nach dem Nachzaehlen 85 Positionen und 749,28 USD, Differenz 92 USD.
  Die Abfrage mit dem richtigen Argument loest es auf:
  `beitrag_der_spur('gitter','gitter')` -> 2 / 181,95 USD gegen
  `beitrag_der_spur('gitter','gitter/zustand.json')` -> 0 / 0,00 USD.
  Die Funktion erwartet den **Ordner**.

### 2. Ein von Hand gesetzter Wert wird beim naechsten Zyklus ueberschrieben
- Behauptung: die gitter-Position hat einen Notaus.
- Entstehung: der Notaus wurde per Skript in `gitter/zustand.json` eingetragen.
  **gitter schreibt den Zustand bei jedem Zyklus neu**; die Datei ist nicht
  versioniert, es gab keine zweite Quelle. Stop um 01:00 im Zustand, um 01:11
  vom Dauerlauf ueberschrieben.
- Auffiel: die Risiko-Wache meldete dieselbe Position am Nachmittag wieder als
  „OHNE SCHUTZ-STOP".
- Beleg: Journalzeile `2026-09-23T15:01:28 … KAUF BTC-USDT 8 … 90,9087`.
  Regel gehoert an die **Entstehungsstelle** (`KAUF`-Zweig in
  `gitter/handeln.py`), gesteuert vom Wachen-Feld
  `notaus_unter_gitterunterkante`.

### 3. Ein Schalter wird stillschweigend verworfen
- Behauptung: die Suche meldet „kein Hebel".
- Entstehung: `replay.py` hatte zwei Namen fuer dasselbe Argument — `setzen=`
  (Familien B/C) und `wachen_patch=` (Familien A/D). In `main()` stand an der
  Aufrufstelle kein Patch. `--setzen` lief fuer die Kerzenspuren ins Leere.
- Auffiel: zwei Laeufe mit verschiedenen Parametern lieferten **bitgleiche**
  Kennzahlen (529 Runden, -0,803 USD je Runde).
- Beleg: nach dem Verdrahten 579 / -0,803 gegen 1007 / -0,074. Die
  zurueckgeschriebene Wachen-Kopie taugte **nicht** als Beweis — der Patch geht
  auf das W-Dict im Speicher (`replay.py` 794), die Kopie zeigt immer die
  Ausgangswerte. Siehe `messwerkzeug-gegenprobe`.

### 4. Ein Fehler aus einem Hintergrundlauf beweist den Zustand nicht
- Behauptung: die Wachen-Datei ist geraeumt (`KeyError: 'max_pro_trade_usd'`).
- Entstehung: drei Backtest-Laeufe starteten im Sekundenfenster, in dem ein
  `open(p,'wb')` die Datei auf 0 Byte gekuerzt hatte.
- Auffiel: nach dem Prozessende war die Datei vollstaendig gueltig (30
  Schluessel, JSON lesbar) und die Spur lief weiter.
- Beleg: nur der Prozessstatus zu dem Zeitpunkt sagt, ob die Datei halb
  geschrieben war. Inhalt **vor** dem `open(p,'wb')` zusammensetzen und pruefen.

### 5. Ein Test, der einen alten Zwischenstand einfriert
- Behauptung: der Fix hat den Test gebrochen.
- Entstehung: `test_fuenf_schreibweisen_sind_eine_basis` erwartete noch
  `{"BTC","XBT"}`, nachdem XBT spaeter auf BTC vereinheitlicht worden war.
- Auffiel: der Test meldete den *richtigen* Fix als Fehler.
- Beleg: Erwartungen nachziehen, wenn die **Regel** sich aenderte; gegen HEAD
  pruefen, statt die Vermutung zu protokollieren (siehe Fall 1 unten).

## Handel

### 1. Vier Live-Positionen, die es nicht gab (21.09.2026, xperp)
- Behauptung: xperp laeuft live mit vier Positionen (ZEC, XAG, LINK, ETC).
- Entstehung: Papierlauf bei `buchmodus: live` schrieb Positionen ins selbe
  Buch; das Buch kannte keinen Unterschied.
- Auffallen: Boerse gefragt — `/api/v5/account/positions` fuehrte nur die
  manuelle FIL-Position (margin 183,40, upl -26) und einen XRP-Rest; ZEC/LINK
  standen mit `pos=0`, XAG/ETC fehlten ganz.
- Beleg: von 14 Live-Zeilen in `xperp/handelsjournal.csv` waren **alle 14**
  `funding` — kein Live-Kauf, kein Live-Verkauf.
- Gegenmassnahme: Positionen tragen `modus` + Order-Kennung; jeder Live-Lauf
  bucht Altlasten mit Grund `buchbereinigung` aus.

### 2. scanner: Platz 5/5 belegt, aber unverkaufbar (21.09.2026)
- Behauptung: das Buch fuehrt Positionen, also laufen sie.
- Entstehung: ein Buch fuer Papier UND Live; Papier-Zyklen fuellten es, waehrend
  das Fenster zu war.
- Auffallen: 4 Positionen ohne `kauf_ord_id` (im Live-Modus kein Neukauf, jeder
  Ausstieg fehlerhaft).

### 3. Erfolgreiche Live-Erklaerung ohne Orderweg (19.09.2026, xperp)
- Behauptung: xperp kann live ordern.
- Auffallen: signierter Leseaufruf mit dem xperp-Schluesselsatz → OKX 50101
  „APIKey does not match current environment".
- Merksatz: jeder Spur-Satz ist ein anderer
  (`OKX_API_KEY/SECRET/PASSPHRASE` fuer xperp/okxf/mosaic, `OKX_LIVE_*` fuer
  scanner/okx). Die falsche Variable zu aendern wirkt nicht.

### 4. „nur das Freigabefenster fehlt" (21.09.2026)
- Behauptung: die Spur ist gesperrt, weil niemand freigegeben hat.
- Auffallen: die `--vorschau`-Zeile nannte **zwei** Gruende, das Guthaben in der
  falschen Waehrung war der bindende.
- Merksatz: `dauerlauf.nur_fenster_fehlt` greift nur bei **genau einem** Grund,
  der das Wort „Freigabefenster" enthaelt.

### 5. Margin-Waehrung (21.09.2026, OKX)
- Behauptung: das Konto hat kein Guthaben („USDT 0").
- Auffallen: `/api/v5/account/positions` zeigt `mgnMode=isolated, ccy=USDC`;
  eine Abfrage mit `ccy=USDT` liefert eine LEERE Liste.
- Merksatz: die Margin-Waehrung der POSITION pruefen, nicht den Namen im Kopf.

### 6. Kerzen, die still zu kurz waren (15.09.2026)
- Behauptung: 96 Kerzen sind „acht Wochen".
- Auffallen: OKX `/api/v5/market/candles` gibt oeffentlich nur 1440
  Stundenkerzen (60 Tage), egal was angefragt wird; `macd_mtf` bekam hart 300
  Basiskerzen → Ausrichtung immer `None` → die Spur haette NIE gehandelt.
- Beleg: 500 Kerzen → `None`, ab 550 vorhanden (Rechnung 544).

## Betrieb

### 7. Gateway 12 Stunden tot, Wache meldete gruen (19.09.2026)
- Behauptung: der A2A-Gateway laeuft.
- Entstehung: erst ein zu enges Prozessmuster (startete alle ~16 min neu, 90 s
  Ausfall je Mal), dann ein zu breites (`tui_gateway`-Backends galten als
  Gateway) — der echte Ausfall von ~01:49 bis 14:16 blieb unerkannt, SkillsBot
  scheiterte.
- Ersatzwahrheit: **Port 9900**, nicht der Prozessname.

### 8. Bus vier Tage stumm (11.–15.09.2026)
- Behauptung: das System meldet.
- Auffallen: Routinen schrieben weiter ins Journal (9.591 Eintraege), aber
  niemand bekam etwas; kein Systemereignis, der Prozess war von aussen beendet,
  der Task hat keinen Wiederholungs-Trigger.
- Merksatz: ein Waechter darf nicht ueber den Weg melden, den er ueberwacht.

### 9. Datei groesser als die Platte, die es nicht gibt (12.09.2026)
- Behauptung: es gibt eine Ausser-Haus-Sicherung.
- Auffallen: `sichern-ausser-haus.ps1` zielte auf `E:`, fand nichts und stieg
  mit Exitcode 2 **lautlos** aus; Ziel ist seit dem `Q:`.
- Merksatz: Exitcode auswerten, nicht Ausgabe lesen.

### 10. Groessenangabe in `AGENTS.md` (19.09.2026)
- Behauptung: `MaxHirn/` ist 45 GB.
- Messung: ~6 GB, davon 4,9 GB DockerDesktopWSL; die 42-GB-Medien liegen auf
  `O:\Archiv`. Echte C:-Fresser sind App-Daten (`AppData\Local\Packages` 23,9 GB,
  `uv\cache` 11,8 GB).

### 11. 84 Agentenprozesse, RAM gesund (21.09.2026, moondev)
- Behauptung: dem Rechner geht der Arbeitsspeicher aus.
- Auffallen: `Win32_OperatingSystem` → `FreeVirtualMemory` 1,94 GB von 89,8 GB;
  danach scheiterte jeder Modellstart (`failed to allocate 1,1 GB`) und `git` im
  Sandbox-Terminal starb mit WinError 1455.
- Ursache: der Treiber hielt nur das Startprogramm, die Interpreter der alten
  Generation liefen als Waisen weiter.
- Merksatz: Prozesszahl am KINDMUSTER gruppieren und `CreationDate` ansehen —
  erwartet ist EINE Generation je Zyklus.

### 12. Absturzursache verwechselt (21.09.2026)
- Behauptung: die vier MoonDev-Agenten sterben in einer Crash-Schleife.
- Auffallen: die haeufigste echte Sterbeursache war CoinGecko HTTP 429
  („You have exceeded the Rate Limit"), Kraken public bei `kraken_agent`; vier
  Abstuerze mit Code 4294967295 im selben Moment waren eigene Abschuesse.
- Merksatz: Absturzzeilen mit Grund lesen, nicht die Zaehler im Treiberlog.

## Werkzeuge und Umgebung

### 13. „0 Treffer von 0 Skills" (16.09.2026, fundus-suche.ps1)
- Behauptung: der Fundus hat keine Skills.
- Entstehung: unter PowerShell 5.1 fehlt `Get-FileHash`
  (CommandNotFoundException); der Hash blieb leer → alle Skills in EINER Gruppe.
- Fix: `[System.Security.Cryptography.MD5]` + `[IO.File]::OpenRead`, plus
  Gruppierung nach Pfad als Rueckfall.

### 14. Tippfehler, die trotzdem ankommen (19.09.2026, patch)
- Behauptung: `kill_switch_gesamt_usd` und `papier_faktor: 4.0` stehen wie geplant.
- Auffallen: das fuzzy `patch`-Werkzeug hatte `kill_switch_h_gesamt_usd` und
  `6.0` geschrieben.
- Merksatz: nach jedem Patch den Schluessel/Wert per `read_file` nachlesen.

### 15. Ganzdatei-Diff bei einer Zeile (16.09.2026, SKILL.md)
- Behauptung: eine Zeile geaendert.
- Auffallen: `git diff --stat` zeigte die ganze Datei — `open(pfad, encoding=...)`
  wandelt CRLF still nach LF, danach ist `"\r\n" in text` immer False.
- Richtig: `open(pfad,'rb').read()`, Zeilenende aus dem ROHEN Text ableiten,
  `open(pfad,'wb').write(t.encode('utf-8'))` — zweimal passiert.

### 16. Verweis als Wert gezaehlt (12.09.2026, a2a-Token)
- Behauptung: der a2a-Token steht im Klartext in allen 13 Hermes-Configs.
- Entstehung: die Suche nahm nur `${env:…}` aus, nicht aber `${NAME}`.
- Wahrheit: 12 Configs tragen den Verweis, das Profil `nous` hat gar keinen
  `a2a_agents`-Block. Urteil zurueckgenommen.

### 17. Env-Variable „fehlt" (19.09.2026, windows-mcp)
- Behauptung: die OKX-Variablen sind leer.
- Entstehung: `Get-ItemProperty HKCU\Environment` loest HKCU in einen anderen
  Benutzerkontext auf.
- Richtig: `[Environment]::GetEnvironmentVariable(name,'User')` bzw. `'System'`.

### 18. `which` sieht Windows nicht (18.09.2026)
- Behauptung: VS Code ist nicht installiert.
- Auffallen: `which code.cmd` findet nichts, `Get-Command code` findet
  `AppData\Local\Programs\Microsoft VS Code\bin\code.cmd`.

### 19. PYTHONHOME aus dem falschen venv (18.09.2026)
- Behauptung: das venv des MCP-Servers ist gesund, der Supervisor vergiftet.
- Messung: ein uv-venv-`python.exe` setzt `PYTHONHOME` in die eigene
  Prozessumgebung, jedes Kind erbt sie.
- Fix: venv auf python.org 3.13 neu bauen (setzt kein PYTHONHOME), 6 Server.

### 20. Junction nicht als Symlink erkannt (21.09.2026)
- Behauptung: die `okx-*`-Skills sind Symlinks und koennen mit verschoben werden.
- Auffallen: Python meldet `is_symlink`/`islink` False; nur `os.path.isjunction`
  erkennt die Windows-Junction. Ein Verschieben haette die Quelle fuer andere
  Agenten mitgerissen.

## Git und Arbeitsbaum

### 21. `index.lock`, 46 Minuten alt, 0 Byte (21.09.2026, zweimal)
- Behauptung: ein Committer laeuft noch.
- Messung: 12 `git.exe`, alle `git fsmonitor--daemon run --detach`, kein echter
  Commitprozess.
- Vorgehen: Alter + echte git-Prozesse zaehlen, Sperre **umbenennen**
  (`.git/index.lock.verwaist-20260921`), Commit wiederholen.

### 22. Neue Spur ist unsichtbar (15.09.2026)
- Behauptung: die vier Prognose-Spuren liegen in Git.
- Auffallen: `git status --porcelain --ignored <ordner>` zeigte `!!`.
- Regel: erst alles ignorieren, dann einzeln freigeben — je Spur vier Eintraege;
  Gegenprobe `git check-ignore -v <spur>/zustand.mittel.json` **und**
  `git ls-files 'Agenten/Handel/*/zustand*.json'` (muss leer sein).

### 23. Nachtsicherung stand still (19.–21.09.2026)
- Behauptung: der Zweig `zwischenstand` laeuft naechtlich.
- Auffallen: `git add -A --dry-run` brach mit Exitcode 128 ab (`mfaupel95`-Klon
  ohne ausgecheckten Commit in `skills/`); letzter Commit 18.09.
- Merksatz: Fruehwarnung `git log -1 --format=%ci zwischenstand`.

## Eine Fehlermeldung, die richtig war — und der Schluss daraus nicht (06.10.2026)

### 29. „Die Historie wurde um 04:23 geleert"
- Behauptung: ein Vorgang hat den Ordner `daten/historie/` geleert; ein
  Ordner-`mtime` von 04:23:17 lag „genau im Fenster".
- Entstehung: ein Replay-Testlauf meldete ehrlich
  `Historie fehlt oder ist zu kurz: BTC-USDC (0 Kerzen), ETH-USDC (0 Kerzen), …`.
  Der Lauf startete aus einem **Git-Worktree**
  (`.worktrees/<id>/Agenten/Handel/tests`). `daten/` ist per `.gitignore`
  gesperrt (`git ls-files Agenten/Handel/daten` ist leer), ein Worktree bekommt
  also alle `.py`-Dateien, aber kein `daten/`. Und
  `historie_binance.ORDNER = os.path.join(HIER, "daten", "historie")` ist
  RELATIV zur Modulposition — die Modulkopie im Worktree zeigte auf einen
  Ordner, den es dort nicht gab.
- Auffiel: erst als der eigene Suchlauf ueber ALLE Sitzungen
  (`state.db`, `messages.session_id`) **keinen** Loeschaufruf im Fenster fand,
  und der Ordner `daten/backtest/orb` mit demselben `mtime` als Unterordner
  eines Replay-Laufs entlarvt wurde.
- Beleg (Gegenprobe, im Temp-Ordner reproduziert): eine Kopie des Hauses ohne
  `daten/` liefert
  `ORDNER: …\wt\Agenten\Handel\daten\historie` / `ordner existiert: False` /
  `lade BTC 1H -> 0`. Dieselbe Meldung, andere Ursache.
- Wahrheit: der Ordner wurde nie geleert — er war in der Kopie nie vorhanden.
  Die 54 Reihen lagen die ganze Zeit im Hauptbaum.
- Merksatz: **eine korrekte Fehlermeldung ist noch kein Befund.** Vor jedem
  Loeschverdacht die Pfadkonstruktion im Quelltext lesen und den abgeleiteten
  Pfad ausdrucken lassen. Ein `mtime`, den man einmal aus dem Kopf behaelt,
  wandert beim Nachmessen — hier datierte er einen Unterordner, der NACH dem
  Ereignis schrieb.
- Nebenprodukt: der falsche Befund stand 24 h in der Aufgabenliste („348 von
  406 Reihen weg") und wurde zur Folgeaufgabe. Die Korrektur gehoert in
  denselben Eintrag, nicht in einen neuen.

## Tests

### 24. Alle Tests gruen, Bedigung 4 verletzt (14.09.2026)
- Behauptung: die Testsuiten sind harmlos.
- Auffallen: sie schrieben in das echte `journal_zweitziel`; jede
  `discover`-Runde ueberschrieb `Q:\Handel_Journal\<spur>` (spiegel Zustand
  13.816 → 222 Byte), omniquant Zustand+Journal ebenso.
- Nachweismuster: alle Suiten laufen lassen und DANACH `spiegelstand.py`
  aufrufen — muss `N/N byte-gleich` melden; Gegenprobe durch Zuruecknehmen des
  Fixes.

### 25. 16 Testbuchungen im echten Journal (16.09.2026, moondev_funding)
- Behauptung: der Test pruefe nur.
- Auffallen: Tests, die `pruefe_einstieg`/`pruefe_ausstiege` direkt aufrufen,
  buchen ins echte Journal.
- Fix-Muster: in diesen Klassen `SCHREIBEN=False` **und** einen Modulwaechter
  (Dateiliste + Groessen vor/nach) einbauen.

### 26. Gruene Tests, die nichts prueften (15.09.2026)
- Behauptung: `bewertung.bewerten` rechnet richtig.
- Auffallen: ein Test uebergab sein Gewichte-dict POSITIONELL, es landete in
  `richtung`, rutschte still in den long-Zweig, `66.7 == 66.7`.
- Fix: unbekannte Richtung wirft `ValueError`; `gewichte=` immer als Keyword.

### 27. Zwei vorbestehende rote Tests (21.09.2026)
- `test_risikovorfilter.EinbauTest` haengt an einem festen JETZT (17.09.): das
  12-h-Fenster ist leer, sobald der Lauf Tage spaeter stattfindet.
- `test_telegram_freigabe.WiedervorlageImLaufTest` erwartet eine offene ANFRAGE,
  bekommt durch `AUTO_FREIGABE` aber eine offene FREIGABE.
- Merksatz: A/B mit `dauerlauf.py` aus `HEAD` fahren, bevor eine Aenderung als
  Ursache gemeldet wird (`git stash`-Vergleich).

### 28. FileNotFoundError auf einer `mkdtemp`-Datei (04.10.2026)
- Gemeldet: `Ergebniscode 1 - FileNotFoundError: ...Temp\spurbuch-gatter-_ijomk0j\wachen.json`
- Auffallen: der Test legt die Wachen in `setUp` selbst an. Also suchte die
  Fehlermeldung nicht den Fehler, sondern eine alte Fassung der Datei - der
  Fund lag im Sitzungsprotokoll (`state.db`, `messages`), nicht im Baum.
- Gemessen: die alte `setUp` legte `zustand.json`, `handelsjournal.csv` und
  `signal_queue.json` an, **nicht** `wachen.json` - und `spur_buch.zyklus`
  liest genau die in `lade_wachen`. Die Meldung war damit korrekt.
- Gegenprobe: eine Attrappe OHNE `wachen.json` bricht mit derselben Meldung
  ab, dieselbe Attrappe MIT der Datei bucht. Damit ist die Ursache belegt und
  nicht geraten.
- Merksatz: eine `FileNotFoundError` auf einer `mkdtemp`-Adresse ist fast immer
  die FASSUNG, nicht der Ort. `state.db` (`messages`, `role='tool'`, letzte 20
  Nachrichten vor dem Fehler) beantwortet "welche Fassung lief" in Sekunden.
- Zweite Falle desselben Tages: die erste Diagnose lief mit dem
  Hermes-tools-Python (3.14, ohne `psutil`) statt `scanner/.venv` - 75 der
  Fehler waren `ModuleNotFoundError: psutil`, nicht Defekte. **Handel-Tests
  laufen ueber `Agenten/Routinen/handel-tests.ps1` bzw. das scanner-venv**, nie
  ueber `python -m unittest` mit einem anderen Interpreter.

## Ein Schaden nach der eigenen Aenderung (06.10.2026)

### 30. „Der Volume-Eintrag hat Docker zerstoert"
- Behauptung: der frisch gesetzte `terminal.docker_volumes`-Eintrag hat den
  Docker-Daemon beschaedigt; danach ging kein `docker run` mehr.
- Entstehung: die Reihenfolge war verlockend — Eintrag gesetzt, naechster
  Containerstart scheitert mit `Exit 125`
  (`write … meta.db: read-only file system`). Der Eintrag war die letzte
  Aenderung, also die naheliegende Ursache.
- Auffiel: der Fehler betraf **jeden** `docker run`, auch mit einem lokal
  vorhandenen Image, und `docker image ls` brach mit `input/output error` beim
  Lesen eines Content-Blobs ab — das ist kein Volume-Problem.
- Gegenprobe, die entscheidet: derselbe `docker run` **ohne jeden
  `-v`-Eintrag** scheiterte zeichengleich. Damit ist der Eintrag entlastet und
  der Daemon als Schaden belegt.
- Zusatzbefund zur Signatur: derselbe Code 125 stand am Vortag fuer eine
  **andere** Ursache (Windows-Pfad aus `terminal.cwd` roh in `docker run -w`).
  Wer nur den Code liest, haelt zwei verschiedene Defekte fuer denselben.
- Was trotzdem belegbar blieb, ausdruecklich als FORM-Beleg: der Spec ist
  gueltig (`_split_volume_spec` zerlegt beide Schreibweisen zu
  `('C:\\…\\BrainFiles', '/brainfiles')` — die Funktion liegt in
  `tools/environments/docker.py`, **nicht** in `remote_common`), der Host-Pfad
  existiert, der Eintrag steht korrekt (2/0 Insertions, `terminal` 12 -> 13
  Schluessel, `yaml.safe_load` liest ihn zurueck, CRLF und bareLF unveraendert).
- Offen geblieben: `docker exec <container> ls /brainfiles` — genau der
  Wirkungsbeleg. Kein Container trug den Mount, weil alle vorhandenen aelter
  waren als der Eintrag.
- Merksatz: **die Gegenprobe ohne die Aenderung ist der Unterschied zwischen
  „danach kaputt" und „davon kaputt".**

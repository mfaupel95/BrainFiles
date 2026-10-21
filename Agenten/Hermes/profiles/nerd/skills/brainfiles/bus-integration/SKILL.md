---
name: bus-integration
description: Use when adding a BrainFiles routine to the Telegram Bus.
category: brainfiles
---

## Procedure

1. **Create the Bus Wrapper PowerShell Script**
   - File: `Agenten/Routinen/bus.ps1`
   - Content:
     ```powershell
     # Registriert den Bus als Aufgabe 'bei Systemstart'.
     # ... (see skill for full script)
     ```
   - This script registers a scheduled task `BrainFiles-Bus` that runs `Agenten/Bus/bus.py` at startup with highest priority and restart on failure.

2. **Update the Central README**
   - File: `Agenten/Bus/README.md`
   - Provide a short description of the bus, its files, usage, and the guarantee "ein toter Bus darf niemals einen Lauf abbrechen".

3. **Extend the Routinen Overview in the Vault**
   - File: `MaxHirn/Wissen/Routinen.md`
   - Insert a new row in the "Geplant" table:
     ```markdown
     | bei Systemstart | BrainFiles-Bus starten | Agenten/Bus/bus.py | **eingeplant** 2026-09-10 — `MaxHirn-BrainFiles-Bus` |
     ```
   - Keep the existing table format. **Zeilenenden bytes-genau einfuegen:** die Datei
    ist CRLF mit einzelnen LF-Zeilen. `.bak-JJJJMMTT` anlegen, die neue Zeile per
    kurzem Skript an der Ankerzeile einfuegen, danach gegenpruefen, dass die Datei
    ohne die neue Zeile byte-identisch zur Sicherung ist. Weder komplett neu
    schreiben noch per Patch-Werkzeug anfassen - beide normalisieren die
    Zeilenenden und drehen genau die einzelnen LF-Zeilen um; im Diff stehen dann
    Aenderungen, die niemand gemacht hat.

4. **Add End-to-End Test**
   - File: `Agenten/Bus/tests/test_ende_zu_ende.py`
   - This test verifies:
     - Errors reach the user's device within one minute.
     - A stopped bus still lets a routine run (journal entries appear).
     - All module tests pass.
   - Ensure it is runnable with `python tests/test_ende_zu_ende.py` from the `Agenten/Bus` directory.

5. **Run the Test Suite**
   - Execute:
     ```bash
     cd Agenten/Bus && python tests/test_ende_zu_ende.py
     ```
   - Expect output ending with "Ende-zu-Ende bestanden".

6. **Commit Changes**
   - Stage the new/changed files:
     ```bash
     git add Agenten/Routinen/bus.ps1 Agenten/Bus/README.md MaxHirn/Wissen/Routinen.md Agenten/Bus/tests/test_ende_zu_ende.py
     ```
   - Commit with a descriptive German message and the required trailer:
     ```bash
     git commit -m "Bus: Betrieb ueber die Aufgabenplanung, Ende-zu-Ende-Abnahme" -m "Co-Authored-By: Claude Opus 5 noreply@anthropic.com"
     ```

## Pitfalls
- **Zeilenenden: die Datei kennt zwei Sorten - beide unangetastet lassen.**
  `MaxHirn/Wissen/Routinen.md` ist CRLF mit einzelnen LF-Zeilen; jedes Werkzeug,
  das die Datei neu schreibt (`write`, Patch-Werkzeug, `sed`, `edit`, Python),
  normalisiert sie und dreht genau diese Zeilen um. Richtig: Sicherung anlegen,
  bytes-genau einfuegen, Gegenprobe (Datei ohne die neue Zeile == Sicherung).
  Erkennen VOR dem Schreiben: Zeilenenden BINAER lesen (`open(p,'rb').read()`).
  Ein Textmodus-`read()` wandelt `\r\n` schon beim Lesen zu `\n`; eine Pruefung
  `'\r\n' in text` meldet dann falsch „reine LF-Datei", und der Write stellt die
  ganze Datei um. Auf CRLF-Zielen findet der Fuzzy-Abgleich des Patch-Werkzeugs
  den Anker ausserdem oft nicht („Could not find a match", obwohl die Zeile
  sichtbar dasteht) - dann nicht weiter probieren, sondern die Ersetzung per
  Skript mit binaer gelesenem Text und `newline=''` fahren und den Erfolg an der
  Trefferzahl festmachen (`assert text.count(alt) == 1`, sonst NICHTS schreiben).
  Eine dritte Form der Falle: das Patch-Werkzeug FINDET den Anker, ersetzt aber
  mit verschobener Einruedung (gemessen: 12 -> 24/28 Spaces im Ersatzblock).
  Einmal war die Datei danach syntaktisch kaputt, einmal gruen - ein falsch
  eingerueckter String in einer Verkettung ist fuer den Parser gueltig. Deshalb
  nach JEDEM Patch auf CRLF-Ziel den Ersatzbereich ansehen (git diff), nicht nur
  den Lint glauben; ist die Einruedung verschoben, die Korrektur per Skript mit
  eindeutigem Anker fahren, nicht ein zweites Patch versuchen.
  Nach jeder Massenaenderung `git diff --stat` ansehen: eine gewollte Zeile darf
  nicht als ganzes Dateidiff erscheinen.
  Fuer `.ps1` gibt es statt Augenschein eine harte Gegenprobe nach jedem Patch:
  `$e=$null; [void][System.Management.Automation.Language.Parser]::ParseFile($pfad,[ref]$null,[ref]$e); $e.Count`
  muss `0` ergeben - ein falsch eingerueckter Ersatz kann fuer den Parser gueltig
  sein und trotzdem die Verkettung zerstoeren. Umgekehrt gilt: eine nachweislich
  LF-reine `.ps1` (binaer lesen) darf mit dem Patch-Werkzeug bearbeitet werden,
  die Zeilenenden- und Einrueckungsfallen gelten fuer CRLF-Ziele. Erst messen,
  dann das Werkzeug waehlen.
- **Zugriff verweigert heisst hier: erhoehte PowerShell.** `Register-ScheduledTask`
  legt ohne Admin GAR keine Aufgabe an (`HRESULT 0x80070005`), auch keine harmlose
  ohne `-RunLevel Highest` - unabhaengig davon, ob der Benutzer lokal
  Administrator ist. Das Registrierungsskript laeuft deshalb erhoeht und hat kein
  Fenster, in dem man das Ergebnis lesen koennte: es schreibt sein Ergebnis selbst
  in eine Logdatei (`logs/<name>-aufgabe.log`, mit Zeitstempel) und nennt diesen
  Pfad im Kopf. Der Wrapper dagegen laeuft ohne Admin - beide Zweige lassen sich
  von Hand fahren, waehrend die Aufgabe noch fehlt.
- **Do not alter routine logic**: Only add the four required lines (`. (Join-Path $wurzel 'Bus\Ereignis.ps1')`, `$marke = Melde-Start ...`, and `Melde-Ende` before each `exit` and in each `catch`). Keep the existing behavior, exit codes, and output unchanged.
- **`$wurzel` ist neuer als manche Routine.** Routinen aus der Zeit vor dem
  Anbindungs-Muster kennen `Split-Path $PSScriptRoot -Parent` nicht - eine
  ergaenzte dot-source-Zeile `. (Join-Path $wurzel 'Bus\Ereignis.ps1')`
  bricht dann beim Lauf mit leerem Path. Beim Anbinden einer ALTEN Routine
  `$wurzel` mit definieren und den Parser-Komplettlauf (`ParseFile` mit
  `$e.Count == 0`) fahren, nicht nur die Suite.
- **Die Suite verlangt `Melde-Ende` in den vier Zeilen DIREKT vor jedem
  `exit`** - ein `Melden`/Log-Schritt dazwischen laesst den Anbindungstest
  (test_melde_ende_steht_an_jedem_ausstieg) fehlschlagen, obwohl die Meldung
  existiert. `Melde-Ende` direkt ueber die exit-Zeile setzen.
- **Avoid absolute paths**: All paths must be relative to `$PSScriptRoot` or derived from it; the only absolute path appears in `bus.ps1` where it is constructed at runtime from `$PSScriptRoot`.
- **Test before committing**: Always run the end‑to‑end test after modifications; a failure indicates a missing `Melde-Ende` or an incorrect `-Wer` value.

## References
- See `Agenten/Bus/Ereignis.ps1` for the `Melde-Start` / `Melde-Ende` contract.
- Refer to `Wissen/Routinen.md` for the complete list of planned tasks and their wrappers.

- **Jedes neue Skript in `Agenten/Routinen/` gilt als Routine.** Die Prüfung
  `tests/test_anbindung_routinen.py::geplante()` nimmt **jede** `*.ps1` in diesem
  Ordner, ausgenommen `einmalig-*`, `*-hook.ps1`, `bus.ps1`, Dateien mit
  `BUS: Bibliothek` und Registrierungsskripte (`Register-ScheduledTask` ohne
  `Melde-Start`). Ein
  Registrierungsskript (eigene Aufgabe per `Register-ScheduledTask`, wie das
  Gegenstück zu `bus.ps1`) fällt damit unter den Routine-Begriff und färbt die
  ganze Kette rot: `test_ende_zu_ende.py` bricht in `test_alle_modultests_laufen`
  ab, die Meldung lautet `ohne Bus-Anbindung: ['<name>']`. Nicht das Skript
  anbinden, sondern die Ausnahme generisch fassen — Dateien mit
  `Register-ScheduledTask` überspringen, statt Namen aufzuzählen; sonst reißt das
  nächste Registrierungsskript die Suite erneut ein.
- **Eine einmalige Aktion ist keine Routine und heisst deshalb `einmalig-`.**
  Ein Skript, das genau einmal laeuft (Admin-Handgriff, Umstellung, Aufraeumen),
  bekommt **keine** Bus-Anbindung: es meldet nie wieder, die Zeilen waeren eine
  Attrappe. Richtig ist der Name in der Hauskonvention
  `einmalig-JJJJMMTT-<thema>.ps1` — die Pruefung ueberspringt genau diesen
  Praefix, und `git mv` haelt den Verlauf. Umgekehrt gilt: ein Einmal-Skript ohne
  diesen Praefix faerbt die Suite rot, obwohl es mit ihm seine Richtigkeit hat;
  dann wird umbenannt, nicht angebunden.
- **Die dritte Sorte ist die Bibliothek.** Ein Skript, das andere Routinen per
  dot-source einbinden (`safe-file-ops.ps1` in `posteingang.ps1` und
  `datensortierung.ps1`, mit eigenem `$MyInvocation`-Einsprung), bekommt **keine**
  eigene `Melde-Start`/`Melde-Ende`-Zeile: sie schriebe bei jedem Aufruf des
  Einbinders einen zweiten Zyklus ins Journal, der wie ein eigener Lauf aussieht.
  Gemeldet wird, wer den Lauf verantwortet (`routine/<einbinder>`). Solche Dateien
  kennzeichnen sich im Kopf mit der Zeile `BUS: Bibliothek`; die Prüfung
  überspringt genau diese Kennzeichnung. Den Marker in die Datei schreiben, nicht
  den Dateinamen in den Test — sonst reißt die nächste Bibliothek die Suite
  erneut ein.
- **Ein roter Anbindungstest hat zwei mögliche Ursachen mit GEGENWÄRTLIGER
  Lösung — erst die Aufgabenplanung fragen, dann bauen.** Der Test
  `test_jede_routine_meldet` kennt nur das Symptom „Datei ohne Anbindung"; er
  sagt nicht, welche der beiden Bauarten hier richtig ist. Die unterscheidet
  genau eine Messung: `Get-ScheduledTask | Where-Object {$_.TaskName -like '*<name>*'}`
  (die Aufzaehlung nehmen, `Get-ScheduledTask -TaskName` findet vorhandene
  Aufgaben nicht zuverlässig) und `grep -n '<name>' Agenten/Routinen/*.ps1` —
  wer ruft sie auf?
  - **Hat sie einen eigenen Ausloeser** (eigene geplante Aufgabe, im Journal
    `routine/<name>`): gehoert sie an den Bus. Fehlt die Anbindung, ist es ein
    Loch, das man zulaest.
  - **Wird sie von einem anderen Skript gerufen** (dot-source oder
    `& powershell -File <datei>` aus einer Routine heraus), hat sie **keinen**
    eigenen Ausloeser und die geplante Aufgabe gehoert dem EINBINDER: eine
    eigene `Melde-Start` schriebe jeden Befund mehrfach ins Journal. Dann
    `BUS: Bibliothek` in den Kopf, mit der Begruendung, aus welcher Datei sie
    aufgerufen wird und wie oft.
  Falsch gebaut ist beides mit Symptomen: die Anbindung trotzdem eingebaut
  verdoppelt den Journal-Eintrag, die Kennzeichnung trotzdem noetig laesst die
  Suite rot. Die Aufgabenplanung ist die eine Messung, die die Frage entscheidet,
  und sie ist billig — also vor dem Bau, nicht danach.
- **Ein abgebrochener Lauf sieht wie ein Ausbleiben aus, ist aber keins.** Wird
  die Aufgabe von außen beendet (Herunterfahren, `Stop-ScheduledTask`, Absturz),
  steht ein `start` ohne `ende` im Journal — kein PowerShell kann die Schlusszeile
  nach einem Kill noch schreiben. Vor dem Melden einer fehlenden Meldung deshalb
  immer `Get-ScheduledTaskInfo` fragen: `0` = sauber, `267009` (0x41301) = läuft
  gerade, `3221225786` (0xC000013A) = von außen beendet. Nur `0` ohne `ende` ist
  ein Befund am Bus.
- **Angebunden ist nicht gestartet.** Eine Routine ohne eigene geplante Aufgabe
  meldet nie; die Anbindung ist vorhanden, aber unsichtbar. Bei der Abnahme die
  gemeldeten Namen gegen die Liste der geplanten Aufgaben halten — sonst hält man
  den Bus für kaputt, während nur der Auslöser fehlt. Dazu gehoert die Zeile in
  `Wissen/Routinen.md`: sie behauptet **eingeplant** erst, wenn die Aufgabe
  wirklich existiert und einmal gelaufen ist - bis dahin "vorbereitet" mit dem
  Registrierungsbefehl daneben. Ein Dokument, das eine Aufgabe als geplant
  fuehrt, die es nicht gibt, ist derselbe Fehler eine Ebene hoeher; der Wrapper
  darf dafuer schon bewiesen sein.
- **Umgekehrt: der Autostart kann trotzdem stehen — ueber den Startup-Ordner.**
  Scheitert das Anlegen der Aufgabe an der fehlenden Erhoehung, wird der Dienst
  still durch eine Verknuepfung im Benutzer-Startup gestartet (der Weg ohne
  Admin). Vor jedem Befund „Autostart fehlt" ODER „Autostart ist da" deshalb
  BEIDE Orte fragen: `Get-ScheduledTask -TaskName <aufgabe>` (Fehler = gibt es
  nicht) und den Ordner
  `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`. Ruft die
  Verknuepfung den Wrapper auf, ist dessen Bus-Anbindung sehr wohl scharf — ein
  Wrapper ohne Aufgabe ist kein toter Code, und ein Dokument, das nur den einen
  der beiden Wege kennt, fuehrt in die Irre. Die Kopie im Startup-Ordner ist
  maschinengebunden und traegt einen absoluten Pfad: die Fassung im Repo gehoert
  in die `.gitignore`-Freigabe und muss nach einem Umzug neu geschrieben werden.
- **Logik unangetastet lassen.** Beim Anbinden einer bestehenden Routine keine
  Bedingungen, Reihenfolgen, Exit-Codes oder Ausgaben ändern; ein Fremdskript
  (`.ps1`) nie per Python-Rewrite bearbeiten, das stellt CRLF auf LF um.

## Dienst-Start-Routinen (etwas hochfahren statt etwas pruefen)

Faehrt eine Routine einen Dienst hoch, gelten zusaetzliche Regeln — sonst startet
sie eine zweite Instanz oder der Wrapper stirbt vor seiner Schlusszeile:

- **Erst fragen, ob er schon laeuft.** Port-Probe am Anfang (`New-Object
  Net.Sockets.TcpClient` + `Connect('127.0.0.1', <port>)`); Treffer = Logzeile
  „laeuft schon, kein Start" + `Melde-Ende … -Code 0` + `exit 0`. Zwei Instanzen
  teilen sich Zustand (`~/.omniroute/storage.sqlite`) und nehmen sich
  gegenseitig Verbindungen ab. Ein „nichts zu tun" ist ein sauberer Lauf, kein
  Fehler — die Verzweigung gehoert ins Protokoll, sonst sieht sie wie ein
  stummer Abbruch aus.
- **Den Starter in einem eigenen Prozess aufrufen.** Das Startskript beendet
  sich an einigen Stellen mit `exit`; per `& powershell.exe -ExecutionPolicy
  Bypass -NoProfile -File <starter> *>&1 | Add-Content $log` (Kindprozess)
  aufrufen, danach `$LASTEXITCODE` pruefen. Im eigenen Prozess reisst das `exit`
  die Routine samt `Melde-Ende` mit.
- **Nach dem Start nachmessen, nicht glauben:** Port erneut pruefen; erst dann
  „laeuft" melden.
- **Ein GUI-Starter hat keinen Port - sein Nachweis ist der Fenstertitel.**
  `Get-Process -Name python* | Where-Object { $_.MainWindowTitle -like
  "*<Titel>*" }` ist die „laeuft schon"-Probe; das erkennt auch ein von Hand
  gestartetes Fenster, waehrend eine PID-Datei nach jedem Absturz eine Sperre
  hinterlaesst. Starten mit `pythonw.exe` (fensterlos, kein Konsolenfenster),
  Fehler in eine eigene Logdatei umleiten; nach dem Start bis ~30 s auf den
  Titel warten und dann erst melden.
- **Ein von einem Skript gestartetes GUI-Fenster hat kein Vordergrundrecht:**
  es ist offen (`IsWindowVisible` true) und steht trotzdem hinter allem -
  Befund „das Fenster ist weg", waehrend der Prozess laeuft. Gegenmittel im
  Programm, nicht im Starter: nach dem Aufbau kurz `-topmost` setzen (und
  nach ~1 s wieder loesen, sonst laesst es sich nicht wegklicken), dazu
  `lift()` und `focus_force()`. `SetForegroundWindow` aus einem fremden
  Prozess scheitert an der Vordergrundsperre.
- **Eine Aufgabe anzulegen braucht eine erhoehte PowerShell.** Ohne Admin
  lehnen `Register-ScheduledTask` UND `schtasks /create` mit „Zugriff
  verweigert" ab (geprueft 13.09.2026, auch fuer einen eigenen Ordnerpfad) -
  das ist kein Fehler im Skript. Eine Routine, die eine Aufgabe anlegen soll,
  braucht eine Registrierungsdatei mit `Register-ScheduledTask`, sonst faellt
  sie unter den Routine-Begriff (siehe Pitfall oben).
- **Ein erhoeht gestartetes Skript schreibt seine Startspur VOR jeder
  Pruefung** (wer, wann, erhoeht ja/nein) und bricht ohne Admin mit Exit 1
  ab. Grund: Nach einem UAC-Klick mit Wirkung stand weder Aufgabe noch
  Protokoll da - das ist von einem abgelehnten UAC-Klick nicht zu
  unterscheiden, und die Ursache laesst sich hinterher nicht mehr befragen.
- **Ein Fenster ist kein Port - der Nachweis ist der FENSTERTITEL des Kindes.**
  Fuer eine GUI-Routine gibt es nichts zu verbinden. Statt Port-Probe den Titel
  suchen (`Get-Process -Name python* | Where-Object { $_.MainWindowTitle -like
  "*<Titel>*" }`); das erkennt auch ein von Hand gestartetes Fenster, waehrend
  eine PID-Datei nach einem Absturz eine Sperre hinterlaesst. Ein venv-Start ist
  ein Paar aus Launcher und Interpreter: die PID des Starters traegt einen leeren
  Titel, der Titel steht auf dem Kind.
- **GUI fensterlos starten, Fehler in eine Datei.** `pythonw.exe` statt
  `python.exe`, dazu `Start-Process ... -RedirectStandardError <log>`: sonst steht
  bei jeder Anmeldung ein schwarzes Konsolenfenster auf dem Bildschirm. Ohne
  Fenster ist der Traceback eines misslungenen Aufbaus sonst unsichtbar - die
  Datei waechst nur, wenn wirklich etwas schiefging.
- **Start abwarten und BEIDES pruefen.** Nach `Start-Process -PassThru` bis ~30 s
  in einer Schleife auf den Fenstertitel warten (`Start-Sleep -Seconds 1`), Abbruch
  bei `$p.HasExited`. Scheitert es, den Grund zusammensetzen: Exit-Code UND die
  letzten Zeilen des Fehlerlogs in den `Melde-Ende`-Text - sonst steht im Journal
  nur "kein Fenstertitel nach 30 s" und niemand weiss warum.
- **Beide Zweige VOR dem Anlegen der Aufgabe von Hand fahren.** Der Wrapper
  braucht keinen Admin, das Anlegen der Aufgabe schon: erst mit laufendem Fenster
  (Waechter-Zweig, "laeuft schon" + `Melde-Ende -Code 0`), dann mit beendetem
  Fenster (Start-Zweig). Danach steht die Routine bewiesen, waehrend die Aufgabe
  noch auf den einen erhoehten Klick wartet.
- **Ausloeser „Anmeldung" mit Verzoegerung** (`New-ScheduledTaskTrigger -AtLogOn`,
  `$trigger.Delay = 'PT2M'`) und grosszuegiges Zeitlimit
  (`-ExecutionTimeLimit (New-TimeSpan -Minutes 15)`): im Startpfad kann ein
  Produktions-Build liegen, das Fuenf-Minuten-Limit der uebrigen Aufgaben ist
  dafuer zu knapp.
- **Abnahme ueber die Aufgabenplanung, nicht per Hand:** `Start-ScheduledTask`,
  dann muss `Get-ScheduledTaskInfo` `LastTaskResult: 0` zeigen und das eigene
  Protokoll die erwartete Verzweigung nennen. Jeder neue `.ps1` in
  `Agenten/Routinen/` zaehlt als Routine — Bus-Anbindung (oben) und eine Zeile
  in `Wissen/Routinen.md` gehoeren dazu.

## Neue Routine anlegen — was der Bau am 16.09.2026 gelehrt hat

- **Ohne Admin registrieren.** Fuer eine wöchentliche Aufgabe des angemeldeten
  Benutzers (`Interactive`, `RunLevel Limited`) genuegte eine **nicht** erhöhte
  Sitzung: `Register-ScheduledTask` lief durch, `Get-ScheduledTaskInfo` meldete
  danach `rc=0`. Die Warnung „ADMINISTRATOR NOETIG" in `handelszentrale-aufgabe.ps1`
  Der Unterschied liegt am AUSLOESER, nicht am Benutzer: eine
  Anmelde-Aufgabe (`-AtLogOn`, Principal `Interactive`) verlangt Erhoehung - eine
  nicht erhoehte Registrierung endet mit „Zugriff verweigert", und die Aufgabe
  existiert danach schlicht nicht, waehrend Wrapper und Startverknuepfung daneben
  unbeanstandet weiterlaufen (der Dienst startet also, nur ohne Task). Fuer eine
  Anmelde-Aufgabe darum gleich erhoeht registrieren und den einen UAC-Klick
  ankuendigen; fuer eine zeitgesteuerte Wochenaufgabe zuerst ohne Admin versuchen.
  **Erhoeht registrieren und VORHER/NACHHER belegen:** ein duenner Aufrufer
  (`Start-Process -FilePath powershell.exe -Verb RunAs -Wait -PassThru
  -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',<aufgabe.ps1>`)
  schreibt in ein eigenes Protokoll: Aufgabe vorher (State oder „NICHT VORHANDEN"),
  Exitcode der erhoehten Sitzung, danach `Get-ScheduledTask` mit State, Aktion,
  Ausloeser-Delay, `MultipleInstances`, `StartWhenAvailable`, `ExecutionTimeLimit`
  und Principal. Ohne diese Zeilen ist ein abgelehnter UAC-Klick von einem
  fehlgeschlagenen Registrierungsversuch nicht zu unterscheiden.
  **Und die Kopfzeile des Registrierungsskripts danach korrigieren.** „Kein
  Administrator noetig" war genau der Satz, der eine fehlgeschlagene Registrierung
  ueberlebt hat: er stand im Skriptkopf, in der To-do-Notiz des Repos und in
  diesem Skill. Wer den Fehlschlag findet, schreibt die falsche Zusage an allen
  drei Stellen um - sonst laeuft die naechste Sitzung in dieselbe Wand.
- **Das Protokoll ist die spätere Abnahmeprüfung.** Erste Zeile
  `=== Lauf <Zeitstempel> ===`, letzte Zeile beginnt mit `ENDE`. Nur damit lässt
  sich hinterher unterscheiden, ob ein Lauf fertig wurde oder abgeschnitten ist —
  `Agenten/Hermes/scripts/optimierungen-finden.py` prüft genau das. Achtung:
  `Set-Content -Encoding UTF8` setzt ein BOM vor die erste Zeile; beim Lesen
  abschneiden, sonst greift die Kopfzeilen-Prüfung nicht.
- **Befund ist kein Fehler.** „Es gibt etwas zu melden" gehört in `Melde-Hinweis`
  (wird immer gemeldet); `Melde-Ende -Code 1` bleibt echten Fehlern vorbehalten.
  Sonst sieht die Routine jede Woche wie ein kaputter Lauf aus.
- **Neue `.ps1` kommen als LF an und müssen auf CRLF.** Nach dem Schreiben
  umstellen (siehe Zeilenenden-Falle oben) — und den Testlauf aus der
  Aufgabenplanung heraus fahren (`Start-ScheduledTask`, dann
  `Get-ScheduledTaskInfo`), nicht nur von Hand.
- **Abnahme:** `python tests/test_anbindung_routinen.py` aus `Agenten/Bus`. Jede
  neue `.ps1` in `Routinen/` ohne Anbindung reisst die ganze Suite ein.

- **Ein Schattenarm, der den Kern aufruft, braucht seine EIGENE Meldung.** Ein
  Walker, der nur eine Umgebungsvariable setzt und dann `kern._main()` ruft
  (Muster `spiegel_knapp.py`), meldet ohne eigene `ereignis.lauf`-Zeile unter dem
  Namen des Hauptarms — er laeuft, schreibt Journal, Buch und Spiegelung und ist
  trotzdem unsichtbar. Der Test `test_dauerlauf_subprocess_skripte_haben_bus`
  faellt genau dann, wenn `dauerlauf.SPUREN` einen `skript`-Eintrag auf einen
  eigenen Dateinamen zeigt und diese Datei den Bus-Namen nicht woertlich traegt.
  Muster:

  ```python
  os.environ["HANDEL_BUCH"] = "eth"          # VOR dem Import
  import ereignis
  import handeln
  def main():
      with ereignis.lauf("handel/<arm>"):     # eigener Name, nicht der des Kerns
          return handeln._main()               # _main, nicht main()
  ```

  `main()` statt `_main()` kapselt den Lauf ein zweites Mal **und** meldet unter
  dem Kern-Namen — beides zusammen sieht aus wie „Anbindung vorhanden" und ist
  trotzdem unsichtbar. Nach dem Bau beide Wege belegen: Test gruen, und
  **Gegenprobe** — eigene Meldung entfernt, Test muss wieder an derselben Zeile
  rot werden, dann zuruecksetzen. Ein Fix ohne Gegenprobe ist hier nicht
  belegt, weil die Datei vorher zufaellig schon gruen sein koennte.

## Abnahme am laufenden System

Die vier Punkte der Spec werden am echten Rechner geprüft, nicht am Testcode
allein. Kurzfassung, vollständiges Rezept mit allen Befehlen in
`references/abnahme-am-laufenden-bus.md`:

1. **Bus lebt?** Port aus `Agenten/Bus/bus.json` gegen `Test-NetConnection`
   prüfen, dazu `bus.pid` und `Get-ScheduledTask -TaskName 'BrainFiles-Bus'`.
2. **Fehler kommt an:** eine Probe über `ereignis.melden(...)` absetzen, dann
   belegen, dass der Bus sie verarbeitet hat (Probe-ID in `Agenten/Bus/stand.json`)
   und `auffaellig.bewerte` sie für meldewürdig hält.
3. **Toter Bus:** `Stop-ScheduledTask`, Port als geschlossen belegen, eine **nur
   lesende** Routine starten — sie muss mit Exit 0 durchlaufen und trotzdem
   `start` und `ende` ins Journal schreiben —, Bus starten und das Nachholen
   beweisen (keine Journal-ID bleibt ungelesen).
4. **Tagesmeldung:** `sprecher.Sprecher(None, auffaellig.regeln()).tagesmeldung()`
   gegen die `ende`-Zeilen des Tages halten.

Für die Prüfung eine harmlose Routine wählen (`wissen-index-pruefen.ps1` liest
nur) — keine Sicherung, kein Versand, keine Order, solange die Abnahme nicht
ausdrücklich einen echten Lauf verlangt. Vor dem Anbinden und nach jeder Änderung
an `.ps1`-Routinen die Suite zeigen: `python tests/test_ende_zu_ende.py` aus
`Agenten/Bus`.

## Telegram-Meldungen: zwei Fallen, die eine Meldung wertlos machen

`melder.sende()` sendet mit `parse_mode=HTML`. Zwei Regeln folgen daraus:

1. **Freitext escapen - und zwar an der SENDESTELLE, nicht nur im Erzeuger.**
   `sprecher._sende` escaped jeden Text mit `html.escape`; richtig ist die
   Entschaerfung aber IN `melder.sende()` selbst, direkt vor dem Teilen der
   Nachricht. Grund: Texte kommen aus mehreren Erzeugern (Tagesbericht,
   Wochenbericht, Handelsmeldungen, Wachen) und enthalten Fremdtext, den kein
   Erzeuger escapen kann.
   Telegram liest mit `parse_mode=HTML` JEDES `<wort>` als Marke und weist die
   ganze Nachricht ab: `400 Bad Request: can't parse entities: Unsupported start
   tag "zahl"`. Ein Bericht mit dem Satz `n=<Zahl> heisst: zu wenige Runden` kam
   deshalb NIE an - und ein Traceback im Bericht (`<module>`, `<lambda>`) trifft
   dieselbe Falle. Der Fehler sieht aus wie "Telegram mag den Bericht nicht",
   ist aber ein Wort im Text.
   Vorgehen beim Entschaerfen: nur **rohe** `<`, `>` und nackte `&` umschreiben;
   erlaubte Marken (`b i u s code pre a`, mit optionalen Attributen) stehen
   lassen; gueltige Entitaeten (`&amp;`, `&#39;`, `&lt;`) NICHT doppelt
   entschaerfen, sonst steht `&amp;amp;` in der Nachricht. Gegenproben, die den
   Test wert sind: `n=<Zahl>` wird zu `n=&lt;Zahl&gt;`, ein `<b>` bleibt Marke,
   `a & b` wird `a &amp; b`, und die Entschaerfung ist idempotent.
   Den ECHTEN Bericht mitpruefen: `wochenbericht.baue()` entschaerfen und
   zusichern, dass nach dem Entfernen der erlaubten Marken keine `<`/`>`
   uebrig bleiben.
2. **Ursache mitschicken.** `auffaellig.bewerte` haengt bei Fehlern `text` und
   `log` an den Grund (`_mit_ursache`). Ohne das sagt die Meldung nur
   "Ergebniscode 1" und ist nicht zu deuten; die Ursache steht im Journal.
   **Die Ursache kann selbst die Ursache des 400 sein** - sie ist Fremdtext und
   wird nach Regel 1 mitentschaerft.

Warum die Meldung ueberhaupt lautlos verschwand: `sprecher._sende` **verschluckt**
den 400er (ein totes Telegram darf den Bus nicht reissen). Ein Bericht, der nie
ankommt, sieht dann aus wie ein Bericht, den niemand liest. Beim Senden deshalb
so pruefen, dass der Fehler SICHTBAR wird: das Sendeskript wirft bei `ok=false`
(`melder.sende` tut das), und der Beweis ist ein Lauf, der ohne Ausnahme
durchgeht - nicht die gerenderte Nachricht.

Nach jeder Aenderung an `sprecher.py` oder `auffaellig.py` den Bus neu starten
(`Stop-ScheduledTask`/`Start-ScheduledTask -TaskName 'BrainFiles-Bus'`): er
laedt die Module beim Start, nicht je Ereignis. Eine alte `bus.pid` ist danach
harmlos, `pid_sperren` ersetzt sie.

Beim ersten Start nach Stillstand holt `sprecher.nachholen()` das Journal des
Tages nach - bis zum Deckel (`deckel_je_stunde`, 20). Ein Schwall alter
Meldungen direkt nach dem Start ist also kein neuer Fehler.

**Probelauf: echt fahren, ohne das Handy zu wecken.** `auffaellig.bewerte`
schickt nur `hinweis`-Ereignisse und ein `ende` mit `code != 0` (oder
auffaelliger Dauer) hinaus; `start` und ein sauberes `ende` bleiben im Journal.
Ein Lauf mit Exit 0 und leerem Fehlerpfad ist also still und trotzdem der beste
Beweis fuer eine Anbindung. Wer auch den Journaleintrag nicht will, nutzt die
Testhaken aus `Ereignis.ps1`:
`BUS_PORT=9999 BUS_JOURNAL=$LOCALAPPDATA/Temp/bus-probe powershell.exe -NoProfile -File <routine>.ps1`
schreibt beide Ereignisse in eine Wegwerfdatei statt an den Bus (im
bash-Terminal so gesetzt, in PowerShell `$env:BUS_PORT='9999'`). Danach die zwei
Zeilen lesen (`wer`/`was`/`code`) und den Probeordner loeschen.

## Einen Befehl im SkillsBot ergaenzen

Der SkillsBot (`Agenten/Bus/skillsbot.py`) ist die Telegram-Seite: Freitext geht
per A2A an den lokalen Agenten, daneben hat er eigene Befehle. Fuer einen neuen
Befehl gilt:

1. **Datenquelle waehlen, die die Wahrheit traegt - nicht den bequemsten Proxy.**
   `/skills` las die A2A-Agent-Card (`/.well-known/agent-card.json`); deren Feld
   `skills` listet die WERKZEUGSAETZE (rund 42 Eintraege `toolset.*`, Beschreibung
   „Hermes 'x' capabilities", tags = Werkzeugnamen). Ausgegeben sieht das wie eine
   Zufallsliste aus und beantwortet „welche Skills gibt es" nicht. Richtig ist die
   Bibliothek auf der Platte (`Agenten/Hermes/skills/**/SKILL.md`, Frontmatter
   `name`/`description`/`category`), Umsetzung `Agenten/Bus/skillkatalog.py`.
2. **Nachschlagen statt laden.** Der Katalog laeuft nur im Bot-Prozess und kostet
   den Agentenkontext nichts; stillgelegte Skills (`.archive`, `*rollback*`)
   bleiben draussen - sonst sieht Ungeladenes wie geladen aus.
3. **Befehl an `wort` haengen, nicht an den ganzen Text.** `t = text.strip()` bleibt
   in Originalschreibweise, `wort` ist die klein geschriebene erste Silbe; das
   Argument aus `t[len(wort):]` schneiden. Ein Vergleich gegen `t` scheitert,
   sobald gross geschrieben wird.
4. **Laengenlimit beachten:** Telegram fasst 4096 Zeichen (Emojis zaehlen doppelt).
   `sende()` teilt selbst; ein eigener Schnitt trennt nur ZWISCHEN Zeilen, damit
   keine Zeile ohne Kopf in der zweiten Nachricht steht.
5. **Neuen Befehl in die Hilfe aufnehmen und den Bot neu starten**
   (`Stop-ScheduledTask`/`Start-ScheduledTask -TaskName 'BrainFiles-SkillsBot'`) -
   ein neuer Befehl gilt erst nach dem Neustart, und `/hilfe` ist die einzige
   Uebersicht. Der Befehlspfad wird aus dem Bot-Ordner importiert (`import
   skillkatalog`), weil die Spuren-/Bot-Module dort liegen.
6. **Test gegen die echte Quelle, nicht gegen eine Attrappe:** der Test prueft die
   Antwort des Befehlspfads und belegt, dass kein Proxy-Inhalt mehr darin steht
   (Beispiel: die Antwort darf kein `toolset.` enthalten). Beispiel:
   `Agenten/Bus/tests/test_skillkatalog.py`.
7. **Was Hermes nicht laedt, darf nicht als Faehigkeit erscheinen.** Hermes liest
   `platforms:` im Frontmatter und laesst Skills fremder Systeme weg (9 der
   Bibliothek sind `[macos]`/`[linux, macos]`; auf Windows sind es deshalb 58 von
   67 Eintraegen). Der Katalog wendet dieselbe Regel an (`skillkatalog.ladbar`)
   und nennt die ausgelassenen in EINER Schlusszeile - sie zu zeigen waere
   gelogen, sie zu verschweigen auch. Gegenprobe: die Kopfzahl muss
   `hermes skills list` entsprechen (58 enabled).
8. **Der SkillsBot sendet KLARTEXT** (kein `parse_mode`): HTML-Marken aus einer
   Antwort stehen woertlich in der Telegram-Nachricht - so war die alte
   `<b>`-Kopfzeile bei Max zu sehen. Also ohne Marken bauen und kurz halten:
   `/skills` zeigt NUR die Namen (58 Zeilen = eine Nachricht), die Beschreibung
   erst beim Filtern (`/skills handel`). Ein Befehl, der ohne Suchbegriff
   Beschreibungen ausgibt, sprengt die 4096 Zeichen und wird zerschnitten.
9. **Ein Befehl, der etwas AUSFUEHRT, wird anders abgesichert als einer, der
   liest.** `/run NAME [Auftrag]` reicht per A2A "Fuehre den Skill NAME aus" +
   Auftrag weiter und gibt die Antwort zurueck. Regeln dafuer:
   - Nur ausfuehren, was `skillkatalog.finde()` kennt UND `ladbar` ist, und nur
     bei EINDEUTIGEM Teiltreffer. Unbekannter Name, Tippfehler und Skills fremder
     Systeme enden OHNE A2A-Aufruf mit Begruendung - sonst laeuft irgendein
     Skill, und niemand erfaehrt welcher. Genau das ist der Test wert: bei
     abgelehntem Namen darf `frage()` NICHT gerufen worden sein.
   - Vorher eine Zwischenmeldung ("Fuehre X aus - das kann bis 5 min dauern"):
     eine Ausfuehrung dauert, der A2A-Timeout liegt bei 300 s, und ohne die
     Zeile wirkt der Bot haengend.
   - `/skill NAME` bleibt LESEN, `/run` ist AUSFUEHREN - zwei Namen fuer zwei
     Aufgaben, kein Schalter.
10. **Denkblock abschneiden, bevor die Antwort rausgeht.** Der A2A-Agent stellt
   seiner Antwort seinen Planungsblock voran (`\U0001f4ad **Reasoning:**` in einem
   ```-Zaun). Ungeschnitten ist auf dem Handy der halbe Text interne Notiz und
   liest sich wie das Ergebnis (im Test 3826 -> 1368 Zeichen).
   `skillsbot.ohne_denken()` entfernt NUR diesen Block, laesst Text davor/danach
   stehen und gibt bei fehlendem Block den Text unveraendert zurueck - ein
   anderer Aufbau darf keine Antwort kosten. Gilt fuer Ausfuehrungs- UND
   Freitext-Antworten.
11. **Ohne Telegram nachstellen** (sonst schickt jeder Testlauf Nachrichten an
   Max): `import skillsbot as s`, `s.sende = lambda chat, text:
   gesammelt.append(text)`, dann `s.bearbeite('/run <name> [auftrag]', 1)`. Die
   Antwort in eine Datei schreiben und dort lesen, nicht durch `tail` schicken -
   so sind Zwischenmeldung, Katalogpruefung und A2A-Weg in EINEM Durchlauf belegt.
12. **Eine dritte Sorte Befehl spricht ein PROFIL an statt den A2A-Agenten.**
   `/bot NAME NACHRICHT` (seit 16.09.2026) startet einen frischen Einzelauftrag
   `hermes -p NAME chat -q` als Subprozess - kein A2A, kein Gateway, kein
   Kontext. Der Name wird gegen die Platte validiert (`profiles/<name>/` mit
   config.yaml existiert), nie gegen eine gepflegte Liste. Subprozess-Umgebung:
   PYTHONHOME/PYTHONPATH entfernen, HERMES_HOME explizit setzen, cwd auf die
   BrainFiles-Wurzel (das SkillsBot-cwd ist nicht das Hermes-Home).
   **Nicht `subprocess.run(timeout=...)` benutzen:** das KILLT den Bot mitten in
   der Arbeit, und die ganze Aufgabe ist verloren. Ein Repo-Bot, der liest oder
   rechnet, braucht Minuten bis eine Viertelstunde; eine Frist von wenigen
   Minuten laesst JEDEN echten Auftrag mit "Zeitlimit" abbrechen, obwohl nichts
   kaputt ist. Richtig ist `Popen` + `communicate(timeout=<grosszuegige Frist>)`
   (Haus: `BOT_FRIST_S = 1800`), und erst danach wird getoetet - die Meldung
   nennt dann Ziel und Frist und sagt, was zu tun ist (Auftrag teilen oder
   Cronjob). Vorher eine Zwischenmeldung senden (Kaltstart 30-60 s, echte
   Aufgabe bis 30 min), sonst wirkt der Bot haengend.
   Den hermes.exe-Pfad als **Modulkonstante** halten (`HERMES_EXE`), nicht im
   Funktionorumpf zusammensetzen: der Test ersetzt sie durch ein Stub-Skript und
   prueft dann die ECHTE Prozessstrecke (schneller Lauf liefert die Antwort,
   langer Lauf bricht mit der erklaerenden Meldung ab) - ein gemocktes
   `subprocess.run` bemerkt den Unterschied zwischen killendem und abwartendem
   Aufruf nicht.
   Frist und Form gehoeren in einen **Selbsttest gegen Rueckbau**: den Quelltext
   zwischen `def _bot_fragen` und dem Ende lesen, Kommentarzeilen entfernen und
   `subprocess.run(` darin verbieten (`subprocess.Popen` muss dastehen). Sonst
   faellt die naechste Sitzung in dieselbe Falle, weil der Bot dann einfach
   wieder nach fuenf Minuten abbricht.

## Eine neue Windows-Aufgabe registrieren, ohne Einstellungen nachzubauen

- **Vorlage spiegeln statt Einstellungen nachbauen:** `Export-ScheduledTask -TaskName
  <bewaehrte-aufgabe>` liefert die XML, darin die Action-Argumente und
  `<StartBoundary>` per `-replace` ersetzen, dann
  `Register-ScheduledTask -TaskName <neu> -Xml $xml -Force`. Damit sind
  `StartWhenAvailable`, `MultipleInstances=IgnoreNew`, Zeitlimit und das versteckte
  Fenster (`-WindowStyle Hidden` steht in den Action-Argumenten) mitgenommen - genau
  die Einstellungen, die eine von Hand gebaute Aufgabe still anders hat.
- **Das Registrierungsskript heisst `Routinen/<name>-aufgabe.ps1`** (Hauskonvention,
  neben `bus.ps1` / `handelszentrale-aufgabe.ps1`) und enthaelt kein `Melde-Start`:
  damit faellt es unter die Ausnahme fuer Registrierer und braucht weder Bus-Anbindung
  noch `einmalig-`-Praefix.
- **Erhoehung haengt am AUSLOESER, nicht am Benutzer:** eine ZEIT-Aufgabe (taeglich/
  woechentlich, Principal `Interactive`) liess sich ohne Admin registrieren; eine
  ANMELDE-Aufgabe (`-AtLogOn`) verlangt Erhoehung. Nach der Registrierung
  `NextRunTime` nennen und einmal ueber die Aufgabenplanung fahren
  (`Start-ScheduledTask`, dann muss `Get-ScheduledTaskInfo` `LastTaskResult: 0` zeigen).
- **Reihenfolge im Tageslauf mitdenken:** eine Uebernahme-Aufgabe nach der
  Sicherungs-Aufgabe legen (erst sichern, dann umziehen) - laeuft die Uebernahme
  zuerst, arbeitet sie auf einem Stand, den die Sicherung gleich danach ueberschreibt.

## Eine Routine testen, die es nur so gibt (Temp-Baum statt Attrappe)

- **Funktionstest einer `.ps1`-Routine:** Kopie in einen Temp-Baum legen, der die
  Pfadableitung nachbildet - `<tmp>/Agenten/Routinen/<routine>.ps1` und
  `<tmp>/Agenten/Bus/Ereignis.ps1`, weil die Routine Wurzel und Bus relativ zu
  `$PSScriptRoot` sucht. Dann laeuft das unveraenderte ORIGINAL ohne Testschalter; ein
  `-Wurzel`-Parameter nur fuer Tests waere eine Hintertuer in ein Produktionsskript.
  Assertions gegen `git log/show/status/ls-files` und ein bare-Origin-Repo, nie gegen
  die Stdout-Ausgabe des Skripts.
- **Ein neues Testmodul muss in `test_ende_zu_ende.py` in die Namenstuple von
  `test_alle_modultests_laufen`** - sonst laeuft es nie mit der Suite, und "einzeln
  gruen" heisst nicht "mitgelaufen".
- **Die Suite bricht am ERSTEN roten Modul ab** (das `assert` steht in der Schleife):
  alles danach laeuft gar nicht. Bei einem roten Lauf die Module einzeln nachfahren
  und im Bericht TRENNEN, was vorbestehend rot ist und was von der eigenen Aenderung
  kommt - `git log --oneline -- <datei>` nennt den Commit, der die Annahme des Tests
  gebrochen hat. Ein hart auf einen alten Commit verdrahteter Vergleich ("weicht vom
  Stand vor Aufgabe N ab") ist der typische Uebeltaeter; er wird NICHT still
  umgeschrieben, sondern als Befund gemeldet.

## When to Use
Use this skill whenever you need to add a new automated routine to the BrainFiles Telegram Bus, or when you are setting up the bus for the first time on a new machine. Auch beim Auftrag "Autostart Routine einrichten" fuer einen Dienst oder ein Fenster (Abschnitt Dienst-Start-Routinen).

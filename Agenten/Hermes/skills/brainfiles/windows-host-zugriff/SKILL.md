---
name: windows-host-zugriff
description: "Use when Tools den Windows-Host nicht erreichen."
category: brainfiles
---

# Auf dem echten Rechner arbeiten (Windows-Host)

Wenn `terminal`, `read_file` oder `write_file` nicht auf dem Arbeitsrechner
landen: Befehle und Dateizugriffe über `windows-mcp` ausführen — Aufgabenplanung,
Dienste, Ports, Prozesse, Registry, alles unter `C:\Users\faupe\`.

## Wann

- `terminal`, `read_file` oder `write_file` finden `C:\...` nicht, oder der
  Aufruf landet offensichtlich in einem Linux-Sandkasten statt auf dem Rechner.
- **Das Terminal laeuft, aber die Wurzel fehlt.** Im Docker-Backend bindet der
  Container nur `terminal.cwd` (haeufig `Agenten/Hermes`). Dann antwortet das
  Terminal normal, `Agenten/Handel`, `MaxHirn` und jedes `git` im
  BrainFiles-Repo sind aber unsichtbar (`/workspace/..` zeigt die
  Container-Wurzel, kein `/mnt/c`). Kein Fehler, sondern der Sichtbereich —
  Wurzel-Arbeit laeuft ueber windows-mcp. Herkunft und Fix: Skill
  `hermes-config-ops`, Datei `references/docker-sandbox.md`.
- Ein Befehl **muss** auf dem Arbeitsrechner laufen: Aufgabenplanung, Dienste,
  Ports, Prozesse, Registry, Pfade unter `C:\Users\faupe\`.
- Ein Skript soll geprüft werden, das auf dem Host liegt (Routinen, Sicherungen,
  Bus).

## Zuerst feststellen, wo die Sitzung steht

```bash
uname -a; pwd; ls /; which powershell
df -h; cat /proc/mounts | head -20
```

Antwortet das mit Linux, ohne `C:\` und ohne `powershell` auf dem PATH, dann ist
die Werkzeugsitzung nicht auf dem Host. Nicht weiter mit Pfadraten versuchen —
der Host kommt dann nur über `windows-mcp`.

Zwei Symptome ersparen die Prüfung ganz:

- `write_file`/`patch` bricht ab mit `Write denied: '<pfad im Sandkasten>' is
  outside HERMES_WRITE_SAFE_ROOT ('<Windows-Pfad>')` — der Vergleich stellt
  einen Sandkastenpfad gegen einen Windows-Pfad und kann nie aufgehen.
- `read_file` meldet `File not found` für eine Datei, die auf dem Rechner
  nachweislich liegt, oder die gerade geschrieben wurde.

Beides heißt: die Werkzeugsitzung steht im Kasten. Das Terminal antwortet dann
zwar (mit Linux), und `C:\` taucht unter `/proc/mounts` auf — bleibt aber leer.

## Der Weg: windows-mcp

```
tool_describe(["mcp__windows_mcp__PowerShell", "mcp__windows_mcp__FileSystem"])
tool_call([{"name": "mcp__windows_mcp__PowerShell", "arguments": {"command": "..."}}])
```

- `mcp__windows_mcp__PowerShell` — beliebige PowerShell-Befehle auf dem Host, mit
  Max' Benutzerrechten (nicht erhöht). Ausgabe kommt als Text zurück.
- `mcp__windows_mcp__FileSystem` — `read`, `write`, `copy`, `move`, `delete`,
  `list`, `search`, `info`. Relative Pfade lösen vom Desktop auf, also **absolute
  Pfade** verwenden.
- `mcp__desktop_commander__read_file` — wenn eine Host-Datei **seitenweise** gelesen
  werden soll: `offset`/`length` in Zeilen (0-basiert, negatives `offset` = vom Ende).
  Dazu `list_directory` (mit `depth`) und `start_process` für lange Läufe. Für grosse
  zeilenorientierte Dateien (Aufgabenlisten, Quellcode im vierstelligen Zeilenbereich)
  der bequemere Leser: `Get-Content` liefert sonst eine abgeschnittene Ausgabe, und ein
  zweiter Aufruf mit mehr Zeilen wiederholt die ganze Abfrage.
- Lokale Werkzeuge lassen sich nicht mit anderen in einem `tool_call` mischen:
  ein Eintrag pro Aufruf.

## Regeln

1. **Schmal abfragen.** Grosse Ausgaben werden abgeschnitten und als Datei
   abgelegt (der Pfad steht im Ergebnis). Dann den Hinweis dort befolgen: gezielt
   mit `read_file` nachlesen, **nicht** dieselbe Abfrage erneut stellen —
   filtern, zaehlen, ein `in`-Ergebnis drucken statt ganze Dateien auszugeben.
   **Rekursion meiden:** `Select-String -Path "<ordner>\**\*.py" -Recurse` oder
   `Get-ChildItem -Recurse` laeuft in `Agenten\Handel` durch `.venv` und reisst
   auch ein 60-180-s-Zeitlimit. Stattdessen eine explizite Pfadliste uebergeben:
   `Select-String -Path "$h\*.py","$h\xperp\*.py"` — kein `-Recurse`.
   **Bei jeder mehrzeiligen Messung die Ausgabe SELBST in eine Datei schreiben**
   (`& $py <skript> > $o 2>&1; 'exit=' + $LASTEXITCODE`) und die Datei mit
   `read_file` lesen. Die Bruecke kuerzt lange Zeilen ab, und ein Zeitlimit
   verwirft die Ausgabe des Aufrufs ganz — die Datei ueberlebt beides.
   `Select-Object -Last N` auf der Konsolenausgabe ist KEIN Ersatz: es kuerzt
   erneut und man sieht nicht, dass gekuerzt wurde. Am Ende der Antwort auf
   die Datei zeigen, nicht die Ausgabe abschreiben.
2. **Erhöhte Rechte bleiben Handarbeit.** Aufgabenplanung mit `-RunLevel Highest`
   kann eine nicht erhöhte Sitzung nicht registrieren („Zugriff verweigert";
   auch `schtasks` scheitert genauso, `Register-ScheduledTask` wirft
   0x80070005). Der fuehrende Weg ist die selbst ausgeloeste Elevation statt
   eines Max-auftrags: `Start-Process powershell -ArgumentList
   '-NoProfile','-ExecutionPolicy','Bypass','-WindowStyle','Hidden','-File','<setup.ps1>'
   -Verb RunAs -WindowStyle Hidden` — das Setup-Skript schreibt ein Log (das
   Fenster ist versteckt) und registriert die Aufgabe fuer den angemeldeten
   Benutzer; der Lauf danach braucht keine Rechte. Danach **lesend** belegen:
   `Get-ScheduledTask`, `Get-ScheduledTaskInfo`, das Log, der Port.
   **Ein erhoehtes `-File`-Skript schreibt seine Ausgabe ins Nirwana.** Das
   Fenster ist versteckt und schliesst sich mit dem Lauf: ohne eigenes Log gibt
   es keine Zeile, und ein terminierender Fehler (`$ErrorActionPreference='Stop'`)
   hinterlaesst GAR keine - der Lauf sieht wie Erfolg aus, waehrend er in der
   Mitte stehen blieb. Das Skript selbst in eine Logdatei schreiben lassen
   (`Start-Transcript`, oder einen Wrapper mit `Tee-Object`), und das Ergebnis am
   ZIEL messen (`Get-CimInstance …`, `Get-ScheduledTask …`, `Test-Path`), nicht am
   Exitcode des Starters: **Exitcode 0 heisst nur, dass der UAC-Dialog bestaetigt
   wurde.** Ein `-Testlauf`/`-Rueckgaengig`-Paar gehoert dazu, und die Idempotenz
   einmal echt zeigen (zweiter Lauf meldet „schon gesetzt") - sonst geht ein
   Abbruch beim ersten Mal als Endstand durch.
   Wird der UAC-Dialog abgelehnt, NICHT erneut aufpoppen: die Arbeit
   vorbereitet hinterlassen (Wrapper + Setup-Skript versioniert) und Max die
   Registrierung als Ein-Zeilen-Aufgabe nennen.
   **Fuer Dauerlaeufer-Aufgaben im Wrapper zwingend:** `ExecutionTimeLimit
   ([TimeSpan]::Zero)` — sonst beendet Windows die Aufgabe nach 72 Stunden;
   `MultipleInstances IgnoreNew`, damit je Trigger nicht eine Instanz
   dazuwaechst; `-WindowStyle Hidden` in der Action. Dem Kindprozess
   `$env:PYTHONIOENCODING='utf-8'` mitgeben: ein per Wrapper gestartetes
   Windows-Python bricht sonst unter der cp1252-Codepage beim ersten
   Emoji-print ab (`UnicodeEncodeError`), waehrend derselbe Code aus einer
   UTF-8-Shell laeuft — die Codepage erbt der Kindprozess vom Wrapper, nicht
   vom Benutzerprofil.
3. **Kein Geheimnis in eine Kommandozeile.** PowerShell gibt Argumente in
   Fehlermeldungen im Klartext aus. Werte in der Datei lassen und nur Länge oder
   Hash ausgeben.
4. **Versionierte Textdateien nicht per Rewrite schreiben** — die Umgebung
   stellt LF auf CRLF um, und aus einer Ein-Zeilen-Änderung wird ein
   Volltext-Diff. In Python `newline=""` setzen, in PowerShell
   `[IO.File]::WriteAllText($p,$t,(New-Object System.Text.UTF8Encoding($false)))`
   verwenden; für `.ps1` und Vault-Markdown gezielter Ersatz (patch/sed), und
   danach den Diff ansehen. Nachkontrolle: `([regex]::Matches($t,"`r`n")).Count`
   muss `0` sein, und `$b[0] -eq 0xEF` wäre ein BOM. **Wie** der gezielte Ersatz
   im Kasten sicher abläuft — Anker, Trefferzahl, Nutzlast — und die drei
   PowerShell-Fallen dabei: Abschnitt „Skripte im Kasten ändern" unten.
5. **Ergebnis zeigen, nicht behaupten.** Ein Befehlsaufruf ist kein Nachweis:
   Zustand über eine zweite, lesende Abfrage belegen (Status, Zähler, ID). Für
   Schreibvorgänge gilt das doppelt — ein Schreibwerkzeug kann `verified: true`
   melden und trotzdem woanders geschrieben haben. Vor jeder Meldung „angelegt"
   die Datei über `windows-mcp` nachlesen: Größe, Zeilenzahl, Hash. **Gilt auch
   fürs Löschen:** `rm -rf` auf einen nicht existierenden (relativen) Pfad
   meldet still Erfolg — nach jedem Löschvorgang mit `ls` gegenprüfen, dass das
   Ziel wirklich fehlt, und den Pfad vorher auf den richtigen Elternordner
   prüfen (ein Ziel, das unter `Werkstatt/` liegt, ist ohne Präfix nicht
   erreichbar).
6. **Einen langen Lauf nicht synchron abwarten.** Die Brücke bricht nach 300 s
   ab, und eine Routine, deren echter Durchlauf Minuten bis eine halbe Stunde
   braucht (vollständige Archiv-Scans), ist so nicht nachweisbar. Die geänderte
   Phase schreibt ihr Protokoll aber innerhalb von Sekunden: den Protokollkopf
   lesen und belegen, was dort steht, den Rest dem geplanten Lauf überlassen.
   Dabei offen sagen, dass der Durchlauf nicht end-to-end belegt ist — und die
   Anschlussprüfung beim nächsten geplanten Lauf nachholen.
   Ein `Start-Sleep` **innerhalb** eines MCP-Aufrufs ist der zweite Fehlerfall:
   dauert er länger als das Limit, kommt der ganze Aufruf als `TimeoutError`
   zurück und die Ausgabe des Befehls ist verloren — Warten und Messen trennen
   (kurz warten, dann in einem EIGENEN Aufruf lesen) oder den Lauf als
   Hintergrundprozess starten und seinen Status abfragen.
   **Ein `TimeoutError` heisst NICHT, dass der Kindprozess tot ist** — er laeuft
   weiter und schreibt seine Ausgabe. Beim naechsten Aufruf also NICHT neu
   starten, sondern die Ausgabedatei lesen (`(Get-Content <log>).Count`,
   `-Tail 5`) und die Prozessliste pruefen. Ein zweiter Start legt sonst einen
   zweiten Lauf auf dieselbe Sperre.
   **Fuer eine lange Suite die Umleitung per `cmd /c` nehmen:**
   `cmd /c '<exe> -m unittest a b > <log> 2>&1'`, danach `$LASTEXITCODE` und die
   Datei lesen. Das traegt auch dann, wenn `Start-Process -PassThru` leer
   zurueckkommt (kein PID, keine Datei) — in dem Fall den Aufruf **einmal** mit
   der `cmd /c`-Form wiederholen und erst dann urteilen. Ein leerer PID ist noch
   kein Befund ueber das Programm.
7. **Eine Messung ist ein Zeitpunkt, kein Zustand.** Auf diesem Rechner arbeiten
   mehrere Sitzungen und Agenten gleichzeitig am selben Baum: zwischen zwei
   Aufrufen können Ordner auftauchen oder verschwinden (eine parallele
   Wiederherstellungsprüfung räumt um), Gigabyte umziehen und `config.yaml` neu
   geschrieben werden. Deshalb **nie aus einem einzigen Aufruf** schließen „X
   gibt es nicht" — das ist die teuerste falsche Aussage, weil sie eine Arbeit
   als unmöglich abtut, die es gibt. Vor jeder Behauptung frisch nachlesen, den
   Messzeitpunkt nennen („zuletzt gelesen um …") und bei einem Befund, der
   einer anderen Beobachtung widerspricht, **beide** Messungen zeigen statt eine
   auszuwählen. Für Erfolgsmeldungen gilt dasselbe doppelt: die Zahl vorher
   **und** nachher im selben Durchgang messen, nicht die von vor einer Stunde
   übernehmen.

## Skripte im Kasten ändern (Ersatz statt Rewrite)

Regel 4 verlangt gezielten Ersatz. Die Mechanik, sonst kostet sie einen
ganzen Durchgang:

```powershell
$t = [IO.File]::ReadAllText($f)
$paare = @()
$paare += ,@($alt, $neu)   # NICHT @( ,@($a,$b), ,@($c,$d) ): das flacht ab,
                           # $p[0] ist kein String mehr, jeder Anker trifft 0x
foreach ($p in $paare) {
  $c = ([regex]::Matches($t, [regex]::Escape($p[0]))).Count
  if ($c -ne 1) { throw "Anker $c mal gefunden: $($p[0])" }
}
foreach ($p in $paare) { $t = $t.Replace($p[0], $p[1]) }
[IO.File]::WriteAllText($f, $t, (New-Object System.Text.UTF8Encoding($false)))
```

- **Je Anker die Trefferzahl drucken und nur bei genau 1 schreiben.** Ein stiller
  Nulltreffer sieht aus wie ein gelungener Ersatz, bis man die Datei zurückliest
  — und die Änderung fehlt dann.
- **Anker über ganze Zeilen legen.** Ein Anker, der mitten in einer Zeile endet,
  trifft nie; die Datei führt die Zeile weiter.
- **Den Anker mit den Zeilenenden der Zieldatei bauen.** Erst messen
  (`([regex]::Matches($t,"`r`n")).Count`), dann den Anker mit demselben Umbruch
  schreiben. Ein LF-Anker trifft eine CRLF-Datei nie. Die Umbruch-Art ist von
  Datei zu Datei verschieden, auch innerhalb desselben Ordners — nicht aus der
  Nachbardatei schliessen.
- **Anker ASCII halten.** Ein Emoji oder ein anderes Zeichen ausserhalb des BMP
  kommt durch die Werkzeugschicht verstümmelt an und trifft nie. Den Absatz an
  einer emoji-freien Zeile anfassen.

Beide Fälle melden sich wie ein gewöhnlicher Nulltreffer. Der Unterschied ist
nur, wo man nachfasst: nicht an der Datei, sondern am Anker.
- **Nutzlast als einfach-quotierte Here-String** schreiben: `$` und Backtick
  bleiben dann literal, statt als Escape gefressen zu werden.
- **Native Werkzeuge schreiben Fortschritt auf stderr.** Mit
  `$ErrorActionPreference='Stop'` und `2>&1` bricht ein `.ps1` mitten im Lauf ab
  (NativeCommandError), weil `git` und `hermes.exe` ihre Fortschrittszeilen als
  Fehler liefern. `Continue` setzen, `git clone --quiet` verwenden und Erfolg am
  Exit-Code bzw. am Ergebnis prüfen — nicht am Ausbleiben von Fehlertext.
- **Zweimal geänderte Datei unter eigenem Namen sichern.** Ein zweites
  `.bak-<JJJJMMTT>` am selben Tag überschreibt genau den Stand, den es erhalten
  sollte; Zeitstempel anhängen.
- **Suchmuster in deutschen Texten gegen BEIDE Schreibweisen pruefen** — Umlaut
  UND ASCII-Umschreibung (`geändert`/`geaendert`). Ein Filter, der nur eine
  Form kennt, findet die andere nicht, und ein Nulltreffer liest sich wie
  „nichts offen" statt wie ein Fehler (belegt: ein Statusabschnitt meldete
  leer, obwohl sechs Statuszeilen existierten). Die echten Statuswoerter aus
  der Quelle ablesen (nie aus dem Kopf) und einen Nulltreffer mit einer
  Zaehlung der Quelldatei gegenrechnen, bevor „nichts da" gemeldet wird.

### Fallen, die anders aussehen als sie sind

- **Eine Referenz mit der FALSCHEN ENDUNG meldet „No such file or directory"
  und sieht wie eine verschwundene Datei aus.** `git commit -F <pfad>` (und jedes
  andere native Programm, das eine Pfadangabe bekommt) liest genau den Pfad, den
  man getippt hat: wird die Meldung als `.md` geschrieben und mit `-F ….txt`
  referenziert, bricht der Commit mit `could not read log file` ab, waehrend die
  Datei unversehrt daneben liegt. Das Schreibwerkzeug hatte Erfolg gemeldet
  (`bytes_written`), also existiert die Datei — unter dem Namen, den man ihm
  GEGEBEN hat. Vor jedem „die Datei ist weg": das Verzeichnis auflisten und den
  Namen lesen, statt den Dateischwund zu diagnostizieren. Gilt genauso fuer
  Endungs-Verwechslungen bei `.json`/`.yaml`/`.csv`-Zielen.
- `Split-Path -LiteralPath <datei> -Leaf` liefert leer (in 7.x gesehen). Daraus
  entsteht ein Ziel ohne Dateinamen, und Windows PowerShell 5.1 bricht mit
  `AmbiguousParameterSet` / „Parametersatz kann nicht aufgelöst werden" ab — die
  Meldung zeigt auf die Cmdlet-Bindung, nicht auf das leere Argument.
  `[System.IO.Path]::GetFileName()` und `[System.IO.File]::Move()` /
  `[System.IO.Directory]::Move()` verhalten sich auf beiden Versionen gleich.
- `exit` in einem Skript, das aus einem `try`-Block aufgerufen wird, beendet auch
  den umgebenden Block. Die Anweisungen danach entfallen still — samt der
  Ausgabe, die den Befund belegen sollte. Solche Skripte als eigenen Prozess
  starten (`& powershell -File <skript>`): das kapselt `exit` und lässt
  `$LASTEXITCODE` lesbar.
- `$pid` ist eine schreibgeschützte automatische Variable; `foreach ($pid in
  $liste)` iteriert nie und meldet still nichts.
- **Ein Schalter und eine Variable sind dieselbe Variable.** Namen werden
  case-insensitiv verglichen: `[switch]$Alle` und die Datenliste `$alle` sind
  eins, die Zuweisung `$alle = ...` überschreibt also den Schalter. Das Skript
  läuft fehlerfrei durch und liefert still ein einziges Ergebnis statt Hunderter.
  Schalter und Datenvariablen immer unterschiedlich benennen
  (`-MitKopien` / `$skills`).
- **Ein selbst-aktualisierendes Programm kann sich auf Windows nicht selbst
  ersetzen.** `onchainos upgrade --force` meldet `failed to replace binary:
  Zugriff verweigert (os error 5)` — auch wenn der Ordner schreibbar ist, keine
  Instanz läuft und die Datei kein ReadOnly trägt: die laufende Datei ist das
  Abbild des laufenden Prozesses, und Windows verweigert das Überschreiben.
  Der Weg, der trägt, ist der Tausch **von außen**: Release-Asset der
  offiziellen Quelle laden, `sha256` gegen die mitgelieferte `checksums.txt`
  prüfen, die alte Datei **umbenennen** (umbenennen geht, überschreiben nicht)
  und die neue hineinkopieren — dann `--version` und einen echten Leseaufruf als
  Rauchprobe, mit der alten Fassung als `.bak-<JJJJMMTT>` daneben. Denselben
  Ablauf bei jeder anderen selbst-aktualisierenden CLI erwarten.
- **`sha256sum` in der MSYS-Bash stellt der Prüfsumme einen Backslash voran**,
  wenn sie mit einer Ziffer beginnt (`\0714f1a4…`). Der Vergleich gegen die
  Sollsumme schlägt dann fehl, obwohl die Summe stimmt. Vor dem Vergleich
  entfernen (`tr -d '\\'`) — sonst wird eine korrekte Datei als Abweichung
  gemeldet und die Arbeit unnötig wiederholt.
- **Ein Prüfer sucht Kommandos auf dem PATH, nicht im Projekt-venv.** „Werkzeug
  fehlt“, obwohl die Datei im venv liegt: viele Prüfer rufen `shutil.which("<name>")`
  oder starten `<name> --version`. Dann muss ein Shim im PATH liegen — sauber ohne
  PATH-Bearbeitung: `uv tool install <paket>` legt ihn nach `~\.local\bin`, das im
  Benutzer-PATH steht. Danach mit `which <name>` **und** dem Prüfer erneut belegen.
  Und beim Prüfer nachsehen, WAS er verlangt (Datei, Dienst, Browser-Erweiterung,
  Anmeldung) — die Meldung nennt oft den genauen Befehl, das Raten kostet mehr.
- **Ein zu großer oder gemischter Inline-Befehl wird von der Werkzeugschicht
  abgewiesen**, nicht von der Shell: die Antwort ist ein Block, der auf den
  gespeicherten Skriptpfad verweist, mit dem Auftrag, **nicht inline zu
  wiederholen**. Auslöser sind Einzeiler, die Here-Doc, `grep`, `sed` und
  mehrzeiligen Text in einem Aufruf mischen. Statt zu wiederholen: in mehrere
  kleine Aufrufe teilen, oder die Logik in eine Datei schreiben und diese
  starten — ein Werkzeugaufruf gehört nicht in einen Satz Text.
- **PowerShell-Code gehoert in eine `.ps1`-DATEI, nicht inline durch die
  bash-Schicht.** Die Terminal-Schicht ist bash: sie liest den Backtick als
  Kommando-Substitution. Ein PowerShell-String mit Backtick-Escapes
  (`` `t `` fuer Tabulator, `` `r`n ``) wird deshalb von bash verarbeitet — das
  Ergebnis ist entweder ein Abbruch („syntax error near unexpected token") oder,
  schlimmer, eine **halb-leere, kaputte Ausgabe**, die wie eine Messung
  aussieht: gemessen lieferte `'{0}`t{1}' -f $name, $wert` Namen ohne Zahl, und
  die Liste fiel auf drei von 15 Zeilen zusammen. Richtig: die Logik mit
 `write_file` als `.ps1` unter `Agenten/Hermes/cache/scratch/` ablegen
 (`$ErrorActionPreference='Continue'`, keine Backtick-Formatstrings noetig),
 mit `powershell -NoProfile -ExecutionPolicy Bypass -File <pfad> > <out> 2>&1`
 starten und `<out>` mit `read_file` lesen. Der `<pfad>` aus der bash-Schicht
 braucht SCHRAEGSTRICHE (`Agenten/Routinen/x.ps1`) — Backslashes im Argument
 werden von bash gefressen (`-File Agenten\Routinen\x.ps1` wird zu
 `AgentenRoutinenx.ps1` und PowerShell meldet „nicht vorhanden", obwohl die
 Datei liegt); PowerShell nimmt Vorwaerts-Slashes genauso an. Dieselbe Regel gilt fuer jedes
  Fremdwerkzeug mit `$`, Backtick oder `%` in den Argumenten — Datei statt
  Einzeiler, und `2>/dev/null` weglassen, sonst verschluckt sie die Ursache.
  **Auch ein doppelt-quotierter `-Command "…"`-String ist bash-Land:** bash
  expandiert `$name` VOR PowerShell, das Skript sieht eine leere Variable und
  meldet still Erfolg — gemessen blieb ein so gesetzter PATH-Eintrag einfach
  aus, ohne Fehlermeldung. Am haeufigsten beisst `$_`: bash kennt ES als
  „letztes Argument des vorherigen Kommandos" und ersetzt es IMMER durch einen
  Pfad — ein `Where-Object { $_.ProcessId -eq N }` inline kommt kaputt an
  (Syntaxfehler mit dem Pfad statt `$_` im Text; gemessen dreimal mit
  `powershell -Command` aus bash). PowerShell-Variablen also nicht in einen
  doppelt-quotierten Inline-String schreiben: `.ps1` per `-File` starten
  (immer die verlaessliche Form), oder mindestens einfach quotieren, damit `$`
  literal ankommt.
- **`cmd //c <wrapper>.cmd` aus bash kann nur den cmd-Banner drucken und die
  Batch-Datei NICHT ausfuehren** (gemessen: Log enthielt nur die
  Versionszeile und den Prompt, kein Skript-Output). Der Aufruf meldet
  Erfolg — es ist kein Fehlschlag mit Meldung, sondern ein Nichtstart. Vertrau
  nie dem Wrapper-Output: die Wirkung am ZIEL pruefen (Prozessliste + frische
  Statusdatei-mtime nach dem erwarteten Start), oder den Befehl, den der
  Wrapper ausfuehren wuerde, direkt als Hintergrundprozess starten
  (`./target/debug/...exe live ... > log 2>&1`) und danach die Statusdatei
  lesen — ein lebender Lauf schreibt sie weiter.
- **Dasselbe fuer Python-Code: Datei statt Heredoc.** Ein Heredoc
  (`python - <<'PY' … PY`) durch die Terminal-Schicht loest die Fluchtfolgen VOR
  Python auf — aus dem zweibuchstabigen `\n` INNERHALB eines String-Literals wird ein
  echter Zeilenumbruch, und die Zieldatei traegt danach
  `SyntaxError: unterminated string literal`. Der Befehl selbst meldet Erfolg; der
  Fehler faellt erst beim naechsten Lauf auf (ein Cron-Skript stand so stundenlang
  still, ohne dass es jemandem auffiel). Richtig: das Schreib-/Reparaturskript mit
  `write_file` auf die Platte legen und ausfuehren, oder das `patch`-Werkzeug nehmen.
  Muss es doch inline sein, die Fluchtfolge aus `chr(92) + "n"` bauen statt als
  Literal — und die geaenderte Datei danach mit `ast.parse` parsen.
- **Auch eine PowerShell-Ersetzung gehoert in eine DATEI, nicht in einen
  `-Command`-Einzeiler.** Derselbe Grund, teurer: ein mehrzeiliger neuer Text
  braucht in PowerShell Backtick-Escapes (`` `n `` fuer Zeilenumbruch), und die
  kommen durch die Werkzeugschicht verstuemmelt an. Gemessen: zwei Anlaeufe, beide
  `Status Code 1` — einmal ein stiller Nichtlauf ohne jede Ausgabe, einmal ein
  `ParserError` (`Nach „(“ wurde ein Ausdruck erwartet`), weil der Backtick-Ausdruck
  im Quelltext als Code gelesen wurde. Beide Male war das Skript NICHT angewendet,
  und der stille Fall sah wie ein Erfolg aus (`OK: gepatcht` kam aus der
  Shell-Zeile, nicht aus dem Schreibvorgang).
  **Verlaesslicher Weg fuer eine Textersetzung auf dem Host:** den Ersatz als
  **Python**-Skript schreiben (nicht PowerShell) — `write_file` auf
  `Agenten/Hermes/cache/scratch/<zweck>.py`, darin die Datei per
  `open(p,"rb").read()`, `assert text.count(anker) == 1`, `replace`, und
  `open(p,"wb").write(...)`; dann
  `python <pfad>` ueber `mcp__windows_mcp__PowerShell` starten. Python hat keine
  Backtick-Escapes, die Assertion belegt den Treffer, und der Exitcode ist
  eindeutig. PowerShell bleibt fuer alles, was WIRKLICH PowerShell ist (Dienste,
  Registry, Aufgabenplanung, Prozesse).
  **Nach JEDEM Host-Schreibvorgang die Wirkung nachlesen, nicht den Exitcode
  glauben:** `Select-String -Path <datei> -Pattern '<neuer text>'` bzw.
  `grep -n` — gemessen war die Datei nach dem „OK" unveraendert. Derselbe Blick
  zeigt, ob der Ersatz an der richtigen Stelle landete.
- **Syntax mit `ast.parse` pruefen, nicht mit `py_compile`.**
  `py_compile.compile(p, doraise=True)` wirft `PyCompileError` (kein `SyntaxError`) —
  ein `except SyntaxError` greift nicht, und eine Reparatur per `lineno` laeuft ins
  Leere. `ast.parse(text)` wirft `SyntaxError` MIT `lineno`. Nach jeder
  Massenaenderung alle angefassten `.py` einmal durchparsen; „0 kaputte Dateien" ist
  der Beleg.
- **Ein Regex, das in Aufruf-Argumente einfuegt, braucht echtes Klammer-Matching —
  sonst landet die Einfuegung NACH der schliessenden Klammer oder verschluckt sie.**
  Ein `re.sub` auf `subprocess.run(...)` mit einem naiven `[^)]*`-Muster findet die
  ERSTE schliessende Klammer, nicht die zum Aufruf gehoerende: das eingefuegte
  `creationflags=...` steht dann ausserhalb des Aufrufs (kompiliert als Tupel,
  wirkt aber nicht) oder die schliessende Klammer fehlt ganz (SyntaxError erst beim
  naechsten Lauf). Nach JEDEM solchen Massen-Patch: (1) `ast.parse` ueber alle
  Dateien, (2) die eingefuegte Zeile visuell pruefen, dass sie VOR der schliessenden
  Klammer steht, (3) nach dem Muster `else 0,` + Nicht-Klammer-Zeile suchen (fehlende
  Klammer). Ein zeilenbasiertes Einfuegen (Flag in die Zeile mit `capture_output=True`
  legen) ist robuster als ein Aufruf-Regex, weil es die Klammerposition nie anfasst.
- **Skript unter 5.1 auf Syntax prüfen:** `[Parser]::ParseFile($p,[ref]$null,[ref]$err)`
  und bei Treffern Zeile und Meldung ausgeben. Häufigste Ursache: `\"` ist in einem doppelt-quotierten
  PowerShell-String **kein** Escape — die Zeichenkette endet zu früh und der Rest
  wird als Code gelesen („Der Operator "<" ist für zukünftige Versionen
  reserviert"). Backtick-Quoting benutzen oder auf einfach-quotierte Strings
  ausweichen. Ein Parse-Fehler führt das ganze Skript nicht aus: es gibt keine
  Teilausgabe, an der man den Fehler festmachen könnte.
- **`.Count` auf einem Einzelobjekt aus der Pipeline ist in 5.1 LEER** — nur
  Arrays zählen. `$x | Where-Object … | Sort-Object …` liefert bei genau einem
  Treffer ein Skalar, und `$ergebnis.Count` wird `$null`: Gruppenköpfe zeigen
  `(0)`/`()` und Trefferzeilen verlieren ihre Zahl. Vor jeder Zählung
  `@(...)` um die Pipeline legen — `@($x | Where-Object …).Count` zählt auch
  Einzelobjekte (und leere Mengen) korrekt.
- **In `@("# " + $var, '…')` gewinnt das Komma gegen das Plus** — PowerShell
  bindet den Komma-Operator stärker, die ganze Liste wird EIN String und der
  Kopf einer generierten Datei steht in einer Zeile. Den ersten Ausdruck vorher
  in eine Variable legen und diese in das Array schreiben.
- **`Get-Content` ohne `-Encoding UTF8` liest UTF-8-Dateien als ANSI** —
  Umlaute und alle Nicht-ASCII-Zeichen (auch chinesische Beschreibungen)
  werden zu Mojibake, das beim Weiterschreiben in die Datei gelangt. Beim
  Lesen von Skript- und Skill-Dateien immer `-Encoding UTF8` angeben; beim
  beim Schreiben `[IO.File]::WriteAllText` mit explizitem UTF8Encoding.
  - **`Start-Process -ArgumentList` zerlegt Inline-Code an den Leerzeichen.**
    `-ArgumentList '-c','from x import y; tu_was()'` uebergibt dem Kind nur das
    erste Wort; es stirbt mit `SyntaxError: invalid syntax` auf `from`, und der
    Auftrag liest sich wie ein kaputtes Skript oder ein fehlendes Modul. Inline-Code
    gehoert in eine DATEI; die Datei per `-ArgumentList <skriptpfad>` starten.
  - **Ein Lauf, der laenger dauert als das Bruecken-Limit, als abgekoppelten
    Prozess starten — nicht synchron warten.** `Start-Process -FilePath <exe>
    -ArgumentList <skript> -WorkingDirectory <ordner> -RedirectStandardOutput
    <datei> -RedirectStandardError <datei>.err -PassThru -WindowStyle Hidden`,
    dann NICHT `Wait-Process` (das erschiesst den Aufruf am Limit). Die Datei
    waechst weiter, waehrend der Aufruf schon zurueckkam; Status und Ergebnis in
    einem SPAETEREN Aufruf lesen (Groesse der Datei, `.HasExited`). Ein Import
    ueber hunderte Module kann minutenlang bei wenigen MB Speicher haengen, ohne
    Fehler und ohne Ausgabe — das ist kein Fortschritt: nach der Frist per PID
    beenden (`Stop-Process -Id <pid> -Force`) und den Zustand als "nicht
    gemessen" berichten statt eine Zahl zu erfinden.

**Die Werkzeugschicht ist nicht der Interpreter der Aufgabe.** Sie ist 7.x, die
Aufgabenplanung startet `%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe`
(5.1). Was unter 7 parst und läuft, kann unter 5.1 scheitern — vor „fertig" das
Skript oder wenigstens einen Trockenlauf unter der 5.1-Bahn laufen lassen.

## Massenlaeufe und git: erst den Commit-Spielraum messen, dann auf den Host

Massenlaeufe (viele `git`-Aufrufe, Subprozesse je Datei, Modellstarts) brechen im
Kasten mit **`OSError: [WinError 1455] Die Auslagerungsdatei ist zu klein`** ab —
oder MSYS meldet `fork: Resource temporarily unavailable` / `child_copy: cygheap
read copy failed`. Das ist kein Skriptfehler und keine kaputte Shell: Windows kann
den Speicher nicht mehr *zusagen* (Commit), weil viele Prozesse reserviert haben.

- **Spielraum messen, nicht raten:** `$o = Get-CimInstance Win32_OperatingSystem;
  '{0:N0} MB frei von {1:N0} MB' -f ($o.FreeVirtualMemory/1KB),
  ($o.TotalVirtualMemorySize/1KB)`. Ein Modellstart braucht mehrere GB Spielraum;
  unter ~2 GB freiem Commit scheitert er mit
  `ggml_backend_cpu_buffer_type_alloc_buffer: failed to allocate buffer`.
- **Der RAM ist die falsche Zahl.** 28 GB freier RAM und trotzdem kein Commit
  ist der Normalfall — die Reservierungen zaehlen, nicht der belegte Speicher.
- **Erster Verdaechtiger sind geleakte Kindprozesse desselben Programms**, nicht
  der Massenlauf selbst: Prozesse nach dem Kommandozeilen-MUSTER des Kindes
  gruppieren (nicht nach Namen) und die Generationen zaehlen. Erwartet ist EINE
  Generation je laufendem Zyklus.
- **Ausweg:** denselben Lauf ueber `mcp__windows_mcp__PowerShell` auf dem Host
  fahren (eigener Prozessbaum, eigener Adressraum) und danach dieselbe Messung
  wiederholen. Das ist die Regel fuer alles, was viele Kindprozesse startet:
  der Kasten ist fuer Einzelabfragen da, nicht fuer Flottenlaeufe.
- **Ein abgebrochener `git commit` ist kein Datenverlust.** Erneut versuchen —
  `git status` zeigt danach den echten Stand; ein `index.lock` mit falschem Alter
  stammt aus dem Abbruch und wird umbenannt, nicht geloescht.

### Die Commit-Grenze selbst einstellen (Auslagerungsdatei)

RAM + Auslagerungsdatei = Commit-Grenze. Ist sie zu klein, ist das mit keinem
Programm zu beheben — die 2004-Ereignisse (Resource-Exhaustion) und
`0xc000012d` (STATUS_COMMITMENT_LIMIT) sind die FOLGE, nicht die Ursache. Die
Datei muss groesser werden.

- **Autoritativer Weg ist die Registry**, genau das, was die Windows-GUI
  schreibt: `HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory
  Management` -> `PagingFiles` (`REG_MULTI_SZ`, je Zeile
  `<Laufwerk>:\pagefile.sys <AnfangMB> <MaximumMB>`). `Win32_PageFileSetting`
  zeigt danach den Stand, `Win32_ComputerSystem.AutomaticManagedPagefile` sagt,
  ob Windows selbst verwaltet.
- **Die WMI-Klasse hat eine Typfalle:** `New-CimInstance -ClassName
  Win32_PageFileSetting` scheitert mit „Typenkonflikt fuer die Eigenschaft
  InitialSize" (die Klasse verlangt `UInt32`, die Parameteruebergabe liefert
  `Int32`). Mit `$ErrorActionPreference='Stop'` stirbt das Skript dort — und
  still, wenn die Ausgabe nicht mitgeschrieben wird. `[uint32]` casten.
- **Fest statt selbstverwaltet, wenn das Laufwerk knapp ist.** Eine
  selbstverwaltete Datei waechst bis zum Maximum und fuellt das Laufwerk
  (gemessen: C: mit 19 GB frei, Datei bei 21 GB). Anfang = Maximum setzen und die
  grosse Datei auf das Laufwerk mit Platz legen.
- **Die Wirkung kommt erst beim NEUSTART.** Die Dateien werden beim Start
  angelegt; `TotalVirtualMemorySize`/`FreeVirtualMemory` und die Existenz der
  Datei aendern sich vorher nicht. Also nicht „erledigt" melden, sondern „gesetzt,
  wirkt nach dem Neustart" plus eine Nachpruefung als Aufgabe — und vorher sagen,
  dass ein Neustart die laufenden Dauerprozesse beendet (Boersen-Stops der
  Live-Positionen liegen bei der Boerse und greifen weiter).

## Prozess-Befunde: erst die eigene Kette, dann Urteile

- **Vor jedem Beenden von Prozessen die EIGENE Kette lesen.** Von `$PID`
  aufwaerts die Elternkette wandern (`Win32_Process` je `ParentProcessId`);
  die Kette endet im Hermes-Gateway (`-m hermes_cli.main gateway run`) und
traegt die windows-mcp-Prozesse, die die eigenen Tool-Aufrufe bedienen. Eine
Beendeliste muss diese PIDs ausschliessen — erst pruefen, dann beenden.
- **Zwei MCP-Server-Generationen sehen aus wie Waisen, sind aber eine zweite
  Installation.** Verwaiste MCP-Server haben oft einen LEBENDEN Ahnherrn: ein
dashboard/`serve` einer frueheren Hermes-Installation (anderer Checkout-Pfad
in der Kommandozeile, z. B. `C:\Hermes\…` gegen `BrainFiles\Agenten\Hermes\…`)
haelt seinen eigenen Server-Satz. Der Ahnherr entscheidet, nicht der
Prozessname: fuer jeden Kandidaten die Kette bis zur Wurzel aufloesen und die
Kommandozeile der Ahnherren zeigen. Solche Server kommen nach dem Beenden
wieder, solange ihr Ahnherr laeuft.
- **Prozesse nach der KOMMANDOZEILE gruppieren, nicht nach dem Namen:** ein
venv-Python ist ein Launcher-Shim + echtes Python mit identischer
Kommandozeile; mehrere „gleiche" Prozesse sind oft 2N einer Handvoll
Instanzen. Instanzen zaehlen = Paare nach `CreationDate` gruppieren.

## Subagenten an den Host anschliessen

Delegierte Subagenten bekommen ein eigenes Terminal — auf diesem Rechner ist
das die Sandbox, `C:\` ist fuer sie unsichtbar. Wer ihnen Arbeit am Host gibt
(Code lesen, greppen, git), muss in den TASK-KONTEXT schreiben:

1. Das Host-Werkzeug-Rezept (`tool_describe` + `tool_call` auf
   `mcp__windows_mcp__PowerShell`/`FileSystem`, ein lokales MCP-Werkzeug je
   Aufruf, schmal filtern, grosse Ausgaben werden abgeschnitten).
2. Absoluter Pfad der zu pruefenden Datei ODER eines vorbereiteten
   Patch-Files (grosse Diffs nicht in den Prompt kopieren — der Pfad reicht).
3. Den Hinweis, dass Ausgaben verlustig ankommen koennen: sich kritische
   Stellen selbst per base64 holen
   (`[Convert]::ToBase64String([IO.File]::ReadAllBytes($f))`).

Ohne dieses Rezept koennen Review-Subagenten nur raten — ein Befund ohne
Host-Beleg ist dann ein Hinweis, keine Tatsache.

## GUI-Automation über windows-mcp: Klicks landen auf dem falschen Fenster

Snapshots liefern Koordinaten, aber die Wahrheit entscheidet die Z-Ordnung:

- **Der Klick geht an das OBERSTE Fenster an der Stelle, nicht an das im
  UI-Tree gelistete.** Ein grosses Terminal oder ein maximierter Browser in
  Depth 8 frisst Klicks, die für ein dahinter liegendes Fenster (Depth 45)
  gedacht waren — der Snapshot listet beide, der Klick trifft nur den
  Vordergrund. Vor dem Klicken das Zielfenster per Win32 nach vorne holen:
  `Add-Type` mit `user32.dll`, `SetForegroundWindow($h)` UND
  `SetWindowPos($h, -1, 0,0,0,0, 0x0001 -bor 0x0002)` (HWND_TOPMOST); nur
  Foreground reicht nicht immer. Oder Tastatur statt Maus: `Shortcut enter`
  auf das Element mit `has_focused: 1` im UI-Tree.
- **Tray-Menues sind die verlaesslichere Koordinate.** Ein Rechtsklick auf
  das Taskleisten-Icon (fester Platz, keine Z-Ordnung) oeffnet ein
  Kontextmenue mit den Aktionen, die man im Fenster sucht — und der UI-Tree
  des Menues liefert die Punkt-Koordinaten direkt.
- **Koordinatensysteme der Screenshot-Backends unterscheiden sich.** pillow-
  und dxcam-Snapshots melden unterschiedliche Originalgroessen (z. B.
  3847x2167 gegen 3840x2160); Bildkoordinaten nur mit dem Skalierungsfaktor
  des jeweiligen Backends auf Klick-Koordinaten umrechnen, nicht mischen.
- **GetWindowRect liefert in nicht-DPI-aware PowerShell virtuelle Pixel.**
  Bei 150 %-Skalierung meldet powershell.exe 5.1 ein Fenster als 1066x719
  bei (99,616), physisch ist es 1599x1079 bei (149,924) — Klicks mit den
  virtuellen Koordinaten landen 1,5x daneben. Vor jedem Koordinatenwechsel
  `SetProcessDPIAware()` (user32.dll) aufrufen und die Position FRISCH
  lesen; der Skalierungsfaktor ist physische/virtuelle Fensterbreite und
  multipliziert ALLE aus Bitmaps abgeleiteten Offsets.
- **Tkinter-Widgets erscheinen NICHT im UI-Tree von Snapshot.** Tk zeichnet
  seine Controls selbst; der Tree listet nur Fensterrahmen, Menues und
  Taskleiste. Button-Koordinaten aus dem Quelltext-Layout ableiten
  (pack-Reihenfolge, Padding) oder per Fenster-Capture messen — nie im
  UI-Tree suchen.
- **Nur das Zielfenster capturen statt des ganzen Desktops:**
  `user32.dll PrintWindow(hwnd, dc, 2)` auf einen System.Drawing-Graphics-
  Context rendert genau EIN Fenster in eine PNG — funktioniert auch hinter
  anderen Fenstern und auf anderen virtuellen Desktops und zeigt keine
  fremden privaten Inhalte. Das Bitmap liegt im VIRTUELLEN Pixelraum (bei
  150 % also 1066x719 fuer ein 1599x1079-Fenster): Offsets daraus vor dem
  Klick mit dem Skalierungsfaktor multiplizieren.
- **Python-GUI mit RedirectStandardOutput starten: die Logdateien bleiben
  LEER.** Ohne TTY puffert Python stdout blockweise; ein laufender
  Tk-Knoten schreibt nichts in die umgeleitete Datei. GUI-Start nie ueber
  die Redirect-Datei belegen — erst den Fensterzustand pruefen
  (PrintWindow-Capture/Statuszeile).
- **`-WindowStyle Hidden` versteckt auch das Tk-Hauptfenster.**
  `Start-Process -WindowStyle Hidden` auf einen Python-Tk-Knoten macht das
  Fenster unsichtbar, waehrend der Prozess laeuft. Fuer sichtbare GUIs
  nicht verwenden; die Konsole des Wrappers ist davon getrennt regelbar.

## Aufblitzende Konsolenfenster / Fokus-Klau: der ELTERNprozess ist die Quelle

Wenn „alle paar Sekunden poppt ein Fenster auf und raubt den Fokus" (kurz
aufblitzende cmd/powershell/git-Fenster), liegt die Ursache fast nie am Kind,
sondern am Elternprozess:

- **Ein GUI-Subsystem-Elternprozess (pythonw.exe, Electron) hat keine Konsole —
  jedes Konsolen-Subsystem-Kind (git.exe, gh, cmd, onchainos, powershell …)
  legt deshalb sein EIGENES sichtbares Fenster an.** Das gilt je Spawn: ein
  Dauertakt, der ein Konsolen-Kind startet, blitzt je Takt.
- **`windowsHide: true` ist gegen einen GUI-Eltern WIRKUNGSLOS.** Das Flag
  wirkt nur, wenn der Elternprozess selbst eine Konsole besitzt; ein
  GUI-Prozess hat keine, auf die es einwirken koennte (Hermes dokumentiert das
  in `apps/desktop/electron/main.ts` wörtlich: „A GUI-subsystem parent has no
  console, so every console-subsystem child must allocate its own — which
  flashes a window").

**Diagnose: die NEUEN zaehlen, nicht den Bestand.** Eine hohe Zahl vorhandener
`conhost.exe` ist kumulierter Bestand und beweist keinen Takt. Ueber ein festes
Fenster (30–45 s, in 3–5-s-Schritten) alle NEU entstandenen
`conhost`/`cmd`/`powershell` mit `ParentProcessId` aufzeichnen und die Eltern
per `Win32_Process` nach `Name`/`CommandLine` aufloesen. Der Elternprozess ist
die Quelle — nicht der fluechtige Kindprozess, der beim Nachschauen oft schon
wieder tot ist. Typisch: ein GUI-Eltern ruft ein Konsolen-Tool auf (Electron
pollt `git`, ein pythonw-Daemon startet CLI-Kinder).

**Fix: den spawenden Prozess auf Konsolen-Subsystem stellen, nicht jeden
Kind-Spawn.** Einen pythonw-Daemon durch `python.exe` ersetzen und dessen
Konsole versteckt starten (`Start-Process -FilePath python.exe -WindowStyle
Hidden`). Dann besitzt der Elternprozess EIN fensterloses Konsolenfenster, das
alle Kinder erben — kein Kind legt mehr ein eigenes sichtbares an; `-WindowStyle
Hidden` trifft nur die Konsole des Parents, nicht die Arbeit der Kinder. Fuer
einen DAEMON ohne eigenes Fenster ist der Wechsel gefahrlos; eine sichtbare
GUI (Tk-Hauptfenster) hat den eigenen Konflikt oben (`-WindowStyle Hidden`
versteckt auch das Fenster) — dort die Konsole getrennt regeln statt das
Fenster zu verstecken.

**Zweiter Fix, wenn der Elternprozess fensterlos BLEIBEN muss (Gateway,
Cron-no_agent, pythonw-Dienst): `creationflags=subprocess.CREATE_NO_WINDOW`
an JEDEN `subprocess.run`/`Popen` eines Konsolenprogramms.** Der Gateway
laeuft als pythonw und kann nicht auf Konsolen-Subsystem umgestellt werden —
dann bekommt jedes Kind (tasklist, powershell, cmd, python, hermes) sein
eigenes sichtbares Fenster, und ein Dauertakt (Cron-Wache, die je Lauf eine
Prozessabfrage macht) poppt je Takt auf. Das Flag ist Windows-spezifisch und
gehoert mit Portabilitaets-Guard: `creationflags=subprocess.CREATE_NO_WINDOW
if os.name == "nt" else 0`. **Jede Wache, die als no_agent-Cron laeuft und
subprocess aufruft, braucht es** — auch wenn der Aufruf nur `sys.executable`
(startet ein Python-Kind) oder `powershell` ist, nicht nur tasklist. Nach dem
Patch die Wachen neu starten, die ihr Modul cachen (SkillsBot, Bus); no_agent-
Cron-Wachen lesen ihre Skripte je Lauf frisch und brauchen keinen Neustart.
Einen Test, der `CREATE_NO_WINDOW` als Design-Regel VERBIETET („rein lesend,
keine Fenstersteuerung"), praezisieren statt umgehen: das Flag ist jetzt
Pflicht, weil das Modul auch aus dem fensterlosen Gateway laeuft — die Regel
wird von „verboten" zu „muss vorhanden sein" gedreht.

## Eine Datei erscheint immer wieder (Desktop, Arbeitsverzeichnis): den SCHREIBER belegen

Dieselbe Fehlerklasse wie das aufblitzende Fenster: ein Artefakt, das „zu oft
aufploppt" (eine Datei auf dem Desktop, ein wiederkehrender Logname), wird
nicht am Artefakt erklaert, sondern am Prozess, der es erzeugt.

- **Der NAME ist der erste Zeuge.** Sieht ein Dateiname aus wie ein Pfad ohne
  seine Trennzeichen (`CUsersfaupe…Hermestoolspython-3.14.7…python.exe.txt`),
  wurde ein Pfad als DATEINAME benutzt: die Trennzeichen hat der Schreibende
  verloren, und die Datei liegt dort, wo sein ARBEITSVERZEICHNIS war. Aus dem
  Fundort folgt also der CWD des Schreibers, nicht ein Zielort.
- **Eine Verknuepfung ohne „Ausfuehren in" setzt den CWD auf ihren eigenen
  Ordner.** Ein Desktop-`.lnk` auf eine GUI-Anwendung startet den Prozess damit
  im Desktop-Ordner — ein relativer Logname landet genau dort. Ziel und
  Arbeitsverzeichnis aus den `.lnk`-Bytes lesen, nicht raten (Rezept in
  `references/herkunft-belegen.md`).
- **Erst pruefen, ob die Datei noch GEHALTEN wird**, bevor Prozesse verdaechtigt
  werden: exklusiv oeffnen. Geht es auf, ist der Schreiber fertig und aus der
  Prozessliste verschwunden — ein Schnappschuss Minuten spaeter ist wertlos, und
  die Frage muss beim NAECHSTEN Auftauchen beantwortet werden (Wache unten).
- **Eine leere Kommandozeilen-Suche beweist nichts.** Ein Redirect (`… > datei`)
  steht in der Kommandozeile des ELTERNprozesses, nicht des Kindes; ein
  `cmd /c … > datei`-Elternteil kann laengst beendet sein, waehrend das Kind
  weiterlaeuft. Kein Treffer heisst nur: der Starter ist weg.
- **Die eigene Herkunft ausschliessen statt vermuten.** Hermes' eigener
  Dateinamen-Reiniger (`hermes_cli/gateway_windows._sanitize_filename`) ERSETZT
  verbotene Zeichen durch `_` — ein Name, in dem sie einfach FEHLEN, stammt
  nicht von dort. Solche Diskriminatoren sparen ganze Suchlaeufe.
- **Die Aufgabenplanung zuerst abfragen, nicht zuletzt:** alle `MaxHirn-*`-
  Aufgaben mit `Execute` + `Arguments` + `WorkingDirectory` ausgeben. Ein
  Redirect dort ist damit in einem Aufruf ausgeschlossen.
- **Wenn nur die Stoerung weg soll:** den CWD des Starters geradeziehen
  (Verknuepfung → Eigenschaften → „Ausfuehren in": Startverzeichnis des
  Dienstes). Der Mechanismus (CWD) ist damit belegt, der Schreiber selbst
  nicht — beides so benennen, statt einen Fix zu behaupten.
- **Einen ungeklaerten Schreiber nicht als geloest ausgeben.** Ist der Prozess
  beim Nachsehen schon tot, heisst die ehrliche Antwort: Mechanismus belegt,
  Erzeuger offen, naechster Schritt ist die Wache. Die vergeblichen Suchlaeufe
  (Quellbaum, Bundle, Prozessliste) gehoeren dann NICHT als Rezept in die
  Antwort.

Die Sonden im Detail (`.lnk`-Bytes, Halte-Test, Prozess-Schnappschuss,
Aufgaben-Dump, `FileSystemWatcher`, begrenztes Grep):
`references/herkunft-belegen.md`.

Der Rueckwaerts-Weg von der Tatzeit (wer hat um 22:12:52 geschrieben?), die
Temp-Fixture-Gegenprobe, die eine Testsuite entlastet, und die Grenze dessen,
was ein Zeitgleichlauf beweist: `references/schreiber-finden.md` — laden,
wenn ein Ordner, eine Datei oder ein Junction ohne erklaerenden Prozess
entstanden oder verschwunden ist.

## "Keine Verbindung" zu einem Dienst: erst lokal von global trennen

Wenn ein Dienst (Claude Desktop, eine API, eine Webseite) „keine Verbindung“
meldet, nicht an der Konfiguration drehen — erst ortbar machen, wo der Fehler
sitzt, in dieser Reihenfolge:

1. **Globalen Ausfall ausschliessen per Fremd-Check:**
   `curl "https://check-host.net/check-tcp?host=<ip>:<port>&max_nodes=3" -H
   "Accept: application/json"` gibt ein `request_id`; das Ergebnis einige
   Sekunden spaeter mit `GET https://check-host.net/check-result/<request_id>`
   holen. Antwortet ein fremder Knoten in Millisekunden, ist der Dienst oben
   und der Fehler sitzt im lokalen Pfad. Statusseite des Anbieters als zweite
   Quelle.
2. **DNS NICHT der lokalen Auflösung glauben** — VPN-DNS und
   Threat-Protection koennen Antworten umschreiben. Gegenprobe per DoH:
   `curl "https://dns.google/resolve?name=<host>&type=A"` (bzw.
   `cloudflare-dns.com`). Stimmt die IP nicht mit der lokalen ueberein, ist
   die lokale Auflösung manipuliert/geblockt.
3. **Welche Schnittstelle traegt das Ziel?** `Find-NetRoute
   -RemoteIPAddress <ip>` zeigt Interface und NextHop. Steht ein Tunnel
   (NordLynx, NextHop 100.64.x) mit Metric 1 vor dem LAN (Metric 25), laeuft
   der Verkehr durch den Tunnel — und `curl --interface` umgeht das NICHT,
   es aendert nur die Quell-IP, nicht die Routenwahl. Der echte Weg am
   Tunnel vorbei heisst: VPN trennen (Tray, kein Admin) oder Admin-Route.
   ICMP-Ping ist durch den Tunnel grundsätzlich blockiert und damit kein
   Diagnosemittel; `curl -o /dev/null -w "%{http_code} (%{time_total}s)"`
   ist die Masszahl.

Belegtes Beispiel: NordLynx-Exit (Frankfurt, AS207137 PacketHub) konnte das
Anthropic-Netz nicht routen — alle Anthropic-Domains timeouteten, andere
Domains liefen. Nach VPN-Trennung antwortete `api.anthropic.com` in 0,1 s.

## Aufgabenplanung beurteilen

`Get-ScheduledTaskInfo` je Aufgabe liefert `LastRunTime`, `NextRunTime` und
`LastTaskResult`:

| Wert | Bedeutung |
|---|---|
| `0` | sauber beendet |
| `267009` (0x41301) | läuft gerade |
| `267014` (0x41306) | Aufgabe wurde beendet (nicht durchgelaufen) |
| `3221225786` (0xC000013A) | von außen beendet (Kill, Herunterfahren, Absturz) |

**Ein harmlos aussehender Code kann einen Dienstausfall verdecken.** `267014` sagt
nur, dass die Aufgabe beendet wurde — hat der Starter einen DAUERprozess gestartet,
kann der Dienst mit der Aufgabe gestorben sein (Prozessbaum der Aufgabe). Bevor so
ein Code als „von außen beendet, egal“ abgetan wird: prüfen, ob die Komponente
ueberhaupt noch lauscht (Port/`Get-Process`) und ob die zugehoerige Wache sie
vermisst haette. Ein Code ohne Wache ist kein Beweis, dass alles laeuft.

Ein Ledger-Skript kann nach einem Kill keine Schlusszeile mehr schreiben: Eine
angefangene Meldung ohne Ende ist dann kein Skriptfehler, sondern die Folge des
Abbruchs. Deshalb vor jedem Befund erst `LastTaskResult` ansehen.

### Eine Aufgabe per XML anlegen (ohne Adminrechte)

Fuer eine Aufgabe mit `LeastPrivilege` + `InteractiveToken` + Logon-Trigger mit
`Delay` ist eine XML-Datei der verlaessliche Weg:
`schtasks /create /tn <name> /xml <datei> /f` — das braucht KEINE Elevation.

- **Vom HOST aus anlegen, nicht aus dem Sandkasten.** Der Kasten hat eine eigene
  Sicht auf `C:\Windows\System32\Tasks`; dort angelegte Aufgaben sind im naechsten
  Aufruf weg, obwohl `schtasks` Erfolg gemeldet hat.
- **Die XML-Datei MUSS UTF-16LE MIT BOM am ANFANG sein.** Ein hinten angehaengtes
  `b"\x00\x00"` ist kein BOM: `schtasks` antwortet `FEHLER: Die Aufgaben-XML ist
  ungueltig. (1,2)::FEHLER: Ein Stammelement.` — die Meldung zeigt auf den
  XML-INHALT, gemeint ist die KODIERUNG. Richtig:
  `f.write(codecs.BOM_UTF16_LE)` dann `f.write(xml.encode("utf-16-le"))`, und
  vorher `roh[:2] == b"\xff\xfe"` asserten.
- **Idempotenz zuerst pruefen:** `schtasks /query /tn <name>` liefert Exit 0, wenn
  die Aufgabe schon existiert — dann nichts tun. `Get-ScheduledTask -TaskName`
  findet auch VORHANDENE Aufgaben nicht zuverlaessig; die Aufzaehlung und
  `schtasks /query` sind die belastbaren Wege.
- **Danach EINEN echten Lauf zeigen:** `schtasks /run /tn <name>`, dann das Log des
  Wrappers lesen. Die Zeile „Bereit" im Query beweist nur die Registrierung, nicht
  die Funktion — der Lauf beweist die Aufgabe.

## Linux-gated Installer/CLI: in WSL2 laufen lassen, nicht in der MSYS-Bash

Manche Fremd-Installer und CLIs sind auf Linux/macOS fest verdrahtet (z.B. ein
`setup-in-agent.sh`, dessen Bun-Runtime-Auswahl per `uname` nur Linux/macOS
kennt) und lehnen Windows ab. Auf diesem Rechner ist die WSL2-Distribution
`archlinux` der einzige Linux-Computer — dort laufen lassen, nicht in der
MSYS-Bash. Der Aufruf von Windows aus:

```
wsl.exe -d archlinux -- /bin/sh /mnt/c/Users/faupe/Documents/BrainFiles/Agenten/Hermes/scripts/<skript>.sh
```

### WSL2-Fallen, die Zeit kosten

Vollstaendiger GBrain-Install-/Reparatur-Ablauf: `references/gbrain-install.md`.

- **`wsl.exe` verschluckt inline uebergebene Flags und `-w`-Formatstrings**
  (die MSYS/Windows-Argumentgrenze frisst sie: `curl: option : blank argument`).
  Den Befehl in ein Skript unter `Agenten/Hermes/scripts/` legen und das
  Skript ausfuehren statt eines Inline-Einzeilers.
- **`/tmp` in WSL ist tmpfs und wird zwischen zwei Aufrufen geleert** — was
  dort gestaged wurde (Helper, Quelldatei), ist beim naechsten Aufruf weg.
  Scratch im persistenten `/mnt/c/...`-Baum ablegen oder im selben Lauf neu
  erzeugen.
- **WSL2-`archlinux`-pacman scheitert ueber IPv6** (`Resolving timed out`),
  obwohl GitHub laeuft. Fix: EINEN IPv4-faehigen offiziellen Mirror pinnen
  (`Server = https://geo.mirror.pkgbuild.com/$repo/os/$arch`) und IPv4 per
  `XferCommand = /usr/bin/curl -4 -L -C - -f -o %o %u` in pacman.conf
  erzwingen. `$repo`/`$arch` muessen die aeussere Shell ueberleben — die
  Mirrorlist aus einer Skriptdatei schreiben, nicht per Inline-`printf`, das
  die aeussere Shell expandiert.
- **Ein abgebrochener Installer-Lauf hinterlaesst eine korrupte Runtime**
  (z.B. `bun` als 100-MB-Datei, `file` sagt `data` statt ELF) und eine
  Receipt im Zustand `installing`. Die Receipt nennt den exakten
  Wiederherstellungsbefehl; ihn erneut ausfuehren repariert, ohne den
  Speicher neu zu initialisieren. Nicht den Root loeschen, um den Fehler
  „verschwinden zu lassen".
- **`head -c` auf einen Multi-Datei-Glob druckt pro Datei einen
  `==> <pfad> <==`-Kopf** — `head -c 4 /pfad/*/bun` zeigt den Kopf, nicht die
  Dateibytes. Fuer echten Inhalt `od`/`file` auf EINEN Pfad.

## Wurzel-Aufrufer fuer Hand-Aufrufe (Max tippt in der Wurzel)

Die Shell des Nutzers startet im Startverzeichnis der Verknuepfung — das ist die
Repo-Wurzel (`C:\Users\faupe\Documents\BrainFiles`), waehrend die Werkzeuge in
Unterordnern liegen. Ein nackter Dateiname wird im AKTUELLEN Ordner gesucht, nicht
im Baum: `python omnitrade_bridge.py` endet dort mit `[Errno 2] No such file or
_directory`. Das ist kein Fehler, sondern das Startverzeichnis — nicht nach einer
Ignore-Regel oder einem Pfadproblem suchen.

- **Fuer Werkzeuge, die er oft von Hand aufruft, gehoert ein Wurzel-Aufrufer hin**
  (Muster `omnitrade.cmd`: ohne Argument den lesenden Stand, mit `start` den Lauf
  beginnen). Er loest seine Ziele relativ zu `%~dp0` auf und funktioniert damit aus
  JEDEM Verzeichnis.
- **Der Aufrufer braucht eine `.gitignore`-Freigabe** (`!/<name>.cmd`), sonst ist er
  unter der Whitelist unsichtbar und liegt nur auf dieser Platte.
- Ein Aufrufer, der einen Dauerdienst startet, prueft VORHER, ob schon einer laeuft,
  und lehnt dann mit Exitcode ungleich 0 ab: zwei Instanzen schreiben dieselbe
  Statusdatei und ordern doppelt.

## Kurznamen fremder Werkzeuge im PATH: die Pruefung faellt still aus

In einer `.cmd`/`.ps1` NIE `find`, `tasklist`, `sort` oder `time` mit blossem Namen
aufrufen. Laeuft die Shell mit MSYS/git-bash im PATH, gewinnt deren gleichnamiges
Werkzeug: `tasklist /FI ... | find /I "<name>"` findet dann nichts, die Pruefung
„laeuft schon" faellt still aus und der Aufrufer startet eine ZWEITE Instanz. Der
Fehler sieht wie ein bestandener Test aus.

- Immer den vollen Pfad nehmen: `%SystemRoot%\System32\tasklist.exe`,
  `%SystemRoot%\System32\findstr.exe` — oder in PowerShell
  `Get-CimInstance Win32_Process -Filter "Name like '<name>%'"`, ganz ohne Textwerkzeug.
- **Gegenprobe ist der ABGELEHNTE Fall:** den Guard aufrufen, waehrend der Prozess
  wirklich laeuft, und Exitcode ungleich 0 verlangen. Ein durchgelaufener „startet"-Fall
  beweist nichts ueber den Guard.
- Ein Prozessfilter traegt seinen Suchtext selbst und muss den EIGENEN Aufruf
  ausschliessen (das Muster aus Teilen bauen) — sonst findet und beendet er die eigene Shell.

## Junctions im Baum: still durch echte Ordner ersetzt

`BrainFiles\Werkstatt` (und `Modelle`) sind Junctions auf `O:\…`: dasselbe
Verzeichnis, zwei Namen. Host-Werkzeuge melden beim Schreiben den `O:`-Pfad,
`Test-Path` findet die Datei unter beiden. Beim Nachlesen nicht irritieren
lassen.

**Eine Junction kann still durch einen echten (fast leeren) Ordner ersetzt
werden** — eine parallele Sitzung oder ein Tool, das in den Pfad schreibt und
dabei `rm -rf` + `mkdir` macht. Symptom: alles unter dem Pfad „verschwindet"
(Repos, omnitrade, Projekte), obwohl die Daten auf `O:` unversehrt liegen —
`omnitrade.cmd` meldet dann „keine Statusdatei", Repo-Bots lesen ins Leere.
Nichts ist verloren, nur der Verweis ist weg.

- **Erkennung:** `test -L <pfad>` (MSYS) bzw. `Get-Item <pfad> -Force |
  Select-Object LinkType,Target` (PowerShell) — `LinkType` leer = echter Ordner,
  kein Junction. `cmd //c dir /AL` listet alle Junctions.
- **Reparatur (verlustfrei, reversibel):** 1) versionierte Dateien im echten
  Ordner zuerst nach `O:\Werkstatt` kopieren (git sieht sie über die Junction
  wieder); 2) echten Ordner per `Remove-Item -LiteralPath <pfad> -Recurse -Force`
  entfernen (aus der bash-Schicht **nicht** `rm -rf` — siehe unten); 3) `New-Item -ItemType Junction -Path
  <pfad> -Target O:\Werkstatt`. 4) Verifizieren: `test -L`, Inhalt, `git status`.
- **`cmd //c mklink /J` aus bash ist unzuverlaessig** (haengt/Timeout). Die
  PowerShell-Form `New-Item -ItemType Junction` in einer `.ps1`-Datei ist der
  verlaessliche Weg — und `$`-Variablen gehoeren in die Datei, nicht in einen
  doppelt-quotierten `-Command`-String (bash expandiert sie vorher, siehe oben).
- **Auch das ENTFERNEN des echten Ordners gehoert in die PowerShell-Datei.**
  `rm -rf <pfad>` aus der bash-Schicht auf einen Pfad, der ein Junction sein
  KOENNTE, ist doppelt falsch: das Verhalten beim Aufloesen des Reparse-Punkts
  ist unklar (es kann das ZIEL treffen statt den Verweis), und der Aufruf lief
  in einen Timeout, dessen Abbruch den Zustand offen liess. `Remove-Item
  -LiteralPath -Recurse -Force` trifft genau den benannten Pfad; danach mit
  `Test-Path` belegen, dass er weg ist, und erst dann den Junction neu setzen.
  `-LiteralPath` ist Pflicht — ein Pfad mit eckigen Klammern wird sonst als
  Wildcard gelesen.
- **Nach der Reparatur zeigt `git status` die Whitelist-Dateien als `??`** —
  das ist normal (Werkstatt = Durchgangsware, per `.gitignore` freigegeben),
  kein neuer Schaden.

## Abgrenzung
- Bus-Meldungen und ihre Abnahme: `bus-integration`
- MCP-Server zwischen Claude und Hermes abgleichen: `mcp-sync`
- Hermes' eigene `config.yaml`/`.env`: `hermes-config-ops`

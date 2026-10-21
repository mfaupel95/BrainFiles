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
2. **Erhöhte Rechte bleiben Handarbeit.** Aufgabenplanung mit `-RunLevel Highest`
   kann eine nicht erhöhte Sitzung nicht registrieren („Zugriff verweigert").
   Dann Max den einen Befehl ausführen lassen und danach **lesend** belegen:
   `Get-ScheduledTask`, `Get-ScheduledTaskInfo`, Port prüfen.
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

### Fallen, die anders aussehen als sie sind

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
  Schreiben `[IO.File]::WriteAllText` mit explizitem UTF8Encoding.

**Die Werkzeugschicht ist nicht der Interpreter der Aufgabe.** Sie ist 7.x, die
Aufgabenplanung startet `%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe`
(5.1). Was unter 7 parst und läuft, kann unter 5.1 scheitern — vor „fertig" das
Skript oder wenigstens einen Trockenlauf unter der 5.1-Bahn laufen lassen.

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

## Abgrenzung

- `BrainFiles\Werkstatt` ist ein Junction auf `O:\Werkstatt`: dasselbe Verzeichnis,
  zwei Namen. Host-Werkzeuge melden beim Schreiben den `O:`-Pfad, `Test-Path`
  findet die Datei unter beiden. Beim Nachlesen nicht irritieren lassen.
- Bus-Meldungen und ihre Abnahme: `bus-integration`
- MCP-Server zwischen Claude und Hermes abgleichen: `mcp-sync`
- Hermes' eigene `config.yaml`/`.env`: `hermes-config-ops`

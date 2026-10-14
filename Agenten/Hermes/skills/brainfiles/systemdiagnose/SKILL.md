---
name: systemdiagnose
description: "Systemcheck fahren: Laufwerke, Ereignisse, Dienste, Laeufe."
version: 0.1.0
author: Hermes Agent
license: MIT
category: brainfiles
platforms: [windows]
metadata:
  hermes:
    tags: [systemcheck, diagnose, ereignisprotokoll, dienste, dauerlauf, brainfiles]
    related_skills: [laufwerk-platz-schaffen, omniroute-betrieb, absturz-recovery]
---

# Systemdiagnose

Ein vollstaendiger Gesundheitscheck des BrainFiles-Rechners auf Ansage:
Laufwerke, Ereignisprotokoll, Dienste, geplante Aufgaben, Dauerlaeufe,
Hermes-Installation. Liefert einen Befund nach Dringlichkeit, keine Rohdaten.

Fuer den Einzelfall gilt der jeweilige Spezialskill: Platz →
`laufwerk-platz-schaffen`, Router → `omniroute-betrieb`, nach einem Absturz →
`absturz-recovery`. Dieses Skill ist der Uberblick, nicht die Kopie.

## Wann
„pruef das System“, „check system for problems“, „was ist kaputt“,
„vollstaendiger Systemcheck“, „laeuft alles“, oder als Vorarbeit, wenn ein
einzelnes Symptom (Haenger, Absturz, ein Dienst antwortet nicht) eine noch
unbekannte Ursache hat. Auch der Einstieg bei **„computer haengt“ / „alles
zieht“** — dann ist die Reihenfolge Speicher → CPU → **Datentraegerlast**, und
der dritte Schritt wird oft der einzige mit einem Befund.

## Vorgehen

1. **Zuerst den letzten automatischen Bericht lesen — nicht neu erfinden.**
   `Agenten/Routinen/logs/systempruefung-letzter-lauf.md` listet die offenen
   Punkte der Nachtpruefung. Was dort steht, ist bekannt; nur Neues oder
   inzwischen Erledigtes gehoert in die Antwort.
   *Fertig, wenn fuer jeden Punkt des Berichts klar ist: offen / erledigt /
   veraltet.*
2. **Behauptungen aus dem alten Bericht gegenpruefen, bevor sie wiederholt
   werden.** Der Bericht hinkt hinterher. Belegt: „Ollama-Store O:\Modelle
   fehlt, OLLAMA_MODELS zeigt ins Leere“ war falsch — der Store lag nur unter
   dem neuen Pfad, Ollama lief mit Modellen. Eine Altmeldung nie ungeprueft
   weiterreichen.
3. **Ist-Zustand erheben**, Reihenfolge nach Wirkung statt nach Schema:
   Laufwerke, RAM/Uptime, kritische Ereignisse, Dienste, geplante Aufgaben,
   Dauerlaeufe und Ports der eigenen Dienste. Befehle: siehe unten.
4. **Ein Befund wird erst gemeldet, wenn er belegt ist.** Fuer jede
   Auffaelligkeit die Ursache eine Ebene tiefer holen (Logzeile, Prozess, Port,
   Zeitstempel). Sonst wandert ein Verdacht als Tatsache in den Bericht.
5. **Bericht nach Dringlichkeit**, nicht in Pruefreihenfolge: kritisch (kostet
   Funktion) / offen (nicht blockierend) / Entwarnung. Am Ende genau **eine**
   Empfehlung mit Begruendung.
6. **Ausdruecklich nennen, was NICHT angefasst wurde** — laufende Dienste,
   Zugangsdateien, fremder Git-Arbeitsbaum. Max fragt danach.

## Befehle

Laufwerke und Platz:
```
df -h
powershell -NoProfile -Command "Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | Select-Object DeviceID,@{n='FreiGB';e={[int](\$_.FreeSpace/1GB)}},@{n='Prozent';e={[int](100*\$_.FreeSpace/\$_.Size)}}"
```
RAM, Uptime:
```
powershell -NoProfile -Command "\$os=Get-CimInstance Win32_OperatingSystem; 'Boot: ' + \$os.LastBootUpTime; 'RAM frei GB: ' + [math]::Round(\$os.FreePhysicalMemory/1MB,1)"
```
Kritische und Fehler-Ereignisse, 7 Tage:
```
powershell -NoProfile -Command "Get-WinEvent -FilterHashtable @{LogName='System';Level=1,2;StartTime=(Get-Date).AddDays(-7)} -MaxEvents 25 | Select-Object TimeCreated,Id,ProviderName"
```
Unsauberer Abschuss — kein Bugcheck heisst Stromausfall/Reset:
```
powershell -NoProfile -Command "Get-WinEvent -FilterHashtable @{LogName='System';Id=41} -MaxEvents 10 | ForEach-Object { \$_.TimeCreated.ToString('dd.MM HH:mm') + ' Bugcheck=' + \$_.Properties[15].Value + ' PowerButton=' + \$_.Properties[11].Value }"
```
Geplante Aufgaben mit Ergebnis:
```
powershell -NoProfile -Command "Get-ScheduledTask | Where-Object { \$_.TaskName -match '<Muster>' } | Select-Object TaskName,State,@{n='Result';e={(Get-ScheduledTaskInfo \$_.TaskName).LastTaskResult}}"
```
`LastTaskResult` lesen, **nicht nur `0` zaehlen**: `0` = sauber, `267009`
(0x41301) = laeuft gerade, `267014` (0x41306) und `1073807364` (0x40010004) =
Prozess von aussen beendet (bei Dauerlaeufen der Normalfall beim Herunterfahren),
`2147946720` (0x800710E0) = Aufgabe laeuft schon (`IgnoreNew`), `3221225786`
(0xC000013A) = abgebrochen, `3221225794` (0xC0000142) = der Prozess kam gar nicht
hoch (DLL-/Speicher-Initialisierung; typisch, wenn der Commit knapp ist). Jeden
Nicht-`0`-Wert als Fehler zu melden, erzeugt
Fehlalarme; ein Befund ist er erst zusammen mit `ENDE FEHLER` im eigenen
Protokoll oder wenn der Dienst nachweislich nicht antwortet. Umgekehrt gilt für
`3221225794`: ist das eigene Protokoll **aelter als `LastRunTime`**, hat der Lauf
nicht einmal begonnen — der letzte `ENDE ok`-Eintrag stammt dann vom Vorlauf und
belegt gar nichts. Eine solche Aufgabe einmal von Hand starten und das Ergebnis
gegen den Code halten, bevor daraus ein Fehler der Aufgabe wird.
Dauerlaeufe und ihre Kinder:
```
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | ForEach-Object { \$_.ProcessId.ToString() + ' | Parent ' + \$_.ParentProcessId + ' | ' + \$_.CreationDate + ' | ' + \$_.CommandLine }"
```
Vielfachheit statt Einzelprozess — der schnellste Weg bei „der Rechner ist
unendlich langsam“: Prozesse **nach Kommandozeile gruppieren** und je Gruppe
zaehlen, dann Eltern-Kind-Paare trennen. Eine Gruppe mit vier Eintraegen ist
vierfacher Dauerbetrieb;
```
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" | ForEach-Object { \$c=\$_.CommandLine; if(-not \$c){\$c='(ohne)'}; (\$c -replace '.*BrainFiles\\\\','') } | Group-Object | Sort-Object Count -Descending | Select-Object -First 12 | ForEach-Object { '{0,3} x  {1}' -f \$_.Count, \$_.Name }"
```
Hermes selbst: `hermes doctor` (vorher `unset PYTHONHOME PYTHONPATH`, sonst
bricht der Aufruf aus einer MCP-Session heraus ab).
Ports: echter TCP-Connect oder `Get-NetTCPConnection` — `netstat` nicht parsen,
die deutsche Anzeige schreibt „ABHOEREN“ mit Umlaut und wird als Binaer
fehlgedeutet.

## systempruefung.ps1 pflegen

- **Neue Bloecke zuerst isoliert testen, nicht ueber den vollen Lauf.**
  `systempruefung.ps1` braucht ~2 min und mischt viele Bloecke — ein Fehler
  im neuen Block ist im vollen Lauf schwer zu orten. Den Block in eine
  Standalone-Testdatei kopieren, die Stub-Funktionen `Notiz`/`Info`/
  `Entscheiden` definiert (je `Write-Host`), und pruefen, dass er die
  erwartete Info-/Entscheiden-Zeile liefert. Erst dann den vollen Lauf
  (`-NurPruefen`, im Hintergrund, `grep` auf den Block) als Beleg.
- **Gewollt deaktivierte Aufgaben in eine Whitelist, nicht als Entscheiden.**
  Block 9 meldet jede deaktivierte `MaxHirn-*`-Aufgabe als Entscheiden. Ist
  die Deaktivierung gewollt (z. B. ersetzt durch einen Dauerlauf), gehoert sie
  in die Hashtable `$gewolltDeaktiviert` (Name → Grund) — dann meldet der
  Block sie als Info mit Grund. Jede ANDERE deaktivierte Aufgabe bleibt
  Entscheiden. Eintrag + Grund, damit der Grund im Bericht steht.
  Aktuelle Eintraege: `MaxHirn-MoonDev-Agent` (ersetzt durch den
  MoonDev-Dauerlauf, kein Doppelstart).
- **Block 14 (Docker `nautilus-demo`) kennt vier Fallen, die alle im Code
  dokumentiert sind:** (1) JEDER docker-Aufruf braucht eine Zeitgrenze
  (`DockerMitFrist`, `System.Diagnostics.Process` mit `WaitForExit(ms)`,
  Ausgabe asynchron lesen): ist die Engine aus, wartet der Client
  unbegrenzt auf die Pipe, der ganze Lauf wird von aussen gekillt und der
  Bericht **gar nicht mehr geschrieben** — 19.–22.09.2026 dreimal passiert,
  `letzter-lauf.md` blieb auf dem 19.09. stehen. Ohne Antwort in 20/25 s
  liefert der Helfer `$null` und der Block meldet „Engine antwortet nicht".
  Gemessen: 8,2 s statt unbegrenzt; (2) EAP lokal auf `Continue` setzen, sonst
  zaehlt stderr von docker als NativeCommandError; (3) `docker logs` liefert
  ANSI-Escape-Sequenzen (`\x1b[...m`) — vor dem Regex-Match entfernen;
  (4) `[datetimeoffset]::Parse(ts+'Z', InvariantCulture, AssumeUniversal)`
  statt `[datetime]::ParseExact(AssumeUniversal)` — das speichert als Local
  und verfaelscht die Differenz um die Zeitzone (120-min-Fehler).
  Dazu: ein toter Daemon nimmt auch den Container mit. Fehlt `nautilus-demo`
  **samt Image**, hilft nur Neubau aus `Agenten/Handel/nautilus/Dockerfile`
  (Routine `nautilus-docker-start.ps1` macht das idempotent).
- **Grosse PowerShell-Bloecke ganz neu schreiben statt in kleinen Patches
  iterieren.** Der Patch-Mechanismus verzieht bei mehrzeiligen Bloecken gern
  die Einrueckung und schleust Tippfehler ein (`Select-ObjectObject`,
  `nautilusutilus`, `\}:` im Regex) — und ein `continue`, das aus dem `if`
  herausgezogen wird, bricht die Schleife nach dem ersten Element ab. Nach
  jedem Patch den Block exakt lesen und den isolierten Test laufen lassen.

## Pitfalls

- **„Der Rechner haengt“ heisst zuerst: Warteschlange je Platte messen.** RAM
  (20 GB frei), Commit (16 GB frei) und CPU (0 %) koennen alle gesund sein,
  waehrend eine einzige Platte mit `CurrentDiskQueueLength` > 5 ihre Schlange
  nicht abarbeitet. Je Volume `Win32_PerfFormattedData_PerfDisk_PhysicalDisk`
  nehmen, das Feld mit der Warteschlange benennen, dann den Schreiber ueber
  die **I/O-Rate je PID** (`Win32_PerfFormattedData_PerfProc_Process`,
  `IODataBytesPersec`) suchen — nie ueber `Sort-Object CPU`, das
  Lebenszeit sortiert und den Schuldigen weg von der Spitze fuehrt. Vollstaendige
  Messfolge, Indexer/Watcher-Muster, Waisen derselben Binary und die Fallstricke
  einer begrenzten Volumensuche: `references/datentraegerlast-und-schreiber.md`.
- **Ein Anzeige-Symptom ist kein Energieplan-Problem, solange die Auszeit nicht
  gemessen ist.** Unter Speicherdruck faellt zuerst die Anzeige-Schicht aus: gehaeufte
  Ereignisse 2004 (Ressourcenerschoepfung) und Abstuerze von `dwm.exe` im
  Application-Log gehen jedem unerklaerlichen Anzeige-/Grafikverhalten voraus — nach
  einem Neustart mit wieder freier Commit-Luft ist das Symptom weg, ohne dass eine
  Einstellung geaendert wurde. Beide Quellen lesen, bevor eine Einstellung verdaechtigt
  wird; fuer die Messung selbst `windows-energie-und-anzeige`.
- **Werkzeugnamen nie erfinden.** Schlaegt ein Aufruf mit „Tool X does not
  exist. Available tools: …“ fehl, ist die zurueckgegebene Liste die Wahrheit:
  den naechsten Aufruf daraus waehlen, nicht aus der Erinnerung an die
  Umgebung. Andersherum kostet es Runde um Runde, weil jeder geratene Name
  denselben Fehler erneut ausloest.
- **`$_.Message.Substring(0, N)` wirft**, sobald eine Meldung kuerzer als N ist
  (`ArgumentOutOfRangeException`), und ueberschwemmt die Ausgabe mit
  PowerShell-Fehlerbloecken. Immer `[Math]::Min(N, $_.Message.Length)` als
  Laenge nehmen — und zwar gemessen an **demselben String, der gekuerzt wird**:
  `($m -replace "\r\n",' ').Substring(0, [Math]::Min(N, $m.Length))` wirft
  weiter, weil das Ersetzen den Text verkuerzt, die Laenge aber noch vom
  Original stammt. Erst in eine Variable legen, dann ersetzen, dann messen:
  `$t = $m -replace ...; $t.Substring(0, [Math]::Min(N, $t.Length))`.
- **Zwei Prozesse mit gleichem Namen sind nicht automatisch ein Doppelstart.**
  Vor der Alarmmeldung `ParentProcessId` pruefen: laeuft der zweite als Kind
  des ersten, ist es ein gewolltes Gespann (Fall: der Dauerlauf startet einen
  Unterprozess je Spur). Erst ein zweiter Prozess **ohne** diese Elternschaft
  ist ein Doppelstart-Befund.
- **Auch die Startzeit gruppiert nicht — die KOMMANDOZEILE entscheidet.** Fuenf
  Prozesse derselben Binary sind nicht zwei Doppelpaare plus einer, nur weil
  zwei um 03:46 und zwei um 20:03 starteten: die Argumente koennen fuenf
  VERSCHIEDENE Auftraege sein (verschiedenes `--script`, `--symbol`,
  `--status-file`). Vor jedem Beenden `Get-CimInstance Win32_Process` mit
  `CommandLine` je PID ausgeben und die Zeilen lesen — ein Duplikat ist erst
  eines, wenn Kommandozeile **und** Zielressource (Statusdatei, Port, Symbol)
  dieselben sind. Eine Beendeliste, die nur aus Name + Startzeit gebaut ist,
  trifft lebende Arbeit; die Empfehlung dazu ist aktiv zurueckzunehmen, sobald
  die Argumente sie widerlegen.
- **In einer langen Sitzung ist ein Befund von vorhin kein Ist-Zustand.** Vor
  der Zusammenfassung `date` erneut aufrufen. Erscheint der Zeitstempel einer
  Datei **in der Zukunft**, ist nicht die Datei falsch, sondern die angenommene
  Uhrzeit — dann zuerst die Uhr klaeren, sonst wird ein laufender Dienst als
  „laeuft nicht“ gemeldet.
- **Ein Dienst „laeuft nicht“, weil der Port nicht antwortet, heisst nicht,
  dass er tot ist.** `401` ist eine gueltige Antwort. Vor dem Urteil den
  Lauscher-PID und einen Statuscode holen — *laeuft* und *erreichbar* sind zwei
  Aussagen.
- **Ein Dienst, der laut eigener Startmeldung nicht hochkam, kann laufen.** Die
  Verifikationsstufe eines Starters bricht gern zu frueh ab und schreibt
  „kam nicht hoch“, waehrend der Dienst seit Stunden Anfragen beantwortet. Vor
  jedem Urteil und erst recht vor einem Neustart das **Dienstprotokoll** auf
  erfolgreiche Arbeit pruefen (Erfolgs-Statuszeilen, `status=200`, „succeeded“)
  **und** den Port proben. Beides fehlt = wirklich nicht hochgekommen; eines von
  beiden traegt = die Startmeldung ist der Befund.
- **Jeder Dienst braucht einen Waechter — und der Waechter darf nicht ueber den
  Weg melden, den er ueberwacht.** Ein Dienst ohne eigene Ueberwachung faellt
  tagelang nicht auf (belegt: eine Meldekette war vier Tage stumm und niemand
  sah es, weil ihre Meldungen ueber genau den toten Dienst liefen). Wer eine
  Ueberwachung prueft, prueft fuenf Dinge: existiert eine Aufgabe dafuer, laeuft
  sie, meldet sie auf einem Weg, der den Ausfall ueberlebt (direkter Versand oder
  ein fremder Scheduler), meldet sie **nur** im Fehlerfall (sonst wird sie
  ignoriert) und steht die Ausfallhaeufigkeit irgendwo sichtbar.
- **Der Hermes-Gateway hat keine eingebaute Neustart-Instanz — die EINZIGE ist
  die geplante Aufgabe `MaxHirn-Gateway-Waechter`.** Die Exit-75-Meldung
  ("exiting ... so the service supervisor can restart it") benennt KEINEN
  Dienst: ist die Aufgabe DISABLED, bleibt ein gecrashter Gateway stundenlang
  tot und Telegram-/Cron-Zustellungen schweigen in der ganzen Luecke. Vor
  jeder Gateway-Diagnose ZUERST den Aufgabenzustand lesen — deaktiviert ist
  ein Befund, kein "laeuft irgendwie". Crash-Beleg im Log: `CRITICAL
  gateway.shutdown_watchdog: missed 3 consecutive liveness probes ... exiting
  with code 75` mit einem `MemoryError` kurz davor = Speicherdruck-Crash.
  Reaktivieren (`Enable-ScheduledTask`) braucht Erhoehung (einmal UAC ansagen,
  nie wiederholen); danach den Waechter EINMAL von Hand laufen lassen und im
  Bus-Journal (`Agenten/Bus/journal/<datum>.jsonl`) die Zeile "Gateway laeuft ...
  kein Start" suchen — das ist der Churn-Gegenbeweis. Achtung: direkt nach
  einem Neustart steht `gateway_state.json` auf "starting", die
  Primaer-Pruefung des Waechters (`gateway_state == 'running'`) greift dann
  noch nicht — der Kommandozeilen-Rueckfall traegt, also dessen Muster VOR dem
  Aktivieren gegen die echte Kommandozeile des Prozesses testen.
- **Zerstoerte Junction erkennen, bevor Werkzeug-Ausfaelle einzeln untersucht
  werden.** Meldet `fremd.py` auf einmal ALLE `Werkstatt/...`-Eintraege "nicht
  auf der Platte" oder tauchen `konfig-doktor-<datum>.md` an der
  Werkstatt-Wurzel auf, ist `BrainFiles\Werkstatt` kein Verweis mehr auf
  `O:\Werkstatt` (zweimal zerstoert; dort liegt eine echte Ordner-Teilkopie
  mit eingebetteter Repos-Junction). Pruefung: `(Get-Item Werkstatt -Force).LinkType`
  (leer = kaputt) und Eintraegezahl gegen `O:\Werkstatt`; verlustfreie
  Reparatur (Rettungskopie → Junction neu): `references/windows-junctions.md`.
- **`Get-Process ... | Sort-Object CPU` zeigt Lebenszeit, nicht Last.** `CPU` ist
  die aufsummierte Prozessorzeit seit Prozessstart — oben stehen damit
  langlebige Anwendungen (Terminal, Browser, Afterburner), nicht die aktuelle
  Ursache. Fuer Jetzt-Werte `Win32_PerfFormattedData_PerfProc_Process`
  (`PercentProcessorTime`) nehmen oder zweimal messen und die Differenz bilden.
- **Ein leerer `Get-Counter`-Wert ist keine Null-Last.** Counter-Pfade sind
  lokalisiert; `Get-Counter '\PhysicalDisk(_Total)\...'` liefert auf einem
  deutschen Windows stillschweigend nichts. Dann nicht „keine Last“
  hinschreiben, sondern die Kennzahl ueber `Win32_PerfFormattedData_*` holen
  oder ausdruecklich als „nicht messbar“ melden.
- **Commit-Druck ist keine niedrige physikalische-Zahl.** Ein Rechner kann 30+ GB physisch
  frei haben und trotzdem an Commit (virtuell, `FreeVirtualMemory`) ersticken — das Seitenfile
  (50,2 GB benutzt bei 5,5 GB Commit frei) ist der Treiber. Angezeigtes Symptom sind dann
  regellose Cron-/SIGTERM/Exit-15-Fehler und `WinError 1455 Auslagerungsdatei zu klein`.
  Fuer Commit-Messung je Prozess `PagefileUsage`/`PrivateMemorySize64` nehmen, NICHT
  `WorkingSetSize` — angefangene 947 MB Commit je `windows-mcp`-Zombie bei nur ~49 MB physisch
  sieht in der WorkingSet-Tabelle wie 0 aus. Gruppieren nach Alter: laufen viele Prozesse einer
  Kommandozeile (36 Stueck, aeltester >24 h, kein einziger juenger als 1 h), sind es **Waisen** —
  der Gateway/Gast startet Kindpaare und gibt alte nicht frei. Die ueber der Altersgrenze
  beenden (`Stop-Process -Force`, nativer Befehl; taskkill aus windows-mcp tut still nichts),
  Commit danach messen — 5,5 → 15 GB frei war der Beleg, und die SIGTERM-Welle hoerte auf.
  **Die Umkehrung gilt genauso: `FreeVirtualMemory` = 0 ist KEIN Beweis fuer Commit-Druck.**
  Gemessen 29.09.2026: Win32_OperatingSystem meldete 0 GB frei, aber das Seitenfile war
  fast leer (0,2 von 8 GB genutzt) — die Messung war ein Artefakt, kein Druck. Vor jedem
  Waisen-Kill das Seitenfile gegenpruefen (`Win32_PageFileUsage`: `AllocatedBaseSize` gegen
  `CurrentUsage`); erst wenn es wirklich voll ist, ist der Commit der Treiber. Und
  `PagefileUsage`/`PrivateMemorySize64` koennen fuer ALLE Prozesse 0 MB zeigen — dann ist
  die Messung kein Beleg fuer „kein Fresser", sondern schlicht unbrauchbar; nicht daraus
  schliessen, dass kein Prozess Commit haelt.
  **Waisen-Muster: exakt gleiche Startzeit ueber viele Prozesse einer Kommandozeile**
  (87 Stueck, alle 21:13:59) ist ein EINMALIGER Start, der nie endete = abgebrochener
  Build, kein laufender Dienst. Ein laufender Build haette juengere Kinder. Solche
  Waisen beenden und danach pruefen, ob sie wiederkommen (der Gateway startet ein paar
  neu — das ist normal, nicht das Waisen-Problem).

- **Einen Dauerprozess nie mit `timeout` testen.** `timeout 60 dauerlauf.py` beendet ihn
  nach Ablauf mit SIGTERM (Rueckgabe 143), und der Dauerlauf beendet dann seine Kinder —
  das Log zeigt danach „xperp (papier) Rueckgabe 143", als waere die Spur abgestuerzt.
  Das ist ein Test-Artefakt, kein Befund. Einen Dauerprozess im Hintergrund starten
  (`background=true`) und in einem SEPARATEN Aufruf pruefen, ob er laeuft und Zyklen
  schreibt; nie mit einem eigenen Zeitlimit, das ihn killt.
- **Ein Cron „Script exited with code 15“ ist ein SIGTERM von aussen, kein Skriptfehler.**
  Gibt das Skript selbst nur 0/1 zurueck, wird der Prozess mitten im Lauf beendet — sehr zum
  Auslesen der Ereigniszeit (Lauf in 12 s statt der ueblichen 20–50 s). Nicht den Quelltext des
  Skripts verdaechtigen: in `cron/executions.db` das historische Muster pruefen (kommt code 15
der erste Mal heute bei MEHREREN Jobs? = gemeinsame aussenstehende Ursache wie Speicherdruck,
  kein Zufall), den Gateway-Neustart als Ursache ausschliessen (letzter „Press Ctrl+C"-Start),
  und erst dann Ressourcen parallel zum Tatzeitpunkt messen. Erst nachdem Commit-Luft da ist,
  erkennen, dass der Radar selbst gesund war und nur Kollateralschaden unter Druck erlit.

- **„RAM freigeben“ heisst meist „CPU messen“.** Ein Rechner mit 21 GB freiem RAM
  und `LoadPercentage` 100 wird als RAM-Problem gemeldet, obwohl ein einzelnes
  seit Stunden **idle** geladenes CPU-Modell (`:cpu` → `size_vram: 0`) auf allen
  Kernen rechnet: 47,6 Kerne gemessen, dabei null offene Verbindungen und ein
  Log, das seit Stunden nicht gewachsen ist. Erst Differenzmessung der Last
  (zweimal `CPU` ablesen, nicht `Sort-Object CPU`), dann freigeben. Die
  Umkehrung gilt auch: **Memory Compression mit 9 GB ist kein Leak** bei 23 GB
  freiem RAM — das ist eine Container-Laufzeit, die Commit haelt. Vollstaendige
  Messfolge und die Belegbefehle: `references/ram-und-cpu-freigeben.md`.
- **Eine bestehende Waechter ist blind, wenn sie den falschen Prozessnamen
  zaehlt.** Ein MCP-Kreislauf mit 84 `node`-Knoten blieb unentdeckt, weil die
  Zombie-Wache nur `python`/`pythonw` filterte. Vor jeder Ueberzahl-Bereinigung
  die Waechter-Definition lesen: **welche Interpreter zaehlt sie ueberhaupt?**
  Sonst raeumt man von Hand, was die Wache nicht sieht, und der Kreislauf kommt
  zurueck.
- **Eine PowerShell-Fehlerblende, die sich hundertfach wiederholt, ist fast nie
  ein Datenproblem.** Bei einer CIM-Gruppierung lieferte
  `$grp = if (...) {...} else { @() }; $grp += $p` den Fehler
  „CimInstance enthaelt keine Methode op_Addition“ — der `if`-Ausdruck lieferte
  ein Objekt statt eines Arrays. Die Regel: gleiche Meldung mehrfach = Muster
  lesen, nicht weiterlaufen. Richtig ist `New-Object System.Collections.ArrayList`
  plus `[void]$h[$k].Add($p)`. Der Fehler hat sich als „0 Waisen gefunden“
  getarnt, also auch die Belegpflicht: **eine Vorschau, die 0 beenden meldet,
  ist erst nach diesem Ausschluss eine belegte Null.**
- **Ein traeger Rechner hat selten einen CPU-Fresser.** Gemessene 18 % CPU,
  25 GB freier RAM und leere Disk-Queue passen zu einer Kiste, die sich
  trotzdem kriechend anfuehlt — dann zuerst nach **Vielfachheit** (Duplikate
  desselben Dauerlaufs) und nach verwaisten Kindprozessen suchen, nicht nach
  einem einzelnen Schuldigen.
- **Fuer Hashes `DateiHash()` aus `System.Security.Cryptography` nutzen, nicht `Get-FileHash`.** In der `powershell.exe` (5.1) dieses Rechners existiert das Cmdlet nicht (`CommandNotFoundException`) — und der stille Fall ist schlimmer als der laute: bleibt der Hash leer, wirft jedes `Group-Object` alle Elemente in EINE Gruppe, und das Werkzeug meldet danach eine **falsche Zahl** statt eines Fehlers (Fundus-Suche: „0 von 0 Dateien" bei vorhandenem Bestand, systempruefung Block 10 vorher dasselbe). Regel: den Rueckfall einbauen (kein Hash -> den PFAD als Schluessel nehmen, damit nichts verschwindet) und beide Interpreter gegeneinander proben — `powershell.exe` und `pwsh` muessen dieselben Zahlen liefern.
- **Nicht jeder Fehler im Log ist ein aktueller Fehler.** Start- und
  Haushaltslogs wachsen ueber Stunden; die **letzten** Zeilen lesen. Viele
  Systeme heilen sich selbst (Verbindungs-Wiederaufbau, „error cleared“) —
  sonst steht im Bericht ein Problem, das sich laengst geloest hat.
- **Ein Pruefer, der haengen kann, verliert den ganzen Bericht — und die
  Luecke ist unsichtbar.** Der Aufgabenzustand bleibt „Ready", die Tageslogs
  existieren, nur `systempruefung-letzter-lauf.md` wird alt. Wer eine
  Systempruefung „abarbeitet", vergleicht deshalb ZUERST das Datum im Bericht
  mit heute: ist es aelter als der letzte geplante Lauf, wurde der Lauf
  abgebrochen und die Befunde darin sind Geschichte. Zweiter Zeuge: das Ende
  des Tagesprotokolls (`Agenten/Routinen/logs/systempruefung-<datum>.log`)
  muss eine Ende-Zeile haben.
- **Bloecke, die jeden Lauf dieselben Zeilen melden, gehoeren in eine
  Whitelist mit Grund — nicht in die Entscheiden-Liste.** Ein Dauerfehlalarm
  deckt die echten Neufunde zu. Muster im Skript: `$gewolltDeaktiviert`
  (Aufgaben), `$gewolltStores` (Ollama-Stores mit Nur-hier-Blobs),
  `$ausgenommen` (Pfad-Pruefung) und der Fremd-Baum-Ausschluss in Block 6
  (`.mcp.json` in `skills/`, `plugins/` — dort gilt die Umgebung des
  Herstellers, `bun` fehlt hier absichtlich). Neue Eintraege nur mit
  Begruendung, und nur der NAME wird freigestellt, nie eine Loeschung.
- **`robocopy`-`FEHLER 32` (Zugriff verweigert) in einer eigenen Sicherung ist
  meist ein SELBST gehaltenes Schloss, keine Beschaedigung.** Eine lang
  laufende eigene Automatisierung (eine Headless-Browser-Instanz, eine offene
  DB-Journaldatei, ein Cache-Prozess) haelt Dateien offen; mit `/R:1 /W:1`
  bricht der Lauf nach einer Wiederholung ab (robocopy-Code 20/21, Task-Exit
  `0x40010004`). Halter finden ueber
  `Get-CimInstance Win32_Process -Filter "Name='<prozess>.exe'"` — die
  `CommandLine` nennt den betroffenen Datenpfad (z. B. `--user-data-dir=...`),
  `ParentProcessId` den Starter. Fix ist, den Ordner per `/XD` aus dem
  Kopierumfang zu nehmen, nicht die Wiederholungszahl zu erhoehen (das wartet
  nur laenger auf denselben Halter). Ein Abbruch OHNE jedes Ereignis im
  Zeitfenster des betroffenen Laufs (`Get-WinEvent` liefert nichts) ist meist
  ein spaeterer Reboot/Shutdown (Event 1074), der den Prozess von aussen
  beendet hat — kein Fehler im Skript selbst.

- **Ein Schreibjob ist erst gesund, wenn sich sein ARTEFAKT bewegt hat — und das
  Alter des Artefakts ist die Messung.** `LastTaskResult` sagt *dass* ein Lauf brach,
  nicht *seit wann*: eine taegliche Routine kann jeden Abend mit `1` enden, ohne dass
  es auffaellt, weil niemand das Erzeugnis ansieht. Beim Zwischenstand ist das
  Erzeugnis der Zweig — dafuer reicht ein Befehl:
  `git log -1 --format=%ci zwischenstand`; steht der letzte Eintrag tagealt, ist die
  Routine abgebrochen (bei Stillstand schreibt sie ausdruecklich „ENDE unveraendert“)
  und nicht „es gab nichts zu tun". Denselben Griff auf JEDEN Schreibjob uebertragen:
  **Alter des Erzeugnisses gegen den Zeitplan halten**, nicht nur den Aufgabenzustand
  lesen. Ist der Abbruch gefunden, liegt die Ursache fast immer im Arbeitsbaum und
  nicht im Skript — Gegenprobe mit genau dem Befehl, der scheitert
  (`git add -A --dry-run`; Exitcode 128 = kaputt, 0 = gesund), dann den Lauf einmal
  von Hand nachziehen, damit die Luecke zu ist.
- **Ein Artefakt gehoert einem bestimmten STARTER — ohne ihn ist sein Alter kein
  Befund.** Eine veraltete Statusdatei beweist nicht, dass etwas ausgefallen
  ist: schreibt sie nur der eine Launcher (ein `start`-Befehl mit einem festen
  Skript), waehrend mehrere andere Laeufe ihre EIGENEN Dateien fortschreiben,
  ist sie voellig zu Recht alt. Vor jedem „veraltet / kein Lebenszeichen": den
  Schreiber aus der Startzeile lesen (`--status-file`), die Geschwisterdateien
  im selben Ordner auflisten und deren Alter vergleichen. Ist die Familie
  frisch und nur die eine alt, laeuft der Betrieb — gemeldet wird dann die
  verwaiste Datei, nicht ein Ausfall. Der Hausweg fuer diese Frage ist das
  Werkzeug mit den zwei Zeugen (Statusdatei **und** PID), das 0/1 liefert; es
  liest die Schreiberzuordnung selbst. Dasselbe gilt rueckwaerts: eine lebende
  PID ohne Namenspruefung kann eine wiederverwendete PID sein (siehe
  `trugschluesse`).

## Ereignis-IDs
Welche ID was bedeutet (Kernel-Power 41, Volsnap 36, disk 11/153, Service
Control Manager 7000/7023/7031/7034/7043): `references/ereignis-ids.md`.

## Speicher und Last freigeben
Auftrag „RAM freigeben“ / „System beschleunigen“: Reihenfolge, idle-CPU-Modell,
MCP-Knoten-Generationen, Memory Compression als Symptom, PowerShell-Falle beim
Gruppieren: `references/ram-und-cpu-freigeben.md`.

## Junctions
`Werkstatt`/`Modelle` als Verweise statt echter Ordner: Zerstoerungs-Symptome
(alle Werkstatt-Pfade „nicht auf der Platte", konfig-doktor-Dateien tauchen an
der Werkstatt-Wurzel auf), verlustfreie Reparatur:
`references/windows-junctions.md`.

## Bericht
- Ergebnis zuerst, dann Belege. Tabellen fuer Zustandswerte, keine Prosa.
- Zahlen konkret: frei/belegt je Laufwerk, Uptime, RAM frei, PID und Startzeit
  der laufenden Dienste, Exitcodes der geplanten Aufgaben.
- Genau eine Empfehlung, begruendet — keine Optionsliste.
- Zum Schluss: was bewusst nicht angefasst wurde und was eine Entscheidung von
  Max braucht.

## Aufraeumen
Nach der Pruefung die Pruef-Artefakte loeschen (Max: „nach pruefung loeschen") — Scratch-Dateien, Aktivierungs-Skripte samt Log, und Rettungskopien, sobald
ihr Inhalt verifiziert in den Zielort gemerged ist. Eine Rettungskopie ist kein
Dauerlager: sie bleibt nur bis zur Verifikation stehen, dann weg. Destruktive
Loeschung im Approval-Terminal als EIGENER Aufruf ansagen, nie in eine Kette
gebuendelt.

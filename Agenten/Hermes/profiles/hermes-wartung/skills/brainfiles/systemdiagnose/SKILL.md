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
unbekannte Ursache hat.

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
(0xC000013A) = abgebrochen. Jeden Nicht-`0`-Wert als Fehler zu melden, erzeugt
Fehlalarme; ein Befund ist er erst zusammen mit `ENDE FEHLER` im eigenen
Protokoll oder wenn der Dienst nachweislich nicht antwortet.
Dauerlaeufe und ihre Kinder:
```
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | ForEach-Object { \$_.ProcessId.ToString() + ' | Parent ' + \$_.ParentProcessId + ' | ' + \$_.CreationDate + ' | ' + \$_.CommandLine }"
```
Vielfachheit statt Einzelprozess — der schnellste Weg bei „der Rechner ist
unendlich langsam“: Prozesse **nach Kommandozeile gruppieren** und je Gruppe
zaehlen, dann Eltern-Kind-Paare trennen. Eine Gruppe mit vier Eintraegen ist
vierfacher Dauerbetrieb; waechst sie im Minutentakt, ist es eine Spawn-Schleife
— Ursache und die drei Gegenproben stehen in `dauerprozess-bewachen`, Abschnitt
„Ein Dienst, der sich vermehrt".
```
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" | ForEach-Object { \$c=\$_.CommandLine; if(-not \$c){\$c='(ohne)'}; (\$c -replace '.*BrainFiles\\\\','') } | Group-Object | Sort-Object Count -Descending | Select-Object -First 12 | ForEach-Object { '{0,3} x  {1}' -f \$_.Count, \$_.Name }"
```
Hermes selbst: `hermes doctor` (vorher `unset PYTHONHOME PYTHONPATH`, sonst
bricht der Aufruf aus einer MCP-Session heraus ab).
Ports: echter TCP-Connect oder `Get-NetTCPConnection` — `netstat` nicht parsen,
die deutsche Anzeige schreibt „ABHOEREN“ mit Umlaut und wird als Binaer
fehlgedeutet.

## Speicherdruck messen (RAM, Commit, Auslagerung)

Der harte Deckel ist nicht der freie RAM, sondern das **Commit-Limit** — RAM
plus Auslagerungsdateien. Es zu ueberschreiten beendet Prozesse, unabhaengig
davon, wie viel RAM gerade frei ist.

```
powershell -NoProfile -Command "\$os=Get-CimInstance Win32_OperatingSystem; 'Commit-Limit GB: ' + [math]::Round(\$os.TotalVirtualMemorySize/1MB,1); 'Commit belegt GB: ' + [math]::Round((\$os.TotalVirtualMemorySize-\$os.FreeVirtualMemory)/1MB,1); 'RAM frei GB: ' + [math]::Round(\$os.FreePhysicalMemory/1MB,1)"
```

`TotalVirtualMemorySize` **ist** das Commit-Limit (RAM + Pagefiles zusammen),
`FreeVirtualMemory` der Rest. Beide Zahlen nennen — „18 GB RAM frei“ neben
„15 GB Commit frei“ beschreibt einen Rechner unter Druck, nicht einen gesunden.

**Wenn Windows schon gemeldet hat, WER den Speicher haelt, diese Meldung
lesen statt zu suchen.** `Id 2004` („virtueller Speicher unzureichend“)
**nennt die drei groessten Verbraucher mit PID und Bytezahl** — die guenstigste
Ursachendiagnose ueberhaupt. Wiederholt sie sich im Minutentakt, ist es kein
Ausrutscher:

```
powershell -NoProfile -Command "Get-WinEvent -FilterHashtable @{LogName='System'; Id=@(2004,2019,2020); StartTime=(Get-Date).AddDays(-7)} -MaxEvents 15 | ForEach-Object { \$t=\$_.Message -replace \"`r`n\",' '; \$_.TimeCreated.ToString('dd.MM HH:mm') + '  Id ' + \$_.Id + '  ' + \$t.Substring(0,[Math]::Min(220,\$t.Length)) }"
```

**Die Verbraucher nachpruefen, nicht die Meldung wiederholen.** Typische Halter
sind `vmmemWSL` (WSL/Docker), ein lokaler Modellserver (`llama-server` mit
`--models-autoload` laedt nach) und ein Terminal-Emulator. Je Prozess
`WorkingSet64` (Arbeitsseite) **und** `PrivateMemorySize64` (Zusage, zaehlt
gegen das Commit-Limit) zeigen — ein Prozess mit kleiner Arbeitsseite und
riesiger Zusage sieht sonst harmlos aus.

**Gestuerzte Prozesse liegen mit Zeit und Groesse bereit:**
`%LOCALAPPDATA%\CrashDumps`. Ein 232-MB-Dump eines Modellservers ist der
Nachweis einer Speicherspitze, die kein Log zeigt.

**Externe Deckel sind der eigentliche Hebel, nicht die Hermes-Config.** Eine
WSL-VM hat ohne `%USERPROFILE%\.wslconfig` keinen Deckel und nimmt sich die
Haelfte des RAM (Vorgabe). **Docker Desktops `MemoryMiB` aus
`%APPDATA%\Docker\settings-store.json` greift im WSL2-Modus NICHT** — die
Docker-Doku verweist fuer Speicher/CPU/Swap ausdruecklich auf die WSL-Utility-VM.
Belegt: `MemoryMiB = 33024`, gemeldet wurden 31.932 MB (die 50-%-Vorgabe).
**Ein gesetzter Wert ist kein wirkender Wert — nach dem Setzen den Ist-Stand
messen** (`wsl --system free -m`): stimmt die Zahl mit dem Vorgabewert ueberein
statt mit dem eingestellten, sitzt der Schalter an der falschen Stelle. Rezept
fuer die `.wslconfig`: im Skill `hermes-config-ops`, Abschnitt
"Die Config ist selten die Ursache".

**Ein grosser `vmmemWSL` ist meist kein Leck, sondern Summe.** Er enthaelt alle
WSL-Distributionen: Container, Images, Linux-Page-Cache. Vor dem Urteil die
Treiber zaehlen und benennen (`docker ps`, `docker system df` inkl.
"reclaimable") — sonst wird eine gewollte Last als Fehler gemeldet.

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
- **Block 14 (Docker `nautilus-demo`) kennt drei Fallen, die alle im Code
  dokumentiert sind:** (1) EAP lokal auf `Continue` setzen, sonst zaehlt
  stderr von docker als NativeCommandError und die Zuweisung bleibt leer;
  (2) `docker logs` liefert ANSI-Escape-Sequenzen (`\x1b[...m`) — vor dem
  Regex-Match entfernen, sonst beginnt die Zeile nicht mit der Ziffer;
  (3) `[datetimeoffset]::Parse(ts+'Z', InvariantCulture, AssumeUniversal)`
  statt `[datetime]::ParseExact(AssumeUniversal)` — das speichert als Local
  und verfaelscht die Differenz um die Zeitzone (120-min-Fehler).
- **Grosse PowerShell-Bloecke ganz neu schreiben statt in kleinen Patches
  iterieren.** Der Patch-Mechanismus verzieht bei mehrzeiligen Bloecken gern
  die Einrueckung und schleust Tippfehler ein (`Select-ObjectObject`,
  `nautilusutilus`, `\\}:` im Regex) — und ein `continue`, das aus dem `if`
  herausgezogen wird, bricht die Schleife nach dem ersten Element ab. Nach
  jedem Patch den Block exakt lesen und den isolierten Test laufen lassen.
- **Ternaerer Operator `? :` nicht im Rahmen eines `[PSCustomObject]@{}`-Literals
  oder einer `ForEach-Object`-Lambda definieren.** Die PowerShell-Parser-Version
  auf diesem Rechner (Windows PowerShell 5.1) akzeptiert den ternaeren Operator
  **nicht** an diesen Stellen — der Fehler meldet „Unerwartetes Token" oder
  „Das Hashliteral war unvollstaendig" und bricht den Block ab, ohne dass die
  betroffene Zeile im Editor auffaellig ist. Stattdessen den Regex-Ergebnis mit
  `[regex]::Match($line, '<pattern>')` holen und im Nachgang mit `if
  ($m.Success) { ... }` verzweigen — und **vor dem Einbetten das Skript einmal
  mit `powershell -NoProfile -File <datei>` durchlaufen**, nicht nur auf
  Syntax mit einem Linter vertrauen.
- **PowerShell-Skripte schreiben, bevor sie ausgefuehrt werden — nie aus dem
  Patch- oder Write-Workflow heraus direkt in einen `terminal`-Aufruf
  uebergehen, ohne das Skript erst als eigenstaendige Datei vorzulegen und zu
  pruefen.** Der `write_file`-Mechanismus kann bei Skripten, die zuvor mit
  `read_file` (insbesondere `offset`/`limit`-Paginierung) gelesen wurden,
  mit „stale_write_blocked" oder „Refusing to overwrite … last read with
  offset/limit pagination" verweigern — die Datei ist auf der Platte in Ordnung,
  das Tool blockiert den Schreibzugriff aber dennoch. Vor jedem Schreiben die
  Datei vollstaendig mit `read_file` (ohne Pagination-Parameter) lesen.
  Fehler dieser Art sind am ehesten durch **Neuschreiben ganzer Bloecke** zu
  umgehen, nicht durch wiederholtes Patchversuchen dasselbe Fragment.

## Pitfalls

- **Ein Datentraeger-Test, dessen Testdatei in den Dateicache passt, misst den
  RAM.** 200 zufaellige 4-KB-Zugriffe auf eine 8-MB-Datei meldeten fuer eine
  USB-HDD, eine USB-SSD und zwei NVMe **dieselben 0,2–0,6 ms** — alles las aus
  dem Cache, und das Ergebnis war „ueberall NVMe". Richtig ist
  **sequentielles Lesen von ~1 GB aus einer Datei, die groesser als das
  Doppelte der Lesemenge ist** (oder einer vorhandenen dicken Datei), in
  1-MB-Bloecken mit `[System.IO.File]::Open` und Stoppuhr. Das ergab 73 MB/s
  (USB-HDD) gegen 930 MB/s (NVMe) — Faktor 13, den der Cache-Test verschluckt
  hatte. **Fertige Sonde statt selbst tippen:**
  `scripts/disk-durchsatz.ps1` (findet je Laufwerk selbst eine Datei > 1 GB,
  liest read-only 1 GB, nennt MB/s und Einordnung; warnt, wenn die Datei zu
  klein ist, um den Cache auszuschliessen).
- **`$HOME` (und `$PID`, `$HOST`) sind in PowerShell schreibgeschuetzt.** Ein
  Skript, das `$home = '...'` als Laufzeitvariable setzen will, bricht mit
  „Die Variable "HOME" kann nicht ueberschrieben werden, da sie konstant oder
  schreibgeschuetzt ist" ab — und zwar **mitten in der Schleife**, sodass die
  restlichen Zeilen des Durchlaufs fehlen. Fuer den eigenen Zielpfad einen
  anderen Namen nehmen (`$ziel`, `$hermesHome`).
- **`[Environment]::GetEnvironmentVariable('NAME','System')` wirft** — der
  Scope-Name heisst `Machine`, nicht `System`:
  „Der Wert "System" kann nicht in den Typ System.EnvironmentVariableTarget
  konvertiert werden. … Geben Sie einen der folgenden Enumeratornamen an:
  Process, User, Machine". Die drei gueltigen Werte sind `Process`, `User`,
  `Machine`.
- **`MediaType` aus `Get-PhysicalDisk` entscheidet ueber USB nichts.**
  USB-Gehaeuse melden `Unspecified` bei `BusType=USB`; eine NVMe im einen und
  eine Magnetplatte im anderen Gehaeuse sind damit nicht unterscheidbar. Das
  Feld als Hinweis lesen, den gemessenen Durchsatz als Beweis.
- **Vor „ist X auf Laufwerk Y in Ordnung“ erst pruefen, ob X dort liegt.** Die
  Frage „ist der Pagefile auf G: ok?“ setzt voraus, dass dort einer ist;
  `Get-CimInstance Win32_PageFileSetting` zeigte zwei Pagefiles, beide auf
  NVMe, und keines auf G:. Die Praemisse der Frage gehoert geprueft und
  ausdruecklich korrigiert — sonst wird eine Empfehlung zu einem Problem
  abgegeben, das es nicht gibt.
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
- **Eltern-Kind-Aussagen aus der Prozessliste sind ungeprueft, solange PIDs
  recycelt werden koennen.** Windows vergibt freigegebene PIDs neu: ein
  `ParentProcessId` aus einer Abfrage kann auf einen Prozess zeigen, der erst
  NACH dem toten Eltern entstand — und „A hat B gespawnt" ist dann falsch, obwohl
  die Zahlen plausibel aussehen. Vor einer solchen Aussage das `CreationDate`
  beider Prozesse vergleicht: ist das Kind AELTER als der behauptete Elternprozess,
  ist die Elternschaft falsch. (Belegt: eine Gruppe, deren Mehrheit eine Instanz
  derselben Komponente als Eltern hatte, sah wie eine Spawn-Kette aus und war
  reines PID-Recycling.)
- **Eine einzige Zaehlung ist keine Rate.** Ein Wert aus einer Abfrage ueber
  mehrere Huelle meldete „522 neue Prozesse in 60 s"; die Wachstumsrate lag bei
  etwa 2 pro Minute. Richtig: Anzahl **vorher und nachher** im selben Intervall,
  aus Differenz und Sekundenzahl die Rate bilden — und das Intervall gross
  genug waehlen, dass ein einzelner Zyklus das Ergebnis nicht verfaelscht.
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

## App-spezifische Policy-Diagnose

Wenn eine Anwendung einen Ordner/Pfad ablehnt, der auf den ersten Blick
zugänglich ist (volle ACL, kein Schreibschutz, kein versteckter Ordner), liegt
die Ursache oft in der **Policy der Anwendung selbst** oder in einer
**administrativen Richtlinie (GPO/Intune/MDM)** — nicht im Windows-Dateisystem.

Für Claude Desktop Workspace-Probleme (Ordner kann nicht als Workspace
hinzugefügt werden, `WorkspaceTrustError`, `trust approval required`) →
detailliert in `references/claude-desktop-workspace.md`.

Allgemeines Muster für App-spezifische Policy-Diagnose:

1. **App-eigene Logs scannen** — das Entscheidende steht in der App, nicht in
   Windows-Ereignissen. Stichworte: `denied`, `restricted`, `policy`,
   `trust`, `blocked`, `whitelist`.
2. **Fehlertyp identifizieren** — eine Tabelle wie in der Referenz unterscheidet
   App-interne Trust-Policy von administrativen Richtlinien.
3. **Administrative Richtlinien prüfen** — `gpresult /h` (HTML-Bericht) und
   Registry-Scans auf Policies- und App-Einträge.
4. **Test mit Kontrollordner** — ein Ordner ohne auffällige Merkmale (`.`-Prefix,
   schräge ACL, simuliertes Systemverzeichnis) hilft, die Ursache einzugrenzen.
5. **ACL und Owner dokumentieren** — falls relevant, zeigt das, ob ein Dritter
   (System, Admins, Sandbox-Identität) Einschränkungen verursacht.

**Laufendes Diagnose-Skript:** `scripts/claude-workspace-diagnose.ps1` führt
alle Schritte 1–5 automatisch aus und schreibt einen Report nach
`./diagnose-report/`. Aufruf:
`powershell -ExecutionPolicy Bypass -File scripts/claude-workspace-diagnose.ps1`.

### PowerShell-Client-Notiz

`$HOME` (und `$PID`, `$HOST`) sind in PowerShell schreibgeschützte
Umgebungs-Token. Ein Skript, das `$HOME` als Laufzeitvariable belegen will,
bricht mit „Die Variable … kann nicht überschrieben werden, da sie konstant
oder schreibgeschützt ist" ab — oft mitten in einer Schleife. Für den eigenen
Zielpfad einen anderen Namen verwenden (`$userProfile`, `$ziel`,
`$hermesHome`). Siehe Pitfall weiter oben.

## Ereignis-IDs
Welche ID was bedeutet (Kernel-Power 41, Volsnap 36, disk 11/153, Service
Control Manager 7000/7023/7031/7034/7043): `references/ereignis-ids.md`.

## Bericht
- Ergebnis zuerst, dann Belege. Tabellen fuer Zustandswerte, keine Prosa.
- Zahlen konkret: frei/belegt je Laufwerk, Uptime, RAM frei, PID und Startzeit
  der laufenden Dienste, Exitcodes der geplanten Aufgaben.
- Genau eine Empfehlung, begruendet — keine Optionsliste.
- Zum Schluss: was bewusst nicht angefasst wurde und was eine Entscheidung von
  Max braucht.

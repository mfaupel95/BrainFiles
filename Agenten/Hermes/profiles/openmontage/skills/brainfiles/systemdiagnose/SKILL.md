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
vierfacher Dauerbetrieb;
```
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" | ForEach-Object { \$c=\$_.CommandLine; if(-not \$c){\$c='(ohne)'}; (\$c -replace '.*BrainFiles\\\\','') } | Group-Object | Sort-Object Count -Descending | Select-Object -First 12 | ForEach-Object { '{0,3} x  {1}' -f \$_.Count, \$_.Name }"
```
Hermes selbst: `hermes doctor` (vorher `unset PYTHONHOME PYTHONPATH`, sonst
bricht der Aufruf aus einer MCP-Session heraus ab).
Ports: echter TCP-Connect oder `Get-NetTCPConnection` — `netstat` nicht parsen,
die deutsche Anzeige schreibt „ABHOEREN“ mit Umlaut und wird als Binaer
fehlgedeutet.

## Pitfalls

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

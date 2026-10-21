---
name: stille-ausfaelle-eingrenzen
description: Use when ein Aufruf gelingt, aber nichts passiert.
version: 0.1.0
author: Hermes
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [Diagnose, Windows, Launcher, Startweg, Belege, BrainFiles]
    related_skills: [wirkung-nachweisen, trugschluesse, systemdiagnose, hermes-maintenance, hermes-profil-antwortet-nicht]
---

# Stille Ausfaelle eingrenzen — die Marke statt der Rueckgabe

Wenn ein Aufruf mit Erfolg zurueckkehrt und trotzdem nichts geschieht, ist nicht
die Wirkung kaputt, sondern die MESSUNG: man hat den Rueckgabewert des Wirts
gelesen statt das Erzeugnis des Kindes. Dieser Skill grenzt so einen Fall mit
Marken-Dateien und einer Wahrheitstabelle ein, bis genau ein Faktor uebrig
bleibt. Er repariert nichts und bewertet keinen laufenden Betrieb — dafuer
`wirkung-nachweisen`; er belegt keine Zustandsaussage an der Quelle — dafuer
`trugschluesse`.

## When to Use

- ein Aufruf kehrt mit Erfolg zurueck (Exit 0, keine Fehlermeldung) und die
  erwartete Datei/der erwartete Prozess fehlt
- ein Waechter protokolliert im Takt "Neustart ausgeloest", der Dienst kommt
  aber nicht
- ein Startweg funktioniert in einer Umgebung und in einer anderen nicht
- zwei Werkzeuge widersprechen sich: eines sieht die Datei, das andere nicht
- ein Skriptwirt/VBS/Task startet ein Programm "versteckt" und es passiert nichts
- ein Prozess lebt, seine Statusdatei sagt `running`, aber es geschieht seit
  Stunden nichts (keine Orders, keine Zyklen, keine neuen Zeilen)
- bevor "das Werkzeug ist kaputt" oder "der Dienst ist tot" gemeldet wird

## Prerequisites

- Ein Scratch-Ordner, den BEIDE beteiligten Werkzeuge sehen koennen
  (`Agenten/Hermes/cache/scratch/`), und absolute Pfade darin.
- Ein ZWEITES Werkzeug als Gegenprobe (Host-PowerShell `mcp__windows_mcp__PowerShell`
  gegen das `terminal`-Werkzeug) — ohne zweites Instrument ist ein "nein"
  wertlos (Schritt 0).
- `write_file` fuer die Probe, `terminal` fuer den Lauf, `read_file` fuer die
  Marken. Probe immer als DATEI, nie inline: eine `-Command`-Zeile durch die
  Bash-Huelle verliert `$_` und Backslashes.

## How to Run

Jede Probe geht ueber das `terminal`-Werkzeug als
`cscript.exe //nologo "C:/…/probe.vbs"` bzw.
`powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:/…/probe.ps1"`.
Die Marken liest `read_file` oder ein `Test-Path` aus dem ZWEITEN Werkzeug.
Fertige Wahrheitstabelle fuer Fensterstile: `scripts/probe-stiller-start.ps1`.

## Quick Reference

    # Marke statt Rueckgabe: jede Variante schreibt ihre eigene Datei
    Test-Path "<scratch>\marke-<variante>.txt"

    # Kindprozess statt Erfolgsmeldung
    Get-CimInstance Win32_Process -Filter "Name='python.exe' or Name='pythonw.exe'" |
      Where-Object { $_.CommandLine -match '<muster>' } |
      Select-Object ProcessId,ParentProcessId,Name,CreationDate

    # Gemessen 30.09.2026 (WScript.Shell.Run, cscript):
    #   Ziel                     Stil 0  Stil 1  Stil 2  Stil 3  Stil 7  Stil 8
    #   cmd /c echo ...          nein    ja      nein    ja      nein    ja
    #   python.exe (Konsole)     nein    ja       -       -       -       -
    #   pythonw.exe (GUI)        JA      ja       -       -       -       -
    # Stil 0 startet ein KONSOLENprogramm gar nicht - ohne Fehlermeldung.

## Procedure

0. **Erst das Messinstrument eichen.** Bevor irgendetwas als "passiert nicht"
   notiert wird: mit dem BENUTZTEN Werkzeug eine Datei schreiben und mit einem
   ANDEREN Werkzeug lesen. Sieht das zweite sie nicht, ist nicht der
   untersuchte Gegenstand kaputt, sondern die Messung — dann das Werkzeug
   wechseln (Host-PowerShell statt Sandbox-Terminal) und die ganze Reihe dort
   wiederholen. Belegt: eine Reihe von "nein"-Befunden entstand nur, weil die
   Ausgabe des ersten Werkzeugs unbrauchbar zurueckkam.
1. **Die kleinste Probe bauen, die eine MARKE hinterlaesst.** Nicht die
   Rueckgabe des Aufrufs pruefen, sondern eine Datei, die das Kind schreibt
   (`open(<pfad>,'w').write(...)`, `cmd /c echo … > <pfad>`, `fso.CreateTextFile`).
   Jede Variante schreibt ihre EIGENE Marke mit Namen.
2. **Einen Faktor je Lauf veraendern** und die uebrigen konstant halten
   (Fensterstil, Programmname, Ziel-Interpreter, Arbeitsverzeichnis,
   Umgebungsvariable). Nie zwei Faktoren gleichzeitig — sonst ist die
   Zuordnung weg. `scripts/probe-stiller-start.ps1` faehrt genau das.
3. **Von aussen nachsehen, nicht von innen.** Die Marken mit einem anderen
   Werkzeug/Prozess lesen als dem, der sie erwartet hat. Ein Wirt, der seinen
   eigenen Erfolg meldet, ist kein Zeuge.
4. **Negativbefunde sind Ergebnisse und gehoeren aufgeschrieben.** Ausgeschlossene
   Ursachen (keine Attack-Surface-Reduction-Regeln, kein Controlled Folder
   Access, kein Policy-Block) schliessen Hypothesen — ohne sie wird derselbe Weg
   spaeter ein zweites Mal gegangen.
5. **Die Wahrheitstabelle festschreiben** (Wissensbasis/Wiki), mit der Zeile,
   die FUNKTIONIERT, nicht nur mit der, die scheitert. Die funktionierende Zeile
   ist der Fix.
6. **Den Fix am ECHTEN Weg nachweisen**, nicht an der Probe: den echten
   Launcher/Aufruf starten und die Kette zeigen (Wirt-PID → Kind-PID →
   Zustandsdatei `running` → die erwarteten Verbindungen). Eine Probe beweist
   nur, dass die Probe laeuft.
7. **Pruefen, wer den Fix wieder umdrehen kann.** Ein Updater, der die Datei neu
   schreibt, oder eine Sammel-Routine, die alte Fassungen committet, hebt ihn
   beim naechsten Lauf auf — dann gehoert eine Pruefung dazu (Cron/Aufgabe) und
   ein Punkt in `MaxHirn/Archiv/TASKS.md`.

## Wenn der Prozess lebt und das Erzeugnis schweigt

Der Haenger sieht wie ein gesunder Dienst aus: Prozess da, Zustandsdatei sagt
`running`, CPU nahe null. Vier Messungen entscheiden ihn, keine davon ueber den
Prozessnamen:

1. **Alter gegen den SCHREIBRHYTHMUS des Erzeugnisses messen, nicht gegen eine
   feste Grenze.** Eine Statusdatei, die nur je Ereignis geschrieben wird (je
   Kerze, je Zyklus, je Auftrag), ist im Ruhezustand absichtlich still. Ihre
   Frische ist erst dann ein Lebensbeweis, wenn man die Zeile gelesen hat, die
   sie schreibt, und den Takt kennt (Kerzenabstand, Zyklusdauer). Ein festes
   "10 Minuten" ist bei einer Stundenkerze ein Fehlalarm und bei einer
   Minutenkerze zu spaet.
2. **CPU zweimal messen** (`KernelModeTime + UserModeTime`, 20 s Abstand, beide
   Werte mit der Startzeit des Prozesses). Millisekunden Zuwachs heisst: der
   Prozess WARTET. Sekunden Zuwachs heisst: er arbeitet.
3. **Den Ausgang des Wartens pruefen.** Wartet der Prozess auf einem Kanal, den
   ein abgebrochener Leseteil nicht schliesst, kehrt er nie zurueck: die
   Empfangs-Task bricht bei einem Lesefehler ab, ein Sender-Klon haelt den Kanal
   offen, `recv()` liefert nie `None`, und die Abbruchbedingung (`None => break`)
   ist unerreichbar. Die Wartestelle im Code lesen und fragen: WELCHES Ereignis
   beendet sie, und kann dieses Ereignis ueberhaupt noch eintreten?
4. **Pruefen, ob das Log Evidenz ueber Neustarts traegt.** Wird stdout je Start
   umgeleitet bzw. abgeschnitten (`-RedirectStandardOutput`, `>`), existiert nach
   einem Neustart nur der letzte Lauf — "dieser Fehler kam genau einmal" ist dann
   ein Artefakt der Datei, nicht des Betriebs. Vor jeder Haeufigkeitsaussage
   nachsehen, ob die Datei angehaengt oder ueberschrieben wird.

Gehoert zu einem Dienst immer ein Neustart-Weg: meldet eine Wache den Haenger
nur, ist das eine bewusste Entscheidung mit Preis (Stunden Blindflug) — dann den
Preis in die Aufgabe schreiben, nicht nur den Befund.

## Pitfalls

- **Ein Rueckgabewert ist keine Wirkung.** `sh.Run` meldet in den
  Nein-Faellen KEINEN Fehler; der Aufruf kehrt sauber zurueck und der Prozess
  entsteht nicht. Genauso meldet `Start-Process` den Start, nicht das Leben.
- **Ein Wirt, der sein eigenes Erzeugnis startet, wird am Soll gemessen.**
- **Nur EINEN Programmnamen zu suchen ist eine Falle.** Wer den Start von
  `python.exe` auf `pythonw.exe` umstellt, macht jede Wache unsichtbar, die
  `Name='python.exe'` fest verdrahtet hat — sie startet den gesunden Dienst im
  Takt weiter neu. Immer beide Namen abfragen.
- **Zwei Werkzeuge, zwei Dateisystem-Sichten.** Derselbe Pfad kann im Sandbox-
  Terminal und auf dem Host unterschiedlich aussehen; eine Marke "fehlt" dann,
  obwohl sie existiert. Vor jeder "Datei fehlt"-Aussage mit dem zweiten
  Werkzeug gegenlesen.
- **Der stille Erfolg hat eine zweite Form: Exitcode 0 plus `uebersprungen`.**
  Eine Routine, die sich selbst ueberspringt, meldet Erfolg. Den GRUND in der
  Logzeile lesen und das Alter des ERZEUGNISSES messen.
- **Beim Festschreiben die Zeilenenden der Zieldatei erhalten.** `Hardware.md`
  ist LF, `Archiv/TASKS.md` ist CRLF; ein Ersatz mit LF in einer CRLF-Datei
  erzeugt einen Ganzdatei-Diff. Erst messen (`b.count(b'\r\n')`), dann
  schreiben, und im Skript VOR dem Schreiben abbrechen, wenn das Ende kippt.
- **Nur eigene Pfade committen.** Der Git-Index ist geteilt: vor dem Commit
  `git status --porcelain` (erste Spalte = vorgemerkt = fremd) und
  `git diff --cached --numstat` lesen. Sind fremde Pfade drin, mit eigenem
  `GIT_INDEX_FILE` (`git read-tree HEAD` + `git add <eigene>`) committen.
- **PowerShell-JSON-Zeitstempel sind `/Date(ms)/`, kein ISO.** `ConvertTo-Json`
  serialisiert `DateTime` als `/Date(1791388881211)/`; `datetime.fromisoformat()`
  wirft darauf, und ein Waechter, der die Zeit in einer Schleife parst, ueberspringt
  JEDES Ereignis still — Exit 0, leere Ausgabe, nie eine Meldung. Der Waechter
  "laeuft", misst aber nichts. Fix: das ISO-Format schon in PowerShell erzeugen
  (`@{n='TimeCreated';e={$_.TimeCreated.ToString('o')}}` im `Select-Object`),
  nicht nachtraeglich in Python. Gegenprobe: Erstlauf ohne Merkdatei MUSS melden;
  meldet er nichts, ist der Parser schuld, nicht der Markt.
- **Ein selbst gerechneter Wert erfindet Blocker.** Ein Leser, der "frei" als
  `eq − staking − gebunden` zusammenrechnet, meldet ein Konto als leer, waehrend
  das Feld `availEq` derselben Antwort ein Vielfaches nennt (gemessen: 0,56
  gegen 46,43 — und die darauf gebaute Frage "Guthaben fehlt" war gegenstandslos).
  Fuer jede Sperr-Entscheidung das FERTIGE Feld der Quelle nehmen (`availEq`,
  `max-size`, `availBal`), nicht die eigene Subtraktion; und wenn eines fehlt,
  `max-size` fragen statt zu schaetzen.
- **Die Uhr der Sandbox geht falsch.** Datum/Zeit fuer Notizen und Commits vom
  Host (`Get-Date`) oder aus `git log -1 --format=%ci` nehmen — sonst gilt
  eigene Arbeit als "ruhend" und wird als fremde committet.

## Verification

Der Fall ist eingegrenzt, wenn eine Wahrheitstabelle genau EINEN Faktor als
Unterschied zeigt und der Fix am echten Weg belegt ist:

    cscript.exe //nologo "<scratch>/probe-stiller-start.ps1"   # oder von Hand
    Get-CimInstance Win32_Process -Filter "Name='python.exe' or Name='pythonw.exe'" |
      Where-Object { $_.CommandLine -match 'gateway' } |
      Select-Object ProcessId,ParentProcessId,Name,CreationDate
    python -c "import json;d=json.load(open('Agenten/Hermes/gateway_state.json'));print(d['gateway_state'], d['pid'])"

Erwartet: Wirt-PID und Kind-PID mit wenigen Sekunden Abstand, danach
`running` in der Zustandsdatei und die erwarteten Verbindungen. Bleibt die
Wache danach still (Exit 0, keine neue Logzeile), ist auch die zweite Haelfte
belegt.

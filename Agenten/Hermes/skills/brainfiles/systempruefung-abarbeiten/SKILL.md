---
name: systempruefung-abarbeiten
description: Arbeite den Systempruefungsbericht ab.
version: 0.1.0
author: Hermes Agent
license: MIT
category: brainfiles
platforms: [windows]
metadata:
  hermes:
    tags: [Systemcheck, Befunde, Wachen, Reparatur, BrainFiles]
    related_skills: [systemdiagnose, betriebsrunde, trugschluesse, arbeitsbaum-git-hygiene]
---

# Systempruefung abarbeiten

Nimmt den letzten Bericht `Agenten/Routinen/logs/systempruefung-letzter-lauf.md`,
belegt jeden Punkt, behebt ihn, weist die Behebung mit einem echten Lauf nach und
sichert alles. Es ist **keine neue Diagnose** (dafuer `systemdiagnose`), kein
Sammeln (`sammelauftrag`) und kein Einzelauftrag (`brainfiles-auftrag`). Neue
Abhaengigkeiten gibt es nicht: PowerShell 5.1, Stdlib-Python, git.

## When to Use

- "letzte Systempruefung abarbeiten", "was steht in der Nachtpruefung", "die Punkte der Pruefung"
- der Morgenbericht ist da und soll weggearbeitet werden
- ein Punkt der Pruefung wurde schon oefter gemeldet und niemand hat ihn entschieden
- der Bericht wirkt alt, aber der Aufgabenzustand sagt "Ready"

## Prerequisites

- Arbeiten aus der Repo-Wurzel (`C:\Users\faupe\Documents\BrainFiles`).
- `terminal` laeuft hier ueber git-bash; PowerShell-Aufrufe gehen mit
  `powershell -NoProfile -Command "..."`.
- Admin-Aufgaben (`Start-/Stop-ScheduledTask` sind ohne Erhoehung moeglich,
  `Set-/Register-/Disable-ScheduledTask` nicht) in EIN Skript buendeln und per
  `Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile','-File','<pfad>'`
  ausloesen; danach nachmessen.

## How to Run

1. Bericht mit `read_file` oeffnen: `Agenten/Routinen/logs/systempruefung-letzter-lauf.md`.
2. Erstanweisung des Skripts, wenn der Bericht alt ist:
   `terminal`: `cd "$HERMES_HOME/../.." && powershell -NoProfile -ExecutionPolicy Bypass -File Agenten/Routinen/systempruefung.ps1`
3. Alterswache von Hand: `terminal`:
   `cd "$HERMES_HOME/../.." && Agenten/Handel/scanner/.venv/Scripts/python.exe Agenten/Hermes/skills/brainfiles/systempruefung-abarbeiten/scripts/berichts-alter.py`
   (jede Python 3.10+ tut es — das Skript nutzt nur die Standardbibliothek)

**Alle Befehle dieses Skills sind relativ zur BrainFiles-Wurzel.** Hermes' Werkzeuge starten in
`Agenten/Hermes` (`terminal.cwd`) — deshalb der `cd "$HERMES_HOME/../.."` davor.

## Quick Reference

```
Wurzel           cd "$HERMES_HOME/../.."                                   # vor jedem Befehl hier
Bericht          Agenten/Routinen/logs/systempruefung-letzter-lauf.md
Vollprotokoll    Agenten/Routinen/logs/systempruefung-<JJJJ-MM-TT>.log  (muss mit einer Ende-Zeile enden)
Skript           Agenten/Routinen/systempruefung.ps1
Arbeitsbaum      powershell -NoProfile -ExecutionPolicy Bypass -File Agenten/Routinen/arbeitsbaum-pruefen.ps1
Fremdarbeit      powershell -NoProfile -ExecutionPolicy Bypass -File Agenten/Routinen/fremdarbeit-einziehen.ps1 -Testlauf
Aufgaben         Get-ScheduledTask -TaskName 'MaxHirn-*' | ForEach-Object { $i=Get-ScheduledTaskInfo $_.TaskName; '{0,-42} {1,-9} {2,-4} {3}' -f $_.TaskName,$_.State,$i.LastTaskResult,$i.LastRunTime }
Sicherung prüfen powershell -NoProfile -ExecutionPolicy Bypass -File Agenten/sichern.ps1   (Handlauf, ~4 min)
Aufgabe aktivieren schtasks /Change /TN '<TaskName>' /ENABLE   (OHNE Admin; Enable-ScheduledTask braucht Erhoehung!)
```

Nicht-0-Codes: `0` sauber, `267009` laeuft, `267014`/`1073807364` von aussen
beendet (bei Dauerlaeufen normal), `2147946720` laeuft schon, `3221225794`
(C0000142) kam nicht hoch, `1` ist ein echter Skriptfehler. Ein Code wird erst
zum Befund mit dem eigenen Protokoll daneben.

## Procedure

1. **Berichtsdatum gegen heute pruefen — VOR allen Befunden.** Steht im Kopf
   `# Systempruefung <Datum>` von heute, ist die Lage frisch. Ist es aelter als
   der letzte geplante Lauf (taeglich 07:00), wurde der Lauf abgebrochen: die
   Punkte darin sind Geschichte, und der eigentliche Befund ist der Pruefer
   selbst. Zweiter Zeuge: das Ende von `systempruefung-<heute>.log` — fehlt die
   Ende-Zeile, wurde der Lauf gekillt (in der Aufgabenplanung dann `267014`).
2. **Protokoll bis zum Abbruchort lesen** (`read_file`, die letzte
   Blockmarke `--- n) ... ---` vor dem Ende ist der Haenger). Ein Block, der
   ungeschuetzt ein fremdes System aufruft (Docker, Netz, Dienst), wartet
   unbegrenzt — dann Zeitgrenze einbauen, nicht nur neu starten.
3. **Jeden Punkt einer Klasse zuordnen:** laufender Zustand (Datei/Prozess),
   Aufgabe mit Code, Konfig-Drift, Portabilitaet, Whitelist-Kandidat
   (Dauerfehlalarm), Fremdarbeit im Baum. Fuer jede Klasse gilt der Beweisweg
   aus `betriebsrunde`.
4. **Wiederkehrende Zeilen in eine Whitelist mit Grund** (im Skript: Muster
   `$gewolltDeaktiviert`, `$gewolltStores`, `$ausgenommen`, Fremd-Baum-Ausschluss
   in Block 6). Nur den NAMEN freistellen, nie eine Loeschung — ein Store oder
   eine Aufgabe, die nicht in der Liste steht, wird weiter gemeldet. Ohne das
   deckt der Dauerfehlalarm die echten Neufunde zu.
5. **Fremdaufrufe im Pruefer mit Zeitgrenze versehen** (Muster DockerMitFrist:
   `System.Diagnostics.Process`, `WaitForExit($Sekunden*1000)`, Ausgabe mit
   `ReadToEndAsync()` lesen, bei Frist `Kill()` und `$null` zurueck). Den
   Zeitueberschreitungs-Fall als EIGENEN Befund melden, nicht als "alles ok".
6. **Beheben, dann mit einem echten Lauf beweisen.** `git diff --numstat` je
   Datei (wenige Zeilen = gewollt, ganze Datei = Zeilenenden verstellt);
   Python: `scanner/.venv/Scripts/python.exe -m py_compile <datei>` plus eine
   Pfadprobe (`Path(__file__).resolve().parents[n]` gegen eine Datei testen, die
   es geben muss). PowerShell: Parser-Syntaxpruefung, dann der Handlauf.
   Fasst die Aenderung Scheduled Tasks an, laeuft der Beweis ueber den
   Wegwerf-Task-Weg (anlegen+deaktivieren+TEMP-Eintrag+Lauf+Rueckbau) statt am
   echten Waechter — Rezept in `references/selbstheilende-waechter.md`.
7. **Aufgaben, die nur bei Anmeldung laufen** (`MaxHirn-Nautilus-Docker`,
   `-Optimierungen-Finden`), per `Start-ScheduledTask -TaskName <name>` einmal
   anstossen — die sind idempotent und erneuern `LastTaskResult` auf `0`.
   Dauerkopierer wie `MaxHirn-Sicherung` NICHT zur Unzeit doppelt starten; ein
   Handlauf am Tag ist der Nachweis.
8. **Fremdarbeit einziehen und den Index geradeziehen.**
   `fremdarbeit-einziehen.ps1 -Testlauf` zeigt, was ruht. Nach dem echten Lauf
   kann `git status` ein Paar `D <pfad>` + `?? <pfad>` zeigen: Datei existiert,
   Index sagt geloescht. Erst `git rev-parse HEAD:<pfad>` gegen
   `git hash-object <pfad>` vergleichen; sind die Hashes gleich, mit
   `git add <pfad>` den Index herstellen — das aendert keine Datei.
9. **Verwaiste Sperre:** bricht git mit `index.lock: File exists` ab, Alter
   pruefen und echte `git.exe`-Prozesse ohne `fsmonitor` zaehlen. Ist die Sperre
   0 Byte alt und kein echter Prozess da, UMBENENNEN (z.B.
   `.git/index.lock.verwaist-JJJJMMTT-HHMM`), nie loeschen. Traegt die Sperre den
   Zeitstempel des EIGENEN Commit-Versuchs (Erstversuch 17:11:43, Lock 17:11:43),
   ist sie das Abbruch-Artefakt des eigenen Aufrufs - umbenennen und denselben
   Commit wiederholen.
10. **Bericht neu erzeugen und den Rueckgang zeigen** (Anzahl Entscheidungen
    vorher/nachher) — das ist der Beleg, dass die Rauschfixes greifen.
11. **Committen und pushen:** nur eigene Pfade namentlich, nie `git add -A`;
    `--author="Hermes <hermes@local>"` fuer eigene, `fremd@local` fuer fremde
    Arbeit; `git push origin master`.

## Befund-Klassen: konkrete Behebung

Die haeufigsten Entscheiden-Zeilen und ihre Aufloesung (jede mit echtem Lauf
belegt, nicht nur umgebaut):

- **MCP-Drift "im Manifest aktiv, fehlt bei Hermes"** — die Richtung bestimmt
  der IST-Zustand, nicht das Manifest. Pruefen: laeuft die App, die der Server
  braucht (Prozess), und kennt die Claude-Config den Server? Laeuft die App
  nicht und fehlt er in Claude, ist die Hermes-Config (`enabled: false`) die
  neuere Wahrheit — das Manifest auf `false` anheben (gleiche Bauart wie
  blender), NICHT den Server erzwingen. Danach `mcp-sync-check.ps1` erneut:
  muss "ALLES IN ORDNUNG" melden.
- **Fremd-Grenze "Ordner liegt nicht auf der Platte"** — meldet der Block
  PLOTZLICH alle oder viele `Werkstatt/...`-Eintraege, ist zuerst die
  `Werkstatt`-Junction zu pruefen (`(Get-Item Werkstatt -Force).LinkType` —
  leer statt `Junction` = zerstoert, Reparatur in `systemdiagnose`
  `references/windows-junctions.md`), NICHT die Eintraege umschreiben. Erst
  wenn die Junction steht, weiter im Einzelfall: pruefen, ob der Ordner
  verschoben wurde (z. B. nach `Werkstatt/`). Liegt er unter einem
  bereits gelisteten Elternordner (`Werkstatt` ist als Ganzes gelistet),
  ist der Einzeleintrag REDUNDANT und wird entfernt, nicht auf den neuen Pfad
  umgeschrieben. `fremd.py --pruefen` nennt die Redundanz selbst ("ein Eintrag
  genuegt (der kuerzere)").
- **konfig-doktor "Datei hinter Flag fehlt"** (Status "Vermutung") — ist oft
  ein Fehlalarm: die Datei ist optional oder wird vom Server selbst erzeugt.
  Vor jedem Umbau pruefen, ob der Server nachweislich laeuft (mcp-sync-check
  OK, Werkzeuge antworten). Laeuft er, ist der Pfad im Manifest eine harmlose
  Altlast — nicht anfassen.
- **Bedingung 4 "Ziel fehlt / Ordner nicht erreichbar"** — der Q:-Zielordner
  der Spur existiert schlicht nicht. Fix: `mkdir -p Q:\Handel_Journal\<spur>`;
  der naechste Dauerlauf-Zyklus spiegelt hinein. Danach `spiegelstand.py`
  erneut — muss "gleich" melden.
- **Herzschlag-Wert weicht von der Regel ab** (Block 11b) — beim Korrigieren
  des Werts AUCH die Felder `_herzschlag_regel` und `_herzschlag_folge` in
  derselben wachen.json anheben: sie koennen den Stand VOR der Regelanderung
  beschreiben und widersprechen sonst dem neuen Wert. Wert + Feldtexte in
  einem Zug, mit `.bak-JJJJMMTT`.
- **"Kritischer Waechter war deaktiviert" (Block 9, Selbstheilung)** — ein
  deaktivierter Waechter ist schutzloser Betrieb, und ein Check, der das nur
  meldet, verhindert nichts (13.10.2026: morgens gemeldet, abends 5-h-
  Gateway-Ausfall, weil niemand reparierte). Block 9 aktiviert die Aufgaben in
  `$kritischeWaechter` (derzeit Gateway-Waechter, Basis-Dauerlauf,
  Dauerlauf-Waechter) bei Deaktivierung selbst wieder per `schtasks /Change
  /ENABLE` und meldet es als `[erledigt]`; `$gewolltDeaktiviert` (Allowlist,
  dokumentiert abgeschaltete Stufen) bleibt unangetastet. In die kritische
  Liste gehoert nur, wessen Neustart KEINE Handels-Gates umgeht.
  `Enable-ScheduledTask` braucht Admin (0x80070005), schtasks.exe nicht.
  Muster, Auswahlregel und Testweg: `references/selbstheilende-waechter.md`.

## Pitfalls

- **JSON-Konfigdateien (Manifest, wachen.json, FREMD-Liste) nicht mit dem
  fuzzy patch-Werkzeug editieren.** Es verzieht bei mehrzeiligen Bloecken die
  Einrueckung und schleust Tippfehler in Stringwerte ein (`Werkstatttatt`,
  `WerkWerkstatt`), und der Escape-Drift-Fehler verlangt Backslash-Zaehlen.
  Fuer strukturierte Dateien den Block per Python `json.load`/`json.dump`
  aendern (ein Feld setzen, dann zurueckschreiben) und danach IMMER
  `json.loads` als Validierung laufen lassen — der Patch-Mechanismus meldet
  "JSON ok" nicht von selbst. Ein Tippfehler in einem Pfadwert faellt sonst
  erst beim naechsten Prueflauf auf.
- **Ein Haenger ist kein "kein Befund".** Der Bericht wird am Ende geschrieben:
  haengt Block 14, fehlen ALLE Bloecke danach, und `letzter-lauf.md` bleibt
  tagealt, waehrend jeden Morgen ein Tageslog entsteht. Der Aufgabenzustand
  sagt dabei "Ready".
- **Protokolle werden je Tag ueberschrieben** (`systempruefung-<heute>.log`):
  ein zweiter Lauf am selben Tag macht den ersten unfindbar. Vor dem Neulauf
  die Befunde notieren.
- **Ein Check, der nur meldet, ist kein Schutz.** Block 9 meldete den
  deaktivierten Gateway-Waechter im Morgenbericht; der Ausfall kam 8 h spaeter.
  Kritische Waechter brauchen Selbstheilung, Dauerfehlalarme eine Whitelist —
  beide Muster in `references/selbstheilende-waechter.md`.
- **`Enable-ScheduledTask` braucht Admin, `schtasks /Change /ENABLE` nicht.**
  Auch fuer Limited/faupe-Tasks kommt 0x80070005; schtasks.exe laeuft ohne
  Erhoehung (Exit 0). Selbstheilung im user-Kontext MUSS schtasks nutzen.
- **Der volle Prueflauf dauert ~150 s** (Block 5 wandert den Baum) — im
  Hintergrund fahren (`background=true, notify=true`), nie mit 400-s-Timeout im
  Vordergrund warten (gemessen: erster Vordergrund-Versuch lief in den Timeout).
- **Testlaeufe ueberschreiben die Tagesberichte.** Vor einem Lauf mit
  Wegwerf-Task die drei `systempruefung-*.md/.log` als `.bak-test` sichern und
  danach zurueckschieben — sonst ist der offizielle Bericht ein Test-Artefakt.
- **`$LASTEXITCODE` nach einer Pipe pruefen, nicht erst nach dem Filtern mit
  `read_file`-Aequivalenten der Shell** — sonst misst man den Exit des letzten
  Rohrglieds und haelt einen toten Dienst fuer gesund.
- **Ein toter Docker-Daemon nimmt den Container mit.** Fehlt `nautilus-demo`
  samt Image, hilft nur der Neubau: `docker build -t nautilus-demo-node:1.231.0 Agenten/Handel/nautilus`
  dann `docker run -d --name nautilus-demo --restart unless-stopped -e OKX_API_KEY=dummy-node-key -e OKX_API_SECRET=dummy-node-secret -e OKX_API_PASSPHRASE=dummy-node-pass nautilus-demo-node:1.231.0`
  (idempotent auch in `Agenten/Routinen/nautilus-docker-start.ps1`).
- **Ein Aufgaben-Code ist erst mit seiner Zeitgrenze ein Befund.** `3221225786`
  (0xC000013A) bei einem Wrapper, der einen Dauerdienst startet, ist fast immer
  die `ExecutionTimeLimit` der Aufgabe, nicht ein Skriptfehler. Vor dem Beheben
  `(Get-ScheduledTask <name>).Settings.ExecutionTimeLimit` lesen: ein zu kleines
  Limit killt eine echte Sicherung MITTEN im Lauf, und ihr Protokoll endet ohne
  Ende-Zeile. Beleg am 30.09.2026: Sicherung/Zweitkopie standen auf `PT1H` und
  wurden nach genau einer Stunde abgeraeumt; Zielordner waren trotzdem frisch.
  `267014` bei einem Stundenlauf ist dagegen der Neustart, kein Skriptfehler.
- **`IgnoreNew` schuetzt nicht gegen einen zweiten Prozess.** Eine Aufgabe, deren
  Wrapper sofort zurueckkehrt, startet bei JEDER zweiten Ausloesung (Handstart,
  Fremdsitzung) ein zweites Kind: am 30.09.2026 liefen zwei MoonDev-Treiber
  samt doppeltem Agentensatz. Der Einzelinstanz-Schutz gehoert in den Wrapper
  (Prozessabfrage; Suchtext aus Teilen bauen, sonst trifft der Filter die eigene
  Kommandozeile), nicht in die Aufgabenplanung.
- **Ein Volltext-Suchlauf ueber den ganzen Baum ist O(156.000).** Agenten+MaxHirn
  tragen so viele Dateien (ohne node_modules/.venv/hermes-agent). Eine
  Referenzsuche je Kandidat mit eigenem `Get-ChildItem -Recurse` stand nach
  43 Minuten noch im Block. Regel: erst ALLE Kandidaten sammeln, dann EIN
  Suchlauf, und der nur ueber Textendungen und ohne `site-packages`,
  `.venv*`/`dist-info`. `.venv.bak-*` faellt durch keine Ausschlussliste, die
  nur `.venv` kennt.
- **"Docker-Engine antwortet nicht" heisst: die WSL-Distro steht.** Der Motor
  ist `docker-desktop`; Docker Desktop allein bringt ihn nicht hoch (Log:
  `returning engine error`). Was hilft: `wsl --shutdown`, haengende
  `Docker Desktop`/`com.docker.backend` beenden, Docker Desktop neu starten,
  ~90 s warten, `docker ps` pruefen - danach laeuft auch `nautilus-demo`.
- **Robocopy meldet Code 11, wenn Dateien waehrend des Laufs entstehen und
  vergehen** (Cache-, Cron-Ausgabe-, Log-, Sperrordner). Fix ist `/XD` fuer den
  fluessigen Ordner, NICHT `/R` erhoehen.
- **Nicht jeder Nicht-0-Code ist ein Fehler** — `267014` bei einem Dauerlauf ist
  der Normalfall beim Herunterfahren. Umgekehrt: ein Code `0` beweist ohne das
  eigene Protokoll nichts.
- **Angebotene Loeschungen aus der Pruefung sind Vorschlaege**, keine Auftraege.
  Modelle (`Modelle/`, Stufe 2) erst nach Rueckfrage bei Max loeschen; vorher
  pruefen, ob eine Kopie auf `G:`/`Q:` liegt (Modelle sind von der Sicherung
  ausgenommen, meist gibt es keine).
- **Der Bericht traegt ein UTF-8-BOM** (PowerShell `Set-Content -Encoding UTF8`):
  ein Anker `^#` findet die Kopfzeile nicht, solange das BOM nicht abgeschnitten
  ist (`text.lstrip("\ufeff")`). Gilt fuer jeden Parser auf diese Logs.
- **Testsuiten schreiben in echte Spuren** (Bedingung 4) — nach einem Testlauf
  kurz `spiegelstand.py` gegenproben, bevor man "Basis unberuehrt" behauptet.

## Verification

- `read_file` auf `systempruefung-letzter-lauf.md`: Kopfzeile von heute, Ende
  des Tagesprotokolls mit Ende-Zeile, Entscheiden-Liste kleiner als vorher.
- `git status --porcelain` nennt nur frische Fremdarbeit (< 30 min) und keine
  eigenen Dateien mehr; `git log --oneline origin/master..master` ist leer.
- Fuer jede behobene Aufgabe steht `LastTaskResult 0` mit frischem `LastRunTime`
  oder der Handlauf mit "ENDE ok".

## Wache

`scripts/berichts-alter.py` meldet mit Exit 1, wenn der Bericht aelter als die
Schwelle ist (Standard 26 h, `--stunden N`). Gedacht fuer einen Cronjob
(`cronjob_manage`, no_agent, taeglich nach dem Prueflauf): leere Ausgabe = still.
Invoke through the `terminal` tool.

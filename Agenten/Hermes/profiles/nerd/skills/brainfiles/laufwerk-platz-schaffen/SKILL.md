---
name: laufwerk-platz-schaffen
description: "Platz auf Laufwerken schaffen: messen, löschen, umziehen."
category: brainfiles
platforms: [windows]
metadata:
  hermes:
    tags: [Plattenplatz, Aufraeumen, Windows, Caches]
---

# Platz schaffen, ohne etwas zu verlieren

## Wann
„C: ist voll“, „räum auf“, „was kann weg“, „was kann auf die externe SSD“,
„warum wird der Platz nicht mehr“, oder wenn eine Routinemeldung
`No space left on device` auftaucht. Auch als Vorarbeit vor jedem langen
Schreibvorgang auf einem fast vollen Laufwerk.

Für den eigentlichen Ordnerumzug mit Verweissuche gilt der Skill `umzug`
(nutzerverwaltet) — hier geht es um Messen, Bewerten, Platz gewinnen.

## Prozedur

1. **Laufwerke messen, nicht schätzen.**
   `Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3'` liefert je Laufwerk
   Frei/Gesamt/Prozent. Kleine Prozente sind der Auftrag, nicht die absolute
   Zahl: 4 % von 2,7 TB ist genauso kritisch wie 4 % von 475 GB.
2. **Verknüpfungen zuerst prüfen.** Bevor irgend ein Ordner dem Laufwerk
   zugerechnet wird:
   `Get-ChildItem <Wurzel> -Force | Select-Object Name, LinkType, Target`.
   Eine Junction (`Modelle -> O:\Modelle`) bedeutet: die gemessenen Gigabyte
   liegen **auf dem Ziel**, nicht hier. Ohne diese Prüfung zieht man falsche
   Schlüsse und verschiebt, was längst verschoben ist.
3. **Belegung zuordnen.** Pro Ordner eine Größe, dann die dicksten
   Einzeldateien. Auf demselben Laufwerk kann man abschätzen; bei großen
   Bäumen kostet eine rekursive Messung mehr Zeit als die Aktion selbst — siehe
   Werkzeugfallen.
4. **Jeden Kandidaten einordnen, bevor gelöscht wird:**
   - *regenerierbar* (Temp, Build-Cache, `node_modules`, `.build`, `target`,
     Duplikat-Ordner mit `DUPLIKAT` im Namen) → löschen, mit Nachweis.
   - *Fremd-Klon / Werkzeugordner* (geklonte Fremd-Repos, Plugin-Sammlungen) →
     **erst nachweisen, dass niemand ihn liest**, dann löschen. Ein Klon mit
     eigenem `.git` und bekanntem Remote ist jederzeit neu holbar und damit
     regenerierbar; ein Ordner mit `SKILL.md` oder Plugin-Marker ist es nicht.
     Traegt der Klon geladene Skills, ist oft schon sein `.git` allein der dicke
     Brocken (belegt: 570 von 828 MB) und darf weg, solange der Arbeitsbaum
     bleibt. Rezept mit Befehlen, inklusive der Pruefung auf eigene Commits:
     `references/fremd-klon-ballast.md`.
   - *Umgebung* (`hiberfil.sys`, `pagefile.sys`, Windows-Update-Cache) →
     melden, erst nach ausdruecklicher Freigabe des Nutzers umsetzen (Admin
     + Neustart noetig). Nachweis fuer eine aufgeblaehte Auslagerungsdatei:
     `Get-CimInstance Win32_PageFileUsage` — `AllocatedBaseSize` gegen
     `CurrentUsage` stellen (belegt: 40.960 MB zugeteilt, 193 MB benutzt).
     Das komplette Fix-Rezept (Registry-MultiString, Admin-Skript, UAC,
     Verifikation): `references/auslagerung-ruhezustand.md`.
   - *Archiv, das nur einmal existiert* → **verschieben, nie löschen**.
   - *Nutzerdaten* (Papierkorb, Bilder, Videos, Dokumente) → nur melden. Der
     Papierkorb gehört dem Nutzer; Größe nennen, nicht leeren.
5. **Löschen mit Nachweis.** Größe vorher messen, löschen, `Test-Path`
   nachher, am Ende die Differenz des freien Platzes. Die Differenz ist die
   Zahl, die der Nutzer sehen will.
6. **Umziehen statt löschen**, wo die Daten noch gebraucht werden: auf einen
   **anderen physischen Datenträger** (`Get-Partition` / `Get-Disk`), danach
   den alten Pfad als Junction stehen lassen, damit kein Verweis bricht.
7. **Verifizieren.** Dateizahl und Größe auf beiden Seiten vergleichen, dann
   erst die Quelle entfernen. Die Zusammenfassung eines Kopierwerkzeugs ist
   kein Nachweis.

## Skripte im Skill (statt abtippen)

Alle per `terminal` aufrufen, Ausgabe in eine Datei im Scratch-Ordner leiten.

| Skript | Wofuer | Aufruf |
|---|---|---|
| `scripts/groessen-messen.ps1` | Posten je Unterordner **reparse-sicher** messen (Reparse-Punkte werden benannt statt gezaehlt) | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/groessen-messen.ps1 -Wurzel $env:LOCALAPPDATA -Top 15` |
| `scripts/caches-leeren.sh` | reproduzierbare Caches leeren und je Ordner vorher/nachher messen | `bash scripts/caches-leeren.sh > <scratch>/cache-leeren.txt 2>&1` |
| `scripts/muell-leeren.ps1` | Inhalte von Muell-Ordnern leeren, mit Zahl je Ordner | `powershell … -File scripts/muell-leeren.ps1` (oder `-Ordner <pfad>`) |

Alle drei als **Hintergrundauftrag** starten (ein Lauf braucht Minuten, das
Terminal-Zeitlimit liegt bei ~420 s), danach die Ausgabedatei mit `read_file`
lesen. `scripts/caches-leeren.sh` nennt jede Zahl selbst — die Meldung eines
Reinigungswerkzeugs ist keine Quittung, die Ordnergroesse ist es.

## Regeln (Standing)
- **Eine Reserve wird GEHALTEN, nicht nur gemeldet.** Auf `C:` bleiben 30 GB frei
  (Entscheidung des Nutzers); faellt der Platz darunter, raeumt die Wache selbst auf —
  aber nur die vier erlaubten, reproduzierbaren Posten: Temp-Dateien aelter als 24 h,
  CrashDumps, uv-Cache, npm-Cache. Werkzeug `Agenten/Hermes/scripts/platz-wache.py`
  (Cron `platz-wache`, taeglich, leere Ausgabe = nichts senden); Schalter
  `--ohne-aufraeumen` (nur messen), `--trocken`, `--immer`, `--json`. Die Reserve muss
  ueber dem liegen, was ein einzelner Bau transient braucht (Desktop-/Electron-Build:
  rund 20 GB) — sonst ist sie keine Reserve.
- **Waehrend eines Baus/Updates wird GAR NICHT geloescht.** Ein Cache-Leeren mitten im
  Bau zerstoert ihn: bei vollem Laufwerk bricht der App-Tausch mit `WinError 5` ab und
  der Bau mit `OSError: [Errno 28] No space left on device`; die halbfertige Obligation
  bleibt im Baum stehen, und JEDER weitere Start versucht sie erneut (Bootschleife statt
  Fehlermeldung). Vor dem Loeschen die Zeugen pruefen: Marker
  `$HERMES_HOME/.hermes-update-in-progress` und `installs/*/source-completion-pending`
  sowie Kommandozeilen (`source_completion`, `hermes_cli.main update`, `electron-builder`,
  `npm run build`, `vite build`, `uv`). Vor einem eigenen Bau/Update einmal messen:
  `python Agenten/Hermes/scripts/platz-wache.py --ohne-aufraeumen`.
- **Routine-Aufräumen fasst nur Temp und Cache an.** `node_modules`, `.venv`,
  virtuelle Umgebungen sind Projektzustand, kein Müll; sie nur löschen, wenn
  es für dieses Projekt ausdrücklich entschieden und der Weg zurück (das
  Paketwerkzeug) benannt ist.
- **Nichts aus Stufe 0 anfassen** — Nutzerdaten, Zugangsdateien,
  Platzhalter-PDFs. Löschkandidaten dort nur *melden*.
- **Keine Massenoperation ohne Sicherung** bei Stufe‑1‑Dateien.
- **Ein Ergebnisbericht mit Zahlen** (frei vorher → frei nachher, was wohin),
  eine Empfehlung, keine Optionsliste.
- **Volle Laufwerke melden sich im Ereignisprotokoll.** Wiederholte
  `Volsnap`-Ereignisse 36 („Die Schattenkopien von Volume … wurden abgebrochen,
  weil der Schattenkopiespeicher nicht auf ein benutzerdefiniertes Limit
  vergroessert werden konnte“) heissen: Das Laufwerk ist so voll, dass die
  Wiederherstellungspunkte sterben. Das ist ein harter Dringlichkeitsgrund fuer
  `C:` — und ein Nachweis, den ein reiner Prozentwert nicht liefert.

## Pitfalls
- **Junctions verfälschen jede Größenmessung** in beide Richtungen: der
  Quellpfad zeigt auf das Ziel, und ein rekursives Aufsummieren zählt die
  Daten doppelt, wenn beide Wege erfasst werden. Umgekehrt liefern Werkzeuge,
  die der Verknüpfung **nicht** folgen (`find`, `rg`), über den Junction-Pfad
  **still nichts**: eine Zählung über `Werkstatt/...` meldete „2 Atlanten,
  1,0 MB" statt 33 Atlanten und 5,1 GB. Eine Null über einem Junction-Pfad ist
  deshalb kein Beweis, dass nichts da ist — über die **Liste der Zieleinträge**
  summieren (je Eintrag den erzeugten Pfad messen) oder den echten Pfad
  (`O:/Werkstatt/...`) nennen. Vor einer Zahl kurz prüfen, ob der gemessene Pfad
  selbst eine Verknüpfung ist.
  **Selbst-Verweise machen die ganze Liste unbrauchbar, nicht nur eine Zeile:**
  In `%LOCALAPPDATA%` zeigt der historische Verweis `Anwendungsdaten`
  (englisch `Application Data`) auf den Elternordner zurück. `du -sm <ordner>/*/`
  folgt ihm, zaehlt den Verzeichnis-Inode einmal — und druckt danach fast nichts
  mehr: die Liste bestand aus drei Eintraegen (`Anwendungsdaten` als groesster
  Posten mit der ganzen Summe), die zwoelf echten Unterordner fehlten ganz. Wer
  daraus schliesst, es liege nur ein Ordner dort, irrt sich um zwei
  Zehnerpotenzen. Richtig fuer Groessen unter Windows: PowerShell, mit
  Reparse-Punkten explizit aussortiert
  (`if ($d.Attributes -band [IO.FileAttributes]::ReparsePoint) { … }`), und den
  Rest je Unterordner mit `Get-ChildItem -Recurse -File | Measure-Object Length
  -Sum` summieren. Merkmal eines Artefakts: ein Verweis-Ordner
  (`Anwendungsdaten`, `Application Data`, Junction-Namen) erscheint als
  groesster oder einziger Posten.
- **Auch ein Elternordner, der Verknüpfungen nur ENTHÄLT, wird unterschätzt —
  nicht nur der Verknüpfungspfad selbst.** Ein rekursives Aufsummieren über den
  Elternpfad (`du -sh <ordner>` oder `Get-ChildItem -Recurse | Measure-Object
  Length -Sum`) zählt die Junction-Kinder nicht mit, weil es den Links nicht
  folgt; der korrekte Befehl ist die **Liste der Einträge**: `du -sh <ordner>/*/`
  liefert die Junction-Ziele mit. Sanity-Check vor dem Melden: **eine Summe,
  die kleiner ist als ein einziges bekanntes Kind, ist selbst-evident falsch**
  (gemessen 0,7 GB für einen Ordner mit bekanntem 828-MB-Unterordner) — dann
  neu messen statt die Zahl zu glauben. Derselbe Fehler entsteht leise, wenn
  `-ErrorAction SilentlyContinue` eine abgebrochene Rekursion verschluckt: eine
  zu niedrige Zahl ist kein Befund, sondern ein Messfehler.
- **Rekursive Größenmessung großer Bäume reißt die Zeitgrenze des
  Host-PowerShell-Werkzeugs (~300 s).** Das gilt auch fuer einen **einzelnen**
  Ordner: `AppData\Local\Temp`, `AppData\Local\Packages` und `C:\$Recycle.Bin`
  enthalten sechsstellige Dateizahlen und laufen einzeln schon in die Grenze.
  Nie rekursiv messen, um eine Zahl zu bekommen: die Belegung je Laufwerk aus
  `Win32_LogicalDisk`/`df` nehmen und darunter nur benannte Teilpfade mit
  begrenzter Tiefe ansehen. Die billigste belastbare Zahl bleibt die Differenz
  des freien Platzes vor/nach der Aktion. Liegt die Quelle auf einem externen
  oder langsamen Laufwerk (USB, exFAT) oder laeuft dort gerade eine Kopie, ist
  auch eine einzelne rekursive Messung unbrauchbar: Umfang und Bytes stattdessen
  aus einem **Trockenlauf des Kopierers** holen (`robocopy <quelle> <ziel> /L /E`
  meldet Dateien und Bytes, ohne zu kopieren) — das kostet Sekunden statt der
  Zeitgrenze.
- **Lange Pfade (~260 Zeichen) brechen Umzüge.** `robocopy /MOVE` bleibt an
tiefen `node_modules` hängen und wiederholt endlos, statt zu berichten;
  Fortschritt deshalb am freien Platz messen. Das `\\?\`-Präfix hilft bei
  robocopy **nicht**, zum Löschen langer Bäume aber sehr wohl:
  `cmd /c rd /s /q "\\?\C:\...\tief"`.
- **Was robocopy nicht kopieren kann, ist fast immer der regenerierbare
  Cache** — dieser gehört vor dem Umzug gelöscht, nicht mitgeschleppt.
- **Ein Umzug darf nicht am Zeitlimit hängen.** Lange Läufe als eigenen
  Prozess starten und pollen, statt blockierend aufzurufen:
  `Start-Process cmd.exe -ArgumentList '/c', '<robocopy … /LOG:…>'`, dann
  `Get-Content <log> -Tail` und den freien Platz beobachten. `/R:0 /W:0` macht
  aus dem endlosen Wiederholen einen schnellen, im Log lesbaren Fehler — ohne
  die beiden Schalter dreht robocopy an denselben Dateien Runde um Runde, und
  der blockierende Aufruf reißt dabei die Zeitgrenze. Das `\\?\`-Präfix
  **nicht** über `cmd /c` reichen: cmd zerlegt es, und robocopy sieht dann
  einen Netzwerkpfad.
- **Kein Zwischenzustand stehen lassen.** Gelingt die Junction nicht, weil
  eine Anwendung den Ordner hält, bleibt eine leere Hülle liegen — und wer
  dort schreibt, füllt das alte Laufwerk wieder. Das gehört in den Bericht.
- **Ein Ordner unter einem Werkzeug-/Plugin-Verzeichnis ist noch kein
  benutztes Werkzeug.** Vor dem Löschen die Quelle autoritativ erfragen, nicht
  aus dem Ordnernamen schließen: `hermes plugins list --json` liefert je Plugin
  `source` — `bundled` heißt, es steckt im Hermes-Paket und der Ordner wird
  nicht gebraucht; nur ein Katalog-/Pfadeintrag (`catalog:…`) macht den Ordner
  zur Quelle. (Belegt: von 21 Ordnern in `Agenten/Hermes/plugins` mit 2,1 GB war
  genau einer ein echtes Katalog-Plugin.) Genauso bei Claude-Plugins: die
  lebenden Marketplaces stehen in `~/.claude/plugins/known_marketplaces.json`
  unter `~/.claude/plugins/marketplaces/…` — ein Ordner mit
  `.claude-plugin/marketplace.json` unter `Agenten/Hermes/plugins/` ist eine
  Kopie, nicht die Quelle.
- **Eine SKILL.md-Zählung mit zu kleiner Tiefe erklärt einen skill-tragenden
  Klon für tot.** `find <ordner> -maxdepth 2 -name SKILL.md` meldete 0 für einen
  Ordner mit 46 Skills (die liegen in Unterordnern der Klone) — dieselbe Zahl
  hätte 828 MB gelöscht, die Skills tragen. Immer mindestens `-maxdepth 4`
  zählen, bevor „kein SKILL.md, also Ballast" behauptet wird.
- **Ein Suchlauf über einen Baum mit einem großen Klon reißt die Zeitgrenze.**
  `grep -rn` (und rekursives Lesen über `~/.claude`) bricht nach der Grenze ab
  und liefert **nichts**, was wie ein sauberes „keine Treffer" aussieht. Suche
  auf die kleinen Wahrheitsdateien begrenzen (`config.yaml`, `profile.yaml`,
  `MCP-Manifest.json`) bzw. `--exclude-dir=plugins --exclude-dir=.venv`, und
  Indizes lesen statt Bäume scannen.
- **Bash-`/tmp` ist für native Windows-Werkzeuge unsichtbar.** Eine Ausgabe, die
  die Shell nach `/tmp/x.json` schreibt, findet `python` beim Lesen nicht
  (`FileNotFoundError`) — die MSYS-Pfade werden nicht übersetzt. In den
  Scratch-Ordner mit **nativem** Pfad schreiben
  (`C:/Users/<user>/…/Agenten/Hermes/cache/scratch/x.json`) und diesen Pfad auch
  dem Leser geben.
- **Die dicken Posten liegen in App-Daten und Update-Rueckstaenden, nicht in den
  Nutzerordnern.** Gemessen auf einem vollen `C:`: `AppData\Local` 88 GB,
  `AppData\Roaming` 33 GB — der Vault selbst 6,5 GB. Bevor ein Umzug von
  Dokumenten vorgeschlagen wird, diese drei Kandidaten pruefen und mit Zahlen
  nennen: (a) App-Daten und Paket-Caches (`AppData\Local`, `Roaming`,
  `Local\Packages`, `uv\cache`, Docker-vhdx), (b) **Update-Rueckstaende**: ein
  Programmupdate legt Kopien seiner Zustandsdateien ab (belegt: 2 x 408 MB
  Notfallkopien plus 410 MB Snapshot plus 427 MB Live-Datenbank = ~1,6 GB fuer
  EIN Update), (c) Prozess-Logs von Dauerprozessen. Diese Baeume rekursiv zu
  messen reisst die Zeitgrenze (s. o.) — benannte Teilpfade mit begrenzter Tiefe
  messen oder ueber die Liste der Eintraege summieren (`du -sm <ordner>/*/`). Legt
  das Programm seine Rueckstaende in einen EIGENEN Ordner (`state-snapshots/`),
  gehoert dessen Groesse in den Bericht — sonst wird der Nutzer beim naechsten
  Mal wieder den Vault verdaechtigen. Gemessene Posten je Unterordner und was
  davon NICHT geloescht werden darf (Roaming-`npm` traegt global installierte
  CLIs, `ms-playwright` die Browser-Binaries, `Packages` Programmzustand):
  `references/app-daten-und-caches.md`.
- **`skill_view` listet nicht jede Datei unter `scripts/` auf.** Nach dem Anlegen
  der Skripte erschien in `linked_files` nur die `.sh`-Datei, die beiden `.ps1`
  waren aber da (per `search_files`/`read_file` im Skill-Ordner nachsehen). Kein
  Grund, ein Skript neu zu schreiben, nur weil die Liste es nicht nennt.
- **Ein laufendes Skript darf man nicht ueberschreiben.** bash liest eine
  Skriptdatei stueckweise waehrend der Ausfuehrung; wird sie mittendrin neu
  geschrieben, bricht der LAUFENDE Prozess mit
  `unexpected EOF while looking for matching "` ab (Exitcode 2, belegt am
  23.09.2026: ich habe `caches-leeren.sh` verbessert, waehrend die alte Fassung
  lief). Neue Fassung als eigene Datei schreiben oder den Lauf abwarten — sonst
  ist der gerade laufende Auftrag verloren und die Ausgabedatei bricht mitten
  in der Liste ab.
- **Dubletten-Verdacht pruefen, nicht annehmen.** Ein Ordner namens `…DUPLIKAT`
  ist ein Hinweis, kein Beweis; vor dem Loeschen Inhalt gegen die eine Kopie
  stellen, die bleiben soll.
- **Vor einem Umzug in ein festes Ziel (Archiv) auf Kollision pruefen.**
  `Test-Path <ziel>`; existiert das Ziel, ABBRECHEN statt ueberschreiben — der
  Erhaltenswerte kann dort schon liegen, und zwar vollstaendiger (belegt:
  eine 151-Dateien-Kopie fast ueber einen 229-Dateien-Bestand geschrieben;
  der Kollisionsschutz hat es verhindert). Gleich davor die Praemisse pruefen,
  dass die Quelle ueberhaupt die einzige Kopie ist: existiert der Erhaltenswerte
  schon im Archiv oder in der Zweitkopie, ist der Umzug ueberfluessig — die
  Quelle wird dann zu Redundanz, kein neuer Zielort noetig.
- **Eine Junction innerhalb einer Sicherungsquelle zieht die Daten in die
  Sicherung.** robocopy folgt Verknüpfungen. Ein Junction irgendwo unter der
  Quelle (`Agenten/`, Vault) lässt den nächsten Sicherungslauf den Inhalt des
  Ziels mitkopieren und flutet das Sicherungslaufwerk. Vor jedem Junction
  prüfen, ob der Ort in einer Sicherungsquelle liegt, und ihn sonst dorthin
  legen, wo die Sicherung nicht hinsieht (z. B. unter `%LOCALAPPDATA%`) — auch
  wenn der Pfad dort uneleganter wirkt.
- **Erst die Pfadauflösung des Verbrauchers lesen, dann den Ort wählen.** Ob
  ein Programm seinen Ordner über eine Umgebungsvariable, eine Konstante oder
  `HERMES_HOME` findet, entscheidet, **welcher** Junction überhaupt wirkt. Im
  Quelltext nachsehen, welche Funktion den Pfad baut; existiert keine Variable,
  ist der Junction die einzige Möglichkeit. Ein Junction am falschen Ort ist
  stille Arbeit: der erwartete Pfad bleibt leer, und es fällt erst auf, wenn
  der Verbraucher eingeschaltet wird. Gleich mitprüfen, ob er überhaupt aktiv
  ist — ist er abgeschaltet, liest niemand den Ordner und der Gewinn ist reine
  Platzzahl (gehört in den Bericht, weil es die Dringlichkeit ändert).
- **Die Zahl „frei vorher" nicht aus einem früheren Aufruf übernehmen.** Bei
  mehreren gleichzeitig arbeitenden Sitzungen kann sich der belegte Platz
  zwischen zwei Messungen um Gigabyte ändern. Vorher und nachher im selben
  Durchgang messen und beide Zahlen nennen.
- **Ein Cache-Befehl ist kein Nachweis — die Ordnergroesse vor und nach dem
  Befehl ist es.** Werkzeuge melden Unzutreffendes: `uv cache clean` schrieb
  „No cache found at <pfad>", waehrend der Ordner von 2,2 GB auf 1 MB fiel —
  die Meldung ist keine Quittung. Und die Ausbeute ist je Werkzeug sehr
  verschieden: ein inhaltsadressiertes Store-Pruning (`pnpm store prune`) gibt
  nur wenige hundert MB zurueck, `npm cache clean --force` etwa die Haelfte,
  `pip cache purge` und die Dump-/Temp-Ordner fast alles. Deshalb je Ordner
  eine Zahl VORHER nennen, dieselbe NACHHER, und die erwartete Ausbeute nicht
  an der Summe der Ordner festmachen (sonst wirkt ein korrekter Lauf wie ein
  Fehlschlag). Bleibt in `Temp`/`CrashDumps` ein Rest, sind das Dateien in
  Benutzung — kein Fehler. Die Reinigungsbefehle selbst plus die Nachmessung
  sprengen das Zeitlimit des Terminals (~420 s): als EINEN Hintergrundauftrag
  mit Ausgabedatei fahren und die Datei lesen. Messwerte und Fahrplan:
  `references/app-daten-und-caches.md`.
- **Ein ploetzlicher Schwund von zig GB ist oft die Auslagerungsdatei, nicht
  ein laufender Schreiber.** `pagefile.sys` waechst bei einer Commit-Spitze und
  schrumpft nie von selbst; sie kann 40 GB belegen und 200 MB benutzen. Das gilt
  NICHT nur fuer die systemverwaltete Form: auch eine per Registry mit **Bereich**
  eingestellte Datei (`PagingFiles`-Eintrag `o:\pagefile.sys 4096 16384`, sichtbar
  auch in `Win32_PageFileSetting` als `InitialSize`/`MaximumSize`) laeuft bis zu
  ihrem Maximum hoch — belegt: 4 GB zugeteilt, 16 GB Maximum, stand bei 15,96 GB,
  und der Schwund sah wie ein Datenschreiber von 12 GB aus. Bevor ein „aktiver
  Schreiber" gesucht wird: `Win32_PageFileUsage` (`AllocatedBaseSize` gegen
  `MaximumSize` stellen), die **Datei selbst** ansehen (`Get-Item
  O:\pagefile.sys | Select Length,LastWriteTime` — der Aenderungszeitpunkt sagt,
  WANN der Platz weg ging) und den freien Platz zweimal messen (~45 s Abstand).
  Den Schluessel im Befund nennen: die Datei gibt den Platz nicht zurueck
  (Heilung erst mit fester Groesse + Neustart) — und sie ist kein Grund, irgendwo
  Daten zu loeschen.

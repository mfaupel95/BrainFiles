---
name: laufwerk-platz-schaffen
description: "Platz auf Laufwerken schaffen: messen, löschen, umziehen."
category: brainfiles
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
   - *Umgebung* (`hiberfil.sys`, `pagefile.sys`, Windows-Update-Cache) →
     melden und den Befehl nennen, nicht selbst entscheiden.
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

## Regeln (Standing)
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
- **Rekursive Größenmessung großer Bäume reißt die Zeitgrenze des
  Host-PowerShell-Werkzeugs (~300 s).** Das gilt auch fuer einen **einzelnen**
  Ordner: `AppData\Local\Temp`, `AppData\Local\Packages` und `C:\$Recycle.Bin`
  enthalten sechsstellige Dateizahlen und laufen einzeln schon in die Grenze.
  Nie rekursiv messen, um eine Zahl zu bekommen: die Belegung je Laufwerk aus
  `Win32_LogicalDisk`/`df` nehmen und darunter nur benannte Teilpfade mit
  begrenzter Tiefe ansehen. Die billigste belastbare Zahl bleibt die Differenz
  des freien Platzes vor/nach der Aktion.
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
- **Dubletten-Verdacht prüfen, nicht annehmen.** Ein Ordner namens `…DUPLIKAT`
  ist ein Hinweis, kein Beweis; vor dem Löschen Inhalt gegen die eine Kopie
  stellen, die bleiben soll.
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

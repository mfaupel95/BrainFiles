---
name: sicherung-fahren
description: "Sicherungen fahren: G:, O: und ausser Haus pruefen."
category: brainfiles
platforms: [windows]
metadata:
  hermes:
    tags: [Sicherung, Backup, robocopy, Laufwerke]
---

# Sicherungen fahren und pruefen

## Wann
„vorher sichern", „Sicherung fahren", „Sicherung pruefen", eine Routinemeldung
ueber einen fehlgeschlagenen Lauf, oder eine Sicherung als erste Zeile eines
groesseren Auftrags. Max' Muster ist *„X warten. Vorher sicherung"* — die
Sicherung laeuft VOR der Arbeit, nicht danach; der Auftrag selbst wird in dieser
Zeit nicht angefasst und das gehoert in den Bericht.

## Wo die Skripte liegen
Unter `Agenten\` — **nicht** in der BrainFiles-Wurzel. Wer dort `sichern*.ps1`
sucht, findet nichts und schliesst falsch, es gebe keine Sicherung: den Pfad im
Wrapper lesen (`$wurzel = Split-Path $PSScriptRoot -Parent`), statt zu raten.

| Skript | Ziel | Besonderheit |
|---|---|---|
| `Agenten\Routinen\sicherung.ps1` | Wrapper, schreibt das Protokoll | ruft das eigentliche Skript |
| `Agenten\sichern.ps1` | G: Hauptsicherung | laeuft ueber den Wrapper |
| `Agenten\sichern-zweitkopie.ps1` | O: Zweitkopie | eigener Task |
| `Agenten\sichern-ausser-haus.ps1` | Q: ausser Haus | `-NurPruefen` = Trockenlauf |

Die geplanten Aufgaben starten denselben Wrapper. `robocopy` traegt `/XD`-Ausnahmen
fuer Ordner, die eine laufende Anwendung sperrt (z. B. `browser-profile`);
die Fehlermeldungen dazu stehen in `handel-spuren/references/browser-edge-sperre.md`.

## Prozedur
1. **Stand messen, nicht erinnern.** Die drei Kopien GETRENNT pruefen (Alter und
   Ergebnis je Kopie) aus `Agenten\Routinen\logs\` — der Hauptlauf schreibt
   `<name>-letzter-lauf.log`. „Die Sicherung ist aktuell" ist eine Aussage ueber
   DREI Laeufe, nicht ueber einen.
2. **Ziele pruefen.** Angesteckt und Platz frei?
   `Get-CimInstance Win32_LogicalDisk` (`DeviceID`, `VolumeName`, freier Platz).
   Ein Ziel, das nicht angesteckt ist, ist kein Skriptfehler.
3. **Hauptlauf fahren** — idempotent und schnell, wenn nichts geaendert wurde.
   Abgekoppelt starten, sonst reisst der Aufruf die Zeitgrenze des
   Host-Werkzeugs (~300 s):
   `Start-Process powershell -ArgumentList '-ExecutionPolicy','Bypass','-NoProfile','-File','<pfad>' -WindowStyle Hidden`,
   danach auf die ENDE-Zeile im Protokoll warten.
4. **Ausser-Haus zuerst trocken** (`-NurPruefen`). Der Trockenlauf nennt je
   Durchgang Dateien und Bytes (robocopy `/L`) und damit den echten Nachholbedarf
   in Sekunden — statt einer rekursiven Messung, die in die Zeitgrenze laeuft.
5. **Echte Kopie** abgekoppelt starten und pollen (Prozessliste + Protokoll),
   nie blockierend warten.
6. **Bewerten an den Zahlen des Laufs:** robocopy-Code 0–3 ist Erfolg (0 = nichts
   zu tun, 1 = kopiert, 2 = Extras, 3 = beides), ab 8 ist es ein Fehler; dazu die
   Zeile „0 Fehler" und die verglichene Dateizahl. `$LASTEXITCODE` pruefen — die
   Ausgabe allein sagt nichts.
7. **Danach melden, in der Reihenfolge:** je Kopie Ziel, Alter, Ergebnis in
   Zahlen; was jetzt konkret gesichert ist; was offen blieb.

## Pitfalls
- **Das Wrapper-Protokoll fuellt sich erst am ENDE.** Der Lauf sammelt die
  Ausgabe und haengt sie in einem Zug an — wer mittendrin hineinsieht, findet nur
  die Kopfzeile und schliesst falsch „haengt". Der Fortschritt steht in der
  **tmp-Datei daneben** (waechst waehrend des Laufs). „Protokoll leer, aber
  robocopy laeuft" heisst also nur „noch nicht fertig".
- **Die Ausser-Haus-Kopie hat absichtlich keine geplante Aufgabe** — sie braucht
  die angesteckte SSD, ein zeitgesteuerter Lauf wuerde nur scheitern. Folge: sie
  wird still alt und niemand merkt es. Belegt: 13 Tage alt, 89.421 Dateien /
  18 GB Nachholbedarf, waehrend die beiden anderen Kopien stundenaktuell waren.
  Wer „alles gesichert" meldet, ohne das Alter DIESER Kopie einzeln zu messen,
  meldet einen Zustand, den es nicht gibt.
- **Ein Lauf, der 0 Dateien kopiert, ist ein gueltiges Ergebnis.** „0 kopiert /
  N uebersprungen" heisst: der Zielstand ist schon aktuell. Nicht als Fehler
  lesen und nicht in eine Nachkontrolle umdeuten.
- **Waehrend eine Kopie auf ein externes Laufwerk laeuft, dort nichts rekursiv
  messen.** `Get-ChildItem -Recurse | Measure-Object Length -Sum` laeuft in die
  Zeitgrenze und liefert NICHTS (sieht wie ein leeres Verzeichnis aus). Umfang
  ueber den Trockenlauf des Kopierers holen (robocopy `/L /E`).
- **Ein Abbruch mitten im Lauf sieht nicht wie ein Fehler aus.** Nicht auf den
  START schauen, sondern auf die ENDE-Zeile warten; erst danach ist „Sicherung
  gelaufen" gedeckt.
- **Vor einem Start pruefen, ob schon ein Lauf laeuft** (Prozessliste) — zwei
  Laeufe derselben Quelle auf dasselbe Ziel schreiben sich in die Quere, und ein
  zweiter Start sieht wie eine Wiederholung aus, ist aber eine Parallelkopie.
- **Die Zusammenfassung des Kopierers ist keine Quittung.** Wenn Max fragt „ist
  alles gesichert", gehoeren Dateizahl und Groesse auf BEIDEN Seiten dazu (Quelle
  gegen Ziel), nicht nur die Exit-Codes.
- **Ein laufender Sicherungsjob ist kein vollstaendiger Beweis.** Sperrt eine
  offene Anwendung Dateien, laeuft der Lauf weiter und laesst sie aus — sichtbar
  an der Fehlerzeile im Protokoll; also nie „vollstaendig" melden, solange dort
  etwas steht.
- **Ein Eingriff in die Sicherungsquelle gehoert VOR den Lauf.** Waehrend der
  Kopie keine Stufe-1-Dateien aendern (`.ps1`, Wachen, `AGENTS.md`) — sonst
  sichert man einen halben Stand und weiss hinterher nicht, welchen.

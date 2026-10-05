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

**Was das laufende System offen haelt oder selbst neu erzeugt, gehoert NICHT in
die Kopie — sonst faerbt EINE gesperrte Datei den ganzen Lauf rot.** robocopy
meldet dann "Code 11" (Dateien fehlten oder waren gesperrt) und der Wrapper endet
mit Exit 1, obwohl alles Uebrige kopiert wurde. Belegte Klassen, jede mit
gemessenem Grund: Bau-Caches (`.whl` waehrend eines Baus gesperrt), die
Berichtsausgabe der Cron-Jobs (entsteht und verschwindet WAEHREND des Laufs),
`.pid`-Sperrdateien und die Begleitdateien einer laufenden SQLite-Datenbank
(`*.db-shm`, `*.db-wal` — eine Rohkopie waere ohnehin kein gueltiger
Datenbankstand). Solche Pfade EINMAL in die `/XD`-Liste bzw. nach `/XF` aufnehmen
und den GRUND daneben schreiben; sonst raeumt die naechste Sitzung die Ausnahme
weg, weil sie wie eine Luecke aussieht. Erfolg ist die Zeile "robocopy-Code 0-3 -
erfolgreich." plus "ENDE ok" im Protokoll — nicht das Ausbleiben einer
Fehlermeldung.

## Prozedur
1. **Stand messen, nicht erinnern.** Die drei Kopien GETRENNT pruefen (Alter und
   Ergebnis je Kopie) aus `Agenten\Routinen\logs\` — der Hauptlauf schreibt
   `<name>-letzter-lauf.log`. „Die Sicherung ist aktuell" ist eine Aussage ueber
   DREI Laeufe, nicht ueber einen. Bei der Ausser-Haus-Kopie gehoert die EXISTENZ
   ihrer geplanten Aufgabe dazu (Schritt 2b): ohne Aufgabe laeuft sie nicht mehr,
   egal was das Protokoll zeigt.
   **Die Wrapper-Protokolle sind UTF-16.** Roh gelesen (mit einem Zeilenwerkzeug)
   kommt Nullbyte-Salat zurueck, der wie ein leeres oder kaputtes Protokoll
   aussieht — mit einem Decoder lesen (BOM strippen, dann `utf-16-le`, danach erst
   `utf-8`). Dasselbe gilt fuer die `.tmp`-Datei daneben.
   **Ein Decode, der nicht abbricht, ist kein Decode, der funktioniert.**
   `bytes.decode("utf-16-le")` wirft fast nie eine Ausnahme — bei falscher
   Endianness oder falschem BOM liefert es still CJK-Salat, der wie ein kaputtes
   Protokoll aussieht und einen zu der Fehlannahme verleitet, die Datei sei leer
   oder beschaedigt. Deshalb NICHT die erste Ausnahme-freie Kodierung nehmen,
   sondern die Kandidaten durchprobieren und das Ergebnis PRUEFEN: BOM strippen,
   dann je Kodierung den Anteil druckbarer Zeichen in den ersten ~2000 Zeichen
   messen (> 85 % = plausibel) und erst die beste nehmen, sonst `utf-8` mit
   `errors="replace"`. Als Einzeiler:

```python
b = open(p, "rb").read()
if b.startswith(b"\xef\xbb\xbf"):
    b = b[3:]
for enc in ("utf-16-le", "utf-8", "cp1252"):
    try:
        t = b.decode(enc)
    except Exception:
        continue
    kopf = t[:2000]
    if sum(1 for c in kopf if c.isprintable() or c in "\r\n\t") > len(kopf) * 0.85:
        break
```
2. **Ziele pruefen.** Angesteckt und Platz frei?
   `Get-CimInstance Win32_LogicalDisk` (`DeviceID`, `VolumeName`, freier Platz).
   Ein Ziel, das nicht angesteckt ist, ist kein Skriptfehler.
2b. **Bei der Ausser-Haus-Kopie zusaetzlich die Aufgabe selbst pruefen** —
   `schtasks /query /tn 'MaxHirn-Ausserhaus-Kopie'` oder die Aufzaehlung
   `Get-ScheduledTask | Where-Object { $_.TaskName -like 'MaxHirn*' }`.
   `Get-ScheduledTask -TaskName <name>` findet auch VORHANDENE Aufgaben nicht
   und taugt nicht als Zeuge. Fehlt die Aufgabe, laeuft die Kopie nicht mehr,
   auch wenn ihr Protokoll einen frischen Lauf zeigt — das war ein Handlauf.
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
- **Die Ausser-Haus-Kopie erneuert sich selbst** — Aufgabe
  `MaxHirn-Ausserhaus-Kopie`, taeglich 21:30 (nach der Zweitkopie 21:00), Wrapper
  `Agenten\Routinen\ausserhaus-kopie.ps1`. Fehlt die SSD, endet der Lauf in
  Sekunden mit **Exitcode 2 = "uebersprungen", und das ist kein Fehlschlag**
  (dieselbe Regel wie bei der Zweitkopie). Anlegen und Nachziehen uebernimmt der
  Hermes-Cron `ausserhaus-aufgabe-sichern` (taeglich 08:30): er legt eine
  fehlende Aufgabe an und schaltet eine abgeschaltete wieder ein. **Dieser Cron
  ist kein Beleg fuer Dauerhaftigkeit** — meldet er bei JEDEM Lauf
  „war nicht vorhanden und ist angelegt", ist die Aufgabe offenbar nicht haltbar,
  und die Kopie laeuft nur, wenn jemand sie von Hand nachzieht. Die wortgleiche
  Wiederholung IST der Befund; der Zeuge sind seine Ausgabedateien
  (`Agenten/Hermes/cron/output/<job-id>/*.md`, mehrere Tage nebeneinander), nicht
  der letzte Lauf.
  **Was dann zu tun ist — heilen UND messbar machen.** Ein Tages-Cron ist als
  Wache untauglich: er heilt einmal um 08:30 und die Kopie um 21:30 faellt wieder
  aus. Statt weiter zu raten, wer die Aufgabe entfernt, zwei Dinge in EINEM
  Skript (Muster: `Agenten/Hermes/scripts/ausserhaus-aufgabe-wache.py`, Cron
  alle 10 min, `no_agent`, leere Ausgabe = nichts senden):
  (a) fehlt die Aufgabe, neu anlegen — im 10-Minuten-Takt, damit der eigentliche
  Termin nicht mehr ausfaellt;
  (b) bei JEDER Pruefung Anlege-/Weg-Zeitpunkt in eine Merkdatei schreiben
  (`cache/<name>-wache.json`), sodass die UEBERLEBENSZEIT ablesbar wird. Ohne
  (b) weiss man nach einer Woche nur „verschwindet", mit (b) „haelt 20 Minuten"
  — und das ist die Angabe, die den Loescher eingrenzt (ein Prozess mit
  Minuten-Takt, nicht ein Logon-Skript).
  **Und die Reihenfolge: das Ereignisprotokoll VOR dem naechsten Ausfall
  einschalten** (`wevtutil sl Microsoft-Windows-TaskScheduler/Operational /e:true`,
  braucht Admin). Es ist im Auslieferungszustand AUS und hat KEINE Vorgeschichte —
  nach dem Einschalten sind nur neue Faelle belegt, alles davor ist spurlos. Ein
  Loeschvorgang erscheint dort als Ereignis **Id 141** (mit Benutzer/Prozess);
  bleibt 141 leer, wurde die Aufgabe nicht ueber die Task-API entfernt. Wer erst
  beim naechsten Mal einschaltet, hat wieder nichts. Trotzdem gilt:
  das Alter DIESER Kopie einzeln messen (Fristwache `ausserhaus-frist-wache`,
  14 Tage), und **"ausser Haus bringen" bleibt Handarbeit** — eine Kopie auf dem
  Schreibtisch ist keine Kopie ausser Haus.
  Wer „alles gesichert" meldet, ohne das Alter DIESER Kopie einzeln zu messen,
  meldet einen Zustand, den es nicht gibt.
- **Die Kopie ausser Haus bleibt bewusst UNVERSCHLUESSELT** (Entscheidung Max,
  abgeschlossen - kein offener Punkt). Auf ihr liegen Klartext-Zugangsdaten
  (`Wissen/Zugaenge.md`); die Vertraulichkeit haengt damit am AUFBEWAHRUNGSORT,
  nicht an einer Verschluesselung. BitLocker oder eine andere Verschluesselung
  deshalb nicht erneut vorschlagen und nicht als Luecke melden - die Warnung im
  Abschlusstext des Skripts bleibt stehen und wird als bewusst hingenommen gelesen.
  Gemessen wird weiter nur, was ohnehin gemessen wird: Alter der Kopie (Fristwache)
  und dass sie physisch ausser Haus liegt.
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

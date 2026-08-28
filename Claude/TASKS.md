# Offene Punkte

Sitzungsübergreifende Aufgabenliste. Einzige Quelle für „was ist noch offen".
Angelegt am 2026-08-28, weil offene Punkte aus früheren Chats bis dahin
nirgends festgehalten wurden und mit dem Sitzungsende verloren gingen.

## Regeln

- **Am Sitzungsanfang lesen**, bevor gefragt wird, woran gearbeitet werden soll.
- **Sofort eintragen**, wenn ein Punkt entsteht — nicht am Sitzungsende sammeln.
  Wird die Sitzung vorher abgebrochen, ist der Punkt sonst weg.
- **Erledigtes nach `## Erledigt` verschieben**, mit Datum. Nicht löschen —
  die Historie zeigt, was schon einmal versucht wurde.
- **Nichts erfinden.** Nur eintragen, was Max gesagt hat oder was aus einer
  abgebrochenen Arbeit tatsächlich offen blieb. Vermutete Folgeaufgaben
  gehören als Vorschlag in die Zeile „Kontext", nicht als eigener Punkt.
- **Stand aktuell halten.** Fällt beim Arbeiten auf, dass ein Eintrag hier
  überholt ist, sofort korrigieren und die Korrektur melden — auch wenn es
  nicht zur laufenden Aufgabe gehört.
- IDs fortlaufend `T-001`, `T-002`, … Einmal vergeben, nie wiederverwenden.

## Status-Kürzel

| Kürzel | Bedeutung |
|---|---|
| `[ ]` | offen, noch nicht angefangen |
| `[~]` | in Arbeit / teilweise erledigt |
| `[?]` | wartet auf Entscheidung oder Information von Max |
| `[!]` | blockiert, Ursache im Kontext benannt |
| `[x]` | erledigt → gehört nach unten |

## Eintragsformat

```
- [ ] **T-001 — Kurztitel**
      Kontext: worum es geht, warum es offen ist
      Nächster Schritt: eine konkrete, ausführbare Handlung
      Angelegt: 2026-08-28 · Zuletzt: 2026-08-28
```

Optional zusätzlich: `Betrifft:` (Pfad, Projekt, Gerät), `Wartet auf:` (bei `[?]`/`[!]`).

## Offen

- [?] **T-002 — Auslagerungsdatei liegt auf einer USB-Platte**
      Kontext: In `HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\
      Memory Management\PagingFiles` stehen drei Einträge:
      `c:\pagefile.sys 0 0`, `g:\pagefile.sys 4096 16384`,
      `o:\pagefile.sys 4096 16384`. **`G:` ist die Seagate Portable, also USB.**
      Im S3-Standby wird die USB-Anbindung stromlos; greift der Kernel nach dem
      Aufwachen auf ausgelagerte Seiten zu, bevor die Platte zurück ist, folgt
      ein harter Reset ohne Bluescreen und ohne Speicherabbild — genau das
      beobachtete Bild (T-004). Begründete Hypothese, kein Beweis; unabhängig
      davon ist der Eintrag falsch am Platz.
      Stand 28.08.: Auf `G:` liegt **derzeit keine** `pagefile.sys`, weil die
      Platte beim Systemstart abgezogen war. Beim nächsten Neustart mit
      angeschlossener Platte legt Windows sie wieder an — der Eingriff wirkt
      also nur, wenn er **vor** dem nächsten Neustart erfolgt.
      Nächster Schritt: Max führt den Befehl mit erhöhten Rechten aus (siehe
      unten) — Claude hat in dieser Sitzung keine Adminrechte.
      Sicherung des Schlüssels liegt als
      `Routinen/sicherungen/MemoryManagement-20260828.reg`.
      Wartet auf: Ausführung durch Max
      Angelegt: 2026-08-28 · Zuletzt: 2026-08-28

- [ ] **T-003 — Windows Search stürzt seit 24.08. in Endlosschleife ab**
      Kontext: Über 5000 Dienstabstürze im Protokoll (815 allein am 28.08.,
      läuft weiter). Fehler: „Das System kann den angegebenen Pfad nicht
      finden", `SetupCompletedSuccessfully = 0`, keine `Windows.edb`. Folgen:
      Dauerlast und ein Systemprotokoll, das so schnell überschrieben wird,
      dass Absturzspuren älter als vier Tage verloren sind. Betrifft Max'
      eigene Archivsuche nicht — die ist SQLite-basiert.
      Nächster Schritt: Suchindex neu aufbauen lassen oder WSearch abschalten.
      Angelegt: 2026-08-28 · Zuletzt: 2026-08-28

- [ ] **T-004 — Neun Abstürze ohne Bluescreen seit 08.08., Ursache offen**
      Kontext: Alle Kernel-Power-41-Ereignisse haben `BugcheckCode = 0` und
      `SleepInProgress = 16` — kein Bluescreen, kein Speicherabbild, sondern
      harter Reset im Standby-Zusammenhang. Vier davon 3–10 Minuten nach dem
      Aufwachen aus S3. Keine WHEA-Hardwarefehler, keine Speicherfehler,
      beide SSDs `Healthy`. Es liegt kein einziger Dump zum Auswerten vor.
      **Vorbehalt zum jüngsten Fall:** Am 28.08. hat Max das CMOS zurückgesetzt.
      Ein Kaltstart dabei erzeugt im Protokoll dasselbe Bild wie ein Absturz
      (Kernel-Power 41, `BugcheckCode = 0`, EventLog 6008). Ob der Eintrag vom
      28.08. ein echter Absturz war oder Max' eigener Eingriff, ist ungeklärt.
      Die Vorfälle vom 20., 21. und 27.08. sind davon unberührt — das Muster
      steht auch ohne den heutigen Datenpunkt.
      Nächster Schritt: nach T-002 beobachten, ob es aufhört. Wenn nicht:
      S3-Standby probeweise abschalten (Rechner durchlaufen lassen).
      Angelegt: 2026-08-28 · Zuletzt: 2026-08-28

- [ ] **T-005 — J: (WD My Book) nicht angeschlossen, iCloud-Junction ins Leere**
      Kontext: Nach dem CMOS-Reset am 28.08. sind Seagate (`G:`, `H:`, `I:`)
      wieder da, die WD My Book aber nicht: `Get-PnpDevice` meldet `Unknown`,
      `Test-Path J:\` ist `False`. Die Junction
      `C:\Users\faupe\iCloudPhotos` zeigt auf `J:\iCloudPhotos` und läuft
      damit ins Leere — rund 30.635 Mediendateien. Nichts ist verloren, die
      Platte hängt nur nicht dran. Dieselbe Platte hat 479 unkorrigierte
      Lesefehler (Messung 14.08.), sie ist das schwächste Laufwerk im System.
      Nächster Schritt: Max fragen, ob sie absichtlich ab ist.
      Angelegt: 2026-08-28 · Zuletzt: 2026-08-28

- [?] **T-006 — Echtzeituhr ging 68 Minuten nach**
      Kontext: Am 28.08. um 15:20:12 hat der Zeitdienst die Systemzeit um
      **4.108.764 ms (68,5 Minuten)** vorgestellt — von 14:11:43 auf 15:20:12.
      Bis dahin liefen alle Protokolleinträge seit dem Start mit falscher Zeit.
      Zwei Erklärungen: harmlos die Uhr, die nach dem CMOS-Reset neu gestellt
      werden musste; unangenehm eine schwache CMOS-Batterie, die auch
      BIOS-Einstellungen wieder verlieren würde.
      Folge für die Diagnose: **Zeitstempel um den 28.08. herum sind bis 15:20
      um 68 Minuten verschoben.** Zeitabstände innerhalb dieses Fensters
      stimmen, absolute Uhrzeiten nicht.
      Nächster Schritt: nach dem nächsten Kaltstart prüfen, ob die BIOS-Zeit
      erneut wegläuft. Wenn ja: CMOS-Batterie (CR2032) tauschen.
      Wartet auf: Beobachtung beim nächsten Start
      Angelegt: 2026-08-28 · Zuletzt: 2026-08-28

## Erledigt

- [x] **T-001 — Sicherungslaufwerk G: fehlt, Hauptsicherung hat kein Ziel**
      Erledigt 2026-08-28: Kein Defekt. Max hatte die USB-Platten für einen
      CMOS-Reset abgezogen. Seagate Portable ist wieder angeschlossen,
      `G:\MaxHirn-Sicherung` erreichbar (2751,1 GB, 128,8 GB frei, `Healthy`).
      Der 20-Uhr-Lauf kann wieder arbeiten. Der Fehlstand bestand nur, solange
      die Platte ab war.

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

- [!] **T-001 — Sicherungslaufwerk G: fehlt, Hauptsicherung hat kein Ziel**
      Kontext: `MaxHirn-Sicherung` kopiert nach `G:\MaxHirn-Sicherung\`.
      G: ist keine der beiden internen SSDs (nur C: und O: vorhanden) und
      derzeit nicht angeschlossen. Letzter erfolgreicher Lauf 27.08. 20:00.
      Der 20-Uhr-Lauf schlägt fehl, solange die Platte fehlt. Die Zweitkopie
      nach `O:\MaxHirn-Zweitkopie\` läuft unabhängig weiter.
      Nächster Schritt: Platte anschließen oder klären, ob sie ausgefallen ist.
      Betrifft: Routinen/sicherung.ps1, Aufgabe MaxHirn-Sicherung
      Angelegt: 2026-08-28 · Zuletzt: 2026-08-28

- [?] **T-002 — Auslagerungsdatei auf nicht vorhandenem Laufwerk g:**
      Kontext: In `HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\
      Memory Management\PagingFiles` steht `g:\pagefile.sys 4096 16384`,
      obwohl G: fehlt. Aktiv sind nur C: (9 GB) und O: (4 GB). Verdacht auf
      Zusammenhang mit den Abstürzen: liegt eine Auslagerungsdatei auf einem
      Laufwerk, das im Standby wegfällt, ist ein harter Reset ohne
      Speicherabbild die typische Folge. Nicht bewiesen.
      Nächster Schritt: Eintrag für g: entfernen — erfordert Ansage und
      Neustart, deshalb noch nicht getan.
      Wartet auf: Entscheidung von Max
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
      Nächster Schritt: nach T-002 beobachten, ob es aufhört. Wenn nicht:
      S3-Standby probeweise abschalten (Rechner durchlaufen lassen).
      Angelegt: 2026-08-28 · Zuletzt: 2026-08-28

## Erledigt

_Noch keine Einträge._

---
name: aufgaben-verfolgen
description: "Aufgaben fortsetzen oder offenen Bestand abfragen."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [aufgaben, tasks, fortsetzen, FREMD, Status, Inventur]
    related_skills: [hermes-config-ops, systemdiagnose, dauerprozess-bewachen]
---

# Aufgaben verfolgen und fortsetzen

Gilt für: *"setz die offenen Aufgaben fort"*, *"was ist noch offen?"*,
*"fortsetzen"*, *"summarize open tasks"*, *"what's pending?"* — also
Lead-in-Anfragen, die keine konkrete Aufgabe benennen, sondern den
Aufgabenbestand abfragen oder eine Unterbrechung übernehmen.

## Wann nicht

- Eine **konkrete** Aufgabe ist genannt (z. B. ein T-ID wie T-371, ein
  Repo-Name wie agent-trade-kit, ein Skill-Name). Dann gehe direkt zum
  fachlichen Skill oder zur betroffenen Datei — nicht hierher.
- Es geht um **laufende** Wachen/Dauerläufe: `dauerprozess-bewachen`.
- Es geht um **Scheduling**: `hermes-config-ops` (Cron) und
  `Wissen/Routinen.md` (Windows-Aufgaben).

## Die Trackers (in dieser Reihenfolge lesen)

Das Repo hat keine einzelne TASKS-Datei; der Bestand ist über mehrere
Dateien verteilt. Bei einer Lead-in-Anfrage immer in dieser Reihenfolge:

| # | Datei | Inhalt | Wo |
|---|-------|--------|-----|
| 1 | `FREMD-Phasen.json` | Phasenstand je Fremd-Repo, mit `status` (`offen`/`in_arbeit`/`fertig`/`blockiert`) und `blockiert_weil` | Wurzel (`../` von `Agenten/Hermes`) |
| 2 | `Werkstatt/plan-fremdrepos-ausbau-2026-10-09.md` | Der Plan, der `FREMD-Phasen.json` treibt; enthält Phase-0-Ergebnisse, Adaptervertrag, Auswertungen, nächste Schritte | `../../Werkstatt/` |
| 3 | `MaxHirn/Wissen/Sitzungsanalyse-YYYY-MM-DD.md` | Gezählte T-IDs, priorisierte offene Punkte, Erfolge — die kompakte Prioritätenliste | `../../../MaxHirn/Wissen/` |
| 4 | `MaxHirn/Archiv/TASKS.md` | Detaillierte T-ID-Einträge mit Kontext, Massnahmen, Nachweis — die Einzelarchivdatei | `../../../MaxHirn/Archiv/` |
| 5 | `MaxHirn/Wissen/Routinen.md` | Eingeplante Abläufe mit Status, Zeitplan, Wrapper — was ohne Aufforderung läuft | `../../../MaxHirn/Wissen/` |

**Begründung der Reihenfolge:** (1) und (2) sind die *aktuellen* Planungsdateien — sie sind frischer als die Archiv-TASKS.md und enthalten Entscheidungen, die nach dem letzten T-ID-Eintrag getroffen wurden. (3) ist die kompakte Prioritätenliste, wenn (1) und (2) zu viel Ballast tragen. (4) ist der Archivbestand — für Detailtiefe, wenn die anderen drei nicht genügen. (5) ist nur für den Fall, dass "offen" eigentlich "noch nicht eingeleitet" bedeutet.

### Lesen — Pfade

Der Arbeitsbaum beginnt in `Agenten/Hermes`. Von dort:

- Wurzel: `../` (ein Level hoch)
- Werkstatt: `../../Werkstatt/`
- MaxHirn/Vault: `../../../MaxHirn/`

**Falle:** `MaxHirn/` und `Werkstatt/` sind im Arbeitsbaum jeweils Junctions
auf `O:\`. Wenn ein suchbasierter Aufruf (z. B. `search_files` über die
Wurzel) ins Zeitlimit läuft, dann **gezielt in den wahrscheinlichen Ordnern
suchen** und den Umfang der Prüfung nennen — nie "gibt es nicht" aus einem
Abbruch schließen.

**Falle:** relative Pfade zu `MaxHirn/` scheitern still, wenn sie von einem
Arbeitsverzeichnis aus beginnen, das nicht `Agenten/Hermes` ist. Vor einem
`read_file` auf `MaxHirn/...` den tatsächlichen Standort des Stub-Verzeichnisses
prüfen (`pwd`) und bei Bedarf den absoluten Pfad nehmen (`C:/Users/faupe/Documents/BrainFiles/MaxHirn/...`).

### FREMD-Phasen.json — Statuswerte

```
_status: ["offen", "in_arbeit", "fertig", "blockiert"]
```

- `offen` — Phase `phase_aktuell` noch nicht begonnen
- `in_arbeit` — Phase läuft
- `fertig` — Phase abgeschlossen; Repo wartet auf nächste Entscheidung
- `blockiert` — Phase kann nicht weiter, weil `blockiert_weil` gesetzt ist

**`blockiert` ohne `blockiert_weil` ist ein Fehler im Tracker** — die Regel
steht in der Datei selbst (`_regeln`). Vor der Meldung "blockiert" immer
`blockiert_weil` lesen; fehlt es, ist das ein Befund, kein Standsaldo.

### Sitzungsanalyse — T-IDs

Die Sitzungsanalyse enthält eine Liste priorisierter offener Punkte mit
T-IDs (z. B. T-371, T-369). Diese sind oft **älter** als der Stand in
`FREMD-Phasen.json` und `plan-fremdrepos-ausbau-*.md`. Vor der Übernahme in
eine Antwort:

1. Die erwähnte T-ID in `MaxHirn/Archiv/TASKS.md` suchen (`search_files`
   nach `T-<nummer>`).
2. Den Eintrag auf `[x]` (erledigt) oder `[ ]` (offen) prüfen.
3. Den Eintrag auf "Erledigt Datum" und Hinterkopf prüfen — viele Einträge
   sind als `[x]` markiert, haben aber einen nachgelagerten Hinterkopf (z. B.
   "Ursache unbewiesen, Wache gebaut" oder "Fix auf der Platte, Gateway
   hat ihn noch nicht gelesen"). Das ist kein reines Offen, aber auch kein
   vollständiger Abschluss — beide Seiten melden.

## Was eine "Fortsetzung" konkret sein kann

Nach dem Lesen der Tracker stehen drei Arten von Weiterarbeit zur Diskussion:

| Art | Beispiel | Wer entscheidet |
|-----|----------|-----------------|
| **Blocker entfernen** | Demo-Key für agent-trade-kit (Max muss liefern) | Nutzer |
| **Entscheidung treffen** | Binance→OKX-Umbau intelligent-trading-bot; Fork-Entscheidung; moon-dev-Lizenz | Nutzer |
| **Arbeit fortsetzen** | Phase-0-Inventur für Recherche/Gedächtnis/UI-Repos | Agent (nach Freigabe) |

## When to Use

Diese Skill lädt, wenn die Anfrage **keine namentliche Aufgabe** nennt, sondern
nach dem Gesamtstand, offenen Punkten, einer Unterbrechung oder dem Weiterführen
von etwas Frageltem fragt. Benannte Aufgaben (T-ID, Repo-Name, Skill-Name) gehen
an den fachlichen Skill.

Trigger-Beispiele: "setz die offenen Aufgaben fort", "was ist noch offen?",
"fortsetzen", „summarize open tasks“.

Vor dem Weiterarbeiten die Bereichs-Zuordnung prüfen (`Agenten/Werkzeuge/bereiche.py
--register`): Schreibzugriffe auf `Agenten/Handel/` gehören in Bereich
`handel`, auf `MaxHirn/Wissen/` in Bereich `wissen`. Ein in fremden Bereich
geschriebener Befund wird als `BEFUND` gemeldet (`--aufrufer <bereich>
--pfad <pfad>`), nicht blockiert.

## Bericht

Eine Antwort auf eine Lead-in-Aufgabenanfrage enthält:

1. **Kurzantwort** — wie viele offene Items, wie viele blockiert, wie viele
   laufen.
2. **Blockierte Items mit Grund** — `blockiert_weil` zitieren, nicht
   umschreiben.
3. **Nächste Entscheidung, die vom Nutzer kommt** — konkret benennen, was
   fehlt, damit etwas weiterlaufen kann.
4. **Was läuft ohne Aufforderung** — ein Blick auf `Routinen.md` und die
   Windows-Aufgaben (`MaxHirn-*`), damit nichts doppelt angefangen wird.
5. **Was nicht angefasst wurde** — explizit nennen.

Keine Inventur-Liste der 53 Repos, es sei denn, die Frage zielt danach.
Die FREMD-Listen sind lang; eine aggregierte Antwort (Rollen, Anzahl je
Status) ist der erste Satz, dann nur die Items, die handlungsfähig sind.

## Nach der Bestandsabfrage: Plan schreiben, dann delegieren

Wenn die Anfrage nach dem Bestand zeigt, dass mehrere unabhängige Arbeiten
anstehen (mehr als eine), ist der nächste Schritt vor der Delegierung ein
Pläne-Dokument. Das Dokument kategorisiert die Arbeit nach Wer entscheidet
und enthält keine ausgeführte Arbeit.

**Wann dieser Schritt spurts:** Die Bestandsabfrage ergibt ≥ 2 offene Arbeiten
ohne dass eine davon sofort allein durch einen Agenten erledigt werden kann
(z. B. mehrere Bereiche, ein Nutzer-Entscheid vor Agentenarbeit, mehrere
Repos in derselben Phase).

**Das Pläne-Dokument:**

- **Datei:** `Agenten/offene-arbeiten-plan-YYYY-MM-DD.md` — jedes Mal ein neues
  Datum, nie überschreiben.
- **Struktur:** Kategorien nach Wer entscheidet:
  - Blockierer (Nutzer muss liefern)
  - Entscheidungen (Nutzer)
  - Agent-Arbeit (nach Freigabe), ggf. nach Bereich getrennt
  - Was bereits läuft (ohne Aufforderung)
- **Inhalt pro Eintrag:** Status, was fehlt, nächster Schritt — nicht Begründung
  oder Narration. Ein Eintrag ohne nächsten Schritt ist unvollständig.
- **Kein README-Format:** Das Dokument ist ein Arbeitsplan, kein Projektbeschreibung.
  Keine Kapitel wie "Einleitung", "Ziel", "Hintergrund". Direkt mit den Kategorien.

**Danach:** Pro Handlung (Agent-Arbeit, nicht Entscheidung/ Blocker) eine
separate Delegation starten. Jede Delegation ist ein eigenständiger Task mit
eigener Goal, eigenem output_schema, eigenem Ziel-Pfad. Keine Super-Delegation
die alles auf einmal machen soll.

**Abgrenzung:** Wenn nur eine Arbeit ansteht (z. B. eine Inventur, ein Adapter),
direkt die Arbeit — kein Plan-Dokument als Zwischenschritt. Das Plan-Dokument
ist nur da, wenn es Mehrdeutigkeit gibt, was als Nächstes kommt.

# Anleitung FindusArbeitus — die Tagesrunde

Der Job heißt `findus-tagesdienst` (Cron des Profils, täglich 22:15, Zustellung in den
Telegram-Kanal; auf Zuruf: `hermes -p findusarbeitus chat -q "<Tagesrunde>"`).

Dies ist der Fahrplan für jeden Lauf. Reihenfolge einhalten, Quellen nur lesend.
Bei jeder Feststellung: Quelle dazuschreiben (Befehl/Datei/Log/Zeitstempel).
Was du nicht messen kannst, schreibst du als „ungeprüft" — nie als Tatsache.

## 0. Start

```bash
cd "$HERMES_HOME/../.."          # BrainFiles-Wurzel
cat MaxHirn/Wissen/Schutzregeln.md   # Pflicht vor jedem Schreibzugriff
```

Wurzel = `C:\Users\faupe\Documents\BrainFiles` (bash: `/c/Users/faupe/Documents/BrainFiles`).
Das Terminal startet in `Agenten/Hermes` — immer zuerst `cd` zur Wurzel.

## 1. Quellen sammeln (alle lesend)

| Quelle | Befehl | Was du daraus nimmst |
|---|---|---|
| Git heute | `git log --since="today 00:00" --pretty=format:"%h %an %s" --date=iso --all` | Commits des Tages (wer, was) |
| Git offen | `git status --porcelain` | uncommittete/ruhende Arbeit |
| Dauerlauf | `tail -40 Agenten/Handel/dauerlauf.log` (analog `dauerlauf.mittel.log`, `dauerlauf.hoch.log`) | letzte Zyklen, Fehler, „(live)/(papier) ok" |
| Spuren | `cd Agenten/Handel && ../scanner/.venv/Scripts/python.exe spuren_stand.py` (oder `python spuren_stand.py`) | Tabelle aller Spuren, offene Positionen, letzte Läufe |
| Kanban | `cd Agenten/Hermes && unset PYTHONHOME PYTHONPATH && ./bin/hermes.exe kanban boards list` und je Board `--board <slug> list` | offen/running/blocked je Board |
| TASKS.md | `grep -n "^## " MaxHirn/Archiv/TASKS.md` + `git diff HEAD -- MaxHirn/Archiv/TASKS.md` | heutige Änderungen, höchste Nummer |
| Routinen | `ls -t Agenten/Routinen/logs/*.log | head -8` + letzte Zeilen der neuesten | Sicherung 20:00, Zweitkopie 21:00, Fremdarbeit 20:40, Ausserhaus 21:30 |
| Gateway | `cat Agenten/Hermes/gateway_state.json` + `ls -t Agenten/Hermes/logs/*.log | head -5` | pid, code_version, update-Logs |
| Cron-Übersicht | `ls -t Agenten/Hermes/cron/output | head -10` | nur auffällige Fehler-Marker, nicht jede Datei lesen |

NICHT lesen: `Wissen/Zugaenge.md`, `.env`-Dateien, `auth.json`, `state.db`-Rohdumps,
Handelsjournale im Detail (Zählwerte kommen aus `spuren_stand.py`).

## 2. Tagesnote schreiben

Pfad: `MaxHirn/Wiki/Betrieb/Tageschronik/JJJJ-MM-TT.md` (LF, UTF-8, [[Wikilinks]] erlaubt)

```markdown
# Tageschronik 2026-10-09
> Von FindusArbeitus erstellt — gemessen, nicht erinnert. Quellen je Zeile.

## Systemlauf
- Dauerlauf: Basis PID .., letzter Zyklus .. ; mittel .. ; hoch .. — N Spuren, auffällige Fehler: ..

## Gebaut, geändert, neu
- `abc1234` kurz: Commit-Titel — (1 Zeile Wirkung)

## Befunde
- was aufgefallen ist, mit Beleg (Datei/Log/Nummer)

## Aufgaben & Entscheidungen
- T-NNN neu angelegt: ..
- T-NNN wartet auf Max (`- [?]`): ..

## Ungeklärt / Fehlende Quellen
- was nicht messbar war und warum

## Stand der Boards
- repos: X offen / Y running / Z blocked — handel: .. — wartung: .. — wissen: ..
```

Max 40–60 Zeilen. Wenn ein Tag nichts Neues hat, steht „keine Änderungen" mit Beleg — nie einen erfundenen Eintrag füllen.

## 3. AKTUELL.md überschreiben

Pfad: `MaxHirn/Wiki/Betrieb/Tageschronik/AKTUELL.md` — max 15 Zeilen, fester Ort für alle Agenten.

```markdown
# AKTUELL — Systemstand
Stand: 2026-10-09T22:15+02:00 (von FindusArbeitus)
- Dauerlauf: Basis läuft (PID .., letzter Zyklus ..), mittel .., hoch .. — keine Fehler
- Offene Positionen: N (spuren_stand.py)
- Kanban: repos X offen, handel Y, wartung Z, wissen W
- Letzter Commit: <hash> <Titel>
- Offene Entscheidungen: T-NNN (..), T-NNN (..)
- Nächster geplanter Lauf: morgen 22:15
```

Die alte Fassung steht vollständig in der Tagesnote — nicht aufheben, überschreiben.

## 4. TASKS.md pflegen (Skill `aufgabenliste-pflegen` beachten!)

**Neuer Befund → neue Aufgabe:**
1. Höchste Nummer frisch messen: `grep -oE "T-[0-9]+" MaxHirn/Archiv/TASKS.md | sort -u -t- -k2 -n | tail -1` → nächste freie = max+1 (nie aus dem Kopf).
2. Block einfügen direkt unter `## Offen` (Anker = Blockgrenze, CRLF!):
```
- [ ] **T-NNN — Kurztitel**
      Kontext: .. (mit Beleg)
      Naechster Schritt: ..
      Angelegt: JJJJ-MM-TT · Zuletzt: JJJJ-MM-TT
      Betrifft: <pfade>
```
3. Schreiben byte-genau (CRLF erhalten), dann Tor: `python Agenten/Hermes/skills/aufgabenliste-pflegen/scripts/doppelte_nummern.py --ruhig` — Exit 0 nötig.

**Belegtes Erledigtes schließen:** `python Agenten/Hermes/skills/aufgabenliste-pflegen/scripts/erledigen.py T-NNN "**Erledigt JJJJ-MM-TT.** <gemessenes Ergebnis>"` — nimmt nur `- [ ]`; `- [?]` per Byte-Weg schließen (Kastenstellung wechseln, Entscheidung mit Datum in den Block).

**Entscheidungen von Max:** Einträge, die auf eine Entscheidung warten, tragen `- [?]` und enden mit „Wartet auf: Max — …". Nie selbst entscheiden.

## 5. Kanban pflegen (Skill `kanban-board`)

- `./bin/hermes.exe kanban --board <slug> list` je Board; bei `running` zusätzlich `runs <id>`.
- **Neue Karte NUR wenn:** Arbeit parallel laufen soll, auf Review wartet, oder einen Betriebsprozess startet — und sie KEINE Entscheidung von Max ist. Entscheidungen gehören in TASKS.md.
- Anlegen: Body als Datei nach `Agenten/Hermes/cache/scratch/`, dann
  `./bin/hermes.exe kanban --board <slug> create "Titel" --body-file C:/<nativ>/<pfad> --assignee <profil> --priority 2`
  Hausverbote in jeden Body: „Kein Live-Schalter, keine echte Order" + „Nur eigene Pfade stagen, nie git add -A" + die T-Nummern woertlich.
- Karte schließen nur nach Beleg: Arbeit wirklich fertig geprüft (Commit/Lauf/Test) → `complete <id>`.
- Keine Stufe-0-Inhalte in Kartentexte (Klartext in kanban.db).

## 6. Committen (eigene Pfade) und Bericht

```bash
git add -- MaxHirn/Wiki/Betrieb/Tageschronik/ MaxHirn/Archiv/TASKS.md
git diff --cached --numstat    # LESEN — nur eigene Pfade!
git commit -m "Tageschronik JJJJ-MM-TT: <1-Zeile>"
```

- Fremdes im Index: mit eigenem Index committen (`GIT_INDEX_FILE=Agenten/Hermes/cache/scratch/idx_fau` + `git read-tree HEAD` + `git add <eigene>` + `git commit -F <msg>`), danach `unset GIT_INDEX_FILE` und die eigenen Pfade im echten Index nachziehen.
- Commit-Meldung als Datei unter `Agenten/Hermes/cache/scratch/` und mit C:-Pfad übergeben (`git commit -F C:/...`) — `git commit -F` findet MSYS-/tmp-Pfade nicht.
- Eigene Arbeit innerhalb von 30 Minuten committen, sonst übernimmt sie `fremdarbeit-einziehen.ps1` als fremde Arbeit.

## Fehlerbehandlung

- Ein Fehler: einmal selbst prüfen (Datei da? Befehl vorher/nachher? Quelle verfügbar?).
- Zweiter Fehlversuch mit derselben Annahme ist verboten — Annahme wechseln, Grund notieren.
- Kein erfundener Beleg: wenn die Quelle fehlt, steht in der Tagesnote „Quelle nicht verfügbar", nicht eine Zahl.
- Der Bericht am Ende nennt: was funktioniert · was NICHT angefasst wurde · welche Entscheidung offen ist.

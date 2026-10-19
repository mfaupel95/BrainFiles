---
name: sammelauftrag
description: "Offene Sitzungen zusammenfuehren, pruefen, schliessen."
version: 0.1.0
author: Hermes
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [Brainfiles, Sitzungen, Routinen, Uebergabe, Aufgabenplanung]
    related_skills: [sitzungs-rekonstruktion, bus-integration, sichern, brainfiles-auftrag]
---

# Sammelauftrag: offene Sitzungsarbeit zu einer Aufgabe bündeln

Führt die unerledigte Arbeit paralleler Sitzungen (Claude, Hermes, Codex) zu EINER
Übergabedatei zusammen, entscheidet je Punkt zwischen „Routine“ und „Auftrag“ und
registriert die Routine samt Nachweis. Es ist **kein** Ersatz für `sitzungs-rekonstruktion`
(eine abgebrochene Sitzung verstehen) und baut **keine** neue Fachlogik: es ordnet,
was schon existiert.

Zwei Quellen: der Hermes-Sitzungsspeicher (`state.db`, Schritt 0) und der Arbeitsbaum.
Am Ende steht der Abschluss: erledigte Sitzungen werden **archiviert** (weiches
Verstecken, umkehrbar), nie gelöscht. Tiefe Details zum Speicher in
`references/sitzungsspeicher.md` (laden mit `skill_view`).

Weil Raten hier teuer ist, gilt: jeder Punkt braucht Beleg, Fertig-Kriterium und
Prüfkommando. Ein Punkt ohne diese drei wird nicht aufgenommen, sondern verworfen.

## When to Use

- „Arbeit aller offenen Sitzungen zusammenführen“, „was liegt noch offen“, „nimm alles auf, was hier liegt“
- nach mehreren parallelen Sitzungen oder nach einem Rechnerabsturz, wenn unklar ist, was fertig ist
- „mach daraus einen Task / eine Routine“, „das soll automatisch laufen“
- ein nicht abgeschlossener Auftrag soll nicht im Chatverlauf liegen bleiben
- „aus allen offenen Sitzungen Informationen ziehen“, „was steht in den offenen Sitzungen“, „Sitzungen zusammenführen“
- „Sitzungen schließen/aufräumen, die erledigt sind“, „offene Sitzungen aufräumen“

**Don't use for:** eine einzelne abgebrochene Sitzung rekonstruieren (`sitzungs-rekonstruktion`),
Arbeitsbaum nur committen (`sichern`), eine bestehende Routine an den Bus hängen
(`bus-integration`), eine Regeländerung an einer Handels-Spur (`handel-spuren`).

## Prerequisites

- Arbeiten aus der Repo-Wurzel `BrainFiles/` (Git-Wurzel, enthält `Agenten/`, `MaxHirn/`, `Werkstatt/`).
- Übergabeort ist `Werkstatt/Austausch/<JJJJ-MM-TT>/` — durch `Werkstatt/AGENTS.md` festgelegt
  und **nicht** versioniert (Regel 4: „Versioniert ist hier nur diese Datei“).
  Was dauerhaft bleiben soll, gehört zusätzlich in den Vault (`MaxHirn/Wissen/`).
- Für Schritt 6b: das `cronjob`-Werkzeug. Für 6a: eine **erhöhte** PowerShell
  (`Register-ScheduledTask` legt ohne Admin gar keine Aufgabe an, auch keine harmlose).
- Vor jedem schreibenden Zugriff: `MaxHirn/Wissen/Schutzregeln.md` lesen (Stufe 0/1/2).

## How to Run

Erst sammeln (lesend), dann entscheiden, dann schreiben — in dieser Reihenfolge und
nie in einem Rutsch:

1. `terminal` + `search_files` + `read_file` + `session_search` → Bestandsaufnahme (Schritt 1–2)
2. `write_file` → EINE Übergabedatei mit allen Punkten (Schritt 3–4)
3. `terminal` → Routine registrieren und abnehmen (Schritt 5–7)

## Quick Reference

| Was | Wo |
|---|---|
| uncommittete Arbeit | `git status --porcelain` (jeder Treffer ist ein Kandidat) |
| Sitzungen, letzte Aktivität | `session_search` |
| Claude-/Claude-Code-Sitzungen | `references/claude-sessions.md` (Orte + Lese-Rezept) |
| Übergaben | `Werkstatt/Austausch/` (Ordner je Datum) |
| Sitzungsablagen | `Werkstatt/Sitzungen/`, `Werkstatt/Protokolle/` |
| Läufe mit Fehler | `Agenten/Routinen/logs/*.log` — Zeilen mit `ENDE FEHLER` |
| Hermes-Zeitpläne | `Agenten/Hermes/cron/jobs.json`, Ausgaben in `Hermes/cron/output/` |
| versprochene Routinen | `MaxHirn/Wissen/Routinen.md` (Spalte **Status**) |
| Termine | `MaxHirn/Wissen/Fristen.md` |
| Aufgabenzustand | `Get-ScheduledTask -TaskName 'MaxHirn-*'`, `Get-ScheduledTaskInfo` |
| offene Sitzungen | `scripts/offene_sitzungen.py` (nur lesend) |
| beendete, nicht archivierte | `scripts/beendete_sitzungen.py` (nur lesend) |
| Sitzungsspeicher | `Agenten/Hermes/state.db` (+ `profiles/<name>/state.db`) |
| Sitzungen verwalten | `hermes sessions list/archive/prune/pin/pinned` |

## Procedure

### 0. Sitzungsspeicher abklopfen (lesend)

Dafür liegt `scripts/offene_sitzungen.py` im Skill (stdlib, **nur lesend**). Über das
`terminal`-Werkzeug aus der Repo-Wurzel:

```bash
python Agenten/Hermes/skills/brainfiles/sammelauftrag/scripts/offene_sitzungen.py
```

Es listet die offenen Sitzungen (`ended_at IS NULL`) mit Alter, Umfang und Quelle,
ordnet sie in lebendig / abgebrochen / still ein, zeigt die letzte Nutzer- und
Assistentenzeile je Sitzung (die Grundlage des Zusammenführens) und nennt die
Abschluss-Kandidaten samt Trockenlauf-Befehl. `--alle-profile` bezieht auch die
Bot-Sitzungen unter `profiles/<name>/state.db` ein. Tiefe Details zum Speicher:
`references/sitzungsspeicher.md`.

### 1. Quellen abklopfen (lesend, 5–10 Minuten)

Dafür liegt `scripts/sammeln.py` im Skill (stdlib, **nur lesend**). Über das
`terminal`-Werkzeug aus der Repo-Wurzel:

```bash
python Agenten/Hermes/skills/brainfiles/sammelauftrag/scripts/sammeln.py
```

Es gibt uncommittete Pfade, frisch angefasste Dateien (< 10 min), `ENDE FEHLER`
aus `Routinen/logs/`, die Aufgabenplanung mit Zustandscode, die Cron-Aufträge,
den Inhalt von `Werkstatt/Austausch/` und ein Skelett für die Übergabedatei aus.
Der Zustandscode der Aufgaben ist mit ausgewertet — siehe Pitfalls, nicht jeder
Nicht-`0`-Wert ist ein Fehler.

Ergänzend von Hand:

```bash
git status --porcelain                       # uncommittet = offene Arbeit
git log --oneline -15                        # was zuletzt fertig wurde
```

Dazu `search_files` über `Werkstatt/Austausch/` und `read_file` auf
`MaxHirn/Wissen/Routinen.md` (Statusspalte). Den Chatverlauf nicht mitzählen:
`session_search` liefert Sitzungen und ihre letzte Aktivität, nicht deren Auftrag.

Claude- und Claude-Code-Sitzungen liegen NICHT in `state.db` — Orte, Lese-Rezept
und die Signale, die einen offenen Punkt bedeuten (Session-Limit-Abbruch,
HANDOVER-Open-Questions, ungemergte Worktree-Zweige), stehen in
`references/claude-sessions.md`.

### 2. Lebende von toten Ständen trennen

- **Vor dem Schreiben erneut messen** (`sitzungs-rekonstruktion`): eine „tote“
  Sitzung wacht auf, sobald dort jemand tippt, und hat den Auftrag in der
  Zwischenzeit womöglich erledigt.
- **Fremde Datei mit Änderungszeit < 10 Minuten nicht anfassen** — die Zahl steht
  in `Werkstatt/AGENTS.md`, Regel 2, und ist bewusst keine Ermessensfrage:
  `powershell -NoProfile -Command "(Get-Item <pfad>).LastWriteTime"`.
- **Prozesssuche nie über die eigene Kommandozeile filtern.**
  `Where-Object { $_.CommandLine -like '*dauerlauf.py*' }` findet den Suchenden
  selbst (und jede Shell, die den Text enthält). Immer zusätzlich auf den
  Prozessnamen einschränken:

```bash
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { \$_.Name -like '*python*' -and \$_.CommandLine -like '*<skript>.py*' } | Select-Object ProcessId,ParentProcessId,CreationDate | Format-Table -AutoSize"
```

### 3. Je Punkt fünf Felder

| Feld | Inhalt |
|---|---|
| Auftrag | ein Satz, im Imperativ |
| Beleg | Datei/Pfad/Lauf, aus dem der Punkt stammt (kein Chatverlauf) |
| Fertig-Kriterium | woran man Erledigung **sieht** |
| Prüfkommando | ein Befehl, der genau das zeigt |
| Eigentümer | Mensch / Routine / offene Entscheidung von Max |

Fehlt eins der drei mittleren Felder: Punkt verwerfen und im Bericht unter
„nicht aufgenommen“ nennen. Ein Punkt ohne Fertig-Kriterium wird nie fertig.

### 4. Eine Übergabedatei schreiben

**Achtung Schreibweg:** `Werkstatt` ist eine **Junction** (auf `O:\Werkstatt`).
Das `write_file`-Werkzeug prüft den **aufgelösten** Pfad gegen
`HERMES_WRITE_SAFE_ROOT` und lehnt ab („is outside HERMES_WRITE_SAFE_ROOT /
C:\Users\faupe\Documents\BrainFiles"), obwohl der Pfad im Baum liegt. Kein
Rechteproblem — die Junction wird aufgelöst. Über das `terminal`-Werkzeug
schreiben (Verzeichnis vorher anlegen) oder das Ziel in einen Ordner legen, der
keine Junction ist.

**Die Junction kann STILL verschwunden sein — vor dem Schreiben pruefen.**
`Werkstatt` (und `Modelle`) sind Junctions auf `O:\`; ein echter Ordner an ihrer
Stelle (LinkType leer, Attributes nur `Directory`) heisst: alle Zugriffe ueber
`BrainFiles\Werkstatt\...` laufen in einen Schatten auf C:, nicht nach O: —
zweimal passiert (05.10. und 10.10.2026). Symptom von aussen: eine Routine
scheitert mit „Python oder Ordner fehlt" oder „keine Statusdatei", obwohl der
Ordner auf O: existiert. Vor jedem Schreiben in `Werkstatt/`:
`(Get-Item 'Werkstatt' -Force).LinkType` muss `Junction` sein. Ist er es nicht:
Schatten-Inhalte verlustfrei nach O: retten (Kollisionen nie ueberschreiben,
Hash-Vergleich, Abweichendes nach `O:\Werkstatt\zusammenfuehrung-<datum>`),
dann `New-Item -ItemType Junction -Path <w> -Target 'O:\Werkstatt'`; ein von
einem Prozess gehaltener leerer Schatten laesst sich umbenennen statt loeschen.
Reparatur-Protokoll: `Agenten/Routinen/logs/werkstatt-junction-reparatur-<datum>.log`.
Eine Wache dafuer fehlt (T-390).

`write_file` bzw. `terminal` nach `Werkstatt/Austausch/<JJJJ-MM-TT>/<thema>.md`,
mit dem Vault-Frontmatter (`id`, `title`, `tags`, `created`, `updated`,
`related`, `summary`) und den Regeln aus `Werkstatt/AGENTS.md` Regel 3: **der
Auftrag trägt sich selbst** — was damit geschehen soll, woher die Zahlen
stammen, woran man Erledigung sieht. Ein Agent, der die Datei in einer Woche
findet, hat keinen Gesprächsverlauf mehr. Keine Zugangsdaten hinein (dafür gibt
es genau eine Ablage: `MaxHirn/Wissen/Zugaenge.md`).

### 5. Routine oder Auftrag entscheiden

`Routinen.md` definiert: „Eine Routine ist immer ein vorhandener Skill plus ein
Zeitplan.“ Daraus folgt die Zuordnung:

| Kandidat | Weg |
|---|---|
| wiederkehrend, entscheidungsarm, prüfbar (Abgleich, Spiegelung, Sicherung) | Routine (6a oder 6b) |
| braucht Sprache, Abwägung oder eine Empfehlung („beurteile“, „schlage vor“) | Routine 6b mit Modell |
| einmalig, oder Auslöser ist immer ein Mensch | Auftrag — bleibt in der Übergabedatei, **nicht** automatisieren |
| verbotene Zone (Stufe 0, Schlüssel, Massenlöschung) | nur Vorschlag; Ausführung entscheidet Max |

Faustregel: was kein Prüfkommando hat, darf keine Routine werden — es würde still
falsch laufen.

### 6. Routine registrieren

**6a — lokale Arbeit (Skript/PowerShell), ohne Modell:** Wrapper
`Agenten/Routinen/<name>.ps1` mit den vier Pflichtzeilen
(`. (Join-Path $wurzel 'Bus\Ereignis.ps1')` sowie `Melde-Start` … `Melde-Ende` vor
jedem `exit` und in jedem `catch`), dann die Aufgabe erzeugt eine erhöhte
PowerShell per `Register-ScheduledTask` — vollständige Regeln, Fallen und die
Abnahme stehen in `bus-integration`.

```powershell
$marke = Melde-Start -Wer 'routine/<name>' -Log 'Agenten/Routinen/logs/<name>-letzter-lauf.log'
try { <arbeit> ; Melde-Ende -Marke $marke -Code $LASTEXITCODE }
catch { Melde-Ende -Marke $marke -Code 1 -Text "$_"; throw }
```

**6b — Arbeit, die ein Modell braucht:** über das `cronjob`-Werkzeug anlegen,
nicht über die Aufgabenplanung. Pflichtfelder und worauf es ankommt:

- `schedule` — `'30m'`, `'every day at 9am'`, `'0 9 * * *'`.
- `prompt` — **selbsttragend**: der Lauf hat keinen Chat-Kontext und kann nicht
  zurückfragen. Dateipfade und Erwartung ausschreiben.
- `deliver` — wohin das Ergebnis geht (Vorgabe: dieser Chat; `'local'` nur sichern).
- `enabled_toolsets` — einschränken (z. B. `["terminal"]`), spart Tokens.
- `script` (Ausgabe wird in den Prompt eingespeist) oder `monitor` (läuft erst,
  wenn sich die Ausgabe ändert) für die Sammelarbeit davor.
- `continuity` — jeder Lauf sieht die eigene vorherige Ausgabe (Dedupe, Fortsetzen).
- `workdir` — Verzeichnis, aus dem der Lauf startet (dessen `AGENTS.md` gilt).

Geliefert wird die **letzte Antwort** des Laufs. Vor dem Anlegen liste die
vorhandenen Aufträge (`action='list'`) — ein zweiter, fast gleicher Auftrag ist der
häufigste Fehler.

### 7. Beleg und Abnahme

- Neue/geänderte `.ps1` in `Agenten/Routinen/` sind **automatisch** eine Routine:
  `Agenten/Bus/tests/test_anbindung_routinen.py` nimmt jede `*.ps1` (außer
  `einmalig-*`, `*-hook.ps1`, `bus.ps1` und Dateien mit Marker `BUS: Bibliothek`).
  Ohne Bus-Anbindung wird die Suite rot.
- Zeile in `MaxHirn/Wissen/Routinen.md` ergänzen: Format
  `| <Wann> | <Was> | <Skript> | **eingeplant** <Datum> — \`<Aufgabenname>\` |`.
  **„eingeplant“ erst, wenn die Aufgabe existiert UND einmal gelaufen ist** —
  bis dahin „vorbereitet“ mit dem Registrierungsbefehl daneben.
- Commit nur auf benannten Pfaden (`Agenten/Routinen/<name>.ps1`,
  `MaxHirn/Wissen/Routinen.md`, ggf. Tests). Fremde Änderungen im Baum nicht
  mitnehmen. Details: `brainfiles-auftrag`.
- Die Übergabedatei in `Werkstatt/` ist **nicht** im Git (Regel 4) — sie ist
  Durchgangsware. Was bleiben soll, in den Vault.

### 8. Sitzungen abschließen

Erledigte Sitzungen **archivieren**, nie löschen — `archive` ist weiches Verstecken
(umkehrbar, kein Datenverlust), `prune` löscht endgültig. Immer zuerst trockenlaufen.
Der vollständige Abschluss-Ablauf (drei Zustandsachsen, was „erledigt“ heißt,
Befehlssatz, Fallen) steht in `references/sitzungen-schliessen.md` (laden mit
`skill_view`). Zwei lesende Skripte decken den Bestand ab: `offene_sitzungen.py`
(offen) und `beendete_sitzungen.py` (beendet, noch nicht archiviert — die
natürlichen Abschluss-Kandidaten):

```bash
python Agenten/Hermes/skills/brainfiles/sammelauftrag/scripts/beendete_sitzungen.py
```

Dann der Abschluss selbst — **zuerst die Altersverteilung der Kandidaten messen,
nie einen festen Wert raten**: `--older-than` filtert auf der LETZTEN AKTIVITAET
(`last_activity_at`, der Trockenlauf nennt es im Kopf: "last active before …"),
nicht auf `ended_at`, und ein einzelnes Alter kann leer treffen, waehrend ein
juengeres greift (gemessen: 130 beendet+unarchiviert, davon 0 aelter als 30 d;
`--older-than 30d`/`7d`/`14d` alle "No sessions match", `--older-than 2d` traf 18).
Die Buckets liefert ein lesender SQL-Lauf (Zeitstempel sind gemischt REAL-Epoch
ODER ISO — beide Formen behandeln):

```bash
python - <<'EOF'
import sqlite3, datetime
from collections import Counter
db = sqlite3.connect(r"file:Agenten/Hermes/state.db?mode=ro", uri=True)
now = datetime.datetime.now(datetime.timezone.utc)
def alter(ts):
    if isinstance(ts, (int, float)):
        dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
    else:
        dt = datetime.datetime.fromisoformat(str(ts).replace('Z', '+00:00'))
    return (now - dt).days
rows = db.execute("SELECT ended_at, source FROM sessions WHERE ended_at IS NOT NULL AND archived = 0").fetchall()
print(Counter(('<1d' if alter(e) < 1 else '1-7d' if alter(e) < 7 else '7-30d' if alter(e) < 30 else '>30d', s) for e, s in rows))
EOF
```

Danach Trockenlauf ZAEHLEN und mit dem Bucket-gerechten Alter wirklich laufen:

```bash
hermes sessions archive --older-than 2d --dry-run | wc -l   # Zahl nennen, nicht ansehen
hermes sessions archive --older-than 2d --yes
```

Vor einem Massen-Abschluss `hermes sessions pinned` lesen und Angeheftete ausnehmen
(`archive`/`prune` schützen sie ohnehin, solange kein `--include-pinned` steht).
Reine Hüllen (0 Nachrichten) sind Kandidaten für `prune --never-active`. Eine
Sitzung mit wiederaufnahmefähigem `end_reason` (`agent_close`, `ws_orphan_reap`,
`startup_orphan_reap`, `superseded_by_resume`) ist verlassen, nicht erledigt —
auch sie nur archivieren. Fremde Sitzungen (Claude/Codex) schließt Hermes nicht;
sie werden nur gelesen oder per `hermes sessions import` einseitig übernommen.

- Nach dem naechtlichen `fremdarbeit-einziehen`-Lauf (20:40) lohnt der Blick auf
  `git log --oneline origin/master..master`: die geplante Aufgabe committet
  lokal, ihr Push kann aber scheitern (403), waehrend derselbe Push von Hand
  funktioniert. Unpushed Commits sind eine Sicherung, die es nicht gibt.

## Pitfalls

- **Den Trockenlauf ZAEHLEN, nicht ansehen.** `archive ... --dry-run` gibt eine
  Zeile je betroffener Sitzung aus; ein Blick auf die letzten Zeilen (z. B.
  `tail`) zeigt nur den Rest. Am 29.09.2026 standen so 7 sichtbare Zeilen fuer
  144 wirkliche Sitzungen — der Ernstlauf versteckte 144 statt der erwarteten 7.
  Vorher `| wc -l` nehmen und die Zahl nennen, sonst ist die Wirkung ungewollt.
  Die Zahl ist eine GROESSE, kein Versprechen: laeuft eine parallele Sitzung,
  kann der Ernstlauf um wenige Sitzungen abweichen (gemessen 89 dry-run / 87
  archived) — Sitzungen werden zwischen den beiden Laeufen beendet oder neu
  angelegt. Abweichung im einstelligen Bereich ist Bewegung, kein Fehler;
  Beleg ist der Zaehler aus `beendete_sitzungen.py` vorher/nachher, nicht die
  Trockenlauf-Zahl.
- **`archive` hat kein Gegenstueck im CLI.** Es gibt `archive`, aber kein
  `unarchive` (`hermes sessions --help`); umkehrbar heisst hier: in `state.db`
  `UPDATE sessions SET archived=0` (Spalte existiert, Tabelle `sessions`).
  Wer 100+ Sitzungen versteckt, muss diesen Rueckweg mitliefern.
- **`archive --older-than AGE` filtert auf der LETZTEN AKTIVITAET, nicht auf
  `ended_at` — und jedes einzelne Alter kann leer treffen.** "No sessions match"
  trotz 100+ beendeter, unarchivierter Sitzungen ist der Normalfall, wenn die
  Auswahl alle juenger sind als der Wert (gemessen: von 130 beendeten 0 aelter
  als 30 d, `--older-than 7d`/`14d`/`30d` leer, `--older-than 2d` traf 18). Der
  Wert gehoert aus den Alters-Buckets der DB gewaehlt (Schritt 8, SQL-Rezept),
  nie aus dem Gedaechtnis; der Bestand kommt aus `beendete_sitzungen.py`,
  nicht aus einem einzelnen Filter.
- **`Wissen/Routinen.md` ist CRLF mit einzelnen LF-Zeilen.** Weder `write_file`
  noch `patch` darauf ansetzen: beide normalisieren die Zeilenenden und erzeugen
  im Diff Änderungen, die niemand gemacht hat. Sicherung `.bak-JJJJMMTT` anlegen,
  die Zeile per kurzem Skript bytes-genau an der Ankerzeile einfügen, danach
  gegenprüfen, dass die Datei **ohne** die neue Zeile byte-identisch zur Sicherung
  ist (Rezept in `bus-integration`).
- **`git status --porcelain` mischt eigene und fremde Arbeit.** Ein uncommitteter
  Stand kann von einer anderen Sitzung stammen (z. B. `Agenten/Hermes/config.yaml`):
  benennen, nicht committen, nicht wegräumen — und im Bericht unter „nicht
  angefasst“ führen.
- **Aufgabenplanung ist nicht Abarbeitung.** Eine Zeile in `Routinen.md` behauptet
  nichts über die Wirklichkeit; der einzige Beleg ist `Get-ScheduledTaskInfo`.
  `LastTaskResult`: `0` = sauber, `267009` (0x41301) = läuft gerade,
  `267014` (0x41306) und `1073807364` (0x40010004) = Prozess von außen beendet
  (typisch für Dauerläufe beim Herunterfahren), `2147946720` (0x800710E0) =
  Aufgabe läuft schon (`IgnoreNew`), `3221225786` (0xC000013A) = abgebrochen.
  Ein `start` ohne `ende` im Journal ist dann kein Befund am Bus. Nur `0` ohne
  `ende` oder ein Fehlercode **mit** `ENDE FEHLER` im eigenen Protokoll ist einer.
  Nicht-`0`-Codes pauschal als Fehler zu melden, erzeugt Fehlalarme: bei einem
  Dauerprozess ist das Beenden durch das System der Normalfall.
- **„Angebunden ist nicht gestartet.“** Eine Routine ohne eigene geplante Aufgabe
  meldet nie: die Anbindung ist da, aber unsichtbar.
- **Ein Einmal-Auftrag als Routine ist falsch.** Wiederkehrend heißt: derselbe
  Auslöser, dieselbe Prüfung, kein Mensch nötig. Sonst läuft er still ins Leere
  oder schreibt jeden Tag dieselbe Meldung.
- **`todo_list` ist sitzungsflüchtig.** Es ordnet die Schritte **dieser** Sitzung
  und stirbt mit ihr — nie als Ablage für einen Auftrag verwenden, der eine
  Sitzung überleben soll.
- **Cron-Aufträge können nicht fragen.** Fehlt im `prompt` der Pfad oder das
  Ziel, tut der Lauf etwas Plausibles statt des Richtigen.
- **Die Feldnamen eines Cron-Auftrags sind `last_run_at`, `next_run_at`,
  `state`, `last_status` — nicht `last_run`.** Ein `job.get("last_run")`
  liefert immer `None` und liest sich wie „nie gelaufen". Genau dieser
  Fehlalarm ist passiert: ein erledigter Auftrag wurde als offen gemeldet,
  obwohl sein Ergebnis seit zwei Tagen in
  `Agenten/Hermes/cron/output/<job_id>_<ts>.txt` lag. Vor einer solchen Meldung
  den Schlüssel im `jobs.json` **nachsehen** (nie aus dem Gedächtnis) und
  `cron/output/` lesen. `scripts/sammeln.py` gibt die Felder seit dem
  15.09.2026 mit aus.
- **Ein Wächter darf nicht über den Weg melden, den er überwacht.** Ein
  Bus-Wächter, der seine Warnung per `Melde-Ende` in den Bus-Journal schreibt,
  schweigt genau dann, wenn der Bus tot ist — der Ausfall vom 11.–15.09.2026
  (vier Tage stumme Meldekette, niemand hat es gesehen) lief so ab. Entweder der
  Wächter sendet über `melder.sende` direkt an Telegram, oder er ist ein
  Hermes-`cronjob` mit `script` + `no_agent` und `deliver`. Prüfen, ob für den
  überwachten Dienst überhaupt ein Wächter existiert: für den Handels-Dauerlauf
  gab es einen, für den Bus nicht.
- **Nichts löschen, was nach Stufe 0 aussieht** (Schlüssel, Dokumente, Bilder,
  unsortierter Posteingang). Löschkandidaten nach
  `Claude/Posteingang/_zu_loeschen/`, dort entscheidet Max.
- **`archive` ist kein Löschen.** Es setzt nur `archived=1` (umkehrbar). `prune`
  löscht endgültig und schützt Archivierte/Angeheftete standardmäßig — nur
  `--include-*` nimmt sie mit. `prune` ohne Filter löscht standardmäßig 90 Tage:
  immer `--dry-run` zuerst.
- **`archive` und `prune` greifen nur auf BEENDETE Sitzungen.** Offene Sitzungen
  (`ended_at IS NULL`) werden stillschweigend uebergangen; `prune` sagt es selbst:
  "N open sessions also match these filters but will be skipped because prune
  only deletes ended sessions". Ein "No sessions match" bei `--older-than 30d`
  ist deshalb KEIN Beweis, dass nichts offen ist - offene Sitzungen koennen
  wochenlang still liegen und bleiben trotzdem unberuehrt (gemessen 18.09.2026:
  46 offene, still seit ueber 24 h, kein Filter greift). Solche Sitzungen sind
  kein Aufraeum-Kandidat, sondern ein Speicherbefund; nur `hermes sessions
  delete <id>` entfernt eine ausdruecklich, und das ist Loeschen, nicht
  Archivieren. Was `archive` wirklich bewegt hat, beweist nur ein Vergleich der
  Zaehler aus `scripts/offene_sitzungen.py` (offen/beendet/archiviert) davor und
  danach.
- **`hermes sessions list` kann nicht nach „offen“ filtern.** Für den Bestand
  offener Sitzungen die DB direkt lesen (`scripts/offene_sitzungen.py`) oder
  `browse`. Jedes Profil hat eine eigene `state.db` — ein Sweep nur der
  Default-DB verpasst die Bot-Sitzungen.
- **Angeheftete Sitzungen sind Keep-Flags.** Vor einem Massen-Abschluss
  `hermes sessions pinned` lesen.
- **Eine Sitzung mit wiederaufnahmefähigem `end_reason` ist nicht erledigt.**
  `agent_close`/`ws_orphan_reap`/`startup_orphan_reap`/`superseded_by_resume`
  holt die Wiederaufnahme zurück — nur archivieren, nie löschen.

## Verification

Drei Kommandos beweisen den Lauf — das erste den Sitzungsbestand, das zweite die
Anbindung, das dritte den Zeitplan. Sitzungsbestand (muss die erwarteten offenen
Sitzungen und Abschluss-Kandidaten zeigen):

```bash
python Agenten/Hermes/skills/brainfiles/sammelauftrag/scripts/offene_sitzungen.py
python Agenten/Hermes/skills/brainfiles/sammelauftrag/scripts/beendete_sitzungen.py
```

Anbindung und Zeitplan:

```bash
cd Agenten/Bus && python tests/test_ende_zu_ende.py     # muss enden mit: Ende-zu-Ende bestanden
```

```bash
powershell -NoProfile -Command "Start-ScheduledTask -TaskName '<Aufgabenname>'; Start-Sleep -Seconds 10; Get-ScheduledTaskInfo -TaskName '<Aufgabenname>' | Select-Object LastRunTime,LastTaskResult | Format-List"
```

Erwartet: `LastTaskResult : 0` und im Protokoll
`Agenten/Routinen/logs/<name>-letzter-lauf.log` die erwartete Verzweigung (nicht
nur „ENDE ok“). Zusätzlich im Bus-Journal ein Paar `start`/`ende` mit
`-Wer 'routine/<name>'`. Bei einem Cron-Auftrag statt dessen
`cronjob action='run'` und die gelieferte Nachricht prüfen.

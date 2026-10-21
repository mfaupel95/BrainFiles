# Claude- und Claude-Code-Sitzungen lesen

Hermes' `state.db` ist NICHT der einzige Sitzungsspeicher. Offene Punkte aus
Claude-Sitzungen findet man an drei Orten; alle lesend, nichts davon schliesst
Hermes (fremde Sitzungen werden nur gelesen oder per `hermes sessions import`
einseitig uebernommen).

## 1. Claude Code CLI-Transkripte (`~/.claude/projects/`)

Ein Ordner JE ARBEITSVERZEICHNIS (cwd), Name = Pfad mit `-` statt `\` und `:`:
`C--Users-faupe-Documents-BrainFiles`, `...-Werkstatt`, `...-Agenten`,
`...-Agenten-Handel-OpenAlice-workspaces-workspaces-<name>` (jedes OpenAlice-
workspace hat einen eigenen). Darin je Sitzung eine `.jsonl`:

```bash
ls -t "$HOME/.claude/projects/C--Users-faupe-Documents-BrainFiles/"*.jsonl | head
```

Zeilen sind JSON-Objekte; die letzten Zeilen der Datei = juengster Stand (in
Claude-Code-Transkripten steht der NEUESTE Eintrag am ENDE, anders als bei
manchen Logs). Lese-Rezept:

```python
rows = [json.loads(l) for l in open(fn, encoding="utf-8", errors="replace")]
# je Zeile: msg = row["message"]; msg["role"] in ("user","assistant")
# msg["content"] ist EIN str ODER eine Liste von dicts mit type=="text"
```

- **User-Auftraege** extrahieren: `content` als str, nicht leer, nicht mit
  "This session is being continued" beginnend (das sind automatische
  Kompaktierungs-Summaries, KEINE Auftraege).
- **Assistent-Texte** (`type=="text"`, len > ~60): die letzten 3–8 zeigen den
  offenen Stand (was lief, was abgelehnt wurde, was wartet).

## 2. Claude Desktop-Sitzungen (MSIX-Container)

Metadaten unter dem Desktop-Profil:
`%LOCALAPPDATA%\Packages\Claude_*\LocalCache\Roaming\Claude\claude-code-sessions\
<profil>\(unterordner)\local_*.json` — je Sitzung eine JSON mit **nur
Metadaten** (title, model, cwd, branch, cliSessionId, isArchived,
lastActivityAt). Das TRANSCRIPT liegt nicht hier, sondern unter
`~/.claude/projects/<encoded-cwd>/<cliSessionId>.jsonl` — also Titel + cwd aus
`local_*.json`, Inhalt aus dem zugehoerigen Projekt-JSONL. Nach `title` und
`cwd` sortieren, nicht nach Dateinamen.

## 3. Der Arbeitsbaum (Git) und Uebergaben

Eine Claude-Sitzung, die am Session-Limit oder beim Schliessen abbrach, hinterlaesst
ihre offene Arbeit im Baum:

```bash
git worktree list                                   # Offene Worktrees + Zweige
for b in <zweig>; do git log --oneline master..$b; done   # ungemergte Commits
ls -t Werkstatt/Austausch/                           # HANDOVER-*.md je Sitzung
```

`HANDOVER-<datum>.md` in `Werkstatt/Austausch/` traegt einen Abschnitt
"Open Questions" und "Next Steps" — die offiziellen offenen Punkte einer
abgeschlossenen Claude-Sitzung. Zusaetzlich `MaxHirn/Archiv/TASKS.md` gegen den
Bericht halten, wenn Punkte bereits als T-Nr. erfasst sind.

## Signale, die einen OFFENEN Punkt bedeuten

- Letzte Assistenten-Zeile enthaelt **"You've hit your session limit"** (Reset
  ~2:30 Europe/Berlin): die Sitzung wurde MITTLENIG abgebrochen, ihre letzte
  Arbeit (Backtest, Merge, Junction-Versuch) ist unfertig — Kandidat.
- Assistent schreibt "ich konnte nicht / wurde abgelehnt / ich umgehe diese
  Sperre nicht": die Ursache ist der offene Punkt, nicht die Meldung.
- Ein gemeldeter Backtest/Messlauf ohne Ergebnis-Zeile danach: lief noch oder
  wurde nie ausgewertet — im Bericht als "laufend/unbestätigt" führen, nicht als
  fertig.

## Pitfalls

- **Die Desktop-JSON ist kein Transcript.** In `local_*.json` nach
  `message`-Strukturen zu suchen, liefert nichts — Transcript kommt immer aus
  dem Projekt-JSONL ueber die `cliSessionId`.
- **Neueste Sitzung != neuester Stand:** `ls -t` nach mtime ist ok, aber die
  Desktop-App schreibt `local_*.json` auch bei Fokus-Wechsel neu
  (`lastFocusedAt`) — zuerst nach `lastActivityAt` im JSON sortieren, dann
  Titel/cwd pruefen.
- **Ein leerer `.jsonl`-Projektordner ist eine frisch geoeffnete, nie benutzte
  Sitzung** (0 Zeilen) — kein offener Punkt.
- Claude-Sitzungen arbeiten oft aus `Werkstatt/` oder OpenAlice-Workspaces,
  nicht aus der Repo-Wurzel — der Projektordner heisst dann anders. Vor der
  Suche `ls ~/.claude/projects/` und die juengsten mtimes aller Ordner nehmen.
- Der Junction-/Dateisystem-Zustand (z. B. `Werkstatt` wieder ein ECHTER
  Ordner statt Verweis) ist ein Befund, keine Session-Eigenschaft: erst den IST-
  Zustand pruefen (`(Get-Item <pfad> -Force).LinkType`), dann dem Chat glauben.

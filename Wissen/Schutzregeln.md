# Schutzregeln

Welche Dateien in `MaxHirn/` ein Agent **nicht** anfassen darf, und warum.
Angelegt 24.08.2026 nach einer Bestandsaufnahme des gesamten Vaults.

Kurzfassung für den Alltag: **Alles unter `Claude/Dokumente/`, `Claude/Bilder/`,
`Claude/Videos/`, `Claude/Musik/` und `Wissen/` ist Originalgut ohne Zweitquelle.
Dort wird gelesen, nicht geschrieben.**

## Warum das hier steht

Drei Dinge machen diesen Vault empfindlicher als ein normales Projektverzeichnis:

1. **Keine Versionsverwaltung.** `MaxHirn/` ist kein Git-Repository (geprüft
   24.08.2026). Jede Überschreibung ist endgültig — es gibt kein `git checkout`.
   Die vorhandenen `.bak-JJJJMMTT`-Dateien sind Handarbeit und decken nur eine
   Handvoll Dateien ab.
2. **Die Sicherung ist keine Historie.** `sichern.ps1` läuft ohne `/MIR` und
   kopiert nur Neues und Geändertes. Wer eine Datei um 19:00 kaputtschreibt, hat
   um 20:01 auch auf `G:` nur noch die kaputte Fassung. Die Sicherung schützt
   gegen Plattenausfall, **nicht** gegen einen falschen Schreibvorgang.
3. **Das Archiv ist bereits einmal beschädigt worden.** 691 Dateien sind durch
   einen Netzteildefekt zerstört (siehe [[../Claude/BESCHAEDIGTE_DATEIEN|BESCHAEDIGTE_DATEIEN]]).
   Was noch intakt ist, ist der Rest — nicht der Normalzustand.

## Stufe 0 — unersetzlich, nie schreibend anfassen

Kein Agent ändert, verschiebt, benennt um oder löscht hier etwas **ohne dass Max
es in derselben Sitzung ausdrücklich für genau diese Datei angeordnet hat.**
Massenoperationen (Schleife, `--recurse`, Platzhalter) sind hier grundsätzlich
verboten, auch mit Anordnung — erst eine Liste vorlegen, dann einzeln.

| Ort | Warum |
|---|---|
| `Claude/Dokumente/` | Verträge, Bescheide, Gericht, Gesundheit, Behörden. Originale, oft die einzige Fassung. |
| `Claude/Bilder/`, `Claude/Videos/`, `Claude/Musik/` | Rohmedien. 25 GB ohne Zweitquelle; 18,3 % der Bilder sind bereits verloren. |
| `Wissen/` | Der Kopf des Systems. Profil, Fristen, Projekte, Verbindungen. |
| `Wissen/Zugaenge.md` | Einzige Ablage für Schlüssel und Tokens. Nie ausgeben, nie in eine Chat-Antwort, nie in ein Protokoll. |
| `.obsidian/` | Vault-Konfiguration. Kaputt = Obsidian öffnet den Graphen nicht mehr. |
| `Claude/Software/**/*.pfx` | ELSTER-Zertifikate. Zerstört, aber sie **belegen** den Verlust. |
| Alle 0xFF-Platzhalter | Die 61 verbliebenen Nullbyte-PDFs sind der einzige Hinweis darauf, **welche** Dokumente fehlen. Nicht aufräumen. |

### Löschen ist hier nie die Lösung

Ein Agent löscht in Stufe 0 **gar nicht**. Wenn etwas weg soll, wird es nach
`Claude/Posteingang/_zu_loeschen/` verschoben und Max entscheidet. Der Grund ist
dieselbe Erfahrung, die schon in `sort_inbox.py` steckt: eine
Duplikat-Erkennung nach Änderungsdatum hätte in einem einzigen Lauf 1001
gleichnamige, inhaltlich verschiedene Dateien abgeräumt.

## Stufe 1 — Betriebsteile, Änderung nur mit Ansage

Diese Dateien sind ersetzbar, aber wenn sie stillschweigend kaputtgehen, merkt
es niemand — und genau das ist bereits passiert (`sichern.ps1` meldete am
23.08.2026 „ENDE ok", während robocopy mit Code 11 gescheitert war).

**Regel: vor der Änderung `.bak-JJJJMMTT` anlegen, nach der Änderung einmal
ausführen und die Ausgabe zeigen.** Eine Änderung an einem Sicherungsskript
gilt erst als erledigt, wenn ein echter Lauf sie bestätigt hat.

| Ort | Risiko bei stiller Beschädigung |
|---|---|
| `sichern.ps1`, `sichern-zweitkopie.ps1` | Sicherung fällt aus, ohne Fehlermeldung. |
| `Routinen/*.ps1` | Geplante Aufgabe läuft ins Leere; die Aufgabenplanung meldet trotzdem Erfolg. |
| `Claude/ArchivSuche/sort_inbox.py` | Verschiebt und löscht echte Dateien. Höchste Sorgfalt. |
| `Claude/ArchivSuche/index.py`, `vektor_index.py` | Index fällt aus; Suche liefert stillschweigend nichts. |
| `AGENTS.md`, `CLAUDE.md`, `Dashboard.md` | Steuern das Verhalten aller Agenten. |
| `.claude/skills/` | Dasselbe. |
| `MCP-Server/`, `Handel/agent.py`, `Handel/plan.json` | Laufender Betrieb, eigene Zugangsdaten. |
| `Hermes/` | Konfiguration und Gedächtnis des zweiten Agenten. |

## Stufe 2 — reproduzierbar, freie Hand

Hier darf ein Agent ohne Rückfrage arbeiten, weil sich alles neu erzeugen lässt:

- `**/.venv/`, `**/__pycache__/`, `**/node_modules/` — aus `requirements.txt` / `package.json`
- `GitHub/` — geklonte Fremd-Repos, aus Git; ohnehin von der Sicherung ausgenommen
- `Modelle/` (3,9 GB) — neu herunterladbar
- `Claude/ArchivSuche/archiv_index.db`, `vektor_index.db` — `index.py` erzeugt sie neu
- `Routinen/logs/` — jeweils nur der letzte Lauf
- `Claude/Posteingang/` — Durchgangsordner. **Ausnahme:** was dort liegt, ist noch
  nirgends einsortiert und damit ein Original. Vor dem Sortieren gilt Stufe 0.

## Vor jedem schreibenden Zugriff

1. **Stufe bestimmen.** Im Zweifel die höhere annehmen.
2. **Bei Stufe 0 oder 1: erst lesen, dann eine Liste des Geplanten zeigen,
   dann handeln.** Kein „ich habe schon mal angefangen".
3. **Trockenlauf, wo es einen gibt.** `sort_inbox.py --dry-run`,
   `robocopy /L`, `git status` — bevor der echte Lauf startet.
4. **Nach der Änderung prüfen**, nicht auf den Rückgabewert eines Werkzeugs
   vertrauen. Robocopy wirft keine Ausnahme, es meldet über den Exitcode.

## Mehrere Sitzungen gleichzeitig

Max arbeitet mit mehreren Chats parallel, dazu kommt Hermes. Alle schreiben in
denselben Vault. Der Schutz durch Git hat dabei eine genau bestimmbare Lücke:

**Git schützt nur, was committet ist.** Zwischen dem Schreiben einer Datei und
ihrem Commit liegt ein Fenster, in dem die Arbeit nirgends gesichert ist — nicht
in Git, und in der Sicherung um 20:00 steht danach der überschriebene Stand.
Eine zweite Sitzung, die in diesem Fenster verwirft, vernichtet die Arbeit der
ersten endgültig.

Am 24.08.2026 ist das zum ersten Mal aufgefallen, im harmlosen Fall: Eine zweite
Claude-Sitzung fand zwei geänderte Dateien im Arbeitsbaum vor und committete sie
samt Nachricht in der Ich-Form — Arbeit, die sie nicht getan hatte. Verloren ging
nichts. Dasselbe Muster mit `git checkout` statt `git commit` hätte die Arbeit
gelöscht, und zwar ohne Rückholmöglichkeit.

Vier Regeln, für Claude und Hermes gleichermaßen:

1. **Nichts committen, was man nicht selbst geändert hat.** Vor jedem Commit
   `git status` lesen. Dateien namentlich hinzufügen: `git add <pfad>`. **Nie**
   `git add -A`, `git add .` oder `git commit -a` — die nehmen fremde Arbeit
   ungefragt mit. Liegt Fremdes im Arbeitsbaum: liegen lassen und melden.

2. **Nichts verwerfen.** `git reset --hard`, `git checkout -- <datei>`,
   `git restore <datei>`, `git stash`, `git clean` löschen genau das, was Git
   noch nicht schützt. Nur auf ausdrückliche Anweisung in derselben Sitzung —
   und vorher ansagen, welche Dateien es trifft.

3. **Eigenes zügig committen.** Nach jedem abgeschlossenen Arbeitsschritt, nicht
   erst am Sitzungsende. Das ist der einzige Hebel, der das ungeschützte Fenster
   wirklich verkleinert.

4. **Exklusive Läufe nicht doppelt starten.** `index.py`, `sort_inbox.py`,
   `sichern.ps1` und `zweitkopie.ps1` schreiben eine SQLite-Datenbank oder
   verschieben Dateien. Zwei gleichzeitige Läufe blockieren sich oder
   hinterlassen einen halben Stand. Vorher prüfen, ob schon einer läuft.

**Was diese vier Regeln nicht leisten:** Sie verhindern nicht, dass zwei
Sitzungen dieselbe Datei nacheinander überschreiben. Dagegen hilft nur,
verschiedenen Sitzungen verschiedene Bereiche zu geben — oder nachzufragen,
bevor man eine Datei anfasst, an der erkennbar eine andere Sitzung arbeitet.

## Was diese Regeln nicht leisten

- **Alle drei Kopien stecken im selben Rechner.** Original auf Disk 0,
  Sicherung auf `G:` (Disk 2), Zweitkopie auf `O:` (Disk 1). Gegen einen erneuten
  Netzteilschaden — der 2026 schon mehrere Platten gleichzeitig getötet hat —
  hilft das nicht. **Eine Kopie außer Haus ist der wichtigste offene Punkt.**
  Siehe [[Hardware]].
- **Versionsstände seit 24.08.2026.** Ein Git-Repository über die Textebene des
  Vaults schließt die Lücke, die alle drei Kopien teilen: Sie halten nur den
  jetzigen Stand. Erfasst sind 85 Dateien (`Wissen/`, Steuerdateien der Agenten,
  `.claude/skills/`, `ArchivSuche/`, `Handel/`, die drei eigenen MCP-Server,
  die Sicherungsskripte) — **ohne** die 42 GB Medien. Zurückholen einer
  versehentlich überschriebenen Datei: `git restore <pfad>`, geprüft am
  24.08.2026 an `Fristen.md` (bit-genau identisch wiederhergestellt).
  Die `.gitignore` ist eine **Whitelist**: erst alles ignorieren, dann einzeln
  freigeben. `Zugaenge.md`, `Passwoerter-Quarantaene.md`, alle `.env`, `.pem`,
  `.pfx`, `.p12`, `.kdbx` stehen als Rückausnahme draußen und waren nie im
  Verlauf. **Das ist wichtig, denn Git vergisst nichts** — eine einmal
  eingecheckte Schlüsseldatei bleibt auch nach dem Löschen im Verlauf.
  Neue Dateien werden also **nicht automatisch** erfasst; was mitversioniert
  werden soll, braucht eine Freigabezeile in `.gitignore`.
- **`Zugaenge.md` liegt im Klartext** und wird nach `G:` und `O:` mitkopiert.
  Bewusst so, geprüft von `sichern.ps1`. Wer die Platte hat, hat die Schlüssel.

Verwandt: [[Portabilitaet]], [[Hardware]], [[Routinen]]

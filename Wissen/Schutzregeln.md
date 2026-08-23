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

## Was diese Regeln nicht leisten

- **Alle drei Kopien stecken im selben Rechner.** Original auf Disk 0,
  Sicherung auf `G:` (Disk 2), Zweitkopie auf `O:` (Disk 1). Gegen einen erneuten
  Netzteilschaden — der 2026 schon mehrere Platten gleichzeitig getötet hat —
  hilft das nicht. **Eine Kopie außer Haus ist der wichtigste offene Punkt.**
  Siehe [[Hardware]].
- **Keine Versionsstände.** Ein Fehler, der länger als bis 20:00 unbemerkt
  bleibt, ist in allen drei Kopien. Ein Git-Repository über die Textdateien
  des Vaults (`Wissen/`, `*.md`, `*.ps1`, `ArchivSuche/*.py` — ohne die 42 GB
  Medien) würde genau diese Lücke schließen; noch nicht eingerichtet.
- **`Zugaenge.md` liegt im Klartext** und wird nach `G:` und `O:` mitkopiert.
  Bewusst so, geprüft von `sichern.ps1`. Wer die Platte hat, hat die Schlüssel.

Verwandt: [[Portabilitaet]], [[Hardware]], [[Routinen]]

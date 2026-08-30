---
id: 20260830-schutzregeln
title: 'Schutzregeln'
tags: [sicherheit, betrieb]
created: 2026-08-27
updated: 2026-08-28
related: []
summary: 'Welche Dateien in MaxHirn ein Agent nicht anfassen darf und warum.'
---

# Schutzregeln

Welche Dateien in `MaxHirn/` ein Agent **nicht** anfassen darf, und warum.
Angelegt 24.08.2026 nach einer Bestandsaufnahme des gesamten Vaults,
**Hauptregel am 25.08.2026 auf Max' Anweisung gelockert** (siehe unten).

## Hauptregel

**Automatisiert gelöscht und aufgeräumt werden darf überall — ausgenommen sind
nur persönliche Inhalte.** Das sind:

- **Medien:** `Claude/Bilder/`, `Claude/Videos/`, `Claude/Musik/`, samt
  Playlisten (`.m3u`, `.m3u8`, `.pls`)
- **Dokumente:** `Claude/Dokumente/`
- **Noch nicht Einsortiertes** in `Claude/Posteingang/`
- **Schlüssel und Zertifikate** (`Zugaenge.md`, `.env`, `.pem`, `.pfx`, `.p12`,
  `.kdbx`, `.key`, `.ovpn`)

Alles andere — Caches, Indizes, Protokolle, geklonte Repos, Build-Reste,
Duplikate, Modelle, Notizen unter `Wissen/` — darf ein Agent ohne Rückfrage
löschen, verschieben und umbenennen, auch als Massenoperation.

**Was sich am 25.08.2026 geändert hat und warum:** Vorher stand `Wissen/` mit in
der höchsten Schutzstufe, und Massenoperationen waren im ganzen Vault
untersagt. Das hat nicht die Originale geschützt, sondern das Arbeiten und
Aufräumen ausgebremst — jede Notizänderung und jedes Aufräumen von
reproduzierbarem Ballast brauchte eine Rückfrage. Die Sperre gilt jetzt dort,
wo ein Verlust endgültig ist, und nur dort. Wer diesen Absatz liest und die
alte, weitere Fassung „wiederherstellen" will: Das war kein Versehen.

## Warum es die Sperre überhaupt gibt

Zwei Dinge machen die geschützten Ordner empfindlicher als ein normales
Projektverzeichnis:

1. **Sie sind nicht in Git.** Git versioniert seit dem 24.08.2026 die Textebene
   des Vaults (Notizen, Skills, Skripte, Konfiguration) — die 42 GB Medien und
   Dokumente sind durch die Whitelist in `.gitignore` bewusst ausgenommen. Für
   sie gibt es kein `git restore`; für `Wissen/` gibt es das sehr wohl, und
   genau deshalb steht `Wissen/` nicht mehr unter der Sperre.
2. **Die Sicherung ist keine Historie.** `sichern.ps1` läuft ohne `/MIR` und
   kopiert nur Neues und Geändertes. Wer eine Datei um 19:00 kaputtschreibt, hat
   um 20:01 auch auf `G:` nur noch die kaputte Fassung. Die Sicherung schützt
   gegen Plattenausfall, **nicht** gegen einen falschen Schreibvorgang.

Dazu kommt: **Das Archiv ist bereits einmal beschädigt worden.** 691 Dateien
sind durch einen Netzteildefekt zerstört (siehe
[[../Claude/BESCHAEDIGTE_DATEIEN|BESCHAEDIGTE_DATEIEN]]). Was noch intakt ist,
ist der Rest — nicht der Normalzustand.

## Stufe 0 — unersetzlich, nie automatisiert löschen

Kein Agent löscht, überschreibt, verschiebt oder benennt hier um **ohne dass Max
es in derselben Sitzung ausdrücklich für genau diese Datei angeordnet hat.**
Massenoperationen (Schleife, `--recurse`, Platzhalter) sind hier grundsätzlich
verboten, auch mit Anordnung — erst eine Liste vorlegen, dann einzeln.

| Ort | Warum |
|---|---|
| `Claude/Dokumente/` | Verträge, Bescheide, Gericht, Gesundheit, Behörden. Originale, oft die einzige Fassung. |
| `Claude/Bilder/`, `Claude/Videos/`, `Claude/Musik/` und Playlisten | Rohmedien. 25 GB ohne Zweitquelle; 18,3 % der Bilder sind bereits verloren. |
| `Claude/Posteingang/` | Durchgangsordner — was dort liegt, ist noch nirgends einsortiert und damit ein Original. Erst sortieren, dann gilt der Zielordner. |
| `Wissen/Zugaenge.md` | Einzige Ablage für Schlüssel und Tokens, bewusst außerhalb von Git. Nie ausgeben, nie in eine Chat-Antwort, nie in ein Protokoll — und nie löschen. |
| `**/*.env`, `.pem`, `.pfx`, `.p12`, `.kdbx`, `.key`, `.ovpn` | Zugangsdaten, an der Endung erkennbar, nicht am Namen. Auch `Claude/Software/**/*.pfx`: die ELSTER-Zertifikate sind zerstört, aber sie **belegen** den Verlust. |
| Alle 0xFF-Platzhalter | Die 61 verbliebenen Nullbyte-PDFs sind der einzige Hinweis darauf, **welche** Dokumente fehlen. Nicht aufräumen. |

### Löschen ist hier nie die Lösung

Ein Agent löscht in Stufe 0 **gar nicht**. Wenn etwas weg soll, wird es nach
`Claude/Posteingang/_zu_loeschen/` verschoben und Max entscheidet. Der Grund ist
dieselbe Erfahrung, die schon in `sort_inbox.py` steckt: eine
Duplikat-Erkennung nach Änderungsdatum hätte in einem einzigen Lauf 1001
gleichnamige, inhaltlich verschiedene Dateien abgeräumt.

## Stufe 1 — Betriebsteile, Änderung nur mit Ansage

Hier geht es **nicht** um die Löschsperre, sondern um stille Beschädigung:
Diese Dateien sind ersetzbar, aber wenn sie kaputtgehen, merkt es niemand — und
genau das ist bereits passiert (`sichern.ps1` meldete am 23.08.2026 „ENDE ok",
während robocopy mit Code 11 gescheitert war).

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
| `.obsidian/` | Vault-Konfiguration. Kaputt = Obsidian öffnet den Graphen nicht mehr. |
| `MCP-Server/`, `Handel/agent.py`, `Handel/plan.json` | Laufender Betrieb, eigene Zugangsdaten. |
| `Hermes/` | Konfiguration und Gedächtnis des zweiten Agenten. |

## Stufe 2 — freie Hand, auch beim Löschen

**Alles, was nicht in Stufe 0 oder 1 steht.** Ein Agent räumt hier ohne
Rückfrage auf, auch in Massenoperationen. Häufige Fälle:

- `Wissen/` — Notizen, Profil, Fristen, Projekte. Seit 24.08.2026 in Git:
  `git restore <pfad>` holt einen Fehlgriff zurück, geprüft an `Fristen.md`.
  **Ausnahme:** `Zugaenge.md` steht in Stufe 0 und ist nicht in Git.
- `**/.venv/`, `**/__pycache__/`, `**/node_modules/` — aus `requirements.txt` / `package.json`
- `GitHub/` — geklonte Fremd-Repos, aus Git; ohnehin von der Sicherung ausgenommen
- `Modelle/` (3,9 GB) — neu herunterladbar
- `Claude/ArchivSuche/archiv_index.db`, `vektor_index.db` — `index.py` erzeugt sie neu
- `Routinen/logs/` — jeweils nur der letzte Lauf
- Build-Reste (`.pyc`, `.pyo`, `.toc`, `build/`, `dist/`), Temporärdateien, Duplikate

Der einzige Vorbehalt: **vor dem Löschen kurz hinsehen.** Name und Größe allein
sind bei Containerformaten (`.vob`, `.iso`, `.img`) kein Duplikatbeweis — dort
per Hash gegenprüfen.

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

Genau diese Unterscheidung trägt Regel 1 seit dem 27.08.2026: Falsch war an dem
Vorfall nur die **Ich-Form**, nicht das Sichern. Der Commit selbst war das
Richtige — er hat fremde Arbeit aus dem ungeschützten Fenster geholt.

Vier Regeln, für Claude und Hermes gleichermaßen:

1. **Verwerfen ist verboten, Sichern ist Pflicht.** Vor jedem Commit
   `git status` lesen. Fremde Änderungen im Arbeitsbaum werden **nicht liegen
   gelassen**, sondern in einem **eigenen, getrennten Commit** gesichert — nie
   vermischt mit eigener Arbeit im selben Commit. Dateien namentlich
   hinzufügen: `git add <pfad>`. **Nie** `git add -A`, `git add .` oder
   `git commit -a` — nicht wegen der fremden Arbeit, sondern weil sie beide
   Sorten zusammenwerfen.

   Die Herkunft steht im Autorenfeld, nicht nur in der Nachricht:

   ```
   git commit --author="Hermes <hermes@local>" -m "…"
   ```

   Damit lügt auch `git log --author` nicht, und `git log --author=Hermes`
   zeigt jederzeit, was nicht aus einer Claude-Sitzung stammt. Lässt sich der
   Urheber nicht feststellen — der Regelfall, denn eine Änderung im
   Arbeitsbaum trägt keinen Namen —, gilt
   `--author="Andere Sitzung <fremd@local>"`. Nicht raten: „Hermes" ins
   Autorenfeld zu schreiben, weil es plausibel klingt, macht die Historie
   genauso falsch wie die Ich-Form.

   **Ausnahme:** Eine Datei, deren Änderungszeit weniger als **10 Minuten**
   zurückliegt, ruht möglicherweise nicht — dort kann eine andere Sitzung
   mitten im Arbeitsschritt sein. Solche Dateien liegen lassen und melden.
   Die Schwelle ist bewusst eine Zahl und kein Ermessen, sonst entscheidet
   jede Sitzung anders; geprüft wird mit `(Get-Item <pfad>).LastWriteTime`.
   Der Schaden wäre allerdings nur ein unschöner Zwischenstand in der
   Historie, kein Datenverlust: ein Commit löscht nichts.

   **Warum die Regel am 27.08.2026 gedreht wurde** — sie lautete vorher
   „nichts committen, was man nicht selbst geändert hat". Das schützte nichts
   und schadete: Ein Commit fremder Arbeit ist zurücknehmbar — solange er die
   Spitze ist mit `git reset --soft HEAD~1`, sonst mit `git revert` —, der
   einzige Schaden war eine Nachricht in falscher Ich-Form. Unumkehrbar ist
   allein das Verwerfen — dafür gibt es Regel 2.
   Die alte Fassung ließ fremde Arbeit dagegen unbegrenzt in dem
   ungeschützten Fenster liegen, das Regel 3 gerade verkleinern soll. Bei
   Hermes ist das kein Sonderfall: **Hermes committet nie selbst** (geprüft
   27.08.2026, alle 30 Commits der Historie tragen denselben Autor). Seine
   Arbeit ist nur versioniert, wenn eine Claude-Sitzung sie mitnimmt —
   die Notiz [[Hermes]] lag deshalb einen ganzen Tag ungeschützt im Arbeitsbaum.
   Zweiter Blocker: Steht in einer Datei schon Fremdes uncommittet, lässt
   sich der eigene Anteil gar nicht isoliert committen — Regel 1 und Regel 3
   waren dann gleichzeitig unerfüllbar.

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

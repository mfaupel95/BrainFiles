---
id: 20260830-schutzregeln
title: 'Schutzregeln'
tags: [sicherheit, betrieb]
created: 2026-08-27
updated: 2026-09-29
related: [20260902-handelsregeln]
summary: 'Welche Dateien unter BrainFiles ein Agent nicht anfassen darf und warum.'
---

# Schutzregeln

Welche Dateien unter `BrainFiles/` ein Agent **nicht** anfassen darf, und warum.
**Seit dem 30.08.2026 gilt das über vier Ordner** — `MaxHirn/`, `Modelle/`,
`Agenten/`, `Werkstatt/`; die Aufteilung steht in [[Ordnerstruktur]].
Angelegt 24.08.2026 nach einer Bestandsaufnahme des gesamten Vaults,
**Hauptregel am 25.08.2026 auf Max' Anweisung gelockert**, **Handverbot am
01.09.2026 ersetzt: automatischer Handel ist erlaubt, solange die Grenzen in
den beiden `wachen.json` eingehalten werden**, **Notizen unter `Wissen/` am
01.09.2026 wieder geschützt: kein Löschen durch den Agenten, Änderung nur im
Rahmen des Bestehenden**, **Kraken am 02.09.2026 geteilt: der MCP-Server bleibt
lesend, gehandelt wird dort nur durch die bewachte dritte Spur** — alles siehe
unten.

## Hauptregel

**Automatisiert gelöscht und aufgeräumt werden darf überall — ausgenommen sind
nur persönliche Inhalte und die Notizen unter `Wissen/`.** Persönliche Inhalte
sind:

- **Medien:** `Archiv/Bilder/`, `Archiv/Videos/`, `Archiv/Musik/`, samt
  Playlisten (`.m3u`, `.m3u8`, `.pls`)
- **Dokumente:** `Archiv/Dokumente/`
- **Noch nicht Einsortiertes** in `Archiv/Posteingang/`
- **Schlüssel und Zertifikate** (`Zugaenge.md`, `.env`, `.pem`, `.pfx`, `.p12`,
  `.kdbx`, `.key`, `.ovpn`)

Alles andere — Caches, Indizes, Protokolle, geklonte Repos, Build-Reste,
Duplikate, Modelle — darf ein Agent ohne Rückfrage löschen, verschieben und
umbenennen, auch als Massenoperation. Für die **Notizen unter `Wissen/`** gilt
die eigene, mildere Regel im Abschnitt *Notizen unter `Wissen/`* weiter unten.

**Was sich am 25.08.2026 geändert hat und warum:** Vorher stand `Wissen/` mit in
der höchsten Schutzstufe, und Massenoperationen waren im ganzen Vault
untersagt. Das hat nicht die Originale geschützt, sondern das Aufräumen von
reproduzierbarem Ballast ausgebremst — jeder Cache und jedes alte Protokoll
brauchte eine Rückfrage. Für Caches, Indizes, Protokolle, geklonte Repos,
Build-Reste, Duplikate und Modelle bleibt es bei dieser Lockerung: Die Sperre
gilt dort, wo ein Verlust endgültig ist, und nur dort.

**Was am 01.09.2026 zurückgenommen wurde und warum:** Die Lockerung von 25.08.
hatte die **Notizen unter `Wissen/`** mitgenommen — ein Agent durfte sie ohne
Rückfrage löschen, verschieben, umbenennen, auch als Massenoperation. Auf Max'
Anweisung sind sie wieder geschützt. `git restore` holt einen Fehlgriff nur
zurück, wenn er auffällt und die Datei zuvor committet war; eine gelöschte oder
umgeschriebene Notiz im ungeschützten Fenster zwischen zwei Commits (siehe
*Mehrere Sitzungen gleichzeitig*) ist weg. Und der Wert einer Notiz steckt im
gewachsenen Text samt seinen Querverweisen — den baut kein `git restore` wieder
auf, wenn eine Sitzung ihn „aufgeräumt" hat.

### Notizen unter `Wissen/`

Gilt für alle `.md`-Dateien unter `Wissen/`. Ausgenommen bleibt `Zugaenge.md`
(Stufe 0, siehe unten); `Passwoerter-Quarantaene.md` wird wie eine Zugangsdatei
behandelt und nicht ohne Anweisung angefasst.

- **Ein Agent löscht keine Notiz.** Nicht von sich aus, nie als
  Massenoperation. Soll eine wirklich weg, ordnet Max das in derselben Sitzung
  für genau diese Datei an.
- **Geändert wird im Rahmen des Bestehenden:** ergänzen, präzisieren, einen
  Abschnitt überarbeiten, `updated` im Frontmatter hochsetzen. Das braucht
  keine Rückfrage, solange die neue Erkenntnis zum Kontext der Notiz passt und
  ihn weiterträgt.
- **Widerspricht die Änderung dem, was dort steht** — eine Aussage umkehren,
  einen ganzen Abschnitt streichen, eine belegte Zahl gegen eine andere
  tauschen, das Thema der Notiz verschieben —, **wird erst zurückgefragt.**
- **Umbenennen** bleibt erlaubt, wenn die `id` im Frontmatter gleich bleibt und
  die Registry in [[INDEX]] im selben Arbeitsschritt nachgezogen wird — so
  ohnehin schon in [[INDEX]] geregelt.

## Handel: was ein Agent selbst auslösen darf

**Steht seit dem 02.09.2026 in einer eigenen Notiz: [[Handelsregeln]].** Der
Abschnitt war auf rund die Hälfte dieses Dokuments angewachsen — Spuren,
Prüfpflicht, Hebel, Funding, fünf Freigabebedingungen. Dieses Dokument wird vor
jedem schreibenden Zugriff gelesen; was dabei nicht gebraucht wird, macht es
unbrauchbar.

Das Nötigste in drei Sätzen: Automatischer Handel ist erlaubt, aber nur in den
drei Spuren mit eigener `wachen.json` (Marktscanner und XPERP auf OKX, seit
02.09.2026 dazu Kraken in EUR) — die Datei ist die einzige Wahrheit über die
Grenzen. Der **Kraken-MCP** bleibt davon unberührt und lesend:
`kraken_order_aufgeben` und `kraken_order_stornieren` sind gesperrt, auch mit
Bestätigung im Chat, weil eine Sitzung keine Wachen mitbringt — auf Kraken
handelt nur das Skript der Spur 3. Auszahlungsrechte hat kein Schlüssel, und jede
Geldbewegung außerhalb dieser Spuren bleibt vorbereitend — der Skill `geld`
arbeitet bis zur Bestätigungsseite und hält dort an.

## Warum es die Sperre überhaupt gibt

Zwei Dinge machen die geschützten Ordner empfindlicher als ein normales
Projektverzeichnis:

1. **Sie sind nicht in Git.** Git versioniert seit dem 24.08.2026 die Textebene
   des Vaults (Notizen, Skills, Skripte, Konfiguration) — die 42 GB Medien und
   Dokumente sind durch die Whitelist in `.gitignore` bewusst ausgenommen. Für
   sie gibt es kein `git restore`. Für `Wissen/` gibt es das sehr wohl; deshalb
   ist die Regel für Notizen milder als Stufe 0 — kein Listenzwang, Rückfrage
   nur beim Widerspruch —, aber seit 01.09.2026 nicht mehr aufgehoben:
   `git restore` hilft nur bei einer committeten Fassung und nur, wenn der
   Fehlgriff überhaupt auffällt.
2. **Die Sicherung ist keine Historie.** `sichern.ps1` läuft ohne `/MIR` und
   kopiert nur Neues und Geändertes. Wer eine Datei um 19:00 kaputtschreibt, hat
   um 20:01 auch auf `G:` nur noch die kaputte Fassung. Die Sicherung schützt
   gegen Plattenausfall, **nicht** gegen einen falschen Schreibvorgang.

Dazu kommt: **Das Archiv ist bereits einmal beschädigt worden.** 691 Dateien
sind durch einen Netzteildefekt zerstört (siehe
[[../Archiv/BESCHAEDIGTE_DATEIEN|BESCHAEDIGTE_DATEIEN]]). Was noch intakt ist,
ist der Rest — nicht der Normalzustand.

## Stufe 0 — unersetzlich, nie automatisiert löschen

Kein Agent löscht, überschreibt, verschiebt oder benennt hier um **ohne dass Max
es in derselben Sitzung ausdrücklich für genau diese Datei angeordnet hat.**
Massenoperationen (Schleife, `--recurse`, Platzhalter) sind hier grundsätzlich
verboten, auch mit Anordnung — erst eine Liste vorlegen, dann einzeln.

| Ort | Warum |
|---|---|
| `Archiv/Dokumente/` | Verträge, Bescheide, Gericht, Gesundheit, Behörden. Originale, oft die einzige Fassung. |
| `Archiv/Bilder/`, `Archiv/Videos/`, `Archiv/Musik/` und Playlisten | Rohmedien. 25 GB ohne Zweitquelle; 18,3 % der Bilder sind bereits verloren. |
| `Archiv/Posteingang/` | Durchgangsordner — was dort liegt, ist noch nirgends einsortiert und damit ein Original. Erst sortieren, dann gilt der Zielordner. |
| `Wissen/Zugaenge.md` | Einzige Ablage für Schlüssel und Tokens, bewusst außerhalb von Git. Nie ausgeben, nie in eine Chat-Antwort, nie in ein Protokoll — und nie löschen. |
| `**/*.env`, `.pem`, `.pfx`, `.p12`, `.kdbx`, `.key`, `.ovpn` | Zugangsdaten, an der Endung erkennbar, nicht am Namen. Auch `Archiv/Software/**/*.pfx`: die ELSTER-Zertifikate sind zerstört, aber sie **belegen** den Verlust. |
| Alle 0xFF-Platzhalter | Die 61 verbliebenen Nullbyte-PDFs sind der einzige Hinweis darauf, **welche** Dokumente fehlen. Nicht aufräumen. |

### Löschen ist hier nie die Lösung

Ein Agent löscht in Stufe 0 **gar nicht**. Wenn etwas weg soll, wird es nach
`Archiv/Posteingang/_zu_loeschen/` verschoben und Max entscheidet. Der Grund ist
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
| `Agenten/sichern.ps1`, `Agenten/sichern-zweitkopie.ps1` | Sicherung fällt aus, ohne Fehlermeldung. |
| `Agenten/Routinen/*.ps1` | Geplante Aufgabe läuft ins Leere; die Aufgabenplanung meldet trotzdem Erfolg. |
| `Archiv/ArchivSuche/sort_inbox.py` | Verschiebt und löscht echte Dateien. Höchste Sorgfalt. |
| `Archiv/ArchivSuche/index.py`, `vektor_index.py` | Index fällt aus; Suche liefert stillschweigend nichts. |
| `AGENTS.md`, `CLAUDE.md` (in der Wurzel **und** in `MaxHirn/`), `Dashboard.md` | Steuern das Verhalten aller Agenten. |
| `.claude/skills/` | Dasselbe. |
| `.obsidian/` | Vault-Konfiguration. Kaputt = Obsidian öffnet den Graphen nicht mehr. |
| `Agenten/MCP-Server/`, `Agenten/Handel/agent.py`, `Agenten/Handel/plan.json` | Laufender Betrieb, eigene Zugangsdaten. |
| `Agenten/Hermes/` | Konfiguration und Gedächtnis des zweiten Agenten. |

## Stufe 2 — freie Hand, auch beim Löschen

**Alles, was nicht in Stufe 0 oder 1 steht.** Ein Agent räumt hier ohne
Rückfrage auf, auch in Massenoperationen. Häufige Fälle:

- `Wissen/`-Notizen sind seit 01.09.2026 **nicht mehr Stufe 2** — für sie gilt
  der Abschnitt *Notizen unter `Wissen/`* oben: kein Löschen durch den Agenten,
  Änderung nur im Rahmen des Bestehenden, bei Widerspruch erst zurückfragen.
  `git restore <pfad>` holt einen committeten Fehlgriff weiterhin zurück
  (geprüft an `Fristen.md`). **`Zugaenge.md`** steht in Stufe 0 und ist nicht in
  Git; `Passwoerter-Quarantaene.md` wird wie eine Zugangsdatei behandelt.
- `**/.venv/`, `**/__pycache__/`, `**/node_modules/` — aus `requirements.txt` / `package.json`
- `Werkstatt/` — Übergaben, Sitzungsreste, geklonte Fremd-Repos (seit
  14.10.2026 direkt in `Werkstatt/`, nicht mehr unter `Werkstatt/Repos/`).
  Durchgangsware, aus der Sicherung ausgenommen, eigene Spielregeln in
  `Werkstatt/AGENTS.md`
- `Modelle/` (51 GB, seit 30.08.2026 außerhalb des Vaults) — neu herunterladbar.
  **Achtung: `BrainFiles/Modelle` ist kein Ordner, sondern eine Junction auf
  `O:\Modelle`** — und auf `O:` liegt auch die Zweitkopie. Ein rekursives Löschen
  „im Ordner `Modelle/`" verlässt damit den Vault, und je nach Werkzeug folgt es
  der Junction oder entfernt sie. Vor einer Massenoperation dort prüfen, worauf
  man wirklich steht: `(Get-Item Modelle -Force).Target`.
- **Seit 07.09.2026: die Archivdaten `{Bilder,Dokumente,Musik,Videos,Software,
  Posteingang}` liegen ganz auf `O:\Archiv\…`** (echter Umzug, siehe
  [[Ordnerstruktur]]). Keine Junction mehr im Vault — unter
  `MaxHirn\Archiv\` stehen nur noch `ArchivSuche/` und die Steuerdateien auf
  `C:`. Die Werkzeuge finden die Daten über `ARCHIV_ROOT` (`O:\Archiv`). Der
  Inhalt bleibt **Stufe 0** — der physische Ort ändert die Schutzstufe nicht.
  `O:` trägt auch die Modelle-Zweitkopie; vor einer Massenoperation dort prüfen,
  worauf man wirklich steht.
- `Archiv/ArchivSuche/archiv_index.db`, `vektor_index.db` — `index.py` erzeugt sie neu
- `Agenten/Routinen/**/logs/` — jeweils nur der letzte Lauf
- Build-Reste (`.pyc`, `.pyo`, `.toc`, `build/`, `dist/`), Temporärdateien, Duplikate

Der einzige Vorbehalt: **vor dem Löschen kurz hinsehen.** Name und Größe allein
sind bei Containerformaten (`.vob`, `.iso`, `.img`) kein Duplikatbeweis — dort
per Hash gegenprüfen.

## Vor jedem schreibenden Zugriff

**Die Stufe hängt am Inhalt, nicht am Pfadanfang.** Derselbe Text liegt an
mehreren Stellen: in einem Worktree unter `Werkstatt/Worktrees/<zweig>/`, in
einer Sicherung auf `G:` oder `O:`. Nach dem Wortlaut von Stufe 2 wäre eine
Notiz unter `Werkstatt/Worktrees/PC/MaxHirn/Wissen/` freigegeben — sie ist es
nicht. Ein Worktree ist derselbe Vault mit einem anderen Zweig davor; es gilt
die Stufe, die für das Original gälte. Frei ist in `Werkstatt/` nur, was dort
entstanden ist.

1. **Stufe bestimmen.** Im Zweifel die höhere annehmen.
2. **Bei Stufe 0 oder 1: erst lesen, dann eine Liste des Geplanten zeigen,
   dann handeln.** Kein „ich habe schon mal angefangen". **Bei einer Notiz
   unter `Wissen/`:** ergänzen ohne Rückfrage, aber sobald die Änderung dem
   Bestehenden widerspricht, erst zurückfragen (Abschnitt *Notizen unter
   `Wissen/`*).
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

   **Was die Schwelle nicht leistet:** Sie misst, wann zuletzt geschrieben
   wurde — nicht, ob gleich wieder geschrieben wird. Eine Sitzung, die vor
   einer halben Stunde eine Datei angelegt hat und jetzt darauf zurückkommt,
   ist damit nicht geschützt. Die zehn Minuten verkleinern das Fenster, sie
   schließen es nicht; der tragende Schutz bleibt Regel 1 — sichern statt
   verwerfen.

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

**Getrennte Arbeitsbäume statt getrennter Disziplin** (29.09.2026). Für
`Agenten/Handel` ist genau das eingerichtet: Codearbeit läuft dort in einem
eigenen `git worktree`, der Hauptbaum bleibt dem Betrieb vorbehalten. Ein
Worktree hat eigenen Index und eigenen HEAD — die Lücke, die die vier Regeln
oben nur verkleinern, ist dort geschlossen, weil es nichts Fremdes mehr zu
treffen gibt. Für jeden Commit im Hauptbaum gelten sie unverändert weiter.
Einzelheiten in `Agenten/Handel/AGENTS.md`, Abschnitt *Ein Arbeitsbaum je
Aufgabe*.

Anlass war eine Sitzung am 28./29.09.2026, die `master` dreimal unter sich
weiterwandern sah, zwei rote Tests aus fremden Commits zugerechnet bekam und
ihren Arbeitszweig mitten im Testlauf an einen Merge von außen verlor.

## Was diese Regeln nicht leisten

- **Alle drei Kopien stecken im selben Rechner.** Original auf Disk 0,
  Sicherung auf `G:` (Disk 2), Zweitkopie auf `O:` (Disk 1). Gegen einen erneuten
  Netzteilschaden — der 2026 schon mehrere Platten gleichzeitig getötet hat —
  hilft das nicht. **Eine Kopie außer Haus ist der wichtigste offene Punkt.**
  Siehe [[Hardware]].
- **Versionsstände seit 24.08.2026.** Ein Git-Repository über die Textebene des
  Vaults schließt die Lücke, die alle drei Kopien teilen: Sie halten nur den
  jetzigen Stand. Erfasst sind 187 Dateien, Stand 02.09.2026 — 95 unter
  `MaxHirn/`, 86 unter `Agenten/`, 6 in der Wurzel und in `Werkstatt/` (`Wissen/`,
  Steuerdateien der Agenten,
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

Verwandt: [[Ordnerstruktur]], [[Portabilitaet]], [[Hardware]], [[KI-Ablagen-im-Benutzerordner]], [[Routinen]]

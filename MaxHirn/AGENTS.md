# KI-Betriebssystem

Dieser Ordner (`MaxHirn/`) ist Obsidian-Vault und Wissensspeicher von Max'
persönlichem KI-Betriebssystem. Alle Pfade hier sind **relativ**, damit das
System später unverändert auf eine externe SSD umziehen kann.

Diese Datei liegt zweimal, als `CLAUDE.md` und als `AGENTS.md`. Gleicher
Inhalt, zwei Namen, weil Claude die eine und Hermes/Codex die andere liest.
**Wer eine ändert, ändert beide.** Geprüft wird das maschinell von
`../Agenten/Routinen/wissen-index-pruefen.ps1`: Die beiden Fassungen müssen
Zeichen für Zeichen gleich sein, sonst meldet die Systemprüfung es am nächsten
Morgen. Am 02.09.2026 waren sie auseinandergelaufen und mussten zusammengeführt
werden.

**Seit dem 30.08.2026 ist `MaxHirn/` nicht mehr die Wurzel.** Sie liegt eine
Ebene höher in `BrainFiles/` und ist in vier Ordner geteilt — die Karte steht in
[../CLAUDE.md](../CLAUDE.md). Die tragende Regel dieser Teilung:

> **In `MaxHirn/` liegt nichts, was startet.** Programme, Server, Routinen und
> Sicherungsskripte wohnen in `../Agenten/`, Modellgewichte in `../Modelle/`,
> gemeinsame Arbeit in `../Werkstatt/`.

Eine bewusste Ausnahme: `Archiv/ArchivSuche/` bleibt hier — der Werkzeugcode ist
git-versioniert, der Index neu baubar. Die Archivdaten selbst liegen seit dem
07.09.2026 ganz auf `O:\Archiv`; die Werkzeuge finden sie über die
Umgebungsvariable `ARCHIV_ROOT` (siehe [Wissen/Ordnerstruktur.md](Wissen/Ordnerstruktur.md)).

## Aufbau

| Modul | Ort | Inhalt |
|---|---|---|
| **Wissen** | `Wissen/` | Wer Max ist, laufende Projekte, Werkzeuge — Einstieg über [Wissen/INDEX.md](Wissen/INDEX.md) |
| **Wiki** | `Wiki/` | Lernspeicher der Agenten: Lehren, Betriebsstand, offene Punkte — Einstieg über [Wiki/INDEX.md](Wiki/INDEX.md) |
| **Archiv** | `Archiv/` | Dateiarchiv mit Volltextsuche (eigene `CLAUDE.md`), 45 GB. **Hieß bis 30.08.2026 „Claude“** |
| **Skills** | `.claude/skills/` | eigene, wiederverwendbare Fähigkeiten |
| **Verbindungen** | `Wissen/Verbindungen.md` | MCP-Server und ihr Anmeldestatus |
| **Zugänge** | `Wissen/Zugaenge.md` | API-Schlüssel und Tokens — **einzige** Ablage |
| **Schutzregeln** | `Wissen/Schutzregeln.md` | was nicht angefasst werden darf — **vor jedem Schreibzugriff lesen**. Seit 06.10.2026 gibt es eine `permissions.deny`-Liste in `.claude/settings.local.json`, die `rm`, `mv`, `Remove-Item`, `git reset --hard`, `git clean`, `robocopy /MIR` und `rsync --delete` blockiert — sowie `Edit`/`Write` in `Archiv/`, `Wissen/`, `Claude/`, `Bilder/`, `Videos/`, `Musik/`, `Dokumente/`, `.obsidian/` und `Read` auf `Zugaenge.md`, `.env`, `.pfx`, `.p12`, `.kdbx`, `id_rsa`, `id_ed25519`, `private.pem`. |
| **Struktur** | `Wissen/Ordnerstruktur.md` | die vier Ordner und die Fallen beim Umzug |
| **Referenz** | `Referenz/` | Fremdmaterial: Anleitungen, Beispiele, Installationspakete |

### Was außerhalb liegt

| Ort | Inhalt | Größe |
|---|---|---|
| `../Agenten/MCP-Server/` | die Serverprogramme — von Claude **und** Hermes gestartet, siehe [Wissen/Verbindungen.md](Wissen/Verbindungen.md) | 1,8 GB |
| `../Agenten/Hermes/` | Daten des zweiten Agenten. Der **Programmcode** liegt unter `C:\Hermes` — siehe [[Hermes]] | 2,0 GB |
| `../Agenten/Handel/` | DCA-Agent (`agent.py`), eigenes `.venv`, eigenes README | 171 MB |
| `../Agenten/Routinen/` | Wrapper für die geplanten Aufgaben, deren Protokolle in `logs/`, dazu die Umzugsskripte in `umzug/` | klein |
| `../Modelle/` | Ollama-Store (`Ollama/Store/`, Ziel von `OLLAMA_MODELS`), Programm unter `Programme/`, dazu HuggingFace, GGUF, Checkpoints | 51 GB |
| `../Werkstatt/` | Übergaben zwischen den Modellen, Projekte, Worktrees, geklonte Fremd-Repos, Sitzungsablagen | 1 GB |

Einstieg für Menschen: [Dashboard.md](Dashboard.md)

## Reihenfolge bei jeder Anfrage

1. **`Wissen/` zuerst — und zwar über [Wissen/INDEX.md](Wissen/INDEX.md).**
   Der Index listet **alle** Notizen mit einem Satz Zweck; daraus gezielt ein
   bis drei Notizen öffnen, statt den Ordner einzulesen. Dort steht der
   persönliche Kontext (Profil, Projekte, Vorlieben) — er beantwortet viele
   Fragen ohne jeden Werkzeugaufruf. Wer eine Notiz anlegt, umbenennt oder
   löscht, zieht die Registry in `INDEX.md` **im selben Arbeitsschritt** nach.
2. **Dann das Archiv.** Geht es um eigene Rechnungen, Verträge, Notizen, Fotos,
   Anleitungen? Dann `archiv`-Skill benutzen, nicht das Internet.
3. **Erst danach Internet** (WebSearch/WebFetch) — für allgemeines Weltwissen.

**Und bei allem, was den Betrieb betrifft** (Hermes, Bus, Handel, Wachen, Werkzeuge):
zuerst [Wiki/INDEX.md](Wiki/INDEX.md). Dort steht, was beim Arbeiten schon einmal Zeit
gekostet hat — die Falle, der Merksatz, der gemessene Stand. Das Wiki gehoert den
Agenten, `Wissen/` gehoert Max.

**Bei jedem Schritt gezielt lesen, nicht vollständig.** Vor einem Datei-Read
zuerst gezielt suchen (`rg` für Projektdateien, `archiv`-Skill für persönliche
Unterlagen) und nur die nötigen Trefferbereiche lesen. Eine ganze Datei nur,
wenn ihre vollständige Struktur für die Aufgabe gebraucht wird.

## Jede Aufgabe wird wiederholbar gemacht

Angeordnet am 28.08.2026: **Aus jedem Anwendungsfall entsteht eine wiederholbare
Aufgabe.** Ziel ist, langfristig alle Operationen lokal ausführen zu können,
ohne dass ein Weg zweimal gesucht werden muss.

Am Ende einer Aufgabe, die ein zweites Mal vorkommen wird, wird also abgelegt —
ungefragt, und die Ablage in einem Satz gemeldet:

| Was dabei herauskam | Wohin |
|---|---|
| ein Verfahren mit Fallen | Skill unter `.claude/skills/` (Skill `skill`) |
| eine Zahl, ein Befund, ein Zustand | Notiz unter `Wissen/` (Skill `notiz`) |
| eine Lehre, ein Merksatz, eine Falle | Wiki-Seite unter `Wiki/` (Skill `wiki-pflege`), `Wiki/INDEX.md` im selben Schritt nachziehen |
| etwas, das ohne Nachdenken laufen soll | Skript in `../Agenten/Routinen/` oder `Archiv/ArchivSuche/` |
| ein offener Punkt | `Archiv/TASKS.md`, sofort |

**Der Skill verweist, er wiederholt nicht.** Zahlen stehen in der Notiz, sonst
veraltet die Kopie im Skill still. Verlinkt wird mit `[[Notizname]]`.

Nicht jeder Fall verdient einen Skill — die Prüffragen und das Hausformat stehen
im Skill `skill`. Ob sich etwas wirklich wiederholt, wird gemessen (Skill
`rueckschau`), nicht geschätzt.

## Notizen im Vault

Neue Erkenntnisse, die dauerhaft gelten, gehören als Markdown-Datei nach
`Wissen/` (Skill `notiz`), nicht in eine Chat-Antwort. Verlinkung untereinander
mit `[[Dateiname]]`, damit Obsidian den Graphen aufbauen kann.

**Das geschieht ungefragt, nicht als Angebot.** Wenn am Ende einer Aufgabe ein
Ergebnis steht, das in einem Monat noch gilt — eine Messung, eine Entscheidung
mit Begründung, eine Falle, die Zeit gekostet hat —, wird es abgelegt und die
Ablage in einem Satz gemeldet. Nicht „ich könnte das als Notiz ablegen".
Gefragt wird nur im Zweifelsfall, ob etwas überhaupt dauerhaft gilt.
Ausgewertete Zahlen brauchen dabei das Skript, mit dem sie entstanden sind —
sonst ist die Notiz beim nächsten Mal nicht nachrechenbar (Beispiel:
[[Handelsbots]] und `../Agenten/Handel/dca_auswertung.py`).

Kurzlebiges (Zwischenstände, Ausgaben eines einzelnen Laufs) gehört **nicht**
in den Vault, sondern nach `../Werkstatt/`.

## Mehrere Sitzungen gleichzeitig

Max hat mehrere Chats offen, dazu Hermes — alle schreiben in denselben Vault.
**Git schützt nur, was committet ist**, alles davor kann eine andere Sitzung
vernichten. Deshalb:

- **Verwerfen ist verboten, Sichern ist Pflicht.** Fremdes im Arbeitsbaum nicht
  liegen lassen, sondern in einem **eigenen, getrennten Commit** sichern, mit
  `git commit --author="Andere Sitzung <fremd@local>"` — nie vermischt mit
  eigener Arbeit. Den echten Namen nur eintragen, wenn der Urheber wirklich
  feststeht (etwa `"Hermes <hermes@local>"`); **nicht raten**, das macht die
  Historie genauso falsch wie die Ich-Form. `git add <pfad>` namentlich, nie
  `git add -A`, `git add .` oder `git commit -a`. Liegen lassen, was in den
  letzten **10 Minuten** geschrieben wurde (`(Get-Item <pfad>).LastWriteTime`)
  — älter gilt als ruhend.
- **Das erledigt jetzt auch eine Routine.** `Agenten/Routinen/fremdarbeit-einziehen.ps1` läuft täglich 20:40 (Aufgabe `MaxHirn-Fremdarbeit-Einziehen`, nach dem Zwischenstand um 20:00) und zieht die **ruhende** Fremdarbeit in einem Commit mit dem Autor `Andere Sitzung <fremd@local>` nach `master`. Ruhend heißt: länger als 30 Minuten unberührt — was eine laufende Sitzung gerade schreibt, bleibt liegen. Dieselbe Arbeit von Hand zu committen bleibt richtig und schneller; die Routine ist der Nettofang für alles, was liegen bleibt.
- **Nie verwerfen:** `git reset --hard`, `checkout -- <datei>`, `restore`,
  `stash`, `clean` löschen die uncommittete Arbeit anderer Sitzungen
  unwiederbringlich. Nur auf ausdrückliche Anweisung, vorher ansagen.
- **Kein `git stash` im geteilten Arbeitsbaum.** `stash` ist Verwerfen mit
  Verzögerung: Der Stash friert Arbeit ein, während andere Sitzungen weiter
  committen; ein späteres `stash pop` konfligiert gegen Zwischencommits.
  Bei Pop-Konflikten gilt: OURS = aktueller Repo-Stand, THEIRS = der ältere
  Stash — die Seiten erst per Datum vergleichen (Stash-Datum gegen die
  Commits, die die Datei seither berührt haben), dann auflösen; nur
  übernehmen, was im Repo noch fehlt. Eigene Arbeit sofort committen statt
  stashen. Lehre vom 08.10.2026: Der Stash „Vault-Schutzschicht" kollidierte
  beim Pop mit 14 Zwischencommits anderer Sitzungen.
- **Eigener Zweig je Agent (seit 08.10.2026).** Jeder Agent arbeitet auf einem
  eigenen Zweig, der von `master` abzweigt, in einem eigenen Arbeitsbaum unter
  `.worktrees/` (`git worktree add .worktrees/<name> -b <agent>/<thema> master`),
  nie per `git switch` im geteilten Hauptbaum. Nach `master` kommt erst etwas,
  wenn die PR abgeschlossen ist (Tests grün, freigegeben); danach Zweig und
  Arbeitsbaum löschen. Offene Zweige sind keine Altlast. Vollständig: Wurzel-
  `CLAUDE.md`, Abschnitt „Zweige".
- **Eigenes zügig committen**, nach jedem Arbeitsschritt.
- **`index.py`, `sort_inbox.py`, `sichern.ps1`, `zweitkopie.ps1` nie doppelt
  starten.**

Vollständig: [Wissen/Schutzregeln.md](Wissen/Schutzregeln.md)

## Portabilität

- Keine absoluten Pfade (`C:\Users\...`) in Skills, Notizen oder Skripten.
- Das Python-`.venv` unter `Archiv/ArchivSuche/.venv` ist an seinen Pfad gebunden
  und muss nach einem Umzug einmal neu erzeugt werden — siehe
  [Wissen/Portabilitaet.md](Wissen/Portabilitaet.md).
- Beim Verschieben ganzer Ordner gilt das Verfahren aus dem Skill `umzug`:
  editable installs und `.exe`-Startprogramme in `.venv` tragen absolute Pfade
  im Inneren und brechen still.

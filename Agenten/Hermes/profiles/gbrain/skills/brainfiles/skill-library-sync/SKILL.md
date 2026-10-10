---
name: skill-library-sync
description: "Skills zwischen Vault (Claude) und Hermes abgleichen, einzelne Fremd-Skills übernehmen."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [skills, brainfiles, hermes, vault, import]
    related_skills: [skill, umzug, verbindungen, hermes-config-ops]
---

# Skill-Bibliothek abgleichen

Hält die Skill-Ablagen von Vault (Claude Code) und Hermes auf demselben Stand:
fehlende Skills nachziehen, still veraltete Kopien finden, das Ergebnis gegen die
geladene Bibliothek prüfen. Der Vault bleibt Quelle und wird zeichengleich
übernommen — geändert wird dort nur die Notiz `Wissen/Hermes.md`.

## Wann

- "such die Skills und füge sie hinzu", "der Skill fehlt in Hermes", "importier die Skills"
- nach jedem neuen Skill unter `.claude/skills/`
- nach jedem Umbenennen oder Verschieben im Vault — dann driften alle Kopien mit
- ein **fremder, benannter** Skill soll einzeln übernommen werden (Abschnitt
  „Fremden Skill einzeln übernehmen"); das ist die Ausnahme vom Verbot der
  Fremd-Bäume, nicht sein Ende

**Don't use for:** einen neuen Skill entwerfen (Skill `skill`), MCP-Server übertragen
(`verbindungen`), Skills im laufenden Betrieb vergleichen (dafür Hash-Prüfung unten).

## Wo was liegt (Wurzel `BrainFiles/`)

| Ablage | Rolle |
|---|---|
| `MaxHirn/.claude/skills/` | **Quelle.** Hier entstehen die Skills; maßgeblich laut AGENTS.md |
| `MaxHirn/.agents/skills/` | **Kein Spiegel, sondern eine Codex-Fassung** (eigene Texte mit `Codex/TASKS.md`, `~/.Codex/…`). Gemessen 12.09.2026: 17 statt 22 Skills, 10 abweichend. **Nicht aus dem Vault überschreiben** — das ersetzt die Codex-Anpassung durch Claude-Werkzeugnamen. Vorher prüfen, wer den Baum liest. |
| `MaxHirn/.claude/skills-sicherung/` | Sicherung **global** installierter Skills; nicht geladen, nur Rückfallebene |
| `MaxHirn/optional-skills/` | Skills im Hermes-Format |
| `Agenten/Hermes/skills/claude-code-imports/<name>/` | Ziel für Skills im Claude-Format |
| `Agenten/Hermes/skills/<sachkategorie>/<name>/` | Ziel für Skills im Hermes-Format |
| `Agenten/Hermes/.sicherung/` | Sicherung ersetzter Dateien |

**Nicht die eigene Bibliothek:** `MaxHirn/skills/` (geklonte Fremd-Repos) und
`MaxHirn/codex/` (Codex-CLI samt `skills/src/assets/samples/`). Aus fremden Bäumen
nichts importieren — die Beispiele dort gehören anderen Werkzeugen.

Erreichbar bleiben sie trotzdem, ohne Import: Skill `fundus-zugriff` sucht sie auf
Anforderung (~25 statt ~14.700 Tokens je Anfrage). Ein Symlink des Fremd-Baums in
`Agenten/Hermes/skills/` hebelt genau diesen Schutz aus.

## Vorgehen

1. **Bestand aufnehmen.** `Get-ChildItem -Recurse -File -Filter SKILL.md` über
   `MaxHirn` und `Agenten/Hermes/skills` **je Ablage einzeln** (eine Suche über die
   ganze Wurzel `BrainFiles/` lässt Teilbäume still aus: in einem solchen Lauf fehlten
   die Hermes-Kopien vollständig), jeden Fund einer Zeile der Tabelle oben
   zuordnen. *Fertig, wenn* kein Fund aus einem Fremd-Baum stammt und jede der
   beiden Zielablagen einzeln aufgelistet ist.
2. **Drift prüfen.** Je Bestandsskill `Get-FileHash` auf Vault und Kopie, Ergebnis
   auf `gleich` / `abweichend` / `fehlt`. *Fertig, wenn* kein Bestandsskill ohne
   Urteil bleibt.
3. **Sichern.** Jede Kopie, die ersetzt wird, vorher nach
   `Agenten/Hermes/.sicherung/skills-import-<JJJJMMTT>/<name>/` kopieren.
   *Fertig, wenn* jede ersetzte Datei dort liegt.
4. **Richtung prüfen, dann kopieren.** Bei jeder *abweichenden* Kopie zuerst
   `Compare-Object` in **beide** Richtungen. Zeilen, die nur in der Quelle stehen,
   sind verpasster Nachzug. Zeilen, die nur in der Kopie stehen, sind Inhalt, den
   die Quelle nie bekommen hat — den **zuerst in die Quelle nachziehen**, sonst
   löscht das Kopieren ihn. In der Praxis ist genau das vorgekommen: die
   Hermes-Kopie eines Skills trug einen ganzen Abschnitt, den die Quelle nicht
   hatte. Erst danach `Copy-Item -Recurse -Force` Ordner für Ordner, fehlende und
   (jetzt) abweichende zusammen. **Nicht** `hermes import-agent` benutzen: der
   schreibt den ganzen Satz neu und überschreibt die Nacharbeit in den Kopien,
   ohne dass nachvollziehbar bleibt, welche Fassung ersetzt wurde.
   *Fertig, wenn* keine abweichende Kopie mehr Zeilen enthält, die in der Quelle fehlen.
5. **Nacharbeit nur in den Kopien.** Werkzeugnamen auf Hermes umsetzen
   ([references/werkzeugnamen-claude-hermes.md](references/werkzeugnamen-claude-hermes.md)),
   im Vault bleiben sie stehen. *Fertig, wenn* unverändert übernommene Skills per Hash
   weiterhin gleich sind.
6. **Prüfen.** Frontmatter (beginnt mit `---`, `name` und `description` vorhanden),
   LF, kein BOM, keine doppelt kodierten Umlaute; dann `hermes skills list`.
   *Fertig, wenn* jeder neue Eintrag als `local` und `enabled` erscheint.
7. **Vault-Notiz nachziehen.** Abschnitt `## Skills` in `Wissen/Hermes.md`
   (Stufe 1: vorher `.bak-<JJJJMMTT>`), dann namentlich committen — `git add <pfad>`,
   Autor `Hermes <hermes@local>`.

## Fremden Skill einzeln übernehmen

Ein von außen benannter Skill (Repo, Blog, Zuruf) kommt **einzeln** in die
Bibliothek — kein Klon des Ganzen, kein Import des Fremd-Baums:

    hermes.exe skills install "https://raw.githubusercontent.com/<owner>/<repo>/<branch>/skills/<name>/SKILL.md" --category <kategorie> --yes

1. **Rohquelle statt Repo-Seite.** Die `raw.githubusercontent.com`-URL auf die
   kanonische `SKILL.md` zeigen lassen (die spiegelt das Repo oft mehrfach —
   `.cursor/`, `.claude-plugin/`; die kanonische Fassung nennt die README oder
   `AGENTS.md` des Repos). `--category` bestimmt den Unterordner; ohne
   `--category` landet der Skill flach in `skills/`.
2. **Der Lauf hat drei sichtbare Stationen:** Quarantäne (`.hub/quarantine/<name>`),
   Sicherheitsscan mit Verdikt (`SAFE` / `BLOCKED`), dann
   `Installed: <kategorie>/<name>`. `--force` nur bei blockiertem Verdikt und nur
   nach dem Lesen der Scanbegründung. Fehlt ein `name:` im Frontmatter, `--name` setzen.
3. **Vor dem Nehmen prüfen, was es sonst gibt:** `hermes skills search <wort>`
   listet die Register (skills.sh, clawhub, …) mit Quelle und Vertrauensstufe.
   Oft existiert schon eine gepflegte Fassung, dann ist der Fremd-Klon unnötig.
4. **Belegen:** `hermes skills list` zeigt den Eintrag mit Quelle `url` und
   Herkunft `community` als `enabled` — und den Slash-Namen des Skills.
5. **Claude-Seite:** denselben Text nach `MaxHirn/.claude/skills/<name>/SKILL.md`
   legen. Der Pfad ist in `.gitignore` freigegeben (`!MaxHirn/.claude/skills/**`),
   `git check-ignore -v <pfad>` bestätigt das vor dem Commit.
6. **Immer-an-Wirkung gehört woanders hin.** Ein Skill wird nachgeladen, nie
   dauerhaft in den Prompt geschrieben — soll der Fremd-Skill das Verhalten
   *jeder* Antwort ändern, landet sein Kern in `SOUL.md` (`hermes-config-ops`,
   Abschnitt „Persona und Ausgabestil"), der Skill bleibt die Nachschlagefassung.

Fallen:

- **Mehrere Skills aus einem Klon: parallele Delegation mit Adoptionsauftrag.**
  Bringt der Nutzer einen ganzen Klon (z. B. Werkstatt/Repos) ins Spiel, ist je
  Skill dieselbe Adaption faellig: Kern behalten, fremde Werkzeugnamen auf
  Hermes-Werkzeuge umsetzen, auf ~6.000 Zeichen kuerzen, Beschreibung kurz und
  selbsttragend (erste ~57 Zeichen = Ausloeser), Provenienz-Zeile. Das ist
  Einzelarbeit mit klarem Auftrag — 2-3 Skills je Subagent parallel delegieren
  (delegate_task), jeder Kontext enthaelt: Quelldatei-Pfad(e), die
  Adoptionsregeln, das Verbot von Duplikaten (VORHER pruefen, welche Skills aus
  derselben Quelle schon adaptiert in der Bibliothek liegen!), und den Zielweg
  ueber skill_manage create. Danach NACHPRUEFEN — Subagent-Berichte sind
  Selbstauskuenfte: jede SKILL.md existiert, Frontmatter valide, Beschreibung
  kurz, keine Duplikate entstanden.
- **Hub-Installiertes ist danach nicht mehr unsere Datei.**
  `hermes skills check` / `update` frischt `skills/<kategorie>/<name>/` gegen die
  Quelle auf — eigene Ergänzungen in der installierten `SKILL.md` gehen dabei
  verloren. Zusätze also in eine eigene Notiz oder in die Immer-an-Schicht
  schreiben, nicht in die Kopie.
- **Das Fremd-Baum-Verbot meint Bäume, nicht einen benannten Skill.** `MaxHirn/skills/`
  und `MaxHirn/codex/` bleiben gesperrt (Token-Kosten bei jeder Anfrage, fremde
  Werkzeugnamen); ein einzelner, vom Nutzer benannter Fremd-Skill darf in die
  Bibliothek. Den Unterschied im Ergebnis benennen, sonst liest es sich wie ein
  Rückfall hinter die eigene Regel.
- **Für die Claude-Desktop-App ist der Ordnerpfad kein Beleg.** Die App lädt
  Skills über ihre Einstellungen hoch; `MaxHirn/.claude/skills/` allein deckt
  Claude Code ab. Diesen Schritt beim Nutzer als **offen** melden, solange kein
  Lauf ihn zeigt — nie als erledigt zählen.

## Fallen

- **Die SKILL.md hat eine harte Groessengrenze: ab ~100.000 Zeichen verweigert
  `skill_manage` JEDE Aenderung an diesem Skill** — auch eine einzelne Zeile, auch eine
  neue Referenzdatei im selben Aufruf (der ganze Stapel wird zurueckgerollt). Ein
  uebergrosser Text ist damit nicht nur teuer (er wird bei jedem Ausloesen mitgeladen),
  sondern macht den Skill unwartbar. Reparatur in einem Zug: den groessten Abschnitt
  VOLLSTAENDIG nach `references/<thema>.md` verschieben und in der SKILL.md eine
  nummerierte Landkarte behalten (ein Satz je Punkt, gleiche Nummer wie im Volltext)
  plus References-Eintrag. Danach mit einer kleinen Testaenderung belegen, dass
  Schreiben wieder geht, und die Testaenderung zuruecknehmen.
- **Eine `references/`-Datei ohne Eintrag in der SKILL.md ist toter Text.** Der Loader
  zeigt beim `skill_view` nur, was die SKILL.md selbst nennt; eine Referenz, die dort
  nicht auftaucht, wird nur durch Zufall gefunden (Ordner durchsuchen, Stichwort greppen)
  — im Zweifel arbeitet die nächste Sitzung die Aufgabe noch einmal von vorn. Beim
  Anlegen oder Umschreiben einer Referenz gehört der Pfad im selben Zug in die
  Auslöserliste („Wann") der SKILL.md, formuliert in den Worten, nach denen man
  später sucht („Änderung, die alle Spuren trifft → `references/x.md`"), nicht nur als
  Dateiname am Ende. Gegenprobe: den Referenznamen in der SKILL.md suchen — genau ein
  Treffer, sonst ist sie verwaist.

- **`HERMES_HOME` in derselben Shell setzen.** Kindprozesse erben Windows-Benutzervariablen
  nicht: ohne `$env:HERMES_HOME='…\Agenten\Hermes'` liest `hermes skills list` das
  Standardprofil und meldet eine plausibel aussehende, aber falsche Menge (64 statt 113).
  Gegenprobe: die Zahl muss zur erwarteten Bibliothek passen.
- Startprogramme liegen in `Agenten/Hermes/bin/` als **`.exe`** (`hermes.exe`) — ein
  `hermes.cmd` gibt es dort nicht. Bei `CommandNotFoundException` die `.exe` nehmen,
  statt nach einem Wrapper zu suchen.
- **Byte-Gleichheit halten:** UTF-8 ohne BOM, LF. Prüfen mit
  `[System.IO.File]::ReadAllBytes` auf `EF BB BF` (BOM) und `C3 83` (doppelt kodierte
  Umlaute); schreiben mit
  `[System.IO.File]::WriteAllText($p,$t,(New-Object System.Text.UTF8Encoding($false)))`.
  **Im Bestand gemischt, das ist kein Fehler:** importierte Skills unter
  `claude-code-imports/` sind LF, Hermes-eigene (`brainfiles/`, `autonomous-ai-agents/`)
  CRLF. Nicht „vereinheitlichen". Ein von Hand nachgearbeiteter Skill bekommt beim
  Schreiben per PowerShell CRLF, obwohl der Inhalt gleich ist — dann lügt der Hash.
  Vor dem Vergleich und nach dem Kopieren **beide Seiten** auf LF normalisieren,
  danach ist der Hash aussagekräftig.
- **Mehrzeilige Textblöcke nie als PowerShell-Here-String durch eine Werkzeugschicht
  schicken** — die Begrenzer kommen verstümmelt an ("Die Zeichenfolge hat kein
  Abschlusszeichen"). Den Block als eigene Datei schreiben, mit Regex an der
  Überschriftengrenze einsetzen (`(?s)## Name\r?\n.*?(?=\r?\n## )`, Ersetzungen=1),
  Vorlage wieder löschen.
- **Windows-Pfade im Python-Heredoc als RAW-String schreiben.** Die Werkzeugschicht
  kollabiert `\\` zu `\`: im Quelltext steht dann `C:\Users\…`, und Python bricht
  schon beim Parsen ab (`SyntaxError: truncated \UXXXXXXXX escape`) — die Datei ist
  dabei unangetastet, der Fehler kommt also vor dem Schreiben. Also `r"…\pfad…"`
  fuer Muster und Ersetzungen oder den Backslash ueber `chr(92)` bauen; ganze
  Textbloecke als eigene Datei schreiben und mit `read_text` einsetzen. Nach jeder
  Textersetzung `git diff --numstat` lesen: wenige Zeilen = gewollt, ganze Datei =
  Zeilenenden oder Kodierung verstellt (dann `git checkout HEAD -- <datei>` und neu).
- **Ein kopierter Skill ist noch keine Funktion.** Kopien, die auf Vault-Pfade per
  Kommandozeile zugreifen, arbeiten nur, wenn das Terminal-Arbeitsverzeichnis im Vault
  liegt; ein Docker-Backend sieht außer den Skills nichts vom Vault. Nach dem Kopieren
  den Terminal-Stand prüfen und ihn nennen — sonst meldet der Abgleich Erfolg für
  Skills, die nichts tun können. Startet kein Terminal (`proxy.enabled: true` ohne
  iron-proxy): `hermes egress setup`.
- **Umbenannte Ordner sind die häufigste Drift.** Ein Pfad, der ins Leere zeigt, macht
  den Skill wertlos, ohne dass sein Text sich ändert. Nach jedem Umzug im Vault die
  Kopien zusätzlich nach dem **alten** Ordnernamen absuchen (`Select-String`), nicht
  nur Hashes vergleichen.
- **Ein Baum, der wie ein Spiegel aussieht, kann eine eigene Bibliothek sein.** Nicht
  annehmen, sondern beim Verbraucher nachsehen: im Quellbaum des betreffenden Agenten
  nach dem Pfad greppen. Für `.agents/skills/` liegt die Antwort in
  `MaxHirn/codex/codex-rs/skills` und `ext/skills` — Codex entdeckt Skills unter
  `.agents/skills`, im Arbeitsverzeichnis wie als Benutzerschicht
  `$HOME/.agents/skills`. Die Texte dort sind entsprechend angepasst; ein
  `Copy-Item` aus dem Vault ersetzt sie durch die eigene Werkzeugnamen-Konvention,
  ohne dass ein Hash das zeigt. Ist es ein Fork, ihn aus der **aktuellen** Quelle neu
  erzeugen und dabei nur die Agenten-Identität umsetzen — die alte Umbenennung
  fortzuschreiben lässt Pfade stehen, die auf den früheren Vault-Namen zeigen.
- Kopien werden erst in einer **neuen Sitzung** geladen; `skills_list` und `skill_view`
  zeigen in der laufenden Sitzung weiter den alten Stand. Das ist kein Fehlschlag.

## Nachweis

- `hermes skills list` (mit gesetztem `HERMES_HOME`) listet jeden neuen Skill als
  `local`/`enabled`, und die Gesamtzahl passt zur erwarteten Bibliothek.
- `Get-FileHash` der Bestandsskills: Vault und Kopie gleich.
- Jede ersetzte Datei liegt unter `.sicherung/skills-import-<JJJJMMTT>/`.
- `Wissen/Hermes.md` nennt Anzahl, Quelle und offene Punkte; committet.

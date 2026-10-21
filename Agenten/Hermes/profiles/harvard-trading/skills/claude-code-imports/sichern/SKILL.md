---
name: sichern
description: Committet den Arbeitsbaum im Mehrsitzungsbetrieb, ohne fremde Arbeit zu vermischen oder zu verlieren. Benutzen bei "commite", "sichere den Stand", "Commit the working tree changes", "was ist uncommittet", "git status", "fremdarbeit zusammenführen und sichern", "fremde Arbeit einziehen", oder nach jedem abgeschlossenen Arbeitsschritt im Vault.
---

# Stand sichern

Mehrere Claude-Sitzungen und Hermes schreiben in denselben Vault. **Git schützt
nur, was committet ist** — alles davor kann eine andere Sitzung vernichten.
Vollständige Begründung in [[Schutzregeln]]; hier steht der Ablauf.

## 1. Lage feststellen

**Zuerst die eigene Arbeit committen, dann prüfen.** Ein `git status` über einen
Arbeitsbaum, in dem die eigene Änderung noch offen steht, meldet sie als „fremd"
— die Ruheschwelle sieht nur das Alter, nicht den Urheber. Erst die eigene Arbeit
namentlich committen, dann den Baum lesen; was danach noch liegt, ist wirklich
fremd.

```powershell
..\Agenten\Routinen\arbeitsbaum-pruefen.ps1
```

Liest `git status --porcelain`, ergänzt je Datei die Änderungszeit und trennt
nach der 10-Minuten-Schwelle. Ändert nichts. Die fertige `git add`-Zeile für die
ruhende Gruppe gibt es dazu.

Die Schwelle ist bewusst eine Zahl und kein Ermessen: Eine Datei, die vor
weniger als zehn Minuten geschrieben wurde und **nicht** aus dieser Sitzung
stammt, kann mitten in einem fremden Arbeitsschritt stehen. Die bleibt liegen
und wird gemeldet. Was diese Sitzung selbst geschrieben hat, wird natürlich
committet — dafür ist die Uhrzeit ohne Belang.

## 2. Zwei Commits, nicht einer

Eigene und fremde Arbeit werden **getrennt** committet, nie im selben Commit.
Dateien namentlich hinzufügen:

```bash
git add "Wissen/Hardware.md" "Archiv/TASKS.md"
git commit -m "Hardware: Absturzanalyse vom 28.08."
```

Fremdes bekommt das Autorenfeld, nicht nur eine Randbemerkung im Text:

```bash
git commit --author="Andere Sitzung <fremd@local>" -m "Fremde Arbeit gesichert: Hermes.md"
```

**Nie** `git add -A`, `git add .` oder `git commit -a` — nicht wegen der fremden
Arbeit, sondern weil sie beide Sorten zusammenwerfen.

**Nicht raten, wer es war.** „Hermes" ins Autorenfeld zu schreiben, weil es
plausibel klingt, macht die Historie genauso falsch wie die Ich-Form. Steht der
Urheber nicht fest — der Regelfall, denn eine Änderung im Arbeitsbaum trägt
keinen Namen —, gilt `Andere Sitzung <fremd@local>`. Hermes committet nie
selbst; seine Arbeit ist nur versioniert, wenn eine Claude-Sitzung sie mitnimmt.

### Fremdarbeit gesammelt einziehen

Liegt viel ruhende Fremdarbeit herum, nicht von Hand zusammensuchen, sondern die
Routine nehmen (sonst läuft sie stündlich um :20 von selbst):

```powershell
..\Agenten\Routinen\fremdarbeit-einziehen.ps1 -Testlauf
..\Agenten\Routinen\fremdarbeit-einziehen.ps1 -NichtPushen
```

- Ohne `-NichtPushen` pusht sie nach `origin master` — Push nur nach Rückfrage.
- Ihre Ruheschwelle ist **30** Minuten, nicht 10: was der Testlauf als „in
  Arbeit" meldet, bleibt liegen.
- Eigener Index (`.git\fremdarbeit.index`), Autor `Andere Sitzung <fremd@local>`;
  bei Git-Sperre wird übersprungen. Eigene Arbeit vorher selbst committen.

Einzelheiten und Log in [[Routinen]] („Fremdarbeit übernehmen"); Hermes-Gegenstück
ist der Skill `arbeitsbaum-git-hygiene`.

## 3. Zweige und Merge (seit 08.10.2026)

Maßgeblich ist der Abschnitt „Zweige" in der Wurzel-`CLAUDE.md`; hier nur, was
beim Sichern daraus folgt:

- **Eigene Arbeit** liegt auf dem eigenen Zweig (`<agent>/<thema>`, Arbeitsbaum
  unter `.worktrees/`), nie per `git switch` im geteilten Hauptbaum. Dort oft
  committen, auch halbfertig.
- **Nach `master` kommt nur Abgeschlossenes:** Tests grün, PR eröffnet und
  freigegeben. Gemergt wird per PR, danach Zweig und Arbeitsbaum löschen
  (`git branch -d`, `git worktree remove`, `git push origin --delete`).
  Direkt auf `master` committet werden nur Routinen (kb-sync, Fremdarbeit
  einziehen) und reine Pflege (Notizen, Index, TASKS-Vermerke).
- **Fremdarbeit aus einem anderen Zweig-Arbeitsbaum** (Zweig `wt/…`, `t_…`)
  wird nicht still nach `master` geschoben: erst melden, was drinliegt, dann
  per PR oder auf ausdrückliche Freigabe mergen. Liegenlassen ist erlaubt.
- **Fremd-Repos** in `Werkstatt/` haben ihre eigenen Zweignamen (meist
  `main`). Die Regel „alles auf master" gilt nur fürs BrainFiles-Repo; ein
  Push in einen Fork braucht Rückfrage, und Workflow-Dateien
  (`.github/workflows/`) lehnt GitHub ohne Token-Scope `workflow` ab — der Push
  überträgt die ganze Commit-Kette, nicht nur den eigenen Commit.

## 4. Was nie passiert

`git reset --hard`, `git checkout -- <datei>`, `git restore`, `git stash`,
`git clean` löschen genau das, was Git noch nicht schützt. Nur auf ausdrückliche
Anweisung in derselben Sitzung — und vorher ansagen, welche Dateien es trifft.

Ein zu viel gemachter Commit ist dagegen harmlos: als Spitze mit
`git reset --soft HEAD~1` zurückzunehmen, sonst mit `git revert`. **Sichern ist
immer die richtige Richtung** — verwerfen ist die einzige unumkehrbare Handlung.

## 5. Was nicht ins Repository gehört

Versioniert ist nur die Textebene des Vaults. Die persönlichen Bestände
(`Archiv/Dokumente/`, `Bilder/`, `Videos/`, `Musik/`) enthalten keine einzige
versionierte Datei; die Whitelist in `.gitignore` gibt sie bewusst nicht frei.

Nie hinzufügen: Zugangsdaten, `.env`, `.pem`, `.pfx`, `.p12`, `.kdbx`, `.key`,
`~/.claude/.credentials.json`. Servereinträge ohne Geheimnis (Name, Typ,
öffentliche Adresse) sind dagegen gefahrlos versionierbar.

Vor dem Commit prüfen, ob versehentlich etwas Großes oder Geheimes ansteht:

```bash
git diff --cached --stat
```

## 6. Wann

Nach **jedem** abgeschlossenen Arbeitsschritt, nicht am Sitzungsende. Ein
Sitzungsabbruch nimmt sonst alles mit, was noch im Arbeitsbaum liegt — und in
diesem Vault arbeitet nie nur eine Sitzung.

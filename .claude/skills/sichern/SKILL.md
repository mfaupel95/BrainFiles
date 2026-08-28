---
name: sichern
description: Committet den Arbeitsbaum im Mehrsitzungsbetrieb, ohne fremde Arbeit zu vermischen oder zu verlieren. Benutzen bei "commite", "sichere den Stand", "Commit the working tree changes", "was ist uncommittet", "git status", oder nach jedem abgeschlossenen Arbeitsschritt im Vault.
---

# Stand sichern

Mehrere Claude-Sitzungen und Hermes schreiben in denselben Vault. **Git schützt
nur, was committet ist** — alles davor kann eine andere Sitzung vernichten.
Vollständige Begründung in [[Schutzregeln]]; hier steht der Ablauf.

## 1. Lage feststellen

```powershell
.\Routinen\arbeitsbaum-pruefen.ps1
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
git add "Wissen/Hardware.md" "Claude/TASKS.md"
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

## 3. Was nie passiert

`git reset --hard`, `git checkout -- <datei>`, `git restore`, `git stash`,
`git clean` löschen genau das, was Git noch nicht schützt. Nur auf ausdrückliche
Anweisung in derselben Sitzung — und vorher ansagen, welche Dateien es trifft.

Ein zu viel gemachter Commit ist dagegen harmlos: als Spitze mit
`git reset --soft HEAD~1` zurückzunehmen, sonst mit `git revert`. **Sichern ist
immer die richtige Richtung** — verwerfen ist die einzige unumkehrbare Handlung.

## 4. Was nicht ins Repository gehört

Versioniert ist nur die Textebene des Vaults. Die persönlichen Bestände
(`Claude/Dokumente/`, `Bilder/`, `Videos/`, `Musik/`) enthalten keine einzige
versionierte Datei; die Whitelist in `.gitignore` gibt sie bewusst nicht frei.

Nie hinzufügen: Zugangsdaten, `.env`, `.pem`, `.pfx`, `.p12`, `.kdbx`, `.key`,
`~/.claude/.credentials.json`. Servereinträge ohne Geheimnis (Name, Typ,
öffentliche Adresse) sind dagegen gefahrlos versionierbar.

Vor dem Commit prüfen, ob versehentlich etwas Großes oder Geheimes ansteht:

```bash
git diff --cached --stat
```

## 5. Wann

Nach **jedem** abgeschlossenen Arbeitsschritt, nicht am Sitzungsende. Ein
Sitzungsabbruch nimmt sonst alles mit, was noch im Arbeitsbaum liegt — und in
diesem Vault arbeitet nie nur eine Sitzung.

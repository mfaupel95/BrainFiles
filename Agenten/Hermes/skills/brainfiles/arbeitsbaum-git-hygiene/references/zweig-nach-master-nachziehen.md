# Eigenen Commit vom Zweig einer Parallelsitzung nach master nachziehen

Wenn die eigene Arbeit auf dem ZWEIG einer parallelen Sitzung gelandet ist
(HEAD stand dort, `git switch` wurde nie gemacht) oder Max sagt „nachziehen,
Parallelsitzung mitnehmen": der Zweig haengt oft an einem aelteren Stand als
`origin/master` (andere Sessions haben per PR gemergt), `--ff-only` ist dann
keine Option.

## Ablauf

1. **Lage messen** (lesend, ein Aufruf):
   `git fetch`, `git log --oneline master..<zweig>`,
   `git rev-list --left-right --count master...origin/master`,
   `git cherry origin/master <zweig>` — nur `+`-Zeilen fehlen in
   origin/master. **Ein `+` fuer den eigenen Commit heisst NICHT „Inhalt
   fehlt":** der Commit wurde beim Nachzug unter anderer SHA gemergt
   (Konfliktloesung). Identitaet per Inhalt pruefen:
   `git diff <eigener-sha> <gemergte-sha> --numstat` — leer oder klein =
   derselbe Inhalt, nichts nachzutragen.

2. **Ruhende Fremdarbeit ZUERST sichern** (bevor etwas bewegt wird). Die
   30-min-Regel aus `fremdarbeit-uebernehmen`; Leerlauf der Prozesse messen
   (CPU-Delta zweimal, ~0 = tot), NICHT nur das Dateialter — ein Ordner mit
   Minuten-mtime kann ein laufender Dienst sein (Cron-`ticker_heartbeat`,
   `eingelegt.hoch.json` vom Dauerlauf). Dauerlauf-Schreibzugriffe
   (`eingelegt.hoch.json`, Minuten alt) sind KEIN Ruhezustand und bleiben
   liegen; vor dem Reset aus `cache/scratch/` zuruecksichern.

3. **Worktree von `origin/master`, eigener Commit zuerst:**
   `git worktree add .worktrees/<name> -b <zug> origin/master`, darin
   `git cherry-pick <eigener-sha>`.

4. **Konflikt in einer Datei, die master inzwischen NEU hat: KEINE Seite
   verwerfen — VERKETTEN.** Die HEAD-Fassung (fremde Aenderung) behalten und
   den eigenen Block als ZUSAETZLICHEN Schritt danach einfuegen; beide Filter
   wirken dann zusammen. Die Aufloesung und der Grund gehoeren in die
   Commit-Meldung.

5. **Rest des Zweigs der Reihe nach:** `git cherry-pick` in umgekehrter
   chronologischer Reihenfolge (`git log --reverse --format=%h
   origin/master..<zweig> | grep -v <eigener-sha>`), beim ersten Konflikt
   (`git diff --name-only --diff-filter=U`) stoppen und aufloesen.

6. **Ein Commit, der eine Datei LOESCHT, auf Referenzen pruefen.** Ein
   Housekeeping-Commit (z. B. kb-sync) kann eine Datei entfernen, auf die ein
   Task noch zeigt („Betrifft: <pfad>"). Aus dem ANLAGE-Commit zurueckholen
   (`git show <add-sha>:<pfad> > <pfad>`) und als eigenen Commit hinterher —
   sonst zeigt der Task ins Leere. Dateien unter `Werkstatt/Projekte` brauchen
   `git add -f` (die `*`-Sperre der .gitignore trifft sie).

7. **Push:** `git push origin <zug>:master`. Vorher `GITHUB_TOKEN`/`GH_TOKEN`
   leeren (`export GITHUB_TOKEN= GH_TOKEN=`) — der Registry-Token hat keinen
   Schreibzugriff und der Push endet sonst als 403, waehrend derselbe Push von
   Hand geht.

8. **Aufraeumen in DIESER Reihenfolge:** `git worktree remove
   .worktrees/<name> --force` → `git branch -D <zug>` →
   `git push origin --delete <fremder-zweig>` → `git worktree prune`.
   `git branch -D <paralleler-zweig>` kann mit „used by worktree at ...
   pr79" scheitern: erst DORT den Stand pruefen (`git diff origin/master
   HEAD --stat` leer = inhaltlich identisch), dann dieses Worktree entfernen,
   dann den Zweig loeschen.

9. **Mischzustand nach dem Zweig-Wechsel erkennen und heilen.** Schreibt die
   parallele Sitzung waehrend des Wechsels in den GETEILTEN Index, bewegt
   `git switch master` den Kopf, aber der Arbeitsbaum traegt weiter den
   Inhalt des anderen Zweigs: 40+ `M`-Zeilen und fremde `??`-Ordner stehen
   da, obwohl HEAD stimmt. **Erst den Beweis fuehren, dann hart
   zuruecksetzen:** `git cherry origin/master <zweig>` (nur der eigene,
   gemergte Commit darf `+` sein) UND je `??`-Datei
   `git cat-file -e origin/master:<pfad>` — steht alles in origin/master,
   `git checkout -- .` und `git reset --hard origin/master`. OHNE diesen
   Beweis ist reset verboten (Regel „nichts fremdes zuruecksetzen" aus dem
   SKILL.md gilt).

10. **Die Suite NACH dem Reset im Hauptbaum fahren**, nicht im Worktree: nur
    dort laeuft sie gegen den Zustand, den master wirklich hat.

## Nachweis vor dem Abschluss

- `git log -1 --format=%h %s` = der eigene Commit oben auf origin/master
- `git status --porcelain` leer (bis auf Dauerlauf-Schreibzugriffe)
- betroffene Suite im Hauptbaum: `Ran N tests ... OK`
- `git branch -a | grep -E '<zug|fremd>'` leer, `git worktree list` nur
  noch erwartete Eintraege

## Merksatz

**Nachziehen ist Beweisfuehrung in der Reihenfolge: sichern → Worktree →
verkettet mergen → pushen → aufraeumen.** Ein `reset --hard` ohne den
cherry-Beweis verwirft fremde Arbeit; ein `--ff-only` auf einen Zweig, der
hinter origin/master liegt, tut nichts und sieht erledigt aus.

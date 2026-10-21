# Fremde Dateien im Weg: Klon nachziehen und nach dem Merge aufraeumen

Zwei Arbeitsbaum-Chirurgien an einem geteilten Klon. Beide gelten fuer JEDES
Repo im Baum (Werkstatt/, Agenten/Handel/*), nicht nur fuer BrainFiles selbst.

## 1. Unversionierte Fremddateien blockieren den Wechsel

Symptom: `git checkout <ziel>` oder ein Pull bricht ab mit

```
error: The following untracked working tree files would be overwritten by checkout
```

und nennt Dateien, die diese Sitzung nie angelegt hat. Sie gehoeren einer
Parallelsitzung.

**NIE `checkout -f`.** Das ueberschreibt fremde Arbeit ohne Spur. Stattdessen
klassifizieren — das kostet einen Lauf und ist verlustfrei rueckholbar.

### Ablauf

1. Zielbaum als Set holen:
   ```bash
   git ls-tree -r --name-only <ziel>        # z. B. origin/main
   ```
2. Unversionierte Eintraege auflisten:
   ```bash
   git status --porcelain | grep '^?? '
   ```
3. **Je Eintrag entscheiden, ob er ueberhaupt der Kandidat ist.** Ein `??` kann
ein ganzer ORDNER sein; dann sind seine DATEIEN die Kandidaten, nicht der Ordner
(Praefix-Test gegen das Zielbaum-Set).
4. Je kollidierender Datei den Inhalt vergleichen — nicht den Namen:
   ```bash
   git hash-object <pfad>              # Arbeitsbaum
   git rev-parse <ziel>:<pfad>         # Ziel
   ```
   - **gleich** -> das Loeschen verliert nichts (der Checkout stellt sie her).
   - **anders** -> nach `<repo>/.fremd-JJJJMMTT/<pfad>` kopieren und ein
     `MANIFEST.json` daneben schreiben (`identisch_geloescht` /
     `abweichend_gesichert`). Ohne Manifest weiss der Naechste nicht, was der
     Ordner ist und ob er weg darf.
5. Erst sichern, DANN loeschen, DANN wechseln. Reihenfolge in einem Skript, nicht
von Hand: der Schritt „loeschen" ist der einzige, der nicht rueckgaengig ist.
6. Nachweis, dass der Wechsel wirklich sitzt:
   ```bash
   git rev-parse --short HEAD
   git status --porcelain           # nur noch Datenordner + Sicherung
   <build/test des Repos>           # Pflicht: der Baum muss bauen
   ```

### Pitfalls

- **Eine unversionierte Datei kann ein Modulverzeichnis verdecken und mit KEINEM
  Pfad kollidieren.** In Rust gewinnt `src/okx.rs` gegen `src/okx/mod.rs` (die
  Datei ist der Modulwurzelpunkt) — der Build laeuft still gegen einen anderen
  Modulbaum als das Repo enthaelt, und `git status` zeigt die Datei brav als
  `??`. Vor dem Wechsel pruefen, ob neben einem Modulordner eine gleichnamige
  `.rs`-Datei liegt (`<stamm>.rs` neben `<stamm>/mod.rs`) und sie mitnehmen.
  Dasselbe Muster gibt es in Python (`paket.py` neben `paket/`) und in JS
  (`x.js` vor `x/index.js`, je nach Aufloesung).
- **Datenordner nie als Kollision behandeln.** `daten/`, `logs/`, `status/`,
  `target-live/`, `.projectatlas/` stehen NICHT im Zielbaum und bleiben stehen —
  ein pauschales `git clean -fdx` loescht Messgrundlagen.
- **Byte-gleich heisst byte-gleich.** Nur `hash-object` gegen
  `rev-parse <ziel>:<pfad>`; ein Blick auf `diff` reicht bei Zeilenenden (CRLF/LF)
  nicht, dort meldet jeder Vergleich Aenderungen, die keine sind.
- **Der Nachweis ist der Build, nicht der Checkout.** `HEAD` stimmt auch, wenn
  die falsche Datei liegen geblieben ist — erst `cargo check` / `py_compile` /
  die Testsuite trennt „gezogen" von „gesund".

## 2. Nach dem Merge aufraeumen

1. **Fast-Forward vorher pruefen**, statt einen Merge zu bauen:
   ```bash
   git merge-base --is-ancestor origin/main <zweig> && echo FF
   ```
   Bei FF genuegt `git push origin <zweig>:main` — kein Merge-Commit, kein
   Konflikt. Ist der Zweig 68 Commits voraus, sind es 68 Zeilen Log, nicht 68
   Konflikte.
2. **Remote vor dem Push abgleichen**: `git ls-remote origin <branch>` gegen
   `git rev-parse HEAD`. Ein „behind" beim Push heisst, dass eine andere Sitzung
   gepusht hat: `git fetch` + `git rebase origin/<branch>`, danach die Tests
   erneut fahren (der Rebase kann fremden Code unter die eigene Aenderung
   schieben).
3. **Zweig loeschen ist auch bei detached HEAD sauber.** `git branch -d <zweig>`
   warnt „not yet merged to HEAD", wenn der Baum detached auf einem aelteren
   Commit steht; gemeint ist der Vergleich mit HEAD, nicht mit `main`. Der Zweig
   wird trotzdem geloescht (Inhalt steckt in `main`). Diese Warnung ist kein
   Befund.
4. **`git worktree remove --force` kann einen leeren Ordner hinterlassen.**
   `git worktree list` kennt ihn danach nicht mehr, der Ordner bleibt wenige
   Kilobyte gross stehen und `rmdir`/`Remove-Item` meldet „Device or resource
   busy" — gehalten wird er von einer EIGENEN Shell, deren Arbeitsverzeichnis
   darin lag. Nicht mit Gewalt nachfassen: das Verzeichnis verschwindet mit der
   Shell, und ein Worktree-Eintrag existiert nicht mehr.
5. **Nach dem Merge die lokalen Klone getrennt behandeln.** Ein Klon, in dem
   eine andere Sitzung arbeitet (unversionierte oder geaenderte Dateien), wird
   NICHT nachgezogen — 68 Commits unter dem offenen Editor wegzuziehen ist der
   teurere Fehler. Im Bericht nennen, welcher Klon auf welchem Commit steht und
   warum.

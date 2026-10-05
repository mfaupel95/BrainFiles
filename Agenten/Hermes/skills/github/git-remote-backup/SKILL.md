---
name: git-remote-backup
description: "Use when a repo needs a private remote, or a tree of repos/worktrees must be swept."
category: github
---

# Git-Remote-Backup

Die robocopy-Sicherungen (sichern.ps1/zweitkopie.ps1) nehmen `.git`-Ordner
generell aus (`/XD .git`): die Historie eines Repos existiert nur dort, wo ein
Remote sie spiegelt oder ein Bundle sie ablegt. Diese Routine macht aus einem
rein lokalen Repo ein privates GitHub-Repo und prueft, dass nichts
Leakbares mitgeht.

## Wann
- „remote einrichten“ / „setz den Remote auf“ fuer ein lokales Repo.
- Lokales Repo mit eigenem `.git`, dessen Historie keine zweite Kopie hat.
- Vor dem ersten Push eines Repos, das je mit Schluesseln/Tokens/Credential-
  Konfiguration zu tun hatte.
- „welche Repos haben keinen Remote?“ / „ist ueberall gepusht?“ — eine Frage
  ueber einen BAUM, nicht ueber ein Repo: dann zuerst den Flotten-Scan unten,
  danach nur die Repos anfassen, die wirklich einen Befund haben.
- „raeume die Worktrees auf“ / „es liegen 30 Zweige herum“ — Rezept und
  Fallen in `references/worktrees-und-verwaiste-zweige.md`, Inventur per
  `scripts/worktree-inventur.py`.

## Ablauf (in dieser Reihenfolge)

1. **Bestandsaufnahme:** `cd <repo>` · `git remote -v` (existiert origin
   schon? dann nicht doppelt anlegen) · `git branch --show-current` (der
   Zweig wird der Remote-Default) · `git status -sb` (fremde uncommittete
   Aenderungen liegen bei?). Verschachtelte Repos unter einem groesseren Baum
   (z. B. `Agenten/Handel/nautilus` im BrainFiles-Baum) haben eigene
   Remotes — `git remote -v` an der Wurzel zeigt sie nicht, also erst
   `find . -maxdepth 4 -name .git` laufen lassen, wenn „welche Repos haben
   keinen Remote?“ zu klaeren ist.
2. **Secret-Gate VOR jedem Push** — Rezept in
   `references/secret-scan-before-push.md`: kompletter Verlauf
   (`git log -p --all`) plus Credential-Felder getrackter Configs. Nur
   Env-Var-Namen, Platzhalter und Code, der aus der Umgebung liest, sind ok;
   echte Werte nie pushen.
3. **Anlegen + Pushen in einem Schritt:**
   `gh repo create <owner>/<name> --private --source . --push` — setzt origin
   samt upstream. Immer `--private`: auch „nur Quellcode“ traegt oft die
   persoenliche Textebene (Notizen, Steuerunterlagen).
4. **Verifizieren statt dem Push-Output glauben:**
   `git ls-remote origin -h refs/heads/<branch>` muss `git rev-parse HEAD`
   entsprechen; `gh repo view <owner>/<name> --json
   visibility,defaultBranchRef,pushedAt` muss die erwartete Sichtbarkeit und
   den erwarteten Zweig zeigen.
5. **Herkunft dokumentieren:** eine Zeile im README des Repos selbst (Historie
   liegt ausser Haus via mfaupel95/<name>), und in einer evtl. uebergeordneten
   README des Umgebungs-Repos eine alte „`.git` ist nicht gesichert“-Formulierung
   korrigieren — sonst meldet die naechste Session die geschlossene Luecke
   erneut als offen. Verwandte Memory-Aussagen („Repo hat keinen Remote“)
   sind danach veraltet und gehoeren ersetzt, nicht stehen gelassen.

## Flotten-Scan: welche Repos im Baum haben kein oder kein aktuelles Remote?

Der Einzelschritt (`git remote -v` in einem Repo) findet verschachtelte Repos
nie. Der Scan ist eine Schleife ueber `find`, und er unterscheidet vier
Befunde, die nicht verwechselt werden duerfen:

```bash
cd <wurzel>
for g in $(find . -name .git -maxdepth 7 2>/dev/null | grep -v "/.worktrees/\|/.claude/worktrees/\|probe-\|skills/.archive/\|/cache/"); do
  d=${g%/.git}
  o=$(git -C "$d" remote get-url origin 2>/dev/null)      # leer = kein origin
  n=$(git -C "$d" log --oneline @{u}..HEAD 2>/dev/null | wc -l)  # leer = kein Upstream
  [ -z "$o" ] && echo "KEIN-ORIGIN $d"
  [ -n "$o" ] && [ "${n:-0}" -gt 0 ] && echo "$n UNGEPUSHT <- $d"
done
```

Befund -> Handlung:
- **KEIN-ORIGIN, Commits vorhanden** → Secret-Gate, `gh repo create`, push.
- **KEIN-ORIGIN, ein Branch ohne Commits** (`git status` sagt „No commits yet“) →
  kein Befund. Der leere Zweig ist ein Arbeitsplatz, keine Historie.
- **UNGEPUSHT** → Secret-Gate nur ueber `git diff @{u}..HEAD`, dann pushen.
- **„behind N“** (ein Quellklon mit `upstream`) → kein Verlust, ist upstream-
  Arbeit. NICHT pushen, NICHT als Luecke melden.
- **`.git` ist eine Datei, kein Ordner** (Worktree-Link, uv-Cache) → `git`
  bricht mit „invalid gitfile format“ ab. Wegwerf, nicht reparieren, aber im
  Befund benennen, damit die naechste Session nicht erneut danach sucht.

Danach in JEDEM gefundenen Repo `git remote -v` und `gh repo view` — der Scan
sagt „hat Origin“, erst der Blick auf die URL sagt, ob es das richtige private
Repo ist.

## Fallen
- **`git log @{u}..HEAD` scheitert ohne Upstream** und schreibt den Fehler in
  die Schleife, statt eine Zahl zu liefern. Deshalb `2>/dev/null` plus
  Default `:-0`, sonst wird aus „kein Upstream“ ein ungezaehlter Befund.
- **Pfade mit Leerzeichen** (Worktrees, `Arbeitsbereich 1`) zerlegen eine
  `for`-Schleife ueber `find`-Ausgabe still. Entweder `find -print0` mit
  `read -d ''` oder jeden Kandidaten mit `git -C "$d"` statt `cd` ansprechen —
  `cd` in einer Schleife ohne Quotes ist der teure Weg (Fehlermeldung, dann
  rennt der Rest der Schleife im falschen Verzeichnis weiter).
- **Ein Secret-Gate auf den VOLLEN Verlauf ist beim Nachpushen nur noch
  teuer.** Was jetzt rausgeht, ist der Diff gegen den Upstream; steht dort
  nichts Verdächtiges, ist der Verlauf bereits einmal geprueft worden.
- **Ein einmal committeter Schluessel bleibt dauerhaft im Verlauf** —
  Entfernen heisst History-Rewrite. Deshalb das Secret-Gate VOR dem ersten
  Push, nicht danach. Auch ein privates Repo ist eine Kopie ausserhalb der
  Maschine.
- **`git add -A` in einem Repo mit fremden uncommitteten Aenderungen**
  committed fremde Arbeit mit (andere Agenten/Sessions haben in einer
  Umbrella wie BrainFiles oft Dateien liegen). Immer nur die konkrete Datei
  stagen: `git add <datei>` und committen; die fremden Aenderungen unangetastet
  lassen und melden.
- **Wenn `.git` aus der Dateisystem-Sicherung ausgenommen ist, IST der Remote
  die Ausser-Haus-Kopie der Historie** — ungepushte Commits existieren dann
  nur auf diesem Rechner. Nach jeder Aenderung committen UND pushen.

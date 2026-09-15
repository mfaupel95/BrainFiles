---
name: git-remote-backup
description: "Local git repo gets a private GitHub remote as backup."
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

## Fallen
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

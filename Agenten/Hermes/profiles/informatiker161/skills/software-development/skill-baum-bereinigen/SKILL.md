---
name: skill-baum-bereinigen
description: Skill-Duplikate im Hermes-Ladepfad verlustfrei aufloesen.
version: 1.0.0
author: Informatiker161
license: Proprietary
metadata:
  hermes:
    tags: [skills, duplikate, kollision, ladepfad, hermes]
---

# Skill-Baum bereinigen: Duplikate und Namenskollisionen

Klasse: Der Hermes-Skill-Ladepfad (`Agenten/Hermes/skills/`) haelt denselben
Skill-Namen mehrfach, weil Kopien aus verschiedenen Quellen nebeneinander liegen.
Ziel ist, trainingsdatei-frei aufzuraeumen: byte-identische Duplikate loeschen,
echte Namenskollisionen (verschiedene Inhalte unter demselben Namen) so aufloesen,
dass keine Quelle verloren geht und kein Fremd-Klon angetastet wird.

## When to Use

Wenn `skill_view(Name)` oder der Resolver "Ambiguous skill name" meldet, `hermes
skills list` unerwartete Kopien zeigt, oder eine Bereinigung des Skill-Baums
ansteht. Dieselben Namen liegen haeufig in mehreren Ebenen gleichzeitig:

- **Aktiv-/enabled-Ausgang:** Symlink/Junction nach `~/.agents/skills/` (geladene
  Version, NIE loeschen)
- **Kategorie-Original:** `Agenten/Hermes/skills/<kategorie>/<name>/` (eigene, echte
  Kopie)
- **Import-Kopie:** `Agenten/Hermes/skills/claude-code-imports/<name>/` (meist
  byte-identisches Duplikat)
- **Fremd-Repo-**Original: `Agenten/Hermes/skills/onchainos-skills/skills/<name>/`
  (Fremd-Klon, NIE anfassen, oft ANDERE Version)

## Kernregel: Kollision vs. Duplikat

- **Byte-identische Kopien stoeren den Resolver NICHT.** Er loest zur Active-Quelle
  auf, die identische Kopie faellt weg. Solche Kopien sind gefahrlos zu loeschen.
- **Eine echte Namenskollision ("Ambiguous") entsteht NUR, wenn zwei Kopien
  verschiedenen Inhalt tragen** (verschiedene Hashes/Versionsnummern). Sie bleibt
  bestehen, solange zwei verschiedene Inhalte im Ladepfad liegen.

Daraus folgt die Arbeitsaufteilung: Duplikate kann ein Agent selbst bereinigen;
echte Kollisionen brauchen eine Entscheidung, welche Version allein bleiben soll.

## Ablauf: Byte-identische Duplikate entfernen

1. **Schutzregeln lesen** (`MaxHirn/Wissen/Schutzregeln.md`).
   `Agenten/Hermes/skills/` ist Stufe 1 (Aenderung mit Ansage); der Duplikat-Anteil
   selbst ist Stufe 2 (Duplikate). Max-Entscheidung holen, bevor geloescht wird.
2. **Alle Kopien eines Namens auflisten.** `search_files (target='files')` je
   Ebene
   oben; bei
   `Fremd-Klon`-Ordnern auch die Unterordner pruefen
   (`onchainos-skills/skills/`), nicht nur `skills/`.
3. **Den enabled-Ausgang identifizieren** (`hermes skills list`; die Junction in
   `Agenten/Hermes/skills/`). Er ist Referenz fuer die Identitaetspruefung.
4. **GANZE Ordner byte-identisch pruefen, nicht nur SKILL.md** — ein Skill ist
   Verzeichnis + Referenzen/Skripte, nicht nur die Steuerdatei. Referenz je Name
   einzeln aufloesen und `diff -rq` einzeln ausfuehren; ein breiter
   `search_files` ueber
   den ganzen Baum trifft den Timeout (60 s reicht oft nicht).
5. **Loeschen als reine git-Loesungen:** `git rm -r -q <dir>...` fuer die
   identischen Kopien. Nachher `git diff --cached --numstat` pruefen: jede Zeile
   muss `0 <n>` sein (nur geloescht, nichts hinzugefuegt/modifiziert). Eigene
   Pfade stagen, nie `git add -A`.
6. **Ein Commit fuer alle Loeschungen**, Nachricht nennt die Namen und dass die
   Quelle (Junction/Fremd-Repo) unangetastet blieb.
7. **Gegenprobe:** `git ls-files` der geloeschten Pfade = 0; `diff -rq` je
   verbleibender Name gegen seine Quelle bleibt leer; `git status` der
   Fremd-Klone zeigt 0 Modifikationen.

## Fallen

- **Duplikat-Beseitigung loest eine Kollision nicht.** Verschiedene Inhalte
  (z. B. Junction v4.6.0 vs. Fremd-Repo v4.5.3) bleiben nach Entfernen der
  identischen Kopie weiter mehrdeutig. Das ist eine eigene Entscheidung
  (Quelle angleichen oder eine Version ausschliessen) — als offener Punkt an Max
  melden, das Fremd-Repo nicht einfach anfassen.
- **`skill_view` sagt nicht immer "Ambiguous".** Gleiche er des Namens nicht (weil
  er im Profil-Ladepfad dieses Profils gar nicht liegt), lautet die Antwort
  "Skill not found". Beides lesen: not found kann auch bedeuten, dass der Name in
  diesem Profil nie geladen wurde — dann liegt die Kollision in einem anderen
  Profil-Baum.
- **`hermes skill ...` ist falsch**, das Kommando heisst `hermes skills ...`
  (list/view/inspect). Der CLI startet nur mit entferntem `PYTHONHOME`/
  `PYTHONPATH` (`env -u PYTHONHOME -u PYTHONPATH ...`).
- **Ein Skill-Name kann in jedem Profil-Ordner eine eigene Kopie haben**
  (`Agenten/Hermes/profiles/<bot>/skills/...`). Diese sind pro Profil legitim und
  keine Kandidaten; der Bereinigungsbereich ist `Agenten/Hermes/skills/` selbst.

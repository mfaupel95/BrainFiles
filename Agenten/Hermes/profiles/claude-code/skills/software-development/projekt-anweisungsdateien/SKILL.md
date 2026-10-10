---
name: projekt-anweisungsdateien
description: "AGENTS.md und CLAUDE.md schreiben/pflegen."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [agents-md, claude-md, repo, onboarding, konventionen]
    related_skills: [skill-library-sync, claude-code]
---

# Projekt-Anweisungsdateien schreiben

AGENTS.md/CLAUDE.md ist die Datei, die jeder Agent bei Sitzungsbeginn lädt. Sie
trägt: was das Projekt ist, die **exakten** Befehle zum Bauen, Testen und Prüfen,
die Konventionen, die der Code tatsächlich zeigt, und die Fallen, die Zeit kosten.
Ziel unter ~100 Zeilen — jede Zeile kostet in jeder künftigen Sitzung Kontext.

## When to Use — Wann

- ein Repo bekommt AGENTS.md/CLAUDE.md
- nach einem Werkzeugwechsel im Repo (neue Skripte, geänderte CI) — dann die Befehle nachziehen
- vorher die höher liegende Regeldatei `..\rule_repo-bots.md` lesen: sie trägt Stil-,
  Betriebs- und Gelerntes-Regeln, die diese Datei nur ergänzt, nie wiederholt

## Vorgehen

1. **Werkzeugebene lesen, nicht raten.** Manifeste und Toolchain zuerst:
   `package.json` (die `scripts`!), `pyproject.toml`, `Makefile`, `Cargo.toml`,
   `go.mod`, `.github/workflows/*.yml` (die `run:`-Zeilen sind die echten Befehle),
   Lint-/Format-Configs. **Kein `package.json` heißt: kein Root-Build** — dann
   keinen erfinden. *Fertig, wenn* jeder Befehl aus einer Datei belegt ist.
2. **Befehle ausführen, bevor sie in die Datei kommen.** Jeden Befehl, der in die
   Datei soll, einmal wirklich laufen lassen und den Exit-Code nennen. Nur so
   fällt auf, was die Datei sonst falsch behauptet: ein Werkzeug, das nicht im Repo
   liegt, ein Env-Var, das der Befehl voraussetzt, ein Prüfskript, das sein
   Arbeitsverzeichnis braucht. *Fertig, wenn* jeder Befehl einen echten Lauf hat.
3. **Konventionen am Code ablesen.** Zwei bis fünf repräsentative Quelldateien und
   eine Testdatei lesen: Datei- und Funktionsbenennung, Modulaufbau (Barrel-Dateien?),
   Kommentarstil, Fehlerbehandlung. Dazu `git log --oneline -30` für das Commit-Schema.
   Nichts annehmen, was nicht im Code steht.
4. **Vorhandene Anweisungsdateien prüfen.** Liegt schon eine `CLAUDE.md`, gehört in
   `AGENTS.md` nur ein Verweis darauf statt einer zweiten Fassung derselben Regeln —
   zwei Dateien mit denselben Vorgaben driften auseinander.
5. **Schreiben.** Kurzer Titel und ein Absatz Überblick, dann flache Abschnitte:
   Layout, Bauen & Testen, Konventionen, Fallen. Keine tiefe Verschachtelung.
6. **Nachziehen.** Nach jeder Änderung an Skripten oder CI die Befehle der Datei
   gegen die Quelle prüfen.

## Was hineingehört — und was nicht

- **Befehle exakt**, so wie sie laufen: `npx -y -p typescript@5.9.3 tsc -p mods/tsconfig.json`,
  nie „die Tests laufen lassen".
- **Keine Allgemeinplätze.** „Schreib Tests für neuen Code", „halte dich an Best
  Practices" — jeder Satz, der auf jedes Repo passt, wird gestrichen.
- **Fallen nur, wenn belegt:** vorausgesetzte Env-Vars, generierte Dateien, die
  nicht von Hand geändert werden, langsame Läufe, belegte Ports. Nichts gefunden,
  dann fällt der Abschnitt weg.
- **Nichts wiederholen, was das Repo selbst lehrt** — vorhandene Anweisungsdatei,
  README, Tool-Beschreibungen.

## Fallen

- **Zwei unabhängige Schranken vor der Ablage — nicht verwechseln.**
  (1) AGENTS.md/CLAUDE.md sind geschützte Anweisungsdateien: der Schreibvorgang
  braucht eine ausdrückliche Freigabe des Nutzers. **Läuft die Freigabeanfrage ohne
  Antwort ab, ist Schweigen keine Zustimmung** — dann nicht erneut versuchen und
  nicht über `terminal`, `execute_code` oder `patch` umgehen, sondern den fertigen
  Inhalt im Chat ausgeben (oder unter anderem Dateinamen ablegen) und den Nutzer
  entscheiden lassen. Der Inhalt ist nicht verloren, nur die Ablage wartet.
  (2) Erst **nach** erteilter Freigabe zeigt sich die zweite Schranke: liegt das
  Ziel außerhalb der Schreib-Sandbox (Symlink!), scheitert das Dateiwerkzeug
  weiterhin. Der Weg „Inhalt in die Sandbox schreiben, per `terminal` an den
  Zielpfad kopieren, `md5sum` Quelle gegen Ziel“ ist dann **erlaubt und richtig** —
  er umgeht keine Freigabe, nur die Werkzeuggrenze. Eine abgelehnte Freigabe
  dagegen wird nie umgangen. Erkennen und Einzelheiten: Skill `windows-host-zugriff`.
- **Ein Repo, das nur verteilt** (Plugins, Vorlagen, Beispiele) hat oft keinen
  Build und kein Root-Manifest. Ein erfundenes `npm test` schickt jeden künftigen
  Agenten ins Leere.
- **CI-Workflows sind die verlässlichste Befehlsquelle**, aber sie laufen auf dem
  CI-Image: was dort ohne Zusatz läuft, kann lokal fehlen (global installiertes
  Werkzeug). Den Unterschied in der Datei nennen.
- **Zeilenenden des Repos treffen.** Vor dem Schreiben `.gitattributes` lesen —
  `* text=auto eol=lf` heißt LF. Ein Windows-seitiger Schreibvorgang führt sonst
  still CRLF ein. Gegenprobe am Ziel: `head -c 3 | od -An -tx1` (kein BOM),
  `grep -c $'\r'` (0).

## Nachweis

- Jeder Befehl in der Datei hat in dieser Sitzung einen echten Lauf mit Exit-Code.
- Alle genannten Pfade gibt es im Repo wirklich.
- Liegt eine zweite Anweisungsdatei vor, widerspricht sie der neuen nicht.
- Kodierung des Ziels geprüft: kein BOM, Zeilenenden wie `.gitattributes` verlangt.

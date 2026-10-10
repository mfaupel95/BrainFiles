---
name: vorarbeit-uebernehmen
description: "Unfertige Repo-Vorarbeit uebernehmen und gruen machen."
category: brainfiles
---

# Unfertige Vorarbeit uebernehmen

## Wann

Ein halbfertiger Arbeitsstand im Baum: uncommittete Aenderungen aus einer anderen
Sitzung, ein Projekt, dessen Doku „pending“ sagt, ein Build, der nicht durchgeht,
oder ein Auftrag wie „vervollstaendige X“ / „schliess das ab“. Auf diesem Rechner
arbeiten mehrere Sitzungen gleichzeitig am selben Baum — ein sauberes
`git status` ist die Ausnahme, nicht die Regel.

## Prozedur

1. **Stand am Code messen, nicht an der Doku.** Backlog-, Ticket- und
   Statusdateien zuerst lesen, dann gegen die Wirklichkeit halten: existieren die
   genannten Dateien, Module, Funktionen, Re-Exports? Ein Backlog sagt „Phasen
   2–5 pending“, waehrend der Code fertig ist — Doku altert in beide Richtungen.
   Den Ticketstatus erst dann umsetzen, wenn der Code ihn belegt.
2. **Bauen, bevor geurteilt wird.** Ein „es ist fertig“ ohne Build ist eine
   Behauptung. Bei Rust: `cargo check --workspace`; der Fehler steht im
   Traceback, nicht in der Vermutung.
3. **Die volle Kette fahren, nicht nur `check`.** `cargo fmt --all`, `cargo
   check --workspace`, `cargo clippy --workspace --all-targets -- -D warnings`,
   `cargo test --workspace`. Erst `-D warnings` deckt, was sonst durchrutscht:
   ein `assert!(x.len() >= 0)` auf einem `usize` ist immer wahr und faellt nur so
   auf. Clippy-Vorschlaege automatisch anwenden lassen:
   `cargo clippy --fix --allow-dirty --workspace --all-targets`.
4. **Den Fehler an der Ursache loesen, nicht am Symptom.** `no method named
   clone` auf einem Client heisst meist: die Rollen brauchen verschiedene
   Borrows — Stream `&mut self` (connect), Trading `&self`. Dann **eine Instanz
   je Rolle** aus denselben Zugangsdaten bauen (der Credential-Typ ist `Clone`),
   statt `Clone` auf dem Client zu erzwingen: der haelt `JoinHandle` und offene
   Verbindungen und ist bewusst nicht klonbar.
5. **Fremde Nebenprodukte aus dem Commit halten.** `git status` vollstaendig
   lesen, `??`-Eintraege einzeln ansehen, `git worktree list` befragen. Ein
   Agent-Worktree-Ordner (`.claude/`) gehoert in die Projekt-`.gitignore`, nicht
   in den Verlauf. Committen mit `git add -u` plus den neuen Pfaden einzeln —
   `git add -A` nimmt mit, was man nicht kennt.
6. **Einen gruenen Stand committen, nicht den kaputten Zwischenstand.**
   Uebernommene Arbeit und eigene Reparatur als **einen** Commit mit Begruendung:
   ein separater „Vorarbeit“-Commit, der nicht baut, bricht `git bisect` und
   schiebt den Fehler in die Historie.
7. **Fertig ist, was laeuft.** Bei einem Programm das erzeugte Artefakt aufrufen
   (`<bin> --help`, ein Trockenlauf) — „kompiliert“ ist kein Beleg fuer „laeuft“.
8. **Widerspruechliche Statusdateien mitziehen.** Eine Wachen-/Notizdatei, die
   „pending“ sagt, waehrend alles fertig ist, wird korrigiert — samt der
   Angabe, ob sie ueberhaupt einen Leser hat. Eine Datei ohne Leser als
   „angebunden“ zu bezeichnen ist die naechste falsche Aussage.

## Pitfalls

- **Ein PR-Body ist ein Schnappschuss, kein Git-Zustand.** Der Text „der Zweig ist
  noch nicht fertig" kann stehen bleiben, obwohl der PR laengst gemergt ist und
  alle Commits in master liegen. Stand immer aus Git lesen (`git merge-base
  --is-ancestor <oid> master` je Commit, `git log --oneline <basis>..master --
  <pfade>`), nie aus dem PR-Text.
- **„Vorbestehender Fehler" ist eine Behauptung, bis git log sie belegt.** Bevor
  ein Testfehler als gruenfremd/bekannt abgehakt wird: pruefen, wann der Test
  eingefuehrt wurde und ob der Aenderungsbereich die Dateien unter dem Test je
  angefasst hat (`git log --oneline <planstart>..master -- <dateien>` leer =
  wirklich fremd; `git show <planstart>^:<pfad>` = existierte schon vorher).
- **Ein Differenz-/Vortags-Test braucht Kontrolle, sonst behauptet er nichts.** Bei
  „Bericht von Hand"-Pruefungen: den echten `stand/<datum>.json` nach /tmp sichern,
  den Testvortag absichtlich veraendern (eine Position entfernen), damit eine
  Differenzzeile garantiert ist, laufen lassen, danach den echten Stand zurueck.
  Ohne Manipulation kann der zweite Lauf zeichengleich sein und der Test ist gruen,
  ohne etwas geprueft zu haben.
- **Verwaiste Worktrees nicht aufraeumen.** `locked` und `prunable` in `git
  worktree list` heissen nicht „loeschbar“: dort kann fremde, noch nicht
  gesicherte Arbeit liegen. Melden, nichts entfernen — im Ergebnis ausdruecklich
  als „nicht angefasst“ auffuehren.
- **Ein Worktree ist kein Widerspruch, sondern ein Alter.** `.claude/worktrees/<x>/`
  enthaelt oft eine aeltere Fassung derselben Datei. Vor dem Vergleich
  Zeitstempel und `git log` ansehen, statt die neuere Fassung fuer die einzige zu
  halten.
- **Erst nachsehen, wer daran arbeitet.** Vor dem Schreiben in eine Datei
  `git status --porcelain <pfad>` und, wenn vorhanden, den Index pruefen: ist sie
  schon gestaged, arbeitet eine zweite Sitzung daran. Dann nicht selbst
  schreiben, sondern den Ist-Stand nachpruefen und nur Fehlendes ergaenzen.
- **Ein gruener Testlauf gilt fuer den Stand, den er gesehen hat.** Nach dem
  letzten `cargo test` nichts mehr schreiben, ohne neu zu bauen — sonst belegt
  der Testlauf eine Fassung, die es nicht mehr gibt.
- **Nicht pushen, ohne zu fragen.** Commits liegen auf dem lokalen Zweig; ein
  Push nach `origin` ist eine eigene Entscheidung des Nutzers.

## Abgrenzung

- Arbeitsbaum im Mehrsitzungsbetrieb committen: `sichern` (Claude-Import).
- Dateien auf dem Host schreiben/ersetzen: `windows-host-zugriff`.
- Superpowers-Plan-Arbeit von Claude Code uebernehmen (ENTWURF-*/PLAN-*.md,
  Abschlusspruefung-Block, Checkboxen mit Beleg):
  `references/superpowers-plan-abschluss.md`.

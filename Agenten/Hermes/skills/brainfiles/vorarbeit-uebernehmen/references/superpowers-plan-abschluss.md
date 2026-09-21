# Superpowers-Plan abschliessen (Claude Code Arbeit uebernehmen)

Max startet Arbeit haeufig ueber Claude Code mit `/superpowers:using-superpowers`.
Das hinterlaesst im Repo: einen `ENTWURF-*.md` (Spec), einen `PLAN-*.md` mit
Checkbox-Aufgaben und einen GitHub-PR. „Mach die letzten Schritte fertig" heisst:
die offenen Checkboxen des Plans abarbeiten — meist der Abschlusspruefung-Block.

## Wo die Plaene liegen

- `Agenten/Handel/PLAN-*.md` + `ENTWURF-*.md` (versioniert; Datum im Dateinamen
  = Reihenfolge, neuester zuerst).
- Jeder Plan endet mit einem Abschlusspruefung-Block: 3-4 Checkboxen (volle
  Suite, Bedingung 4, Hand-Test, keine Laufzeitdaten im Index). Das sind die
  „letzten Schritte".
- Mehrere Plaene koennen nebeneinander liegen; der neueste traegt die offenen
  Schritte, aeltere sind abgeschlossen (auch wenn ihr PR-Body etwas anderes sagt).

## Ablauf

1. **Neuesten Plan lesen** (`search_files` auf `PLAN-*.md` in Agenten/Handel),
   Abschlusspruefung-Block + alle ungehakten `- [ ]`-Zeilen sammeln.
2. **Git-Zustand messen, nicht den PR lesen.** `gh pr view <nr>` gibt State und
   Body; der Body ist ein Schnappschuss und kann „noch nicht fertig" sagen,
   waehrend der PR laengst gemergt ist. Je Commit der PR-Liste
   `git merge-base --is-ancestor <oid> master`; sind alle in master, ist die
   Feature-Arbeit erledigt und es bleibt nur die Abschlusspruefung.
3. **Abschlusspruefung in der Reihenfolge des Plans abarbeiten.** Ueblich:
   - Volle Suite: `python -m unittest discover -s tests -p "test_*.py"` (aus
     Agenten/Handel). Ein Fehler ist erst „bekannt", wenn git log belegt, dass
     der Plan die Dateien unter dem Test nie angefasst hat (Falle im SKILL.md).
   - Bedingung 4: `python spiegelstand.py` -> „N von N byte-gleich". Eine
     Abweichung direkt nach der Suite ist der bekannte Testeffekt (Tests
     schreiben in echte Spurenordner, Q: wird im naechsten Zyklus nachgezogen) —
     zweiten Lauf abwarten; erst zwei Zyklen Abweichung sind ein Befund.
   - Bericht von Hand: Vortag kontrolliert manipulieren (naechster Punkt).
   - Index: `git status --short | grep <laufzeitordner>` muss leer sein.
4. **Kontrolle beim Vortags-Test:** echten `stand/<datum>.json` nach /tmp sichern,
   Testvortag schreiben (gleiche Erhebung, aber einer Spur eine Position
   entfernen), Bericht bauen -> „Kein Stand von gestern" muss weg sein und
   „seit gestern:" mindestens eine Zeile zeigen, danach echten Stand zurueck.
5. **Checkboxen abhaken mit Beleg.** `- [x]` setzen und unter jede Pruefung eine
   Zeile `**Beleg:** <konkretes Ergebnis>` (Zahl der Tests, byte-gleich-Befund,
   die gezeigte Differenzzeile) — der Plan wird so zur pruefbaren Doku.
6. **Nur den Plan-Pfad committen** (`git add Agenten/Handel/PLAN-*.md`) und
   pushen. Der Baum traegt fremde uncommittete Arbeit — nie `git add -A`.

## Fallen

- Ein abgehaktes Kästchen ohne Beleg verwandelt den Plan in eine Schoen­schrift.
- Plan-Commits von Claude tragen `Co-Authored-By: Claude Opus 5`; eigene
  Fortsetzungs-Commits nicht erfinden, sondern mit dem Hermes-Autor signieren.

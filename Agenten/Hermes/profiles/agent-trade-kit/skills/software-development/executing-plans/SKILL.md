---
name: executing-plans
description: Use when ein geschriebener Plan auszufuehren ist.
---

# Plaene ausfuehren

Plan laden, kritisch pruefen, alle Aufgaben ausfuehren, Abschluss melden. Wenn Subagenten verfuegbar sind (delegate_task), kann delegierte Ausfuehrung - pro Aufgabe ein frischer Subagent mit Review dazwischen - schneller sein; der Nutzer entscheidet.

## Schritt 1: Plan laden und pruefen

1. Sauberen Arbeitsbereich sicherstellen (Arbeitszweig/Worktree fuer die Arbeit, nicht main).
2. Plan-Datei vollstaendig lesen (read_file).
3. Kritisch pruefen: Fragen oder Bedenken zum Plan notieren.
4. Bei Bedenken: erst dem Nutzer vorlegen, bevor begonnen wird.
5. Ohne Bedenken: Aufgaben als Todo-Liste anlegen und abarbeiten.

## Schritt 2: Aufgaben ausfuehren

Je Aufgabe:
1. Status "in Arbeit" setzen.
2. Jeden Schritt exakt befolgen (der Plan enthaelt haeppchengrosse Schritte).
3. Die im Plan angegebenen Verifikationen ausfuehren (Tests, Checks).
4. Erst nach bestandener Verifikation als fertig markieren.

## Schritt 3: Entwicklung abschliessen

Nachdem alle Aufgaben fertig und verifiziert sind:
- Gesamttestlauf: alle Tests gruen (terminal).
- Ergebnis dem Nutzer praesentieren; Optionen anbieten (z.B. Review, Merge/Commit auf den Arbeitszweig) und die gewaehlte Option ausfuehren.
- Vor einem Merge bei Bedarf den Skill requesting-code-review anwenden.

## Stoppen und Fragen

**Sofort stoppen, wenn:**
- Ein Blocker auftritt (fehlende Abhaengigkeit, Test schlaegt fehl, Anweisung unklar)
- Der Plan kritische Luecken hat, die den Start verhindern
- Eine Anweisung nicht verstanden wird
- Verifikation wiederholt fehlschlaegt

Lieber nachfragen als raten.

## Wenn fruehere Schritte besucht werden

Zum Plan-Review (Schritt 1) zurueckkehren, wenn:
- Der Nutzer den Plan auf Basis von Feedback aendert
- Der grundlegende Ansatz ueberdacht werden muss

Blocker nicht durchdruecken - stoppen und fragen.

## Merksaetze

- Plan zuerst kritisch reviewen.
- Schrittfolge exakt einhalten.
- Verifikationen nie ueberspringen.
- Referenz-Skills laden, wenn der Plan es verlangt (skill_view).
- Bei Blockern stoppen, nicht raten.
- Nicht ohne ausdrueckliche Zustimmung des Nutzers direkt auf main/master implementieren (Arbeitszweig nutzen).

Adaptiert aus obra/superpowers (Fork mfaupel95/superpowers), 16.09.2026.

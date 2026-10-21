---
name: superpowers
description: "Use when eine neue Sitzung beginnt."
---

# Superpowers — Methodik bei Sitzungsbeginn

Standing order von Max (11.10.2026): zu Beginn JEDER neuen Session die Superpowers-Methodik anwenden. Dieser Skill ist der Einstiegspunkt; die eigentlichen Anleitungen liegen als Haus-Skills unter `software-development`.

## Ablauf bei Sitzungsbeginn

1. **Erst verstehen, dann planen** — `brainstorming` (kreative Arbeit: erst Design, dann Code) und `writing-plans` (Implementierungsplan vor dem Code, haeppchengrosse Aufgaben, keine Platzhalter).
2. **Plan ausfuehren** — `executing-plans`; mehrere unabhaengige Teile parallel ueber `dispatching-parallel-agents`.
3. **Probleme systematisch debuggen** — `systematic-debugging` (4-Phasen-Root-Cause: Ursache verstehen, bevor gefixt wird).
4. **Tests zuerst** — `test-driven-development` (RED-GREEN-REFACTOR).
5. **Fertig nur nach Verifikation** — `verification-before-completion` (erst verifizieren, dann fertig melden); vor dem Merge `requesting-code-review`.
6. **Review-Feedback annehmen** — `receiving-code-review` (pruefen, dann umsetzen).

## Wann das Ritual gilt

- **Komplexer Auftrag / neue Sitzung mit Bauauftrag:** `skill_view('superpowers')` laden, dann je Phase die passenden software-development-Skills.
- **Einfache Aufgabe / reine Auskunft:** kein Ritual noetig — die Methodik gilt trotzdem (Antwort zuerst, belegt, verifiziert, keine Floskeln).

## Quelle und Hausregel

Die Muster stammen aus obra/superpowers (Claude-Code-Skill-Sammlung, Fork mfaupel95/superpowers). Im Haus sind sie als Kategorie `software-development` integriert (z. B. `writing-plans` traegt den Vermerk "Adaptiert aus obra/superpowers").

- Der Fremd-Klon liegt NICHT mehr im Baum: `Werkstatt/superpowers` existiert nicht (Stand 11.10.2026); `docs/superpowers/` ist ein lokaler Plan-/Spec-Ordner, keine Skill-Sammlung; `profiles/.deleted/superpowers` ist ein 9-Byte-Rest.
- Fremde SKILL.md werden laut `skill-library-sync` NICHT importiert — die Haus-Skills sind die geltende Fassung.

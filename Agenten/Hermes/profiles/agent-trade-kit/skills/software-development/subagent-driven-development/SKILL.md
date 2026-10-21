---
name: subagent-driven-development
description: "Use when executing plan: fresh subagent per task."
---

# Subagent-Driven Development

Ein Implementierungsplan wird ausgefuehrt, indem pro Task ein frischer Implementierungs-Subagent dispatcht wird, danach ein Task-Review (Spec-Compliance + Code-Qualitaet), und am Schluss ein breiter Whole-Branch-Review.

## Wann einsetzen
- Implementierungsplan liegt vor (Aufgaben weitgehend unabhaengig)
- Subagenten sollen die Ausfuehrung uebernehmen, ohne Session-Kontext zu verpolluen
- Schnelle Iteration ohne Zwischenabstimmung pro Task

**Nicht einsetzen, wenn:** keine klaren Aufgaben, Aufgaben abhaengig von Zustand, oder keine Session-Persistenz verfuegbar.

## Setup und Ledger
- **Workspace pro Plan:** ein Verzeichnis unter `.sdd/<plan-name>/` anlegen - dort landen Ledger, Briefs, Reports, Review-Packages.
- **Fortschritts-Ledger:** `<workspace>/progress.md` mit Zeilen wie `Task <N>: complete`. Bei Kompaktion/Laufzeit-Verlust: Ledger + `git log` als Wahrheitsquelle.
- **Plan-Scan vor Task 1:** Aufgaben gegen die Global Constraints des Plans pruefen; Widersprueche in einer einzigen Frage dem User vortragen, bevor es losgeht.

## Modell-Auswahl
| Aufgabenart | Modell |
|---|---|
| Mechanisch (1-2 Dateien, klarer Spec) | Guenstigstes |
| Integration/Debugging (mehrere Dateien) | Standard |
| Architektur / Gesamtbranch-Review | Staerkstes |
| Fix-Runden 4-5 | Mindestens ein Tier ueber dem Implementierer |

**Immer** das Modell explizit beim Dispatch angeben. Ohne Angabe erbt es das Session-Modell (oft das teuerste), was Kosteneffizienz zerstoert.

## Task-Schleife
Alles was der Subagent ausgibt, bleibt im Session-Kontext - Erfassung von Artefakten in Dateien, nicht in Kontext. Kurze Skizzen zwischen den Aufrufen erlaubt; das Ledger traegt die Aufzeichnung.

### 1. Implementierer dispatchen
- `git rev-parse HEAD` als BASE merken (fuer spaeteren Review-Package).
- **Task-Brief erzeugen:** Aufgabentext aus dem Plan in eine Brief-Datei schreiben.
- Den Implementierer mit Brief + Report-Datei + Kontext (Global Constraints, Arbeitsverzeichnis) dispatchen.
- **Status-Handling:**
  - `DONE` -> Review-Package erzeugen, Task-Reviewer dispatchen.
  - `DONE_WITH_CONCERNS` -> Bedenken vor dem Review pruefen.
  - `NEEDS_CONTEXT` -> Fehlenden Kontext nachliefern, neu dispatchen.
  - `BLOCKED` -> Einschaetzen: (a) Kontextproblem -> Kontext liefern, (b) Reasoning noetig -> staerkeres Modell, (c) Aufgabe zu gross -> aufteilen, (d) Plan falsch -> User eskalieren. Nie dasselbe Modell ohne Aenderung nochmal versuchen.
- Fuer Rueckfragen des Implementierers klar antworten; nicht ueberstuerzen.

### 2. Task-Reviewer dispatchen
- Aufgaben: Spec-Erfuellung UND Code-Qualitaet in einem Durchlauf.
- Review-Package mit Diff (`git diff BASE..HEAD` + Stat) erzeugen und dem Reviewer uebergeben.
- **Calibration:**
  - `Critical`: Must fix vor Merge (falsches Verhalten, fehlende Spec-Anforderung)
  - `Important`: Muss geklaert werden, bevor der Task vertrauenswuerdig ist
  - `Minor`: Im Final Review triagen; kein eigener Fix-Zyklus

### 3. Fix-Schleife (max. 5 Runden pro Task)
- Runden 1-3: Implementierer weiterfuehren lassen (Kontext noch intakt).
- Runden 4-5: Frischen Implementierer mit staerkerem Modell dispatchen, Kontext aus Brief + Reports mitgeben; ein vorheriger Implementierer, der dreimal gescheitert ist, braucht frische Augen.
- Nach jeder Runde: Fix-Report erzeugen, scoped Re-Review dispatchen.
- Re-Review-Ergebnisse: `ADDRESSED` / `NOT ADDRESSED` + ggf. neue Breakage im Fix-Diff.
- **Breaker bei Runde 5:** Offene Funde selbst pruefen (Plan + Laufzeit-Kontext):
  - `Minor` / `Parked`: im Ledger ablegen (spaeteres Final Review).
  - `Load-bearing` (spaetere Aufgaben bauen drauf): `BLOCKED` an User, Fund + Plan-Text + Fix-Historie melden.

### 4. Aufgabe abschliessen
Wenn Review sauber oder offene Funde geparkt/geringt:
`Task <N>: complete (commits <base7>..<head7>, review clean)` im Ledger eintragen, naechste Aufgabe.

## Final Whole-Branch-Review
- Manuell statt Script: Merge-Basis-Commit ermitteln (`git merge-base`), Diff + Stat der gesamten Branch erzeugen.
- Auf dem staerksten Modell dispatchen; im Klartext weisen, dass Deferreds und Parkings aus dem Ledger hier erstmals vollstaendig getriagt werden.
- Ein Finder = EIN Fix-Subagent mit allen Funden; nicht ein Fixer pro Fund (Kontextkosten multiplizieren).
- Danach genau EIN scoped Re-Review; danach restliche Minor-Funde adjudyzieren und im Ledger parken.

## Workspace schliessen
Wenn Final Review sauber und Fixes gemergt:
- Plan-Workspace loeschen (`rm -rf <workspace>`). Git ist jetzt Aufzeichnung.
- Danach den naechsten Branch-Finish-Skill anwenden.

## Verhaltensmaxime
| Ausrede | Realitaet |
|---|---|
| "Close enough an Spec" | Spec-Luecken sind nicht erfuellt; Fixen oder adjudyzieren, nicht tolerieren. |
| "Ich fixe es selbst, Overhead fuer Dispatch" | Eigene Fixes verpesten den Kontext und umgehen den Review-Prozess. Implementierer weiterfuehren lassen. |
| "Noch eine Runde, dann passt es" | Jenseits von 5 Runden Strukturproblem, kein Tweaking. Adjudicate oder BLOCKED. |
| "Der Reviewer findet eh noch was" | Scoped Re-Review verifiziert den Fix; selbst evaluieren geht vor. |

---

## Prompt-Vorlagen

Die Original-Vorlagen (`implementer-prompt.md`, `task-reviewer-prompt.md`, `re-review-prompt.md`) sind als Dateien in dieser Skill-Ordnerstruktur angelegt (Ordner `templates/`), damit sie beim Dispatchen referenziert werden koennen:

- `templates/implementer-prompt.md` - fuer Dispatch 1: Report-Vertrag (DONE/DONE_WITH_CONCERNS/NEEDS_CONTEXT/BLOCKED), Self-Review-Checkliste, Fix-Report-Anhang.
- `templates/task-reviewer-prompt.md` - fuer Dispatch 2: Spec-Compliance + Qualitaet, Calibration, file:line-Beweisfuehrung.
- `templates/re-review-prompt.md` - fuer Fix-Schleifen-Re-Review: Findings verifizieren, neue Breakage im Fix-Diff pruefen.

Adaptiert aus obra/superpowers (Fork mfaupel95/superpowers), 16.09.2026.

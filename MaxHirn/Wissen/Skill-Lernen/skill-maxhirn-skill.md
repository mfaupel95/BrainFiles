---
name: skill-maxhirn-skill
description: Trockenlauf des Skills MaxHirn:skill — wann einen neuen Skill anlegen, Hausformat, drei Ablageorte; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Aus einem Anwendungsfall eine wiederholbare Aufgabe machen — ungefragt, nicht als Angebot.

**Lauf:** 2026-10-22, trockenlauf.

**Drei Ablageorte:**
| Art | Ort | Wann |
|---|---|---|
| Verfahren | `.claude/skills/<name>/SKILL.md` | Wie vorgehen, welche Fallen |
| Wissen | `Wissen/<Thema>.md` (Skill `notiz`) | Zahlen, Zustände, Befunde |
| Ausführung | `Routinen/*.ps1` / `ArchivSuche/*.py` | Ohne Nachdenken laufen soll |

**Wichtig:** Der Skill verweist (`[[Notiz]]`), wiederholt nicht. Zahlen in der Notiz, nicht im Skill.

**Prüffragen vor Anlegen:**
- In mehreren Sitzungen vorgekommen? (Einmal = Vorfall)
- Beim zweiten Mal denselben Umweg gehabt?
- Deckt ein vorhandener Skill es ab?

**Hausformat:**
```markdown
---
name: kurzwort
description: Was der Skill tut. Benutzen bei "...", "...", "...".
---
# Titel
## 1. Der Befehl, der wirklich läuft
## 2. Die Fallen, die Zeit gekostet haben
## 3. Grenzen — was der Skill nicht tut
```

**description-Regel:** Worte benutzen die Max tatsächlich sagt — inkl. schiefer Diktiervarianten. Nicht „Analyse von Systemereignissen", sondern „der PC ist abgestürzt", „warum hängt".

**Inhalt:** Befehle und Fallen, keine Erklärungen. Negativbefunde gehören rein.

**Überarbeitung-Regel:** Skill sofort korrigieren, wenn beim Arbeiten ein überholter Stand auffällt. Vor/nach jedem Umbau `(Get-Item <pfad>).Length` vergleichen.

**Ablage:** `.claude/skills/<name>/SKILL.md`, nie in `.agents/skills/` (Drift-Gefahr).

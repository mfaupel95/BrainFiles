---
name: skill-maxhirn-notiz
description: Trockenlauf des Skills MaxHirn:notiz - prüft, ob die Lernnotizen dem Hausformat einer Vault-Notiz entsprechen; Abweichungen werden benannt, keine Notiz angelegt.
metadata:
  type: reference
---

**Zweck:** Legt dauerhaftes Wissen als Markdown-Notiz im Vault unter `Wissen/` ab und verlinkt sie. Entscheidet zuerst, ob etwas dauerhaft gilt, dann, ob eine bestehende Notiz ergänzt wird.

**Wann nutzen:** Bei „merk dir das“, „schreib das auf“ oder wenn eine dauerhafte Erkenntnis entsteht.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Lernnotizen gegen das Hausformat prüfen. Keine Notiz angelegt, nichts geändert.

**Ergebnis:**

Bestand (lesend): 126 Notizen in `Wissen/Skill-Lernen/`.
- Alle 126 haben Frontmatter mit `name`, `description` und `metadata`.
- Keine hat `id`, `title`, `tags`, `created`, `updated` oder `related`. Das Hausformat verlangt diese Felder.
- Alle Dateinamen sind ohne Umlaute und Leerzeichen. Das erfüllt die Regel.

Abweichungen zum Hausformat:
1. **Frontmatter:** Das Hausformat nutzt `id`, `title`, `tags`, `created`, `updated`. Die Lernnotizen nutzen ein anderes Schema, das für Skills gedacht ist.
2. **Registry:** Die Notizen stehen in `INDEX.md` mit eigener Zeilenform (`- \`id\` — **Titel** — \`Pfad\` — Satz`). Das passt zur Registry, aber die `id` im Index und das `name`-Feld in der Notiz sind verschiedene Schlüssel.
3. **Verlinkung:** Die Notizen verlinken nicht auf `[[Dashboard]]` oder eine Elternnotiz. Sie hängen nur an der Registry. Die Regel „eine Notiz, auf die nichts verlinkt, wird nie gelesen“ trifft damit zu, obwohl die Index-Zeile sie findbar macht.

Empfehlung: Das Schema bleibt, weil die Lernnotizen eine eigene Gruppe bilden. Eine Elternnotiz `Skill-Lernen.md` mit Verweisen auf alle Lernnotizen würde die Verlinkung schließen.

**Gelernt:** Der Notiz-Skill setzt ein Schema voraus, das die Lernnotizen nicht erfüllen. Eine Gruppe mit eigenem Schema braucht eine Elternnotiz, sonst bleibt sie vom Rest des Vaults getrennt.

**Grenzen:** Prüfung nur über Feldnamen und Dateinamen. Die Inhalte der Notizen und die Verlinkung im Text sind nicht gelesen.

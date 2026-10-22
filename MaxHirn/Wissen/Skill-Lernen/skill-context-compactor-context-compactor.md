---
name: skill-context-compactor-context-compactor
description: Trockenlauf des Skills context-compactor:context-compactor — Rezept um Kontextfenster klein zu halten; lokal; kein API-Aufruf; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Kontextfenster bei langen Sitzungen klein halten — damit Geschwindigkeit und Genauigkeit erhalten bleiben.

**Wann nutzen:** Wenn Sitzung lang wird, Kontext voll läuft oder ein Themenbruch kommt.

**Lauf:** 2026-10-22, trockenlauf.

**Gelernt — Rezept:**

1. **Weniger lesen von Anfang an:** Grep/Glob vor Read; nur nötige Zeilenbereiche (offset+limit); Logs erst filtern (`tail`, `grep`); keine lockfiles/minified/node_modules lesen; breite Suche an Subagent delegieren.

2. **Wenn Sitzung lang:** Kurze Zustandszusammenfassung schreiben (Ziel, Entscheidungen, geänderte Dateien, offene Punkte, nächster Schritt) → User auf `/compact <focus>` oder `/clear` hinweisen → danach nur nötige Dateien neu lesen.

3. **Übergabe:** Zustand in `NOTES.md` oder `.claude/handoff.md` speichern, wenn neue Sitzung weiterarbeiten soll.

**Grenzen:** Kein echtes Speicher-Freigeben; Kontext ändert sich nur durch `/compact`, `/clear` oder neue Sitzung. Abgrenzung zu `compact-plan`: compact-plan = Shortcut für fertigen Befehl; context-compactor = vollständiges Rezept.

---
name: skill-superpowers-parallel-agents
description: Trockenlauf des Skills superpowers:dispatching-parallel-agents — unabhängige Probleme an parallele Subagenten delegieren; ein Agent pro Problemdomäne.
metadata:
  type: reference
---

**Zweck:** Mehrere unabhängige Fehler gleichzeitig beheben, indem je ein fokussierter Subagent pro Problemdomäne dispatcht wird. Spart Gesamtzeit erheblich.

**Wann nutzen:** ≥3 unabhängige Fehlschläge in verschiedenen Subsystemen; parallele Investigation ohne gemeinsamen Zustand.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill geladen. ~2 Seiten. Klares Muster mit Entscheidungsbaum und konkretem Beispiel.

**Gelernt — Entscheidungsbaum:**
```
Mehrere Fehlschläge?
  → Ja: Sind sie unabhängig?
       → Nein (verwandt): Ein Agent untersucht alles
       → Ja: Können sie parallel laufen?
              → Nein (geteilter Zustand): Sequenzielle Agenten
              → Ja: Parallel dispatchen
```

**Muster in 4 Schritten:**
1. **Domänen identifizieren** — nach Subsystem/Datei gruppieren
2. **Fokussierte Agent-Tasks erstellen** — Scope, Ziel, Constraints, erwartete Ausgabe
3. **Parallel dispatchen** — alle Subagent-Aufrufe in einer Antwort = parallele Ausführung
4. **Ergebnisse integrieren** — Zusammenfassungen lesen, Konflikte prüfen, Gesamttests laufen

**Guter Agent-Prompt (Vorlage):**
- Konkrete Fehlermeldungen einfügen
- Klare Constraints: "Do NOT change production code"
- Spezifische Ausgabe: "Return summary of root cause and changes"
- Keine willkürlichen Timeouts als Fix

**Häufige Fehler:**

| Falsch | Richtig |
|---|---|
| "Fix all the tests" (zu breit) | "Fix agent-tool-abort.test.ts" (fokussiert) |
| Kein Kontext | Fehlermeldungen + Testnamen einfügen |
| Keine Constraints | "Do NOT change production code" |
| Vage Ausgabe | "Return summary of root cause and changes" |

**Nicht verwenden wenn:**
- Fehler verwandt sind (einer behebt auch andere)
- Vollständiger Systemüberblick nötig
- Explorative Fehlersuche (Problem noch unklar)
- Agenten würden sich gegenseitig stören (selbe Dateien bearbeiten)

**Kritische Mechanik:** Mehrere Agent-Aufrufe in *einer Antwort* = parallel. Ein Aufruf pro Antwort = sequenziell.

**Grenzen:** Setzt voraus, dass Domänen wirklich unabhängig sind. Verwandte Ursachen → erst gemeinsam untersuchen.

---
name: skill-superpowers-test-driven-development
description: Trockenlauf des Skills superpowers:test-driven-development — Red-Green-Refactor; kein Produktionscode ohne fehlschlagenden Test; Test nach Code = Neustart; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** TDD-Disziplin sicherstellen: Test zuerst, Scheitern beobachten, minimaler Code, Refactor.

**Wann nutzen:** Neue Features, Bug-Fixes, Refactoring, Verhaltensänderungen. Ausnahmen nur mit Partner-Erlaubnis.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill geladen. ~4 Seiten. Striktestes superpowers-Regelwerk — keine Ausnahmen ohne explizite Erlaubnis.

**Gelernt — Red-Green-Refactor:**

**Kernregel:** `NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST`

| Phase | Aktion | Verifizierung |
|---|---|---|
| RED | Test schreiben, der genau ein Verhalten beschreibt | Test läuft und schlägt fehl (nicht Error) |
| Verify RED | Test ausführen, Fehler lesen | Schlägt fehl weil Feature fehlt, nicht wegen Tippfehler |
| GREEN | Minimalen Code schreiben | Test besteht, ALLE anderen Tests grün |
| Verify GREEN | Vollständige Suite laufen lassen | Suite komplett grün, keine Warnings |
| REFACTOR | Aufräumen ohne Verhalten hinzufügen | Suite bleibt grün |

**Wichtige Regeln:**
- Code vor Test geschrieben → **löschen**, nicht "als Referenz behalten"
- Test besteht sofort → testet bereits vorhandenes Verhalten, Test anpassen
- "Minimal" bedeutet: nur was nötig, kein YAGNI
- Vor "done" immer die ganze Suite, nicht nur den eigenen Test

**Guter Test:**
- Beschreibt ein Verhalten, nicht "test1"
- `"and"` im Namen → aufteilen
- Testet echten Code, nicht Mock-Verhalten
- Name benennt welche Produktionsänderung ihn brechen würde

**Rationalisierungen → Wirklichkeit:**

| Entschuldigung | Wirklichkeit |
|---|---|
| "Zu simpel zum Testen" | Simpler Code bricht auch |
| "Ich teste danach" | Tests danach sind biased — du testest was du weißt, nicht was du hättest entdecken können |
| "Schon manuell getestet" | Kein Record, nicht wiederholbar |
| "Als Referenz behalten" | Du wirst es adaptieren → Test nach Code |
| "TDD verlangsamt mich" | TDD ist der pragmatische Weg |

**Red Flags (alle → Code löschen, neu mit TDD):**
- Code vor Test
- Test besteht sofort
- "Nur dieses eine Mal"
- "Spirit, nicht Ritual"
- "Schon X Stunden investiert"

**Grenzen:** Erfordert absolute Disziplin. Throwaway-Prototypen sind Ausnahme — aber danach wegwerfen, nicht weiterbauen.

---
name: skill-superpowers-receiving-code-review
description: Trockenlauf des Skills superpowers:receiving-code-review — Code-Review-Feedback technisch verifizieren, nicht performativ bestätigen; Rückfragen vor Umsetzung; YAGNI-Check.
metadata:
  type: reference
---

**Zweck:** Code-Review-Feedback korrekt verarbeiten: verifizieren, klären, technisch pushback geben, umsetzen. Keine leeren Zustimmungen.

**Wann nutzen:** Immer wenn Review-Kommentare (von Partner oder externem Reviewer) eingehen und umgesetzt werden sollen.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill geladen. ~3 Seiten. Klares Anti-Pattern-Repertoire + Reaktionsmuster.

**Gelernt — 6-Schritt-Antwortmuster:**

```
1. READ     — Vollständiges Feedback lesen
2. UNDERSTAND — Anforderung in eigenen Worten wiedergeben (oder fragen)
3. VERIFY   — Gegen Codebase-Realität prüfen
4. EVALUATE — Technisch korrekt für DIESEN Code?
5. RESPOND  — Technische Bestätigung oder begründeter Widerspruch
6. IMPLEMENT — Ein Item, testen, nächstes
```

**Verbotene Antworten:**
- "You're absolutely right!" / "Great point!" / "Thanks for catching that!" → Verboten
- "Let me implement that now" (vor Verifizierung) → Verboten
- Jeder Dankesausdruck → Verboten

**Unklares Feedback → erst klären:**
```
Partner: "Fix items 1-6"
Unklar: 4, 5

❌ FALSCH: 1,2,3,6 umsetzen, 4,5 später fragen
✅ RICHTIG: "Verstehe 1,2,3,6. Brauche Klärung zu 4 und 5 vor der Umsetzung."
```

**YAGNI-Check (externe Reviewer):**
```
Reviewer: "Proper metrics tracking mit DB, Filter, CSV"
✅ grep → nichts ruft Endpoint auf → "Nichts nutzt das. Entfernen (YAGNI)?"
```

**Wann Widerspruch einlegen:**
- Vorschlag bricht bestehende Funktionalität
- Reviewer fehlt Kontext
- YAGNI — Feature nicht genutzt
- Konflik mit Architekturentscheidung des Partners

**Korrekte Bestätigung nach richtiger Kritik:**
```
✅ "Behoben. [kurze Beschreibung]"
✅ "Guter Fund - [spezifisches Problem]. Behoben in [Ort]."
✅ Einfach beheben und im Code zeigen
```

**Fehler-Tabelle:**

| Fehler | Korrekt |
|---|---|
| Performative Zustimmung | Anforderung formulieren oder einfach handeln |
| Blind umsetzen | Erst gegen Codebase prüfen |
| Alle auf einmal | Eins nach dem anderen, je testen |
| Reviewer als unfehlbar annehmen | Prüfen ob es Dinge bricht |
| Widerspruch vermeiden | Technische Korrektheit > Komfort |

**Grenzen:** Erfordert Zugriff auf Codebase für Verifikation. GitHub-Thread-Replies per `gh api` (inline, nicht als Top-Level-PR-Kommentar).

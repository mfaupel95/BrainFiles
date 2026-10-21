---
name: skill-agent-memory-memory-search
description: Lauf des Skills agent-memory:memory-search - sucht im Projektgedächtnis; in dieser Sitzung nicht ausführbar, weil das Werkzeug fehlt.
metadata:
  type: reference
---

**Zweck:** Sucht im Projektgedächtnis nach früheren Beobachtungen und Änderungen über das Werkzeug `memory_search`. Für Token-Statistiken gibt es `memory_stats`.

**Wann nutzen:** Wenn gefragt wird, was früher entdeckt oder geändert wurde, oder wie viele Tokens gespart wurden.

**Lauf:** 2026-10-21, nicht-ausführbar, Aufgabe: im Gedächtnis nach „Skill-Lernen“ suchen (Trockenlauf-Auftrag).

**Ergebnis:**
- Das Werkzeug `memory_search` ist in dieser Sitzung nicht geladen. Die Werkzeugsuche findet keinen Treffer.
- Die Ursache ist ein Verbindungsfehler: Die MCP-Server `MCP_DOCKER`, `plugin:compartment` und `plugin:github` sind nicht verbunden. Welcher Server das Gedächtnis bereitstellt, ist aus dieser Sitzung nicht ersichtlich.
- Es wurde nichts ersatzweise durchsucht. Eine Suche im Vault wäre eine andere Quelle und hätte den Auftrag verfälscht.

**Gelernt:** Ein Gedächtnis-Skill hängt an einem Server. Fällt der aus, ist der Skill still wertlos. Vor einem Lauf prüfen, ob das Werkzeug geladen ist, bevor der Skill aufgerufen wird.

**Grenzen:** Der Skill selbst ist nicht fehlerhaft. Er wurde nur nicht getestet. Ein neuer Lauf nach Wiederverbindung des Servers ist nötig.

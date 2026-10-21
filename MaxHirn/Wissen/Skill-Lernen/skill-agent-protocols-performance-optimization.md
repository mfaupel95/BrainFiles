---
name: skill-agent-protocols-performance-optimization
description: Messen-zuerst-Workflow für Web-Performance — Core Web Vitals, N+1-Erkennung, Bundle-Splitting, React-Re-render-Prävention, Backend-Caching.
metadata:
  type: reference
---

**Zweck:** Fünfstufiger Optimierungskreislauf (Measure→Identify→Fix→Verify→Guard) mit Entscheidungsbaum für häufige Symptome: langsames First-Load, Interaktionsverzögerung, träge API. Core-Web-Vitals-Zielwerte (LCP ≤ 2,5 s, INP ≤ 200 ms, CLS ≤ 0,1). Konkrete Gegenmuster: N+1-Queries, unbegrenzte Datenabruf, fehlende Bildoptimierung, unnötige React-Re-renders, zu großes Bundle, fehlende Caches.

**Wann nutzen:** Wenn Nutzer oder Monitoring Langsamkeit melden, vor Release mit Performance-Budget, nach Änderungen an datenbankintensiven Endpunkten oder Frontend-Bundles. Nie ohne Messproblem vorher anfangen.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill vollständig geladen. ~4 Seiten. Sehr praxisnah mit Copy-Paste-Beispielen für jedes Anti-Pattern. Entscheidungsbaum „Was ist langsam?" ist sofort nützlich.

**Gelernt:** `fetchpriority="high"` auf dem LCP-Bild — explizit dem Browser signalisieren, was wichtig ist. `React.memo`/`useMemo` überall einzusetzen ist genauso schlecht wie gar nicht. Hinweis auf Synthese (Lighthouse) + RUM (web-vitals library) als Pflicht-Kombination: eines allein reicht nicht. Performance-Budget-Enforcement via `bundlesize`/`lhci` in CI ist direkt auf Artefakt-Projekte anwendbar.

**Grenzen:** Web/React/Node-zentriert. Für Python-Backend (Handelssystem) gelten die Datenbankregeln (N+1, Paginierung, Caching), aber Frontend-Metriken und Bundle-Splitting entfallen. Für PowerShell-Skripte nicht anwendbar.

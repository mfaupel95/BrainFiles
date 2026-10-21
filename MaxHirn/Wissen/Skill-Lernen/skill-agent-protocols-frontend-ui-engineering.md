---
name: skill-agent-protocols-frontend-ui-engineering
description: Produktionsreife UI bauen — Komponentenarchitektur, Design-System-Treue, Barrierefreiheit, Responsive Design, kein "KI-Ästhetik".
metadata:
  type: reference
---

**Zweck:** Vollständiges Frontend-Engineering-Protokoll: Komponentenstruktur (Colocate, Container/Presentation-Trennung), State-Management-Auswahl, Design-System-Treue ohne KI-Ästhetik, WCAG-2.1-AA-Barrierefreiheit, Responsive Design und Lade-/Fehlerzustände.

**Wann nutzen:** Neue UI-Komponenten, bestehende Oberflächen ändern, responsive Layouts, Interaktivität hinzufügen.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill vollständig geladen. Besonders nützlich: die Tabelle "AI Default vs. Production Quality" benennt konkrete Muster die vermieden werden sollen (Lila-Farbgebung, übermäßige Rundungen, Shadow-lastiges Design, Lorem-ipsum-Platzhalter). Optimistic-Updates-Muster mit React Query vollständig beschrieben.

**Gelernt:** Die KI-Ästhetik-Tabelle ist direkt auf Artifact-Arbeit anwendbar — beim nächsten Artifact-Build prüfen, ob die Farben aus dem Projekt-Token-System stammen und keine Gradients-als-Design-Ersatz verwendet werden. State-Management-Hierarchie (useState → lift → Context → URL → Server State → Global Store) ist eine gute Entscheidungshilfe.

**Grenzen:** React/TypeScript/Tailwind-spezifisch. Für reine HTML/CSS-Artifacts ohne Framework gilt das Barrierefreiheits- und Spacing-Wissen, aber die React-Patterns nicht direkt.

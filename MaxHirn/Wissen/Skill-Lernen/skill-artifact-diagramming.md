---
name: skill-artifact-diagramming
description: Trockenlauf des Skills artifact-diagramming — wann ein Diagramm nötig ist, was es zeigen muss, Inline-SVG-Mechanik für HTML-Artifacts; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Diagramme nur zeichnen, wenn sie Mechanismen zeigen, die Prosa nicht kann. Inline SVG ohne Bibliotheken.

**Wann nutzen:** Vor jedem Diagramm in einem HTML-Artifact.

**Lauf:** 2026-10-22, trockenlauf.

**Grundregel:** Ein Diagramm verdient seinen Platz, wenn ein kalter Leser den Mechanismus sieht, den er sonst aus Prosa zusammensetzen müsste. Wenn ein Satz es schneller sagt — Satz schreiben.

**Was zeichnen:**
- Den Mechanismus, nicht seinen Namen (ein Box "cache" sagt weniger als der Pfad durch ihn)
- Beim Optionsvergleich: die Differenz, nicht eine Liste — zwei Architekturen nebeneinander, der eine Pfeil der sich ändert
- So viel Komplexität, wie die Entscheidung braucht — keine erzwungene Vereinfachung, kein Systemkatalog
- Pfeile beschriften: `writes`, `invalidates`, `polls every 30s` — unbeschriftete Pfeile sind "irgendwie verbunden"

**Inline-SVG-Mechanik (HTML-Artifacts):**
- `viewBox="0 0 W H"`, CSS: `max-width: 100%; height: auto` — Größe nach Inhalt, nicht nach Preset
- Striche, Text, Pfeilspitzen in `currentColor` → funktioniert in beiden Themes
- Eine Literal-Farbe nur für das eine Element, das Bedeutung trägt (die empfohlene Option)
- Pfeilspitzen: `<defs><marker>` mit `marker-end="url(#arrow)"` ODER `<polygon>` — nie Image
- Text: ca. 11–13px, `text-anchor` für Ausrichtung, kurze Labels; Erklärungen in `<figcaption>`
- Raster: gemeinsame Baselines und gleichmäßige Abstände — macht handgezeichnete Diagramme lesbar
- Struktur: `<figure>` + `<figcaption>` + `<svg role="img" aria-label="...">`
- Kein `<script>`, `<style>`, `<foreignObject>` im SVG; IDs im selben Fragment referenzieren
- Weite Flows: links→rechts; gestapelte Schichten: oben→unten

**Faustregel Komplexität:** Eine-Hop-Frage = drei Boxen. Eine Migration die Writes durch eine Queue umleitet = Queue + Writer + Reader + Reihenfolge-Pfeil.

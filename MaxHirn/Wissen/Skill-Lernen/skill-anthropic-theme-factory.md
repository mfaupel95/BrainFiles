---
name: skill-anthropic-theme-factory
description: Trockenlauf des Skills anthropic-skills:theme-factory — kuratierte Sammlung von 10 Font/Farb-Themes für Slide Decks; zeigt PDF-Showcase, lässt auswählen, wendet an.
metadata:
  type: reference
---

**Zweck:** Professionelles Styling für Slide Decks (und andere Artefakte). 10 fertige Themes, jedes mit Farbpalette + Font-Paarung. Benutzerdefinierte Themes möglich.

**Wann nutzen:** Wenn ein Deck konsistent gestylt werden soll und ein fertiges Theme passt. Ergänzt `anthropic-skills:pptx` (das die Mechanik macht) um die Design-Entscheidung.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill geladen. Kurz (~1 Seite). Klarer Prozess, kein Overhead.

**Gelernt — Prozess:**
1. `theme-showcase.pdf` anzeigen (nicht verändern)
2. Nutzer wählt Theme
3. Theme-Datei aus `themes/` lesen
4. Farben + Fonts konsistent im Deck anwenden

**10 verfügbare Themes:**
- Ocean Depths — maritim, beruhigend
- Sunset Boulevard — warm, lebendig
- Forest Canopy — Erdtöne, geerdet
- Modern Minimalist — Graustufen, clean
- Golden Hour — herbstlich, warm
- Arctic Frost — kühl, winterlich
- Desert Rose — gedämpfte, elegante Töne
- Tech Innovation — kühn, modern
- Botanical Garden — frisch, organisch
- Midnight Galaxy — dramatisch, kosmisch

**Custom Theme:** Wenn keines passt → aus Beschreibung neues Theme generieren, zeigen, bestätigen lassen, anwenden.

**Grenzen:** Nur Styling-Entscheidung — die eigentliche .pptx-Erzeugung übernimmt `anthropic-skills:pptx`. `theme-showcase.pdf` muss im Skill-Verzeichnis liegen.

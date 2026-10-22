---
name: skill-data-validate-data
description: Trockenlauf des Skills data:validate-data — Analyse-Validierung vor Stakeholder-Weitergabe; QA-Checkliste, Fallstrick-Katalog, Konfidenz-Bewertung; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Eine fertige Analyse auf Fehler, Methodik-Probleme und Verzerrungen prüfen, bevor sie geteilt wird.

**Wann nutzen:** `validate-data <analyse>` — immer vor hochkarätigen Präsentationen oder Entscheidungen.

**Lauf:** 2026-10-22, trockenlauf.

**8-Schritt-Workflow:**
1. Methodik + Annahmen prüfen (richtiger Datensatz? richtige Frage?)
2. QA-Checkliste durchgehen
3. Analytische Fallstricke prüfen
4. Berechnungen stichprobenartig verifizieren
5. Visualisierungen bewerten (Nullachse, Skalierung)
6. Narrative + Schlussfolgerungen validieren
7. Verbesserungen vorschlagen
8. Konfidenz-Bewertung ausgeben

**Konfidenz-Stufen:** Bereit zum Teilen | Mit Vorbehalt teilen | Überarbeitung nötig.

**7 häufigste Fallstricke:**
1. **Join Explosion** — viele-zu-viele Join bläht Zählungen auf → Zeilenanzahl vor/nach Join prüfen
2. **Survivorship Bias** — nur heutige Entitäten analysiert, Churned fehlt
3. **Unvollständiger Zeitraum** — Teil-Periode vs. volle Periode verglichen
4. **Denominator-Verschiebung** — Definition des Nenners ändert sich zwischen Perioden
5. **Average of Averages** — Gruppen-Durchschnitte mitteln ohne Gewichtung → falsch
6. **Timezone-Mismatch** — Zeitstempel verschiedener Systeme in verschiedenen Zeitzonen
7. **Selection Bias** — Segmente durch Outcome definiert statt durch Vorab-Kriterien

**Red Flags:** >50% Änderung ohne klare Ursache; exakte Rundungszahlen; 0% oder 100% Raten; identische Werte über Perioden.

**Grenzen:** Kann nur prüfen, was in der Analyse sichtbar ist — unvollständige Dokumentation erschwert Validierung.

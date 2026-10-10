---
id: 20261007-papier-experiment-zyklus
title: Papier-Experiment-Zyklus
tags: [handel, verbesserer, implementierung]
created: 2026-10-07
updated: 2026-10-07
related: [20261006-verbesserer-architektur, 20261007-spur-bewertung, 20261007-verbesserer-ausloeser]
summary: Wie Verbesserungsvorschläge auf Papier getestet, im Journal festgehalten und bei Erfolg in die Live-Spur übernommen werden.
---

# Papier-Experiment-Zyklus

> Summary: Wie Verbesserungsvorschläge auf Papier getestet, im Journal festgehalten und bei Erfolg in die Live-Spur übernommen werden.

## Kontext
Kein Vorschlag des Verbesserers geht direkt in den Live-Betrieb. Jede Änderung
läuft zuerst im Papier-Modus, damit Fehler keinen realen Schaden anrichten.

## Details

### Phasen des Zyklus

```
Auslöser
  → Bewertung (spur-bewertung.md)
  → Vorschlag generieren
  → Papier-Lauf starten
  → Journal auswerten
  → Übernahme-Entscheidung
  → [optional] Live übernehmen
```

### Phase 1: Vorschlag generieren
- Verbesserer liest Journal der Spur und schlägt max. **1–2 Parameteränderungen** vor (nicht mehr)
- Änderungen sind konkret: z.B. „Stop-Abstand von 1,2 % auf 1,5 %" oder „EMA-Periode von 20 auf 25"
- Vorschlag wird mit Begründung ins Journal geschrieben, bevor der Papier-Lauf beginnt

### Phase 2: Papier-Lauf
- Dauer: **3–7 Tage** (mindestens 20 abgeschlossene Paper-Trades)
- Modi: `--papier` (Spur 1: Scanner-Papier; Spur 2: `xperp/handeln.py --papier`)
- Journal-Eintrag je Trade: Zeitstempel, Signal, Einstieg, Ausstieg, Ergebnis, aktive Parameter
- Papier-Lauf und Live-Lauf laufen **parallel** — Spur bleibt untouched

### Phase 3: Auswertung
- Gleiche Metriken wie [Spur-Bewertung](spur-bewertung.md): Win Rate, Profit-Faktor, Drawdown
- Vergleich: Papier-Ergebnis vs. Live-Ergebnis im selben Zeitfenster
- Entscheidungsregel: Papier muss in **mindestens 2 von 3** Primärmetriken besser sein

### Phase 4: Übernahme
- **Ja:** Parameter in Wachen-Datei schreiben, alten Stand als Kommentar erhalten
  (`// vorher: stop_abstand=0.012`), Abkühlphase starten
- **Nein:** Vorschlag verwerfen, nächsten Regelauslöser abwarten
- **Unsicher (ein Metrik besser, ein Metrik schlechter):** Papier-Lauf um 3 Tage verlängern

### Journal-Format (Mindestfelder)
```json
{
  "ts": "2026-10-07T08:00:00Z",
  "spur": "spur1",
  "modus": "papier",
  "parameter_version": "v2-stop-1.5pct",
  "signal": "long",
  "einstieg": 62100,
  "ausstieg": 62850,
  "ergebnis_pct": 1.21,
  "stop_ausgeloest": false
}
```

## Related
- [Verbesserer-Auslöser](verbesserer-ausloeser.md) — Voraussetzung: was den Zyklus startet.
- [Spur-Bewertung](spur-bewertung.md) — Voraussetzung: Metriken für Auswertung und Übernahme-Entscheidung.
- [Verbesserer-Architektur](verbesserer-architektur.md) — Überblick: wo dieser Zyklus im Gesamtbild liegt.

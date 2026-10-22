---
name: skill-superpowers-diagnosing
description: Trockenlauf des Skills superpowers:diagnosing-superpowers — Sitzungsfehler diagnostizieren: Transkript lesen, Befund mit Zeilenzitat belegen, Bericht schreiben.
metadata:
  type: reference
---

**Zweck:** Fehler oder unerwartetes Verhalten in einer Claude-Code-Sitzung systematisch untersuchen. Liest Transkripte, belegt Befunde mit Zeilen-Zitaten, schreibt Bericht. Diagnose: ja. Änderungen an superpowers vorschlagen: nein.

**Wann nutzen:** Wenn eine Sitzung zu lange dauerte, unnötige Arbeit wiederholte, den Plan ignorierte oder ein Skill nicht auslöste.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill geladen. ~3 Seiten. Investigativer Prozess mit strikten Zitier- und Redaktionsregeln.

**Gelernt — 7-Schritt-Workflow:**

| Schritt | Inhalt | Bedingung |
|---|---|---|
| 1. Problem-Intake | Wer/Was/Wann/Erwartung/Beobachtung klären | Immer |
| 2. Lokalisieren | Sitzungspfade auflösen, Workspace anlegen unter `~/.superpowers/diagnosing-superpowers/<session-id>/` | Immer |
| 3. Triage | 7 Analyst-Subagenten parallel, je eine Dimension | Immer |
| 4. Bericht | `templates/report.md` füllen, speichern, anzeigen | Immer |
| 5. GitHub-Issues | Offene/geschlossene Issues suchen, ggf. erstellen | Nur wenn §7 "möglich/wahrscheinlich" oder User fragt |
| 6. Export/Bundle | Bereinigtes Paket erstellen | Nur auf explizite Anfrage |
| 7. Ähnliche Sitzungen | Signatur aus Befunden → Kandidaten scannen | Nur auf Anfrage |

**7 Analyse-Dimensionen (parallel):**
- `skill-timeline.md` — Skill-Auslöse-Zeitleiste
- `plan-adherence.md` — Plan-Einhaltung
- `repeated-work.md` — Wiederholte Aktionen
- `stumbles.md` — Stolperstellen
- `quality-evidence.md` — Qualitätsnachweise
- `request-conflicts.md` — Anfragen-Konflikte
- `cost-and-time.md` — Kosten und Zeit

**Eiserne Regeln:**
- **Jeder Befund braucht `pfad:zeile`** — ohne Zitat kein Befund
- **Alle Zahlen aus Transkript oder ausgeführtem Befehl** — nie aus Erinnerung
- **Nur lesend** — Session-Dateien nie ändern, verschieben, löschen
- **Nur menschliche Prompts** — Hook-Ausgaben, System-Reminders, Tool-Ergebnisse sind keine Nutzerwörter
- **Intake vor Analyse** — nichts in Schritten 2–7 startet ohne vollständige Problemaussage

**Bundle-Redaktionsstufen (nur auf Anfrage):**
- skeleton: keine Tool-Ergebnis-Bodies
- evidence: Bodies nur für zitierte Ereignisse
- full: alles

**Grenzen:** Erfordert Zugriff auf lokale Sitzungsdateien (`~/.claude/projects/`). Kann keine superpowers-Änderungen vorschlagen — meldet nur Befunde.

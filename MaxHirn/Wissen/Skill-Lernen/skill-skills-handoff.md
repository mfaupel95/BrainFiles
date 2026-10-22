---
name: skill-skills-handoff
description: Trockenlauf des Skills skills:handoff — Kontext-Übergabe vor /clear: strukturiertes handoff.md schreiben; auto (80/85/90/95%) und manuell (/handoff).
metadata:
  type: reference
---

**Zweck:** Kontext strukturiert dokumentieren, bevor `/clear` oder Kontext-Komprimierung ihn zerstört. Ausgabe: `.claude/handoff.md` mit fixem Format.

**Wann nutzen:** `/handoff` manuell vor `/clear`; oder automatisch via Stop-Hook bei 80/85/90/95% Kontext-Auslastung.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill geladen. ~1,5 Seiten. Klar strukturiert, sofort einsetzbar.

**Gelernt — Dateiformat:**

```markdown
# Handoff: <laufende Aufgabe in einer Zeile>

## Nächster Schritt
<eine Aktion, mit Dateipfad und Funktionsname>

## Erledigt
- <verifiziert Abgeschlossenes + wie geprüft>

## Noch offen
- <in Reihenfolge>

## Wichtiges
- Entscheidung: <was + warum, auch verworfene Alternativen>
- Sackgasse: <was versucht wurde + warum gescheitert>
- Berührte Dateien: `pfad/datei.ts:120`
```

**Schlüsselprinzipien:**
- Leere Abschnitte komplett weglassen
- Kein Code-Volltext — nur Pfad + Zeilennummer
- Kein Gesprächs-Replay — nur Ergebnis + Begründung
- Unbestätigtes als "ungeprüft" kennzeichnen
- Immer eine einzige Datei: überschreibt vorherige

**Mechanismus:**
- Trigger: `hooks/handoff.py` mit `THRESHOLD=0.8`, `REWRITE_STEP=0.05`
- SessionStart-Hook liest `.claude/handoff.md` → schiebt es als `systemMessage` → benennt um in `.claude/handoff.md.done`
- Erster Titel (`# Handoff: ...`) wird als 1-Zeilen-Benachrichtigung angezeigt
- Kontext-Limit: 1M Token für moderne Modelle (Sonnet 4.6, Opus 5, Fable 5 etc.), 200k für Haiku und ältere 4.5-Generation; via `HANDOFF_CONTEXT_LIMIT` in settings.json überschreibbar

**Empfehlung:** `.claude/handoff.md` und `.claude/handoff.tok` in `.gitignore` aufnehmen.

**Grenzen:** Hook muss konfiguriert sein (`hooks/handoff.py`). Ohne Hook nur manuell per `/handoff` nutzbar.

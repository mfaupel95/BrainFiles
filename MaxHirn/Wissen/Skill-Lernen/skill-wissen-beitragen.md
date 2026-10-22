---
name: skill-wissen-beitragen
description: Trockenlauf des Skills wissen-beitragen — Wohin mit Ergebnissen (gbrain vs Wissen/ vs Wiki/); gbrain aus Claude Code aufrufen; CRLF-Pflichten; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Ergebnisse richtig ablegen — gbrain, Wissen/, Wiki/ oder TASKS.md.

**Lauf:** 2026-10-22, trockenlauf.

**Wo gehört was hin:**
| Art | Ort |
|---|---|
| Einzelne belegte Aussage (Zahl, Messwert) | **gbrain** mit `--entity` |
| Zusammenhang, Projektstand, Begründung | **`Wissen/`** — vorhandene Notiz bevorzugen |
| Falle oder Merksatz aus dem Betrieb | **`Wiki/`** (Skill `wiki-pflege`) |
| Offener Punkt | `Archiv/TASKS.md` |

**gbrain aus Claude Code (nicht im PATH):**
```bash
MSYS_NO_PATHCONV=1 wsl.exe -d archlinux /workspace/gbrain/bin/gbrain recall --grep <einzelwort>
```
- `MSYS_NO_PATHCONV=1` immer mitsenden (ohne → Pfadfehler, Exit 127)
- Schreiben: Text per `Write` in Scratchpad, `.sh`-Datei daneben, `gbrain remember "$TEXT" --provenance "<quelle, datum>" --entity <entität>`
- Gegenprobe: `recall --grep <ASCII-Stichwort>` — muss Zeichen für Zeichen stimmen

**Wissen/ schreiben:**
1. `Schutzregeln.md` lesen; Bereichsprüfung: `python Agenten/Werkzeuge/bereiche.py --aufrufer wissen --pfad <pfad>`
2. Erst INDEX.md durchsuchen, dann gezielt per `Edit` (nie Rewrite — CRLF)
3. Neue Notiz: INDEX.md-Eintrag + Verlinkung im selben Schritt
4. Zahlen mit Skript-Pfad als Quelle
5. Pflege-Commit auf `master` mit `BRAINFILES_BEREICH=wissen`, nicht pushen

**Falls gbrain streikt:**
- `PGLite WASM runtime` → erst `pglite-repair --dry-run`, dann nur nach Ja von Max `--yes`
- Nie `reinit-pglite` (löscht alle Fakten)
- Bei Ausfall: trotzdem ins Wissen schreiben, gbrain-Teil offen melden

**Grenzen:** Kein Ersatz für Claude Auto-Memory oder Hermes-`memory`. Kurzlebiges → `Werkstatt/`.

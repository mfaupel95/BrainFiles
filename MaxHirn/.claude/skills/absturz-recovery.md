---
name: absturz-recovery
description: Nach PC-Absturz — Arbeitsbaum prüfen und unvollendete Aufgaben fertigmachen
tags: [betrieb, notfall]
---

# PC-Absturz-Recovery

**Automatische Routine nach Absturz.** Immer als erste Aktion ausführen.

## Schritte

1. **Arbeitsbaum prüfen** — `git status` muss „clean" sein. Falls nicht:
   - Uncommitted Changes ansehen → in separater Sitzung sichern (Skill `sichern` mit `--autor="Absturz-Wiederherstellung"`)
   - Beschädigte Dateien (Binary-Junk, 0xFF-Sequenzen) finden
   - `ArchivSuche/.venv` und `index.db` prüfen (`.venv` ist an seinen absoluten Pfad gebunden)

2. **Laufende TASKS prüfen** (`Archiv/TASKS.md`):
   - `[~]` (in Arbeit) → auf Vollständigkeit prüfen
   - `[?]` und `[!]` (blockiert/wartet) → ob Blockade noch besteht
   - Neue Tasks: Kann es unvollendete Git-Operationen geben? (rename, mv mit `.venv`)

3. **Spezifisch nach Umbenennungen suchen:**
   - `.gitignore` auf neue Pfade prüfen
   - Dokumentation (CLAUDE.md-Dateien) gegen Dateisystem abgleichen
   - Ein Task-Eintrag unter "Umbenennung unvollständig" deutet auf Pfad-Mismatch

4. **Python-Virtuelle Umgebungen testen** (`.venv`):
   ```
   Archiv/ArchivSuche/.venv\Scripts\python.exe --version
   ```
   Wenn fehlgeschlagen: `python -m venv Archiv/ArchivSuche/.venv` neu erzeugen + `pip install -r requirements.txt`

5. **Archiv-Index prüfen:**
   ```
   cd Archiv/ArchivSuche
   .venv\Scripts\python.exe search_cli.py "test"  # Funktioniert der Index?
   ```
   Keine Treffer bei bekannten Dateien → `index.py` reindexieren

6. **Git-Integrität prüfen** (falls `.git` großen Dateien enthält):
   ```
   git fsck --full
   ```

## Nach der Fertigstellung

- Alle Änderungen committen mit Autor-Tag: `--author="PC-Absturz Recovery <recovery@local>"`
- Task-Status in TASKS.md aktualisieren
- Diese Routine selbst in die Memory-Docs eintragen (falls neu)

## Verknüpfte Aufgaben

- [[T-004]] — Kernel Power 41 (Stromverlust-Absturz): weiterhin offen
- [[T-015]] — Sicherungslaufwerk `G:` Ziel prüfen
- [[T-016]] — Umbenennung Claude → Archiv fertigmachen

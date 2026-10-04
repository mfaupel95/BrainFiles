---
id: 20260910-optimierungen-umgesetzt
title: 'Optimierungen — Umgesetzt (2026-09-10)'
tags: [betrieb, system]
created: 2026-09-10
updated: 2026-09-11
related: [20260911-off-site-backup, 20260830-routinen]
summary: 'Drei umgesetzte Verbesserungen für Datensicherheit und Wartbarkeit, allen voran die monatliche Off-Site-Kopie auf USB-SSD.'
---

# Optimierungen — Umgesetzt (2026-09-10)

Drei kritische Verbesserungen für Datensicherheit und Wartbarkeit:

## 1. Off-Site USB Backup

**Problem:** Drei lokale Platten (C:, G:, O:) — alle im selben Raum. Simultaner Ausfall (PSU-Fehler, Brand, Diebstahl) = Totalverlust.

**Lösung:** Monatliche kalte Kopie auf externe USB-SSD, off-site gelagert.

**Was gemacht:**
- `sichern-aussenhaus.ps1` — Trockenlauf → Echtkopie → MD5-Verifizierung
- Atomare Übergabe (`.tmp` → aktuell), alte Versionen bleiben als `.alt-YYYYMMDD`
- Vollständiges Protokoll in `Agenten/Routinen/logs/aussenhaus-letzter-lauf.log`
- Automatische Konfigurieren: `[[Off-Site-Backup|Wissen/Off-Site-Backup.md]]`

**Nächste Schritte:**
1. USB 3.0 SSD kaufen (500 GB, NTFS)
2. Festem Laufwerksbuchstaben zuweisen (z.B. D:)
3. Testlauf: `powershell -ExecutionPolicy Bypass -File Agenten\sichern-aussenhaus.ps1 -Laufwerk D -NurPruefen`
4. Echtkopie: `… -Laufwerk D` (ohne `-NurPruefen`)
5. Optional: geplante Aufgabe für monatliche Erinnerung (siehe `Off-Site-Backup.md`)

---

## 2. MCP-Konfiguration-Manifest

**Problem:** 11 MCP-Server doppelt konfiguriert — `claude_desktop_config.json` (Claude) + `Hermes/config.yaml` (Hermes). Änderungen an einem Ort, Vergessen am anderen = eine Agent läuft mit veraltetem Code.

**Lösung:** Zentrales `MCP-Manifest.json` als Single Source of Truth.

**Was gemacht:**
- `Agenten/MCP-Manifest.json` — alle 11 Server mit Pfaden, Argumenten, Variablen
- `mcp-sync-check.ps1` — verifiziert Claude & Hermes, prüft Serverprogramme, findet Drift
- Integration in `systempruefung.ps1` — läuft täglich morgens, meldet Drift als "Zu entscheiden"

**Nächste Schritte:**
1. Manifest selbst ist die Dokumentation — dort Änderungen machen (nicht in beiden Agent-Configs)
2. Manuell nachziehen:
   - `claude_desktop_config.json`: bei geschlossenem Claude, von Hand oder per Skript
   - `Hermes/config.yaml`: dito für Hermes
3. Testen: `powershell -ExecutionPolicy Bypass -File Agenten\mcp-sync-check.ps1`
4. Täglich: `systempruefung.ps1` meldet unter "Zu entscheiden", wenn Drift entdeckt

**Längerfristiger Ausblick:** Der nächste Schritt wäre ein Skript `mcp-update-configs.ps1`, das Manifest → Claude + Hermes bidirektional syncen kann (aber nur mit geschlossenen Agenten).

---

## 3. Tägliche MCP-Drift-Prüfung

**Integration in bestehende Routine:**
- `systempruefung.ps1` läuft täglich morgens (geplante Aufgabe)
- **Neu**: MCP-Sync-Check als "Prüfung 0" — Ausgabe im Protokoll
- Bedient sich bei `mcp-sync-check.ps1`

**Protokolle:**
- `logs/systempruefung-letzter-lauf.md` — Strukturierter Bericht (liest der SessionStart-Hook)
- `logs/systempruefung-JJJJ-MM-TT.log` — Rohprotokoll dieses Laufs

---

## Dateien angelegt/verändert

| Datei | Art | Zweck |
|---|---|---|
| `Agenten/sichern-aussenhaus.ps1` | NEU | Monatliche Off-Site USB Backup |
| `Agenten/mcp-sync-check.ps1` | NEU | Verifizierung Claude/Hermes in Sync |
| `Agenten/MCP-Manifest.json` | NEU | Single Source of Truth für MCP-Server |
| `MaxHirn/Wissen/Off-Site-Backup.md` | NEU | Dokumentation + Setup-Guide |
| `Agenten/Routinen/systempruefung.ps1` | GEÄNDERT | MCP-Drift-Prüfung integriert |

---

## Was funktioniert jetzt besser

### Datensicherheit
- **Vorher:** Drei lokale Platten, alle im selben Raum (Einzelfehlerpunkt)
- **Nachher:** + monatliche Off-Site-Kopie (geografisch getrennt)
- **Schutz:** Gegen simultane Ausfälle aller lokalen Platten

### Wartbarkeit
- **Vorher:** MCP-Änderungen an zwei Stellen von Hand
- **Nachher:** Zentrales Manifest, tägliche automatische Drift-Erkennung
- **Kosten:** Einmal syncen statt zweimal ändern + blind auf Konsistenz hoffen

### Fehler-Früherkennung
- **Vorher:** MCP-Drift = stillschweigend (Agent läuft mit altem Code)
- **Nachher:** Täglich in Systemprüfung erkannt, im `systempruefung-letzter-lauf.md` gemeldet

---

## Noch offen (später)

1. **Archive Indexing Atomicity** — `index.py` sollte atomic schreiben (`.tmp` → `.db`)
2. **Hermes Environment Isolation** — Prüfen, ob mcp-memory die Umgebungsvariablen sieht
3. **Path Traversal Guards** — `O:\Modelle` Junction-Sicherheit hardcoden (statt Guard)
4. **Bidirektionale Manifest-Sync** — Skript, das Claude + Hermes automatisch syncen kann
5. **CLAUDE.md Drift-Detektion** — Automatische Prüfung auf Bit-for-Bit-Gleichheit

---

## Zusammenfassung

- **Off-Site Backup**: Schutz gegen Totalverlust — beginne diese Woche mit Test
- **MCP Manifest**: Entfernt Fehlerquelle — lagere Änderungen dort ab
- **Daily Check**: Erkennt Drift automatisch — liest `systempruefung-letzter-lauf.md`

Alle drei sind selbsterklärend dokumentiert — Skripte haben `param([switch]$NurPruefen)` zum Testen ohne Änderungen.

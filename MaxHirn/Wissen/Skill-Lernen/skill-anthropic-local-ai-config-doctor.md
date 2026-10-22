---
name: skill-anthropic-local-ai-config-doctor
description: Trockenlauf des Skills anthropic-skills:local-ai-config-doctor — 8-Schritte-Workflow zur Diagnose und Reparatur lokaler KI-Tool-Konfigurationen (Hermes, Ollama, Claude CLI, MCP-Server); Kernprinzip: effektive Konfiguration bestimmen bevor diagnostiziert wird.
metadata:
  type: reference
---

**Zweck:** Lokale KI-Konfigurationen (Hermes, Ollama, LLM-Tools, MCP-Server) systematisch reparieren. Kernfehler: an der falschen Instanz arbeiten oder einer Diagnosemeldung aus dem falschen Kontext glauben.

**Wann nutzen:** "Hilf mir X einzurichten", "MCP-Server sieht meine Config nicht", "Modell nicht gefunden", "Tool funktioniert nach Update nicht mehr".

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill vollständig geladen. ~12 Seiten. Einer der praktischsten und direktest anwendbarsten Skills für das eigene System (Hermes, MCP-Server, Ollama). Sehr konkrete Beispiele aus der Praxis.

**Gelernt — 8 Schritte:**
1. **Zielobjekt lokalisieren** — Prozesse, Konfig-Verzeichnisse, Zeitstempel (zuletzt geändert = aktiv), Version; `scripts/inventory.ps1` macht das in einem Aufruf
2. **Effektive Konfiguration bestimmen** — Das ist der Kern. Profile erben oder ersetzen die Hauptconfig? GUI und CLI können auseinanderlaufen. Empirisch: dieselbe Abfrage zweimal in beiden Kontexten. Konkretes Beispiel: `HERMES_HOME=<root> hermes mcp list` → 11 Server; `HERMES_HOME=<root>/profiles/max hermes mcp list` → "No MCP servers configured"
3. **Tool-eigene Diagnose nutzen** — `hermes doctor`, `ollama list`, `claude doctor`; im richtigen Kontext ausführen, Hinweise als Hypothese, nicht als Befund nehmen
4. **Deklariert vs. real prüfen** — Pfade, Modellart (Embedding-Modell im Chat-Slot = unsichtbarer Fehler), Credentials, Key-Referenzen (`${env:FOO}` wird nur aus echten Prozessvariablen aufgelöst, nicht aus `.env`). Security-Check: was startet da eigentlich? Kostenfrage: MoA, mehrfache Reference-Modelle vervielfachen Token-Kosten
4. **Selbst reparieren vs. vorlegen** — Eindeutige, umkehrbare Fixes direkt erledigen; strukturelle Entscheidungen, Löschungen, Mehrkosten vorlegen. Faustregel: "Wenn ich die Änderung nicht ohne 'vermutlich' begründen kann → vorlegen"
6. **Reparieren** — Backup zuerst (`config.yaml.bak.20260830_172140`), chirurgisch editieren (kein YAML-Roundtrip), Reihenfolge: Config → Umgebungsvariablen → Installationen; laufende App schreibt beim Beenden zurück
7. **Verifizieren — Meldungen nicht blind glauben** — Prüffunktion im Quelltext direkt aufrufen wenn sie nach Reparatur immer noch fehlschlägt. Praxisbeispiel: `browser (system dependency not met)` + Chromium-Install-Vorschlag → direkte Prüfung zeigte `_is_browser_use_cli_mode() → True`, Tools waren absichtlich ausgeblendet, 300-MB-Install unnötig
8. **Abschlussbericht** — Änderungstabelle vorher→nachher, Backup-Dateiname + fertiger Rückspielbefehl, was der Nutzer selbst tun muss, eigene Fehlspuren benennen, offene Punkte kategorisiert

**Grenzen:** Braucht Shell-Zugriff (desktop-commander, windows-mcp) — kein Cloud-Container. Referenzdateien `references/windows-shell.md`, `references/tool-map.md` und `scripts/inventory.ps1` liegen im Skill-Verzeichnis. Skill ist hochgradig praxisrelevant für dieses System.

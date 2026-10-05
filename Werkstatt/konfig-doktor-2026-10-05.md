# Konfig-Doktor 2026-10-05 16:57

Wurzel: `C:\Users\faupe\Documents\BrainFiles`. Rein lesender Lauf; Reparaturen nur nach Freigabe.

## Zusammenfassung

| Stufe | Anzahl |
|---|---|
| KRITISCH | 0 |
| WARNUNG | 0 |
| HINWEIS | 4 |
| UNKLAR | 0 |

## HINWEIS (4)

| # | Befund | Belegt durch | Status | Vorschlag |
|---|---|---|---|---|
| 1 | 1 .txt-Zwilling(e) von Dateien | ./proxy.yaml.txt | Vermutung | Ist die .txt eine Kopie (z. B. zum Anhaengen an eine Mail)? Dann in Teilprojekt B entfernen |
| 2 | Ordner unter Agenten/, die wie Wurzelordner heissen | Agenten/Werkstatt (0 Dateien auf Ebene 1) | Vermutung | Inhalt ansehen: gehoert er in die gleichnamige Wurzel? Zusammenfuehren in Teilprojekt B |
| 3 | 11 Altkopien (.bak/.orig/.corrupt/.old/.vor-; davon 2 unsicher) | ./.gitignore.bak-20261002; ./.gitignore.bak-entfernt; ./AGENTS.md.bak-20261001; ./AGENTS.md.bak-20261004; ./CLAUDE.md.bak-20261001; ./CLAUDE.md.bak-20261004; Agenten/MCP-Manifest.json.vor-projectatlas-20260913-1536; Agenten/Hermes/auth.json.corrupt; Agenten/Hermes/config.yaml.vor-delegation-20260929_225456; Agenten/Hermes/models_dev_cache.json.corrupt; Agenten/Hermes/spawn-ledger.json.corrupt | Vermutung | Aufraeumen ist Teilprojekt B; vorher Inhalt gegen die aktuelle Datei pruefen |
| 4 | 1 Skriptpaar(e) mit fast gleichem Namen | Agenten/sichern-aussenhaus.ps1 ~ sichern-ausser-haus.ps1 | Vermutung | Pruefen, welches aufgerufen wird (Aufrufer suchen), dann das andere in Teilprojekt B entfernen |

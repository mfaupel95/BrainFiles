# Konfig-Doktor 2026-10-11 03:10

Wurzel: `C:\Users\faupe\Documents\BrainFiles`. Rein lesender Lauf; Reparaturen nur nach Freigabe.

## Zusammenfassung

| Stufe | Anzahl |
|---|---|
| KRITISCH | 0 |
| WARNUNG | 4 |
| HINWEIS | 7 |
| UNKLAR | 1 |

## WARNUNG (4)

| # | Befund | Belegt durch | Status | Vorschlag |
|---|---|---|---|---|
| 1 | Server 'projectatlas': Pfad loest nur gegen die Wurzel auf, nicht gegen cwd | Betroffen: command: Agenten\Werkzeuge\projectatlas\bin\projectatlas.exe. Test-Path negativ unter cwd C:\Users\faupe\Documents\BrainFiles\Agenten\Werkzeuge\projectatlas, positiv unter Wurzel C:\Users\faupe\Documents\BrainFiles | gesichert | Der Server startet in cwd; Pfad im Manifest relativ zu cwd schreiben oder absolut machen |
| 2 | Server 'projectatlas': Datei hinter Flag oder Nicht-*** fehlt | Fehlend: args: C:\Users\faupe\Documents\BrainFiles\Werkstatt\omnitrade\.projectatlas\config.toml. Geprueft gegen cwd C:\Users\faupe\Documents\BrainFiles\Agenten\Werkzeuge\projectatlas und Wurzel C:\Users\faupe\Documents\BrainFiles; Test-Path negativ | Vermutung | Pruefen, ob die Datei optional ist oder vom Server selbst erzeugt wird; sonst Manifest korrigieren |
| 3 | Server 'pdf-vault': Datei hinter Flag oder Nicht-*** fehlt | Fehlend: args: MaxHirn\Claude. Geprueft gegen cwd C:\Users\faupe\Documents\BrainFiles\Agenten\MCP-Server\ant.dir.gh.anthropic.pdf-server-mcp und Wurzel C:\Users\faupe\Documents\BrainFiles; Test-Path negativ | Vermutung | Pruefen, ob die Datei optional ist oder vom Server selbst erzeugt wird; sonst Manifest korrigieren |
| 4 | Platz/Commit: WARN Laufwerk C: nur 59.2 GB frei (Warnschwelle 60 GB). | plattenplatz-pruefen.ps1 -OhneOrdner, Ausgabezeile: WARN Laufwerk C: nur 59.2 GB frei (Warnschwelle 60 GB). | gesichert | Platz schaffen bzw. Commit-Reserve pruefen (Auslagerungsdatei, Docker/WSL-Speicher); Aufraeumen nur nach Freigabe |

## HINWEIS (7)

| # | Befund | Belegt durch | Status | Vorschlag |
|---|---|---|---|---|
| 5 | 1 Server starten Programme ausserhalb der Wurzel | kraken-papier -> O:\Werkstatt\Repos\kraken-cli\target\release\kraken.exe | gesichert | Nur zur Kenntnis: Pfade ausserhalb der Wurzel ueberleben einen Umzug auf die SSD nicht |
| 6 | 2 Profil(e) ohne eigene config.yaml | .deleted, .sicherung | gesichert | Pruefen, ob das Profil die Hauptconfig erbt (empirisch, nicht annehmen) |
| 7 | 20 Fehlerzeilen in den letzten 200 Zeilen von errors.log | Letzte: 2026-10-11 03:07:45,783 ERROR tools.checkpoint_manager: Git command failed: C:\Users\faupe\Documents\BrainFiles\Agenten\Hermes\tools\git-2.53.0+3-win32-x64\cmd\ | gesichert | Log lesen, bevor spekuliert wird |
| 8 | 1 .corrupt-Reste im Hermes-Ordner | spawn-ledger.json.corrupt (2026-10-10) | gesichert | Ursache der Beschaedigung klaeren, danach aufraeumen (Teilprojekt B) |
| 9 | 1 .txt-Zwilling(e) von Dateien | ./proxy.yaml.txt | Vermutung | Ist die .txt eine Kopie (z. B. zum Anhaengen an eine Mail)? Dann in Teilprojekt B entfernen |
| 10 | 1 Skriptpaar(e) mit fast gleichem Namen | Agenten/Handel/tracking.py ~ trailing.py | Vermutung | Pruefen, welches aufgerufen wird (Aufrufer suchen), dann das andere in Teilprojekt B entfernen |
| 11 | 6 Altkopien (.bak/.orig/.corrupt/.old/.vor-; davon 3 unsicher) | Agenten/MCP-Manifest.json.vor-okx-demo-20261010; Agenten/MCP-Manifest.json.vor-projectatlas-20260913-1536; Agenten/Hermes/.env.bak-20261010; Agenten/Hermes/.env.bak-20261010-2; Agenten/Hermes/config.yaml.vor-delegation-20260929_225456; Agenten/Hermes/spawn-ledger.json.corrupt | Vermutung | Aufraeumen ist Teilprojekt B; vorher Inhalt gegen die aktuelle Datei pruefen |

## Nicht pruefbar (UNKLAR) (1)

- **hermes doctor antwortet nicht im Zeitlimit** - Abbruch nach 15 s (Modul-Limit 20 s). Zur Entscheidung fehlt: hermes doctor von Hand ausfuehren

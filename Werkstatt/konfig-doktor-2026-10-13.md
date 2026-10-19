# Konfig-Doktor 2026-10-13 02:10

Wurzel: `C:\Users\faupe\Documents\BrainFiles`. Rein lesender Lauf; Reparaturen nur nach Freigabe.

## Zusammenfassung

| Stufe | Anzahl |
|---|---|
| KRITISCH | 1 |
| WARNUNG | 4 |
| HINWEIS | 8 |
| UNKLAR | 1 |

## KRITISCH (1)

| # | Befund | Belegt durch | Status | Vorschlag |
|---|---|---|---|---|
| 1 | Platz/Commit: WARN Commit: nur 1.8 GB frei von 103.7 GB (Warnschwelle 10 GB) - Auslagerungsdatei pruefen. | plattenplatz-pruefen.ps1 -OhneOrdner, Ausgabezeile: WARN Commit: nur 1.8 GB frei von 103.7 GB (Warnschwelle 10 GB) - Auslagerungsdatei pruefen. | gesichert | Platz schaffen bzw. Commit-Reserve pruefen (Auslagerungsdatei, Docker/WSL-Speicher); Aufraeumen nur nach Freigabe |

## WARNUNG (4)

| # | Befund | Belegt durch | Status | Vorschlag |
|---|---|---|---|---|
| 2 | Server 'ziplime': Pfad loest nur gegen die Wurzel auf, nicht gegen cwd | Betroffen: command: Werkstatt\ziplime\.venv\Scripts\python.exe. Test-Path negativ unter cwd C:\Users\faupe\Documents\BrainFiles\Werkstatt\ziplime, positiv unter Wurzel C:\Users\faupe\Documents\BrainFiles | gesichert | Der Server startet in cwd; Pfad im Manifest relativ zu cwd schreiben oder absolut machen |
| 3 | Server 'pdf-vault': Datei hinter Flag oder Nicht-*** fehlt | Fehlend: args: MaxHirn\Claude. Geprueft gegen cwd C:\Users\faupe\Documents\BrainFiles\Agenten\MCP-Server\ant.dir.gh.anthropic.pdf-server-mcp und Wurzel C:\Users\faupe\Documents\BrainFiles; Test-Path negativ | Vermutung | Pruefen, ob die Datei optional ist oder vom Server selbst erzeugt wird; sonst Manifest korrigieren |
| 4 | Server 'projectatlas': Datei hinter Flag oder Nicht-*** fehlt | Fehlend: args: C:\Users\faupe\Documents\BrainFiles\Werkstatt\omnitrade\.projectatlas\projectatlas.db; args: C:\Users\faupe\Documents\BrainFiles\Werkstatt\omnitrade\.projectatlas\config.toml. Geprueft gegen cwd C:\Users\faupe\Documents\BrainFiles\Agenten\Werkzeuge\projectatlas und Wurzel C:\Users\faupe\Documents\BrainFiles; Test-Path negativ | Vermutung | Pruefen, ob die Datei optional ist oder vom Server selbst erzeugt wird; sonst Manifest korrigieren |
| 5 | Server 'projectatlas': Pfad loest nur gegen die Wurzel auf, nicht gegen cwd | Betroffen: command: Agenten\Werkzeuge\projectatlas\bin\projectatlas.exe. Test-Path negativ unter cwd C:\Users\faupe\Documents\BrainFiles\Agenten\Werkzeuge\projectatlas, positiv unter Wurzel C:\Users\faupe\Documents\BrainFiles | gesichert | Der Server startet in cwd; Pfad im Manifest relativ zu cwd schreiben oder absolut machen |

## HINWEIS (8)

| # | Befund | Belegt durch | Status | Vorschlag |
|---|---|---|---|---|
| 6 | 1 Server starten Programme ausserhalb der Wurzel | kraken-papier -> O:\Werkstatt\kraken-cli\target\release\kraken.exe | gesichert | Nur zur Kenntnis: Pfade ausserhalb der Wurzel ueberleben einen Umzug auf die SSD nicht |
| 7 | mcp-sync-check.ps1 meldet Abweichung | Exit 1: WARN Konfiguration neuer als Manifest: C:\Users\faupe\Documents\BrainFiles\Agenten\Hermes\config.yaml (2026-10-12 22:33) - vermutlich App-Ueberschreibung, Manifest pruefen / FEHLER archiv: im Manifest aktiv (beide), fehlt bei Claude / FEHLER kraken: im Manifest aktiv (beide), fehlt bei Claude | gesichert | Ausgabe des Skripts lesen; Abgleich Manifest und Client-Configs |
| 8 | 14 Fehlerzeilen in den letzten 200 Zeilen von errors.log | Letzte: 2026-10-13 02:02:52,031 WARNING [20261011_042648_100458cc] agent.tool_executor: Tool terminal returned error (4.12s): {"output": "", "exit_code": 4294967295, "e | gesichert | Log lesen, bevor spekuliert wird |
| 9 | HERMES_HOME zeigt nicht auf Agenten/Hermes | HERMES_HOME=C:\Users\faupe\Documents\BrainFiles\Agenten\Hermes\profiles\bots, erwartet C:\Users\faupe\Documents\BrainFiles\Agenten\Hermes | gesichert | Pruefen, ob das gewollt ist (zweite Instanz?) |
| 10 | 1 Zweig(e) bereits in master gemergt | claude/ensemble | gesichert | Zweigregel: nach dem Merge Zweig und Arbeitsbaum loeschen (git branch -d, git worktree remove) - nur nach Freigabe |
| 11 | 1 Skriptpaar(e) mit fast gleichem Namen | Agenten/Handel/tracking.py ~ trailing.py | Vermutung | Pruefen, welches aufgerufen wird (Aufrufer suchen), dann das andere in Teilprojekt B entfernen |
| 12 | 5 Altkopien (.bak/.orig/.corrupt/.old/.vor-; davon 3 unsicher) | Agenten/MCP-Manifest.json.vor-okx-demo-20261010; Agenten/MCP-Manifest.json.vor-projectatlas-20260913-1536; Agenten/Hermes/config.yaml.vor-delegation-20260929_225456; Agenten/Hermes/spawn-ledger.json.corrupt; Agenten/Handel/moondev_dauerlauf.py.bak-20261012 | Vermutung | Aufraeumen ist Teilprojekt B; vorher Inhalt gegen die aktuelle Datei pruefen |
| 13 | 1 unbekannte Eintraege in der Wurzel | Python (Ordner, 0 Tage alt) | Vermutung | Gehoert es in einen der vier Hauptordner? Sonst nach Werkstatt/ - oder in die Erlaubt-Liste von Modul wurzel aufnehmen |

## Nicht pruefbar (UNKLAR) (1)

- **hermes doctor antwortet nicht im Zeitlimit** - Abbruch nach 15 s (Modul-Limit 20 s). Zur Entscheidung fehlt: hermes doctor von Hand ausfuehren

# Sicherungsreparatur — geprüfter Zwischenstand

## Geändert
- Vier Sicherungsskripte prüfen O:/Archiv vor Scan oder Schreibzugriff und beenden sich bei fehlender Quelle mit Code 2.
- Verschwindet das Archiv nach der Vorprüfung, wird nun ein Fehler statt Erfolg gemeldet.
- sichern-aussenhaus.ps1 verweigert vorhandene Teilkopien, statt sie rekursiv zu löschen; die frühe Sperre erhält auch das vorherige Log.
- Originalfassungen: Agenten/sichern*.ps1.bak-20260911-193930. Jede Sicherung wurde vor Änderung per SHA-256 verglichen. Keine Commits, keine Änderung fremder Arbeitsstände.

## Verifiziert
- Regressionstests in Werkstatt/test-backup-preflight.ps1: fehlende Quelle, Quelle nach Vorprüfung verschwunden, Teilkopie vorhanden. Vorher rot, danach grün. Die isolierten Tests ersetzen Dateisystem-Abfragen und führen die echten AST-Zweige aus; keine Vollsicherung.
- Echter Aufruf: sichern-aussenhaus.ps1 -Laufwerk Q meldet PARTIAL_BACKUP_EXISTS und Exitcode 2. Vorheriges Log per Hash unverändert; Teilkopie weiterhin vorhanden.
- Werkstatt/restore-pruefung.ps1: drei ausgewählte Textdateien aus J: und dieselben aus Q:-Teilkopie in neue Testordner kopiert; sechs SHA-256-Vergleiche erfolgreich. Ergebnis: Werkstatt/restore-pruefung-20260911-194250/ergebnis.json. Kein Beweis für das gesamte Archiv.
- Separate Git-Sicherung: Q:/BrainFiles-Git-Historie-20260911-194220/BrainFiles.bundle. git bundle verify erfolgreich; Test-Klon unter Werkstatt/git-restore-test-20260911-194220.git; git fsck --full Exitcode 0 und HEAD identisch. Hinweis auf einen dangling commit, kein Integritätsfehler. Bundle enthält referenzierte Historie, nicht uncommittierte Arbeit und nicht beliebige Reflog-Reste.
- Alle vier Skripte syntaktisch geprüft; git diff --check auf den bearbeiteten versionierten Skripten bestanden. Gesamtbaum hat fremde Whitespace-Befunde in Agenten/Bus/README.md, nicht verändert.

## Offen und bewusst nicht behauptet
- Kein erfolgreicher neuer Vollsicherungslauf. Hauptsicherungs-Abbruchursache nicht abschließend geklärt. Der numerische Fehlercode ist hexadezimal C000013A; die vorhandene Behauptung STATUS_CONFLICT_WITH_LOCK im Skript ist nicht belegt.
- Q: ist exFAT mit vorhandenen Musikbeständen, nicht neu formatieren. Aktueller Verschlüsselungsstatus konnte wegen fehlender Rechte nicht abgefragt werden. 7-Zip vorhanden; kein Verschlüsselungskennwort angefordert oder erzeugt.
- Außenhausskript benötigt vor echtem Einsatz weitere Arbeit: validierte Quellmenge, Ausschlüsse vor Traversierung, Kapazitätsprüfung, konsistente SQLite-Snapshots, Hashprüfung vor Übergabe, zielbezogene Sperre, Verschlüsselung. Die Schutzpatches machen es nicht zur fertigen Backup-Lösung.
- Bestehende BrainFiles-Backup.tmp nicht gelöscht, überschrieben oder als fertig markiert. Benutzerordner und Medienbestand noch nicht vollständig geschützt.
- Abos, Kostenlimits, Modelle und Skills-Import unverändert. 40 EUR Gesamtbudget bleibt Planungsgrenze, keine eingerichtete technische Ausgabensperre.

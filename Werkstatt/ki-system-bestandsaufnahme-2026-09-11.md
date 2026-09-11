# KI-System — geprüfter Zwischenstand und Ausbauvorschlag
Stand: 2026-09-11. Bestandsaufnahme, keine abgeschlossene Integration oder Wiederherstellungsprüfung.
## Zielbild
BrainFiles bleibt die Steuerzentrale: MaxHirn für Wissen, Agenten für geprüfte Laufzeiten, Modelle für reproduzierbare Gewichte, Werkstatt für isolierte Arbeit. Benutzerdateien werden über einen lokalen, zugriffsbeschränkten Katalog erschlossen, nicht komplett in den Vault verschoben.
## Verifizierte Befunde
- Inventur: `ki-system-inventur.py`; strukturierter Bestand: `ki-system-inventur.json`. Beide relativ zu dieser Datei. Begrenzte bekannte Quellen, kein vollständiger Scan des Benutzerordners.
- Aktives Hermes-Profil max: 124 SKILL.md auf Datenträger, nicht gleichbedeutend mit 124 aktiv nutzbaren Fähigkeiten. Vault-Quelle: 22 Skills; alle vorhanden. videoanalyse weicht nur durch WebFetch → web_extract ab. Sprache existiert ebenfalls, Hashabweichung noch zu prüfen.
- Installierte Claude-Plugins enthalten 72 Skill-Dateien mit 54 unterschiedlichen Ordnernamen. Namensgleichheit ist kein Inhaltsgleichheitsbeweis. Unter anderem Superpowers, Revolut X und Financial Services; nicht pauschal importiert.
- Python erfasst unter globalen .claude/skills und .agents/skills jeweils 9 Skill-Dateien; PowerShell hatte unter .claude/skills nur 2 geliefert. Link-/Traversierungsunterschiede vor dem Import klären.
- 37 unmittelbare Repo-/Projektkandidaten in Documents/GitHub, MaxHirn/skills und Werkstatt/Repos erfasst. Die ersten beiden Bäume sind echte getrennte Ordner, keine Junctions. Viele README-Hashes stimmen überein, cli weicht ab; keine Löschfreigabe ableitbar.
- Hauptsicherung vom 10.09.: Aufgabenresultat 3221225786, Log endet beim Zugangsdaten-Dateinamensscan; kein erfolgreicher Abschluss nachgewiesen.
- Außenhauslauf vom 10.09. auf Q: endet laut Log bei Echtkopie/Quelle. Nur BrainFiles-Backup.tmp vorhanden, BrainFiles-Backup fehlt. Keine fertige Außenhauskopie nachgewiesen; vorhandene andere Sicherungen auf Q: nicht untersucht.
- Zweitkopie nach J: meldet im Log Robocopy-Code 3 und ENDE ok. Deckt Archiv/Dokumente und Bilder ab, nicht Musik, Videos und Posteingang. Noch kein Restore-Test und keine Integritätsprüfung der Medien durchgeführt.
- In Haupt-/Zweitsicherung kann fehlendes O:/Archiv auf Code 4 gesetzt und danach als erfolgreich bezeichnet werden. Beide schließen .git aus: die Git-Historie ist durch diese Kopien nicht gesichert.
- Außenhausskript überspringt fehlendes Archiv mit Erfolgscode, prüft erst nach Übergabe nur Stichproben aus BrainFiles und löscht vorhandenes .tmp rekursiv. Nicht ungeprüft erneut starten.
- Git meldet unter anderem gelöschte Werkstatt-Regeln und Pläne; keine Wiederherstellung oder Commits vorgenommen. Unterschiedliche Sitzungen könnten parallel arbeiten.
- RTX 3060 Ti: 8192 MiB VRAM. Ollama erreichbar; Modellnamen qwen35-8k:latest und gemma-e4b-8k:latest vorhanden. Keine Inferenz-/Tool-Calling-Leistung gemessen. Bei Portprüfung kein Listener auf 20128/20129; dokumentierter OmniRoute-Betrieb aktuell nicht bestätigt.
- Docker-Terminal läuft unter /root, Windows-Pfad unter /mnt/c fehlt. Hostzugriff über Desktop Commander funktioniert. Keine breiten Host-Mounts eingerichtet.
## Empfohlene Reihenfolge
1. Datensicherung reparieren und mit Restore in separaten Testordner beweisen; versionierte, verschlüsselte Außenhauskopie, Git-Historie, eigene Repo-Änderungen und wertvolle Benutzerprofile einbeziehen. Fehlende Pflichtquelle muss Fehler sein. Laufendes SQLite konsistent sichern.
2. Fähigkeitenregister: Quelle/Revision, Lizenz, Kosten, benötigte Programme, Freigaben und letzter Funktionstest. Eigene Skills führend; Plugin-Fähigkeiten dedupliziert und nur bei Bedarf laden. Keine automatischen Upstream-Überschreibungen.
3. Vorhandenes Ollama zuerst mit kleinen, ungefährlichen Aufgaben testen. Skripte für deterministische Arbeit, lokales Modell für Entwürfe/Klassifikation, Cloud für schwierige Analyse und Prüfung. Cloud nur mit erlaubten Daten und festem Budget; kein stiller kostenpflichtiger Fallback.
4. Benutzerordner über Allowlist indexieren: ausgewählte Dokumente/Notizen/Medienmetadaten. Zugangsdaten, Browserprofile und AppData-Caches nicht indexieren. Originale bleiben am Ort, Treffer zeigen Quelle; Schreibrechte nur im Arbeitsbereich.
5. Repos nach konkretem Nutzen anbinden: Chromaprint/AcoustID für Audio; Context7 für Dokumentation; Superpowers für Entwicklung; Finanzskills getrennt von Live-Handel. Unsloth/Fine-Tuning und zusätzliche Router erst nach messbarem Bedarf.
## Offene Entscheidungen
- Ist die SanDisk Q: als abziehbare Außenhaus-Sicherung vorgesehen und verfügbar? Sind die Strom-/RAM-Abstürze behoben?
- Welche bestehenden KI-Abos und welches zusätzliche monatliche API-Budget dürfen genutzt werden? Bis zur Antwort kein neuer kostenpflichtiger Dienst.
- Darf die erste Umsetzungsphase Sicherung und Wiederherstellbarkeit priorisieren, bevor weitere Skills aktiviert werden?

Nachprüfung: Die unterschiedliche globale Skill-Zählung ist erklärt: Die sieben OKX-Skill-Ordner unter .claude/skills sind Junctions auf .agents/skills; odysseus und sprache sind echte Ordner. Nicht als zusätzliche eigenständige Quellen importieren. Bericht und Inventur-JSON wurden zurückgelesen; JSON ist parsebar. Der Skill-Abgleich wurde im aktiven Profil nach gesicherter Originalfassung um Profil-/Plugin-/Junction-Prüfung ergänzt.

## Rückmeldung von Max
- Q: ist als abziehbare Sicherungsplatte bestätigt.
- Die plötzlichen Abschaltungen sind laut Max behoben; der frühere Instabilitätsbefund ist kein aktueller bestätigter Blocker mehr. Keine eigene Hardware-Neudiagnose durchgeführt.
- Vorhandene Anbieter: Claude Code, Nous Portal und OpenRouter. Gewünscht: Claude künftig über Nous bezahlen. AI Horde wird erwogen, ist noch nicht zur Einrichtung freigegeben.
- Monatliches Zusatzbudget bleibt offen. Keine Abos gekündigt, Abrechnung umgestellt oder kostenpflichtigen Fallbacks eingerichtet.
- Offizielle Nous-Dokumentation bestätigt Claude-Modelle mit Abrechnung über Portal. Das ist nicht automatisch eine Übertragung des Claude-Code-Abos oder ein Nachweis, dass dessen CLI bereits über Nous funktioniert.
- Empfehlung: lokale Skripte/Ollama zuerst, Nous als primärer Cloud-Zugang, OpenRouter nur bewusst ausgewählt. AI Horde ausschließlich für unkritische öffentliche Inhalte erwägen, nicht als Verarbeitungspfad für den privaten Vault.

## Budgetentscheidung
Max bestätigt 40 EUR als gesamtes monatliches KI-Budget einschließlich bestehender Abos und zusätzlicher API-Nutzung, nicht als Zusatzbudget. Tatsächliche Tarifkosten, Steuern und Abrechnungszeiträume sind noch zu prüfen. Bis zur Klärung keine neuen kostenpflichtigen Automatismen, Aufladungen oder Fallbacks. Ziel: lokale Verarbeitung als Standard und Cloud-Nutzung nur aus dem nach Fixkosten verbleibenden Budget. Diese Dokumentation ist keine technisch eingerichtete Ausgabensperre.

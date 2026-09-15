---
name: local-ai-config-doctor
description: Diagnose and repair the configuration of locally installed AI tooling on the user's own computer — Hermes, Claude Desktop, MCP servers, Ollama, Codex/Claude CLI, agent gateways, and similar. Use this whenever the user asks to set up, configure, check, fix, or "einrichten" any of these ("hilf mir X einzurichten", "warum sieht Claude meine Tools nicht", "mein MCP-Server taucht nicht auf", "Modell wird nicht gefunden", "set up my agent", "fix my mcp config"), and also when a request that sounds like a fresh install turns out to be an existing installation that needs fixing. The routine finds the effective config first, verifies every declared path/key/model against reality, repairs the unambiguous defects itself and puts structural decisions to the user with evidence, always with backups and a stated way back.
---

# Lokale KI-Konfiguration prüfen und reparieren

## Wofür dieser Skill da ist

Anfragen wie „hilf mir X einzurichten" sind fast nie Neuinstallationen. In der Praxis existiert die Software bereits, läuft sogar, und das Problem liegt in der Konfiguration: eine Referenz zeigt ins Leere, ein Key wird nicht aufgelöst, ein Profil überschreibt die gepflegte Config, ein Modell ist gar nicht installiert.

Der teuerste Fehler bei solchen Aufgaben ist, an der falschen Instanz zu arbeiten oder einer Diagnosemeldung zu glauben, die aus einem anderen Kontext stammt. Deshalb steht hier die Frage „welche Konfiguration gilt tatsächlich?" **vor** jeder Diagnose, und jeder Befund braucht einen Beleg.

Sprache: Antworte auf Deutsch, wenn der Nutzer Deutsch schreibt. Fachbegriffe bleiben englisch.

## Voraussetzung: Zugriff auf den Rechner

Diese Arbeit findet auf dem Rechner des Nutzers statt, nicht im Cloud-Container. Nutzbare Wege, in dieser Reihenfolge:

1. `mcp__remote-devices__device_bash` — Shell auf dem Gerät, beschränkt auf verbundene Ordner
2. Ein lokaler MCP-Server mit Shell-Zugriff (`desktop-commander`: `start_process`, `read_file`, `edit_block`, `start_search`) — greift oft auch außerhalb der verbundenen Ordner und ist damit für Config-Ordner unter `AppData`/`~/.config` der praktikablere Weg
3. `windows-mcp` (`PowerShell`) als Alternative unter Windows

Bevor du sagst, du kämest an eine Datei nicht heran, probiere den zweiten Weg. Wenn gar kein Zugriff besteht, sag das klar und bitte um Dateianhänge — rate nicht.

Lies für die Shell-Mechanik unter Windows `references/windows-shell.md`. Dort steht, warum verschachtelte Anführungszeichen in Inline-Befehlen regelmäßig scheitern und wie du das umgehst; das spart mehrere Fehlversuche pro Sitzung.

## Schritt 1 — Zielobjekt lokalisieren

Erst herausfinden, was überhaupt installiert ist und ob es läuft. Ein Namenstreffer allein reicht nicht: Setup-Dateien in `Downloads`, Reste alter Installationen und die aktive Installation sehen in einer Dateisuche gleich aus.

Sammle in einem Durchgang:

- Dateien und Ordner mit dem Produktnamen (begrenzte Tiefe, sonst dauert es ewig)
- laufende Prozesse
- Konfig-Verzeichnisse (`%APPDATA%`, `%LOCALAPPDATA%`, `~/.config`, `~/.<tool>`)
- Zeitstempel — die zuletzt geänderte Config ist meist die aktive
- Version und Datum der letzten Aktualisierung; nach einem Update sind venvs, Pfade und Configs häufig genau das, was nicht mehr passt

Das Skript `scripts/inventory.ps1` erledigt genau das für Windows. Kopiere es auf das Gerät und ruf es mit dem Produktnamen auf, statt dir die Abfragen neu auszudenken.

Wenn mehrere Kandidaten auftauchen, ist das kein Rauschen, sondern schon ein Befund: mehrere Instanzen sind eine der häufigsten Ursachen für „es funktioniert nicht, obwohl alles konfiguriert ist".

## Schritt 2 — Die *effektive* Konfiguration bestimmen

Das ist der Kern. Was in einer Config-Datei steht, ist nicht zwangsläufig das, was das Programm liest. Klär in dieser Reihenfolge:

| Frage | Wo du nachsiehst |
|---|---|
| Welches Home-/Datenverzeichnis gilt? | Umgebungsvariable (`HERMES_HOME`, `OLLAMA_MODELS`, `XDG_CONFIG_HOME` …), sonst Standardpfad |
| Ist die Variable im *laufenden* Prozess gesetzt? | User- vs. System-Variable prüfen; Prozesse erben nur das, was beim Start galt |
| Gibt es Profile/Workspaces? | `active-profile.json`, `profiles/`, `--profile`-Flags, Workspace-Datei |
| Erbt ein Profil die Hauptconfig oder ersetzt es sie? | Empirisch prüfen, nicht annehmen |
| Welche Config liest die GUI, welche die CLI? | Beide können auseinanderlaufen |

**Empirisch prüfen heißt:** dieselbe Abfrage zweimal ausführen, einmal je Kontext, und die Ausgaben vergleichen. Beispiel aus der Praxis — ein Werkzeug mit Profilen:

```
HERMES_HOME=<root>               hermes mcp list  →  11 Server
HERMES_HOME=<root>/profiles/max  hermes mcp list  →  „No MCP servers configured"
```

Damit war belegt, dass das aktive Profil keinerlei MCP-Server sieht, obwohl die Hauptconfig elf davon sauber deklariert. Ohne diesen Vergleich hätte jede weitere Diagnose ins Leere gezielt.

Der Umkehrschluss ist genauso wichtig: Läuft ein Diagnosekommando versehentlich gegen die falsche Instanz, meldet es reihenweise Fehler, die es gar nicht gibt („config.yaml not found", „not logged in"). Bevor du solche Meldungen weitergibst, vergewissere dich, dass sie aus dem richtigen Kontext stammen.

**Verwaiste Zweitinstanzen** gehören ins Ergebnis, auch wenn sie nicht die Ursache sind. Ein leeres Standard-Home neben dem echten ist eine Falle für den nächsten Durchgang — deiner oder der des Nutzers. Nenn sie beim Namen und schlag vor, sie umzubenennen oder zu entfernen; entscheiden soll das der Nutzer, denn nur er weiß, ob dort noch etwas liegt.

## Schritt 3 — Die eigene Diagnose des Werkzeugs nutzen

Viele Tools bringen eine Selbstprüfung mit — `hermes doctor`, `ollama list`, `claude doctor`, `npm doctor`, `<tool> status`. Die ist gründlicher als alles, was du ad hoc zusammenstellst, und kennt die internen Erwartungen des Programms.

Zwei Regeln dazu:

- Führe sie **im richtigen Kontext** aus (Ergebnis von Schritt 2), sonst ist der Bericht wertlos.
- Nimm ihre Hinweise als Hypothese, nicht als Befund. Reparaturvorschläge in solchen Ausgaben sind oft generisch und können auf die falsche Ursache zeigen — dazu Schritt 7.

**Logdateien sind die zweite Quelle.** `logs/`, `errors.log`, `agent.log`, unter Windows auch `%APPDATA%\<tool>\logs`. Die letzten Zeilen der Fehlerlogs kosten einen Aufruf und liefern oft Befunde, die keine Selbstprüfung meldet — abgelaufene Token, degradierte Verbindungen, Warnungen beim Start. Lies sie, bevor du selbst zu spekulieren anfängst.

## Schritt 4 — Deklariert gegen real prüfen

Jede Referenz in der Konfiguration ist eine Behauptung. Prüf sie:

- **Pfade**: Existiert jede Executable, jedes Skript, jedes venv aus den Server-/Tool-Einträgen? (`Test-Path` über alle auf einmal)
- **Modelle**: Ist das konfigurierte Modell wirklich installiert bzw. beim Provider verfügbar? Gegen die echte Liste prüfen (`ollama list`, Provider-Cache, API), nicht gegen die Erinnerung.
- **Modellart**: Ein Embedding-Modell in einem Chat-Slot ist ein Fehler, der nirgends als Fehler gemeldet wird — er zeigt sich nur als schlechte Ergebnisse.
- **Credentials**: Welche Provider sind wirklich authentifiziert (Auth-Datei, `expires_at`), und für welche steht nur ein Key-Name in der Config?
- **Key-Referenzen**: Platzhalter wie `${env:FOO}` werden je nach Implementierung nur aus echten Prozess-Umgebungsvariablen aufgelöst, nicht aus einer `.env`. Steht der Key nur in der `.env`, bekommt der Zielprozess den Platzhalter als Literal. Erkennbar an Warnungen beim Start — oder gar nicht.
- **Widersprüche**: Zwei Schlüssel, die dasselbe steuern und sich widersprechen; Werte außerhalb des gültigen Bereichs.

Zwei Prüfungen, die leicht untergehen und trotzdem in jeden Bericht gehören:

**Was startet da eigentlich?** Jeder MCP-Server-Eintrag ist ein Programm, das mit den vollen Rechten des Nutzers läuft. Schau dir an, was in `command`/`args` steht: Liegt es an einem Ort, den der Nutzer kennt? Ist es ein Skript, das er selbst geholt hat, oder etwas, das über eine Pipe aus dem Netz kommt (`curl … | sh`)? Du bewertest hier keine Software, du machst sichtbar, was mitläuft — genau das prüft die Selbstprüfung mancher Werkzeuge unter „MCP Server Security".

**Was kostet das?** Einstellungen wie Mixture-of-Agents, mehrfache Reference-Modelle oder aggressive Hintergrundläufe vervielfachen die Tokenkosten pro Anfrage. Wenn du so etwas findest, benenne es als Kostenfrage, nicht als Konfigurationsdetail — der Nutzer sieht die Rechnung, nicht die Config.

**Niemals Werte von Keys ausgeben.** Prüfe auf Vorhandensein und Länge, maskiere den Rest. Der Nutzer sieht seine Keys in seinen eigenen Dateien; im Chatverlauf haben sie nichts zu suchen — und ein Chatverlauf wird kopiert, geteilt und archiviert.

## Schritt 5 — Selbst reparieren oder vorlegen?

Nicht jeder Befund braucht eine Rückfrage. Ständiges Nachfragen bei Eindeutigem ist genauso ärgerlich wie eigenmächtiges Umbauen. Die Trennlinie verläuft entlang von **Eindeutigkeit und Umkehrbarkeit**:

**Erledige direkt** — und berichte es hinterher:

- eine Referenz zeigt auf einen Pfad, der nicht existiert, während das gemeinte Ziel eindeutig auffindbar ist
- ein Wert liegt außerhalb des gültigen Bereichs oder widerspricht sich mit einem zweiten Schlüssel, und nur eine Auflösung ergibt technisch Sinn
- ein Key existiert bereits, wird nur am falschen Ort gesucht (Env-Variable statt `.env`)
- ein konfiguriertes Modell ist nicht installiert, und beim selben Provider liegt ein offensichtlicher Ersatz
- Backups, Diagnoseläufe, Leseoperationen

**Leg vor und warte** — auch wenn du dir ziemlich sicher bist:

- strukturelle Entscheidungen: Instanzen zusammenführen, Profil wechseln, ein Feature abschalten statt reparieren
- alles Löschende und alles, was sich nicht mit dem Backup zurückholen lässt
- alles, was Geld oder spürbar Zeit kostet: Installationen jenseits weniger MB, kostenpflichtige Provider, Abos
- alles, wo mehrere Auflösungen plausibel sind und die Absicht des Nutzers den Ausschlag gibt
- Einstellungen, deren Semantik du nicht belegen konntest

Die Faustregel: **Wenn du die Änderung nicht in einem Satz begründen kannst, ohne „vermutlich" zu sagen, gehört sie in die Vorlage.** Im Zweifel vorlegen — ein Nutzer verzeiht eine Rückfrage leichter als eine Einstellung, die er nicht bestellt hat.

Für die Vorlage: Ist-Zustand als Tabelle, dann der Plan, dann eine gebündelte Frage.

| # | Befund | Belegt durch | Auswirkung |

In der Spalte „Belegt durch" steht die konkrete Beobachtung: das Kommando und seine Ausgabe, die Codestelle mit Zeilennummer, der fehlende Pfad. Kennzeichne jede Zeile als **gesichert** (selbst verifiziert) oder **Vermutung** (plausibel, aber nicht geprüft). Diese Trennung ist keine Formsache: eine als gesichert verkaufte Vermutung führt zu Änderungen, die der Nutzer später nicht nachvollziehen kann.

Den Plan sortierst du nach Hebelwirkung — was den größten Teil des Problems löst, zuerst. Gibt es eine strukturelle Entscheidung, leg sie als benannte Alternativen mit Aufwand und Konsequenz vor und gib eine Empfehlung mit Begründung. Frag dann konkret: nicht „soll ich loslegen?", sondern „Weg A oder B — und Feature X aus oder repariert?".

Ausnahme: Läuft die Sitzung unbeaufsichtigt, triff die naheliegende Wahl, schreib die Annahme oben hin und mach weiter.

## Schritt 6 — Reparieren

**Prüf zuerst, ob die Anwendung läuft.** Eine laufende Anwendung hält ihren Zustand im Speicher und schreibt ihn beim Beenden zurück — deine Änderung an einer Datei wie `active-profile.json` oder `settings.json` ist dann still wieder weg. Entweder du bittest den Nutzer, die Anwendung vorher zu beenden, oder du sagst ihm klar, dass die Änderung nach dem Neustart gegengeprüft werden muss. Beides ist in Ordnung; sie unerwähnt zu lassen ist es nicht, weil der Verlust nicht auffällt.

**Backup zuerst.** Jede Datei, die du änderst, vorher kopieren mit Zeitstempel im Namen (`config.yaml.bak.20260830_172140`).

**Chirurgisch editieren, nicht neu schreiben.** Konfigurationsdateien enthalten Kommentare, Reihenfolge und Formatierung, die der Nutzer angelegt hat. Ein YAML-Roundtrip über eine Bibliothek zerstört das. Nutze `edit_block` (oder `sed -i` / ein kurzes read-modify-write-Skript) mit genug Kontext, damit der Treffer eindeutig ist. Steht derselbe Block mehrfach mit unterschiedlicher Einrückung in der Datei — etwa ein Preset und die Top-Level-Variante desselben Abschnitts —, sind das zwei getrennte Edits; ändere nie nur einen davon.

**Niemals Dateiinhalt aus Tool-Ausgaben abtippen.** Ausgaben können abgeschnitten sein; die Datei liest sich das Skript selbst.

**Reihenfolge:** Erst Config-Dateien (dabei bricht nichts, solange nichts neu startet), dann Umgebungsvariablen, dann Installationen. Nach jedem Block einmal die Selbstprüfung laufen lassen — dann weißt du, welche Änderung ein neues Problem verursacht hat.

**Rechte und Neustarts realistisch behandeln:** System-Umgebungsvariablen brauchen Administratorrechte; wenn das scheitert, ist die User-Variable die funktionierende Alternative, und du gibst den Admin-Einzeiler zum Nachholen mit. Laufende Prozesse übernehmen weder neue Configs noch neue Variablen — sag klar, was neu gestartet werden muss, statt es zu erwähnen, als sei es nebensächlich.

## Schritt 7 — Verifizieren, und Meldungen nicht blind glauben

Zum Schluss dieselbe Selbstprüfung wie in Schritt 3, plus gezielte Gegenproben für jede Änderung (im Beispiel oben: Diagnose grün, Server-Liste vollständig, Warnung verschwunden, sobald die Variable gesetzt ist).

Wenn eine Prüfung nach der Reparatur immer noch fehlschlägt, obwohl die genannte Voraussetzung nachweislich erfüllt ist, **glaub der Meldung nicht — ruf die Prüffunktion selbst auf.** Fast jede Prüfung ist eine Funktion im Quelltext, die du direkt ausführen und deren Zwischenschritte du einzeln abfragen kannst:

```python
import tools.browser_tool as bt
for name in ("_is_browser_use_cli_mode", "_get_cloud_provider", "_chromium_installed"):
    print(name, "->", getattr(bt, name)())
```

Im konkreten Fall meldete die Diagnose „browser (system dependency not met)" und schlug eine Chromium-Installation vor. Der direkte Aufruf zeigte: `_is_browser_use_cli_mode() → True` — die Tools waren **absichtlich** ausgeblendet, weil ein anderes Backend sie ersetzt. Die vorgeschlagene Installation von 300 MB war überflüssig. Zehn Minuten Quelltextlesen hätten sie erspart.

Suchmuster dafür: die Fehlermeldung wörtlich im Quelltext suchen, von dort zur Prüffunktion, dann deren Verzweigungen einzeln auswerten.

## Schritt 8 — Abschlussbericht

Enthält:

1. Änderungstabelle **vorher → nachher** — jede Änderung, auch die, die du ohne Rückfrage erledigt hast. Genau dafür ist die Tabelle da: Der Nutzer hat der Reparatur nicht einzeln zugestimmt, also muss er sie hinterher lückenlos nachvollziehen können.
2. Backup-Dateinamen **plus den fertigen Rückspielbefehl**. Ein Backup, dessen Wiederherstellung sich der Nutzer selbst zusammensuchen muss, ist ein halbes Backup:
   ```powershell
   Copy-Item '<pfad>\config.yaml.bak.20260830_172140' '<pfad>\config.yaml' -Force
   ```
3. Was der Nutzer selbst tun muss — Neustart, Adminrechte, Anmeldungen
4. **Eigene Fehlspuren offen benennen.** Wenn du etwas installiert oder geändert hast, das sich als unnötig herausstellte, sag es und nenn den Rückbauweg. Das kostet zwei Sätze und ist der Unterschied zwischen einem nachvollziehbaren und einem undurchsichtigen System.
5. Offene Punkte, getrennt nach: konnte ich nicht verifizieren / braucht eine Entscheidung von dir / bewusst nicht angefasst

Zu Punkt 5: Eine Einstellung, deren Semantik du nicht belegen konntest, änderst du nicht. Erklär stattdessen, was du nicht klären konntest und welche Information die Entscheidung möglich machen würde. Raten ist hier schlimmer als offen lassen — der Nutzer merkt einen falsch umgelegten Schalter womöglich erst Wochen später.

## Referenzen

- `references/windows-shell.md` — Shell-Mechanik auf Windows-Geräten: Quoting-Fallen, Skriptdatei-Muster, Suchwerkzeuge, Rechte. Lies das, bevor du den ersten längeren Befehl absetzt.
- `references/tool-map.md` — Wo verbreitete lokale KI-Werkzeuge ihre Konfiguration ablegen, wie ihre Selbstprüfung heißt, welche Umgebungsvariable ihr Home steuert. Nachschlagen in Schritt 1 und 2; ist ein Werkzeug nicht gelistet, gilt die generische Suche.
- `scripts/inventory.ps1` — Bestandsaufnahme in einem Aufruf (Prozesse, Pfade, Config-Ordner, Umgebungsvariablen, Keys maskiert).

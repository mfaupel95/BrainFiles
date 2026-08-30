# Digitales Archiv

## Schutzregeln — vor jedem Schreibzugriff

`Dokumente/`, `Bilder/`, `Videos/`, `Musik/` (samt Playlisten) sind **Originale
ohne Zweitquelle**. Hier wird gelesen, nicht geschrieben. Nicht löschen, nicht
verschieben, nicht umbenennen — außer Max ordnet es in derselben Sitzung für
genau diese Datei an. Soll etwas weg, wandert es nach
`Posteingang/_zu_loeschen/`, entschieden wird von Hand.

**Weiter reicht die Löschsperre nicht.** Seit 25.08.2026 gilt sie nur noch für
persönliche Inhalte: diese vier Ordner, den noch unsortierten `Posteingang/`,
Schlüssel- und Zertifikatsdateien (`.env`, `.pem`, `.pfx`, `.p12`, `.kdbx`,
`.key`, `.ovpn`) und die 0xFF-Platzhalter. Überall sonst im Vault — `Wissen/`,
Caches, Indizes, Protokolle, Klone, Build-Reste — räumt ein Agent ohne
Rückfrage auf, auch in Massenoperationen.

Seit 24.08.2026 versioniert Git die **Textebene** des Vaults (85 Dateien:
Notizen, Skills, Skripte, Konfiguration). **Diese vier Ordner gehören nicht
dazu** — sie enthalten keine einzige versionierte Datei, die Whitelist in
`.gitignore` gibt sie bewusst nicht frei. Für sie gilt unverändert: Die
Sicherung läuft ohne `/MIR`, eine falsch überschriebene Datei ist um 20:01 auch
auf `G:` überschrieben. Es gibt kein Zurück.

Der frühere Satz „Der Vault ist kein Git-Repository" stimmt seit dem
24.08.2026 nicht mehr — für die Originale hier ändert das aber nichts.

Vollständig: [Wissen/Schutzregeln.md](../Wissen/Schutzregeln.md)

## Überblick

Dieser Ordner ist Max' zentrales digitales Archiv (Bilder, Videos, Musik, Dokumente)
mit einem lokalen Such-Tool in `ArchivSuche/`. Siehe [README.md](README.md) für die
Ordnerstruktur.

## Wichtig: Archiv-Suche zuerst nutzen

Bevor du für eine Anfrage von Max eine Internetsuche (WebSearch/WebFetch) startest,
prüfe zuerst, ob die Antwort bereits in seinem eigenen Archiv liegt (eigene
Rechnungen, Anleitungen, Verträge, Notizen, Rezepte usw.):

```
cd ArchivSuche
.venv\Scripts\python.exe search_cli.py "suchbegriff"
```

Optional mit Filter: `--category Dokumente` (Bilder | Videos | Musik | Dokumente),
`--limit N` (Standard 5). Kein Treffer oder Frage erfordert allgemeines Weltwissen?
Dann normal mit Internetsuche fortfahren.

## Sparsam arbeiten

Die Werkzeuge geben standardmäßig nur Zusammenfassungen aus – das spart Kontext
und damit Tokens. Wichtig:

- **Nie `--details` oder `--verbose` vorsorglich setzen.** Nur wenn eine Zahl
  aus der Kurzfassung wirklich aufgeschlüsselt werden muss.
- **Ausgaben filtern statt komplett lesen**, z.B. `| tail -3`, `| grep -E "^(Einsortiert|Fertig)"`.
- **Nicht mehrfach denselben Stand abfragen** (Dateizahlen, Index-Statistik) –
  einmal prüfen reicht.
- Bei Massenoperationen auf tausenden Dateien: PowerShell statt Python für das
  reine Einlesen (siehe Gedächtnis-Notiz), sonst dauert es Stunden statt Sekunden.

Falls seit dem letzten Lauf neue Dateien hinzugekommen sind und die Suche nichts
findet, wo eigentlich etwas erwartet wird, zuerst neu indexieren:

```
.venv\Scripts\python.exe index.py
```

## Dateien verschicken

**Der Server ist nicht eingerichtet** (geprüft 28.08.2026): `mail_zugang_pruefen`
antwortet „Keine Absenderadresse hinterlegt", und in 53 Sitzungen wurde er kein
einziges Mal erfolgreich benutzt. Bis das behoben ist (`Claude/TASKS.md`, T-008),
ist Versand über diesen Weg **nicht** möglich — dann Max fragen, statt es zu
versuchen.

Vorgesehen ist: „Schick mir das per Mail" geht über den MCP-Server `mail`
(`mail_datei_suchen` → `mail_senden`), **nicht** über die Gmail-Weboberfläche
im Browser. Ohne
Empfängerangabe geht die Mail an Max selbst. Anhänge dürfen nur aus diesem
Archivordner stammen; fremde Empfängeradressen nur, wenn Max sie selbst in
seiner Anweisung genannt hat. Details und Einrichtung:
[MCP-Server/mail/README.md](../MCP-Server/mail/README.md)

## Posteingang

Max zieht neue Dateien einfach in `Posteingang/`. Wenn er dich bittet, den
Posteingang einzusortieren (oder du dort Dateien vorfindest, die noch nicht in
der Archiv-Struktur liegen), führe aus:

```
cd ArchivSuche
.venv\Scripts\python.exe sort_inbox.py
```

Die Ausgabe ist standardmäßig kurz (nur Zahlen je Zielordner). Erst wenn du
wissen musst, *welche* Dateien betroffen sind: `--details`. Vor größeren Läufen
lohnt `--dry-run`.

Dateien, die das Skript nicht sicher zuordnen konnte, bleiben im Posteingang
liegen – lies den Inhalt und verschiebe sie dann selbst gezielt in den passenden
Unterordner von `Dokumente/` (oder `Bilder/`/`Videos/`/`Musik/`), statt sie zu
raten. Danach `index.py` laufen lassen, falls `sort_inbox.py` das nicht schon
automatisch getan hat.

Ganze Ordner werden samt Unterstruktur übernommen, wenn ihr Name die Kategorie
verrät (`Studium/` → `Dokumente/Privat/Studium`); die Regeln stehen in
`ORDNER_REGELN` in `sort_inbox.py` und lassen sich dort erweitern.

### Was das Skript von sich aus absichert

`sort_inbox.py` hat mehrere eingebaute Sicherungen: Duplikat­entscheidung über
den **Inhalt** (Größe + SHA1), nicht über den Namen — weicht der Inhalt ab, wird
**nichts** gelöscht; Icon-Filter statt `Bilder/`; Zertifikate und Schlüssel
werden nie automatisch verschoben (Endung, nicht Dateiname); Build-Artefakte
werden übersprungen. Schwellen, Messwerte und die vollständige Liste stehen in
[ArchivSuche/README.md](ArchivSuche/README.md) (Abschnitt „Eingebaute
Sicherungen") und im Skill `posteingang` — hier bewusst nicht kopiert, damit die
Zahlen nicht still veralten.

## Was nicht im Index ist

`Software/` (Installationsdateien, iCloud-Restbestand) ist bewusst vom Index
ausgenommen — die verwertbaren Inhalte sind längst im Archiv, übrig sind
Software-Reste und Max' sechs ELSTER-Zertifikate (`.pfx`), allesamt zerstört
(0xFF-Füllbytes). Sie bleiben liegen: einziger Beleg, dass der ELSTER-Zugang
mit den Platten verloren ging. Die 639 ebenfalls zerstörten iCloud-PDFs aus
diesem Ordner wurden bereits gelöscht.

**Zerstörte Dateien im eigentlichen Archiv haben eine andere Ursache** — ein
Netzteildefekt, der mehrere Platten gleichzeitig traf (Dateiname blieb,
Inhalt weg). Stand, Rettungsversuche je Laufwerk, Schadensquote je Ordner und
offene Punkte: [BESCHAEDIGTE_DATEIEN.md](BESCHAEDIGTE_DATEIEN.md) (alle
Dateitypen) und [BESCHAEDIGTE_PDFS.md](BESCHAEDIGTE_PDFS.md) (die 61
verbleibenden PDFs samt Rettungsgeschichte). Geprüft wird mit
`ArchivSuche/pruefe_signaturen.py` (Skill `schaden`) — „beginnt mit FF" ist
die falsche Prüfung, siehe dort.

Such-Falle: Die Kündigung heißt `20231130_tm_kündigung_mf.pdf` mit **ü** —
`*kuendigung*` findet sie nicht. OCR-Rückfall für Scans ohne Textebene:
[Wissen/PDF-Scans-lesen.md](../Wissen/PDF-Scans-lesen.md).

Details zum Tool (Aufbau, OCR, Web-Oberfläche, Sortierregeln): [ArchivSuche/README.md](ArchivSuche/README.md)

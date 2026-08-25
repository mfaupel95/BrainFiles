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

„Schick mir das per Mail" geht über den MCP-Server `mail` (`mail_datei_suchen`
→ `mail_senden`), **nicht** über die Gmail-Weboberfläche im Browser. Ohne
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

- **Über Duplikate entscheidet der Inhalt, nicht der Name.** Liegt am Ziel schon
  eine Datei gleichen Namens, werden Größe und SHA1 verglichen. Nur bei
  Byte-Gleichheit wird die Posteingang-Kopie gelöscht; weicht der Inhalt ab,
  wird **nichts** gelöscht und die Datei als `(2)` abgelegt. Früher entschied das
  Änderungsdatum – das hätte allein in einem Lauf 1001 gleichnamige, aber
  inhaltlich verschiedene Icon-Dateien blind abgeräumt.
- **Icons landen nicht in `Bilder/`.** `.ico`/`.icns` immer; PNG und SVG dann,
  wenn sie quadratisch, höchstens 512 px groß und unter 64 KB sind → nach
  `Software/Windows/Icon`. Die Schwelle ist an den echten Daten gemessen: sie
  fängt 1151 von 1152 bekannten Icons bei genau einem Fehltreffer unter 2927
  echten Bildern.
- **Build-Artefakte werden übersprungen:** `.pyc`, `.pyo`, `.pyd`, `.toc`, `.pyz`
  sowie alles unterhalb von `__pycache__/`, `build/`, `dist/` und `.venv/`.
- **Zertifikate und Schlüssel werden nie automatisch verschoben.** Entscheidend
  ist die Endung (`.pfx`, `.p12`, `.pem`, `.key`, `.kdbx`, `.ovpn` …), nicht der
  Dateiname – ein ELSTER-Zertifikat heißt schlicht `Ann21_elster_….pfx` und
  enthält kein einziges verräterisches Wort.

## Was nicht im Index ist

Der Ordner `Software/` (Installationsdateien Linux/Windows) ist bewusst vom Index
ausgenommen. Die verwertbaren Inhalte der dortigen iCloud-Sicherung (Dokumente,
Bilder, Musik, Videos) wurden bereits ins Archiv übernommen; zurückgeblieben sind
nur Software-Reste sowie Max' ELSTER-Zertifikate (`.pfx`) – die **allesamt
zerstört sind** (0xFF-Füllbytes, geprüft 20.08.2026). Sie bleiben trotzdem
liegen: sie belegen, dass der ELSTER-Zugang mit den Platten verloren ging.

Die beschädigten PDFs aus dieser iCloud-Sicherung (639 Stück, reine 0xFF-Füllbytes
ohne jeden Inhalt – fehlgeschlagene iCloud-Downloads) wurden gelöscht.

**Im eigentlichen Archiv gab es weitere Nullbyte-PDFs – mit anderer Ursache.**
Am 08.08.2026 fanden sich dort 123 Stück. Sie stammen **nicht** von iCloud,
sondern von einem **Netzteildefekt**, der mehrere Festplatten gleichzeitig
zerstört hat: Die Dateinamen wurden noch geschrieben, die Inhalte gingen mit der
Hardware verloren.

Aus den 123 wurden in zwei Durchgängen **61**: 44 Dateien wurden aus intakten
Fassungen zurückgespielt (gefunden auf G:, H: und O:), 18 Platzhalter entfernt,
für die im Archiv längst ein intakter Zwilling lag. Die verbleibenden 61 –
darunter zehn Rechnungen und das Einladungsschreiben zur Meisterprüfung – werden
**bewusst nicht gelöscht**, weil sie der einzige Hinweis darauf sind, welche
Dokumente fehlen.

Die zurückgespielten Fassungen sind **Scans ohne Textebene** und waren dadurch
bis zum 10.08.2026 im Volltextindex leer. Seither hat `index.py` einen
OCR-Rückfall für bildbasierte PDFs; alle 13 wichtigen Dokumente sind jetzt
durchsuchbar. Ein Sonderfall beim Suchen: die Kündigung heißt
`20231130_tm_kündigung_mf.pdf` mit **ü** – `*kuendigung*` findet sie nicht.

Wichtig bei weiteren Rettungsversuchen: **Namensgleichheit genügt nicht.** Von
261 namensgleichen Kandidaten waren 220 selbst mit 0xFF gefüllt. Immer die ersten
vier Bytes prüfen. Auf C:, G:, H:, I: und J: wurde am 08.08.2026 nichts gefunden. **O: ist eine
M.2-SSD im Mainboard-Slot M2_1 und dauerhaft eingebunden** — die frühere Angabe
„nicht eingebunden" war überholt. Der Lauf dorthin am 20.08.2026 brachte 42
Dateien zurück (40 Bilder, 2 Software), aber kein einziges Dokument.

Stand, Fundorte und vollständige Liste: [BESCHAEDIGTE_PDFS.md](BESCHAEDIGTE_PDFS.md).

**Nicht nur PDFs sind betroffen.** Der erste vollständige Lauf über alle
Dateitypen (20.08.2026) fand **691 zerstörte Dateien** unter 62.401 geprüften:
494 in `Bilder/`, 86 in `Software/`, 83 in `Dokumente/`, 31 in `Musik/`,
5 in `Videos/`. Darunter alle sechs ELSTER-Zertifikate und 31 Musikstücke,
die vorher nirgends erfasst waren.

Der Schadensanteil in `Bilder/` beträgt **18,3 %** (494 von 2.693 Bilddateien
dort) — eine frühere Angabe verglich die 494 mit 10.359 Bildern *archivweit*
und ließ den Schaden dadurch fünfmal kleiner wirken.

Geprüft wird mit `ArchivSuche/pruefe_signaturen.py` (Skill `schaden`), nicht
von Hand: **„beginnt mit FF" ist die falsche Prüfung**, denn ein intaktes JPEG
beginnt selbst mit `FF D8 FF`, und HEIC/MP4 tragen ihre Kennung erst ab Byte 4.
Das Skript prüft stattdessen, ob die ersten 4096 Bytes durchgehend denselben
Wert haben.

Gesamtbild und offene Punkte: [BESCHAEDIGTE_DATEIEN.md](BESCHAEDIGTE_DATEIEN.md).

Details zum Tool (Aufbau, OCR, Web-Oberfläche, Sortierregeln): [ArchivSuche/README.md](ArchivSuche/README.md)

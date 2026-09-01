# Offene Punkte

Sitzungsübergreifende Aufgabenliste. Einzige Quelle für „was ist noch offen".
Angelegt am 2026-08-28, weil offene Punkte aus früheren Chats bis dahin
nirgends festgehalten wurden und mit dem Sitzungsende verloren gingen.

## Regeln

- **Am Sitzungsanfang lesen**, bevor gefragt wird, woran gearbeitet werden soll.
- **Sofort eintragen**, wenn ein Punkt entsteht — nicht am Sitzungsende sammeln.
  Wird die Sitzung vorher abgebrochen, ist der Punkt sonst weg.
- **Erledigtes nach `## Erledigt` verschieben**, mit Datum. Nicht löschen —
  die Historie zeigt, was schon einmal versucht wurde.
- **Nichts erfinden.** Nur eintragen, was Max gesagt hat oder was aus einer
  abgebrochenen Arbeit tatsächlich offen blieb. Vermutete Folgeaufgaben
  gehören als Vorschlag in die Zeile „Kontext", nicht als eigener Punkt.
- **Stand aktuell halten.** Fällt beim Arbeiten auf, dass ein Eintrag hier
  überholt ist, sofort korrigieren und die Korrektur melden — auch wenn es
  nicht zur laufenden Aufgabe gehört.
- IDs fortlaufend `T-001`, `T-002`, … Einmal vergeben, nie wiederverwenden.

## Status-Kürzel

| Kürzel | Bedeutung |
|---|---|
| `[ ]` | offen, noch nicht angefangen |
| `[~]` | in Arbeit / teilweise erledigt |
| `[?]` | wartet auf Entscheidung oder Information von Max |
| `[!]` | blockiert, Ursache im Kontext benannt |
| `[x]` | erledigt → gehört nach unten |

## Eintragsformat

```
- [ ] **T-001 — Kurztitel**
      Kontext: worum es geht, warum es offen ist
      Nächster Schritt: eine konkrete, ausführbare Handlung
      Angelegt: 2026-08-28 · Zuletzt: 2026-08-28
```

Optional zusätzlich: `Betrifft:` (Pfad, Projekt, Gerät), `Wartet auf:` (bei `[?]`/`[!]`).

## Offen

- [?] **T-010 — 32 GB Kimi-K2.7-Code: auschecken, behalten oder weg?**
      Kontext: `Modelle/Kimi-K2.7-Code` belegt 32,1 GB, davon liegt alles in
      `.git` (LFS). Im Arbeitsbaum steht keine einzige Gewichtsdatei — nur
      Python- und Konfigurationsdateien. `git lfs ls-files` meldet 67 verwaltete
      Dateien, darunter `model-00001-of-000064.safetensors`. Solange nichts
      ausgecheckt ist, sind die 32 GB totes Gewicht; ein Auschecken bräuchte
      noch einmal so viel Platz.
      Nächster Schritt: entscheiden. Auschecken (`git lfs checkout`), so lassen
      oder löschen. Ein Skript entscheidet das nicht.
      Betrifft: `Modelle/Kimi-K2.7-Code`
      Angelegt: 2026-08-30 · Zuletzt: 2026-08-30

- [ ] **T-011 — Wer schreibt `Modelle/.onchainos`?**
      Kontext: Der Ordner (7 MB) enthält `keyring.enc`, `audit.jsonl` und
      `machine-identity` — also Zugangsdaten, damit Stufe 0. Er lag in
      `MaxHirn/Modelle` und ist beim Umbau am 30.08.2026 unverändert an seiner
      relativen Stelle mitgewandert, weil unbekannt ist, welches Programm ihn
      schreibt und ob es ihn an fester Stelle sucht.
      Nächster Schritt: Urheber bestimmen (OKX/OnchainOS-Werkzeuge prüfen),
      dann entscheiden, ob er nach `Agenten/` gehört.
      Betrifft: `Modelle/.onchainos`
      Angelegt: 2026-08-30 · Zuletzt: 2026-08-30

- [ ] **T-012 — Alte Zweige auf `G:` abräumen**
      Kontext: Die Sicherung läuft ohne `/MIR` und räumt deshalb nichts weg,
      was in der Quelle verschwindet. Auf `G:\MaxHirn-Sicherung` liegen nach
      dem Umbau vom 30.08.2026 noch die 51 GB `Modelle\` (ab jetzt aus der
      Sicherung ausgenommen) und der alte Zweig unter dem früheren Namen „Claude“ (er heißt jetzt
      `Archiv`, wird also ein zweites Mal kopiert).
      Nächster Schritt: erst den ersten Lauf der neuen Sicherung abwarten, dann
      beide Altzweige vorlegen und nach Freigabe entfernen.
      Betrifft: `G:\MaxHirn-Sicherung`
      Angelegt: 2026-08-30 · Zuletzt: 2026-08-30

- [ ] **T-013 — Drei Pfadverweise in `Zugaenge.md` von Hand nachziehen**
      Kontext: Die Datei steht in Stufe 0 der Schutzregeln und wurde beim
      Umbau bewusst **nicht** automatisch ersetzt. Sie enthält drei Verweise
      auf den alten Archivnamen „Claude“, der seit dem 30.08.2026 `Archiv` heißt.
      Nächster Schritt: die drei Stellen einzeln ansehen und ändern — auf
      ausdrückliche Anweisung, nicht nebenbei.
      Betrifft: `Wissen/Zugaenge.md`
      Angelegt: 2026-08-30 · Zuletzt: 2026-08-30

- [ ] **T-014 — 1,5 GB Ollama-Protokolle in 17 Dateien**
      Kontext: `%LOCALAPPDATA%\Ollama` enthält 17 Dateien mit zusammen 1,5 GB —
      im Schnitt 88 MB je Protokolldatei. Sie rotieren offenbar nicht.
      Gemessen am 30.08.2026, siehe [[KI-Ablagen-im-Benutzerordner]].
      Nächster Schritt: löschen und beobachten, wie schnell sie nachwachsen.
      Angelegt: 2026-08-30 · Zuletzt: 2026-08-30

- [?] **T-016 — Whitelist zeigt auf `MaxHirn/Archiv/`, der Ordner heisst `MaxHirn/Claude/`**
      Kontext: Die `.gitignore` gibt seit dem 30.08. `MaxHirn/Archiv/*.md`,
      `MaxHirn/Archiv/ArchivSuche/*.py` usw. frei. Diesen Ordner gibt es im
      Dateisystem nicht — er heisst weiterhin `MaxHirn/Claude/`. Auch
      `MaxHirn/CLAUDE.md` und `Claude/CLAUDE.md` beschreiben die Umbenennung
      bereits als vollzogen. Folge: Jede **neue** Datei unter
      `MaxHirn/Claude/` faellt unter die Grundregel `*` in Zeile 20 und wird
      nie versioniert (geprueft 01.09.2026 mit `git check-ignore`). Die 36
      bereits getrackten Dateien dort ueberleben nur, weil Ignore-Regeln auf
      versionierte Dateien nicht mehr wirken — darunter das ganze
      Archiv-Werkzeug unter `ArchivSuche/`.
      Verschaerfend: `arbeitsbaum-pruefen.ps1` haette diese 36 Dateien ab dem
      01.09. stumm aus jeder Sicherung genommen; das ist mit Commit `6d0f192`
      behoben, die Ursache besteht aber fort.
      Naechster Schritt: entweder den Ordner mit dem Skill `umzug` wirklich
      nach `MaxHirn/Archiv/` umbenennen (Achtung: `ArchivSuche/.venv` ist an
      seinen Pfad gebunden, siehe [[Portabilitaet]]) — oder die Whitelist auf
      `MaxHirn/Claude/` zurueckstellen und die Umbenennung aus den drei
      CLAUDE.md-Dateien streichen. Beides ist vertretbar, aber es muss eines
      von beiden sein.
      Betrifft: `.gitignore`, `MaxHirn/CLAUDE.md`, `MaxHirn/Claude/CLAUDE.md`
      Wartet auf: Entscheidung von Max, welche Richtung gilt
      Angelegt: 2026-09-01 · Zuletzt: 2026-09-01

- [x] **T-017 — Gehebelter Handel hat noch keine `wachen.json`** — erledigt
      2026-09-01. `Agenten/Handel/xperp/wachen.json` liegt (Höchsteinsatz je
      Anlauf 50 USD Margin, gesamt 200, Höchsthebel 5, Pflicht-Stop in ATR
      statt Prozent, Kill-Switch je Anlauf und gesamt). Der Modulkopf von
      `okxf.py` ist auf Spur 2 umgeschrieben und nennt den alten Wortlaut nur
      noch als Historie. Zusätzlich legt `bot.pruefpflicht()` die vier
      geforderten Zahlen vor; neu gerechnet ist Zahl 4 (nötige gegen
      beobachtete Trefferquote) samt Warnung, wenn die seltenere Seite unter
      zehn Ereignissen liegt. Siehe [[XPERP-Handel]].
      Kontext: [[Schutzregeln]] erlaubt seit dem 01.09.2026 gehebelte
      Positionen auf ausdrückliche Anweisung (Spur 2). Die Grenzen dieser Spur
      stehen bisher **nur in der Prosa der Notiz**, nicht in einer Datei — im
      Gegensatz zu Spur 1, wo `scanner/wachen.json` die einzige Wahrheit ist.
      Genau diese Bauform ist aber der Schutz: eine Sitzung kann eine Regel
      vergessen, eine Datei nicht.
      Zweitens trägt `Agenten/Handel/xperp/okxf.py` im Modulkopf noch den
      alten Wortlaut („gilt ausdruecklich nur fuer nur Spot, nur Long, kein
      Hebel … Dieses Modul faellt NICHT darunter"). Das stimmt seit heute
      nicht mehr und widerspricht der Regeldatei.
      Nächster Schritt: `xperp/wachen.json` anlegen (Höchsteinsatz je Position,
      Gesamtnominal, Höchsthebel, Pflicht-Stop, erlaubte Kontrakte) und den
      Modulkopf auf Spur 2 umschreiben.
      Betrifft: `Agenten/Handel/xperp/` — **dort arbeitete am 01.09. 17:34 eine
      andere Sitzung**, deshalb hier nur eingetragen und nicht angefasst.
      Angelegt: 2026-09-01 · Zuletzt: 2026-09-01

- [!] **T-015 — Seagate Portable (`G:`) wieder ab, Hauptsicherung ohne Ziel**
      Kontext: `G:` ist erneut nicht angeschlossen (`Test-Path G:\` = False; in
      der Datenträgerliste nur C:, O:, J:). Der geplante 20-Uhr-Lauf scheitert
      seit mindestens 30.08. 20:12 mit robocopy-Code 16, „Das System kann den
      angegebenen Pfad nicht finden" — dasselbe Muster wie beim abgezogenen
      Laufwerk in T-001, aber ein neuer Vorfall. `MaxHirn-Sicherung` ist
      deaktiviert, bis ein echter Lauf die Phase-8-Änderung an `sichern.ps1`
      bestätigt (neue Quelle `BrainFiles\`, `/XD Modelle Werkstatt`, Commit
      `fc483d4`/`7e3e561`). `sichern-ausser-haus.ps1` (Ziel `E:`) hängt am
      selben Nagel. `sichern-zweitkopie.ps1` (Ziel `O:`) ist am 31.08. 21:00
      grün durchgelaufen und damit bestätigt.
      Nächster Schritt: Seagate Portable anstecken, `Agenten\sichern.ps1`
      einmal von Hand laufen lassen, bei robocopy-Code < 8 `MaxHirn-Sicherung`
      wieder aktivieren (`Enable-ScheduledTask -TaskName MaxHirn-Sicherung`).
      Alternativ Ziel auf ein dauerhaft erreichbares Laufwerk umstellen.
      Betrifft: `Agenten/sichern.ps1`, `Agenten/sichern-ausser-haus.ps1`,
      Aufgabe `MaxHirn-Sicherung`
      Wartet auf: angeschlossenes Sicherungslaufwerk `G:`
      Angelegt: 2026-08-31 · Zuletzt: 2026-08-31

- [!] **T-004 — Zwölf Abschaltungen ohne Bluescreen seit 08.08., Ursache offen**
      Kontext: Alle zwölf Kernel-Power-41-Ereignisse haben `BugcheckCode = 0`
      und `PowerButtonTimestamp = 0` — kein Bluescreen, kein Speicherabbild,
      sondern harter Stromverlust. Keine WHEA-Fehler in 30 Tagen, keine
      Plattenfehler (nur ID 98, Information), kein Dump. In den drei Minuten
      vor dem letzten Abschalten steht **ein einziger** Protokolleintrag.
      **Die Beobachtung vom 28.08. ist entschieden — negativ.** Sie musste nicht
      auslaufen: seit dem Start am 28.08. um 16:00 ist der Rechner dreimal
      ausgegangen (29.08. 10:45, 29.08. 13:17, 30.08. 20:59, echte Zeitpunkte
      aus Ereignis 6008). Aus neun Vorfällen sind damit zwölf geworden, und die
      Abstände sind kürzer geworden: drei in zwei Tagen gegen sieben in den
      vierzehn Tagen davor.
      **Standby scheidet als Ursache aus.** Seit dem 28.08. 06:46 gab es keinen
      einzigen Standby-Zyklus mehr (kein Kernel-Power 42/107) — die drei neuen
      Abstürze fielen also in eine Phase ganz ohne Standby. Der Ablauf „3–10
      Minuten nach dem Aufwachen aus S3" war Begleiterscheinung, nicht Ursache.
      Das frühere Merkmal `SleepInProgress = 16` beruhte auf einer Verwechslung
      mit dem Feld `Checkpoint`; `SleepInProgress` ist bei allen zwölf `0`.
      Nächster Schritt: **Stromzufuhr ausserhalb des Netzteils prüfen** —
      Kaltgerätekabel, Steckdosenleiste, Wandsteckdose. Billig und nie geprüft,
      deshalb zuerst; danach erst der Gegentest mit einem bekannt guten Netzteil.
      Beides Handgriffe an der Hardware, also Max' Sache, und **einen nach dem
      anderen**, sonst ist unbekannt, welcher gewirkt hat. Bei zuletzt 2,5 bis
      32 Stunden Abstand zeigt sich das binnen zwei bis drei Tagen.
      Wartet auf: Max — Handgriff an Kabel und Steckdose.
      Messbefehl: Routinen/absturz-nachmessen.ps1 (nur lesend, ohne Adminrechte)
      Betrifft: [[Hardware]], Abschnitt „Nachmessung 30.08.2026, 22:20"
      Angelegt: 2026-08-28 · Zuletzt: 2026-08-30 (22:20)

- [ ] **T-007 — 18 claude.ai-Connectors ohne einen einzigen Aufruf**
      Kontext: `claude mcp list` meldet 21 aktive claude.ai-Connectors. In
      53 gespeicherten Sitzungen wurden davon **drei** je einmal aufgerufen
      (Kalender, Gmail, Drive); die übrigen 18 kein einziges Mal — darunter
      Uber, Uber Eats, PayPal, HubSpot, monday.com, Morningstar, DataHub,
      Play Sheet Music, tldraw, Excalidraw, Sprouts, Windsor.ai, Superhuman
      Docs, ChangeThisFile, UseMyContext, Unstructured, Economic Index.
      Jeder belegt in **jeder** Sitzung Kontext, bevor ein Wort gesagt ist.
      Max hat das am 27.08. selbst als größten Hebel benannt; der Punkt ging
      danach verloren, weil er nirgends eingetragen war.
      Nächster Schritt: Max schaltet sie in den Connector-Einstellungen auf
      claude.ai ab — das geht nicht lokal und nicht aus einer Sitzung heraus.
      Messbefehl für den Vorher-Nachher-Vergleich:
      `sitzungen_auswerten.py --werkzeuge`
      Betrifft: claude.ai-Konto, nicht den Vault
      Angelegt: 2026-08-28 · Zuletzt: 2026-08-28

- [?] **T-008 — MCP-Server `mail` ist nicht eingerichtet**
      Kontext: `Claude/CLAUDE.md` beschreibt den Versand über `mail_senden`
      als den vorgesehenen Weg für „schick mir das per Mail". Der Server
      antwortet aber mit „Keine Absenderadresse hinterlegt" — in 53 Sitzungen
      wurde er kein einziges Mal erfolgreich benutzt. Der dokumentierte Weg
      existiert also nur auf dem Papier. Die CLAUDE.md ist am 28.08.
      entsprechend korrigiert.
      Nächster Schritt: `MCP-Server/mail/.venv\Scripts\python.exe einrichten.py`
      — braucht Absenderadresse und App-Passwort, also Max' Zutun.
      Wartet auf: Zugangsdaten von Max
      Angelegt: 2026-08-28 · Zuletzt: 2026-08-28

- [?] **T-009 — `Zugaenge.md` als einzige Notiz ohne Frontmatter**
      Kontext: Am 30.08.2026 haben alle 21 übrigen Notizen in `Wissen/`
      YAML-Frontmatter mit stabiler `id` bekommen, dazu `Wissen/INDEX.md` als
      vollständige Registry. `Zugaenge.md` wurde bewusst ausgelassen, weil sie
      in [[Schutzregeln]] unter den geschützten Schlüsseldateien steht und dort
      kein Agent ohne ausdrückliche Anordnung schreibt. Sie ist in der Registry
      geführt, hat aber keine `id`. Fachlich spricht nichts dagegen — das
      Frontmatter berührt keine Zugangsdaten, sondern steht davor.
      Nächster Schritt: Max gibt frei (oder nicht); dann acht Zeilen Frontmatter
      voranstellen, `id: 20260830-zugaenge`, `tags: [sicherheit]`.
      Vorschlag zum selben Themenkreis, nicht eingetragen als eigener Punkt:
      Die Dateinamen in `Wissen/` sind gemischt geschrieben statt durchgehend
      kleingeschrieben. Eine Umbenennung würde alle `[[Wikilinks]]` brechen und
      ist den Gewinn vermutlich nicht wert.
      Betrifft: `Wissen/Zugaenge.md`, `Wissen/INDEX.md`
      Wartet auf: Freigabe von Max
      Angelegt: 2026-08-30 · Zuletzt: 2026-08-30

## Erledigt

- [x] **T-001 — Sicherungslaufwerk G: fehlt, Hauptsicherung hat kein Ziel**
      Erledigt 2026-08-28: Kein Defekt. Max hatte die USB-Platten für einen
      CMOS-Reset abgezogen. Seagate Portable ist wieder angeschlossen,
      `G:\MaxHirn-Sicherung` erreichbar (2751,1 GB, 128,8 GB frei, `Healthy`).
      Der 20-Uhr-Lauf kann wieder arbeiten. Der Fehlstand bestand nur, solange
      die Platte ab war.

- [x] **T-002 — Auslagerungsdatei liegt auf einer USB-Platte**
      Erledigt 2026-08-28: Max hat den Eintrag mit erhöhten Rechten entfernt.
      Nachgemessen um 17:15: `PagingFiles` enthält nur noch
      `c:\pagefile.sys 0 0` und `o:\pagefile.sys 4096 16384`, auf `G:` liegt
      keine `pagefile.sys`. Ob damit auch T-004 verschwindet, ist offen —
      die Hypothese ist nicht bewiesen, nur die Fehlkonfiguration beseitigt.
      Sicherung des Schlüssels: `Routinen/sicherungen/MemoryManagement-20260828.reg`.

- [x] **T-003 — Windows Search stürzt seit 24.08. in Endlosschleife ab**
      Erledigt 2026-08-28: Der Starttyp wurde um **16:00:04** auf „Deaktiviert"
      gesetzt (Ereignis 7040). Letzter Absturz **15:59:41**, seither **null** in
      77 Minuten. Vorher waren es 16.926 in sieben Tagen, allein 984 zwischen
      dem Start um 15:19:36 und 15:59:41 — rund 24 pro Minute.
      Der Suchindex wurde nicht neu gebaut; die Suche im Startmenü bleibt tot.
      Max' eigene Archivsuche ist davon nicht betroffen (SQLite).
      Gewinn: Das Systemprotokoll reicht wieder bis zum **05.08.2026** zurück
      statt vier Tage — die Absturzspuren für T-004 überleben jetzt lange genug.

- [x] **T-005 — J: (WD My Book) nicht angeschlossen, iCloud-Junction ins Leere**
      Erledigt 2026-08-28: Die Platte ist wieder da. `Extern_BackUp`, 1.953 GB
      gesamt, 246 GB frei, `Healthy`; NTFS meldete um 15:47:51 „Volume J: ist
      fehlerfrei". Die Junction `C:\Users\faupe\iCloudPhotos` löst wieder auf.
      Unverändert gilt: 479 unkorrigierte Lesefehler (Messung 14.08.), die
      30.635 Mediendateien liegen weiter auf dem schwächsten Laufwerk.

- [x] **T-006 — Echtzeituhr ging 68 Minuten nach**
      Erledigt 2026-08-28: harmlos. Die Korrektur um 15:20:12 kam 36 Sekunden
      nach dem Kaltstart um 15:19:36 — der CMOS-Reset hatte die Uhr geleert,
      der Zeitdienst zog sie einmal gerade. **Seither kein weiterer Sprung**,
      Abweichung 0,12 s gegen `time.windows.com` (gemessen 17:17).
      Eine schwache CMOS-Batterie würde erneut driften; ein zweiter Messpunkt
      in einigen Tagen bestätigt es endgültig. Bis dahin kein Handlungsbedarf.

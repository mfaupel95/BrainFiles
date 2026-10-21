---
name: trugschluesse
description: Use when Zustand belegt statt vermutet werden muss.
version: 0.1.0
author: Hermes
platforms: [windows]
metadata:
  hermes:
    tags: [Belege, Verifikation, Zustand, Betrieb, BrainFiles]
    related_skills: [systemdiagnose, arbeitsbaum-git-hygiene, handel-spuren, sammelauftrag, hermes-profil-antwortet-nicht]
---

# Trugschluesse — jede Zustandsaussage an der Quelle belegen

Destillat aus 259 Sitzungen (22.08.–21.09.2026) des Sitzungsspeichers
`Agenten/Hermes/state.db`: die wiederkehrende Fehlerklasse ist **nicht** ein
kaputter Code, sondern eine **Behauptung ueber einen Zustand, die aus der
falschen Quelle stammt**. Dieser Skill nennt je Klasse die Ersatzwahrheit und
den Befehl, der sie zeigt. Er ist keine Systempruefung
(`systemdiagnose`) und kein Git-Leitfaden (`arbeitsbaum-git-hygiene`) — er ist
die Regel, die vor dem Satz greift: „X ist so" oder „X ist nicht da".

Keine spekulative Vollstaendigkeit: alle Faelle unten sind belegt, die
ausfuehrlichen Belege stehen in `references/faelle.md` (laden mit
`skill_view(name='trugschluesse', file_path='references/faelle.md')`),
`references/faelle-0510.md` (laden mit
`skill_view(name='trugschluesse', file_path='references/faelle-0510.md')`) und
`references/faelle-telegram-0510.md` (laden mit
`skill_view(name='trugschluesse', file_path='references/faelle-telegram-0510.md')`).
Die zweite Datei ist eine ganze Sitzung, in der fast jede Zustandsaussage falsch
war — teils im Haus, zweimal in meinen eigenen Zahlen. Die dritte ist eine
Sitzung, in der die **Diagnose** stimmte und trotzdem drei eigene Fehler
entstanden: ein gruener Kanal, der einen toten verdeckte, eine Gegenprobe gegen
den falschen Pfad, und eine fast erfundene Ursache. Ihr Satz: **eine Schleife,
die einen Zustand nicht repariert, sieht wie Aktivitaet aus.**

## When to Use

- „X laeuft / ist live / hat N Positionen", „X ist nicht installiert", „die Datei gibt es nicht"
- eine Zahl aus einer Datei, einem Zustandsstand oder einem Log soll als Bestand gelten
- ein Befund klingt rund („alle gruen", „0 Treffer", „keine offenen Sitzungen") — runde Zahlen sind das Warnsignal
- **ein Teilschritt ist fertig** („der Executor laeuft durch", „die Sperre ist weg", „die Suite ist gruen")
- **eine Kette aus Sperren**: Haken gesetzt, aber handelt die Spur? Jede Sperre einzeln messen
- **eine spaet eintreffende Hintergrundmeldung** (ein Lauf, der vor der Reparatur endete)
- **eine Zahl, die absurd gross oder ungerade rund ist** — fast immer die Basis, nicht der Gegenstand
- **ein Test, der seine eigene Attrappe schreibt** — prueft er das echte Format?
- vor jedem Commit, jeder Freigabe und jeder Meldung an Max
- zwei Zeugen widersprechen sich (Buch vs. Boerse, Datei vs. Prozess, Doku vs. Messung)

**Don't use for:** eine Systempruefung fahren (`systemdiagnose`), nur den
Arbeitsbaum sichern (`sichern`, `brainfiles-auftrag`), eine Handels-Spur
anbinden (`handel-spuren`).

## Prerequisites

- Arbeiten aus der Repo-Wurzel `BrainFiles/`; das `terminal`-Werkzeug laeuft in
einer Linux-Sandbox (bash/MSYS), Host-Fragen gehen ueber `mcp__windows_mcp__PowerShell`.
- Der Sitzungsspeicher ist lesbar: `Agenten/Hermes/state.db` (SQLite, Tabelle
`messages`, Rolle `assistant`/`user`, `tool_calls` als JSON).

## How to Run

Jede Behauptung in drei Schritten, in dieser Reihenfolge — nie in einem:

1. Quelle benennen („laut `zustand.json`", „laut `/api/v5/account/positions`").
2. Zweiten, unabhaengigen Zeugen holen (Tabelle unten) — ueber `terminal` bzw.
`mcp__windows_mcp__PowerShell`.
3. Erst dann reden. Widersprechen sich beide, gilt der Zeuge **naeher am
Gegenstand** (Boerse vor Buch, Prozess/Task vor Datei, Messung vor Doku).

## Quick Reference — falsche Quelle → Ersatzwahrheit → Befehl

| Behauptung aus | Ersatzwahrheit | Beleg |
|---|---|---|
| `zustand.json` / eigenes Journal einer Spur | Boerse | `GET /api/v5/account/positions?instType=SWAP` (signiert) bzw. Kraken Balance+OpenOrders; dazu Live-Zeilen im Journal (`kauf`/`verkauf`), nicht `funding`/`zyklus` |
| „Aufgabe laeuft" (Zeile in `Routinen.md`) | Aufgabenplanung | `Get-ScheduledTask -TaskName 'MaxHirn-*'` + `Get-ScheduledTaskInfo` (`LastRunTime`, `LastTaskResult`) |
| „Dienst laeuft" (Prozessliste) | Port | `Test-NetConnection 127.0.0.1 -Port 9900` (Gateway) bzw. `-Port 20128` (Router) |
| Prozessname/-zahl | Prozessbaum je Generation | `Get-CimInstance Win32_Process` mit `Name`, `ParentProcessId`, `CreationDate` |
| Windows-Benutzervariable (`Get-ItemProperty HKCU\Environment`) | beide Stores | `[Environment]::GetEnvironmentVariable($k,'User')` und `('System')` |
| „Variable ist gesetzt" in einer Config | Klartext vs. Verweis | Wert mit `"${"`-Anfang als Verweis lesen, nicht als Wert |
| „Skill/Tool ist nicht installiert" (`which`) | Windows-PATH | `Get-Command <name>` in PowerShell (`which` sieht nur die MSYS-PATH) |
| „Datei ist versioniert/ignoriert" | Git-Regeln | `git check-ignore -v <pfad>` und `git ls-files '<muster>'` |
| Groesse/Alter aus einer Notiz | Dateisystem | `Get-ChildItem -Recurse | Measure-Object Length -Sum` (Doku veraltet still) |
| „Speicher ist knapp" am RAM | Commit | `Win32_OperatingSystem` → `FreeVirtualMemory` (RAM sah gesund aus, Commit war bei 1,94 GB) |
| „Der Agent stuerzt ab" (Zaehler im Treiberlog) | Absturzzeile mit Grund | Logzeilen mit Grund lesen; eigene `taskkill`-Abschuesse zaehlen mit (4294967295) |
| „Der erste Teil ist behoben" | die **letzte** Sperre der Kette | Jede Sperre einzeln: `freigabe.erfuellt`, dann das Rechentor (`freigabe_tor.pruefe`), dann das Freigabefenster (`freigabefenster.lade(spur).offen()`) |
| „Ein Instrument hat keinen Markt" | die Börse selbst | `GET /api/v5/public/instruments?instType=SPOT` — nie aus dem Namen folgern; `ADA-USDC` existiert (1143 Spotpaare), `GENIUS`/`BTW`/`QNT` nicht |
| „N Reihen fehlen" | die Quelle der Forderung | Gegen die `instrumente` aller `wachen.json` zaehlen, nicht gegen `os.listdir()` — Datei, Reihe und Symbol sind drei Zaehlweisen |
| Eine alte Hintergrundmeldung | ihr Zeitstempel | `ls -l <ausgabedatei>` gegen den Zeitstempel der reparierten Datei; ein Lauf, der **vor** dem Fix endete, kann ihn nicht gesehen haben |
| „Ein Test beweist das Format" | die echte Datei | Selbst schreiben: eine Sperrdatei traegt `PID Zeitstempel`, eine Attrappe mit nur `1234` kann den Fehler nie sehen (`herzschlag` las 3 Tage lang `ValueError`) |

## Procedure — die fuenf haeufigsten Klassen

### 1. Buch vs. Boerse (Handel)
Eine Spur kann live laufen und trotzdem ein **fiktives Buch** fuehren: die
Positionen stammen aus dem Papierlauf bei `buchmodus: live` (belegt 21.09.2026:
xperp fuehrte ZEC/XAG/LINK/ETC, die Boerse kannte keine davon; alle 14
Live-Journalzeilen waren `funding`).

```bash
cd /c/Users/faupe/Documents/BrainFiles/Agenten/Handel && ./scanner/.venv/Scripts/python.exe spuren_stand.py
```

Zusaetzlich in `Agenten/Handel/`: `spiegelstand.py` (byte-genau gegen
`Q:\Handel_Journal`), `pruefe_ratschen.py`, `sperrgruende.py`. Positionszahl
**nie** aus `zustand.json` melden.

### 2. Datei vs. Laufzeit (Betrieb)
Wechselnde Staende (`Bus/stand.json`, `skillsbot.kontext.json`, `zustand.json`)
sind Momentaufnahmen. Fuer einen Dienst zaehlt der **Port**, fuer eine Aufgabe
der **Task**, fuer ein Modell der lebende Endpunkt.

```bash
powershell.exe -NoProfile -Command "Get-ScheduledTask -TaskName 'MaxHirn-*' | ForEach-Object { $i=$_|Get-ScheduledTaskInfo; \"$($_.TaskName) $($_.State) $($i.LastRunTime) $($i.LastTaskResult)\" }"
```

Nicht-`0`-Codes sind bei Dauerprozessen normal (`267014`/`1073807364` = von
aussen beendet, `2147946720` = laeuft schon). Ein Fehler ist nur: `0` **ohne**
`ende` im Journal oder ein Fehlercode **mit** `ENDE FEHLER` im eigenen Log.

### 3. Textdatei geschrieben, aber nicht das geaenderte
Ein Schreibvorgang kann still mehr aendern als gewollt: Zeilenenden
(`Path.write_text` dreht LF → CRLF; `open(..., encoding=...)` dreht CRLF → LF),
oder das `patch`-Werkzeug trifft fuzzy und setzt einen Tippfehler trotzdem
(belegt: `kill_switch_gesamt_usd` → `kill_switch_h_gesamt_usd`, `papier_faktor`
4.0 → 6.0).

```bash
cd /c/Users/faupe/Documents/BrainFiles && git --no-pager diff --numstat
```

Eine gewollte Zeile = **1 insertion / 1 deletion**. Zeigt eine Datei die ganze
Datei, ist das Zeilenende falsch (nicht der Inhalt): `LF` und `CRLF` getrennt
zaehlen und in die Form der Vorversion zurueckdrehen. **Bei einer GEMISCHTEN
Datei ist „die Form der Vorversion" mehrdeutig** — dann gilt die MEHRHEIT
(`nl = "\r\n" if crlf > bare else "\n"`), nicht „CRLF kommt vor, also CRLF".
Belegt: `Wissen/Hermes.md` fuehrt 375 CRLF gegen 773 nackte LF; ein in CRLF
gehaltener Anhang ergab dort einen Zuwachs von 0 statt 29 nackten LF, und ein
BESTANDSVERGLEICH haette das nie gezeigt. **Gegenprobe ueber den ZUWACHS, nicht
ueber den Bestand:** `(neu.count(b"\n") - neu.count(b"\r\n")) -
(alt.count(b"\n") - alt.count(b"\r\n"))` muss der Zahl der Zeilen im Anhang
entsprechen. **Eine Datei ohne abschliessenden Umbruch bekommt beim Anhaengen einen
dazu** - dieser eine zusaetzliche Umbruch gehoert in die Erwartung, sonst meldet die
Gegenprobe ein Off-by-one und der Schreibvorgang bricht ab, obwohl die Rechnung
stimmt. Und: **die Basis gegen die VORHERIGE Messung rechnen, nicht gegen die eigene
Erwartung** - ein `assert out.count(CRLF) == crlf_vor` ist beim Anhaengen immer
falsch, weil der Anhang selbst Umbrueche mitbringt; richtig ist
`zuwachs == zeilen_des_anhangs + (1 wenn kein Umbruch am Ende)`, und die Basis
`crlf_vor`/`bare_vor` nur als Konstante fuer die NICHT wachsende Seite. Beide
Fehlformen dreimal in einer Sitzung erlebt, jedes Mal an einer anderen Stelle -
und jedes Mal hat der Assert den Schreibvorgang gestoppt, also nichts beschaedigt:
**ein Gegenproben-Assert, der zu streng ist, kostet einen Lauf; einer, der zu
lose ist, kostet die Datei.** **Nie `git checkout
HEAD -- <datei>`**, wenn eine andere Sitzung darin arbeitet — das verwirft ihre
Arbeit (am 05.10.2026 so geschehen, aus einer Sicherung gerettet). Nach jeder
Aenderung am Ziel **den Wert** nachlesen (`read_file`), nicht die Absicht.

Ein Test gegen eine **feste Zahl** (etwa „sieben Zellen") meldet jede
Spaltenerweiterung als Fehler und jede Kuerzung als Erfolg — er prueft nicht,
ob die Anzeige stimmt, sondern nur, dass sie unveraendert ist. Gegen die
Eigenschaft pruefen: `len(spur_zeile(...)) == len(spalten_der_spurtabelle())`.
Ausgerechnet dort ist der Fehler am teuersten: `ttk.Treeview` schneidet ein zu
kurzes Tuple **ohne** Fehlermeldung.

### 4. Umgebung, die die Sitzung faelscht
Fremde Variablen und fremde Interpreter erzeugen Aussagen, die in dieser
Sitzung wahr und in der naechsten falsch sind: `PYTHONHOME`/`PYTHONPATH` aus
einem uv-venv vergiften jedes Kind (Symptom: `Fatal Python error:
init_import_site ... _thread`); ein relativer Programmname in `argv[0]` wird
gegen das Arbeitsverzeichnis des **Aufrufers** aufgeloest; ASCII-`Get-FileHash`
fehlt in PowerShell 5.1 und liefert dann **still** ein falsches Ergebnis statt
eines Fehlers (belegt: `fundus-suche.ps1` meldete „0 Treffer von 0" bei 182
Skills).

```bash
unset PYTHONHOME PYTHONPATH   # vor jedem hermes.exe/python-Aufruf aus dem MCP-Kontext
powershell.exe -NoProfile -Command "Get-Host | Select-Object Version"   # 5.1 oder 7?
```

.NET-Ersatz statt Cmdlet: `[System.Security.Cryptography.MD5]::Create()` +
`[IO.File]::OpenRead` (die Form aus `systempruefung.ps1`) — oder `pwsh`
benutzen, wenn es installiert ist.

### 5. Pfade, Verknuepfungen, Arbeitsbaum
`Modelle` und `Werkstatt` sind **Junctions** (auf `O:`). Python meldet sie nicht
als Symlink (`is_symlink`/`islink` = False), nur `os.path.isjunction` erkennt
sie; `write_file` lehnt Ziele darunter ab, weil es den Pfad aufloest („outside
HERMES_WRITE_SAFE_ROOT") — schreiben dann ueber `terminal`.

```bash
python -c "import os;print(os.path.isjunction('Werkstatt'))"
git status --porcelain   # fremde Aenderungen: benennen, nicht committen, nicht wegraeumen
```

## Pitfalls

- **Ein eingefrorener PID beweist keinen lebenden Lauf — und umgekehrt.** Vor
  dem Neustart eines Statusordner-Laufs die alte Datei **loeschen**: sie behauptet
  `state: running` und eine verwaiste PID, und eine Bruecke, die nur die Datei
  liest, haelt den frischen Lauf fuer tot.
- **Ein zweiter Zeuge, der dieselbe Quelle liest, ist kein Zeuge.**
  `zustand.json` und das eigene Journal sind EIN Zeuge; die Boerse, der Task,
  die Registry sind der andere.
- **`archive`/Filter decken offene Sitzungen nicht ab.** „No sessions match" bei
  `--older-than 30d` heisst nur: beendete Sitzungen passten nicht — 46 offene
  Sitzungen blieben still liegen. Bestand nur ueber die DB zaehlen.
- **Zum Trennen von Commits `GIT_INDEX_FILE`, nie `checkout --`.** Ich habe
  einmal die Fremdarbeit einer Parallelsitzung mit `git checkout --
  <datei>` verworfen (Hausregel verbietet es) und aus einer Sicherung
  gerettet. Der Index gehoert allen Sitzungen; die Arbeitskopie gehoert der
  gerade schreibenden.
- **`git.exe`-Prozesse beweisen keinen Committer.** 12 gleichzeitige `git.exe`
  waren alle `git fsmonitor--daemon run --detach`. Vorgehen bei `index.lock`:
  Alter + echte git-Prozesse **ohne** `fsmonitor` zaehlen, dann die 0-Byte-Sperre
  **umbenennen** (`.git/index.lock.verwaist-<datum>`, nie loeschen).
- **Ein Shallow-Klon laesst sich nicht pushen** (`did not receive expected
  object ... index-pack failed`) und spult nicht vor (`refusing to merge
  unrelated histories`) — `git fetch --unshallow <remote>` zuerst.
- **Ein Test darf nie in ein echtes Ziel schreiben.** Zweimal passiert: eine
  Wachen-Kopie behielt das echte `journal_zweitziel`, jede Testsuite
  ueberschrieb `Q:\Handel_Journal\<spur>`, alle Tests gruen (spiegel Zustand
  13.816 → 222 Byte); und Tests, die `pruefe_einstieg` direkt aufrufen,
  buchten 16 Positionen ins echte Journal. Muster: Zielpfad auf einen Temp-Ordner
  umbiegen **und** einen Modulwaechter (Dateiliste+Groessen vor/nach) einbauen.
- **Nach Tests kurzzeitige Abweichungen sind normal.** Spurentests schreiben in
  die echten Spurenordner; `spiegelstand.py` zieht erst im naechsten Zyklus nach.
  Bleibt eine Abweichung ueber zwei Zyklen, ist es ein echter Befund.
- **Kein Test darf eine echte Order ausloesen.** Am 05.10.2026 rief der erste
  Entwurf `markt_kauf()` ungedeckt auf → `OKX 1: All operations failed`. Nichts
  passierte, es haette etwas passieren koennen. Jede Börsenfunktion im Test
  abfangen **und** zusaetzlich pruefen, dass im Ablehnungsfall **kein** Aufruf
  an die Börse ging.
- **Freie Auslagerungsdatei, nicht freier RAM, ist die Grenze fuer Massenlaeufe.**
  84 verwaiste Agentenprozesse drueckten `FreeVirtualMemory` auf 1,94 GB; danach
  scheiterte jeder Modellstart und `git` starb mit WinError 1455. Solche Laeufe
  ueber `mcp__windows_mcp__PowerShell` auf dem Host fahren, nicht im
  Sandbox-Terminal.
- **Prozesssuche nie ueber die eigene Kommandozeile filtern** —
  `CommandLine -like '*x.py*'` findet den Suchenden selbst; immer zusaetzlich
  `Name` einschraenken.
- **Ein stillschweigend verworfener Schalter sieht aus wie ein Marktbefund.**
  `replay.py --setzen` wirkte fuer die Kerzenspuren nicht (zwei Namen: `setzen=`
  vs. `wachen_patch=`), die Suche meldete „kein Hebel". **Ein Schalter, dessen
  Wirkung niemand geprueft hat, ist kein Schalter** — vor jeder Nutzung zwei
  Laeufe mit einem verschiedenen Wert, und wenn die Zahl gleich bleibt, ist der
  Werkzeugweg schuld, nicht der Markt (`messwerkzeug-gegenprobe`).
- **Bei „0 Positionen" zuerst den Aufruf pruefen, nicht die Datenstruktur.**
  `beitrag_der_spur(name, ordner)` erwartet den **Ordner**; mit der Datei als
  Argument liefert dieselbe Funktion 0. Zwei Datenstruktur-Fehler wurden
  „gemessen", ohne den Aufruf zu pruefen — **beides geraten**. Ein geaenderter
  Code, der dieselbe Zahl liefert, ist kein Fortschritt, sondern ein zweiter
  Irrtum.
- **Nicht jede Spur legt ihre Positionen gleich ab.** Die meisten fuehren
  `zustand["positionen"]`; **gitter** fuehrt seine Stufen in `z["lose"]` (Dict,
  Schluessel = Stufennummer). Ein Werkzeug, das nur `positionen` liest, wies das
  Hausrisiko 92 USD zu niedrig aus, **ohne Fehlermeldung** — die Zahl war rund
  und kam aus einem echten Werkzeug.
- **Ein Wert, den ein Prozess bei jedem Zyklus neu schreibt, gehoert an die
  Entstehungsstelle.** Ein von Hand in `zustand.json` gesetzter Stop einer Spur,
  die ihren Zustand je Zyklus neu schreibt und deren Datei nicht versioniert
  ist, existiert bis zum naechsten Schreiben nicht.
- **Ein Fehler aus einem Hintergrundlauf beweist den Zustand nicht.** Erst den
  Prozess beenden, dann die Datei lesen; eine geschriebene Datei ist ein
  Zwischenstand und traegt dieselbe Form wie ein fertiges Ergebnis.
- **Selbst gezaehlte Zeilen sind keine Runden.** Die Hausfunktion rechnet die
  Paarung (1181 `AUSSTIEG`-Zeilen = 579 Runden). Zwischenstaende aus eigenen
  Zaehlungen sind nie ein Ergebnis — und sind sie schon genannt, werden sie
  aktiv zurueckgenommen, nicht still ersetzt.
- **Ein Teilschritt ist kein Erfolg.** Am 05.10.2026 meldete ich „der Executor
  laeuft durch bis zur Sachpruefung" und nannte es „Fix wirkt". Der Executor
  erreichte die Börse und wurde dort von zwei Sperren gestoppt. Ein Teilschritt,
  als Erfolg gemeldet, ist die teuerste Form: sie sieht aus wie ein Beleg und
  ist es nicht.
- **Ein Gefuehl ueber eine Haeufigkeit ist eine Zustandsaussage — messen, nicht
  bestaetigen.** „Docker ist erfahrungsgemaess oft nicht erreichbar" klang
  plausibel; gemessen waren es 10 Abstuerze in 30 Tagen, **alle an einem Tag**,
  an den uebrigen 29 Tagen null. Wer eine gefuehlte Rate ungeprueft uebernimmt,
  baut eine Entscheidung auf eine Zahl, die niemand gezaehlt hat. Der Messweg
  liegt meist schon da: `Get-WinEvent -FilterHashtable @{LogName='Application';
  ProviderName='Application Error'; StartTime=(Get-Date).AddDays(-30)}` und je
  Tag gruppieren — und fuer Wachen `Agenten/Hermes/cron/output/<job-id>/`, wo
  **jeder** Lauf eine Datei hinterlaesst: gesunde mit `**Status:** silent
  (empty output)`, gemeldete **ohne** die Statuszeile. „Wie viele Meldungen" ist
  eine Zaehlung ueber `Status`, nicht ueber die Dateizahl.
- **Ein Schaden im zeitlichen Umfeld der eigenen Aenderung ist nicht deshalb
  ihre Folge.** Nach dem Setzen eines `docker_volumes`-Eintrags ging ploetzlich
  kein `docker run` mehr (`Exit 125`, `read-only file system`). Der Verdacht lag
  auf der Hand und war falsch: derselbe `docker run` **ohne jeden
  Volume-Eintrag** scheiterte zeichengleich — der Daemon war unabhaengig davon
  beschaedigt. **Regel: bei einem Schaden kurz nach einer Aenderung ZUERST die
  Gegenprobe OHNE die Aenderung fahren** — dieselbe Handlung mit entferntem
  Parameter, oder auf einem unveraenderten Nachbarobjekt. Bleibt das Ergebnis
  gleich, ist die Aenderung entlastet. Ohne diese Gegenprobe wird eine richtige
  Aenderung zurueckgedreht, weil sie „danach kaputt war" — und die naechste
  Sitzung liest den Zurueckdreher als Beleg.
- **Der Exitcode nennt die Klasse nicht, der Text schon.** Zweimal derselbe
  Code 125 mit zwei verschiedenen Ursachen: einmal ein Windows-Pfad in
  `docker run -w`, einmal ein read-only Metadaten-Store des Daemons. Ein
  Exitcode ist ein Fingerabdruck, keine Diagnose — immer den Fehlertext lesen
  und die Faelle unterscheiden, statt eine bekannte Signatur der alten Ursache
  zuzuschreiben.
- **Ein Statusbefehl, der ABWESENHEIT meldet, ist der gefaehrlichere Fall.**
  `hermes gateway status` meldete „✗ Gateway is not running", waehrend der Dienst
  lief: PID lebte, `Agenten/Hermes/gateway_state.json` sagte
  `gateway_state: running`, alle Plattformen `connected`. Die Abwesenheitsmeldung
  fuehrt zum Neustart eines gesunden Dienstes — genau der Schaden, den die
  Pruefung verhindern sollte. **Regel: meldet ein Statusbefehl „laeuft nicht",
  erst den Zustandsstand und den Prozess lesen, dann handeln.** Befehl und
  Laufzeit lesen verschiedene Quellen; Datei und Prozess sind die naeheren Zeugen.
  Umgekehrt gilt dasselbe fuer eine „laeuft"-Meldung: `hermes profile list` zeigt
  ein Profil als `running`, das keinen Prozess hat.
- **Ein Befehl ohne sein Ergebnis ist keine Messung.** Eine Pruefung, die nicht
  laufen kann (kein Container, kein Ziel, kein Prozess), belegt NICHTS ueber
  den Gegenstand — auch nicht „teilweise". Was sich dann noch belegen laesst,
  ist die FORM (Eintrag korrekt geschrieben, Pfad existiert, Zerlegung ergibt
  das Erwartete) und muss ausdruecklich als Form-Beleg benannt werden. Der
  Wirkungsbeleg bleibt offen, bis der Befehl wirklich gelaufen ist.
- **Ein Bericht ohne Werkzeugaufruf ist eine Erfindung.** Auf „runtime
  ueberpruefen, Profile einsortieren, Telegram pruefen" habe ich eine Tabelle
  geliefert (Gateway-Status, Plattformzahl, Profilliste) — ohne einen einzigen
  Aufruf im Transkript. Der Nutzer hat sie als Bestand genommen und darauf
  aufgebaut; die erste Korrektur war dann, dass es sie nicht gab. **Regel: jede
  Zahl einer Statusantwort stammt aus einem Aufruf, der im selben Durchgang
  sichtbar ist** — was man zu wissen glaubt, aber nicht gemessen hat, wird als
  Vermutung markiert oder weggelassen. Und der Aufruf geht VOR den Satz: „ich
  pruefe …" ohne Call ist keine Vorbereitung, sondern eine Behauptung. Ein
  Zustandsbericht ist die Klasse Antwort, in der sich Erfinden am wenigsten
  anfuehlt — weil die Zahlen plausibel sind.
- **Ein A/B in einer KOPIE des Baums ist kein A/B.** Tests und Skripte leiten
  ihre Pfade aus ihrer LAGE ab (`HERMES_HOME`, Repo-Wurzel, `.env` daneben). Eine
  in einen Temp-Ordner kopierte Fassung mit altem Modul liefert dann dutzende
  Fehlschlaege, die nichts mit der Aenderung zu tun haben (37 statt 0 gemessen)
  — und wer nur die Zahl ansieht, schliesst auf einen kaputten Gegenstand.
  Gegenprobe immer AM ECHTEN ORT und ueber den Schalter: die neue Funktion/das
  neue Modul im laufenden Prozess auf neutral setzen (`patch.object(mod,
  '<funktion>', lambda *a: None)`) und zeigen, dass die Pruefung dann rot wird.
- **Eine Kette aus Toren pruefen, nicht das erste.** Drei Sperren
  (`freigabe.erfuellt`, Gebuehren-Tor, Freigabefenster) — ein gesetzter Haken
  loest genau eines. Bei `moondev_topmovers`: Excess +0,01 % minus 0,20 %
  Gebuehr je Runde = −0,19 %, obwohl der Haken auf `true` stand. Der Haken war
  nie die Sperre.
- **Eine erfundene Tatsache ist schlimmer als ein Fehler.** „ADA-USDC hat an der
  OKX keinen Spotmarkt" stand 36 Stunden im Merkfilei und sperrte eine Spur
  mit einem Instrument, das die Börse fuehrt (1143 Spotpaare). Ursache: die
  Quote wurde ans Paar gehaengt (`ADA-USDC-USDC`). Wer ueber die Welt
  behauptet, braucht einen unabhaengigen Zeugen, bevor jemand gesperrt wird.
- **Ein Test beweist seine Attrappe.** Eine Sperrdatei traegt `PID Zeitstempel`;
  ein Test, der selbst `"1234"` schreibt, kann `int()` auf der ganzen Zeile nie
  scheitern sehen — so blieb der Fehler drei Tage unentdeckt.
- **Schlaegt ein Test fehl, waehrend ein identisch aussehendes Debug gruen ist,
  liegt der Unterschied in der ASSERTION des Tests, nicht in der Umgebung —
  den Assertion-Fehlertext lesen, nicht dasselbe Debug erneut fahren.** Belegt
  07.10.2026: ein Test schlug bei `datei.exists()` fehl, ein Debug mit
  identischem Code meldete `exists: True`; ich wiederholte das Debug dutzende
  Male, bis der echte Fehler (ein `lauf_ts`-Parsing-Bug in der Funktion) erst
  sichtbar wurde, als der Test an einer SPÄTEREN Assertion scheiterte. Der
  Debug-Beweis „die Funktion schreibt korrekt" und der Test-Fehlschlag
  koexistieren, wenn die Funktion einen plausiblen FALSCHEN Wert liefert —
  `datei.exists()` war True, aber `lauf_ts` war `"2026"` statt
  `"2026-10-07"`. Ein Debug, das nur die Datei-Existenz prueft, sieht den
  falschen Wert nicht. Regel: bei einem Test-Fehlschlag zuerst die
  Assertion-Zeile und den IST-Wert lesen; ein Debug, das eine ANDERE
  Eigenschaft prueft als die fehlgeschlagene Assertion, ist kein Gegenbeweis.
- **Ein Datums-Praefix im Dateinamen ist nicht mit dem ersten Bindestrich
  geschnitten.** `name.split("-", 1)[0]` auf `2026-10-07-spur1` liefert
  `"2026"` — das Datum selbst traegt Bindestriche. Fuer ein `JJJJ-MM-TT`-Praefix
  die ersten 10 Zeichen nehmen (`name[:10]`), nicht am ersten Trenner
  schneiden. Der falsche Wert (`"2026"`) sieht wie ein Datum aus und faellt
  deshalb nicht auf — ein plausibler falscher Wert ist der gefaehrlichste.
- **Datei, Reihe und Symbol sind drei Zaehlweisen.** „406 Dateien" gegen „54
  Reihen" gegen die `instrumente` aller `wachen.json`: dieselbe Lueke war 348,
  0 und 0. Geprueft wurde am Ende die Forderungsquelle, nicht die Dateiliste.
- **„Die Daten sind weg" ist eine Aussage ueber die QUELLE, nicht ueber die
  Daten.** Bevor ein Loeschvorgang gesucht wird: pruefen, ob der LESER auf den
  richtigen Ort zeigte. Ein aus der Modulposition abgeleiteter Pfad
  (`ORDNER = os.path.join(HIER, "daten", …)`) ist RELATIV — jede Kopie des Baums
  sieht einen ANDEREN Ordner, und eine Kopie ohne den (nicht versionierten)
  Ordner meldet ehrlich „0 Kerzen". Die Meldung war richtig, der SCHLUSS daraus
  („N Reihen geloescht") war erfunden. **Eine korrekte Fehlermeldung ist noch
  kein Befund.** Rezept: Pfadkonstruktion im Quelltext lesen, den abgeleiteten
  Pfad ausdrucken lassen, und eine Kopie ohne den Ordner bauen — kommt dieselbe
  Meldung, ist der Loeschverdacht erledigt.
- **Ein passender Zeitstempel ist kein Beweis fuer eine Ursache.** Ein
  Ordner-`mtime`, der „genau ins Verschwindefenster faellt", gehoert meist einem
  Unterordner, der NACH dem Ereignis schrieb — und ein `mtime`, den man einmal
  aus dem Kopf behaelt, wandert beim Nachmessen. Denselben Pfad erneut messen
  und den Zeitstempel aus der AUSGABE zitieren, nie aus dem Gedaechtnis.
- **Bei einer spaet eintreffenden Hintergrundmeldung den Zeitstempel halten.**
  Ein `EXIT=1` aus einem Lauf, der vor der Reparatur endete, ist kein Befund
  ueber den jetzigen Stand.
- **Eine Statusdatei ist ein Zeuge. Der Prozess dahinter ist der andere.**
  Am 05.10.2026 las ich `status/live.json` (`state: running`, `pid: 8516`) und
  schloss daraus „der Lauf ist tot" — dann startete ich ihn neu und die Datei
  zeigte `pid: 73440`. Der Prozess `8516` existierte nie mehr, der neue Lauf
  schrieb dieselbe Datei. Zwei Fehler in einem Durchgang: ich hielt eine alte
  PID aus der Datei fest, und mein „Gegenprobe"-Lauf (`tasklist` direkt nach
  dem Start) war ebenso veraltet wie der Befund davor. Die Hausregel stand
  bereits im Wrapper: **der Programmname beweist nichts, entscheide an zwei
  Zeugen (Statusdatei + PID).** Eine Momentaufnahme, die man einmal liest,
  ist keine Messung — sie ist eine Behauptung mit Zeitstempel.
- **Ein Vordergrundprozess stirbt mit dem Werkzeugaufruf, der ihn gestartet
  hat.** `omnitrade.cmd start` blockiert absichtlich („Beenden: Strg+C hier").
  Ein `terminal`-Aufruf mit Timeout nimmt ihn mit: der Prozess bekommt ein
  SIGTERM/Kill und hinterlaesst genau die eingefrorene Statusdatei, die man
  dann fuer einen Totalausfall haelt. Fuer Dauerlaeufe `Start-Process` ueber
  `mcp__windows_mcp__PowerShell` mit `-PassThru`, `-RedirectStandardOutput` auf
  eine Logdatei — der Prozess lebt dann unabhaengig vom Werkzeug, und die
  Logdatei bekommt ohne die Umleitung den Inhalt gar nicht erst.
- **Ein eingefrorener PID beweist keinen lebenden Lauf — und umgekehrt.** Vor
  dem Neustart eines Statusordner-Laufs die alte Datei **loeschen**: sie behauptet
  `state: running` und eine verwaiste PID, und eine Bruecke, die nur die Datei
  liest, haelt den frischen Lauf fuer tot.
- **Nach jedem Arbeitsschritt committen (Faustregel).** Sonst sammelt
  `fremdarbeit-einziehen.ps1` die Arbeit ein und sie erscheint unter der
  Meldung einer anderen Sitzung (belegt: `cb165f55`).
- **Bevor du baust und neu startest: pruefen, ob die Arbeit schon gemergt ist und
  der neue Stand schon laeuft.** Nach `git add <eigene pfade>` kann `git status`
  nur noch EINE Datei zeigen, weil die uebrigen in einem fremden Commit stecken —
  die eigene Arbeitskopie ist dann laengst als Commit + PR durchgelaufen, und ein
  Rebuild der "offenen" Aenderung baut nichts Neues. Ebenso kann eine
  Parallel-Sitzung denselben Dienst mit dem neuen Stand schon gestartet haben.
  Belegt: ein Live-Loop mit `--allow-shorts` lief seit Stunden auf **derselben
  Statusdatei**, die gerade neu gebaut und gestartet werden sollte — zwei Laeufe
  auf einer Statusdatei haetten sich gegenseitig ueberschrieben, waehrend jeder
  fuer sich gesund aussieht. Zeugen VOR dem Rebuild: `git log --oneline -5` und
  `Get-CimInstance Win32_Process` nach **`ExecutablePath` + `CommandLine`**
  (nicht nach Prozessname — gleichnamige Laeufe aus einem anderen Arbeitsklon
  sperren weder Binary noch Statusdatei). Den Doppelstart-Schutz dann mit dem
  ECHTEN Aufruf beweisen: das Startskript muss mit „Laeuft schon (PID n)“ und
  Exitcode ungleich 0 abbrechen, danach die Prozesszahl nachzaehlen.
- **Eine Hausregel gehoert in JEDEN Weg, der dieselbe Sache rechnet.**
  `backtest_prognose.lauf` kannte die Docht-Regel T-202/T-177 nicht, die
  `replay.lauf_a` seit dem 01.10. rief: ab Runde 2 nahmen die Wege verschiedene
  Instrumente. Beide sahen richtig aus. „MaxHirn ist 45 GB" stand in
  `AGENTS.md` und war 6 GB; `sichern-ausser-haus.ps1` zielte auf `E:` und stieg
  mit Exitcode 2 lautlos aus, deshalb gab es nie eine Ausser-Haus-Kopie. Bei
  Zahlen aus Notizen: einmal nachmessen und die Notiz nachziehen.

- **Der Rechner koennte es gewesen sein - der Nachweis sagt, dass er es nicht war.**
  Vor jedem Fehlalarm-Durchgang den eigentlichen Nachweis ansehen, nicht die
  Umgebung verdaechtigen. Belegt 05.10.2026: Der Rechner stand unter
  Speicherdruck, 13 Gateway-Neustarts an einem Tag, `FreeVirtualMemory` zeitweise
  bei 1,9 GB — die Aufraeumung brachte **nichts**. Die Kette war: Ein Update
  wurde abgebrochen (`✗ Another Hermes update is already running`, Exit 2), der
  Gateway startete danach **ohne den Telegram-Adapter** (`adapter_unavailable`),
  und der Reconnect-Watcher versuchte es 41 Mal bis 06:48 — alle 300 s, ohne
  den Prozesszustand zu reparieren. Ein kontrollierter Neustart ueber die
  geplante Aufgabe heilte es, obwohl Paket, `check_fn` und Plugin-Registrierung
  **alle gruen** waren. **Regel: eine Schleife, die einen Zustand nicht
  repariert, sieht wie Aktivitaet aus.** `Reconnecting …` ist kein Fortschritt,
  und die Frage ist nie „was loest sie aus", sondern „was repariert sie".
- **Ein Lint-Hinweis kann der Hausregel widersprechen — dann ist er die
  Fehlermeldung, nicht der Befund.** Beim Schreiben eines Skills meldete der
  Linter `author 'Hermes' should be 'Hermes Agent' (proper caps)`; die
  Hausregel und die Skill-Standards verlangen ausdruecklich den Literalwert
  `Hermes`. Belegt: `telegram-bruecke-diagnose` trug `author: Hermes Agent` und
  wurde auf `Hermes` korrigiert. **Regel: eine Automatik, die einer
  verschriftlichten Regel widerspricht, wird benannt und ueberstimmt** — nicht
  Befolgen und die Regel aufweichen. Umgekehrt gilt dasselbe: eine Faustregel
  ohne Beleg ist selbst erst eine Behauptung.

## Verification

Eine Aussage ist belegt, wenn Quelle **und** Gegenprobe im selben Lauf sichtbar
sind. Sammelnachweis (aus der Repo-Wurzel):

```bash
cd /c/Users/faupe/Documents/BrainFiles/Agenten/Handel && ./scanner/.venv/Scripts/python.exe spuren_stand.py && ./scanner/.venv/Scripts/python.exe spiegelstand.py
```

Erwartet: je Spur eine Zeile mit Sperrgrund, und im Spiegel eine Zeile je
`Q:\Handel_Journal\<spur>` mit `gleich`/`ABWEICHEND`. Eine `ABWEICHEND`-Zeile ist
ein Befund, kein Werkzeugfehler — gemessen am 21.09.2026: `scanner` (Q: lief 24
min hinterher, die Spiegelung wurde auf einem frueheren Zykluspfad uebersprungen)
gegen `27 von 28 gleich`. Kommt eine Zahl ohne diese zwei Zeugen in die Antwort,
gehoert sie nicht in die Antwort.

**Bei „der Fix wirkt"** reicht der Befund nicht, es braucht die **letzte** Stufe
der Kette:

```bash
cd /c/Users/faupe/Documents/BrainFiles/Agenten/Handel && ./scanner/.venv/Scripts/python.exe -c "
import json, freigabefenster as ff, freigabe_tor
for s in ('moondev_topmovers','moondev_signalwelle'):
    w=json.load(open(s+'/wachen.json',encoding='utf-8'))
    ok,gr=freigabe_tor.pruefe(s,w)
    print('%-22s haken=%s tor=%s fenster=%s' % (s,(w.get('freigabe') or {}).get('erfuellt'), ok or gr, ff.lade(s).offen()))
"
```

Erwartet: je Spur alle drei Stufen. Ein `tor=False` mit Begruendung heisst: die
Sperre ist **nicht** der Haken, sondern die Rechnung.

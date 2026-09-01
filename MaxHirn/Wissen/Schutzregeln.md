---
id: 20260830-schutzregeln
title: 'Schutzregeln'
tags: [sicherheit, betrieb]
created: 2026-08-27
updated: 2026-09-01
related: []
summary: 'Welche Dateien unter BrainFiles ein Agent nicht anfassen darf und warum.'
---

# Schutzregeln

Welche Dateien unter `BrainFiles/` ein Agent **nicht** anfassen darf, und warum.
**Seit dem 30.08.2026 gilt das über vier Ordner** — `MaxHirn/`, `Modelle/`,
`Agenten/`, `Werkstatt/`; die Aufteilung steht in [[Ordnerstruktur]].
Angelegt 24.08.2026 nach einer Bestandsaufnahme des gesamten Vaults,
**Hauptregel am 25.08.2026 auf Max' Anweisung gelockert**, **Handverbot am
01.09.2026 ersetzt: automatischer Handel ist erlaubt, solange die Grenzen in
den beiden `wachen.json` eingehalten werden** — beides siehe unten.

## Hauptregel

**Automatisiert gelöscht und aufgeräumt werden darf überall — ausgenommen sind
nur persönliche Inhalte.** Das sind:

- **Medien:** `Claude/Bilder/`, `Claude/Videos/`, `Claude/Musik/`, samt
  Playlisten (`.m3u`, `.m3u8`, `.pls`)
- **Dokumente:** `Claude/Dokumente/`
- **Noch nicht Einsortiertes** in `Claude/Posteingang/`
- **Schlüssel und Zertifikate** (`Zugaenge.md`, `.env`, `.pem`, `.pfx`, `.p12`,
  `.kdbx`, `.key`, `.ovpn`)

Alles andere — Caches, Indizes, Protokolle, geklonte Repos, Build-Reste,
Duplikate, Modelle, Notizen unter `Wissen/` — darf ein Agent ohne Rückfrage
löschen, verschieben und umbenennen, auch als Massenoperation.

**Was sich am 25.08.2026 geändert hat und warum:** Vorher stand `Wissen/` mit in
der höchsten Schutzstufe, und Massenoperationen waren im ganzen Vault
untersagt. Das hat nicht die Originale geschützt, sondern das Arbeiten und
Aufräumen ausgebremst — jede Notizänderung und jedes Aufräumen von
reproduzierbarem Ballast brauchte eine Rückfrage. Die Sperre gilt jetzt dort,
wo ein Verlust endgültig ist, und nur dort. Wer diesen Absatz liest und die
alte, weitere Fassung „wiederherstellen" will: Das war kein Versehen.

## Handel: was ein Agent selbst auslösen darf

**Das Auslösen von Geldbewegungen darf automatisch geschehen, solange die
Regeln zum Schutz des Kapitals eingehalten werden.** Von Max angeordnet am
01.09.2026. Das kehrt die bis dahin geltende Fassung um („das Auslösen von
Geldbewegungen bleibt bei Max, ein Agent bereitet nur vor") — **automatischer
Handel ist seither die Regel, nicht die Ausnahme.**

Damit dieser Satz trägt, muss „Regeln zum Schutz des Kapitals" etwas
Nachprüfbares bezeichnen und keine Haltung. Es sind zwei Dateien, und sie sind
die **einzige** Wahrheit über die Grenzen:

| Spur | Grenzen in | Was dort handelt |
|---|---|---|
| **1 — Spot** | `../Agenten/Handel/scanner/wachen.json` | Marktscanner: Spot, nur Long, kein Hebel |
| **2 — Hebel** | `../Agenten/Handel/xperp/wachen.json` | XPERP-Bot: Long und Short, Hebel bis 5 |

Drei Eigenschaften machen die Erlaubnis tragfähig. **Fehlt eine, gilt sie
nicht** — dann ist es kein bewachter Automat, sondern eine Wette mit
Skriptunterstützung:

1. **Die Grenzen stehen in einer Datei, nicht im Gedächtnis einer Sitzung.**
   Die Skripte lesen `wachen.json`, sie schreiben sie nie. Eine Sitzung kann
   eine Regel vergessen, eine Datei nicht.
2. **Jede Position trägt einen nicht abschaltbaren Stop**, und über allem steht
   ein Kill-Switch auf den Gesamtverlust (`kill_switch_gesamt_usd`).
3. **Scharf geschaltet wird von Hand.** Was danach läuft, läuft ohne Rückfrage
   — aber der Schalter selbst wird nie von einem Zeitplan umgelegt.

### Spur 1 — Marktscanner: läuft von selbst, ohne Hebel

Der Marktscanner unter `../Agenten/Handel/scanner/` (eigenes README) darf im
Rahmen fester Grenzen selbst kaufen und verkaufen, **ohne dass Max jede Order
einzeln anordnet**. Die Grenzen stehen in `scanner/wachen.json` und sind die
einzige Wahrheit darüber:

| Grenze | Wert |
|---|---|
| je Trade | 50 USD |
| gesamt gebunden | 200 USD |
| offene Positionen | höchstens 4 |
| Pflicht-Stop je Position | 4–12 %, nicht abschaltbar |
| Abklingzeit nach Stop-Out | 3 Tage je Wert |
| Instrumente | nur Spot, nur Long, kein Hebel |

Die letzte Zeile ist die Grenze **dieser Spur**, nicht die des ganzen Systems:
Hebel läuft über Spur 2 und hat dort eigene Grenzen.

**Drei Sperren müssen alle offen sein, sonst läuft nur Papierhandel:**

1. `scanner/wachen.json` → `"handel_erlaubt": true`
2. `OKX_API_KEY`, `OKX_API_SECRET`, `OKX_API_PASSPHRASE` als
   Windows-Benutzervariablen (nicht in den Vault, nicht neben den Code)
3. `handeln.py` ausdrücklich mit `--live` aufgerufen

Stand 01.09.2026 ist Sperre 1 zu (`handel_erlaubt: false`) und Sperre 2 leer —
der Live-Pfad ist **noch nie scharf gelaufen**. Bis gültige Schlüssel gesetzt
sind und das Papier-Handelsjournal über Wochen trägt, bleibt es dabei.

### Spur 2 — Gehebelte Produkte: automatisch im Rahmen, oder auf Anweisung

Angeordnet von Max am 01.09.2026. **Hebel ist weder verboten noch an eine
Einzelanweisung gebunden.** Es gibt zwei Wege hinein, und sie unterscheiden
sich nur darin, woher die Parameter kommen:

| Weg | Parameter aus | Wer über die einzelne Position entscheidet |
|---|---|---|
| **automatisch** | `xperp/wachen.json` | `bot.py`, im Rahmen der Datei — ohne Rückfrage je Order |
| **auf Anweisung** | Max' Anweisung im Chat | Max, mit den vier Pflichtangaben unten |

In beiden Fällen gilt: Die Werte in `wachen.json` sind eine **Obergrenze, kein
Ziel**. Eine Anweisung darf sie nicht überschreiten, auch nicht mit
Bestätigung — wer weiter will, ändert erst die Datei, und das ist ein eigener
Vorgang mit Ansage (Stufe 1).

**Was sich geändert hat und warum:** Die alte Fassung schrieb „nur Spot, nur
Long, kein Hebel" als Systemgrenze ohne jeden Ausweg. Das hat kein Geld
geschützt — es hat nur die Arbeit an `../Agenten/Handel/xperp/` in einen
Graubereich gestellt (der Kopf von `okxf.py` verweist selbst auf das Verbot)
und jede gehebelte Aufgabe in eine Diskussion über die Regel verwandelt statt
in eine Rechnung. Die Sperre wandert deshalb dorthin, wo sie etwas taugt: von
**„nicht erlaubt"** zu **„nicht außerhalb von `wachen.json`, und nicht ohne
gerechnete Zahlen"** — siehe Prüfpflicht unten. Am selben Tag ist die zweite
Hälfte gefallen: erst brauchte Hebel eine Anweisung je Vorgang, seit Max'
Änderung am Abend nicht mehr. Geblieben ist die Datei.

**Nimmt Max eine Position von Hand, am Bot vorbei**, nennt die Anweisung
**alle vier Angaben**, in derselben Sitzung:

| Angabe | Beispiel |
|---|---|
| Kontrakt | `RE-USD_UM_XPERP-310620` — der volle `instId`, nicht „das aus der Liste" |
| Richtung | Long oder Short |
| Hebel | als Zahl, nicht „hoch" oder „aggressiv" |
| Einsatz und Stop | Nominal in USD und Stop in Prozent |

Fehlt eine Angabe, wird sie **nicht sinngemäß ergänzt**: kein geratener Hebel,
keine Richtung aus dem Trend abgeleitet. Fehlt etwas, wird genau danach gefragt
— und alles übrige inzwischen schon vorbereitet.

Der Unterschied zum automatischen Weg liegt genau hier: **`bot.py` darf aus
einer Rangliste heraus eröffnen, eine Chat-Antwort nicht.** Was `auswahl.py`
ausgibt, ist für einen Menschen ein Vorschlag; verbindlich wird es durch die
Datei oder durch Max, nicht durch die Rangfolge selbst.

Fest, auf beiden Wegen — auch mit Anweisung, auch im Automatikbetrieb:

| Grenze | Warum sie nicht verhandelbar ist |
|---|---|
| Pflicht-Stop je Position, nicht abschaltbar | Ohne Stop ist der Hebel die Positionsgröße, nicht das Risiko |
| Hebel höchstens `hebel_deckel` aus `xperp/auswahl.py` | Liquidation greift bei rund `1/Hebel` minus Wartungsmarge. Ob ein Hebel den größten beobachteten 7-Tage-Rücklauf überlebt hätte, ist keine Meinungsfrage — es wird ausgerechnet und gemeldet |
| kein Auszahlungsrecht | Die Schlüssel bekommen Handelsrecht, sonst nichts. `account_transfer` und Auszahlungen bleiben außen vor |
| Rahmen aus `xperp/wachen.json` | Margin je Anlauf, Gesamtmargin, `risiko_je_anlauf_usd` und `kill_switch_gesamt_usd` gelten für den Automaten wie für eine Anweisung |
| Scharfschalten nur von Hand | `Routinen/*.ps1` startet den Bot, aber legt nie `handel_erlaubt` um. Der Automat entscheidet über Positionen, nicht über sich selbst |
| Papierlauf zuerst bei einer **neuen Strategie** | Nicht bei einer einzelnen angewiesenen Position — dort ist die Anweisung selbst die Entscheidung |

### Was an die Stelle des Verbots tritt: die Prüfpflicht

Das Verbot war das billige Sicherungsmittel. Es fällt weg, dafür wird
gerechnet. **Vor einer gehebelten Order stehen vier Zahlen** — kurz, als
Tabelle, nicht als Aufsatz:

1. **Liquidationsabstand gegen größten 7-Tage-Rücklauf** (`hebel_deckel`).
2. **Funding über die geplante Haltedauer**, mit Vorzeichen — beim Short oft
   ein Zuschuss, beim Long eine laufende Miete.
3. **Gebühren je Runde gegen den erwarteten Gewinn** (0,05 % je Ausführung
   Taker).
4. **Nötige Trefferquote gegen die beobachtete.**

**Wo sie stehen, hängt vom Weg ab, nicht von der Laune:** Auf dem
Anweisungsweg legt der Agent sie ungefragt im Chat vor, bevor die Order
vorbereitet ist. Auf dem automatischen Weg kann niemand mitlesen — dort gehören
sie **in die Prüfung von `bot.py` und ins Handelsjournal**, je Position mit
abgelegt. Eine Zahl, die der Automat nicht ablegt, ist nicht gerechnet worden;
eine Position ohne diese vier Werte im Journal ist ein Befund, kein Trade.

Die Grundlinie dafür steht in [[Handelsbots]] und ist unbequem: Über 12 Monate
lag **jede** getestete mechanische Einstellung dicht an der Nulllinie, leicht
darunter — nötige und erreichte Trefferquote lagen immer ein bis zwei
Prozentpunkte auseinander, übrig blieben die Gebühren. **Hebel vergrößert
diesen Abstand mit, nicht nur den Gewinn.** Wer das nicht danebenlegt, verkauft
eine Vermutung als Plan.

Drei Denkfehler, die die eigene Rückrechnung schon gemacht hat. Sie gelten hier
unverändert und werden aktiv geprüft, statt abgewartet:

- **Kurze Fenster täuschen zuverlässig.** Dieselbe Rechnung ergab über 30 Tage
  +0,63 $ je Runde statt −0,22 $ über 12 Monate — weil BTC in dem Fenster
  28,5 % stieg. Nie unter einem Jahr bewerten, und den Kursverlauf des
  Testfensters immer mitangeben.
- **Funding fehlt in Rückrechnungen fast immer.** Gemessen −0,031 $ in
  36 Minuten auf 570 $ Position; über drei Tage frisst das rund einen halben
  Durchschnittsgewinn. Mit Hebel entsprechend mehr.
- **Die Kontraktgröße rundet.** Aus 651 $ berechnetem Nominal wurden 570 $
  echte — `ctVal` und `lotSz` bestimmen die Position, nicht der Wunschbetrag.

**Widerspruchspflicht, kein Vetorecht.** Sagen die Zahlen, dass eine Anweisung
falsch gedacht oder mit hoher Wahrscheinlichkeit unprofitabel ist, sagt der
Agent das **einmal** — mit Zahlen und einem konkreten Gegenvorschlag: anderer
Hebel, anderer Stop, anderer Kontrakt, anderes Zeitfenster. Bestätigt Max
daraufhin, wird **wie angewiesen** ausgeführt: vollständig, nicht
stillschweigend kleiner, nicht „vorsichtshalber" nur zur Hälfte. Die verbotene
Antwort ist die umgekehrte: nicht ausführen und stattdessen über Risiko reden.
Die Analyse **ersetzt** das Verbot, sie ist nicht seine Fortsetzung mit anderen
Mitteln.

Dasselbe gilt in die andere Richtung: Fällt bei einer Auswertung eine bessere
Einstellung auf, wird sie **vorgeschlagen** — mit der Rechnung dazu —, nicht
heimlich eingesetzt.

### Was auch diese Erlaubnis nicht aufweicht

- **Kein Zeitplan legt den Schalter um.** `Routinen/marktscanner.ps1` ruft
  `handeln.py` ohne `--live`; scharf wird ein Lauf durch einen bewussten Aufruf
  von Hand. Das ist kein Widerspruch zum automatischen Handel, sondern seine
  Bedingung: Der Automat entscheidet über **Positionen**, nicht darüber, ob er
  selbst scharf ist.
- **Kein Auszahlungsrecht**, in keiner Spur.
- **Jede andere Geldbewegung** — Überweisungen, Ein- und Auszahlungen, Umtausch
  außerhalb dieser beiden Spuren — bleibt vorbereitend. Der Skill `geld`
  arbeitet bis zur Bestätigungsseite und hält dort an.
- **Das Absenden der scharfen Order tut die Claude-Sitzung selbst nicht.**
  Claude rechnet, wählt aus, konfiguriert, startet den Papierlauf und legt die
  Live-Order bis zur Bestätigung fertig vor; ausgelöst wird sie von Max oder von
  dem dafür gebauten Skript (`handeln.py --live`, `xperp/`). Das ist **keine
  Bewertung der jeweiligen Anweisung** und keine Hintertür für das alte Verbot,
  sondern eine Grenze der Claude-Sitzung selbst, die dieses Dokument nicht
  aufheben kann. Wo sie im Weg ist, ist der Weg drumherum das Skript — nicht
  die Diskussion.

## Warum es die Sperre überhaupt gibt

Zwei Dinge machen die geschützten Ordner empfindlicher als ein normales
Projektverzeichnis:

1. **Sie sind nicht in Git.** Git versioniert seit dem 24.08.2026 die Textebene
   des Vaults (Notizen, Skills, Skripte, Konfiguration) — die 42 GB Medien und
   Dokumente sind durch die Whitelist in `.gitignore` bewusst ausgenommen. Für
   sie gibt es kein `git restore`; für `Wissen/` gibt es das sehr wohl, und
   genau deshalb steht `Wissen/` nicht mehr unter der Sperre.
2. **Die Sicherung ist keine Historie.** `sichern.ps1` läuft ohne `/MIR` und
   kopiert nur Neues und Geändertes. Wer eine Datei um 19:00 kaputtschreibt, hat
   um 20:01 auch auf `G:` nur noch die kaputte Fassung. Die Sicherung schützt
   gegen Plattenausfall, **nicht** gegen einen falschen Schreibvorgang.

Dazu kommt: **Das Archiv ist bereits einmal beschädigt worden.** 691 Dateien
sind durch einen Netzteildefekt zerstört (siehe
[[../Claude/BESCHAEDIGTE_DATEIEN|BESCHAEDIGTE_DATEIEN]]). Was noch intakt ist,
ist der Rest — nicht der Normalzustand.

## Stufe 0 — unersetzlich, nie automatisiert löschen

Kein Agent löscht, überschreibt, verschiebt oder benennt hier um **ohne dass Max
es in derselben Sitzung ausdrücklich für genau diese Datei angeordnet hat.**
Massenoperationen (Schleife, `--recurse`, Platzhalter) sind hier grundsätzlich
verboten, auch mit Anordnung — erst eine Liste vorlegen, dann einzeln.

| Ort | Warum |
|---|---|
| `Claude/Dokumente/` | Verträge, Bescheide, Gericht, Gesundheit, Behörden. Originale, oft die einzige Fassung. |
| `Claude/Bilder/`, `Claude/Videos/`, `Claude/Musik/` und Playlisten | Rohmedien. 25 GB ohne Zweitquelle; 18,3 % der Bilder sind bereits verloren. |
| `Claude/Posteingang/` | Durchgangsordner — was dort liegt, ist noch nirgends einsortiert und damit ein Original. Erst sortieren, dann gilt der Zielordner. |
| `Wissen/Zugaenge.md` | Einzige Ablage für Schlüssel und Tokens, bewusst außerhalb von Git. Nie ausgeben, nie in eine Chat-Antwort, nie in ein Protokoll — und nie löschen. |
| `**/*.env`, `.pem`, `.pfx`, `.p12`, `.kdbx`, `.key`, `.ovpn` | Zugangsdaten, an der Endung erkennbar, nicht am Namen. Auch `Claude/Software/**/*.pfx`: die ELSTER-Zertifikate sind zerstört, aber sie **belegen** den Verlust. |
| Alle 0xFF-Platzhalter | Die 61 verbliebenen Nullbyte-PDFs sind der einzige Hinweis darauf, **welche** Dokumente fehlen. Nicht aufräumen. |

### Löschen ist hier nie die Lösung

Ein Agent löscht in Stufe 0 **gar nicht**. Wenn etwas weg soll, wird es nach
`Claude/Posteingang/_zu_loeschen/` verschoben und Max entscheidet. Der Grund ist
dieselbe Erfahrung, die schon in `sort_inbox.py` steckt: eine
Duplikat-Erkennung nach Änderungsdatum hätte in einem einzigen Lauf 1001
gleichnamige, inhaltlich verschiedene Dateien abgeräumt.

## Stufe 1 — Betriebsteile, Änderung nur mit Ansage

Hier geht es **nicht** um die Löschsperre, sondern um stille Beschädigung:
Diese Dateien sind ersetzbar, aber wenn sie kaputtgehen, merkt es niemand — und
genau das ist bereits passiert (`sichern.ps1` meldete am 23.08.2026 „ENDE ok",
während robocopy mit Code 11 gescheitert war).

**Regel: vor der Änderung `.bak-JJJJMMTT` anlegen, nach der Änderung einmal
ausführen und die Ausgabe zeigen.** Eine Änderung an einem Sicherungsskript
gilt erst als erledigt, wenn ein echter Lauf sie bestätigt hat.

| Ort | Risiko bei stiller Beschädigung |
|---|---|
| `Agenten/sichern.ps1`, `Agenten/sichern-zweitkopie.ps1` | Sicherung fällt aus, ohne Fehlermeldung. |
| `Agenten/Routinen/*.ps1` | Geplante Aufgabe läuft ins Leere; die Aufgabenplanung meldet trotzdem Erfolg. |
| `Claude/ArchivSuche/sort_inbox.py` | Verschiebt und löscht echte Dateien. Höchste Sorgfalt. |
| `Claude/ArchivSuche/index.py`, `vektor_index.py` | Index fällt aus; Suche liefert stillschweigend nichts. |
| `AGENTS.md`, `CLAUDE.md` (in der Wurzel **und** in `MaxHirn/`), `Dashboard.md` | Steuern das Verhalten aller Agenten. |
| `.claude/skills/` | Dasselbe. |
| `.obsidian/` | Vault-Konfiguration. Kaputt = Obsidian öffnet den Graphen nicht mehr. |
| `Agenten/MCP-Server/`, `Agenten/Handel/agent.py`, `Agenten/Handel/plan.json` | Laufender Betrieb, eigene Zugangsdaten. |
| `Agenten/Hermes/` | Konfiguration und Gedächtnis des zweiten Agenten. |

## Stufe 2 — freie Hand, auch beim Löschen

**Alles, was nicht in Stufe 0 oder 1 steht.** Ein Agent räumt hier ohne
Rückfrage auf, auch in Massenoperationen. Häufige Fälle:

- `Wissen/` — Notizen, Profil, Fristen, Projekte. Seit 24.08.2026 in Git:
  `git restore <pfad>` holt einen Fehlgriff zurück, geprüft an `Fristen.md`.
  **Ausnahme:** `Zugaenge.md` steht in Stufe 0 und ist nicht in Git.
- `**/.venv/`, `**/__pycache__/`, `**/node_modules/` — aus `requirements.txt` / `package.json`
- `Werkstatt/` — Übergaben, Sitzungsreste, geklonte Fremd-Repos (`Repos/`).
  Durchgangsware, aus der Sicherung ausgenommen, eigene Spielregeln in
  `Werkstatt/AGENTS.md`
- `Modelle/` (51 GB, seit 30.08.2026 außerhalb des Vaults) — neu herunterladbar
- `Claude/ArchivSuche/archiv_index.db`, `vektor_index.db` — `index.py` erzeugt sie neu
- `Agenten/Routinen/**/logs/` — jeweils nur der letzte Lauf
- Build-Reste (`.pyc`, `.pyo`, `.toc`, `build/`, `dist/`), Temporärdateien, Duplikate

Der einzige Vorbehalt: **vor dem Löschen kurz hinsehen.** Name und Größe allein
sind bei Containerformaten (`.vob`, `.iso`, `.img`) kein Duplikatbeweis — dort
per Hash gegenprüfen.

## Vor jedem schreibenden Zugriff

1. **Stufe bestimmen.** Im Zweifel die höhere annehmen.
2. **Bei Stufe 0 oder 1: erst lesen, dann eine Liste des Geplanten zeigen,
   dann handeln.** Kein „ich habe schon mal angefangen".
3. **Trockenlauf, wo es einen gibt.** `sort_inbox.py --dry-run`,
   `robocopy /L`, `git status` — bevor der echte Lauf startet.
4. **Nach der Änderung prüfen**, nicht auf den Rückgabewert eines Werkzeugs
   vertrauen. Robocopy wirft keine Ausnahme, es meldet über den Exitcode.

## Mehrere Sitzungen gleichzeitig

Max arbeitet mit mehreren Chats parallel, dazu kommt Hermes. Alle schreiben in
denselben Vault. Der Schutz durch Git hat dabei eine genau bestimmbare Lücke:

**Git schützt nur, was committet ist.** Zwischen dem Schreiben einer Datei und
ihrem Commit liegt ein Fenster, in dem die Arbeit nirgends gesichert ist — nicht
in Git, und in der Sicherung um 20:00 steht danach der überschriebene Stand.
Eine zweite Sitzung, die in diesem Fenster verwirft, vernichtet die Arbeit der
ersten endgültig.

Am 24.08.2026 ist das zum ersten Mal aufgefallen, im harmlosen Fall: Eine zweite
Claude-Sitzung fand zwei geänderte Dateien im Arbeitsbaum vor und committete sie
samt Nachricht in der Ich-Form — Arbeit, die sie nicht getan hatte. Verloren ging
nichts. Dasselbe Muster mit `git checkout` statt `git commit` hätte die Arbeit
gelöscht, und zwar ohne Rückholmöglichkeit.

Genau diese Unterscheidung trägt Regel 1 seit dem 27.08.2026: Falsch war an dem
Vorfall nur die **Ich-Form**, nicht das Sichern. Der Commit selbst war das
Richtige — er hat fremde Arbeit aus dem ungeschützten Fenster geholt.

Vier Regeln, für Claude und Hermes gleichermaßen:

1. **Verwerfen ist verboten, Sichern ist Pflicht.** Vor jedem Commit
   `git status` lesen. Fremde Änderungen im Arbeitsbaum werden **nicht liegen
   gelassen**, sondern in einem **eigenen, getrennten Commit** gesichert — nie
   vermischt mit eigener Arbeit im selben Commit. Dateien namentlich
   hinzufügen: `git add <pfad>`. **Nie** `git add -A`, `git add .` oder
   `git commit -a` — nicht wegen der fremden Arbeit, sondern weil sie beide
   Sorten zusammenwerfen.

   Die Herkunft steht im Autorenfeld, nicht nur in der Nachricht:

   ```
   git commit --author="Hermes <hermes@local>" -m "…"
   ```

   Damit lügt auch `git log --author` nicht, und `git log --author=Hermes`
   zeigt jederzeit, was nicht aus einer Claude-Sitzung stammt. Lässt sich der
   Urheber nicht feststellen — der Regelfall, denn eine Änderung im
   Arbeitsbaum trägt keinen Namen —, gilt
   `--author="Andere Sitzung <fremd@local>"`. Nicht raten: „Hermes" ins
   Autorenfeld zu schreiben, weil es plausibel klingt, macht die Historie
   genauso falsch wie die Ich-Form.

   **Ausnahme:** Eine Datei, deren Änderungszeit weniger als **10 Minuten**
   zurückliegt, ruht möglicherweise nicht — dort kann eine andere Sitzung
   mitten im Arbeitsschritt sein. Solche Dateien liegen lassen und melden.
   Die Schwelle ist bewusst eine Zahl und kein Ermessen, sonst entscheidet
   jede Sitzung anders; geprüft wird mit `(Get-Item <pfad>).LastWriteTime`.
   Der Schaden wäre allerdings nur ein unschöner Zwischenstand in der
   Historie, kein Datenverlust: ein Commit löscht nichts.

   **Warum die Regel am 27.08.2026 gedreht wurde** — sie lautete vorher
   „nichts committen, was man nicht selbst geändert hat". Das schützte nichts
   und schadete: Ein Commit fremder Arbeit ist zurücknehmbar — solange er die
   Spitze ist mit `git reset --soft HEAD~1`, sonst mit `git revert` —, der
   einzige Schaden war eine Nachricht in falscher Ich-Form. Unumkehrbar ist
   allein das Verwerfen — dafür gibt es Regel 2.
   Die alte Fassung ließ fremde Arbeit dagegen unbegrenzt in dem
   ungeschützten Fenster liegen, das Regel 3 gerade verkleinern soll. Bei
   Hermes ist das kein Sonderfall: **Hermes committet nie selbst** (geprüft
   27.08.2026, alle 30 Commits der Historie tragen denselben Autor). Seine
   Arbeit ist nur versioniert, wenn eine Claude-Sitzung sie mitnimmt —
   die Notiz [[Hermes]] lag deshalb einen ganzen Tag ungeschützt im Arbeitsbaum.
   Zweiter Blocker: Steht in einer Datei schon Fremdes uncommittet, lässt
   sich der eigene Anteil gar nicht isoliert committen — Regel 1 und Regel 3
   waren dann gleichzeitig unerfüllbar.

2. **Nichts verwerfen.** `git reset --hard`, `git checkout -- <datei>`,
   `git restore <datei>`, `git stash`, `git clean` löschen genau das, was Git
   noch nicht schützt. Nur auf ausdrückliche Anweisung in derselben Sitzung —
   und vorher ansagen, welche Dateien es trifft.

3. **Eigenes zügig committen.** Nach jedem abgeschlossenen Arbeitsschritt, nicht
   erst am Sitzungsende. Das ist der einzige Hebel, der das ungeschützte Fenster
   wirklich verkleinert.

4. **Exklusive Läufe nicht doppelt starten.** `index.py`, `sort_inbox.py`,
   `sichern.ps1` und `zweitkopie.ps1` schreiben eine SQLite-Datenbank oder
   verschieben Dateien. Zwei gleichzeitige Läufe blockieren sich oder
   hinterlassen einen halben Stand. Vorher prüfen, ob schon einer läuft.

**Was diese vier Regeln nicht leisten:** Sie verhindern nicht, dass zwei
Sitzungen dieselbe Datei nacheinander überschreiben. Dagegen hilft nur,
verschiedenen Sitzungen verschiedene Bereiche zu geben — oder nachzufragen,
bevor man eine Datei anfasst, an der erkennbar eine andere Sitzung arbeitet.

## Was diese Regeln nicht leisten

- **Alle drei Kopien stecken im selben Rechner.** Original auf Disk 0,
  Sicherung auf `G:` (Disk 2), Zweitkopie auf `O:` (Disk 1). Gegen einen erneuten
  Netzteilschaden — der 2026 schon mehrere Platten gleichzeitig getötet hat —
  hilft das nicht. **Eine Kopie außer Haus ist der wichtigste offene Punkt.**
  Siehe [[Hardware]].
- **Versionsstände seit 24.08.2026.** Ein Git-Repository über die Textebene des
  Vaults schließt die Lücke, die alle drei Kopien teilen: Sie halten nur den
  jetzigen Stand. Erfasst sind 85 Dateien (`Wissen/`, Steuerdateien der Agenten,
  `.claude/skills/`, `ArchivSuche/`, `Handel/`, die drei eigenen MCP-Server,
  die Sicherungsskripte) — **ohne** die 42 GB Medien. Zurückholen einer
  versehentlich überschriebenen Datei: `git restore <pfad>`, geprüft am
  24.08.2026 an `Fristen.md` (bit-genau identisch wiederhergestellt).
  Die `.gitignore` ist eine **Whitelist**: erst alles ignorieren, dann einzeln
  freigeben. `Zugaenge.md`, `Passwoerter-Quarantaene.md`, alle `.env`, `.pem`,
  `.pfx`, `.p12`, `.kdbx` stehen als Rückausnahme draußen und waren nie im
  Verlauf. **Das ist wichtig, denn Git vergisst nichts** — eine einmal
  eingecheckte Schlüsseldatei bleibt auch nach dem Löschen im Verlauf.
  Neue Dateien werden also **nicht automatisch** erfasst; was mitversioniert
  werden soll, braucht eine Freigabezeile in `.gitignore`.
- **`Zugaenge.md` liegt im Klartext** und wird nach `G:` und `O:` mitkopiert.
  Bewusst so, geprüft von `sichern.ps1`. Wer die Platte hat, hat die Schlüssel.

Verwandt: [[Ordnerstruktur]], [[Portabilitaet]], [[Hardware]], [[KI-Ablagen-im-Benutzerordner]], [[Routinen]]

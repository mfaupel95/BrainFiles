---
name: sitzungs-rekonstruktion
description: "Sitzung rekonstruieren: fehlenden Stand nachliefern."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [hermes, sessions, state-db, statusbericht, brainfiles]
    related_skills: [hermes-config-ops, absturz-recovery]
---

# Abgebrochene Sitzung rekonstruieren

Eine Sitzung endet mitten im Turn — die letzte Assistenten-Zeile ist ein halber Satz
(„…, dann der Stand:") — und Stunden später kommt in einer **neuen** Sitzung nur ein
Wort: „stand", „wie siehts aus", eine nackte Ziffer („9"), „ja". Der Auftrag steht
nirgends im aktuellen Kontext. Ziel: den versprochenen Stand nachliefern, mit Belegen,
statt zu raten oder zurückzufragen.

## Wann

- eine Nachricht ohne Bezug im Kontext (Einzelwort, Ziffer, „mach weiter")
- eine Sitzung, die sichtbar mitten im Satz abgebrochen ist
- „wie siehts aus", „stand", „wo waren wir" in einer Sitzung, die den Faden nicht hat

**Don't use for:** Absturz am Rechner mit beschädigtem Arbeitsbaum (`absturz-recovery`),
gezielte Änderung an der Hermes-Konfiguration (`hermes-config-ops`).

## Prozedur

1. **Sitzungen nach letzter Aktivität auflisten** — `session_search` ohne Argument.
   Kandidat ist die jüngste Sitzung, die **nicht** die laufende ist. Mit `query` das
   Thema finden, dann die Nutzer-Nachrichten dieser Sitzung lesen: die letzte offene
   Frage ist der Auftrag.
   - **`session_search` findet nicht alles.** Die eigene `state.db` ist die
     verlaesslichere Quelle: `SELECT id, title, source, started_at FROM sessions
     ORDER BY started_at DESC LIMIT 20` — die `title` ist die erste Nutzer-Nachricht
     und benennt den Strang sofort. Liefert `session_search` nur alte Sitzungen,
     obwohl gerade etwas passiert ist, direkt in der DB weiterlesen.
   - **Die LAUFENDE Sitzung ist fuer `session_search` unsichtbar** (FTS-Index
     indexiert sie erst nach Abschluss: `count: 0, sessions_searched: 0` heisst
     NICHT „existiert nicht"). Braucht man eine Angabe aus der gerade
     kompaktierten Sitzung (z.B. welches Modell ein Kurzbefehl meint), direkt in
     `state.db` suchen: `SELECT id, role, substr(content,1,120) FROM messages
     WHERE content LIKE '%<markantes wort>%' ORDER BY id DESC LIMIT 10` — ein
     markantes Stichwort aus der Nutzerphrase („7,5", „gb", „routen") als Anker,
     nie „nicht gefunden" melden, solange die DB nicht durchsucht ist.
   - **Dieselbe LIKE-Suche ueber ALLE Profile fahren.** Ein Kurzbefehl kann sich
     auf eine Unterhaltung in einem ANDEREN Profil beziehen (z.B. „das 7,5 gb
     modell" = Modellname, den die bots-Session besprochen hat):
     `Agenten/Hermes/profiles/<name>/state.db` je Profil durchlaufen, Tabelle
     `messages`, `content LIKE '%<stichwort>%'`. Der Treffer nennt Profil und
     Kontext; die umliegenden Zeilen (id-Fenster) liefern den Auftrag dazu.
   - **Eine nackte Ziffer ist ein Verweis, kein Auftrag.** Sie zeigt auf eine
   nummerierte Liste, die in einer anderen Sitzung stand. Also die letzten
   Assistenten-Nachrichten der zwei juengsten fremden Sitzungen lesen
   (`session_search` mit `session_id` - das Fenster liegt von selbst am Ende) und
   pruefen, ob eine davon mit einer Liste endet. Endet KEINE damit (typisch: beide
   Sitzungen starben mitten in einem Werkzeugaufruf), hat die Ziffer keinen Bezug -
   dann EINE Rueckfrage ueber `clarify` stellen: die 2-4 offenen Straenge als
   klickbare Optionen, der wahrscheinlichste zuerst, plus eine Versehen-Option. Die
   Straenge mit Datei/Testname benennen, nicht als Thema - die Antwort soll sofort
   weiterfuehren. In Prosa angebotene Optionen sind hier der Fehler: sie sind nicht
   klickbar und der Nutzer tippt, was er sonst nur anwaehlt.
2. **Nur wenn Schritt 1 den Faden nicht hergibt, in die DB sehen** (lesend):
   `sqlite3.connect("file:<HERMES_HOME>/state.db?mode=ro", uri=True)`, Tabelle
   `messages` mit `id, session_id, role, content, tool_name, tool_calls, timestamp,
   `active`. `active=1` ist der lebende Verlauf, `active=0` komprimierte Altstände.
   - **Lebt die Sitzung noch?** `SELECT session_id, MAX(timestamp) FROM messages WHERE
     active=1 GROUP BY session_id ORDER BY 2 DESC LIMIT 10` — die Zahl in Ortszeit
     umrechnen (`time.localtime`) und mit „jetzt" vergleichen: Minuten = sie arbeitet
     gerade, Stunden = abgebrochen.
   - **`id` ist global über alle Sitzungen.** `WHERE session_id=… AND id>N` schneidet
     willkürlich ab und versteckt genau die Zeilen, die man sucht — pro `session_id`
     nach `timestamp` ordnen.
   - Assistenten-Zeilen mit leerem `content` sind reine Werkzeugaufruf-Turns; die Zeile
     `role='tool'` mit `tool_name` und Ergebnis darunter zeigt, woran gearbeitet wurde
     und wie weit es kam.
   - **Eine im Kontext "demotierte" Werkzeugausgabe ist in der DB vollstaendig da.**
     Nach einer Kompaktierung steht im Verlauf nur ein Platzhalter
     (`[terminal output demoted … N chars preserved in session history]`) — und
     `session_search` liefert genau diesen Platzhalter zurueck. Die Ausgabe ist trotzdem
     zu holen: in der DB nach einem FELD suchen, das nur in IHR vorkommt, nicht nach
     Sitzung oder Zeit.
     `SELECT id, length(content) FROM messages WHERE content LIKE '%<feldname>%' ORDER BY id DESC LIMIT 6`
     — die Laenge gegen die im Platzhalter genannte Zeichenzahl halten, dann
     `SELECT content WHERE id=…` und im Python-String nur die Fundstelle ausschneiden
     (`for s in re.finditer(feld, t): t[s-90:s+70]`), statt 20 kB auszugeben.
     Ein Feldname aus der Ausgabe ist der bessere Anker als alles andere: er ist
     eindeutig und man kennt ihn, weil man die Ausgabe ja gelesen hat.
     Beleg-Beispiel: ueber `availableMargin` kam der echte Kontostand zurueck, den der
     Platzhalter verschluckt hatte.
   - **Dieselbe Suche beantwortet „welche Fassung lief?".** Eine Fehlermeldung
     nennt eine Datei, die es im Baum nicht (mehr) gibt — dann ist nicht der Ort
     die Frage, sondern die Version. Wegwerf-Adressen (`mkdtemp`,
     `tempfile.gettempdir()`) sehen wie Systempfade aus und laden zum Raeum-Verdacht
     ein; legt ein Test seine Eingabedateien selbst an, ist eine
     `FileNotFoundError` darauf fast immer die **vorherige Fassung** der Datei.
     Anker ist ein String aus der Meldung selbst (`spurbuch-gatter-<suffix>`,
     `wachen.json`), nicht Sitzung oder Zeit — danach die Nachrichten **vor**
     dem Treffer lesen, dort steht der `write_file`-/`patch`-Turn, der die
     Fassung erzeugt hat, samt Diff.
   - **Ein Fehler, der sich beim Wiederholen nicht einstellt, ist nicht weg.**
     Dann gilt die gefundene Fassung als belegt-veraltet und der Befund ist der
     **alte** Zustand — im Bericht so benennen, statt weiter am Objekt zu
     suchen.
   - Die letzte Zeile einer abgebrochenen Sitzung ist oft ein Werkzeugergebnis ohne
     Nachsatz — der Assistent starb **vor** dem Bericht, nicht weil die Arbeit fehlte.
     Das ist die gute Nachricht: die Fakten sind schon da.
3. **Nichts aus der toten Sitzung ungeprüft übernehmen.** Jeder Satz, der in den Bericht
   soll, wird am lebenden System nachgeprüft (Zustand, Kommando, Datei). Behauptungen
   aus einem abgebrochenen Lauf sind der häufigste Grund für einen falschen Stand.
4. **Bericht in der Hausform:** Ergebnis zuerst, Belege (Kommando + Ausgabe), genau eine
   begründete Empfehlung, dann die nächste Aktion. Keine Optionsliste.
5. **Immer eine Liste „nicht angefasst"** anschließen: laufende Prozesse, fremde
   Arbeitsstände, Dateien, generierte Artefakte. Ohne sie ist der wiederhergestellte
   Stand unvollständig.

## Wiederholbefehle: „retry", „nochmal", „Continue"

Ein Auftrag, den Hermes nie ausgefuehrt hat, ist nicht spurlos: die Assistenten-Zeile
darunter lautet wortgleich **„Your request was not processed. Send it again if you still
want me to carry it out."** Das ist der Anker — die `role='user'`-Zeile unmittelbar
darueber ist der Auftrag, den der Wiederholbefehl meint, **nicht** die letzte Zeile der
Sitzung. Beides gehoert in den Bericht: was der Auftrag war und dass er nie lief.

- **`history=0` in einer frischen Sitzung heisst nicht, dass es keinen Faden gibt.**
  Ist die Hauptsitzung beschaeftigt, legt der Gateway je Nachricht eine
  **Hintergrundsitzung** an (`session_id` beginnt mit `bg_<HHMMSS>_<hash>`); mehrere
  laufen gleichzeitig auf denselben Auftrag. Vor dem Handeln pruefen, ob eine andere
  Sitzung ihn schon fuehrt.
- **Wiederholt wird die ANFRAGE, nicht die Wirkung.** Beruehrt der Auftrag Schalter mit
  echter Wirkung (Live-Handel, Freigaben, Loeschungen), wird er NICHT erneut ausgefuehrt,
  solange eine andere Sitzung ihn fuehrt — zwei Sitzungen an denselben Schaltern sind
  das Risiko, nicht die gesparte Zeit. Dann messen, berichten und den einen Schritt
  benennen, den nur der Nutzer tun kann.
- **Immer derselbe „not processed"-Takt ist keine offene Aufgabe, sondern eine
  haengende Schleife** — der Wiederholungsauftrag eines Kanban-/Goal-Workers, dessen
  Modell nicht antwortet. Sie wird gemeldet und beendet, nicht wiederholt.
- Abfragen, Protokollzeilen und die Schleifen-Erkennung stehen in
  `references/verlorene-anfrage-finden.md`.

## Wenn ein Bot- oder Subagenten-Auftrag abgebrochen ist

Ein `/bot <name> <auftrag>` oder ein Aufruf mit harter Frist endet mit
„Zeitlimit" - der Auftrag steht danach nirgends im eigenen Kontext.

1. **Den vollen Auftrag aus den Artefakten holen, nicht aus dem Protokoll.**
   `Agenten/Bus/skillsbot.log` schneidet den Befehl nach rund 40 Zeichen ab.
   Vollstaendig steht er in der `state.db` des Profils
   (`Agenten/Hermes/profiles/<name>/state.db`, Tabelle `messages`, die
   `role='user'`-Zeile ist der Kickoff) und in
   `Agenten/Hermes/cache/delegation/live/deleg_*/manifest.json` (goal) samt
   `task-N.log` (Live-Transcript des Kindes).
2. **Zuerst pruefen, was schon FERTIG ist.** Der Abbruch trifft oft nur den
   Schluss - Bericht, Messreihe und Skripte liegen bereits auf der Platte,
   waehrend das Kind an seiner Antwortform scheiterte. `task-N.log` bis zur
   letzten Zeile lesen und jeden dort genannten Pfad im Baum pruefen.
3. **Bergen statt neu fahren.** Vorhandene Artefakte gegen ihre eigene Quelle
   halten (JSON gegen die Berichtstabelle), dann nur die fehlenden Gegenproben
   nachziehen. Ein Neu-Dispatch bezahlt dieselbe Arbeit ein zweites Mal.
4. **Nach versionierten Dateien sehen, die der Lauf geloescht hat.**
   `git status --porcelain` nach `D`-Eintraegen abklopfen: ein Kind, das „seine
   Hilfsdatei entfernt", trifft manchmal eine gleichnamige Datei aus dem Repo -
   `git checkout HEAD -- <pfad>` und nur die echte Scratch-Spur loeschen.
5. **Die Frist ist eine Eigenschaft des Absenders, kein Bot-Fehler.** Beim
   SkillsBot kappt `BOT_FRIST_S` (`Agenten/Bus/skillsbot.py`). Lange Fachlaeufe
   (Backtests, Serienlaeufe) deshalb in Teilstuecke schneiden oder als Cron
   abgeben; die Frist hochzusetzen verschiebt nur den Abbruch.
6. **Kind- und Bot-Zusammenfassungen sind Selbstauskunft.** Beleg sind die
   Artefakte und die eigenen Laeufe, nie der Schlussabsatz des Kindes.

## Wenn eine Fehlermeldung nicht zum Arbeitsbaum passt

Bevor irgendein Objekt als defekt gilt: **stimmt die Fehlermeldung ueberhaupt
ueber das, was da ist?** Ein `ModuleNotFoundError`/`ImportError` in roten Tests
kommt in Traegerkraft aus dem falschen Interpreter (Dutzende Zeilen, kein
einziger Defekt) — `welcher-python` gehoert dazu. Ein Pfad, den es nicht gibt,
spricht ueber die Fassung, nicht ueber einen Raeumer.

Beides mit einem **Gegenlauf** besorgen, nicht mit einer Deutung:

```bash
# 1) Attrappe im Fehlerzustand: MUSS mit derselben Meldung abbrechen.
# 2) Attrappe im Sollzustand: MUSS durchlaufen.
# 3) Gegenprobe-Datei danach loeschen - sie gehoert nicht in den Baum.
```

Damit ist die Ursache belegt statt geraten, und die Restfehler der Suite sind
gegen den belegten Stand abzugrenzen (vorhanden und vorbestehend sind
verschiedene Antworten).

## Lektionen einer Parallel-Sitzung uebernehmen (nicht nur ihren Stand)

Ein fertiger Bericht einer anderen Sitzung ist eine Behauptung (siehe Regeln). Aber
er ist auch eine **Quelle**: eine Sitzung, die 1000+ Zeilen in Skills schreibt,
beweist das mit `git log` — und ihre Lehren stehen dann **nur** dort. Skills laden
nur bei greifendem Trigger, eine frische Sitzung findet sie sonst nicht. Wer fremde
Arbeit uebernimmt, muss sie deshalb spiegeln, sonst hat er sie zur Haelfte uebernommen.

Reihenfolge, weil jede spaetere von der vorherigen abhaengt:

1. **Bestand in einem Lauf** — `git log --oneline -12` (Rohfassung der Lehren, oft
   schon mit Messwert und Gegenprobe), `git status --porcelain` (Pfade **ohne**
   Meldung), `git diff --stat` (Gewicht je Pfad). Ein `??`-Eintrag kann ein ganzer
   Skill-Baum sein:
   `git status --porcelain | grep '^??' | awk '{print $2}' | while read f; do if [ -d "$f" ]; then find "$f" -type f | head -20; else echo "$f"; fi; done`
   Je Pfad ohne Meldung: erst die erste Bildschirmzeile (der Docstring sagt, worum es
   geht), dann `git diff` — das reicht zur Einordnung.
2. **Spiegelstand messen, nicht annehmen.** Je Lehrbegriff `grep -rl <begriff>
   MaxHirn/Wiki/ | wc -l`. **Null Treffer = steht nirgends** — das ist der Befund, den
   man nennt. Ein Treffer bedeutet *diese* Seite erweitern, nicht danebenlegen; ein
   Treffer in einer Nachbarrubrik ist kein Treffer.
3. **Zeilenenden aller Zieldateien messen, BEVOR die erste geschrieben wird.** In
   einem Baum mischen sich LF- und CRLF-Seiten, und eine Seite kann ohne
   Schluss-`\n` ausgeliefert worden sein:
   `python -c "b=open(p,'rb').read(); print(b.count(b'\\r\\n'), b.count(b'\\n'), b.endswith(b'\\n'))"`
   Wer erst beim Schreiben misst, hat die erste Datei schon kaputt.
4. **Byte-sicher anhaengen.** `open(p,'wb')` wertet **zuerst** aus und kuerzt auf
   0 Byte, bevor der Ausdruck scheitern kann — Inhalt zuerst fertigstellen, mit
   `assert neu != alt`, `open()` in der letzten Zeile. Ein Rewrite mit `\n` in einer
   CRLF-Datei zeigt im Diff die **ganze** Datei; `git diff --numstat` je Datei ist
   die einzige Kontrolle.
5. **Gegenprobe.** Der neue Absatz findet sich mit demselben `grep -rl`, mit dem
   Schritt 2 gearbeitet hat, und `git diff --numstat` zeigt fuer jede angefasste
   Wiki-Datei wenige Zeilen.

**Fremde Arbeitsstaende werden gelesen und gespiegelt, nie umgebaut** — die Sitzung
kann gerade darin schreiben. Ueber Aenderung oder Uebernahme entscheidet der
Bericht; eine fremde offene Aufgabe gehoert mit ihrer T-Nummer **erwaehnt**, nicht
ersetzt. Mit in den Spiegel gehoert auch eine **getestete Ruecknahme** („erst geloest,
dann mit Protokoll zurueckgenommen, weil die Zahl X“) — das ist eine Regel; „man hat
es gewechselt“ nicht. Nicht hinein: Zahlen ohne Datei/Lauf/Kommando, Zeitstempel aus
Commit-Meldungen, Vorgaengernamen.

## Regeln (Standing)

- **Zuerst suchen, dann fragen.** Eine Nachricht ohne Bezug ist in dieser Umgebung fast
  immer eine Antwort auf eine parallele Sitzung. Wer sofort nachfragt, kostet einen
  Umlauf; wer sucht, liefert beim ersten Mal.
- **Widersprüchliche Belege offen benennen**, nicht glätten: wenn zwei Quellen
  (Git, Backup, Kommandoausgabe) Verschiedenes sagen, steht beides im Bericht — mit der
  Angabe, welche Quelle mehr wiegt. Eine geglättete Version ist ein Fehler, der später
  auffällt.
- **Fremde Arbeit im Arbeitsbaum nicht anfassen** (anderer Autor, gestagte Dateien,
  fremde Notizen). Benennen, nicht wegräumen; Commits nur auf benannten Pfaden.
- **Unmittelbar vor dem Handeln noch einmal messen, ob die „tote" Sitzung wirklich tot
  ist.** Diese Sitzungen wachen auf, sobald der Nutzer dort etwas tippt — und können in
  der Zwischenzeit genau den Auftrag erledigt haben, den man selbst gerade ausführen
  soll. Also vor jedem Schreiben die letzte Aktivität erneut abfragen (Schritt 2) **und**
  `git status --porcelain <pfad>` plus `git diff --cached <pfad>` lesen. Ist sie wieder
  aktiv, nicht doppelt schreiben: ihr Ergebnis unabhängig nachprüfen und den Bericht
  darauf umstellen — „was sie getan hat, was ich nachgeprüft habe, was offen blieb".
  Zwei Schreiber auf derselben Datei sind der Schaden, nicht die verlorene Zeit.
  - **Konkret messen, nicht vermuten: `stat -c '%y' <pfad>` zweimal mit ~5 s
    Abstand.** Bleibt die mtime gleich, ruht die Datei (die andere Sitzung hat
    geschrieben und ist fertig); aendert sie sich, schreibt sie gerade — dann
    nicht committen, sondern ihr Ergebnis nachpruefen. Eine mtime, die NACH
    deinem eigenen Patch liegt, heisst: die andere Sitzung hat auf deiner
    Version aufgebaut oder sie ueberschrieben — `git diff` zeigt, was wirklich
    drinsteht, bevor du committest.
  - **Ein `index.lock` ist nicht automatisch ein aktiver Schreiber.** Pruefen:
    `tasklist //FI "IMAGENAME eq git.exe"` (kein Treffer = kein git-Prozess)
    und die lock-Groesse (0 Byte) + Alter. Ein verwaister lock (kein
    git-Prozess, 0 Byte, aelter als Minuten) blockiert jeden Commit — die Sperre UMBENENNEN
    (`mv .git/index.lock .git/index.lock.verwaist-<datum>`), nicht loeschen:
    laeuft doch ein Schreiber, ist die Datei der einzige Hinweis darauf. Nur
    bei einem AKTIVEN git-Prozess warten.
- **Der fertige Bericht einer parallelen Sitzung ist eine Behauptung, kein Beleg** — auch
  wenn er plausibel klingt und eine Kommandoausgabe mitbringt. Meist fehlt genau der
  entscheidende Schritt: belegt ist der Transport oder die Datei, nicht die Wirkung — dazu
  die Restliste. Diesen fehlenden Schritt selbst nachziehen und als eigenes Ergebnis
  ausweisen, statt ihn der anderen Sitzung zuzuschreiben.

## Verweise

- `hermes-config-ops` — wenn der Stand eine Hermes-Einstellung betrifft: dort steht, wie
  man „was gilt" belegt (Kommando statt YAML-Lesen) und wo Vorher-Kopien liegen.
- `absturz-recovery` — wenn zusätzlich der Arbeitsbaum nach einem Absturz zu prüfen ist.
- `subagent-delegation` — die Lehren zur Kind-Seite: output_schema erzeugt eine
  Wiederholungsschleife, fertige Artefakte vor dem Neu-Dispatch bergen, Fristen
  gehoeren in den Auftrag.
- Hinweis: `absturz-recovery` ist nutzereigen und für die automatische Pflege gesperrt
  (`hermes curator adopt absturz-recovery`, wenn sie mitgepflegt werden soll).

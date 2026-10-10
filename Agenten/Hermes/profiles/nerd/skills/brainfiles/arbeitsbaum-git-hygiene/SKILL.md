---
name: arbeitsbaum-git-hygiene
category: brainfiles
description: "Use when Commits fremde Aenderungen mitnehmen koennten."
version: 0.1.0
author: Hermes
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [git, arbeitsbaum, fremdarbeit, gitignore, commit, brainfiles]
    related_skills: [brainfiles-auftrag, hermes-config-ops, sichern]
---

# Fremdarbeit im Arbeitsbaum stehen lassen, eigene Aenderung committen

An einem BrainFiles-Baum arbeiten **mehrere Sitzungen gleichzeitig** (Desktop, CLI,
Telegram, Bots). Deshalb steht beim Commit fast immer mehr im Baum als die eigene
Aenderung. Dieser Skill ist die Disziplin, die eigene Aenderung sauber
herauszuschneiden — Fachliches und Dokumentation stehen in `brainfiles-auftrag`,
die Hermes-Config im Einzelnen in `hermes-config-ops`.

## Wann

- `git status` zeigt Dateien, die diese Sitzung nie angefasst hat
- in EINER Datei stehen eigene und fremde Aenderungen nebeneinander (`config.yaml`,
  Bus-Zustaende, `stand.json`, Skill-Dateien)
- eine Datei soll aus dem Verlauf verschwinden (Nebenprodukt eines Fremdprogramms)
- eine `.gitignore`-Freigabe soll zurueckgenommen werden
- „geh die letzten Sitzungen und Hintergrund-Aufgaben nach Aenderungen durch, die noch
  nicht uebernommen wurden" — dann Abschnitt „Fremde Arbeit aus beendeten Sitzungen
  einsammeln"

## Regeln (immer)

1. **Nie `git add -A`, nie `git commit -a`.** Nur namentliche Pfade stagen
   (`git add -- <pfad1> <pfad2>`). Der Hinweis „modified by sibling subagent" in einem
   Werkzeug-Ergebnis ist echt, nicht Rauschen.
2. **Vor dem Commit zwei Blicke:** `git status --porcelain` (was ist ueberhaupt da) und
   `git diff --cached` (was geht wirklich mit). Danach `git show --stat` gegen die
   Absicht halten. **Und die ZAHL pruefen, nicht nur die Namen:**
   `git diff --cached --name-only` zaehlen und bei mehr Pfaden als den eigenen
   abbrechen (`git reset -- <fremder-pfad>` nimmt einen fremden Eintrag zurueck, ohne
   den Arbeitsbaum anzufassen) - der Index kann von einer anderen Sitzung gefuellt
   sein, und ein `git commit` ohne Pfadangabe nimmt alles mit, was darin steht.
3. **Gemischte Datei = nur die eigene Aenderung in den Index, nicht die Datei opfern
   und nicht die Fremdarbeit mitnehmen.** Zuerst `git diff --numstat -- <datei>` lesen:
   mehrere Hunks unterschiedlicher Groesse heissen "hier steckt fremde Arbeit drin".
   Dann den Index DETERMINISTISCH bauen statt Hunk-Antworten zu raten:
   `git show HEAD:<datei>`, die eigene Aenderung byte-genau im Speicher einsetzen,
   `git hash-object -w --path=<datei> --stdin`, danach
   `git update-index --cacheinfo 100644,<sha>,<datei>`. Der Arbeitsbaum bleibt
   unberuehrt (die fremde Aenderung steht weiterhin als `M`), und
   `git diff --cached --numstat -- <datei>` nennt genau die eigenen Zeilen —
   `30 0` = ein eingefuegter Abschnitt, `32 2` = Abschnitt plus zwei geaenderte
   Frontmatter-Zeilen. Gegenprobe: `git diff --numstat -- <datei>` muss die fremden
   Zeilen unveraendert weiter ausweisen. Text dabei binaer lesen und schreiben
  (`read_bytes`/`write_bytes`) — `read_text()`/`write_text()` ohne `newline=""`
  kippen das Zeilenende in BEIDE Richtungen (CRLF-Datei wird LF, LF-Datei wird
  CRLF, weil `write_text` den Umbruch gegen `os.linesep` tauscht), und der Diff
  zeigt danach die GANZE Datei. Nach JEDER Textaenderung `git diff --numstat`
  JE Datei zaehlen; ist die ganze Datei umgekippt, das Zeilenende auf den
  HEAD-Stand zuruecknormalisieren (`read_bytes().decode(...).replace(CRLF, LF)`
  bzw. umgekehrt, dann `write_bytes`) statt den Churn zu committen — die
  Semantik ist dann schon geprueft, `yaml.safe_load`/`json.load` beweist, dass
  nur die Enden normalisiert wurden.
   **Der so gebaute Index wirkt nur bei `git commit` OHNE Pfadangabe.**
   `git commit -- <pfad>` committet den ARBEITSBAUM dieser Pfade (wie `git add <pfad>`
   plus Commit) und wirft den eigenen Index-Eintrag weg: die fremden Zeilen gehen mit
   hinein, obwohl `git diff --cached` unmittelbar vorher nur die eigenen zeigte. Also
   erst `git update-index --cacheinfo …`, dann `git diff --cached --name-only` lesen,
   dann `git commit` ohne Pfade. Ist es doch passiert: `git reset --soft HEAD~1`, Index
   deterministisch neu bauen, ohne Pfadangabe erneut committen — und `git show --stat`
   gegen die Absicht halten (je Datei 2/1, nicht 39 Zeilen). `git commit -- <pfad>`
   ist auch dann kein Ersatz, wenn nur EINE Datei betroffen ist.
   `git add -p` bleibt der Notweg fuer zwei klar getrennte kleine Hunks; dort die
   Antwortfolge nicht raten, sondern `git diff --cached -- <datei>` nachlesen und bei
   Abweichung mit `git restore --staged <datei>` neu beginnen — die Zahl der Hunks ist
   vorher nicht sicher bekannt.
4. **Fremde Aenderungen bleiben als `M` im Arbeitsbaum** und werden im Commit-Text als
   NICHT enthalten benannt, nicht stillschweigend mitgenommen und nicht verworfen.
   Fremd Gestagetes nie mitcommitten. **Liegen bleiben heisst aber nicht fuer immer:**
   was niemand einsammelt, holt die Routine `Agenten/Routinen/fremdarbeit-einziehen.ps1`
   (taeglich 20:40, Aufgabe `MaxHirn-Fremdarbeit-Einziehen`) in EINEM Commit mit dem
   Autor `Andere Sitzung <fremd@local>` nach `master` - siehe den Abschnitt
   „Fremde Arbeit aus beendeten Sitzungen einsammeln".
5. **Ein Commit kann einen fremden, schon vorhandenen Commit vor sich haben.** Nach
   dem Push `git log --oneline -4` lesen und im Bericht nennen, was mitging, das nicht
   aus dieser Sitzung stammt. **Und der eigene, schon GESTAGTE Eintrag kann in einem
   fremden Commit landen:** ein `git commit` der anderen Sitzung ohne Pfadangabe
   committet den ganzen Index mit. Deshalb Index bauen und committen in DERSELBEN
   Ausfuehrung, ohne Zeitfenster dazwischen — und danach `git show --stat HEAD` lesen:
   traegt der neueste Commit eine fremde Nachricht und die eigene Datei, ist die
   Aenderung inhaltlich da, aber falsch beschriftet; das im Bericht sagen, statt sie
   ein zweites Mal zu committen (ein zweiter Commit derselben Zeile ist ein leerer
   Diff und verwirrt mehr, als er klaert).
6. **Eine fremde Aenderung, die einen Absturz oder Testfehlschlag verursacht, wird
   wie ein eigener Bug behandelt — nicht nur liegen gelassen.** Eine plausibel
   klingende Begruendung im Fremd-Commit ('X sollte nicht wie Y zaehlen') ist kein
   Beleg: vor dem Vertrauen alle echten Aufrufer des geaenderten Codes greppen und
   pruefen, ob der behauptete Fall ueberhaupt im echten Code vorkommt. Nach jeder
   verdaechtigten externen Aenderung die volle Testsuite laufen lassen, nicht nur
   den vom Fremd-Commit behaupteten Fall — ein Fix fuer einen nie eintretenden Fall
   kann echte Aufrufer zerstoert haben, ohne dass ein einzelner gezielter Test das
 zeigt.
 7. **Der Baum kann sich zwischen zwei Werkzeugaufrufen aendern.** Eine zweite
 Sitzung baut denselben Auftrag fertig, waehrend diese noch Kontext sammelt:
 Dateien, die eben noch `??` oder `M` waren, sind Minuten spaeter committet -
 im Zweifel von einem Commit, den diese Sitzung nie gesehen hat. Vor dem ersten
 Schreibzugriff den Stand FRISCH lesen (`git status --porcelain -- <pfad>`,
 `git log --oneline -3`); ein Blick von vor zwei Minuten ist keine Grundlage,
 und ein `search_files`-Treffer auf einen alten Dateinamen ist oft schon der
 Beweis, dass jemand anderes umbenannt hat. Ist die Arbeit schon da, wird sie
 NACHGEMESSEN und berichtet statt ein zweites Mal gebaut - sonst entstehen
 Doppelarbeit und ein Commit, der fremde Arbeit als eigene ausgibt.
 8. **Einen Rueckstand-Commit vorher pruefen, nicht blind stagen.** Soll ein Stapel
 Dateien auf einmal mit (halbe Skill-Bibliothek, unversionierte Ordner aus frueheren
 Sitzungen), erst (a) nach Kennungen suchen
 (`grep -rInE 'sk-[A-Za-z0-9]{20}|ghp_[A-Za-z0-9]{20}|rt_[A-Za-z0-9]{20}|<eigene Token-Praefixe>' <pfad>`)
 und jeden Treffer einzeln lesen — Platzhalter wie `ghp_xx...xxxx` in einer Doku sind
 harmlos, echte Werte nicht; (b) je `SKILL.md` das Frontmatter pruefen (beginnt mit
 `---`, `name` und `description` gesetzt), sonst geht eine halb geschriebene Datei mit;
 (c) im Commit-Text sagen, dass der Stapel aus frueheren Sitzungen stammt und was davon
 heute dazukam. Fremde Arbeit in einem Rueckstand ist kein Grund, sie liegen zu lassen,
 wenn der Nutzer den Stapel ausdruecklich freigibt — aber der Text muss die Herkunft
 nennen.
 **Zeitgrenze und Urheber:** einen Stapel fremder Arbeit NICHT mit `git add -A`
 einziehen, sondern aus `git status --porcelain` die Pfade sammeln und je Pfad die
 mtime gegen eine Grenze halten (`time.time() - 20*60`): was juenger ist, gehoert
 einer SITZUNG, DIE GERADE SCHREIBT — halb geschriebene Dateien gehen sonst mit.
 Alles unter einem Junction-Ordner (`Werkstatt/` -> O:) bleibt draussen, das ist
 Durchgangsware, kein Repo-Inhalt. Ist der Stapel vollstaendig fremd, ist EIN
 Commit mit `--author="Andere Sitzung <fremd@local>"` und im Text die Herkunft
 („nicht sicher zuzuordnen, mehrere Sitzungen parallel") die richtige Form;
 gemischte Dateien (eigene + fremde Zeilen) gehen NICHT in diesen Comm
 it — die eigene Zeile behaelt ihren eigenen Commit (Regel 3).

## Fremde Arbeit aus beendeten Sitzungen einsammeln

**Zuerst nachsehen, was schon geholt wurde, statt es ein zweites Mal zu bauen:**
`Agenten/Routinen/fremdarbeit-einziehen.ps1` laeuft taeglich 20:40 und zieht die RUHENDE
Fremdarbeit selbst nach `master` (Autor `Andere Sitzung <fremd@local>`, Schwelle 30 min,
eigener Index, `update-ref` mit Alt-Wert). Stand lesen mit
`git log --oneline --author=fremd@local`; Probe mit `-Testlauf`. Die Uebernahme von Hand
bleibt richtig und ist schneller - die Routine ist der Nettofang fuer alles, was liegen
bleibt, und sie zieht nach jedem eigenen Commit den normalen Index fuer die uebernommenen
Pfade nach (sonst meldet `git status` sie gleichzeitig als geloescht und als ungetrackt).
Das vollstaendige Rezept - Bauart des Skripts, Ruhekriterium, Index-Nachtrag,
Testaufbau, Registrierung der Aufgabe - steht in `references/fremdarbeit-routine.md`.

Der Auftrag „die letzten Sitzungen / Hintergrund-Aufgaben nach nicht uebernommenen
Aenderungen durchgehen" meint selten die OFFENEN Sitzungen: die liegengebliebene Arbeit
steckt in den gerade BEENDETEN Hintergrund-Sitzungen (`bg_*`, `tui`, `cli`) und in
ungetrackten Dateien. Reihenfolge:

1. **Bestand aus dem Baum zuerst** — `git status --porcelain`, je Treffer die mtime.
   `??`-Dateien sind die Kandidaten. `M` an einer Datei, die diese Sitzung nie anfasste,
   ist fremde, womoeglich noch laufende Arbeit.
2. **Die BEENDETEN Sitzungen lesen, nicht die offenen.** Jedes Profil hat eine eigene
   `state.db`; `offene_sitzungen.py` zeigt beendete nicht (`ended_at` ist gesetzt).
   Direkt abfragen:
   `SELECT id, source, title, ended_at, started_at FROM sessions ORDER BY started_at DESC LIMIT 25`,
   dann je Sitzung die letzten Nutzer- und Assistentenzeilen (`SELECT role, content FROM
   messages WHERE session_id=? AND role IN ('user','assistant') AND content!='' ORDER BY
   id DESC LIMIT 4`). Der Schlussbericht nennt die offenen Punkte und die „Naechste
   Aktion" — das ist die Landkarte der liegengebliebenen Arbeit.
3. **Jede Behauptung daraus gegen den Baum pruefen.** Ein Selbstbericht ist kein Beleg:
   genannte Commits (`git log --oneline | grep <hash>`), Dateien
   (`git status --porcelain -- <pfad>`) und Zahlen einzeln nachsehen. Der typische
   Ausgang ist „Treiber und Messung geschrieben, Ergebnis nie committet", waehrend der
   Bericht mit „Naechste Aktion: Ergebnis ansehen" endet.
4. **Uebernehmen heisst nachmessen, dann committen.** Fremdes, ruhendes (>10 min) geht
   in EINEN Commit mit `--author="Andere Sitzung <fremd@local>"` und der Herkunft im
   Text; gemischte Dateien nach Regel 3; Durchgangsware unter `Werkstatt/` (Regel 4) und
   Datenausgaben ueber der Whitelist bleiben draussen und gehoeren in den Bericht unter
   „nicht angefasst".
5. **Was eine laufende Sitzung gerade schreibt, wird nur benannt.** Der Stand aendert
   sich zwischen zwei Werkzeugaufrufen (Regel 7): vor dem Uebernahme-Commit frisch
   `git status --porcelain` lesen, sonst zieht man halb fertige Arbeit hinein.

## Datei soll aus dem Verlauf verschwinden

1. **Erst den Schreiber finden, dann loeschen.** Taucht ein Nebenprodukt (Vorlage, Log,
   Cache) an wechselnden Stellen im Baum auf, sucht man die Quelle
   (`grep -rn "<dateiname>" <programmpfad>`) und gibt dem Programm ein festes
   Arbeitsverzeichnis. Nur loeschen heisst: beim naechsten Start ist es wieder da.
2. **Nachweis aus einem FREMDEN Ordner fahren:** Kopie loeschen, Programm aus einem
   anderen Arbeitsverzeichnis starten, pruefen, wo die Datei neu entsteht. Erst damit
   ist die Ursache belegt und nicht nur die Wirkung.
3. **Eine `.gitignore`-Aenderung nimmt nichts aus dem Verlauf.** Was einmal committet
   wurde, bleibt trotz neuer Sperre versioniert und in `git status` sichtbar — es braucht
   ein `git rm`. Zwei Faelle nicht verwechseln: eine Datei, die WEG soll → `git rm`
   (loescht sie auch auf der Platte). Eine Datei, die auf der Platte BLEIBEN muss, aber
   nicht mehr in den Verlauf gehoert — Laufzeitzustand, den jeder Lauf neu schreibt
   (`.curator_state`, `.usage.json`, `stand.json`, `kontext.json`) → **`git rm --cached`**,
   sonst loescht man den lebenden Zustand eines Dienstes. Danach die Sperrzeile in die
   `.gitignore` ans Ende der zustaendigen Gruppe (spaetere Regel gewinnt) und mit
   `git check-ignore -v <pfad>` belegen, dass sie GREIFT. Der Nutzen ist messbar: ohne die
   Sperre steht in JEDEM `git status` eine Phantom-Aenderung, die jede Status-Sicht
   verfaelscht.
4. **`git check-ignore -v <pfad>` meldet versionierte Pfade grundsaetzlich nicht.** Wer
   prueft, ob eine zurueckgenommene Freigabe greift, fragt
   `git check-ignore -v --no-index <pfad>` — sonst haelt er die fehlende Meldung fuer eine
   fehlende Regel. Gegenprobe fuer neu angelegte Dateien: Datei anlegen, pruefen, loeschen.
5. **Grundsatzregel statt Freigabe.** Dieses Repo arbeitet als Whitelist (`*` ignoriert
   alles, unten wird einzeln freigegeben). Eine Freigabe fuer ein Nebenprodukt
   (`!**/*.env.template`) nimmt nur Servermuell in den Verlauf auf — Nebenprodukte bleiben
   ignoriert, verhindert wird ihre Entstehung am Schreiber (Schritt 1).

## Fallen

- **Ein Fremd-Klon IM versionierten Baum kann eine ganze Routine stilllegen.** Ein
  verschachteltes Repo versioniert Git nie (es merkt nur einen Zeiger an); hat es
  zusaetzlich keinen Commit ausgecheckt, bricht `git add -A` mit Exitcode 128 ab
  (`error: '<pfad>/' does not have a commit checked out`, `fatal: adding files failed`)
  - und damit JEDER Lauf, der `git add -A` benutzt. Am 19.09.2026 landeten zwoelf
  Klone (1,8 GB) in `Agenten/Hermes/skills/`, einer davon (`mfaupel95`) ohne Commit;
  die taegliche Routine `zwischenstand.ps1` scheiterte daraufhin an drei Abenden in
  Folge ("ENDE FEHLER: git add fehlgeschlagen"), ohne dass der Zweig `zwischenstand`
  noch wuchs. **Unsichtbar, solange niemand den Zweig ansieht:** Fruehwarnung ist
  `git log -1 --format=%ci zwischenstand` - steht der letzte Zwischenstand tagealt,
  liegt es nicht an fehlenden Aenderungen, sondern an einem Abbruch. Beleg und
  Gegenprobe sind EIN Befehl: `git add -A --dry-run` mit `echo $?` (128 = Abbruch,
  0 = gesund), die Ursache steht in der Ausgabe. Fix ist eine Sperrzeile je
  Fremd-Klon im `.gitignore` - nicht das Loeschen.


- **Neuer Ordner in der Whitelist: jede Ebene einzeln freigeben.** Ein neuer
  Unterordner (`Agenten/Handel/docs/plans/`) bleibt fuer Git unsichtbar, bis JEDE
  Ebene eine eigene `!`-Zeile hat (`!…/docs/`, `!…/docs/plans/`, dann
  `!…/docs/plans/*.md`) - sonst entsteht eine Datei, die nie versioniert wird, ohne
  dass irgendwo ein Fehler auftaucht. Beleg ist `git status --porcelain -- <ordner>`:
  `??` heisst sichtbar, `!!` heisst ignoriert. Was Git wirklich aufnehmen wuerde,
  sagt `git add --dry-run -- <pfade>`: fehlt eine erwartete Datei in der Ausgabe,
  ist sie entweder ignoriert ODER schon versioniert — die Ausgabe unterscheidet
  das nicht, `git ls-files <pfad>` tut es. `git check-ignore -v <pfad>` gibt auch
  bei einer Negationsregel 0 zurueck und nennt die Regel - daraus laesst sich die
  Sichtbarkeit NICHT ablesen. Neue Zeilen mit dem Zeilenende der Datei anhaengen
  (`.gitignore` ist LF, binaer lesen/schreiben).
- **Das Loeschen UNGETRACKTER Dateien ist kein Git-Event.** `git add <untracked-datei>` schlaegt mit `fatal: pathspec … did not match any files` fehl (die Datei ist nie im Index), und `git add -A <ordner>` als Ersatz nimmt JEDE andere ungetrackte Datei in dem Ordner mit — der Commit traegt dann eine Nachricht, die nicht zum Inhalt passt (passiert mit einer `BEFUND-*.md`, die versehentlich mitcommittet wurde). Eine ungetrackte Datei ist mit `rm` schon geloescht; es gibt nichts zu stagen. Nur GETRACKTE Loeschungen brauchen `git add`/`git rm`. Wer eine Loeschung committen will, stagt ausschliesslich die getrackten Pfade namentlich und prueft `git diff --cached --stat` gegen die Absicht — nie `git add -A <ordner>`.
- **Eine geloeschte Datei hat keine mtime - die Ersatzwahrheit ist ihr ORDNER.** Wer
  ruhende Fremdarbeit nach Aenderungsalter auswaehlt, findet fuer ` D`-Eintraege keinen
  Zeitstempel. Sie deshalb als ruhend zu behandeln ist falsch: Windows schreibt beim
  Loeschen die Zeit des ORDNERS fort, also `LastWriteTime` des Elternordners messen.
  Ist er frisch, ruht die Loeschung nicht und bleibt liegen. Folge, die man kennen
  muss: eine Loeschung wird fruehestens im naechsten Lauf uebernehmbar und nie,
  solange in demselben Ordner weiter geschrieben wird.
- **Ein Commit ueber einen EIGENEN Index laesst den normalen Index stale zurueck.**
  Wer fremde Arbeit committet, ohne den Staging-Bereich anzufassen (`GIT_INDEX_FILE`
  + `git read-tree <tip>` + `git add -- <pfade>` + `git write-tree` + `git commit-tree`
  + `git update-ref refs/heads/master <neu> <alt>`), hat danach fuer JEDEN uebernommenen
  Pfad einen Index, der den neuen HEAD nicht kennt: eine neue Datei steht gleichzeitig
  als `D ` (Index gegen HEAD) und `??` (ungetrackt), eine geaenderte als `M ` mit dem
  ALTEN Inhalt - und ein `git commit` einer anderen Sitzung ohne Pfadangabe (es
  committet den ganzen Index) wuerde die neuen Dateien wieder loeschen bzw. die
  Aenderungen zurueckdrehen. Nach dem Commit je Pfad den ECHTEN Index angleichen,
  aber nur dort, wo er noch auf dem Stand VOR dem Commit steht (`git ls-files -s`
  gegen `git ls-tree <alt-tip>` vergleichen): `git update-index --add --cacheinfo
  <mode>,<sha>,<pfad>` bzw. `git update-index --force-remove -- <pfad>`. Eine frische
  Vormerkung einer anderen Sitzung (Index-Blob != Alt-Stand) bleibt unberuehrt.
  Vorher `Remove-Item Env:\GIT_INDEX_FILE` - sonst schreibt `update-index` in den
  falschen Index. Die Reparatur ist idempotent und laeuft am besten zu Beginn jedes
  weiteren Laufs ueber die Pfade der letzten eigenen Uebernahme-Commits
  (`git log -5 --author=fremd@local --name-only --format=`). Rezept:
  `references/fremdarbeit-routine.md`.
- **`Set-Content -Encoding UTF8` schreibt ein BOM.** Unter PS 5.1 wandert es als
  unsichtbares Zeichen in die erste Zeile - und bei `git commit-tree -F <datei>`
  direkt in die Betreffzeile des Commits (`git log` zeigt dann ein BOM vor dem
  Betreff). Nachrichtendateien mit `[System.IO.File]::WriteAllText($pfad, $text,
  (New-Object System.Text.UTF8Encoding($false)))` schreiben.
- **`fatal: Unable to create '…/.git/index.lock': File exists`** heisst fast immer:
  eine andere Sitzung schreibt GERADE in denselben Index. Die Sperre NICHT loeschen -
  warten (Sekunden) und denselben Befehl wiederholen, dann geht er durch. Ist die
  Sperre 0 Byte gross und liegt sie schon viele Minuten, in einer Schleife pollen
  (`for i in $(seq 1 25); do [ -e .git/index.lock ] || break; sleep 20; done`) statt
  einmal zu warten — ein echter paralleler Commit braucht Sekunden, ein haengender
  Prozess laesst die Sperre stehen. Erst wenn der eigene Befehl ueber ~5 Minuten
  wiederholt daran scheitert, sie per `mv` zur Seite legen
  (`.git/index.lock.verwaist-<zeitstempel>`, nie loeschen — der Schritt muss umkehrbar
  bleiben) und im Bericht sagen, dass eine parallele Sitzung aktiv war. **Unter
  Windows mit `[System.IO.File]::Move($quell, $ziel, $true)` umbenennen, NICHT mit
  `Move-Item`:** bei der versteckten Datei `.git\index.lock` tat `Move-Item` still
  NICHTS (keine Fehlermeldung, die Sperre stand danach unveraendert mit altem
  Zeitstempel da, waehrend die Ausgabe wie Erfolg aussah). Danach mit `Test-Path`
  auf BEIDE Pfade nachsehen - sonst arbeitet man weiter gegen eine Sperre, die man
  fuer weg haelt. **Prozesse ansehen,
 nicht nur die Uhr:** `git fsmonitor--daemon` laeuft dauerhaft und ist KEIN Commit —
 eine `git.exe`-Liste voller fsmonitor-Zeilen beweist keine parallele Sitzung. Ein
 echte Committer hat eine CreationDate in den letzten Sekunden und `add`/`commit`
 in der Kommandozeile; fehlt beides und ist die Sperre 0 Byte und aelter als ein paar
 Minuten, ist sie verwaist.
 **Die ZAHL der `git.exe` ist kein Kriterium, nur die ART.** Eine lange Liste
 beantwortet die Frage nicht: sie kann vollstaendig aus `fsmonitor--daemon`
 bestehen (die laufen dauerhaft, auch ohne jede Fremdsitzung). Erst filtern
 (`Get-CimInstance Win32_Process -Filter "Name='git.exe'" | Where-Object {
 $_.CommandLine -notlike '*fsmonitor*' }`): bleibt die gefilterte Liste LEER und
 ist die Sperre 0 Byte und aelter als ein paar Minuten, ist sie verwaist -
 umbenennen und denselben Befehl sofort wiederholen, das ist dann der richtige
 Weg und kein Risiko.
 **Laeuft dagegen ein ECHTER Committer** (CreationDate in den letzten Sekunden,
 `add`/`commit` in der Kommandozeile) und haelt die Sperre ueber die Wartezeit
 hinweg, ist die richtige Antwort NICHT das Umbenennen, sondern der Abbruch: die eigene Arbeit liegt vollstaendig und unversehrt auf der Platte,
 nur uncommittet. Dann den Bericht als „gebaut und geprueft, Commit haengt an einer
 fremden Git-Sperre" schreiben, die Sperre unangetastet lassen und den Commit in
 einer spaeteren Runde nachziehen (oder dem Nutzer anbieten, ihn auszuloesen).
 Kein force, kein `git commit --amend`, kein Wegwerfen der Aenderung, und den
 Erfolg nicht als „fertig committet" melden, solange `git log` ihn nicht zeigt.
 Die Sperre
 ist damit auch ein Messinstrument: sie zeigt an, dass parallel committet wird, also
 direkt danach `git log --oneline -4` lesen und benennen, was mitging, das nicht aus
 dieser Sitzung stammt.
- **Zeilenenden.** Versionierte Textdateien in BrainFiles sind teils CRLF (`.gitignore`
  LF, `config.yaml` CRLF, viele `SKILL.md` CRLF). Nach JEDER Textaenderung
  `git diff --numstat <pfad>` lesen: eine gewollte Zeile = 1/1. Zeigt der Diff die ganze
  Datei, `git checkout HEAD -- <pfad>` und byte-genau neu patchen — nicht committen.
  **Eine Datei kann GEMISCHT sein** (ueberwiegend CRLF mit einzelnen LF-Zeilen —
  `Wissen/Routinen.md` und viele `SKILL.md` sind es): vor dem Schreiben die Enden
  binaer zaehlen (`b.count(b"\r\n")` gegen `b.count(b"\n")`; ein Textmodus-`read()`
  verschleiert das). Ein Rewrite, der das DOMINANTE Ende auf alle Zeilen anwendet,
  dreht genau die einzelnen Zeilen um und erzeugt Diff-Churn, den niemand gemacht hat
  (gemessen: 6 geaenderte Zeilen statt der einen eingefuegten). Richtig ist, aus der
  `.bak` BYTE-GENAU einzufuegen: `open(pfad,'rb').read()`, Anker als bytes suchen
  (`assert b.count(anker) == 1`), hinter dem Anker einfuegen, `open(pfad,'wb').write()`
  — nichts normalisieren. Gegenprobe: `git diff --numstat` muss reine Einfuegungen
  zeigen (`55 0`), keine Loeschungen.
- **Ein Ganzdatei-Diff kommt nicht immer von den Zeilenenden — der INDEX kann stale sein.**
  `git diff` vergleicht Arbeitsbaum gegen INDEX, nicht gegen HEAD. Liegt im Index noch eine
  frueher gestagte Fassung (typisch nach einem abgebrochenen oder verweigerten Commit),
  zeigt der Diff scheinbar die ganze Datei, waehrend der Arbeitsbaum in Ordnung ist. Vor
  jeder Selbstheilung beide Seiten ansehen: `git diff --cached --numstat` (Index gegen HEAD)
  und `git diff --numstat` (Arbeitsbaum gegen Index). Bringt `git reset -- <pfade>` die
  kleinen Zahlen zurueck, war nur der Index stale — `reset` ohne `--hard` fasst den
  Arbeitsbaum nicht an und ist damit auch im Mehrsitzungsbetrieb erlaubt.
- **Eine `.bak-JJJJMMTT` ist der Stand IHRES Vorgangs, nicht der von HEAD.** Eine
  gleichnamige Sicherung aus einer frueheren Runde zurueckzukopieren holt stilla alle
  Aenderungen zurueck, die seither committet wurden (gemessen: eine Instrumentenliste und
  eine ganze Wachen-Datei). Richtiger Rueckweg fuer "meine Zeilen raus": den Zieltext aus
  `git show HEAD:<pfad>` nehmen und die gewollte Aenderung byte-genau einsetzen; die
  Sicherung nur benutzen, wenn sie NACHWEISLICH der letzte Commit-Stand ist (Hash gegen
  `git show HEAD:<pfad>` vergleichen). Und: in einem VERSCHACHTELTEN eigenen Repo
  (`Agenten/Handel/nautilus/`) ist die Datei fuer BrainFiles ungetrackt — dort liefert
  `git show HEAD:<pfad>` LEER, ohne Fehlermeldung: Rueckgriff auf `git -C <unterrepo> show
  HEAD:<datei>` und den Commit auch dort machen. Leerer Treffer immer als Verdacht lesen,
  nicht als "Datei ist leer".
- **Beim Einfuegen in JSON/YAML nach dem Schreiben parsen lassen, und die Kommas mitdenken.**
  Eine eingefuegte Zeile, deren Wert ein doppeltes Anfuehrungszeichen enthaelt, zerbricht die
  Datei (`Expecting ',' delimiter` an der Folgezeile) — im Textwert einfache Anfuehrungszeichen
  verwenden oder escapen. Und: eine neue Zeile hinter `"schluessel": false,` braucht genau
  dann ein abschliessendes Komma, wenn die Ankerzeile eins hatte; fehlt es, ist das Objekt
  ungueltig, steht aber optisch richtig da. Nach jedem Einfuegen `json.loads`/`yaml.safe_load`
  auf die GESCHRIEBENE Datei (nicht auf den Text im Speicher) und die drei Zielwerte asserten.
  **Eine schreibende Funktion nie als "Probe" gegen das ECHTE Ziel laufen lassen:** ein
  Testaufruf am echten Buch schreibt Journalzeilen, auch wenn er nur pruefen sollte — Probe
  gegen eine Kopie, sonst muss der Zustand von Hand nachgezogen werden.
- **`patch` auf `Agenten/Hermes/config.yaml` ist gesperrt** („Refusing to write to Hermes
  config file"); dafuer `hermes config set`. Siehe `hermes-config-ops`.
- **Ein `.bak-JJJJMMTT` ist nicht nur Sicherung, sondern der einzige Rueckweg**, wenn ein
  Werkzeug die Datei umschreibt (z. B. `hermes config set` schneidet den Kommentar-Schluss
  ab). Byte-genau zurueckspielen: aus der Sicherung den Zieltext ersetzen, Anker auf
  `count == 1` asserten, Zeilenenden binaer erhalten. **Anker am Dateiende braucht das
  Zeilenende, das WIRKLICH dort steht:** fehlt der letzten Zeile das abschliessende
  `\n` (verraet `text.count('\n')` um genau 1 kleiner als die Zeilenzahl), trifft ein
  Anker MIT `\n` nie - 0 Treffer, und die ganze Ersetzung faellt aus, obwohl der Text
  sichtbar dasteht. Vor dem Schreiben einmal `repr(text[i:i+len(alt)])` gegen den Anker
  halten, statt den Fehlschlag einer anderen Ursache zuzuschreiben; beim Einfuegen am
  Dateiende das fehlende neue Zeichen mitliefern, sonst schliesst man die letzte Zeile
  an die neue an.
- **Verwaisten Worktree/Branch nicht raten, sondern nachmessen und sauber entfernen.** Ein
  geloester Arbeitsbaum (z. B. `.worktrees/2` auf Branch `2`) ist kein Verlustrisiko, wenn
  seine Commits schon in master stecken. Vor jeder Entfernung belegen:
  `git merge-base --is-ancestor <sha> refs/heads/master` (Exit 0 = alles ist drin) und
  `git rev-list --left-right --count master...<sha>` (`0 <n>` = reiner Vorfahre). Erst dann
  `git worktree remove --force <pfad>`, `git branch -D <zweig>`, `git worktree prune`.
  `git branch -D` bleibt gegen die Gegenprobe verboten; `-D` ohne Nachweis ist hier genau
  wie bei einem normalen Zweig der Fehler. Nachher `git worktree list` + `git branch -a`:
  es soll nur noch `master` (plus `zwischenstand` = Nachtsicherung) stehen.
- **Nested `copilot-worktrees/*` in Klon-Repos sind KEIN Aufraeumkandidat.** `git worktree
  list` in einem Klon unter `Werkstatt/Repos/<repo>` zeigt neben dem Hauptbaum oft
  `Werkstatt/Repos/copilot-worktrees/<repo>/<name>` auf einem Branch mit automatischem
  Copilot-Namen. Das ist die eigene Feature-Sammlung von Copilot (jeder auf dem Helden-
  Commit), nicht ein verwaister BrainFiles-Worktree. Nie mit `git worktree remove` anfassen
  — nur Worktrees im BrainFiles-eigenen Baum (`BrainFiles/.worktrees/*`) aufraeumen, die
  von dieser oder einer fremden Sitzung stammen.
- **Ein riesiger Diff an einer config/JSON-Datei ist oft CRLF-Umstellung, kein Umbau.**
  Zeigt `git diff --numstat <datei>` ~4600/4600 Zeilen an einer Datei, die du nicht
  sinnvoll umgebaut hast, erst mit `git diff --numstat --ignore-all-space <datei>` messen:
  faellt es dort auf 5/4, ist der Arbeitsbaum nur auf LF oder CRLF umgekippt (Fremdsitzung
  hat die Datei mit anderem Zeilenende neu geschrieben), nicht inhaltlich geaendert. Das
  aendert das Urteil: so eine Datei ist Zeilenende-Churn, keine echte Fremdarbeit, und
  gehoert im Bericht als solche benannt statt als „grosse Fremdaenderung".
- **Ein versioniertes Skript buergt nicht fuer die Dateien, auf die es verweist.**
  `!Agenten/Routinen/*.ps1` gibt nur die `.ps1` frei; die Startverknuepfung
  (`*.vbs`), auf die ein Wrapper im Kopf verweist, bleibt unter `*` ignoriert und
  liegt dann als einziger Autostart-Weg nur auf dieser Platte. Beim Anlegen oder
  Versionieren eines Start-/Hilfsskripts die Geschwisterdateien mitpruefen
  (`git check-ignore -v --no-index <pfad>` je Datei) und einzeln freigeben — eine
  Freigabezeile mit dem Grund daneben, nicht ein pauschales `!*.vbs`.
  **Dieselbe Falle im Fremd-Klon, eine Ebene tiefer:** eine Hausdatei, die im
  Repo-Ordner unter `Werkstatt/Repos/<repo>` entsteht (eigenes Werkzeug, eigene
  To-do-Notiz), ist dort `??` - der Klon hat ein EIGENES Repo, also schuetzt die
  BrainFiles-`.gitignore` sie nicht und die Sicherung nimmt sie nicht mit. Vor dem
  Melden „fertig" je selbstgebauter Datei `git -C <klon> status --porcelain --
  <datei>` fragen und den ungetrackten Stand nennen (der Klon ist shallow: vor
  einem Push `git fetch --unshallow <upstream>`).

- **`git status` luegt unter `Werkstatt/`.** Bei laufendem `core.fsmonitor` (BrainFiles hatte ihn an) meldet git fuer Pfade unter der Junction `Werkstatt` -> `O:\Werkstatt` „nichts geaendert“, obwohl die Datei neu geschrieben ist: `git diff` bleibt leer, `git add <pfad>` ist still wirkungslos, `git hash-object <pfad>` zeigt dagegen den neuen Inhalt. Wer dem `git status` dort glaubt, committet nichts und merkt es erst beim naechsten Mal. Gegenprobe: `git rev-parse :<pfad>` gegen `git hash-object <pfad>` halten. Fix: `git -c core.fsmonitor=false add <pfad>` - oder fsmonitor im Repo ganz aus, seit 21.09.2026 gesetzt (`git config core.fsmonitor false`). Trifft jeden Pfad unterhalb einer Junction, auch `Modelle`.
## Verification

- `git diff --cached -- <datei>` nennt genau die eigene Aenderung.
- `git diff -- <datei>` laesst die fremden Hunks unveraendert stehen.
- **Erst den Zweig feststellen, dann den Push messen:**
  `git rev-parse --abbrev-ref HEAD`. Nur auf `master` sagt
  `git log origin/master..master` die Wahrheit; auf einem eigenen Zweig — auch
  einem, den eine andere Sitzung angelegt hat — ist der Vergleich LEER, obwohl
  nichts auf GitHub liegt, und die Arbeit sieht gepusht aus, weil gegen den
  falschen Zweig gemessen wurde. Auf fremdem Zweig stattdessen
  `git log --oneline master..HEAD` (was master fehlt),
  `git rev-list --left-right --count master...HEAD` (`0 <n>` = reiner Vorlauf)
  und `git ls-remote --heads origin` (was GitHub ueberhaupt kennt) lesen.
  Hausregel aus AGENTS.md: EIN Arbeitszweig, `master` — einen reinen Vorlauf
  zieht `git branch -f master <zweig>` konfliktfrei nach, dann
  `git push origin master` und den Zweig loeschen. Das aber erst, wenn die
  Sitzung, die darin committet, still ist: ein Merge waehrend fremder Commits
  verschiebt den Zweig unter ihr weg. Ist der Vorlauf nachgezogen (beide Refs
  zeigen auf denselben Commit), kostet das Umschalten nichts: `git checkout master`
  bewegt nur den Zeiger und fasst den dreckigen Arbeitsbaum nicht an - ein voller
  Baum ist KEIN Grund, die Sitzung auf dem Nebenast zu lassen. Danach
  `git branch -d <zweig>` (nie `-D`: `-d` verweigert, wenn die andere Sitzung
  inzwischen weitercommittet hat - genau die gewuenschte Bremse). `-d` verweigert
  aber AUCH aus einem Grund, der kein Warnsignal ist: wenn der Zweig nur gegen
  seinen eigenen Remote-Tracking-Ref gemessen "not fully merged" ist
  (`origin/<zweig>` liegt hinter dem lokalen Zweig). Dann die Sicherheit selbst
  belegen statt sie zu unterstellen: `git merge-base --is-ancestor <zweig> HEAD`
  (0 = alles ist in HEAD) und `git merge-base --is-ancestor <zweig> origin/master`,
  erst danach `git fetch --prune origin` und `git branch -D <zweig>`. `-D` ohne
  diese zwei Gegenproben bleibt verboten.
  **Auf dem Remote liegen oft Zweige, die lokal niemand kennt** (Reste fremder
  Sitzungen und alter Arbeitsbaeume). `git ls-remote --heads origin` listet sie, und
  `git merge-base --is-ancestor origin/<zweig> master` sagt, ob ihre Arbeit schon in
  master steckt (0 = ja) — dann gehoert der Zweig weg
  (`git push origin --delete <zweig>`), sonst waechst eine Liste von Zweigen, die
  wie offene Arbeit aussehen und beim naechsten `ls-remote` wieder Zeit kosten.
  **Dafuer gibt es ein automatisches Netz:** Block 13 in
  `Agenten/Routinen/systempruefung.ps1` (jeder Tageslauf 07:00) meldet
  „Arbeitszweig ist <x>, nicht master“, „N Commit(s) sind nicht auf origin/master“
  und sagt ausdruecklich, wenn `origin/master` lokal unbekannt ist — dann ist die
  Frage nicht messbar statt stillschweigend „sauber“. Wer den Befund im Bericht
  liest, muss ihn nicht neu bauen. **Ein weiterer Pruefschritt dieser Art gehoert
  als Block in den vorhandenen Tageslauf**, nicht in eine neue geplante Aufgabe:
  kein neuer Zeitplan, keine neue `.ps1` in `Agenten/Routinen/` (jede davon wird
  ueber `test_anbindung_routinen.py` automatisch Bus-Routine, was eine stille
  Pruefung nicht braucht) — und das Ergebnis steht am naechsten Morgen im Bericht
  unter „Zu entscheiden“. Beleg wie bei jeder Stufe-1-Datei: Sicherung
  `.bak-JJJJMMTT` daneben, zwei echte Laeufe (`-NurPruefen`) — der erste zeigt den
  Befund, der zweite die Ruhe —, dann genau diesen Pfad committen
  (`git diff --numstat` muss EINEN eingefuegten Block zeigen, keine ganze Datei). und `git branch -vv`
  plus `cat .git/HEAD` als Beleg. Auf dem Remote angekommen ist der eigene Commit
  erst mit `git merge-base --is-ancestor <sha> master` UND
  `git branch -r --contains <sha>` - nicht mit „ich habe gepusht".
  **Eine Push-Zahl ist eine Momentaufnahme.** Zwischen Messen und Berichten kann die
  andere Sitzung committen: aus „0 unpushed" wurde in Minuten „1". Direkt vor dem
  Bericht erneut `git log --oneline origin/master..HEAD` lesen und die Aenderung
  benennen („dazu kam danach noch X, nicht meiner"), statt die alte Zahl zu
  wiederholen - sonst widerspricht sich der eigene Bericht.
- `git log --oneline -1` nennt nur die eigenen Pfade, `git show --stat` passt zur Absicht,
  und der Push ist gegen `origin/master` gehalten (siehe oben, nicht blind vergleichen).

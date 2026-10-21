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

## Regeln (immer)

1. **Nie `git add -A`, nie `git commit -a`.** Nur namentliche Pfade stagen
   (`git add -- <pfad1> <pfad2>`). Der Hinweis „modified by sibling subagent" in einem
   Werkzeug-Ergebnis ist echt, nicht Rauschen.
2. **Vor dem Commit zwei Blicke:** `git status --porcelain` (was ist ueberhaupt da) und
   `git diff --cached` (was geht wirklich mit). Danach `git show --stat` gegen die
   Absicht halten.
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
   kippen eine CRLF-Datei auf LF, und der Diff zeigt danach die GANZE Datei.
   `git add -p` bleibt der Notweg fuer zwei klar getrennte kleine Hunks; dort die
   Antwortfolge nicht raten, sondern `git diff --cached -- <datei>` nachlesen und bei
   Abweichung mit `git restore --staged <datei>` neu beginnen — die Zahl der Hunks ist
   vorher nicht sicher bekannt.
4. **Fremde Aenderungen bleiben als `M` im Arbeitsbaum** und werden im Commit-Text als
   NICHT enthalten benannt, nicht stillschweigend mitgenommen und nicht verworfen.
   Fremd Gestagetes nie mitcommitten.
5. **Ein Commit kann einen fremden, schon vorhandenen Commit vor sich haben.** Nach
   dem Push `git log --oneline -4` lesen und im Bericht nennen, was mitging, das nicht
   aus dieser Sitzung stammt.
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
- **`fatal: Unable to create '…/.git/index.lock': File exists`** heisst fast immer:
  eine andere Sitzung schreibt GERADE in denselben Index. Die Sperre NICHT loeschen -
  warten (Sekunden) und denselben Befehl wiederholen, dann geht er durch. Die Sperre
  ist damit auch ein Messinstrument: sie zeigt an, dass parallel committet wird, also
  direkt danach `git log --oneline -4` lesen und benennen, was mitging, das nicht aus
  dieser Sitzung stammt.
- **Zeilenenden.** Versionierte Textdateien in BrainFiles sind teils CRLF (`.gitignore`
  LF, `config.yaml` CRLF, viele `SKILL.md` CRLF). Nach JEDER Textaenderung
  `git diff --numstat <pfad>` lesen: eine gewollte Zeile = 1/1. Zeigt der Diff die ganze
  Datei, `git checkout HEAD -- <pfad>` und byte-genau neu patchen — nicht committen.
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
- **Ein versioniertes Skript buergt nicht fuer die Dateien, auf die es verweist.**
  `!Agenten/Routinen/*.ps1` gibt nur die `.ps1` frei; die Startverknuepfung
  (`*.vbs`), auf die ein Wrapper im Kopf verweist, bleibt unter `*` ignoriert und
  liegt dann als einziger Autostart-Weg nur auf dieser Platte. Beim Anlegen oder
  Versionieren eines Start-/Hilfsskripts die Geschwisterdateien mitpruefen
  (`git check-ignore -v --no-index <pfad>` je Datei) und einzeln freigeben — eine
  Freigabezeile mit dem Grund daneben, nicht ein pauschales `!*.vbs`.
  **Dieselbe Falle im Fremd-Klon, eine Ebene tiefer:** eine Hausdatei, die im
  Repo-Ordner unter `Werkstatt/<repo>` entsteht (eigenes Werkzeug, eigene
  To-do-Notiz), ist dort `??` - der Klon hat ein EIGENES Repo, also schuetzt die
  BrainFiles-`.gitignore` sie nicht und die Sicherung nimmt sie nicht mit. Vor dem
  Melden „fertig" je selbstgebauter Datei `git -C <klon> status --porcelain --
  <datei>` fragen und den ungetrackten Stand nennen (der Klon ist shallow: vor
  einem Push `git fetch --unshallow <upstream>`).

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

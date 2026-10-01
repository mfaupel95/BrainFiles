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
   **Die Pruefung muss den Commit ABBRECHEN koennen.** `git diff --cached --numstat`
   nur DRUCKEN und im selben Aufruf danach weitercommitten ist keine Pruefung: die
   Ausgabe laeuft durch, der Commit geht durch, und die fremden Zeilen fallen erst
   auf, wenn jemand `git show --stat` liest. Entweder die Pruefung als TOR bauen, das
   die Kette beendet (Anzahl bzw. Pfadliste im selben Aufruf gegen die Absicht
   vergleichen und bei Abweichung mit Exitcode ungleich 0 abbrechen), oder - wenn
   schon FREMDE Eintraege im Index stehen - die pfadbeschraenkte Form nehmen
   (`git commit -m "..." -- <eigene pfade>`, siehe Regel 3): sie committet den
   Arbeitsbaum genau dieser Pfade und laesst die fremde Vormerkung liegen. Ein
   Ein `git add -- <eigene> && git commit` ohne dieses Tor ist genau der Fehler.
      Als Einzeiler, der wirklich abbrechen kann (die erwartete Zahl VORHER aus der
      eigenen Pfadliste zaehlen):
      `git add -- <eigene pfade> && { n=$(git diff --cached --name-only | wc -l); [ "$n" -eq <erwartet> ] || { echo "ABBRUCH: $n Pfade im Index"; exit 1; }; }`
      Wird die Zahl nur gedruckt und im naechsten Werkzeugaufruf committet, ist
      nichts geprueft: die Ausgabe laeuft durch und die fremden Pfade fallen erst
      in `git show --stat` auf.
   **Diese Pruefung ist eine Momentaufnahme.** Die Routine
   `fremdarbeit-einziehen.ps1` laeuft zu festen Zeiten und baut dabei eigene
   Indizes um; kurz danach trug der geteilte Index einen fremden
   **Loesch**-Eintrag, den diese Sitzung nie angefasst hatte, und er ging mit dem
   eigenen Commit mit. Deshalb Index-Pruefung (`git diff --cached --name-only`)
   und `git commit` in EINER Ausfuehrung verketten (`&&`), nie in zwei
   Werkzeugaufrufen - und nach dem Commit `git show --stat HEAD` JE DATEI lesen:
   eine fremde Zeile mit Loeschungen ohne Einfuegungen heisst, dort ist ein
   fremder Zwischenstand mitgegangen (Regel 3 nennt den Rueckweg: Folge-Commit mit
   dem Arbeitsbaum-Stand, keine Historie umschreiben).
3. **Gemischte Datei = nur die eigene Aenderung in den Index, nicht die Datei opfern
   und nicht die Fremdarbeit mitnehmen.** Zuerst `git diff --numstat -- <datei>` lesen:
   mehrere Hunks unterschiedlicher Groesse heissen "hier steckt fremde Arbeit drin".
   **Derselbe Blick gehoert VOR das Schreiben, nicht nur vor den Commit:** traegt die
   Zieldatei schon FREMDE uncommittete Aenderungen, die groesser sind als die eigene
   (gemessen: 28 fremde Zeilen gegen 3 eigene in einer `SKILL.md`), gehoert die eigene
   Zeile NICHT hinein - sie wandert in eine Datei, die der eigenen Arbeit gehoert
   (die passende `references/`-Datei, ein eigener Abschnitt), und der Grund steht im
   Bericht. So wird weder fremde Arbeit mitgenommen noch die eigene spaeter
   ueberschrieben; ein Schreibwerkzeug, das "modified since you last read" meldet, ist
   genau dieser Fall und kein Fehler.
   Dann den Index DETERMINISTISCH bauen statt Hunk-Antworten zu raten:
   `git show HEAD:<datei>`, die eigene Aenderung byte-genau im Speicher einsetzen,
   `git hash-object -w --path=<datei> --stdin`, danach
   `git update-index --cacheinfo 100644,<sha>,<datei>`. **Der Anker fuer das
   Einsetzen muss aus `git show HEAD:<datei>` kommen, nicht aus dem
   Arbeitsbaum:** eine Zeile, die man dort gerade sieht, kann selbst zur
   fremden Aenderung gehoeren - dann findet der Anker in HEAD nichts
   (`0 mal`) und der eigene Block wird nie eingefuegt. Vor dem Schreiben
   `assert head.count(anker) == 1` und beim Anker NICHT auf den Text aus dem
   Arbeitsbaum zurueckgreifen. Der Arbeitsbaum bleibt
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
   **Vor dem Bau des Fremd-Blobs den Index ZUERST LEEREN (`git reset`, ohne Pfade).**
   Sind die eigenen Dateien schon gestagt, nimmt der Fremd-Commit sie mit: der ganze
   eigene Stapel landete in einem Commit mit dem Autor `Andere Sitzung <fremd@local>` -
   inhaltlich richtig, aber falsch beschriftet und von der eigenen Arbeit nicht mehr zu
   trennen. Reihenfolge: `git reset` -> Fremd-Blob
   (`git hash-object -w --path=… --stdin` + `git update-index --cacheinfo …`) ->
   `git diff --cached --name-only` muss GENAU den fremden Pfad nennen (nicht mehr!) ->
   Commit mit Fremd-Autor -> erst danach die eigene Pfadliste stagen und committen.
   Ist es doch passiert: `git reset --soft HEAD~1`, dann `git reset` (Index leeren),
   Fremd-Teil neu bauen und committen, danach den eigenen.
   **Sind stattdessen FREMDE Eintraege vorgemerkt** (erste Spalte `M `/`A ` in
   `git status --porcelain`) und die eigenen Dateien seit dem Schreiben unveraendert, ist
   der pfadbeschraenkte Commit das RICHTIGE Werkzeug, kein Notbehelf:
   `git add -- <eigene pfade>` und `git commit -m "..." -- <eigene pfade>` committen den
   Arbeitsbaum genau dieser Pfade; die fremde Vormerkung bleibt liegen (nachgemessen: sie
   stand danach unveraendert weiter im Index). Hier ist `git reset` (Index leeren) die
   falsche Antwort — es fasst die Vormerkung einer anderen Sitzung an. Das Verbot gilt
   ausschliesslich dem eigenen, per `hash-object` GEBauten Index-Eintrag (siehe unten).
   **Der so gebaute Index wirkt nur bei `git commit` OHNE Pfadangabe.**
   `git commit -- <pfad>` committet den ARBEITSBAUM dieser Pfade (wie `git add <pfad>`
   plus Commit) und wirft den eigenen Index-Eintrag weg: die fremden Zeilen gehen mit
   hinein, obwohl `git diff --cached` unmittelbar vorher nur die eigenen zeigte. Also
   erst `git update-index --cacheinfo …`, dann `git diff --cached --name-only` lesen,
   dann `git commit` ohne Pfade. Ist es doch passiert: `git reset --soft HEAD~1`, Index
   deterministisch neu bauen, ohne Pfadangabe erneut committen — und `git show --stat`
   gegen die Absicht halten (je Datei 2/1, nicht 39 Zeilen). `git commit -- <pfad>`
   `git commit -- <pfad>` ist auch dann kein Ersatz, wenn nur EINE Datei betroffen ist.
      **Den `--stat` nach dem Commit VOLLSTAENDIG lesen, nicht abschneiden** — die
      Einfuegungs- UND Loeschungszahlen JE DATEI sind das Signal: eine fremde Datei
      mit `65 --------` und ohne `+` heisst, dort ist etwas VERSCHWUNDEN (ein
      Zwischenstand), nicht nur geaendert. Wer die Ausgabe kuerzt, schneidet genau
      diese Zeile weg und der gemischte Commit faellt nicht auf.
      **Ist es doch passiert, weil der Fremdteil ein ZWISCHENSTAND war** (der Autor
      hat ihn im Arbeitsbaum inzwischen zurueckgenommen), NICHT die Historie
      umschreiben: einen normalen Folge-Commit mit dem Arbeitsbaum-Stand dieses Pfades
      setzen und im Text sagen, dass ein fremder Zwischenstand versehentlich mitging
      und hier in Deckung gebracht wird. Vorher belegen, dass es wirklich die Umkehr
      ist: `git diff HEAD~1 -- <pfad>` und `git diff HEAD -- <pfad>` muessen exakt
      gegeneinander laufen und `git show HEAD~1:<pfad>` byte-gleich zum Arbeitsbaum
      sein. Danach `git diff HEAD -- <pfad>` leer und `git show --stat HEAD` lesen.
      Nur wenn der Fremdteil noch im Arbeitsbaum steht, ist `reset --soft` richtig.
   `git add -p` bleibt der Notweg fuer zwei klar getrennte kleine Hunks; dort die
   Antwortfolge nicht raten, sondern `git diff --cached -- <datei>` nachlesen und bei
   Abweichung mit `git restore --staged <datei>` neu beginnen — die Zahl der Hunks ist
   vorher nicht sicher bekannt.
   **Fuer eine GEMEINSAME Registerdatei** (z. B. `TASKS.md`, in die jede Sitzung oben
   eintraegt) ist der kuerzere Weg gleichwertig: aus `git show HEAD:<datei>` eine Fassung
   "HEAD + eigener Block" bauen, schreiben, `git add -- <datei>`, dann den vollstaendigen
   Arbeitsbaum-Text wiederherstellen — der Index traegt nur den eigenen Block, die
   Fremdarbeit steht weiterhin als `M` im Baum. Nur anwenden, wenn in dem Moment keine
   andere Sitzung in diese Datei schreibt, und danach `git diff --numstat -- <datei>`
   gegenpruefen: Arbeitsbaum gegen Index zeigt die fremden Zeilen, Index gegen HEAD nur
   die eigenen. **Den eigenen Block danach IM ERGEBNIS nachweisen, nicht nur den
   Schreibvorgang.** Drei Zahlen lesen: `grep -c '<eigene Kennung>' <datei>` (der
   Eintrag ist auffindbar), die Zahl der gleichnamigen Abschnitte (eine Registerdatei
   kann MEHRERE `## Offen` tragen — ein Einfuegen ohne Positionsangabe landet im
   falschen) und `git diff --numstat` (reine Einfuegungen). Ein nicht angewandtes
   Format — `'%s'` steht woertlich im Eintrag, weil die ID nie eingesetzt wurde — sieht
   wie Erfolg aus, der Diff zeigt Einfuegungen, und der Eintrag ist trotzdem nicht da;
   erst der `grep` findet es.
   **Den eigenen Block VOR dem Trennen in eine eigene Datei schreiben** (`cache/scratch/
   mein_block.txt`) und beim Wiederherstellen AUS DIESER Datei einsetzen — nicht aus einem
   Skript, das den Block im selben Lauf erst entfernt und dann neu berechnet: ist der
   Block im Speicher schon geloescht, trifft der zweite Schritt nichts mehr, und die
   eigene Arbeit ist still weg (Arbeitsbaum UND Commit). Reihenfolge deshalb streng:
   Block herauslesen -> ablegen -> Fremd-Commit -> Block aus der ABLAGE einsetzen ->
   zaehlen. Nach dem Einsetzen `grep -c '<eigene Kennung>' <datei>` gegen die Zahl der
   abgelegten Eintraege UND die Zeilenenden binaer zaehlen (`CRLF` vs. `LF-only`), sonst
   faellt der stille Verlust erst auf, wenn jemand die Eintraege vermisst.
   **Zeilenende erst auf BYTES umsetzen, dann schreiben:**
   `text.encode("utf-8").replace(b"\n", nl)` — die umgekehrte Reihenfolge
   (`text.replace("\n", nl).encode()`) bricht mit `TypeError: replace() argument 2 must be
   str`, sobald `nl` ein `bytes` ist, und schreibt die Datei nicht.
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
   zweiten Mal committen (ein zweiter Commit derselben Zeile ist ein leerer
   Diff und verwirrt mehr, als er klaert). **Auch eine UNGESTAGTE eigene Aenderung
   kann so verschwinden:** eine Fremdsitzung stagt eine GEMEINSAME Registerdatei
   (`TASKS.md`, `INDEX.md`, `Dashboard.md`) als GANZE Datei und committet sie -
   die eigene, eben erst geschriebene Zeile faehrt darin mit. Erkennbar an
   `git status --porcelain -- <datei>` (leer) bei gleichzeitig fehlendem
   `git diff -- <datei>`; der Inhalt ist NICHT weg, sondern in einem fremden
   Commit mit fremder Beschriftung. Nicht neu schreiben (der zweite Commit
   derselben Zeile ist ein leerer Diff): `git show HEAD:<datei> | grep -n
   '<eigene Kennung>'` als Beleg lesen, das im Bericht als "in fremdem Commit
   mitgegangen" benennen — und in so einer Registerdatei die eigene Aenderung
   ZUERST und in EINER Ausfuehrung mit `git add` + `git commit` erledigen, statt
   sie zwischen zwei Rechercheschritten liegen zu lassen.
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
 harmlos, echte Werte nicht. **Auch eine VORLAGENDATEI kann echte Kennungen tragen:
   `.env` ist ignoriert, `.env.example`/`.env.template` sind VERSIONIERT.** Gemessen:
   in der getrackten `.env.example` eines Fremd-Klons standen echte Werte
   (`ANTHROPIC_API_KEY`, `TELEGRAM_BOT_TOKEN`) — ein `git add -A` in diesem Klon und
   ein Push haetten beide in den Fork veroeffentlicht; der Klon-Kopf war noch sauber,
   die Aenderung lag nur im Arbeitsbaum. **Bevor daraus ein Alarm wird, den HEAD-Stand
   lesen — ein echter Wert im Arbeitsbaum ist noch keine Veroeffentlichung.**
   `git -C <klon> show HEAD:<datei>` entscheidet, ob er je committet wurde: gemessen
   standen in zwei getrackten Vorlagen echte Werte, waehrend der HEAD-Stand LEERE Werte
   trug — nichts war geleakt, die richtige Antwort ist dann `git checkout -- <datei>`
   (zurueck auf den HEAD-Stand) und NICHT ein selbst erfundener Platzhalter. Die
   Rotation der Kennungen bleibt ein eigener Task fuer den Nutzer, kein Nebenschritt.
   **Beim Suchen und Berichten nur PFAD, Schluesselname und Wertlaenge ausgeben, nie den
   Wert** (`read_bytes`, `len()` zaehlen, Hash kuerzen) — ein Diff im Sitzungsprotokoll
   ist derselbe Leak wie ein Commit. `Wissen/Zugaenge.md` bleibt dabei ausgenommen
   (Stufe 0). Wer einen Fremd-Klon mit `git add -A`
   sichern will, macht zuerst `git status --porcelain | grep -i env` und liest jede
   getrackte Vorlage: echte Werte NICHT committen, den Zustand liegen lassen und als
   eigenen Task melden (Kennungen neu ausstellen, Werte auf Platzhalter). **Ist der Baum eines FREMDEN Klons vollstaendig fremd (kein eigener Pfad darin), ist `git add -A` DORT vertretbar** — aber erst nach dem env-Blick oben UND nach LESEN der Liste: nimmt es eine eigene Datei oder eine `.env`/Schluesseldatei mit, gilt Regel 1 (namentlich stagen). Regel 1 schuetzt BrainFiles' Mehrsitzungs-Baum, nicht den Klon eines Fremd-Repos. **Und beim
   Berichten die Werte maskieren** (`sed -E 's/=(.{0,4}).*/=\1…/'`) — ein Diff im
   Sitzungsprotokoll ist derselbe Leak wie ein Commit; (b) je `SKILL.md` das Frontmatter pruefen (beginnt mit
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

**`--allow-empty` heisst NICHT „nichts im Index".** Ein Commit, der nur eine
Meldung nachtragen soll (Korrektur, Praezisierung, leerer Marker), committet
trotzdem JEDEN vorgemerkten Eintrag - auch die fremde Vormerkung einer anderen
Sitzung. Gemessen: ein `git commit --allow-empty -m "Korrektur: ..."` nahm eine
fremde vorgemerkte LOESCHUNG mit (eine ganze, in der `.gitignore` ausdruecklich
freigegebene Datei), die diese Sitzung nie angefasst hatte; sie stand danach
unter der eigenen Meldung in HEAD. Der Index ist bei `--allow-empty` genauso
scharf wie bei jedem anderen Commit. **Deshalb: `git diff --cached --numstat`
LESEN, bevor irgendein Commit laeuft - auch ein leerer.** Fuer einen reinen
Meldungs-Nachtrag den eigenen Index nehmen
(`GIT_INDEX_FILE=<scratch>/idx_x` + `git read-tree HEAD`) oder den Nachtrag
lassen - eine ungenaue Betreffzeile ist billiger als eine fremde Loeschung im
eigenen Commit. Ist es passiert: normaler Folge-Commit, der den Inhalt aus
`git show <letzter-guter-commit>:<pfad>` wieder aufnimmt, keine Historie
umschreiben.

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

**Die Routine kann eine Reparatur ZURUECKNEHMEN, nicht nur einsammeln.** Sie prueft
das Alter, nicht den Inhalt: eine Datei, die im Arbeitsbaum nur noch ALT steht (weil
eine parallele Sitzung sie geaendert und committet hat, waehrend die alte Fassung
liegen blieb), ist fuer sie von einer neuen Aenderung nicht zu unterscheiden - sie
committet die alte Fassung und dreht damit eine gewollte Reparatur still um. Genau so
verschwand der reparierte Gateway-Launcher ueber Nacht, und aufgefallen ist es erst,
als der Dienst nicht mehr ansprang. Gegenmittel in dieser Reihenfolge: (1) **nach einer
Reparatur sofort selbst committen** - unter der 30-Minuten-Schwelle bleiben, sonst
wandert sie in eine fremde Meldung oder wird ueberschrieben; (2) nach einem
`Fremdarbeit uebernommen`-Commit in `git log` pruefen, ob er Dateien anfasst, an denen
in den letzten Stunden bewusst gearbeitet wurde (`git show <commit> --stat` gegen die
eigene Pfadliste halten) - bei einem Rueckschritt den Inhalt sofort wieder herstellen
und im Commit-Text benennen; (3) dauerhaft gehoert in die Routine eine Inhaltspruefung
gegen HEAD, nicht nur eine Zeitpruefung.

**Die Routine kann eine ganze Nacht still ausfallen - „uebersprungen" ist nicht
„erledigt".** Sie endet bei einer liegenden `.git/index.lock` (oder einem anderen
Arbeitszweig) mit Exitcode **0** und der Zeile `ENDE uebersprungen`; die Aufgabenplanung
meldet damit Erfolg, und niemand merkt, dass nichts uebernommen wurde. Genau das war der
Fall: Skip am 23.09. 20:40, danach lagen **44 Dateien bis zu 44 h** im Baum. Das
Weckzeichen ist der Tagesbericht („N uncommittete Datei(en) aelter als 1 h")
- wer die Zeile liest, fuehrt die Routine VON HAND aus, statt auf 20:40 zu warten:
`-Testlauf` lesen, dann ohne Schalter laufen lassen. Reihenfolge ist eine Falle: der
`-Testlauf` wird von DERSELBEN Sperre uebersprungen - erst Sperre pruefen (0 Byte,
kein `git.exe` ohne `fsmonitor` = verwaist, umbenennen), dann beide Laeufe.
Das Log `Agenten/Routinen/logs/fremdarbeit-letzter-lauf.log` wird bei JEDEM Lauf
ueberschrieben: den Skip-Grund sofort lesen, sonst ist er beim naechsten Lauf weg
(Historie nur ueber `git log --author=fremd@local`). Nach dem Lauf ist der Baum NICHT
leer - zurueckgehaltene frische Dateien und fremd vorgemerkte Eintraege (`A `) bleiben
absichtlich stehen; sauber ist der Lauf, wenn die EIGENEN uebernommenen Pfade aus
`git status` verschwunden sind.

**Der stille Ausfall ist seit 24.09.2026 bewacht:** `Agenten/Hermes/scripts/sperren-wache.py`
(Test `test_sperren_wache.py`, 23 Tests; Cron `sperren-wache` `da82ced995e1`, alle 60 min,
`no_agent`, Telegram). Sie prueft in EINEM Lauf die Sperre (`.git/index.lock` aelter als
10 min in `BrainFiles` und `Agenten/Handel/nautilus`), die Skip-Zeile des Fremdarbeit-Logs
und den ZUWACHS der weggeraeumten Sperren. Leere Ausgabe = nichts senden. Sie raeumt
NICHTS weg - eine Sperre umzubenennen bleibt eine Entscheidung mit Kontext. Bauart,
Merkdatei und Fallen: `references/fremdarbeit-routine.md`.

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
   - **Laeuft die Sitzung noch, ist es KEINE Alles-oder-nichts-Frage: nimm den ruhenden
     Teil.** Aktivitaet MESSEN, nicht schaetzen: `git log -3 --format='%h %ci %s'`
     (HEAD-Commit vor wenigen Minuten = sie committet gerade selbst) und je offenem
     Pfad das Alter in Minuten in EINEM Lauf —
     `scripts/offene-pfade-alter.ps1` gibt genau das aus (sortiert, und fuer ` D`-Eintraege
     die Zeit des ELTERNORDNERS, weil eine geloeschte Datei keine mtime hat).
     Alles ueber ~30 min unberuehrt gilt als ruhend; nur diese Pfade stagen und den Rest
     im Bericht nennen („13 Pfade, juengste 2 Minuten, ihre eigenen Commits laufen").
     Ein Teil-Commit ist besser als keiner — was liegen bleibt, holt die Routine.
   - **Vor dem Fremd-Commit die uebernommenen Dateien PRUEFEN, nicht nur stagen:**
     `ast.parse` ueber jede `.py` und die BETROFFENEN Testmodule wirklich laufen lassen
     (`python -m unittest test_x` aus ihrem Verzeichnis), die Testzahl in den Commit-Text.
     Gruene Fremdarbeit darf als ruhend gelten, rote wird wie ein eigener Fehler
     behandelt (Regel 6) — nicht "nur liegen gelassen".
   - **Der Teil-Commit braucht die volle Zeremonie aus Regel 3:** `git reset` (Index
     leeren), `git add -- <pfade>` namentlich, `git diff --cached --name-only` muss GENAU
     diese Pfade nennen, dann `git commit` OHNE Pfadangabe mit
     `--author="Andere Sitzung <fremd@local>"` (Herkunft und Inhalt im Text), danach
     `git show --stat HEAD` gegen die Index-Zahlen halten. Der eigene Rest (z. B. ein
     TASKS.md-Eintrag) wird ein ZWEITER Commit mit eigenem Autor — nie derselbe.

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
  Die leichteste Form ist ein ALTERNATIVER Index mit einem NORMALEN Commit:
  `GIT_INDEX_FILE=<scratch>/idx_<thema>` -> `git read-tree HEAD` -> `git add -- <eigene pfade>`
  -> `git diff --cached --numstat` lesen (nur eigene Pfade) -> `git commit -F <meldung>`.
  `read-tree` ist Pflicht, sonst startet der Index leer und ignorierte Freigaben
  fehlen. Danach `unset GIT_INDEX_FILE` UND dieselben Pfade im ECHTEN Index
  nachziehen (`git add -- <eigene pfade>`), sonst vergleicht der echte Index gegen
  den neuen HEAD und meldet eine NEUE Datei als `D ` plus `??` und eine geaenderte
  als `M ` mit dem ALTEN Inhalt - die Fremdarbeit-Routine committet sie dann ein
  zweites Mal als fremd. Randfaelle des Handgriffs (nativer `C:/…`-Pfad fuer
  `GIT_INDEX_FILE`, eigene Indexdatei danach loeschen, fremde Vormerkung nicht
  wegnehmen): `references/fremdarbeit-routine.md`. Eine
  Datei, die eine andere Sitzung NACH dem eigenen Commit weiterbearbeitet hat,
  nicht nachziehen (`git reset -q HEAD -- <pfad>`), sonst liegt ihre laufende
  Arbeit im Index. Gegenprobe: `git status --porcelain` zeigt danach weder `D `
  noch `??` an den eigenen Pfaden. Wer fremde Arbeit committet, ohne den Staging-Bereich anzufassen (`GIT_INDEX_FILE`
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
- **Die Commit-Meldung als Datei braucht einen NATIVEN Pfad.** `git` ist ein
  Windows-Programm: eine Meldungsdatei unter `$TMPDIR` bzw. `/tmp` findet es nicht
  (`fatal: could not read log file '/tmp/commitmsg.txt'`) — der Commit unterbleibt, und
  bei verketteten Aufrufen faellt nur der naechste Schritt auf. Die Datei per
  `write_file` nach `Agenten/Hermes/cache/scratch/commitmsg_<thema>.txt` schreiben und mit
  `git commit -F "C:/Users/<user>/Documents/BrainFiles/Agenten/Hermes/cache/scratch/…"`
  aufrufen. Mehrzeilige `-m "$(cat <<'EOF' …)"`-Heredocs scheitern aus demselben Grund —
  bei jeder Meldung ueber einer Zeile die Datei nehmen.
- **`Set-Content -Encoding UTF8` schreibt ein BOM.** Unter PS 5.1 wandert es als
  unsichtbares Zeichen in die erste Zeile - und bei `git commit-tree -F <datei>`
  direkt in die Betreffzeile des Commits (`git log` zeigt dann ein BOM vor dem
  Betreff). Nachrichtendateien mit `[System.IO.File]::WriteAllText($pfad, $text,
  (New-Object System.Text.UTF8Encoding($false)))` schreiben.
- **`fatal: cannot lock ref 'HEAD': is at <a> but expected <b>` heisst: eine parallele Sitzung hat HEAD bewegt - kein Schaden.** Der eigene Index ist unversehrt (beim Bau ueber `GIT_INDEX_FILE` + `read-tree` liegt der Blob schon in `objects/`). Den Commit einfach wiederholen, vorher `git diff --cached --numstat` lesen und gegen die eigene Absicht zaehlen. **Reihenfolge beachten:** ein direkt danach abgesetztes `git push` schiebt den FREMden Commit hoch, wenn der eigene noch nicht steht - `git log --oneline -1` lesen, statt anzunehmen, es sei der eigene.
- **`fatal: Unable to create '…/.git/index.lock': File exists`** heisst fast immer:
  eine andere Sitzung schreibt GERADE in denselben Index. Die Sperre NICHT loeschen -
  warten (Sekunden) und denselben Befehl wiederholen, dann geht er durch. Ist die
  Sperre 0 Byte gross und liegt sie schon viele Minuten, in einer Schleife pollen
  (`for i in $(seq 1 25); do [ -e .git/index.lock ] || break; sleep 20; done`) statt
  einmal zu warten — ein echter paralleler Commit braucht Sekunden, ein haengender
  Prozess laesst die Sperre stehen. Erst wenn der eigene Befehl ueber ~5 Minuten
  wiederholt daran scheitert, sie per `mv` zur Seite legen
  (`.git/index.lock.verwaist-<zeitstempel>`, nie loeschen — der Schritt muss umkehrbar
  bleiben) und im Bericht sagen, dass eine parallele Sitzung aktiv war. **Das
  Alter der Sperre ist ein schwaches Zeichen:** eine frische, 0 Byte grosse Sperre
  ist genauso verwaist wie eine alte — eine Sitzung kann zwischen Staging und
  Commit abgebrochen sein, waehrend eine andere gerade fertig committet hat (dann
  ist die Sperre Minuten jung und trotzdem tot). Entscheidend ist die ART der
  Prozesse, nicht die Uhr: keine `git.exe` ohne `fsmonitor` in der Kommandozeile =
  umbenennen und SOFORT denselben Befehl wiederholen; die Wartezeit ist nur fuer
  den unklaren Fall. Gegenprobe nach dem Umbenennen: `Test-Path` auf Quell- UND
  Zielpfad, dann den Commit wiederholen und `git log -1` lesen — erst der
  durchgelaufene Commit beweist, dass die Sperre wirklich weg war. **Unter
  Windows mit `Move-Item -LiteralPath <quell> -Destination <ziel> -Force` umbenennen (der
    Schalter ist der Unterschied), alternativ `[System.IO.File]::Move($quell, $ziel)` mit **ZWEI**
    Argumenten:** die Sperre ist eine VERSTECKTE Datei — ein `Move-Item` OHNE `-Force` tat daran still
    NICHTS (keine Fehlermeldung, die Sperre stand danach unveraendert mit altem
    Zeitstempel da, waehrend die Ausgabe wie Erfolg aussah). Danach mit `Test-Path`
    auf BEIDE Pfade nachsehen - sonst arbeitet man weiter gegen eine Sperre, die man
    fuer weg haelt. **Die Ueberladung mit DREI Argumenten gibt es in Windows
 PowerShell 5.1 nicht:** `[System.IO.File]::Move($quell, $ziel, $true)` bricht mit
 „Es kann keine Ueberladung gefunden werden: 3" ab und die Sperre bleibt liegen —
 der Zielname muss also selbst frei sein (Zeitstempel im Namen), sonst die
 Zwei-Argument-Fassung nehmen. **Hat der echte Committer die Sperre nur
 HINTERLASSEN statt sie zu entfernen** (kein echter `git.exe` mehr, Sperre 0 Byte
 und Minuten alt), ist sie verwaist: umbenennen und denselben Befehl sofort
 wiederholen. Die Abbruchregel gilt nur, SOLANGE ein echter Committer lebt — erst pruefen, dann warten, dann umbenennen ist die Reihenfolge (gemessen: nach dem
 Warten auf einen fremden Commit stand die 0-Byte-Sperre noch da und der eigene
 Commit lief erst nach dem Umbenennen durch).
 **Prozesse ansehen,
 nicht nur die Uhr:** `git fsmonitor--daemon` laeuft dauerhaft und ist KEIN Commit —
 eine `git.exe`-Liste voller fsmonitor-Zeilen beweist keine parallele Sitzung.
 **Und die Liste muss erst beweisen, dass sie ueberhaupt laeuft:**
 `tasklist //FI "IMAGENAME eq git.exe"` scheitert unter MSYS mit
 „Argument/Option ungueltig - `//FI`" und gibt dabei eine LEERE Liste aus - man
 liest „kein git.exe", haelt eine lebende Sperre fuer verwaist und raeumt sie weg.
 Richtig ist `MSYS_NO_PATHCONV=1 tasklist /FI "IMAGENAME eq git.exe" /FO CSV`,
 und die Gegenprobe auf einen Prozess, den es SICHER gibt (`bash.exe`), gehoert
 zu jedem solchen Nachweis: erst wenn die Sonde dort Treffer zeigt, ist ein
 leeres Ergebnis eine Aussage. `wmic` gibt es auf Windows 11 26200 nicht mehr
 („command not found") - die Kommandozeile kommt aus
 `Get-CimInstance Win32_Process -Filter "name='git.exe'"`, und die schreibt man
 als `.ps1` nach `Agenten/Hermes/cache/scratch/` und startet sie mit
 `powershell -NoProfile -ExecutionPolicy Bypass -File <datei>`; verschachtelte
 Anfuehrungszeichen in einer bash-`-Command`-Zeile gehen sonst kaputt. Ein
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
 Weg und kein Risiko. **Der Filter „nicht fsmonitor" ist aber zu GROB:** er trifft
 auch git-Aufrufe, die NIE committen — `git worktree list --porcelain` aus dem
 Editor/Projekt-Werkzeug, `rev-parse` aus einer Anzeige. Zwei solche Prozesse
 (Startzeit identisch) sahen wie ein laufender Committer aus, waehrend die
 0-Byte-Sperre 7 Minuten alt war und niemand sie hielt. Entscheidend ist die
 UNTERKommandozeile: nur `add`/`commit`/`merge`/`rebase`/`push`/`cherry-pick`
 sind Verdaechtige — besteht die gefilterte Liste nur aus lesenden Aufrufen,
 ist die Sperre verwaist. Wer nur die Zahl zaehlt, wartet endlos auf einen
 Prozess, der nichts schreibt.
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
- **Fortlaufende Nummern (`T-0NN`) werden von mehreren Sitzungen gleichzeitig vergeben.**
  „hoechste + 1" stammt aus einer Datei, die parallel fortgeschrieben wird — zweimal am
  selben Abend entstanden zwei inhaltlich verschiedene Eintraege mit derselben Nummer.
  Die hoechste Nummer FRISCH lesen, nach dem Schreiben die eigenen gegenpruefen
  (`grep -c '\*\*T-0NN' <datei>` muss je eigener ID `1` sein); bei einer Kollision NUR die
  eigenen Eintraege umnummerieren (am eigenen TITEL erkennbar, nie am Zeitstempel) und die
  fremden unberuehrt lassen. Gegenprobe nach dem Schreiben: `git diff --numstat` zeigt
  reine Einfuegungen, die Umnummerierung nur die eigene Zeile.
- **Beim Einfuegen in JSON/YAML nach dem Schreiben parsen lassen, und die Kommas mitdenken.**
  Eine eingefuegte Zeile, deren Wert ein doppeltes Anfuehrungszeichen enthaelt, zerbricht die
  Datei (`Expecting ',' delimiter` an der Folgezeile) — im Textwert einfache Anfuehrungszeichen
  verwenden oder escapen. Und: eine neue Zeile hinter `"schluessel": false,` braucht genau
  dann ein abschliessendes Komma, wenn die Ankerzeile eins hatte; fehlt es, ist das Objekt
  ungueltig, steht aber optisch richtig da. Nach jedem Einfuegen `json.loads`/`yaml.safe_load`
  **auf den Text IM SPEICHER, und zwar VOR dem Schreiben** (`json.loads(neu)`, dann
  erst `open(pfad,'wb').write(neu.encode())`) — nicht erst auf der geschriebenen Datei.
  Eine kaputte Datei ist teuer: liegt der Pfad unter einem verschachtelten eigenen Repo
  oder ist er ignoriert, gibt es kein `git show HEAD:` als Rueckweg, und
  `git checkout -- <datei>` holt nur den letzten Commit-Stand (ohne die eigene Aenderung).
  Ist die Datei unversioniert, vorher eine byte-genaue Kopie daneben legen. Die drei
  Zielwerte danach asserten. Zwei Anker-Fallen derselben Arbeit: **`rfind('}')` als
  Einfuegepunkt trifft ein `}` INNERHALB eines Notiz-Strings** — dann sauber parsen, den
  Schluessel ergaenzen und mit `json.dumps(..., indent=2, ensure_ascii=False)` schreiben
  (Gegenprobe: `git diff --numstat` bleibt klein, z. B. 4/3; Zeilenende vorher aus dem
  Original ableiten); und **der Anker muss die Schreibweise des WERTS treffen** —
  `'"ETH_USDT": 12'` findet kein `12.0` und umgekehrt, also vor dem Ersetzen
  `count(anker) == 1` asserten und `repr()` gegen die Stelle halten.
  **Eine schreibende Funktion nie als "Probe" gegen das ECHTE Ziel laufen lassen:** ein
  Testaufruf am echten Buch schreibt Journalzeilen, auch wenn er nur pruefen sollte — Probe
  gegen eine Kopie, sonst muss der Zustand von Hand nachgezogen werden.
- **Reparaturcode nie durch einen Shell-Heredoc schicken.** Ein Heredoc
  (`python - <<'PY' … ersatz = "…\n…" …`) zerlegt die Escapes im Ersatztext: ein
  `\n` in einem Stringliteral landet als ECHTER Zeilenumbruch in der Zieldatei —
  die Datei kompiliert danach nicht mehr (`SyntaxError: unterminated string
  literal` in einer Zeile, die richtig aussieht) und sie ist schon
  ueberschrieben. Den Helfer per `write_file` als DATEI nach
  `Agenten/Hermes/cache/scratch/` schreiben (Inhalt kommt unveraendert an) und
  mit `python <datei>` starten; die Stelle ueber ZEILENINDIZES ersetzen, nicht
  ueber einen Suchtext — ein mehrfach vorkommender Anker (`print(…)`, `)))`)
  trifft die fruehere Fundstelle, der Ersatz landet am falschen Ort und der
  eigentliche Schaden bleibt stehen (mehrere Anlaeufe lang unbemerkt). Fuer den
  Rueckweg `git show HEAD:<pfad>` bereithalten (bei ungetrackten Pfaden gibt es
  ihn nicht — dann vorher byte-genau kopieren). Nach jeder Textaenderung einen
  Syntax-Sweep ueber die angefassten `.py` fahren: `ast.parse` je Datei (nicht
  `py_compile.compile(doraise=True)` — das wirft `PyCompileError`, nicht
  `SyntaxError`, und der `except SyntaxError` faengt nichts), inklusive
  `Agenten/Hermes/scripts/`: ein Skript, das nicht kompiliert, nimmt seinen
  Cron-Job mit, und das faellt nur an `last_status: failed` in `cron/jobs.json`
  auf — nie in einer Meldung.
  **Denselben Helfer NIE als `python -c "…"` in die Shell legen:** Backticks im Text
  (Markdown-`code`-Marken) liest die bash als Kommando-Substitution — die Zielzeile landete
  danach in Einzelzeichen zerlegt in der Datei. Text mit Backticks ausschliesslich per
  `write_file` als Datei schreiben und mit `python <datei>` starten.
  **Und den Schreibaufruf nie mit einem rechenbaren Argument bauen:**
  `open(pfad, "wb").write(neu_bauen())` wertet `open()` ZUERST aus — die Zieldatei ist in
  diesem Moment schon leer — und stirbt erst an der Argument-Auswertung. Gemessen: eine
  versionierte Wiki-Datei lag danach mit 0 Byte Inhalt da (Rueckweg nur ueber
  `git show HEAD:<pfad>`). Erst rechnen, Ergebnis `assert`en, dann in zwei Schritten
  `open(pfad, "wb").write(bytes)`.
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

- **Die Uhr im Terminal-Container laeuft hinter dem Rechner her — eine mtime aus dem
  Terminal-Werkzeug beweist kein „ruht".** `date` im Terminal liefert die Zeit des
  Docker-Backends, nicht die des Hosts (gemessen: 7,5 h Rueckstand nach Ruhezustand,
  Terminal 17:06 gegen Host 00:46). Folge: jede eben erst geschriebene Datei traegt
  einen Stunden alten Zeitstempel, gilt sofort als ruhend (>30 min) und wird von
  `fremdarbeit-einziehen.ps1` als `Andere Sitzung <fremd@local>` committet — die
  eigene, gerade fertige Arbeit steht dann in einem Fremd-Commit, obwohl kein
  Mensch sie angefasst hat. Wer das sieht, sucht NICHT die fremde Sitzung: erst die
  Host-Zeit holen (windows-mcp `Get-Date`, oder `git log -1 --format=%ci`) und den
  Rueckstand benennen, statt eine Sibling-Sitzung zu vermuten. Gilt auch fuer den
  Rueckstands-Bericht: jede mtime aus dem Terminal-Werkzeug gegen die Host-Uhr lesen.
- **Eine von einer Fremdsitzung GELOESCHTE getrackte Datei ist kein Verlust - ihr
  Rueckweg ist aber eng.** Zeigt `git status --porcelain` ein ` D <pfad>` an einer
  Datei, die niemand bewusst entfernen wollte (eigene Testdatei, eigene Werkzeugdatei),
  holt `git checkout HEAD -- <pfad>` sie zurueck: verworfen wird nur die LOESCHUNG, der
  Inhalt kommt aus dem letzten Commit. Vorher pruefen, ob die Datei uncommittete Arbeit
  trug (`git diff --numstat -- <pfad>` vor der Loeschung ist weg - also aus dem
  Sitzungsverlauf oder der letzten Sicherung belegen): trug sie welche, wird NICHT
  wiederhergestellt, sondern im Bericht als moeglicher Verlust benannt. Eine Loeschung
  in einem verschachtelten eigenen Repo (`nautilus/`) holt `git -C <unterrepo>
  checkout -- <pfad>`, nicht der BrainFiles-Aufruf.
- **Ein `D` in der EIGENEN Pfadliste wandert in den eigenen Commit.** `git add <pfad>`
  stagt auch eine LOESCHUNG: fehlt die Datei auf der Platte, nimmt der Commit sie mit,
  und `git show --stat HEAD` zeigt sie als `125 ----------` — die eigene Aenderung an
  derselben Datei ist dann mit weg, ohne dass irgendetwas fehlschlaegt. Deshalb VOR
  jedem Commit `git status --porcelain -- <pfade>` **LESEN**, nicht nur abschicken, und
  jedes `D` oder `M` an einer Datei, die man nicht angefasst hat, als Befund behandeln:
  erst `git checkout <letzter-guter-commit> -- <pfad>`, Inhalt zurueckholen, dann
  committen. Beleg nach dem Commit: `git cat-file -e HEAD:<pfad>` (Exit 0 = liegt in
  HEAD) — `git show --stat` nennt nur Zahlen und sieht bei einem Loesch-Commit wie ein
  normaler Commit aus. Die URSACHE einer solchen Loeschung darf offen bleiben (kein
  Defender-Fund, kein Cron, kein `reset`/`clean` im Reflog gemessen): die Regel haengt
  nicht daran, sondern an der Pflichtlektuere vor dem Commit.
- **`git status` luegt unter `Werkstatt/`.** Bei laufendem `core.fsmonitor` (BrainFiles hatte ihn an) meldet git fuer Pfade unter der Junction `Werkstatt` -> `O:\Werkstatt` „nichts geaendert“, obwohl die Datei neu geschrieben ist: `git diff` bleibt leer, `git add <pfad>` ist still wirkungslos, `git hash-object <pfad>` zeigt dagegen den neuen Inhalt. Wer dem `git status` dort glaubt, committet nichts und merkt es erst beim naechsten Mal. Gegenprobe: `git rev-parse :<pfad>` gegen `git hash-object <pfad>` halten. Fix: `git -c core.fsmonitor=false add <pfad>` - oder fsmonitor im Repo ganz aus, seit 21.09.2026 gesetzt (`git config core.fsmonitor false`). Trifft jeden Pfad unterhalb einer Junction, auch `Modelle`.
- **Eine Sicherung mit EIGENEM Index muss vom committeten Baum starten, sonst ist sie keine Kopie.** Wer fuer einen Sicherungszweig (`zwischenstand`) einen frischen Index baut (`GIT_INDEX_FILE` auf eine neue Datei, dann `git add -A`) und daraus `git commit-tree` faehrt, verliert JEDEN Pfad, den `.gitignore` verdeckt - auch wenn er in `HEAD` liegt. Ein frischer Index kennt den versionierten Bestand nicht, und `git add -A` nimmt ignorierte Pfade nie auf; die Freigabezeile (`!Agenten/Hermes/config.yaml`) hilft nicht, weil die spaetere Sperrregel sie ueberstimmt (`git check-ignore -v --no-index <pfad>` nennt die greifende Zeile). Gemessen: der Zweig trug 1591 Dateien gegen 1929 in `master` (338 fehlten, 337 davon ignoriert), waehrend der Lauf `ENDE ok` meldete - eine Wiederherstellung aus diesem Zweig waere unvollstaendig gewesen. Fix ist EINE Zeile VOR dem `add`: `git read-tree HEAD` (Index startet vom committeten Baum, `add -A` ergaenzt nur noch Neues), mit `$LASTEXITCODE`-Pruefung wie bei jedem git-Aufruf in einer Routine. **Die Gegenprobe gehoert in dieselbe Meldung wie das `ok`** - beide Zahlen, nicht optional: `git ls-tree -r <zweig> --name-only | wc -l` muss dem Umfang von `master` entsprechen, `git diff --name-status master <zweig> | grep -c '^D'` muss 0 sein (jede `D`-Zeile ist eine Datei, die der Zweig NICHT hat - das ist die Fruehwarnung, die ein reiner Dateizaehler verbirgt). **Warum das lange unsichtbar bleibt:** die naheliegende Sonde greift nicht. `git check-ignore -v <pfad>` meldet fuer einen Pfad im ECHTEN Index nichts; nur `git check-ignore -v --no-index <pfad>` zeigt die Regel (siehe Abschnitt "Datei soll aus dem Verlauf verschwinden"). Ohne `--no-index` liest man "nicht ignoriert" und sucht die Ursache an der falschen Stelle.

## Verification

- `git diff --cached -- <datei>` nennt genau die eigene Aenderung.
- `git diff -- <datei>` laesst die fremden Hunks unveraendert stehen.
- **Erst den Zweig feststellen, dann den Push messen:**
  `git rev-parse --abbrev-ref HEAD`. Nur auf `master` sagt
  `git log origin/master..master` die Wahrheit; auf einem eigenen Zweig — auch
  einem, den eine andere Sitzung angelegt hat — ist der Vergleich LEER, obwohl
  nichts auf GitHub liegt, und die Arbeit sieht gepusht aus, weil gegen den
  falschen Zweig gemessen wurde. **Das schnellste Fruehwarnzeichen steht in der
  Push-Antwort selbst: `Everything up-to-date`, obwohl in dieser Sitzung gerade Commits
  entstanden sind, heisst "falscher Zweig"** (lokal `master` == `origin/master`, weil
  der eigene Commit auf dem ausgecheckten Nebenast sitzt). Dann NICHT weiterarbeiten
  und nicht ein zweites Mal committen, sondern sofort `git branch -v` und
  `git status -sb` lesen - die Commits sind nicht verloren, sie liegen nur woanders. Auf fremdem Zweig stattdessen
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
  **Wer den Push startet, entscheidet ueber sein Scheitern.** In BrainFiles steht eine
  Windows-Benutzervariable `GITHUB_TOKEN` (scope-arm - darf in dieses Repo nicht
  schreiben). Git zieht sie dem Credential-Manager vor: derselbe Push endet aus einer
  geplanten Aufgabe heraus mit `remote: Write access to repository not granted` und
  **Exit 128**, waehrend er von Hand durchlaeuft. Fuer den einen Aufruf
  `$env:GITHUB_TOKEN=$null; $env:GH_TOKEN=$null` setzen (die Variable selbst bleibt
  stehen - sie gehoert dem Nutzer) und beides messen: „mit Token 128, ohne Token 0" ist
  der Beleg. Ein Push-Fehlschlag ist also erst dann ein Rechteproblem des Kontos, wenn
  die Sonde ohne diese beiden Variablen genauso scheitert.
  **Eine Push-Zahl ist eine Momentaufnahme.** Zwischen Messen und Berichten kann die
  andere Sitzung committen: aus „0 unpushed" wurde in Minuten „1". Direkt vor dem
  Bericht erneut `git log --oneline origin/master..HEAD` lesen und die Aenderung
  benennen („dazu kam danach noch X, nicht meiner"), statt die alte Zahl zu
  wiederholen - sonst widerspricht sich der eigene Bericht.
  **Ein abgelehnter Push heisst: die andere Sitzung war schneller — erst fetchen und
  LESEN, was kommt.** `git fetch origin`, dann `git log --oneline HEAD..origin/master`
  und `git diff --name-only HEAD...origin/master` gegen die EIGENE Pfadliste halten:
  keine gemeinsame Datei = der Merge ist harmlos. **Kein `git pull --rebase` bei
  dreckigem Baum** (rebase verweigert bei unstaged Aenderungen, und `--autostash`
  fasst fremde Arbeit an) — `git merge --no-edit origin/master` geht mit dreckigem
  Baum durch, solange sich die Pfade nicht ueberschneiden. Danach `git push`
  wiederholen und `git log --oneline -3` lesen.
  **Der Merge kann an einer UNGETRACKTEN Datei haengen, die der eingehende Commit
  hinzufuegt.** Die Fremdsitzung hat sie ueber ihren EIGENEN Index committet — der
  normale Index hat sie nie gesehen, lokal liegt sie als `??`, und der Merge bricht
  ab mit `error: The following untracked working tree files would be overwritten by
  merge` + `Aborting`. Nicht mit `-f` darueberfahren und nicht einfach loeschen:
  erst `git hash-object <pfad>` gegen `git rev-parse origin/master:<pfad>` halten.
  Gleich = inhaltsgleich: Kopie nach `cache/scratch/`, Datei entfernen, Merge laufen
  lassen, Hash danach ERNEUT pruefen (sie ist jetzt versioniert). Verschieden = die
  lokale Fassung traegt eine eigene Aenderung: wegsichern und im Bericht benennen,
  nicht wegwerfen. **Die Ursache steht in der ERSTEN Fehlerzeile** — weitere Zeilen
  im selben Abbruch (z. B. `unable to unlink old '<datei>': Invalid argument`) sind
  Folgen des abgebrochenen Auscheckens, nicht der Grund.
- `git log --oneline -1` nennt nur die eigenen Pfade, `git show --stat` passt zur Absicht,
  und der Push ist gegen `origin/master` gehalten (siehe oben, nicht blind vergleichen).
- **Jede Datei, die die Commit-Nachricht NENNT, muss im gestagten Diff stehen - und
  jede Datei, die man stagen will, muss vorher WIRKLICH geschrieben sein.** Ein
  Schreibwerkzeug, das den Vorgang verweigert (z. B. weil die Zieldatei vorher nicht
  gelesen wurde), meldet das nicht zwingend als Fehler: es schreibt nichts und liefert
  auch keine Bytezahl. **Inzwischen verweigert es meist ausdruecklich**
  (`Refusing to overwrite …: this task has not seen its full current content`) - und ein
  blosses erneutes Lesen hebt die Sperre nicht immer auf: gilt die Datei einmal als
  „partial view" (weil sie mit `offset`/`limit` gelesen wurde), bleibt sie das auch nach
  einem vollstaendigen Leseversuch, und der zweite Schreibversuch scheitert identisch.
  Verlaesslicher Weg fuer eine Datei, die man SELBST in derselben Aufgabe angelegt hat:
  den neuen Inhalt per `write_file` an einen FRISCHEN Pfad unter
  `Agenten/Hermes/cache/scratch/` schreiben (eine neue Datei braucht kein Vor-Lesen) und
  sie mit `cp` ueber das Ziel legen, vorher `.bak-JJJJMMTT` daneben. Danach
  `git diff --numstat` lesen: der Austausch muss die gewollte Aenderung zeigen, und bei
  einer selbst neu geschriebenen Datei ist ein Ganzdatei-Diff hier normal (nicht das
  Zeilenende-Symptom). Nicht in einer Schleife gegen dieselbe Sperre anlaufen - nach
  dem zweiten identischen Fehlschlag den Weg wechseln. Die Datei fehlt dann still im `git add`-Aufruf,
  `git diff --cached --numstat` nennt sie nicht, und der Commit traegt eine Nachricht
  ueber eine Aenderung, die gar nicht darin ist. Gegenprobe in EINEM Aufruf:
  `git add <pfade> && git diff --cached --numstat` - die Zahl der genannten Pfade muss
  der Absicht entsprechen; danach `git show --stat HEAD` gegen die Nachricht lesen und
  fehlende Pfade in einem Folge-Commit nachziehen (nicht die Historie umschreiben).
  **Und eine geschriebene Datei kann danach WIEDER VERSCHWINDEN:** ein Werkzeug meldete
  `bytes_written` samt `verified: true`, Minuten spaeter lag nur noch
  `__pycache__/<name>.cpython-*.pyc` da, und `git add` antwortete `fatal: pathspec …
  did not match any files`. Diese Meldung ZUERST als „Datei ist nicht da" lesen
  (`ls -l <pfad>`), nicht als Ignore-Regel oder Pfadfehler — eine ungetrackte Datei
  kann keine `.gitignore`-Regel „verschlucken", sie fehlt einfach. Geschriebene Dateien
  deshalb sofort stagen und committen, statt sie zwischen zwei Rechercheschritten liegen
  zu lassen; bei mehreren neuen Dateien die Zahl der `??`-Eintraege gegen die Zahl der
  Schreibvorgaenge halten.
- **Beim Durchgehen MEHRERER Repos ist ein leeres `@{u}` kein „nichts zu pushen".**
  `git rev-parse --abbrev-ref '@{u}'` scheitert in einem Klon ohne gesetzten Upstream;
  eine Schleife, die nur `git log '@{u}..HEAD'` zaehlt, meldet dann „0 unpushed" fuer
  JEDES solche Repo — man hoert auf zu pruefen und meldet „alles gepusht", obwohl nur
  die Messung leer war. Zwei Messungen je Repo statt einer: `git branch -r --contains
  HEAD` (kennt der Remote den Commit?) und `git status --porcelain | wc -l` (liegt noch
  Arbeit im Baum?). Reihenfolge beim Auftrag „alles pushen": erst die EIGENEN Repos
  (BrainFiles und die verschachtelten eigenen wie `Agenten/Handel/nautilus`), dann die
  Fork-Klone, an denen in dieser Sitzung wirklich gearbeitet wurde — NICHT alle Klone
  unter `Werkstatt/Repos/`; ein Fork, den diese Sitzung nie angefasst hat, bleibt
  unberuehrt und wird nur benannt.

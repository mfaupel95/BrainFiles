---
name: fremdarbeit-uebernehmen
description: 'Use when eine andere Sitzung im selben Baum gearbeitet hat.'
version: 0.1.0
author: Hermes
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [Fremdarbeit, Parallelsitzung, Wiki, Spiegelung, Commit, BrainFiles]
    related_skills: [sammelauftrag, wiki-pflege, sichern, brainfiles-auftrag]
---

# Fremdarbeit uebernehmen — Arbeit UND Wissen einer Parallelsitzung

In einem Baum mit mehreren Sitzungen hinterlaesst eine andere Sitzung zwei
Dinge: **Dateien** im Arbeitsbaum und **Wissen** in Skills. Schritt 1 des
`sammelauftrag` sammelt die Dateien. Dieses Skill holt das Wissen und sichert
beides getrennt.

Ausloeser: „uebernimm, was die andere Sitzung gebaut hat" / „lerne aus der einen
und der anderen Sitzung". Es ist **kein** Ersatz fuer `sammelauftrag` (das
buendelt offene Sitzungen zu EINER Uebergabedatei) und **kein** `befund-zu-fix`
(das schliesst einen Befund).

## When to Use

- „lerne aus der einen und der anderen Sitzung", „uebernimm, was die andere
  Sitzung gebaut hat", „was hat die Parallelsitzung gemacht"
- der Arbeitsbaum enthaelt fremde Skills, Werkzeuge oder Referenzdateien, die
  nirgends dokumentiert sind
- nach einer Sitzungsrunde mit geteiltem Baum, bevor `fremdarbeit-einziehen`
  die fremden Dateien nach 30 min einsammelt
- das Wissen einer Fremdsitzung soll ins Wiki, ohne deren Dateien zu committen

**Don't use for:** eine einzelne abgebrochene Sitzung rekonstruieren
(`sitzungs-rekonstruktion`), offene Sitzungen zu EINER Uebergabedatei
buendeln (`sammelauftrag`), einen Befund von Aussage bis Fix schliessen
(`befund-zu-fix`), nur committen (`sichern`).

## Die eine Unterscheidung

**Arbeit sammeln ist nicht Wissen sammeln.** Ein neuer Skill, ein neues
Werkzeug und eine neue Referenzdatei sind im Wiki unsichtbar, bis sie dort
stehen — und ein Skill wird ohne passenden Trigger selten geladen, das Wiki wird
immer gelesen. Wer nur committet, hat die Lehre nicht weitergegeben.

## Ablauf

### 1. Bestand messen (lesend)

```bash
git log --oneline -12
git status --porcelain
git diff --stat | tail -25
```

Ein `??`-Eintrag kann ein ganzer **Ordner** sein. Pfade aufloesen, sonst
bleibt die Liste unvollstaendig:

```bash
git status --porcelain | grep '^??' | awk '{print $2}' | while read f; do
  if [ -d "$f" ]; then find "$f" -type f | head -20; else echo "$f"; fi
done
```

`git diff --stat` nennt die **geaenderten** Dateien — dort liegen die
eigentlichen Befunde; ein neuer Skill ist nur die halbe Wahrheit.

### 2. Die Luecke messen, statt sie zu behaupten

Je Nachbar-Sitzung ein paar **identifizierende Tokens** waehlen (Werkzeugname,
Fehlercode, Task-Nummer, Modulname, Konstante) und ueber das Wiki laufen lassen:

```bash
for m in okx_takt 50011 LoadPercentage trigger-wache T-362; do
  printf '%-20s ' "$m"; grep -rl "$m" MaxHirn/Wiki/ 2>/dev/null | wc -l
done
```

Null Treffer ist der Befund: die Lehre existiert nur in Skills. Ein Treffer
heisst: dokumentiert, nicht doppelt schreiben. **Diese Messung gehoert in den
Bericht** — ohne sie ist „ich spiegle das" eine Absichtserklaerung.

### 3. Was drin ist, wirklich lesen

Einen neuen Skill nicht aus seinem Namen spiegeln: `skill_view` liefert Anlass
und Abschnitte, ein neues Skript liest man ueber Docstring und Konstanten. Bei
einer fremden Wache zuerst das **Verdrahtungs-Ziel** suchen (Cron-Job? rufende
Spur?) — eine Wache, die niemand aufruft, ist selbst der Befund.

Drei Formen, die getrennt gehoeren:

| Form | Wohin |
|---|---|
| Befund + Gegenprobe + Zahl | Wiki-Seite (erweitern, nicht danebenlegen) |
| Verfahren | Skill, der auf die Wiki-Seite **verweist** statt sie zu wiederholen |
| einzelner Messwert ohne Regel | nirgends hin — ein leerer Lauf ist ein gueltiges Ergebnis |

### 4. Spiegeln

Hausregeln und Ablage-Ort stehen im Skill `wiki-pflege`. Kurzform: bestehende
Seite erweitern, neue Seite nur fuer eine echte Klasse, `updated:` (bzw.
`stand:`) ziehen und die `INDEX.md`-Zeile **mitverbreitern**.

Vor dem Schreiben die **Zeilenenden messen** — das Haus ist nicht einheitlich
(`Lektionen/`/`Betrieb/` LF, manche `Werkzeuge/` CRLF, `Archiv/TASKS.md`
gemischt). Den Byte-Weg macht `scripts/spiegeln.py` fertig:

```bash
python …/scripts/spiegeln.py MaxHirn/Wiki/Handel/Lektionen.md <blockdatei>
```

Idempotent (existiert der Block schon, wird nichts geschrieben), `open(pfad,
'wb')` in der LETZTEN Zeile (Python wertet zuerst aus und kuerzt dann — ein
Fehler im Ausdruck DANACH laesst die Datei leer), und `git diff --numstat`
danach: eine Handvoll Zeilen geplant, ganze Datei = Zeilenende verstellt.

### 5. Getrennt committen

Nur die **Wiki-Seien** sind der eigene Auftrag. Die fremden Skill-Dateien und
Werkzeuge bleiben liegen, werden unter „nicht angefasst“ genannt — ihre
Uebernahme ist eine Entscheidung von Max.

Der Index ist geteilt, also eigener Index, und die Meldung als Datei mit
**C:-Pfad** (`git commit -F /tmp/x.txt` findet ein natives Windows-Programm
nicht, der Commit unterbleibt ohne Fehlermeldung):

```bash
git diff --cached --numstat          # fremde Pfade = eigener Index noetig
export GIT_INDEX_FILE="C:/…/cache/scratch/idx_<thema>"
git read-tree HEAD && git add <nur eigene pfade>
git diff --cached --numstat           # JEDE Zeile muss eigene sein
git commit -F "C:/…/cache/scratch/commitmsg_<thema>.txt"
unset GIT_INDEX_FILE && git add <eigene pfade>
```

### 6. Abnehmen

```bash
git show --name-only --format="" HEAD | grep -v "<eigene praefixe>"   # (leer = sauber)
git diff --numstat -- <eigene pfade>                                  # kleine Zahlen
```

Die volle Fallunterscheidung, die Zeilenend-Messwerte und die Commit-Fallen
stehen in `references/spiegeln-parallelsitzung.md` (laden mit `skill_view`).

## Pitfalls

- **`git check-ignore -v` beweist nichts.** Es trifft auch die Negationsregel
  (`!pfad`) und endet mit 0. Verlaesslich ist `git add --dry-run <pfad>`:
  `add '<pfad>'` = nicht gesperrt, Fehler 128 = gesperrt.
- **Ein Lock nach dem eigenen Commit ist meist ein Wrack — aber ein Lock bei
  laufender Parallelarbeit ist es NICHT.** Wrack-Fall: Nach dem
  Scratch-Index-Commit meldet das Nachziehen `File exists`; misst man die Datei
  danach, ist sie schon weg. Lebend-Fall: eine Sitzung, die in Schueben
  committet, haelt den 0-Byte-Lock nur Sekunden — in einer Stichprobe sieht
  man 0 echte `git.exe`-Prozesse ohne `fsmonitor` und trotzdem ist gerade ein
  Commit im Gange; der Lock verschwindet von selbst, sobald der Commit durch
  ist. Entscheidend ist Bewegung, nicht der Lock: `git log` zwischen zwei
  Messungen vergleichen und die mtimes der geaenderten Dateien beobachten —
  landet ein neuer Commit oder wandert eine mtime, gehoert der Lock der
  Sitzung und ein Umbenennen schlaegt mit PathNotFound fehl (das ist der
  Beleg, kein Fehler). Erst wenn ueber Minuten weder Commits landen noch
  mtimes wandern, umbenennen (`Move-Item -Force`;
  `[System.IO.File]::Move` mit drei Argumenten gibt es in PS 5.1 nicht), nie
  loeschen. Die Routine macht das von selbst richtig: sie ueberspringt bei
  Lock, und ein spaeterer Lauf committet die inzwischen gesicherte Arbeit
  nicht doppelt.
- **Nichts fremdes zuruecksetzen.** `git checkout -- <datei>` verwirft die
  Arbeit der anderen Sitzung. Zum Trennen `GIT_INDEX_FILE` nehmen, aus der
  Sicherung oder byteweise zurueckholen.
- **Der Zeitstempel im Sandbox-Terminal ist die Uhr des Containers**, nicht des
  Rechners — „vor 5 min" kann 7 Stunden heissen. Das Alter fremder Dateien ueber
  den Host pruefen, bevor daraus eine Reihenfolge wird.
- **Die Fremdarbeit-Routine sammelt ein, was 30 min liegt — gemessen an
  RUHE, nicht am Alter allein.** Dateien mit frischer mtime (< 30 min) sind
  per Definition Teil einer noch aktiven Sitzung; auch aeltere Dateien gehoeren
  ihr, solange Geschwister-Dateien weiter geschrieben werden und neue Commits
  landen. Der saubere Gate ist der `-Testlauf` der Routine: ueberspringt er
  wegen eines Locks, warten und spaeter erneut fahren, statt die Arbeit
  manuell wegzunehmen. Wer die fremden Dateien nicht uebernimmt, gehoert nach
  30 min einem „Anderen Sitzung"-Commit mit *anderem* Autor. Das ist eine
  offene Entscheidung fuer Max und gehoert in den Bericht.
- **Der Sweep prueft den Code nicht — und committet ihn trotzdem.** Die
  Commit-Nachricht sagt es selbst: „nicht von Hand geprueft". Am 11.10.2026 hat
  `fremdarbeit-einziehen.ps1` so zwei echte Defekte nach master gebracht
  (`getattr(obj, name, default, False)` — vier Argumente, `TypeError` bei jedem
  `status()`-Aufruf; dazu eine zweite Kraken-Node-Klasse gegen den
  read-only-Kontrakt des Moduls und auf derselben PID-Datei wie der
  Prozesse-Reiter). Ein `py_compile` findet den ersten Fall NICHT — der Aufruf
  ist syntaktisch gueltig.
  **Regel:** Eine Uebernahme, die .py-Dateien enthaelt, ist erst fertig, wenn
  `python Agenten/Hermes/scripts/syntax-tor-wache.py` leer bleibt (Syntax +
  Argumentzahl bekannter Builtins + roter Testlauf gegen
  `Agenten/Handel/testlauf_basis.json`). Das Tor sitzt seit 11.10.2026 auch
  direkt in der Routine: ein Befund in einer uebernommenen Datei bricht den
  Lauf ab, nichts wird committet, die Arbeit bleibt im Baum liegen. Der Cron
  `syntax-tor-wache` (6 h) faehrt die volle Pruefung nach.
- **Eine zurueckgenommene Aenderung gehoert an die Stelle, an der die Zahl
  steht.** Nur einen Kommentar daneben zu setzen heisst: beim naechsten Mal
  liest man den Kommentar und nicht die Zahl.

## Verification

```bash
git show --stat --format="%h %an%n%s" HEAD | head -12
git show --name-only --format="" HEAD        # nur eigene Praefixe
git status --porcelain -- <eigene pfade>    # (leer = sauber nachgezogen)
```

Erwartet: ein Commit mit **ausschliesslich** den eigenen Pfaden, eine Handvoll
geaenderter Zeilen je Wiki-Seite, und unter den eigenen Pfaden keine Ausgabe.
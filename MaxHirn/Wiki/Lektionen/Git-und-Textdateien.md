---
id: 20260921-git-und-textdateien
title: 'Lektionen — Git und Textdateien'
tags: [lektion, git]
created: 2026-09-21
updated: 2026-10-05
related: ['[[Lektionen/Tests]]', '[[Wissen/Schutzregeln]]']
summary: 'Zeilenenden, Whitelist-Falle, index.lock, Fremdarbeit im Arbeitsbaum — die vier Fallen, die am haeufigsten zugeschlagen haben.'
---

# Git und Textdateien

## 1. Zeilenenden: nie per Rewrite schreiben

**Regel.** Eine Textdatei aendern heisst: lesen als Bytes, Zeilenende aus dem ROHEN
Text ableiten, als Bytes zurueckschreiben.

```python
roh = open(pfad, "rb").read()
nl = b"\r\n" if b"\r\n" in roh else b"\n"
neu = roh.replace(alt, ersatz)
open(pfad, "wb").write(neu)
```

**Warum.** `open(pfad, encoding="utf-8")` wandelt CRLF still nach LF um; danach ist
`"\r\n" in text` immer `False` und eine Ein-Zeilen-Aenderung landet als Ganzdatei-Diff.
`Path.write_text()` dreht umgekehrt eine LF-Datei auf CRLF (`os.linesep`).
Zweimal passiert (Skill-Dateien), einmal bei `config.yaml`.

**Nachweis.** Nach JEDER Textaenderung `git diff --numstat` **je Datei**: eine gewollte
Zeile muss `1 1` zeigen. Steht dort die ganze Datei: nicht committen, zurueckholen
(`git checkout HEAD -- <datei>`), neu patchen. Ist es schon committet, in einem
Folge-Commit die Enden wiederherstellen — **nie** force-push.

**Zusatzfalle `git config set`/`hermes config set`:** schneidet den Kommentar-Schluss
der Datei ab und schreibt LF. Vorher kopieren, danach byte-genau zurueckholen,
`git diff --numstat` pruefen.

## 2. Whitelist-Falle: neu ist unsichtbar

**Regel.** BrainFiles arbeitet nach „erst alles ignorieren, dann einzeln freigeben".
Ein NEUER Ordner ist damit unsichtbar, bis er in `.gitignore` freigegeben ist.

**Nachweis.**
`git check-ignore -v <pfad>` — zeigt die Regel, die greift. Gegenprobe:
`git ls-files '<muster>'` muss die gewollten Dateien fuehren.
Global ignoriert wird per `*` (Zeile 20), Verzeichnisse werden per `!*/` freigegeben,
dann Dateimuster wie `!MaxHirn/Wiki/**/*.md`.

**Dritte Form (17.09.2026):** eine spaetere Sperre hebt eine fruehere Freigabe auf —
der LETZTE Treffer gewinnt. Beispiel: `Agenten/Handel/*/zustand.mittel.json` stand
hinter `!Agenten/Handel/moondev_funding/*.json` und machte die Freigabe wirkungslos.
Nach jeder Spur-Anlage beide Proben fahren.

## 3. `index.lock`: umbenennen, nie loeschen

**Regel.** Meldet Git „Unable to create `.git/index.lock`: File exists", erst Alter der
Datei und die echten Git-Prozesse pruefen, dann die Sperre **umbenennen**
(`.git/index.lock.verwaist-JJJJMMTT`).

**Warum.** Die Dutzenden `git fsmonitor--daemon run --detach`-Prozesse laufen dauerhaft
und beweisen nichts — zaehlen nur Prozesse OHNE `fsmonitor`. Meist war die Sperre
0 Byte und von einer abgebrochenen Fremdsitzung — **aber nicht immer**: am
13.10.2026 hielt ein echter `git commit -F -`-Prozess aus GitHub Desktop die
Sperre fast eine Stunde (haengender Commit-Dialog, kein Routinefall). Deshalb
bleibt die Prozessliste Pflicht, auch wenn die Sperre schon mehrfach alt wirkte.

**Eigener Fehlgriff, zweimal am selben Tag:** `rm -f .git/index.lock` statt
umbenennen. Eine geloeschte Sperre laesst sich nicht mehr pruefen, falls die
Einschaetzung falsch war; eine umbenannte schon. Naechstes Mal: immer
`Rename-Item`/`mv`, nie `rm`/`Remove-Item`, auch wenn die Prozessliste leer
aussieht.

## 4. Fremdarbeit im Arbeitsbaum

**Regel.** Nur eigene Pfade namentlich stagen. **Nie** `git add -A`, `git add .`,
`git commit -a`. Fremde Aenderungen in einem EIGENEN Commit mit
`--author="Andere Sitzung <fremd@local>"` sichern, wenn der Urheber nicht feststeht.

**Warum.** Es laeuft zeitweise eine zweite Hermes-Sitzung auf demselben Baum (sie
aendert z. B. `Agenten/Handel/swap/`, `Agenten/Hermes/skills/`, `Bus/stand.json`).
`git add -A` nimmt sie mit und vermischt die Urheberschaft. Kein Verwerfen
(`reset --hard`, `checkout --`, `restore`, `stash`, `clean`) — das loescht die
uncommittete Arbeit der anderen Sitzung unwiederbringlich.

**Merksatz.** Was in den letzten 10 Minuten geschrieben wurde, liegt still und wird
nicht angefasst.

**Falle — `git commit -- <pfad>` committet den ARBEITSBAUM, nicht den Index.** Ein
pfadbeschraenkter Commit geht am Index vorbei und nimmt den aktuellen Dateiinhalt:
wer fremde und eigene Zeilen in EINER Datei trennen will, schreibt damit die
Fremdarbeit in den eigenen Commit (am 22.09.2026 passiert: 47 statt 15 Zeilen).
Richtig ist: den Blob selbst bauen (`git hash-object -w --path=<pfad> --stdin`), ihn
in den Index legen (`git update-index --cacheinfo 100644,<sha>,<pfad>`) und **ohne
Pfadangabe** committen — dann zaehlt allein der Index. Der Arbeitsbaum bleibt
unberuehrt, die Fremdzeilen kommen in einen zweiten Commit mit neutraler Kennung.
Gegenprobe vorher: `git diff --cached --numstat -- <pfad>` muss die eigene Zeilenzahl
zeigen, `git diff --numstat -- <pfad>` den fremden Rest.

## 5. Zweige

`master` ist der einzige Arbeitszweig. `zwischenstand` ist die automatische
Nachtsicherung (nie dort committen). Ein eigener Zweig kostet Ueberblick ohne Gewinn.
Fruehwarnung, wenn die Nachtsicherung stillsteht:
`git log -1 --format=%ci zwischenstand`; Gegenprobe `git add -A --dry-run`
(Exitcode 128 = ein Fremd-Klon im Baum ohne ausgecheckten Commit blockiert das Staging).

## 6. Ein `D` im Arbeitsbaum wandert in den EIGENEN Commit

25.09.2026: `Agenten/Hermes/scripts/test_breite_wache.py` war committet
(`ad081ef`) und verschwand **zweimal** aus dem Arbeitsbaum. Beim zweiten Mal
stand beim Commit `D Agenten/Hermes/scripts/test_breite_wache.py` in der eigenen
Pfadliste - `git add <pfad>` stagt dann das LOESCHEN, und der Commit nahm 125
Zeilen mit. Nur weil der Stand in `ad081ef` lag, war er zurueckzuholen.

Die Ursache der Loeschung ist offen (kein Defender-Fund, kein Cron-Job, kein
`reset`/`clean` im Reflog). Die Lehre haengt nicht daran:

**Vor jedem Commit `git status --porcelain -- <pfade>` LESEN, nicht nur
abschicken.** Steht dort ein `D` oder `M` an einer Datei, die man nicht angefasst
hat, ist das ein Befund: erst `git checkout <letzter-guter-commit> -- <pfad>`,
den Inhalt zurueckholen, dann committen. Eine Pfadliste macht einen Commit nicht
sicher - nur ihr Inhalt tut es.
Gegenprobe danach: `git cat-file -e HEAD:<pfad>` (Exitcode 0 = liegt in HEAD).

## 6b. Eine Luecke von einer Sekunde wird zur dauerhaften Loeschung

Nachtrag 30.09.2026: es waren nicht eine, sondern **sechs** Dateien — alle
`test_*.py` in `Agenten/Hermes/scripts/`: `test_breite_wache.py` (`455e0fe`),
`test_waisen_wache.py` (`22e5f7d`), `test_spiegelfrist_wache.py` und
`test_spur_wache.py` (`3ef372b`), `test_live_wache_stops.py` (`aae26a9`),
`test_hermes_doctor.py` (`cc70977`). Jede lag danach nur noch als Bytecode in
`__pycache__` — Python raeumt einen verwaisten `.pyc` nicht weg, er ist der
Fingerabdruck des Verlusts (und der einzige Grund, warum die Loeschungen
ueberhaupt auffielen).

**Siebter Fall, sekundengenau (30.09.2026, `test_mcp_zombie_wache.py`).** Diesmal
ist das Fenster kurz und die Umgebung bekannt:

| Zeit | Beobachtung |
|---|---|
| 02:42:xx | Datei geschrieben (`write_file`, `verified: true`, 7.977 B), zweimal gepatcht, `python -m unittest` meldet **13 Tests gruen**, `git status` zeigt `??` |
| 02:42 | `__pycache__/test_mcp_zombie_wache.cpython-314.pyc`, 15.426 B — bleibt liegen |
| 02:45 | `ls`: **No such file or directory**; Ordnerzeit des Verzeichnisses = 02:45 |

Damit sind zwei Erklaerungen fuer diesen Fall **ausgeschlossen**: eine
Sammel-Aufraeumung untracked Dateien (im selben Zeitfenster entstanden
`dashboard-wache.py` um 02:44 und `test_dashboard_wache.py` um 02:45 in
DERSELBEN Sorte Ordner und lebten weiter) und der Fremdarbeit-Weg (die Datei war
nie in `HEAD`, es gab nichts festzuschreiben). Neu ist die **Laenge des
Fensters**: drei Minuten gegenueber den bisher bekannten Faellen, die erst nach
dem Routine-Commit auffielen.

Der **Taeter** ist offen. Gemessen und ausgeschlossen (30.09.2026): das
Werkzeug-Backend ist kein Container mit eigener Sicht (`C: on /c type ntfs`,
Terminal nativ auf dem Host), `write_file` schreibt host-sichtbar (Sonde 294 B
in beiden Sichten, `git status` zeigt `??`), kein Haus-Werkzeug loescht dort
(`datensortierung.ps1` verschiebt nur `.bak`, `systempruefung.ps1` nur
Ollama-Reststores/venvs/eigene Logs ueber 30 Tage), nirgends ein `/MIR`-Spiegel,
kein Defender-Fund auf dem Pfad, OneDrive nicht betroffen, die
PowerShell-History (1.761 Zeilen) kennt weder die Dateinamen noch
`git clean`/`checkout`/`stash`.

Der **Schadensweg** ist dagegen belegt: `Agenten/Routinen/fremdarbeit-einziehen.ps1`
sieht eine fehlende Datei nach 30 Minuten als „ruhende Fremdarbeit" und
committet die Loeschung. Die Routine ist der **Schreiber des Verlusts**, nicht
sein Urheber — und ihre Meldung nennt als Urheber „Andere Sitzung", was die
Suche in die Irre fuehrt.

**Regel.** Wer eine Datei kurz wegnimmt (Umbau, Umbenennen, Kopierversuch), hat
30 Minuten, bis sie endgueltig aus `master` ist. Und: eine Wache muss die
Luecke sehen, **bevor** die Routine sie festschreibt — danach ist jeder Befund
eine Grabsteinmeldung.

**Werkzeug.** `Agenten/Hermes/scripts/dateischwund-wache.py` (Hermes-Cron
`dateischwund-wache`, alle 15 Minuten, `no_agent`, Telegram, leere Ausgabe =
kein Befund) prueft zwei Soll-Zustaende: (a) jede Datei, die in `HEAD` steht und
im Arbeitsbaum fehlt — der T-100-Fall, sichtbar mindestens 30 Minuten vor dem
Routine-Commit; (b) jede Datei, die seit dem letzten Lauf verschwunden ist
(faengt auch nie committete Dateien) sowie eine auf 0 Byte zusammengefallene
Datei. Sie aendert nichts; sie meldet nur, mit dem fertigen
`git checkout HEAD -- <pfad>`. 18 Tests in
`Agenten/Hermes/scripts/test_dateischwund_wache.py`.

## 7. Ein eigener Index muss vom committeten Baum starten

Eine Routine, die mit `GIT_INDEX_FILE` einen **frischen** Index baut, verliert
jede Datei, die von `.gitignore` verdeckt ist - auch wenn sie in `HEAD` liegt.
`git add -A` nimmt ignorierte Pfade grundsaetzlich nicht auf; ein frischer Index
kennt den versionierten Bestand nicht und kann die Ausnahme nicht herstellen.

Gemessen am 30.09.2026 an `Agenten/Routinen/zwischenstand.ps1`: der Zweig
`zwischenstand` trug 1591 Dateien gegen 1929 in `master`, es fehlten 338
versionierte Pfade (337 davon ignoriert) - darunter `Agenten/Hermes/config.yaml`.
Der Lauf meldete trotzdem `ENDE ok` nach 4 s. Eine Wiederherstellung aus diesem
Zweig waere unvollstaendig gewesen.

**Regel:** vor `git add -A` in einem eigenen Index `git read-tree HEAD` setzen
(danach ergaenzt `add -A` nur noch Neues), oder ganz auf den eigenen Index
verzichten. `git read-tree HEAD` ist billig und macht die Sicherung erst zu einer.

**Gegenprobe nach jeder Aenderung an einer Sicherungsroutine** - beide Zahlen
gehoeren in dieselbe Meldung wie das `ok`:

```
git ls-tree -r <zweig> --name-only | wc -l        # muss ~ master entsprechen
git diff --name-status master <zweig> | grep -c '^D'   # muss 0 sein
```

**Warum das lange unsichtbar blieb:** `git check-ignore -v <pfad>` meldet nichts
fuer einen Pfad, der im **echten** Index steht - `check-ignore` ueberspringt
verfolgte Dateien und erklaert sie nie fuer ignoriert. Die Probe muss
`git check-ignore -v --no-index <pfad>` heissen, sonst prueft sie nichts
(vier Stichproben meldeten faelschlich „nicht ignoriert").

## Zugangsdaten im Arbeitsbaum sind kein Leak - HEAD pruefen

Beim Sichern von Fremdarbeit am 26.09.2026 standen in zwei VORLAGENDATEIEN
(`.env.example`, beide versioniert) echte Kennungen im Klartext: `ANTHROPIC_API_KEY`
und `TELEGRAM_BOT_TOKEN` im Klon `fomo-robinhood-radar`, ein `OPENAI_API_KEY` im
Klon `skillspector`.

Die Reihenfolge, die den Alarm richtig stellt:

1. **`git status` sagt nur „geaendert", nicht „veroeffentlicht".** Ein Wert im
   Arbeitsbaum ist eine Sitzung, die lokal gearbeitet hat; erst ein Commit macht
   daraus Geschichte.
2. **Den HEAD-Stand der Zeile pruefen**, nicht die Arbeitsbaum-Datei:
   `git show HEAD:.env.example` und dort die Zeile ansehen. In beiden Faellen war
   der Wert dort LEER - es ist nichts gepusht worden, Fork und Upstream trugen
   leere Werte. Damit ist die Reparatur ein `git checkout -- <datei>`
   (HEAD-Stand zurueck) und keine Notfallaktion.
3. **Erst danach ueber Rotation reden.** Wer sofort „Kennung neu ausstellen"
   ruft, ohne den HEAD geprueft zu haben, verwechselt Arbeitsbaum mit
   Veroeffentlichung.

Zwei Regeln fuer den Umgang mit solchen Funden:

- **Nichts committen, was wie ein Wert aussieht.** Beim Sichern der Fremdarbeit
  wurde die Datei bewusst ausgelassen; ein `git add -A` haette sie erfasst.
- **Werte nie ausgeben, auch nicht zum Beweisen.** Gemessen wird ueber Laenge und
  `sha256[:12]`, verglichen wird per Hash - dann steht der Nachweis im Protokoll,
  ohne dass ein Geheimnis im Protokoll steht.

Werkzeug fuer den Scan (liest `*.env`, `.env.example/.template/.sample` in Wurzel
und `Werkstatt`, meldet Pfad + Schluesselname + Laenge, nie den Wert):
`Agenten/Hermes/cache/scratch/keys_bereinigen.py`. Ausgenommen bleiben
`Wissen/Zugaenge.md` (Stufe 0) und die per `.gitignore` gesperrten `.env`-Dateien.

## 7. Ein Dispatcher, der je Karte einen Worktree anlegt, sammelt sie fuer immer (05.10.2026)

**Regel: die Entscheidung „Arbeit oder Wegwerf" faellt am ZWEIG, nie am Alter
des Ordners.** `git worktree list` zeigte nach einem Tag **31** Eintraege (28 in
`.worktrees/`, 3 in `.claude/worktrees/`), weil jede abgeschlossene Karte einen
Worktree mit Zweig `wt/<karte>` hinterlaesst. Zielzahl ist genau EINE Zeile — die
Wurzel.

```bash
git worktree list --porcelain | grep '^worktree ' | sed 's/^worktree //'
# je Zeile (Pfad kann Leerzeichen tragen):
git -C "$w" log --oneline master..HEAD      # eigene Commits
git -C "$w" status --porcelain              # uncommittet
git rev-list --count master..<zweig>        # DIE Entscheidung: 0 = Wegwerf
```

Beide Sorten liegen im selben Ordner: acht Zweige hatten echte Commits, 33
nicht. Ein alter Worktree mit sauberem Status kann auf einem Zweig mit drei
Commits sitzen — umgekehrt liegt die Leistung manchmal nur als uncommittete
Datei im Ordner. Wer nach „alt" sortiert, entscheidet nach einem Kriterium, das
beim naechsten Mal anders belegt ist.

Ablauf in dieser Reihenfolge: (1) Zweige mit Arbeit **zuerst** auf origin
sichern, (2) uncommittete Dateien in einen Rueckgabe-Ordner kopieren (mit
Worktree-Namenspraefix, mehrere Worktrees teilen sich Dateinamen wie
`TASKS.md`), (3) `git worktree remove --force` + `git worktree prune`,
(4) `git branch -D` nur bei `rev-list --count == 0`, (5) verwaiste Zweige auf
origin ebenfalls loeschen.

Zwei Fallen, beide gemessen:

- **`worktree remove` scheitert an Resten mit echten Junctions** (`Werkstatt`
  -> `O:\Werkstatt`, Klonen mit `.venv`). Die drei Ordner bleiben als
  Verzeichnis-Baum stehen und man loescht sie per `shutil.rmtree`. Junctions
  darf man **nicht** verfolgen, sonst hasht man 6.329 Dateien aus dem echten
  Werkstatt-Baum — zweimal passiert, Laufzeit ueber fuenf Minuten.
- **Ein 0-Byte-`.git` im uv-Cache ist kein Repo**, sondern ein Artefakt
  (`invalid gitfile format`). Nur die Datei loeschen, nicht den Ordner.

Werkzeug: `scripts/worktree-inventur.py` im Skill `git-remote-backup`.
Beim Push vorher `env -u GITHUB_TOKEN -u GH_TOKEN` (siehe Abschnitt 3/4) — eine
Benutzervariable mit schmalerem Scope wird von git dem Credential-Manager
vorgezogen und der Push endet mit `403 Write access not granted`, waehrend
derselbe Push von Hand durchgeht.

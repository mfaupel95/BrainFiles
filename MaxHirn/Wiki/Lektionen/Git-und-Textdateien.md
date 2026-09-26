---
id: 20260921-git-und-textdateien
title: 'Lektionen — Git und Textdateien'
tags: [lektion, git]
created: 2026-09-21
updated: 2026-09-26
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
und beweisen nichts — zaehlen nur Prozesse OHNE `fsmonitor`. Bisher war die Sperre
immer 0 Byte und von einer abgebrochenen Fremdsitzung.

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
und `Werkstatt/Repos`, meldet Pfad + Schluesselname + Laenge, nie den Wert):
`Agenten/Hermes/cache/scratch/keys_bereinigen.py`. Ausgenommen bleiben
`Wissen/Zugaenge.md` (Stufe 0) und die per `.gitignore` gesperrten `.env`-Dateien.
